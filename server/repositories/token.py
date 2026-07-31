import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.db_models import AuthCode, RefreshToken


def stage_refresh_token(
    user_id: uuid.UUID,
    token_hash: str,
    expires_at: datetime,
    db: AsyncSession,
) -> None:
    db.add(RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at))


async def get_live_refresh_token(token_hash: str, db: AsyncSession) -> RefreshToken | None:
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


def stage_auth_code(
    user_id: uuid.UUID,
    code_hash: str,
    access_token: str,
    refresh_token: str,
    expires_at: datetime,
    db: AsyncSession,
) -> None:
    db.add(AuthCode(
        user_id=user_id,
        code_hash=code_hash,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
    ))


async def get_auth_code(code_hash: str, db: AsyncSession) -> AuthCode | None:
    result = await db.execute(select(AuthCode).where(AuthCode.code_hash == code_hash))
    return result.scalar_one_or_none()
