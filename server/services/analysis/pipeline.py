import asyncio
import logging

from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from core.clock import utcnow
from core.exceptions import ConflictError
from core.language import normalize, text
from models.db import Analysis
from repositories import analysis as analysis_repo, scan_cache
from repositories.scan_cache import ScanKey
from services.ai.consistency_agent import run_quality_check, run_readme_check
from services.ai.triage import triage_axis
from services.ai.validation import reject_invented_paths
from services.github.repo_fetcher import (
    coverage_of,
    fetch_repo_files,
    get_repo_latest_sha,
    get_repository,
)
from services.rag.chunker import chunk_files
from services.rag.indexer import build_collection_name, collection_exists, index_chunks
from services.rag.selection import select_chunks
from services.analysis import quota
from services.scan import AXES, SCAN_VERSION, run_scan, to_issues
from services.scan.config import CONFIG_HASH

logger = logging.getLogger(__name__)

PENDING = "pending"
SCANNING = "scanning"
SCANNED = "scanned"
ANALYZING = "analyzing"
COMPLETED = "completed"
FAILED = "failed"

LEGACY_SCANNING = "processing"
SCAN_IN_PROGRESS = (SCANNING, LEGACY_SCANNING)

AGENT_STEPS = AXES

PROGRESS_INTERVAL = 0.5

TRIAGE_AXES = ("secrets_detection", "gitignore_check")
DISCOVERY_AXES = ("quality_check", "readme_check")


def assert_scannable(analysis: Analysis) -> None:
    if analysis.status == PENDING:
        return

    if analysis.status in SCAN_IN_PROGRESS:
        logger.warning(
            "Scan %s relance : plus aucune execution ne le portait", analysis.id,
        )
        return

    raise ConflictError(
        "This scan is already finished. Open its report or start a new analysis.",
        code="analysis_finished",
    )


def assert_analyzable(analysis: Analysis) -> None:
    if analysis.status == SCANNED:
        return

    if analysis.status == ANALYZING:
        logger.warning(
            "Analyse IA %s relancee : plus aucune execution ne la portait", analysis.id,
        )
        return

    if analysis.status == COMPLETED:
        raise ConflictError("This AI analysis is already finished.", code="analysis_finished")

    raise ConflictError(
        "The scan must finish before the AI analysis can start.",
        code="scan_required",
    )


assert_runnable = assert_scannable


async def run_scan_phase(
    analysis: Analysis,
    github_token: str,
    db: AsyncSession,
) -> AsyncIterator[dict]:
    owner, repo = analysis.repo_name.split("/")
    analysis_id = str(analysis.id)
    language = normalize(analysis.language)

    try:
        analysis.status = SCANNING
        analysis.phase_started_at = utcnow()
        await db.commit()
        logger.info(
            "Scan %s demarre pour %s (langue=%s)", analysis_id, analysis.repo_name, language,
        )

        yield {
            "event": "progress",
            "step": "fetching",
            "message": text("progress.fetching", language),
        }

        repository = await get_repository(owner, repo, github_token)
        repo_sha = await get_repo_latest_sha(owner, repo, github_token)
        key = ScanKey(repository["id"], repo_sha, SCAN_VERSION, CONFIG_HASH, language)

        scan = await scan_cache.get(key, db)

        if scan is not None:
            yield {
                "event": "progress",
                "step": "scanning",
                "message": text("progress.scanning", language),
                "cached": True,
            }
        else:
            repo_data = await fetch_repo_files(
                owner, repo, github_token, repo_sha=repo_sha,
            )
            coverage = coverage_of(repo_data)

            yield {
                "event": "progress",
                "step": "fetching",
                "message": text("progress.fetched", language, count=coverage["fetched_files"]),
                "truncated": repo_data["truncated"],
                "stats": repo_data["stats"],
            }

            if not repo_data["tracked_paths"]:
                logger.warning("Scan %s: aucun fichier versionne", analysis_id)
                analysis.status = FAILED
                await db.commit()
                yield {"event": "error", "message": text("progress.no_files", language)}
                return

            yield {
                "event": "progress",
                "step": "scanning",
                "message": text("progress.scanning", language),
            }

            scan = await run_scan(
                repo_data["files"],
                language,
                tracked_paths=repo_data["tracked_paths"],
                coverage=coverage,
            )
            await scan_cache.put(key, scan, db)

        await _persist_scan(analysis, scan, db)

        analysis.status = SCANNED
        analysis.repo_id = repository["id"]
        analysis.repo_sha = repo_sha
        analysis.scan_version = SCAN_VERSION
        analysis.config_hash = CONFIG_HASH
        analysis.coverage = {**scan["coverage"], "complete": scan["complete"]}
        analysis.completed_at = utcnow()
        await db.commit()

        for axis in AXES:
            yield {
                "event": "step_complete",
                "step": axis,
                "result": _axis_event(scan["axes"][axis]),
            }

        logger.info(
            "Scan %s termine: %d findings, couverture complete=%s",
            analysis_id, scan["summary"]["findings"], scan["complete"],
        )

        yield {
            "event": "done",
            "analysis_id": analysis_id,
            "status": SCANNED,
            "complete": scan["complete"],
            "scan_version": scan["scan_version"],
            "coverage": scan["coverage"],
            "can_deepen": True,
        }

    except Exception as exc:
        logger.error("Scan %s echoue: %s", analysis_id, exc, exc_info=True)
        analysis.status = FAILED
        await db.commit()
        yield {"event": "error", "message": str(exc)}


