import json
import asyncio
import uuid
import logging
from datetime import datetime
from pathlib import Path

from io import BytesIO

from fastapi import APIRouter, HTTPException, Depends

logger = logging.getLogger(__name__)
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from api.dependencies import get_current_user
from core.database import get_db
from models.db_models import User, Analysis, AnalysisResult, AnalysisLog
from models.schemas import AnalysisResponse, AnalysisDetailResponse
from services.authentication.auth import decrypt_github_token
from services.github.repo_fetcher import fetch_repo_files, get_repo_latest_sha
from services.rag.chunker import chunk_files
from services.rag.indexer import index_chunks, collection_exists, build_collection_name
from services.ai.security_agent import run_secrets_detection, run_gitignore_check
from services.ai.consistency_agent import run_quality_check, run_readme_check


router = APIRouter(prefix="/analyze", tags=["Analysis"])

# Helper SSE
def sse_event(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"

DAILY_ANALYSIS_LIMIT = 3


# Endpoint : Quota restant (AVANT les routes dynamiques /{...})

@router.get("/quota")
async def get_quota(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    count_result = await db.execute(
        select(func.count()).select_from(AnalysisLog).where(
            AnalysisLog.github_id == current_user.github_id,
            AnalysisLog.created_at >= today_start,
        )
    )
    used = count_result.scalar()
    return {
        "used": used,
        "limit": DAILY_ANALYSIS_LIMIT,
        "remaining": max(0, DAILY_ANALYSIS_LIMIT - used),
    }


# Endpoint : Lancement de l'analyse
@router.post("/{repo_full_name:path}")
async def start_analysis(
    repo_full_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    parts = repo_full_name.split("/")
    if len(parts) != 2:
        logger.warning("Format repo invalide: %s", repo_full_name)
        raise HTTPException(status_code=400, detail="Format invalide. Attendu: owner/repo")

    # Rate limit : 3 analyses / jour par github_id
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    count_result = await db.execute(
        select(func.count()).select_from(AnalysisLog).where(
            AnalysisLog.github_id == current_user.github_id,
            AnalysisLog.created_at >= today_start,
        )
    )
    today_count = count_result.scalar()

    if today_count >= DAILY_ANALYSIS_LIMIT:
        logger.info("Rate limit atteint pour github_id=%s (%d/%d)", current_user.github_id, today_count, DAILY_ANALYSIS_LIMIT)
        raise HTTPException(
            status_code=429,
            detail=f"Limite atteinte : {DAILY_ANALYSIS_LIMIT} analyses par jour. Reessayez demain.",
        )

    # Log pour le rate limit (persiste apres suppression de compte)
    db.add(AnalysisLog(
        github_id=current_user.github_id,
    ))

    analysis = Analysis(
        id=uuid.uuid4(),
        user_id=current_user.id,
        repo_name=repo_full_name,
        status="pending",
        created_at=datetime.utcnow(),
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    logger.info("Analyse creee: id=%s repo=%s user=%s", analysis.id, repo_full_name, current_user.login)
    return {"analysis_id": str(analysis.id)}


# Endpoint : Stream des résultats

@router.get("/{analysis_id}/stream")
async def stream_analysis(
    analysis_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Analysis).where(
            Analysis.id == uuid.UUID(analysis_id),
            Analysis.user_id == current_user.id,
        )
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analyse introuvable")

    github_token = decrypt_github_token(current_user.access_token)

    return StreamingResponse(
        _analysis_generator(analysis, github_token, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# Générateur SSE

async def _analysis_generator(
    analysis: Analysis,
    github_token: str,
    db: AsyncSession,
):
    owner, repo = analysis.repo_name.split("/")
    analysis_id = str(analysis.id)

    try:
        analysis.status = "processing"
        await db.commit()
        logger.info("Analyse %s demarree pour %s", analysis_id, analysis.repo_name)

        # Étape 1 : SHA du repo
        yield sse_event({"event": "progress", "step": "fetching", "message": "Récupération des fichiers..."})

        repo_sha = await get_repo_latest_sha(owner, repo, github_token)

        # Étape 2 : Cache check
        cached = collection_exists(str(analysis.user_id), analysis.repo_name, repo_sha)

        if cached:
            yield sse_event({"event": "progress", "step": "fetching", "message": "Analyse en cache — chargement..."})
            collection_name = build_collection_name(str(analysis.user_id), analysis.repo_name, repo_sha)
            readme_chunks = []
            has_gitignore = False
        else:
            # Étape 3 : Fetch des fichiers
            repo_data = await fetch_repo_files(owner, repo, github_token)
            files = repo_data["files"]
            stats = repo_data["stats"]
            truncated = repo_data["truncated"]

            yield sse_event({
                "event": "progress",
                "step": "fetching",
                "message": f"{stats['fetched']} fichiers récupérés",
                "truncated": truncated,
                "stats": stats,
            })

            if not files:
                logger.warning("Analyse %s: aucun fichier analysable", analysis_id)
                yield sse_event({"event": "error", "message": "Aucun fichier analysable trouvé."})
                return

            # Étape 4 : Chunking
            yield sse_event({"event": "progress", "step": "indexing", "message": "Indexation en cours..."})

            chunk_result = chunk_files(files)
            code_chunks = chunk_result["code_chunks"]
            readme_chunks = chunk_result["readme_chunks"]
            all_chunks = code_chunks + readme_chunks

            has_gitignore = any(
                Path(f["path"]).name == ".gitignore"
                for f in files
            )

            # Étape 5 : Embeddings + Indexation ChromaDB
            index_result = await index_chunks(
                user_id=str(analysis.user_id),
                repo_name=analysis.repo_name,
                sha=repo_sha,
                chunks=all_chunks,
            )
            collection_name = index_result["collection_name"]

            yield sse_event({
                "event": "progress",
                "step": "indexing",
                "message": f"{index_result['chunks_indexed']} chunks indexés",
            })

        # Étape 6 : Agents en parallèle
        yield sse_event({"event": "progress", "step": "analyzing", "message": "Analyse IA en cours..."})

        tasks = [
            asyncio.create_task(_run_and_yield("secrets_detection", run_secrets_detection(collection_name))),
            asyncio.create_task(_run_and_yield("gitignore_check", run_gitignore_check(collection_name, has_gitignore))),
            asyncio.create_task(_run_and_yield("quality_check", run_quality_check(collection_name, files if not cached else []))),
            asyncio.create_task(_run_and_yield("readme_check", run_readme_check(collection_name, readme_chunks))),
        ]

        results = {}
        for future in asyncio.as_completed(tasks):
            step, result = await future
            results[step] = result

            yield sse_event({
                "event": "step_complete",
                "step": step,
                "result": result,
            })

        # Étape 7 : Sauvegarde en DB
        for step, result in results.items():
            db.add(AnalysisResult(
                id=uuid.uuid4(),
                analysis_id=analysis.id,
                aspect=step,
                issues=result.get("issues", []),
                recommendations=result.get("recommendations", []),
                status=result.get("status", "clean"),
                created_at=datetime.utcnow(),
            ))

        analysis.status = "completed"
        analysis.repo_sha = repo_sha
        analysis.completed_at = datetime.utcnow()
        await db.commit()

        logger.info("Analyse %s terminee avec succes", analysis_id)
        yield sse_event({"event": "done", "analysis_id": analysis_id})

    except Exception as e:
        logger.error("Analyse %s echouee: %s", analysis_id, e, exc_info=True)
        analysis.status = "failed"
        await db.commit()
        yield sse_event({"event": "error", "message": str(e)})


async def _run_and_yield(step: str, coro) -> tuple[str, dict]:
    result = await coro
    return step, result



# Endpoint : Historique des analyses

@router.get("/history", response_model=list[AnalysisResponse])
async def list_analyses(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Analysis)
        .where(Analysis.user_id == current_user.id)
        .order_by(Analysis.created_at.desc())
    )
    return result.scalars().all()


# Endpoint : Détail d'une analyse

@router.get("/{analysis_id}", response_model=AnalysisDetailResponse)
async def get_analysis(
    analysis_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(Analysis)
        .options(selectinload(Analysis.results))
        .where(
            Analysis.id == uuid.UUID(analysis_id),
            Analysis.user_id == current_user.id,
        )
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analyse introuvable")
    return analysis


# Endpoint : Suppression de tout l'historique (AVANT /{analysis_id} pour eviter le conflit de route)

@router.delete("/history/all")
async def delete_all_analyses(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Analysis).where(Analysis.user_id == current_user.id)
    )
    analyses = result.scalars().all()
    for analysis in analyses:
        await db.delete(analysis)
    await db.commit()
    return {"detail": f"{len(analyses)} analyse(s) supprimee(s)"}


# Endpoint : Suppression d'une analyse

@router.delete("/{analysis_id}")
async def delete_analysis(
    analysis_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Analysis).where(
            Analysis.id == uuid.UUID(analysis_id),
            Analysis.user_id == current_user.id,
        )
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analyse introuvable")

    await db.delete(analysis)
    await db.commit()
    return {"detail": "Analyse supprimée"}


# Endpoint : Export JSON

@router.get("/{analysis_id}/export/json")
async def export_json(
    analysis_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(Analysis)
        .options(selectinload(Analysis.results))
        .where(
            Analysis.id == uuid.UUID(analysis_id),
            Analysis.user_id == current_user.id,
        )
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analyse introuvable")

    data = {
        "repo_name": analysis.repo_name,
        "repo_sha": analysis.repo_sha,
        "status": analysis.status,
        "created_at": analysis.created_at.isoformat(),
        "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None,
        "results": [
            {
                "aspect": r.aspect,
                "status": r.status,
                "issues": r.issues,
                "recommendations": r.recommendations,
            }
            for r in analysis.results
        ],
    }

    filename = f"commitclarify_{analysis.repo_name.replace('/', '_')}_{analysis.created_at.strftime('%Y%m%d')}.json"
    return Response(
        content=json.dumps(data, indent=2, ensure_ascii=False),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# Endpoint : Export PDF

@router.get("/{analysis_id}/export/pdf")
async def export_pdf(
    analysis_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(Analysis)
        .options(selectinload(Analysis.results))
        .where(
            Analysis.id == uuid.UUID(analysis_id),
            Analysis.user_id == current_user.id,
        )
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analyse introuvable")

    pdf_bytes = _generate_pdf(analysis)
    filename = f"commitclarify_{analysis.repo_name.replace('/', '_')}_{analysis.created_at.strftime('%Y%m%d')}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


ASPECT_LABELS = {
    "secrets_detection": "Detection de secrets",
    "gitignore_check": "Verification .gitignore",
    "quality_check": "Qualite du code",
    "readme_check": "README vs Code",
}

SEVERITY_COLORS = {
    "critical": (0.91, 0.30, 0.24),
    "high": (0.91, 0.30, 0.24),
    "medium": (0.91, 0.64, 0.24),
    "low": (0.56, 0.56, 0.56),
}

STATUS_LABELS = {
    "clean": "Aucun probleme",
    "issues_found": "Problemes detectes",
    "unavailable": "Non disponible",
}


def _generate_pdf(analysis: Analysis) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    margin = 20 * mm
    y = height - margin

    def check_page(needed=30):
        nonlocal y
        if y < margin + needed:
            c.showPage()
            y = height - margin

    # --- Header ---
    c.setFont("Helvetica-Bold", 18)
    c.drawString(margin, y, "CommitClarify — Rapport d'analyse")
    y -= 10 * mm

    c.setFont("Helvetica", 11)
    c.drawString(margin, y, f"Repository : {analysis.repo_name}")
    y -= 6 * mm
    c.drawString(margin, y, f"Date : {analysis.created_at.strftime('%d/%m/%Y %H:%M')}")
    y -= 6 * mm
    if analysis.repo_sha:
        c.drawString(margin, y, f"SHA : {analysis.repo_sha[:12]}")
        y -= 6 * mm

    y -= 8 * mm

    # --- Results ---
    for r in analysis.results:
        check_page(40)

        label = ASPECT_LABELS.get(r.aspect, r.aspect)
        status_label = STATUS_LABELS.get(r.status, r.status)

        # Section title
        c.setFont("Helvetica-Bold", 13)
        c.drawString(margin, y, label)
        y -= 6 * mm

        c.setFont("Helvetica", 10)
        c.drawString(margin + 5 * mm, y, f"Statut : {status_label}")
        y -= 6 * mm

        # Issues
        if r.issues:
            for issue in r.issues:
                check_page(25)
                title = issue.get("title", issue.get("message", issue.get("description", str(issue))))
                severity = issue.get("severity", "low")
                file_path = issue.get("file_path", "")
                code_hint = issue.get("code_hint", "")

                sr, sg, sb = SEVERITY_COLORS.get(severity, (0.5, 0.5, 0.5))
                c.setFillColorRGB(sr, sg, sb)
                c.setFont("Helvetica-Bold", 10)
                c.drawString(margin + 5 * mm, y, f"[{severity.upper()}] {title}")
                c.setFillColorRGB(0, 0, 0)
                y -= 5 * mm

                if file_path:
                    check_page()
                    c.setFont("Helvetica", 9)
                    c.setFillColorRGB(0.4, 0.4, 0.4)
                    c.drawString(margin + 10 * mm, y, f"Fichier : {file_path}")
                    c.setFillColorRGB(0, 0, 0)
                    y -= 4.5 * mm

                if code_hint:
                    check_page()
                    c.setFont("Courier", 8)
                    c.setFillColorRGB(0.3, 0.3, 0.3)
                    # Tronquer si trop long
                    hint = code_hint[:100] + ("..." if len(code_hint) > 100 else "")
                    c.drawString(margin + 10 * mm, y, hint)
                    c.setFillColorRGB(0, 0, 0)
                    y -= 4.5 * mm

                y -= 2 * mm

        # Recommendations
        if r.recommendations:
            check_page(15)
            c.setFont("Helvetica-Bold", 10)
            c.drawString(margin + 5 * mm, y, "Recommandations :")
            y -= 5 * mm

            for rec in r.recommendations:
                check_page()
                msg = rec.get("message", rec.get("description", str(rec)))
                c.setFont("Helvetica", 9)
                # Wrap long text
                max_chars = 90
                while msg:
                    check_page()
                    c.drawString(margin + 10 * mm, y, f"- {msg[:max_chars]}")
                    msg = msg[max_chars:]
                    y -= 4.5 * mm

        y -= 8 * mm

    # --- Footer ---
    c.setFont("Helvetica", 8)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawString(margin, 10 * mm, "Genere par CommitClarify")
    c.setFillColorRGB(0, 0, 0)

    c.save()
    return buf.getvalue()
