import asyncio
import json
import uuid

import pytest
import pytest_asyncio
from unittest.mock import patch

from core.clock import utcnow
from models.db import Analysis
from services.analysis import runs
from tests.conftest import TestSession


@pytest.fixture(autouse=True)
def own_session():
    from api.routers import analysis as analysis_router

    with patch.object(runs, "async_session", TestSession), patch.object(
        analysis_router, "decrypt_github_token", return_value="token",
    ):
        yield


async def _analysis(db, test_user, status: str) -> Analysis:
    analysis = Analysis(
        id=uuid.uuid4(),
        user_id=test_user.id,
        repo_name="owner/repo",
        status=status,
        created_at=utcnow(),
    )
    db.add(analysis)
    await db.commit()
    return analysis


@pytest_asyncio.fixture
async def pending(db, test_user) -> Analysis:
    return await _analysis(db, test_user, "pending")


FETCHING = {"event": "progress", "step": "fetching", "message": "..."}
DONE = {"event": "done", "status": "scanned"}


async def _phase(analysis, github_token, session):
    yield FETCHING
    yield DONE


def _events(payload: str) -> list[dict]:
    return [
        json.loads(chunk.removeprefix("data: "))
        for chunk in payload.split("\n\n")
        if chunk.startswith("data: ")
    ]


@pytest.mark.asyncio
async def test_reconnecting_replays_the_whole_run(client, auth_headers, pending):
    with patch.object(runs.pipeline, "run_scan_phase", _phase):
        first = await client.get(f"/analyze/{pending.id}/stream", headers=auth_headers)
        again = await client.get(f"/analyze/{pending.id}/stream", headers=auth_headers)

    assert first.status_code == 200
    assert again.status_code == 200
    assert _events(first.text) == [FETCHING, DONE]
    assert _events(again.text) == [FETCHING, DONE]


@pytest.mark.asyncio
async def test_reconnecting_never_launches_the_scan_twice(client, auth_headers, pending):
    launches = 0

    async def counting(analysis, github_token, session):
        nonlocal launches
        launches += 1
        yield DONE

    with patch.object(runs.pipeline, "run_scan_phase", counting):
        await client.get(f"/analyze/{pending.id}/stream", headers=auth_headers)
        await client.get(f"/analyze/{pending.id}/stream", headers=auth_headers)

    assert launches == 1


@pytest.mark.asyncio
async def test_an_orphaned_scan_is_relaunched(client, auth_headers, db, test_user):
    analysis = await _analysis(db, test_user, "scanning")

    with patch.object(runs.pipeline, "run_scan_phase", _phase):
        response = await client.get(f"/analyze/{analysis.id}/stream", headers=auth_headers)

    assert response.status_code == 200
    assert _events(response.text) == [FETCHING, DONE]


@pytest.mark.asyncio
async def test_a_forgotten_run_sends_the_client_back_to_the_report(
    client, auth_headers, db, test_user,
):
    analysis = await _analysis(db, test_user, "scanned")

    response = await client.get(f"/analyze/{analysis.id}/stream", headers=auth_headers)

    assert response.status_code == 409
    assert response.json()["code"] == "analysis_finished"


@pytest.mark.asyncio
async def test_the_deepening_reserves_the_quota_only_once(client, auth_headers, db, test_user):
    from services.analysis import quota

    analysis = await _analysis(db, test_user, "scanned")

    async def deepened(subject, github_token, session):
        yield DONE

    with patch.object(runs.pipeline, "run_ai_phase", deepened):
        await client.get(f"/analyze/{analysis.id}/deepen/stream", headers=auth_headers)
        runs._runs.clear()
        await client.get(f"/analyze/{analysis.id}/deepen/stream", headers=auth_headers)

    assert (await quota.get_quota(test_user.github_id, db))["used"] == 1


@pytest.mark.asyncio
async def test_a_run_belonging_to_someone_else_is_refused(client, auth_headers, db):
    other = Analysis(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        repo_name="owner/repo",
        status="pending",
        created_at=utcnow(),
    )
    db.add(other)
    await db.commit()

    with patch.object(runs.pipeline, "run_scan_phase", _phase):
        runs.start(other, runs.SCAN, lambda: _phase(other, "token", None))
        response = await client.get(f"/analyze/{other.id}/stream", headers=auth_headers)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_the_stream_keeps_the_connection_warm_while_the_scan_is_silent(monkeypatch):
    monkeypatch.setattr(runs, "HEARTBEAT_SECONDS", 0.01)

    analysis = Analysis(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        repo_name="owner/repo",
        status="pending",
        created_at=utcnow(),
    )
    gate = asyncio.Event()

    async def silent():
        await gate.wait()
        yield DONE

    run = runs.start(analysis, runs.SCAN, silent)
    chunks = runs.stream(run)

    assert await asyncio.wait_for(chunks.__anext__(), timeout=1) == runs.sse(runs.HEARTBEAT)

    gate.set()
    await run.task
    await chunks.aclose()
    runs._runs.clear()


@pytest.mark.asyncio
async def test_no_active_run_is_reported_as_nothing(client, auth_headers):
    response = await client.get("/analyze/active", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() is None


@pytest.mark.asyncio
async def test_a_live_run_is_findable_after_a_reload(client, auth_headers, pending):
    gate = asyncio.Event()

    async def slow(analysis, github_token, session):
        yield FETCHING
        await gate.wait()

    with patch.object(runs.pipeline, "run_scan_phase", slow):
        held = runs.start_scan(pending, "token")

        response = await client.get("/analyze/active", headers=auth_headers)

        assert response.status_code == 200
        assert response.json() == {
            "analysis_id": str(pending.id),
            "kind": runs.SCAN,
            "repo_name": "owner/repo",
        }

        gate.set()
        await held.task

    after = await client.get("/analyze/active", headers=auth_headers)
    assert after.json() is None


@pytest.mark.asyncio
async def test_the_active_run_of_someone_else_stays_hidden(client, auth_headers, db):
    stranger = Analysis(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        repo_name="other/repo",
        status="pending",
        created_at=utcnow(),
    )
    db.add(stranger)
    await db.commit()

    gate = asyncio.Event()

    async def slow(analysis, github_token, session):
        yield FETCHING
        await gate.wait()

    with patch.object(runs.pipeline, "run_scan_phase", slow):
        held = runs.start_scan(stranger, "token")

        response = await client.get("/analyze/active", headers=auth_headers)
        assert response.json() is None

        gate.set()
        await held.task
