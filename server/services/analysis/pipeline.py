import asyncio
import json
import logging

from datetime import timedelta
from pathlib import Path
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from core.clock import utcnow
from core.exceptions import ConflictError
from core.language import normalize, text
from models.db import Analysis
from repositories import analysis as analysis_repo
from services.ai.consistency_agent import run_quality_check, run_readme_check
from services.ai.security_agent import run_gitignore_check, run_secrets_detection
from services.github.repo_fetcher import coverage_of, fetch_repo_files
from services.rag.chunker import chunk_files
from services.rag.indexer import build_collection_name, collection_exists, index_chunks
from services.scan import AXES, run_scan, to_issues

logger = logging.getLogger(__name__)

STALE_AFTER = timedelta(minutes=15)

PENDING = "pending"
SCANNING = "scanning"
SCANNED = "scanned"
ANALYZING = "analyzing"
COMPLETED = "completed"
FAILED = "failed"

LEGACY_SCANNING = "processing"
SCAN_IN_PROGRESS = (SCANNING, LEGACY_SCANNING)

AGENT_STEPS = AXES


def sse_event(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


def _is_stale(analysis: Analysis) -> bool:
    return analysis.created_at < utcnow() - STALE_AFTER


def assert_scannable(analysis: Analysis) -> None:
    if analysis.status == PENDING:
        return

    if analysis.status in SCAN_IN_PROGRESS and _is_stale(analysis):
        logger.warning("Scan %s relance apres interruption", analysis.id)
        return

    if analysis.status in SCAN_IN_PROGRESS:
        raise ConflictError("Ce scan est deja en cours.", code="analysis_running")

    raise ConflictError(
        "Ce scan est deja termine. Consultez son resultat ou lancez une nouvelle analyse.",
        code="analysis_finished",
    )


def assert_analyzable(analysis: Analysis) -> None:
    if analysis.status == SCANNED:
        return

    if analysis.status == ANALYZING and _is_stale(analysis):
        logger.warning("Analyse IA %s relancee apres interruption", analysis.id)
        return

    if analysis.status == ANALYZING:
        raise ConflictError("Cette analyse IA est deja en cours.", code="analysis_running")

    if analysis.status == COMPLETED:
        raise ConflictError("Cette analyse IA est deja terminee.", code="analysis_finished")

    raise ConflictError(
        "Le scan doit etre termine avant de lancer l'analyse IA.",
        code="scan_required",
    )


assert_runnable = assert_scannable


async def run_scan_phase(
    analysis: Analysis,
    github_token: str,
    db: AsyncSession,
) -> AsyncIterator[str]:
    owner, repo = analysis.repo_name.split("/")
    analysis_id = str(analysis.id)
    language = normalize(analysis.language)

    try:
        analysis.status = SCANNING
        await db.commit()
        logger.info(
            "Scan %s demarre pour %s (langue=%s)", analysis_id, analysis.repo_name, language,
        )

        yield sse_event({
            "event": "progress",
            "step": "fetching",
            "message": text("progress.fetching", language),
        })

        repo_data = await fetch_repo_files(owner, repo, github_token)
        coverage = coverage_of(repo_data)

        yield sse_event({
            "event": "progress",
            "step": "fetching",
            "message": text("progress.fetched", language, count=coverage["fetched_files"]),
            "truncated": repo_data["truncated"],
            "stats": repo_data["stats"],
        })

        if not repo_data["tracked_paths"]:
            logger.warning("Scan %s: aucun fichier versionne", analysis_id)
            analysis.status = FAILED
            await db.commit()
            yield sse_event({"event": "error", "message": text("progress.no_files", language)})
            return

        yield sse_event({
            "event": "progress",
            "step": "scanning",
            "message": text("progress.scanning", language),
        })

        scan = await run_scan(
            repo_data["files"],
            language,
            tracked_paths=repo_data["tracked_paths"],
            coverage=coverage,
        )

        await _persist_scan(analysis, scan, db)

        analysis.status = SCANNED
        analysis.repo_sha = repo_data["sha"]
        analysis.completed_at = utcnow()
        await db.commit()

        for axis in AXES:
            yield sse_event({
                "event": "step_complete",
                "step": axis,
                "result": _axis_event(scan["axes"][axis]),
            })

        logger.info(
            "Scan %s termine: %d findings, couverture complete=%s",
            analysis_id, scan["summary"]["findings"], scan["complete"],
        )

        yield sse_event({
            "event": "done",
            "analysis_id": analysis_id,
            "status": SCANNED,
            "complete": scan["complete"],
            "scan_version": scan["scan_version"],
            "coverage": coverage,
            "can_deepen": True,
        })

    except Exception as exc:
        logger.error("Scan %s echoue: %s", analysis_id, exc, exc_info=True)
        analysis.status = FAILED
        await db.commit()
        yield sse_event({"event": "error", "message": str(exc)})


async def run_ai_phase(
    analysis: Analysis,
    github_token: str,
    db: AsyncSession,
) -> AsyncIterator[str]:
    owner, repo = analysis.repo_name.split("/")
    analysis_id = str(analysis.id)
    language = normalize(analysis.language)

    try:
        analysis.status = ANALYZING
        await db.commit()
        logger.info("Analyse IA %s demarree pour %s", analysis_id, analysis.repo_name)

        yield sse_event({
            "event": "progress",
            "step": "fetching",
            "message": text("progress.fetching", language),
        })

        repo_data = await fetch_repo_files(owner, repo, github_token)
        files = repo_data["files"]
        repo_sha = repo_data["sha"]

        if not files:
            logger.warning("Analyse IA %s: aucun fichier analysable", analysis_id)
            analysis.status = FAILED
            await db.commit()
            yield sse_event({"event": "error", "message": text("progress.no_files", language)})
            return

        has_gitignore = any(Path(f["path"]).name == ".gitignore" for f in files)
        chunk_result = chunk_files(files)
        readme_chunks = chunk_result["readme_chunks"]
        user_id = str(analysis.user_id)

        if collection_exists(user_id, analysis.repo_name, repo_sha):
            collection_name = build_collection_name(user_id, analysis.repo_name, repo_sha)
            yield sse_event({
                "event": "progress",
                "step": "indexing",
                "message": text("progress.index_cached", language),
            })
        else:
            yield sse_event({
                "event": "progress",
                "step": "indexing",
                "message": text("progress.indexing", language),
            })

            index_result = await index_chunks(
                user_id=user_id,
                repo_name=analysis.repo_name,
                sha=repo_sha,
                chunks=chunk_result["code_chunks"] + readme_chunks,
            )
            collection_name = index_result["collection_name"]

            yield sse_event({
                "event": "progress",
                "step": "indexing",
                "message": text(
                    "progress.indexed", language, count=index_result["chunks_indexed"],
                ),
            })

        yield sse_event({
            "event": "progress",
            "step": "analyzing",
            "message": text("progress.analyzing", language),
        })

        tasks = [
            asyncio.create_task(_labelled(
                "secrets_detection", run_secrets_detection(collection_name, files, language),
            )),
            asyncio.create_task(_labelled(
                "gitignore_check", run_gitignore_check(collection_name, has_gitignore, language),
            )),
            asyncio.create_task(_labelled(
                "quality_check", run_quality_check(collection_name, files, language),
            )),
            asyncio.create_task(_labelled(
                "readme_check", run_readme_check(collection_name, readme_chunks, language),
            )),
        ]

        produced = {}
        for future in asyncio.as_completed(tasks):
            step, result = await future
            produced[step] = result
            yield sse_event({"event": "step_complete", "step": step, "result": result})

        await _merge_ai_into_scan(analysis, produced, db)

        analysis.status = COMPLETED
        analysis.repo_sha = repo_sha
        analysis.completed_at = utcnow()
        await db.commit()

        logger.info("Analyse IA %s terminee avec succes", analysis_id)
        yield sse_event({"event": "done", "analysis_id": analysis_id, "status": COMPLETED})

    except Exception as exc:
        logger.error("Analyse IA %s echouee: %s", analysis_id, exc, exc_info=True)
        analysis.status = FAILED
        await db.commit()
        yield sse_event({"event": "error", "message": str(exc)})


def _axis_event(result: dict) -> dict:
    return {
        "status": result["status"],
        "issues": to_issues(result),
        "recommendations": [],
        "metrics": result["metrics"],
        "dropped": result["dropped"],
    }


async def _labelled(step: str, coro) -> tuple[str, dict]:
    return step, await coro


def _llm_only(issues: list[dict]) -> list[dict]:
    return [issue for issue in issues if issue.get("source", "llm") == "llm"]


async def _persist_scan(analysis: Analysis, scan: dict, db: AsyncSession) -> None:
    results = {
        axis: {
            "status": result["status"],
            "issues": to_issues(result),
            "recommendations": [],
        }
        for axis, result in scan["axes"].items()
    }
    await analysis_repo.replace_results(analysis.id, results, db)


async def _merge_ai_into_scan(analysis: Analysis, produced: dict, db: AsyncSession) -> None:
    scanned = await analysis_repo.results_by_aspect(analysis.id, db)
    merged = {}

    for axis in AXES:
        base = scanned.get(axis, {"status": "clean", "issues": [], "recommendations": []})
        issues = base["issues"] + _llm_only(produced.get(axis, {}).get("issues", []))

        merged[axis] = {
            "status": "issues_found" if issues else base["status"],
            "issues": issues,
            "recommendations": produced.get(axis, {}).get("recommendations", []),
        }

    await analysis_repo.replace_results(analysis.id, merged, db)


async def _persist_results(analysis: Analysis, results: dict, db: AsyncSession) -> None:
    await analysis_repo.replace_results(analysis.id, results, db)
