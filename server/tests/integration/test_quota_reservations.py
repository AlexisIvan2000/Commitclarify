import uuid
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import func, select

from core import maintenance
from core.clock import utcnow
from core.config import DAILY_ANALYSIS_LIMIT
from core.exceptions import QuotaExceededError
from models.db import Analysis, AnalysisLog
from repositories import analysis as analysis_repo
from services.analysis import quota


async def _rows(db) -> int:
    result = await db.execute(select(func.count()).select_from(AnalysisLog))
    return result.scalar_one()


async def _analysis(db, test_user, status="scanned") -> Analysis:
    analysis = Analysis(
        id=uuid.uuid4(),
        user_id=test_user.id,
        repo_name="owner/repo",
        status=status,
        language="fr",
        created_at=utcnow(),
    )
    db.add(analysis)
    await db.commit()
    return analysis


@pytest.mark.asyncio
async def test_a_reservation_counts_against_the_balance_immediately(db, test_user):
    before = await quota.get_quota(test_user.github_id, db)

    await quota.reserve(test_user.github_id, uuid.uuid4(), db)
    after = await quota.get_quota(test_user.github_id, db)

    assert after["used"] == before["used"] + 1
    assert after["remaining"] == before["remaining"] - 1


@pytest.mark.asyncio
async def test_committing_keeps_the_unit_spent(db, test_user):
    analysis_id = uuid.uuid4()
    await quota.reserve(test_user.github_id, analysis_id, db)

    await quota.commit(analysis_id, db)
    await db.commit()

    assert (await quota.get_quota(test_user.github_id, db))["used"] == 1


@pytest.mark.asyncio
async def test_releasing_gives_the_unit_back(db, test_user):
    analysis_id = uuid.uuid4()
    await quota.reserve(test_user.github_id, analysis_id, db)

    await quota.release(analysis_id, db)
    await db.commit()

    assert (await quota.get_quota(test_user.github_id, db))["used"] == 0
    assert await _rows(db) == 0


@pytest.mark.asyncio
async def test_a_committed_unit_can_never_be_released(db, test_user):
    analysis_id = uuid.uuid4()
    await quota.reserve(test_user.github_id, analysis_id, db)
    await quota.commit(analysis_id, db)
    await db.commit()

    await quota.release(analysis_id, db)
    await db.commit()

    assert (await quota.get_quota(test_user.github_id, db))["used"] == 1


@pytest.mark.asyncio
async def test_the_limit_blocks_before_any_work_starts(db, test_user):
    for _ in range(DAILY_ANALYSIS_LIMIT):
        await quota.reserve(test_user.github_id, uuid.uuid4(), db)

    with pytest.raises(QuotaExceededError):
        await quota.reserve(test_user.github_id, uuid.uuid4(), db)


@pytest.mark.asyncio
async def test_an_expired_reservation_stops_counting_even_before_the_sweep(db, test_user):
    analysis_repo.stage_reservation(
        test_user.github_id, uuid.uuid4(), utcnow() - timedelta(minutes=1), db,
    )
    await db.commit()

    assert (await quota.get_quota(test_user.github_id, db))["used"] == 0
    assert await _rows(db) == 1


@pytest.mark.asyncio
async def test_the_sweep_reclaims_what_a_killed_worker_left_behind(db, test_user):
    analysis_repo.stage_reservation(
        test_user.github_id, uuid.uuid4(), utcnow() - timedelta(minutes=1), db,
    )
    live = uuid.uuid4()
    await quota.reserve(test_user.github_id, live, db)

    released = await quota.sweep_expired(db)
    await db.commit()

    assert released == 1
    assert await _rows(db) == 1
    assert (await quota.get_quota(test_user.github_id, db))["used"] == 1


@pytest.mark.asyncio
async def test_the_sweep_never_touches_committed_units(db, test_user):
    analysis_id = uuid.uuid4()
    await quota.reserve(test_user.github_id, analysis_id, db)
    await quota.commit(analysis_id, db)
    await db.commit()

    assert await quota.sweep_expired(db) == 0
    assert (await quota.get_quota(test_user.github_id, db))["used"] == 1


@pytest.mark.asyncio
async def test_the_sweeper_task_survives_a_failing_pass():
    with patch(
        "core.maintenance.sweep_once", new_callable=AsyncMock, side_effect=RuntimeError("boom"),
    ) as sweep:
        task = maintenance.start(interval=0.01)
        import asyncio

        await asyncio.sleep(0.05)
        await maintenance.stop(task)

    assert sweep.await_count > 1


@pytest.mark.asyncio
async def test_a_scan_never_touches_the_quota(client, auth_headers, db, test_user):
    from tests.integration.test_scan_phase import REPO_DATA, _drain, _github
    from services.analysis import pipeline

    analysis = await _analysis(db, test_user, status="pending")
    repository, sha, files = _github(REPO_DATA)

    with repository, sha, files:
        await _drain(pipeline.run_scan_phase(analysis, "token", db))

    assert analysis.status == "scanned"
    assert await _rows(db) == 0
    assert (await quota.get_quota(test_user.github_id, db))["used"] == 0


@pytest.mark.asyncio
async def test_starting_an_analysis_does_not_spend_anything(client, auth_headers, db, test_user):
    response = await client.post("/analyze/owner/repo", headers=auth_headers)

    assert response.status_code == 200
    assert (await quota.get_quota(test_user.github_id, db))["used"] == 0


@pytest.mark.asyncio
async def test_the_balance_is_readable_before_the_click(client, auth_headers):
    response = await client.get("/analyze/quota", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == {
        "used": 0,
        "limit": DAILY_ANALYSIS_LIMIT,
        "remaining": DAILY_ANALYSIS_LIMIT,
    }


@pytest.mark.asyncio
async def test_deepening_is_refused_when_the_balance_is_empty(
    client, auth_headers, db, test_user,
):
    analysis = await _analysis(db, test_user)

    for _ in range(DAILY_ANALYSIS_LIMIT):
        await quota.reserve(test_user.github_id, uuid.uuid4(), db)

    response = await client.get(f"/analyze/{analysis.id}/deepen/stream", headers=auth_headers)

    assert response.status_code == 429
    assert analysis.status == "scanned"
