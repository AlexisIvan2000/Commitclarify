import uuid

from sqlalchemy import delete as sql_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import Analysis, AnalysisResult, AuthCode, RefreshToken, User


async def get_by_id(user_id: uuid.UUID, db: AsyncSession) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_by_github_id(github_id: int, db: AsyncSession) -> User | None:
    result = await db.execute(select(User).where(User.github_id == github_id))
    return result.scalars().first()


def stage(user: User, db: AsyncSession) -> User:
    db.add(user)
    return user


async def purge_account(user: User, db: AsyncSession) -> None:
    analysis_ids = select(Analysis.id).where(Analysis.user_id == user.id)

    await db.execute(
        sql_delete(AnalysisResult).where(AnalysisResult.analysis_id.in_(analysis_ids))
    )
    await db.execute(sql_delete(RefreshToken).where(RefreshToken.user_id == user.id))
    await db.execute(sql_delete(AuthCode).where(AuthCode.user_id == user.id))
    await db.execute(sql_delete(Analysis).where(Analysis.user_id == user.id))
    await db.delete(user)
