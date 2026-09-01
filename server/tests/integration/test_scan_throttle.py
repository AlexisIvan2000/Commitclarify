import asyncio
import uuid

import pytest
import pytest_asyncio
from unittest.mock import patch

from core.clock import utcnow
from core.exceptions import RateLimitedError
from models.db import Analysis
from services.analysis import runs, throttle
from tests.conftest import TestSession


@pytest.fixture(autouse=True)
def own_session():
    from api.routers import analysis as analysis_router

    with patch.object(runs, "async_session", TestSession), patch.object(
        analysis_router, "decrypt_github_token", return_value="token",
    ):
        yield


async def _pending(db, user_id) -> Analysis:
    analysis = Analysis(
        id=uuid.uuid4(),
        user_id=user_id,
        repo_name="owner/repo",
        status="pending",
        created_at=utcnow(),
    )
    db.add(analysis)
    await db.commit()
    return analysis


@pytest_asyncio.fixture
async def analyses(db, test_user) -> list[Analysis]:
    return [await _pending(db, test_user.id) for _ in range(throttle.MINUTE.allowed + 1)]


async def _fresh_scan(analysis, github_token, session):
    yield {"event": "progress", "step": "scanning"}
    yield {"event": "done", "status": "scanned"}


async def _cached_scan(analysis, github_token, session):
    yield {"event": "progress", "step": "scanning", "cached": True}
    yield {"event": "done", "status": "scanned"}


@pytest.mark.asyncio
async def test_a_burst_of_scans_is_refused_with_a_retry_after(client, auth_headers, analyses):
    with patch.object(runs.pipeline, "run_scan_phase", _fresh_scan):
        for analysis in analyses[:-1]:
            accepted = await client.get(
                f"/analyze/{analysis.id}/stream", headers=auth_headers,
            )
            assert accepted.status_code == 200

        refused = await client.get(
            f"/analyze/{analyses[-1].id}/stream", headers=auth_headers,
        )

    assert refused.status_code == 429
    assert refused.json()["code"] == "scan_throttled"
    assert int(refused.headers["Retry-After"]) > 0
    assert refused.json()["retry_after"] == int(refused.headers["Retry-After"])


@pytest.mark.asyncio
async def test_a_cache_hit_never_costs_a_slot(client, auth_headers, analyses, test_user):
    with patch.object(runs.pipeline, "run_scan_phase", _cached_scan):
        for analysis in analyses:
            response = await client.get(
                f"/analyze/{analysis.id}/stream", headers=auth_headers,
            )
            assert response.status_code == 200

    assert throttle.spent(test_user.id) == 0


@pytest.mark.asyncio
async def test_only_one_scan_at_a_time_per_user(client, auth_headers, analyses, test_user):
    gate = asyncio.Event()

    async def slow(analysis, github_token, session):
        yield {"event": "progress", "step": "fetching"}
        await gate.wait()
        yield {"event": "done", "status": "scanned"}

    with patch.object(runs.pipeline, "run_scan_phase", slow):
        held = runs.start_scan(analyses[0], "token")

        refused = await client.get(
            f"/analyze/{analyses[1].id}/stream", headers=auth_headers,
        )

        assert refused.status_code == 429
        assert refused.json()["code"] == "run_in_flight"
        assert refused.headers["Retry-After"] == str(runs.RETRY_WHEN_BUSY)

        gate.set()
        await held.task

    assert runs.running_for(test_user.id, runs.SCAN) == 0


@pytest.mark.asyncio
async def test_reconnecting_is_not_a_second_scan(client, auth_headers, analyses):
    with patch.object(runs.pipeline, "run_scan_phase", _fresh_scan):
        first = await client.get(f"/analyze/{analyses[0].id}/stream", headers=auth_headers)
        again = await client.get(f"/analyze/{analyses[0].id}/stream", headers=auth_headers)

    assert first.status_code == 200
    assert again.status_code == 200


@pytest.mark.asyncio
async def test_one_user_cannot_starve_another(db, test_user, analyses):
    gate = asyncio.Event()

    async def slow(analysis, github_token, session):
        yield {"event": "progress", "step": "fetching"}
        await gate.wait()

    stranger = await _pending(db, uuid.uuid4())

    with patch.object(runs.pipeline, "run_scan_phase", slow):
        mine = runs.start_scan(analyses[0], "token")
        theirs = runs.start_scan(stranger, "token")

        with pytest.raises(RateLimitedError):
            runs.start_scan(analyses[1], "token")

        gate.set()
        await asyncio.gather(mine.task, theirs.task)


@pytest.mark.asyncio
async def test_the_deepening_is_also_one_at_a_time(db, test_user):
    gate = asyncio.Event()

    async def slow(analysis, github_token, session):
        yield {"event": "progress", "step": "fetching"}
        await gate.wait()

    first = await _pending(db, test_user.id)
    second = await _pending(db, test_user.id)

    with patch.object(runs.pipeline, "run_ai_phase", slow):
        held = runs.start_deepen(first, "token")

        with pytest.raises(RateLimitedError) as error:
            runs.start_deepen(second, "token")

        assert error.value.code == "run_in_flight"

        gate.set()
        await held.task
