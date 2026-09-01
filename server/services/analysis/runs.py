
import asyncio
import json
import logging
import uuid

from collections.abc import AsyncIterator, Callable
from datetime import timedelta

from core.clock import utcnow
from core.database import async_session
from core.exceptions import RateLimitedError
from models.db import Analysis
from repositories import analysis as analysis_repo
from services.analysis import pipeline, throttle

logger = logging.getLogger(__name__)

HEARTBEAT_SECONDS = 15.0
KEEP_FINISHED_FOR = timedelta(minutes=15)

SCAN = "scan"
DEEPEN = "deepen"

HEARTBEAT = {"event": "ping"}
INTERRUPTED = {
    "event": "error",
    "code": "run_interrupted",
    "message": "The server interrupted this run. Start the analysis again.",
}
MISSING = {
    "event": "error",
    "code": "not_found",
    "message": "Analysis not found",
}

Source = Callable[[], AsyncIterator[dict]]


class Run:
    def __init__(self, analysis_id: uuid.UUID, user_id: uuid.UUID, phase: str):
        self.analysis_id = analysis_id
        self.user_id = user_id
        self.phase = phase
        self.events: list[dict] = []
        self.finished_at = None
        self.task: asyncio.Task | None = None
        self._changed = asyncio.Event()

    @property
    def alive(self) -> bool:
        return self.finished_at is None

    def emit(self, event: dict) -> None:
        self.events.append(event)
        self._wake()

    def close(self) -> None:
        self.finished_at = utcnow()
        self._wake()

    def _wake(self) -> None:
        waiters, self._changed = self._changed, asyncio.Event()
        waiters.set()

    async def follow(self) -> AsyncIterator[dict]:
        cursor = 0

        while True:
            while cursor < len(self.events):
                yield self.events[cursor]
                cursor += 1

            if not self.alive:
                return

            waiter = self._changed
            try:
                await asyncio.wait_for(waiter.wait(), HEARTBEAT_SECONDS)
            except asyncio.TimeoutError:
                yield HEARTBEAT


_runs: dict[tuple[uuid.UUID, str], Run] = {}


def find(analysis_id: uuid.UUID, phase: str) -> Run | None:
    return _runs.get((analysis_id, phase))


def running_for(user_id: uuid.UUID, phase: str | None = None) -> int:
    return sum(
        1 for run in _runs.values()
        if run.alive and run.user_id == user_id and (phase is None or run.phase == phase)
    )


ALREADY_RUNNING = {
    SCAN: "A scan is already running on your account.",
    DEEPEN: "An AI analysis is already running on your account.",
}

RETRY_WHEN_BUSY = 30


def assert_free(user_id: uuid.UUID, phase: str) -> None:
    if running_for(user_id, phase) == 0:
        return

    logger.warning(
        "Execution %s refusee : l'utilisateur %s en porte deja une", phase, user_id,
    )
    raise RateLimitedError(
        ALREADY_RUNNING[phase], code="run_in_flight", retry_after=RETRY_WHEN_BUSY,
    )


def start(analysis: Analysis, phase: str, source: Source) -> Run:
    live = find(analysis.id, phase)
    if live is not None and live.alive:
        return live

    run = Run(analysis.id, analysis.user_id, phase)
    _runs[(analysis.id, phase)] = run
    run.task = asyncio.create_task(_drive(run, source))

    logger.info("Execution %s demarree pour l'analyse %s", phase, analysis.id)
    return run


async def _drive(run: Run, source: Source) -> None:
    try:
        async for event in source():
            run.emit(event)
    except asyncio.CancelledError:
        logger.warning("Execution %s de l'analyse %s annulee", run.phase, run.analysis_id)
        run.emit(INTERRUPTED)
        raise
    except Exception as exc:
        logger.error(
            "Execution %s de l'analyse %s echouee: %s",
            run.phase, run.analysis_id, exc, exc_info=True,
        )
        run.emit({"event": "error", "code": "run_failed", "message": str(exc)})
    finally:
        run.close()


def _phase_source(analysis_id: uuid.UUID, user_id: uuid.UUID, phase, github_token: str) -> Source:
    async def source() -> AsyncIterator[dict]:
        async with async_session() as db:
            analysis = await analysis_repo.get_owned(analysis_id, user_id, db)

            if analysis is None:
                yield MISSING
                return

            async for event in phase(analysis, github_token, db):
                yield event

    return source


def start_scan(analysis: Analysis, github_token: str) -> Run:
    assert_free(analysis.user_id, SCAN)
    throttle.acquire(analysis.user_id)

    source = _phase_source(
        analysis.id, analysis.user_id, pipeline.run_scan_phase, github_token,
    )
    return start(analysis, SCAN, throttle.metered(analysis.user_id, source))


def start_deepen(analysis: Analysis, github_token: str) -> Run:
    assert_free(analysis.user_id, DEEPEN)

    return start(analysis, DEEPEN, _phase_source(
        analysis.id, analysis.user_id, pipeline.run_ai_phase, github_token,
    ))


def sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


async def stream(run: Run) -> AsyncIterator[str]:
    async for event in run.follow():
        yield sse(event)


def forget_finished() -> int:
    cutoff = utcnow() - KEEP_FINISHED_FOR
    stale = [
        key for key, run in _runs.items()
        if run.finished_at is not None and run.finished_at < cutoff
    ]

    for key in stale:
        del _runs[key]

    return len(stale)


async def shutdown() -> None:
    live = [run for run in _runs.values() if run.alive and run.task is not None]

    for run in live:
        run.task.cancel()

    if live:
        logger.info("Annulation de %d execution(s) en cours", len(live))
        await asyncio.gather(*(run.task for run in live), return_exceptions=True)

    _runs.clear()
