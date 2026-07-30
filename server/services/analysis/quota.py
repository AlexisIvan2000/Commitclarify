import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.clock import start_of_day
from core.config import DAILY_ANALYSIS_LIMIT
from core.exceptions import QuotaExceededError
from models.db_models import AnalysisLog

logger = logging.getLogger(__name__)


async def count_today(github_id: int, db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count()).select_from(AnalysisLog).where(
            AnalysisLog.github_id == github_id,
            AnalysisLog.created_at >= start_of_day(),
        )
    )
    return result.scalar() or 0


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
        logger.info("Rate limit atteint pour github_id=%s (%d/%d)", github_id, used, DAILY_ANALYSIS_LIMIT)
        raise QuotaExceededError(
            f"Limite atteinte : {DAILY_ANALYSIS_LIMIT} analyses par jour. Reessayez demain."
        )

    db.add(AnalysisLog(github_id=github_id))