async def run_ai_phase(
    analysis: Analysis,
    github_token: str,
    db: AsyncSession,
) -> AsyncIterator[dict]:
    owner, repo = analysis.repo_name.split("/")
    analysis_id = str(analysis.id)
    language = normalize(analysis.language)

    try:
        analysis.status = ANALYZING
        analysis.phase_started_at = utcnow()
        await db.commit()
        logger.info("Analyse IA %s demarree pour %s", analysis_id, analysis.repo_name)

        yield {
            "event": "progress",
            "step": "fetching",
            "message": text("progress.fetching", language),
        }

        repo_data = await fetch_repo_files(
            owner, repo, github_token, repo_sha=analysis.repo_sha,
        )
        files = repo_data["files"]
        repo_sha = repo_data["sha"]

        if not files:
            logger.warning("Analyse IA %s: aucun fichier analysable", analysis_id)
            await quota.release(analysis.id, db, reason="aucun fichier analysable")
            analysis.status = FAILED
            await db.commit()
            yield {"event": "error", "message": text("progress.no_files", language)}
            return

        chunk_result = chunk_files(files)
        readme_chunks = chunk_result["readme_chunks"]
        user_id = str(analysis.user_id)

        if collection_exists(user_id, analysis.repo_name, repo_sha):
            collection_name = build_collection_name(user_id, analysis.repo_name, repo_sha)
            yield {
                "event": "progress",
                "step": "indexing",
                "message": text("progress.index_cached", language),
            }
        else:
            yield {
                "event": "progress",
                "step": "indexing",
                "message": text("progress.indexing", language),
            }

            selection = select_chunks(chunk_result["code_chunks"] + readme_chunks)
            progress = {"done": 0, "total": len(selection["chunks"])}

            indexing = asyncio.create_task(index_chunks(
                user_id=user_id,
                repo_name=analysis.repo_name,
                sha=repo_sha,
                chunks=selection["chunks"],
                on_progress=lambda done, total: progress.update(done=done, total=total),
            ))

            published = 0
            while not indexing.done():
                await asyncio.sleep(PROGRESS_INTERVAL)

                if progress["done"] > published:
                    published = progress["done"]
                    yield {
                        "event": "progress",
                        "step": "indexing",
                        "message": text(
                            "progress.indexing_at", language,
                            done=published, total=progress["total"],
                        ),
                        "indexed": published,
                        "to_index": progress["total"],
                    }

            index_result = await indexing
            collection_name = index_result["collection_name"]

            if selection["dropped"]:
                logger.info(
                    "Analyse IA %s: %d fragment(s) non indexe(s) sur %d (%s)",
                    analysis_id, selection["dropped"], selection["total"],
                    selection["dropped_by_tier"],
                )

            chunk_coverage = {
                "total": selection["total"],
                "indexed": selection["indexed"],
                "dropped": selection["dropped"],
                "dropped_by_tier": selection["dropped_by_tier"],
                "complete": selection["complete"],
            }
            analysis.coverage = {**(analysis.coverage or {}), "chunks": chunk_coverage}
            await db.commit()

            yield {
                "event": "progress",
                "step": "indexing",
                "message": text(
                    "progress.indexed", language, count=index_result["chunks_indexed"],
                ),
                "chunk_coverage": chunk_coverage,
            }

        yield {
            "event": "progress",
            "step": "analyzing",
            "message": text("progress.analyzing", language),
        }

        scanned = await analysis_repo.results_by_aspect(analysis.id, db)
        known_paths = set(repo_data["tracked_paths"])

        tasks = [
            asyncio.create_task(_labelled(axis, triage_axis(
                axis, scanned.get(axis, {}).get("issues", []), language,
            )))
            for axis in TRIAGE_AXES
        ] + [
            asyncio.create_task(_labelled(
                "quality_check", run_quality_check(collection_name, files, language),
            )),
            asyncio.create_task(_labelled(
                "readme_check", run_readme_check(collection_name, readme_chunks, language),
            )),
        ]

        produced = {}
        try:
            for future in asyncio.as_completed(tasks):
                step, result = await future
                produced[step] = result
                yield {"event": "step_complete", "step": step, "result": result}
        finally:
            await _drain_pending(tasks)

        if _every_agent_failed(produced):
            logger.error("Analyse IA %s: tous les agents ont echoue", analysis_id)
            await quota.release(analysis.id, db, reason="tous les agents en erreur")
            analysis.status = FAILED
            await db.commit()
            yield {"event": "error", "message": text("progress.ai_failed", language)}
            return

        await _merge_ai_into_scan(analysis, produced, known_paths, db)
        await quota.commit(analysis.id, db)

        analysis.status = COMPLETED
        analysis.repo_sha = repo_sha
        analysis.completed_at = utcnow()
        await db.commit()

        logger.info("Analyse IA %s terminee avec succes", analysis_id)
        yield {"event": "done", "analysis_id": analysis_id, "status": COMPLETED}

    except Exception as exc:
        logger.error("Analyse IA %s echouee: %s", analysis_id, exc, exc_info=True)
        await quota.release(analysis.id, db, reason=type(exc).__name__)
        analysis.status = FAILED
        await db.commit()
        yield {"event": "error", "message": str(exc)}


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


