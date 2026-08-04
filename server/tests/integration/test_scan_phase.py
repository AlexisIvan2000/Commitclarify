import json
import uuid
from datetime import timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from core.clock import utcnow
from core.exceptions import ConflictError
from models.db import Analysis, AnalysisResult
from services.analysis import pipeline
from services.export.pdf import generate_pdf
from services.export.serializers import analysis_to_dict

def _file(path: str, content: str) -> dict:
    return {
        "path": path,
        "sha": f"blob-{path}",
        "size": len(content),
        "content": content,
        "language": Path(path).suffix.lstrip(".") or "text",
    }


REPO_DATA = {
    "sha": "deadbeef" * 5,
    "truncated": False,
    "tracked_paths": [
        ".gitignore", "README.md", "app.py", "requirements.txt", ".env",
    ],
    "files": [
        _file(".gitignore", "*.log\n"),
        _file("README.md", "# App\n\nSee [guide](docs/guide.md).\n"),
        _file("app.py", "import os\n\nKEY = os.getenv('APP_SECRET')\n"),
        _file("requirements.txt", "fastapi==1.0\nrequests==2.0\nhttpx==0.28\n"),
        _file(".env", "TOKEN=sk-abcdefghijklmnopqrstuvwxyz0123\n"),
    ],
    "readme": None,
    "stats": {
        "total_detected": 5,
        "fetched": 5,
        "skipped": 0,
        "tracked": 5,
        "excluded": {},
        "fetch_failures": {},
        "fetched_detail": {},
        "capped_over_limit": 0,
    },
}


def _events(raw: list[str]) -> list[dict]:
    return [json.loads(chunk.removeprefix("data: ").strip()) for chunk in raw]


async def _drain(generator) -> list[dict]:
    return _events([chunk async for chunk in generator])


REPOSITORY = {"id": 424242, "full_name": "owner/repo", "default_branch": "main"}


def _github(repo_data=REPO_DATA):
    return (
        patch(
            "services.analysis.pipeline.get_repository",
            new_callable=AsyncMock,
            return_value=REPOSITORY,
        ),
        patch(
            "services.analysis.pipeline.get_repo_latest_sha",
            new_callable=AsyncMock,
            return_value=repo_data["sha"],
        ),
        patch(
            "services.analysis.pipeline.fetch_repo_files",
            new_callable=AsyncMock,
            return_value=repo_data,
        ),
    )


@pytest.fixture
def fetched():
    repository, sha, files = _github()
    with repository, sha, files as mock:
        yield mock


async def _pending(db, test_user) -> Analysis:
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
    return analysis


@pytest.mark.asyncio
async def test_scan_phase_reaches_scanned_without_any_llm_call(db, test_user, fetched):
    analysis = await _pending(db, test_user)

    with patch("services.ai.llm.generate", new_callable=AsyncMock) as llm:
        events = await _drain(pipeline.run_scan_phase(analysis, "token", db))

    llm.assert_not_called()
    assert analysis.status == "scanned"
    assert events[-1]["event"] == "done"
    assert events[-1]["status"] == "scanned"


@pytest.mark.asyncio
async def test_the_stream_closes_at_scanned_and_does_not_wait(db, test_user, fetched):
    analysis = await _pending(db, test_user)

    events = await _drain(pipeline.run_scan_phase(analysis, "token", db))
    kinds = [event["event"] for event in events]

    assert kinds.count("done") == 1
    assert kinds[-1] == "done"
    assert "analyzing" not in [event.get("step") for event in events]


@pytest.mark.asyncio
async def test_every_axis_is_persisted_by_the_scan(db, test_user, fetched):
    analysis = await _pending(db, test_user)
    await _drain(pipeline.run_scan_phase(analysis, "token", db))

    rows = await db.execute(
        select(AnalysisResult).where(AnalysisResult.analysis_id == analysis.id)
    )
    aspects = {row.aspect for row in rows.scalars().all()}

    assert aspects == set(pipeline.AXES)


@pytest.mark.asyncio
async def test_a_scanned_report_exports_to_pdf_and_json(db, test_user, fetched):
    analysis = await _pending(db, test_user)
    await _drain(pipeline.run_scan_phase(analysis, "token", db))

    loaded = await db.execute(
        select(Analysis).where(Analysis.id == analysis.id)
    )
    stored = loaded.scalar_one()
    await db.refresh(stored, ["results"])

    pdf = generate_pdf(stored)
    payload = analysis_to_dict(stored)

    assert pdf.startswith(b"%PDF")
    assert len(payload["results"]) == len(pipeline.AXES)
    assert payload["status"] == "scanned"


@pytest.mark.asyncio
async def test_the_scan_finds_the_committed_secret(db, test_user, fetched):
    analysis = await _pending(db, test_user)
    events = await _drain(pipeline.run_scan_phase(analysis, "token", db))

    secrets = next(
        event for event in events
        if event["event"] == "step_complete" and event["step"] == "secrets_detection"
    )
    rules = {issue["rule"] for issue in secrets["result"]["issues"]}

    assert secrets["result"]["status"] == "issues_found"
    assert "committed.env" in rules


