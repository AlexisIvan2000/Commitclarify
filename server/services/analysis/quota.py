import logging
import uuid
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from core.clock import utcnow
from core.config import DAILY_ANALYSIS_LIMIT
from core.exceptions import QuotaExceededError
from repositories import analysis as analysis_repo

logger = logging.getLogger(__name__)

RESERVATION_TTL = timedelta(minutes=60)


async def count_today(github_id: int, db: AsyncSession) -> int:
    return await analysis_repo.count_runs_today(github_id, db)


async def get_quota(github_id: int, db: AsyncSession) -> dict:
    used = await count_today(github_id, db)

    return {
        "used": used,
        "limit": DAILY_ANALYSIS_LIMIT,
        "remaining": max(0, DAILY_ANALYSIS_LIMIT - used),
    }


async def reserve(github_id: int, analysis_id: uuid.UUID, db: AsyncSession) -> None:
    if await analysis_repo.has_live_reservation(analysis_id, db):
        logger.info("Reservation deja vivante pour l'analyse %s", analysis_id)
        return

    used = await count_today(github_id, db)

    if used >= DAILY_ANALYSIS_LIMIT:
        logger.info(
            "Quota atteint pour github_id=%s (%d/%d)",
            github_id, used, DAILY_ANALYSIS_LIMIT,
        )
        raise QuotaExceededError(
            f"Daily limit reached: {DAILY_ANALYSIS_LIMIT} AI analyses per day. Try again tomorrow.",
            params={"limit": DAILY_ANALYSIS_LIMIT},
        )

    analysis_repo.stage_reservation(
        github_id, analysis_id, utcnow() + RESERVATION_TTL, db,
    )
    await db.commit()

    logger.info(
        "Quota reserve pour github_id=%s analyse=%s (%d/%d avant reservation)",
        github_id, analysis_id, used, DAILY_ANALYSIS_LIMIT,
    )


async def commit(analysis_id: uuid.UUID, db: AsyncSession) -> None:
    if await analysis_repo.commit_reservation(analysis_id, db):
        logger.info("Quota decompte pour l'analyse %s", analysis_id)
        return

    logger.warning(
        "Aucune reservation vivante a decompter pour l'analyse %s "
        "(deja expiree et balayee ?)",
        analysis_id,
    )


async def release(analysis_id: uuid.UUID, db: AsyncSession, reason: str = "echec") -> None:
    if await analysis_repo.release_reservation(analysis_id, db):
        logger.info("Quota libere pour l'analyse %s (%s)", analysis_id, reason)
        return

    logger.info("Aucune reservation a liberer pour l'analyse %s (%s)", analysis_id, reason)


async def sweep_expired(db: AsyncSession) -> int:
    released = await analysis_repo.delete_expired_reservations(db)

    if released:
        logger.warning(
            "%d reservation(s) de quota expiree(s) recuperee(s) : "
            "des analyses IA se sont interrompues sans liberer leur reservation",
            released,
        )

    return released