async def _drain_pending(tasks: list) -> None:
    for task in tasks:
        if not task.done():
            task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)


def _every_agent_failed(produced: dict) -> bool:
    return bool(produced) and all(
        result.get("status") == "error" for result in produced.values()
    )


def _llm_only(issues: list[dict]) -> list[dict]:
    return [issue for issue in issues if issue.get("source", "llm") == "llm"]


async def _persist_scan(analysis: Analysis, scan: dict, db: AsyncSession) -> None:
    results = {
        axis: {
            "status": result["status"],
            "issues": to_issues(result),
            "recommendations": [],
            "metrics": result["metrics"],
        }
        for axis, result in scan["axes"].items()
    }
    await analysis_repo.replace_results(analysis.id, results, db)


async def _merge_ai_into_scan(
    analysis: Analysis,
    produced: dict,
    known_paths: set[str],
    db: AsyncSession,
) -> None:
    scanned = await analysis_repo.results_by_aspect(analysis.id, db)
    merged = {}
    invented = 0

    for axis in AXES:
        base = scanned.get(
            axis, {"status": "clean", "issues": [], "recommendations": [], "metrics": None},
        )
        outcome = produced.get(axis, {})

        if axis in TRIAGE_AXES:
            issues = outcome.get("issues") or base["issues"]
        else:
            discovered, rejected = reject_invented_paths(
                _llm_only(outcome.get("issues", [])), known_paths,
            )
            invented += rejected
            issues = base["issues"] + discovered

        merged[axis] = {
            "status": "issues_found" if issues else base["status"],
            "issues": issues,
            "recommendations": outcome.get("recommendations", []),
            "metrics": base.get("metrics"),
        }

    if invented:
        logger.warning(
            "Analyse %s: %d issue(s) LLM rejetee(s) pour chemin inexistant",
            analysis.id, invented,
        )

    await analysis_repo.replace_results(analysis.id, merged, db)


async def _persist_results(analysis: Analysis, results: dict, db: AsyncSession) -> None:
    await analysis_repo.replace_results(analysis.id, results, db)