@pytest.mark.asyncio
async def test_indexing_never_happens_during_the_scan(db, test_user, fetched):
    analysis = await _pending(db, test_user)

    with patch(
        "services.analysis.pipeline.index_chunks", new_callable=AsyncMock,
    ) as index:
        await _drain(pipeline.run_scan_phase(analysis, "token", db))

    index.assert_not_called()


@pytest.mark.asyncio
async def test_a_repository_without_tracked_files_fails_cleanly(db, test_user):
    analysis = await _pending(db, test_user)
    empty = {**REPO_DATA, "files": [], "tracked_paths": []}
    repository, sha, files = _github(empty)

    with repository, sha, files:
        events = await _drain(pipeline.run_scan_phase(analysis, "token", db))

    assert events[-1]["event"] == "error"
    assert analysis.status == "failed"


@pytest.mark.asyncio
async def test_a_second_scan_of_the_same_commit_reuses_the_cache(db, test_user):
    first = await _pending(db, test_user)
    second = await _pending(db, test_user)
    repository, sha, files = _github()

    with repository, sha, files as fetch:
        await _drain(pipeline.run_scan_phase(first, "token", db))
        assert fetch.await_count == 1

        await _drain(pipeline.run_scan_phase(second, "token", db))
        assert fetch.await_count == 1

    assert second.status == "scanned"
    assert second.scan_version == first.scan_version
    assert second.repo_id == REPOSITORY["id"]


@pytest.mark.asyncio
async def test_the_cached_scan_is_invisible_to_the_client(db, test_user):
    first = await _pending(db, test_user)
    second = await _pending(db, test_user)
    repository, sha, files = _github()

    with repository, sha, files:
        fresh = await _drain(pipeline.run_scan_phase(first, "token", db))
        cached = await _drain(pipeline.run_scan_phase(second, "token", db))

    def payloads(events):
        return [
            {key: value for key, value in event.items() if key != "analysis_id"}
            for event in events
            if event["event"] in ("step_complete", "done")
        ]

    assert payloads(fresh) == payloads(cached)


@pytest.mark.asyncio
async def test_another_language_does_not_hit_the_cache(db, test_user):
    french = await _pending(db, test_user)
    english = await _pending(db, test_user)
    english.language = "en"
    await db.commit()

    repository, sha, files = _github()
    with repository, sha, files as fetch:
        await _drain(pipeline.run_scan_phase(french, "token", db))
        await _drain(pipeline.run_scan_phase(english, "token", db))

        assert fetch.await_count == 2


@pytest.mark.asyncio
async def test_a_newer_scan_version_bypasses_the_cache(db, test_user):
    first = await _pending(db, test_user)
    second = await _pending(db, test_user)
    repository, sha, files = _github()

    with repository, sha, files as fetch:
        await _drain(pipeline.run_scan_phase(first, "token", db))

        with patch("services.analysis.pipeline.SCAN_VERSION", pipeline.SCAN_VERSION + 1):
            await _drain(pipeline.run_scan_phase(second, "token", db))

        assert fetch.await_count == 2


@pytest.mark.asyncio
async def test_metrics_survive_persistence(db, test_user, fetched):
    analysis = await _pending(db, test_user)
    await _drain(pipeline.run_scan_phase(analysis, "token", db))

    rows = await db.execute(
        select(AnalysisResult).where(
            AnalysisResult.analysis_id == analysis.id,
            AnalysisResult.aspect == "quality_check",
        )
    )
    metrics = rows.scalar_one().metrics

    assert metrics["complexity"]["threshold"] == 10
    assert "source_files_in_sample" in metrics


def _analysis(status: str, created_at=None) -> Analysis:
    return Analysis(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        repo_name="owner/repo",
        status=status,
        created_at=created_at or utcnow(),
    )


def test_a_scanned_analysis_cannot_be_scanned_again():
    with pytest.raises(ConflictError) as error:
        pipeline.assert_scannable(_analysis("scanned"))

    assert error.value.code == "analysis_finished"


def test_the_ai_phase_requires_a_finished_scan():
    with pytest.raises(ConflictError) as error:
        pipeline.assert_analyzable(_analysis("pending"))

    assert error.value.code == "scan_required"


def test_the_ai_phase_accepts_a_scanned_analysis():
    pipeline.assert_analyzable(_analysis("scanned"))


def test_the_ai_phase_refuses_a_completed_analysis():
    with pytest.raises(ConflictError) as error:
        pipeline.assert_analyzable(_analysis("completed"))

    assert error.value.code == "analysis_finished"


def test_a_stale_ai_phase_can_be_recovered():
    pipeline.assert_analyzable(_analysis("analyzing", created_at=utcnow() - timedelta(hours=2)))


def test_a_running_ai_phase_cannot_be_started_twice():
    with pytest.raises(ConflictError) as error:
        pipeline.assert_analyzable(_analysis("analyzing"))

    assert error.value.code == "analysis_running"
