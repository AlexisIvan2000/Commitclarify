import uuid
from datetime import timedelta

import pytest
import pytest_asyncio

from core.clock import utcnow
from core.exceptions import ConflictError
from models.db_models import Analysis, AnalysisResult
from services.analysis import pipeline


def _analysis(status: str, created_at=None) -> Analysis:
    return Analysis(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        repo_name="owner/repo",
        status=status,
        created_at=created_at or utcnow(),
    )


def test_pending_analysis_can_run():
    pipeline.assert_runnable(_analysis("pending"))


def test_completed_analysis_cannot_be_replayed():
    with pytest.raises(ConflictError):
        pipeline.assert_runnable(_analysis("completed"))


def test_failed_analysis_cannot_be_replayed():
    with pytest.raises(ConflictError):
        pipeline.assert_runnable(_analysis("failed"))


def test_running_analysis_cannot_be_started_twice():
    with pytest.raises(ConflictError):
        pipeline.assert_runnable(_analysis("processing"))


def test_stale_running_analysis_can_be_recovered():
    stale = _analysis("processing", created_at=utcnow() - timedelta(hours=2))
    pipeline.assert_runnable(stale)


@pytest_asyncio.fixture
async def analysis_with_results(db, test_user) -> Analysis:
    analysis = Analysis(
        id=uuid.uuid4(),
        user_id=test_user.id,
        repo_name="owner/repo",
        status="processing",
        created_at=utcnow(),
    )
    db.add(analysis)
    await db.commit()

    db.add(AnalysisResult(
        id=uuid.uuid4(),
        analysis_id=analysis.id,
        aspect="secrets_detection",
        status="issues_found",
        issues=[{"title": "ancien resultat"}],
        recommendations=[],
        created_at=utcnow(),
    ))
    await db.commit()
    return analysis


@pytest.mark.asyncio
async def test_rerun_replaces_results_instead_of_duplicating(db, analysis_with_results):
    from sqlalchemy import func, select

    await pipeline._persist_results(
        analysis_with_results,
        {
            "secrets_detection": {"status": "clean", "issues": [], "recommendations": []},
            "quality_check": {"status": "clean", "issues": [], "recommendations": []},
        },
        db,
    )
    await db.commit()

    total = await db.execute(
        select(func.count()).select_from(AnalysisResult).where(
            AnalysisResult.analysis_id == analysis_with_results.id
        )
    )
    assert total.scalar() == 2

    aspects = await db.execute(
        select(AnalysisResult.aspect).where(
            AnalysisResult.analysis_id == analysis_with_results.id
        )
    )
    assert sorted(a[0] for a in aspects.all()) == ["quality_check", "secrets_detection"]


@pytest.mark.asyncio
async def test_stream_refuses_completed_analysis(client, auth_headers, db, test_user):
    analysis = Analysis(
        id=uuid.uuid4(),
        user_id=test_user.id,
        repo_name="owner/repo",
        status="completed",
        created_at=utcnow(),
    )
    db.add(analysis)
    await db.commit()

    response = await client.get(f"/analyze/{analysis.id}/stream", headers=auth_headers)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_invalid_uuid_returns_422_not_500(client, auth_headers):
    for path in ("/analyze/pas-un-uuid", "/analyze/pas-un-uuid/stream", "/analyze/xx/export/pdf"):
        response = await client.get(path, headers=auth_headers)
        assert response.status_code == 422, f"{path} -> {response.status_code}"


@pytest.mark.asyncio
async def test_health_check_is_public(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
