import asyncio
import logging

from core.database import async_session
from services.analysis import quota

logger = logging.getLogger(__name__)

SWEEP_INTERVAL_SECONDS = 300


async def sweep_once() -> int:
    async with async_session() as db:
        released = await quota.sweep_expired(db)
        await db.commit()

    return released


async def sweep_reservations_forever(interval: float = SWEEP_INTERVAL_SECONDS) -> None:
    while True:
        try:
            await sweep_once()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("Balayage des reservations echoue: %s", exc, exc_info=True)

        await asyncio.sleep(interval)


def start(interval: float = SWEEP_INTERVAL_SECONDS) -> asyncio.Task:
    logger.info("Balayage des reservations de quota toutes les %ss", interval)
    return asyncio.create_task(sweep_reservations_forever(interval))


async def stop(task: asyncio.Task) -> None:
    task.cancel()

    try:
        await task
    except asyncio.CancelledError:
        pass
