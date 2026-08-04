import json
import uuid
from contextlib import ExitStack
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from core.clock import utcnow
from models.db import Analysis, AnalysisResult
from services.analysis import pipeline, quota
from tests.integration.test_scan_phase import REPO_DATA, _drain, _github

CLEAN = {"status": "clean", "issues": [], "recommendations": []}


async def _scanned(db, test_user) -> Analysis:
    analysis = Analysis(
        id=uuid.uuid4(),
        user_id=test_user.id,
        repo_name="owner/repo",
        status="pending",
        language="fr",
        created_at=utcnow(),
    )
    db.add(analysis)
    await db.commit()

    repository, sha, files = _github(REPO_DATA)
    with repository, sha, files:
        await _drain(pipeline.run_scan_phase(analysis, "token", db))

    await quota.reserve(test_user.github_id, analysis.id, db)
    return analysis


async def _issues(db, analysis, aspect) -> list[dict]:
    rows = await db.execute(
        select(AnalysisResult).where(
            AnalysisResult.analysis_id == analysis.id,
            AnalysisResult.aspect == aspect,
        )
    )
    return rows.scalar_one().issues


def _ai_context(llm_response: str, discovery=CLEAN):
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
    stack.enter_context(patch(
        "services.ai.triage.generate", new_callable=AsyncMock, return_value=llm_response,
    ))
    stack.enter_context(patch(
        "services.analysis.pipeline.run_quality_check",
        new_callable=AsyncMock, return_value=discovery,
    ))
    stack.enter_context(patch(
        "services.analysis.pipeline.run_readme_check",
        new_callable=AsyncMock, return_value=discovery,
    ))

    return stack


@pytest.mark.asyncio
async def test_a_verdict_on_a_supplied_identifier_is_applied(db, test_user):
    analysis = await _scanned(db, test_user)
    scanned_issues = await _issues(db, analysis, "secrets_detection")
    target = next(issue for issue in scanned_issues if issue["rule"] == "committed.env")

    response = json.dumps({"verdicts": [
        {"finding_id": target["id"], "verdict": "false_positive", "reason": "exemple"},
    ]})

    with _ai_context(response):
        await _drain(pipeline.run_ai_phase(analysis, "token", db))

    triaged = await _issues(db, analysis, "secrets_detection")
    decided = next(issue for issue in triaged if issue["id"] == target["id"])

    assert decided["verdict"] == "false_positive"
    assert decided["severity"] == "info"
    assert decided["original_severity"] == "critical"
    assert len(triaged) == len(scanned_issues)


@pytest.mark.asyncio
async def test_an_invented_identifier_leaves_every_finding_untriaged(db, test_user):
    analysis = await _scanned(db, test_user)
    scanned_issues = await _issues(db, analysis, "secrets_detection")

    response = json.dumps({"verdicts": [
        {"finding_id": scanned_issues[0]["id"], "verdict": "false_positive", "reason": "x"},
        {"finding_id": "secrets_detection:invente:nulle/part:deadbeef", "verdict": "confirmed", "reason": "y"},
    ]})

    with _ai_context(response):
        await _drain(pipeline.run_ai_phase(analysis, "token", db))

    triaged = await _issues(db, analysis, "secrets_detection")

    assert len(triaged) == len(scanned_issues)
    assert all("verdict" not in issue for issue in triaged)
    assert {issue["severity"] for issue in triaged} == {
        issue["severity"] for issue in scanned_issues
    }


@pytest.mark.asyncio
async def test_the_triage_never_adds_a_finding(db, test_user):
    analysis = await _scanned(db, test_user)
    before = await _issues(db, analysis, "secrets_detection")

    response = json.dumps({"verdicts": [
        {"finding_id": issue["id"], "verdict": "confirmed", "reason": "reel"}
        for issue in before
    ]})

    with _ai_context(response):
        await _drain(pipeline.run_ai_phase(analysis, "token", db))

    after = await _issues(db, analysis, "secrets_detection")

    assert {issue["id"] for issue in after} == {issue["id"] for issue in before}


@pytest.mark.asyncio
async def test_a_discovered_issue_on_an_invented_path_never_reaches_the_report(db, test_user):
    analysis = await _scanned(db, test_user)

    invented = {
        "status": "issues_found",
        "issues": [
            {
                "title": "Code duplique",
                "severity": "medium",
                "file_path": "src/module_inexistant.py",
                "description": "x",
                "code_hint": "y",
                "source": "llm",
            },
            {
                "title": "Logique morte",
                "severity": "low",
                "file_path": "app.py",
                "description": "x",
                "code_hint": "y",
                "source": "llm",
            },
        ],
        "recommendations": [],
    }

    response = json.dumps({"verdicts": []})

    with _ai_context(response, discovery=invented):
        await _drain(pipeline.run_ai_phase(analysis, "token", db))

    quality = await _issues(db, analysis, "quality_check")
    discovered = [issue for issue in quality if issue.get("source") == "llm"]

    assert [issue["file_path"] for issue in discovered] == ["app.py"]


@pytest.mark.asyncio
async def test_each_prompt_only_carries_the_identifiers_of_its_own_axis(db, test_user):
    analysis = await _scanned(db, test_user)
    prompts_seen = []

    async def capture(prompt, max_tokens=1024):
        prompts_seen.append(prompt)
        return json.dumps({"verdicts": []})

    stack = _ai_context("")
    with stack:
        stack.enter_context(patch("services.ai.triage.generate", capture))
        await _drain(pipeline.run_ai_phase(analysis, "token", db))

    secrets_prompt = next(p for p in prompts_seen if "id=secrets_detection:" in p)
    gitignore_prompt = next(p for p in prompts_seen if "id=gitignore_check:" in p)

    assert "id=gitignore_check:" not in secrets_prompt
    assert "id=secrets_detection:" not in gitignore_prompt
    assert all("finding_id" in prompt for prompt in prompts_seen)
