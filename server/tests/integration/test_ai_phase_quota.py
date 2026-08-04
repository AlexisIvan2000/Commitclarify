import uuid
from contextlib import ExitStack
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import func, select

from core.clock import utcnow
from models.db import Analysis, AnalysisLog
from services.analysis import pipeline, quota
from tests.integration.test_scan_phase import REPO_DATA, _drain, _github

CLEAN = {"status": "clean", "issues": [], "recommendations": []}
ERRORED = {"status": "error", "issues": [], "recommendations": [], "error": "JSON invalide"}
FOUND = {
    "status": "issues_found",
    "issues": [{"title": "x", "severity": "low", "source": "llm"}],
    "recommendations": [],
}

TRIAGE_AXES = ("secrets_detection", "gitignore_check")
DISCOVERY_AGENTS = ("run_quality_check", "run_readme_check")


async def _reserved_analysis(db, test_user) -> Analysis:
    analysis = Analysis(
        id=uuid.uuid4(),
        user_id=test_user.id,
        repo_name="owner/repo",
        status="scanned",
        language="fr",
        created_at=utcnow(),
    )
    db.add(analysis)
    await db.commit()

    await quota.reserve(test_user.github_id, analysis.id, db)
    return analysis


def _agents(*results, side_effect=None):
    stack = ExitStack()
    repository, sha, files = _github(REPO_DATA)

    for context in (repository, sha, files):
        stack.enter_context(context)

    stack.enter_context(patch(
        "services.analysis.pipeline.collection_exists", return_value=True,
    ))
    stack.enter_context(patch(
        "services.analysis.pipeline.build_collection_name", return_value="collection",
    ))

    by_axis = dict(zip(TRIAGE_AXES, results))

    async def triage(axis, issues, language):
        if side_effect:
            raise side_effect
        return by_axis[axis]

    stack.enter_context(patch("services.analysis.pipeline.triage_axis", triage))

    for name, result in zip(DISCOVERY_AGENTS, results[2:]):
        stack.enter_context(patch(
            f"services.analysis.pipeline.{name}",
            new_callable=AsyncMock,
            return_value=result,
            side_effect=side_effect,
        ))

    return stack


async def _used(db, test_user) -> int:
    return (await quota.get_quota(test_user.github_id, db))["used"]


async def _rows(db) -> int:
    result = await db.execute(select(func.count()).select_from(AnalysisLog))
    return result.scalar_one()


@pytest.mark.asyncio
async def test_finding_nothing_is_a_result_and_is_charged(db, test_user):
    analysis = await _reserved_analysis(db, test_user)

    with _agents(CLEAN, CLEAN, CLEAN, CLEAN):
        events = await _drain(pipeline.run_ai_phase(analysis, "token", db))

    assert events[-1]["event"] == "done"
    assert analysis.status == "completed"
    assert await _used(db, test_user) == 1


@pytest.mark.asyncio
async def test_a_technical_failure_gives_the_unit_back(db, test_user):
    analysis = await _reserved_analysis(db, test_user)

    with _agents(CLEAN, CLEAN, CLEAN, CLEAN, side_effect=TimeoutError("timeout OpenAI")):
        events = await _drain(pipeline.run_ai_phase(analysis, "token", db))

    assert events[-1]["event"] == "error"
    assert analysis.status == "failed"
    assert await _used(db, test_user) == 0
    assert await _rows(db) == 0


@pytest.mark.asyncio
async def test_invalid_json_from_every_agent_gives_the_unit_back(db, test_user):
    analysis = await _reserved_analysis(db, test_user)

    with _agents(ERRORED, ERRORED, ERRORED, ERRORED):
        events = await _drain(pipeline.run_ai_phase(analysis, "token", db))

    assert events[-1]["event"] == "error"
    assert analysis.status == "failed"
    assert await _used(db, test_user) == 0


@pytest.mark.asyncio
async def test_one_failing_agent_does_not_make_the_analysis_free(db, test_user):
    analysis = await _reserved_analysis(db, test_user)

    with _agents(ERRORED, CLEAN, FOUND, CLEAN):
        events = await _drain(pipeline.run_ai_phase(analysis, "token", db))

    assert events[-1]["event"] == "done"
    assert analysis.status == "completed"
    assert await _used(db, test_user) == 1


@pytest.mark.asyncio
async def test_a_repository_that_became_unreadable_gives_the_unit_back(db, test_user):
    analysis = await _reserved_analysis(db, test_user)
    empty = {**REPO_DATA, "files": []}
    repository, sha, files = _github(empty)

    with repository, sha, files:
        events = await _drain(pipeline.run_ai_phase(analysis, "token", db))

    assert events[-1]["event"] == "error"
    assert await _used(db, test_user) == 0


@pytest.mark.asyncio
async def test_the_released_unit_can_be_spent_again(db, test_user):
    analysis = await _reserved_analysis(db, test_user)

    with _agents(CLEAN, CLEAN, CLEAN, CLEAN, side_effect=RuntimeError("boom")):
        await _drain(pipeline.run_ai_phase(analysis, "token", db))

    second = await _reserved_analysis(db, test_user)

    with _agents(CLEAN, CLEAN, CLEAN, CLEAN):
        await _drain(pipeline.run_ai_phase(second, "token", db))

    assert await _used(db, test_user) == 1
