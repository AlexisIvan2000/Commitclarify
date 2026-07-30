import json
import logging
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.dependencies import get_current_user
from core.database import get_db
from core.exceptions import NotFoundError, ValidationError
from core.language import DEFAULT_LANGUAGE, normalize
from models.db_models import Analysis, User
from models.schemas import AnalysisDetailResponse, AnalysisResponse, QuotaResponse
from services.analysis import pipeline, quota
from services.authentication.auth import decrypt_github_token
from services.export.pdf import generate_pdf
from services.export.serializers import analysis_to_dict, export_filename

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analyze", tags=["Analysis"])


async def _get_owned_analysis(
    analysis_id: uuid.UUID,
    user: User,
    db: AsyncSession,
    with_results: bool = False,
) -> Analysis:
    query = select(Analysis).where(
        Analysis.id == analysis_id,
        Analysis.user_id == user.id,
    )
    if with_results:
        query = query.options(selectinload(Analysis.results))

    result = await db.execute(query)
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise NotFoundError("Analyse introuvable")
    return analysis


@router.get("/quota", response_model=QuotaResponse)
async def get_quota(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await quota.get_quota(current_user.github_id, db)


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


@router.delete("/history/all")
async def delete_all_analyses(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Analysis).where(Analysis.user_id == current_user.id))
    analyses = result.scalars().all()

    for analysis in analyses:
        await db.delete(analysis)
    await db.commit()

    return {"detail": f"{len(analyses)} analyse(s) supprimee(s)"}


@router.post("/{repo_full_name:path}")
async def start_analysis(
    repo_full_name: str,
    language: str = DEFAULT_LANGUAGE,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if len(repo_full_name.split("/")) != 2:
        logger.warning("Format repo invalide: %s", repo_full_name)
        raise ValidationError("Format invalide. Attendu: owner/repo")

    await quota.consume(current_user.github_id, db)

    analysis = Analysis(
        user_id=current_user.id,
        repo_name=repo_full_name,
        status="pending",
        language=normalize(language),
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    logger.info(
        "Analyse creee: id=%s repo=%s user=%s langue=%s",
        analysis.id, repo_full_name, current_user.login, analysis.language,
    )
    return {"analysis_id": str(analysis.id), "language": analysis.language}


@router.get("/{analysis_id}/stream")
async def stream_analysis(
    analysis_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    analysis = await _get_owned_analysis(analysis_id, current_user, db)
    pipeline.assert_runnable(analysis)

    github_token = decrypt_github_token(current_user.access_token)

    return StreamingResponse(
        pipeline.run(analysis, github_token, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{analysis_id}", response_model=AnalysisDetailResponse)
async def get_analysis(
    analysis_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _get_owned_analysis(analysis_id, current_user, db, with_results=True)


@router.delete("/{analysis_id}")
async def delete_analysis(
    analysis_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    analysis = await _get_owned_analysis(analysis_id, current_user, db)
    await db.delete(analysis)
    await db.commit()
    return {"detail": "Analyse supprimée"}


@router.get("/{analysis_id}/export/json")
async def export_json(
    analysis_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    analysis = await _get_owned_analysis(analysis_id, current_user, db, with_results=True)
    filename = export_filename(analysis, "json")

    return Response(
        content=json.dumps(analysis_to_dict(analysis), indent=2, ensure_ascii=False),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{analysis_id}/export/pdf")
async def export_pdf(
    analysis_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    analysis = await _get_owned_analysis(analysis_id, current_user, db, with_results=True)
    filename = export_filename(analysis, "pdf")

    return Response(
        content=generate_pdf(analysis),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
