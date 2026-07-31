import logging

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import DAILY_ANALYSIS_LIMIT
from core.exceptions import QuotaExceededError
from repositories import analysis as analysis_repo

logger = logging.getLogger(__name__)


async def count_today(github_id: int, db: AsyncSession) -> int:
    return await analysis_repo.count_runs_today(github_id, db)


async def get_quota(github_id: int, db: AsyncSession) -> dict:
    used = await count_today(github_id, db)
    return {
        "used": used,
        "limit": DAILY_ANALYSIS_LIMIT,
        "remaining": max(0, DAILY_ANALYSIS_LIMIT - used),
    }


async def consume(github_id: int, db: AsyncSession) -> None:
    used = await count_today(github_id, db)

    if used >= DAILY_ANALYSIS_LIMIT:
        logger.info(
            "Rate limit atteint pour github_id=%s (%d/%d)",
            github_id, used, DAILY_ANALYSIS_LIMIT,
        )
        raise QuotaExceededError(
            f"Limite atteinte : {DAILY_ANALYSIS_LIMIT} analyses par jour. Reessayez demain."
        )

    analysis_repo.stage_run(github_id, db)
