import asyncio
import json
import logging
import uuid
from datetime import timedelta
from pathlib import Path
from typing import AsyncIterator

from sqlalchemy import delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.clock import utcnow
from core.exceptions import ConflictError
from models.db_models import Analysis, AnalysisResult
from services.ai.consistency_agent import run_quality_check, run_readme_check
from services.ai.security_agent import run_gitignore_check, run_secrets_detection
from services.github.repo_fetcher import fetch_repo_files
from services.rag.chunker import chunk_files
from services.rag.indexer import build_collection_name, collection_exists, index_chunks

logger = logging.getLogger(__name__)

STALE_AFTER = timedelta(minutes=15)

AGENT_STEPS = ("secrets_detection", "gitignore_check", "quality_check", "readme_check")


def sse_event(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


def assert_runnable(analysis: Analysis) -> None:
    if analysis.status == "pending":
        return

    if analysis.status == "processing" and analysis.created_at < utcnow() - STALE_AFTER:
        logger.warning("Analyse %s relancee apres interruption", analysis.id)
        return

    if analysis.status == "processing":
        raise ConflictError("Cette analyse est deja en cours.")

    raise ConflictError(
        "Cette analyse est deja terminee. Consultez son resultat ou lancez une nouvelle analyse."
    )


async def run(
    analysis: Analysis,
    github_token: str,
    db: AsyncSession,
) -> AsyncIterator[str]:
    owner, repo = analysis.repo_name.split("/")
    analysis_id = str(analysis.id)

    try:
        analysis.status = "processing"
        await db.commit()
        logger.info("Analyse %s demarree pour %s", analysis_id, analysis.repo_name)

        yield sse_event({"event": "progress", "step": "fetching", "message": "Récupération des fichiers..."})

        repo_data = await fetch_repo_files(owner, repo, github_token)
        repo_sha = repo_data["sha"]
        files = repo_data["files"]

        yield sse_event({
            "event": "progress",
            "step": "fetching",
            "message": f"{repo_data['stats']['fetched']} fichiers récupérés",
            "truncated": repo_data["truncated"],
            "stats": repo_data["stats"],
        })

        if not files:
            logger.warning("Analyse %s: aucun fichier analysable", analysis_id)
            analysis.status = "failed"
            await db.commit()
            yield sse_event({"event": "error", "message": "Aucun fichier analysable trouvé."})
            return

        has_gitignore = any(Path(f["path"]).name == ".gitignore" for f in files)

        chunk_result = chunk_files(files)
        readme_chunks = chunk_result["readme_chunks"]

        if collection_exists(str(analysis.user_id), analysis.repo_name, repo_sha):
            collection_name = build_collection_name(str(analysis.user_id), analysis.repo_name, repo_sha)
            yield sse_event({
                "event": "progress",
                "step": "indexing",
                "message": "Index vectoriel déjà en cache",
            })
        else:
            yield sse_event({"event": "progress", "step": "indexing", "message": "Indexation en cours..."})

            index_result = await index_chunks(
                user_id=str(analysis.user_id),
                repo_name=analysis.repo_name,
                sha=repo_sha,
                chunks=chunk_result["code_chunks"] + readme_chunks,
            )
            collection_name = index_result["collection_name"]

            yield sse_event({
                "event": "progress",
                "step": "indexing",
                "message": f"{index_result['chunks_indexed']} chunks indexés",
            })

        yield sse_event({"event": "progress", "step": "analyzing", "message": "Analyse IA en cours..."})

        tasks = [
            asyncio.create_task(_labelled("secrets_detection", run_secrets_detection(collection_name, files))),
            asyncio.create_task(_labelled("gitignore_check", run_gitignore_check(collection_name, has_gitignore))),
            asyncio.create_task(_labelled("quality_check", run_quality_check(collection_name, files))),
            asyncio.create_task(_labelled("readme_check", run_readme_check(collection_name, readme_chunks))),
        ]

        results = {}
        for future in asyncio.as_completed(tasks):
            step, result = await future
            results[step] = result
            yield sse_event({"event": "step_complete", "step": step, "result": result})

        await _persist_results(analysis, results, db)

        analysis.status = "completed"
        analysis.repo_sha = repo_sha
        analysis.completed_at = utcnow()
        await db.commit()

        logger.info("Analyse %s terminee avec succes", analysis_id)
        yield sse_event({"event": "done", "analysis_id": analysis_id})

    except Exception as exc:
        logger.error("Analyse %s echouee: %s", analysis_id, exc, exc_info=True)
        analysis.status = "failed"
        await db.commit()
        yield sse_event({"event": "error", "message": str(exc)})


async def _labelled(step: str, coro) -> tuple[str, dict]:
    return step, await coro


async def _persist_results(analysis: Analysis, results: dict, db: AsyncSession) -> None:
    await db.execute(
        sql_delete(AnalysisResult).where(AnalysisResult.analysis_id == analysis.id)
    )

    for step, result in results.items():
        db.add(AnalysisResult(
            id=uuid.uuid4(),
            analysis_id=analysis.id,
            aspect=step,
            issues=result.get("issues", []),
            recommendations=result.get("recommendations", []),
            status=result.get("status", "clean"),
            created_at=utcnow(),
        ))
