import asyncio
import uuid

import pytest

from core.clock import utcnow
from models.db import Analysis
from services.analysis import runs


def _analysis() -> Analysis:
    return Analysis(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        repo_name="owner/repo",
        status="pending",
        created_at=utcnow(),
    )


def _source(events, gate=None):
    async def source():
        for event in events:
            if gate is not None:
                await gate.wait()
            yield event

    return source


async def _collect(run):
    return [event async for event in run.follow()]


@pytest.mark.asyncio
async def test_a_second_start_attaches_to_the_live_run():
    analysis = _analysis()
    gate = asyncio.Event()

    first = runs.start(analysis, runs.SCAN, _source([{"event": "done"}], gate))
    second = runs.start(analysis, runs.SCAN, _source([{"event": "done"}]))

    assert first is second

    gate.set()
    await first.task


@pytest.mark.asyncio
async def test_the_scan_and_the_deepening_are_two_distinct_runs():
    analysis = _analysis()

    scan = runs.start(analysis, runs.SCAN, _source([{"event": "done"}]))
    deepen = runs.start(analysis, runs.DEEPEN, _source([{"event": "done"}]))

    assert scan is not deepen
    await asyncio.gather(scan.task, deepen.task)


@pytest.mark.asyncio
async def test_a_late_subscriber_replays_everything():
    analysis = _analysis()
    emitted = [{"event": "progress", "step": "fetching"}, {"event": "done"}]

    run = runs.start(analysis, runs.SCAN, _source(emitted))
    await run.task

    assert await _collect(run) == emitted


@pytest.mark.asyncio
async def test_the_run_survives_a_subscriber_that_walks_away():
    analysis = _analysis()
    gate = asyncio.Event()
    emitted = [{"event": "progress", "step": "scanning"}, {"event": "done"}]

    run = runs.start(analysis, runs.SCAN, _source(emitted, gate))

    follower = run.follow()
    await follower.aclose()

    gate.set()
    await run.task

    assert await _collect(run) == emitted
    assert run.events[-1]["event"] == "done"


@pytest.mark.asyncio
async def test_a_silent_run_still_sends_a_heartbeat(monkeypatch):
    monkeypatch.setattr(runs, "HEARTBEAT_SECONDS", 0.01)

    analysis = _analysis()
    gate = asyncio.Event()
    run = runs.start(analysis, runs.SCAN, _source([{"event": "done"}], gate))

    follower = run.follow()
    beat = await asyncio.wait_for(follower.__anext__(), timeout=1)

    assert beat == runs.HEARTBEAT

    gate.set()
    await run.task
    await follower.aclose()


@pytest.mark.asyncio
async def test_an_interrupted_run_says_so_before_closing():
    analysis = _analysis()
    gate = asyncio.Event()

    run = runs.start(analysis, runs.SCAN, _source([{"event": "done"}], gate))
    await asyncio.sleep(0)
    await runs.shutdown()

    assert run.events[-1] == runs.INTERRUPTED
    assert not run.alive


@pytest.mark.asyncio
async def test_a_crashing_run_closes_on_an_error_event():
    analysis = _analysis()

    async def source():
        yield {"event": "progress", "step": "fetching"}
        raise RuntimeError("boom")

    run = runs.start(analysis, runs.SCAN, source)
    await run.task

    assert run.events[-1] == {"event": "error", "message": "boom"}
    assert not run.alive


@pytest.mark.asyncio
async def test_finished_runs_are_forgotten_once_they_have_aged():
    analysis = _analysis()

    run = runs.start(analysis, runs.SCAN, _source([{"event": "done"}]))
    await run.task

    assert runs.forget_finished() == 0
    assert runs.find(analysis.id, runs.SCAN) is run

    run.finished_at = utcnow() - runs.KEEP_FINISHED_FOR - runs.KEEP_FINISHED_FOR

    assert runs.forget_finished() == 1
    assert runs.find(analysis.id, runs.SCAN) is None


@pytest.mark.asyncio
async def test_the_registry_counts_what_a_user_is_running():
    analysis = _analysis()
    other = _analysis()
    gate = asyncio.Event()

    first = runs.start(analysis, runs.SCAN, _source([{"event": "done"}], gate))
    second = runs.start(other, runs.SCAN, _source([{"event": "done"}], gate))

    assert runs.running_for(analysis.user_id) == 1
    assert runs.running_for(other.user_id) == 1

    gate.set()
    await asyncio.gather(first.task, second.task)

    assert runs.running_for(analysis.user_id) == 0
