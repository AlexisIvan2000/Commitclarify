import logging
import uuid

from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.clock import in_days, in_minutes, in_seconds, utcnow
from core.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_ALGORITHM,
    JWT_KEY,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from core.exceptions import AuthError
from core.security import AUTH_CODE_TTL_SECONDS, generate_token, hash_token
from models.db_models import AuthCode, RefreshToken

logger = logging.getLogger(__name__)


def create_access_token(user_id: uuid.UUID) -> str:
    return jwt.encode(
        {"sub": str(user_id), "exp": in_minutes(ACCESS_TOKEN_EXPIRE_MINUTES)},
        JWT_KEY,
        algorithm=JWT_ALGORITHM,
    )


def verify_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise ValueError("Token invalide ou expiré")


async def create_refresh_token(user_id: uuid.UUID, db: AsyncSession) -> str:
    raw_token = generate_token()

    db.add(RefreshToken(
        user_id=user_id,
        token_hash=hash_token(raw_token),
        expires_at=in_days(REFRESH_TOKEN_EXPIRE_DAYS),
    ))
    await db.commit()
    return raw_token


async def get_active_refresh_token(raw_token: str, db: AsyncSession) -> RefreshToken | None:
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_token(raw_token),
            RefreshToken.revoked_at.is_(None),
        )
    )
    stored = result.scalar_one_or_none()
    if not stored or stored.expires_at < utcnow():
        return None
    return stored


async def revoke_refresh_token(raw_token: str, db: AsyncSession) -> bool:
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_token(raw_token),
            RefreshToken.revoked_at.is_(None),
        )
    )
    token = result.scalar_one_or_none()
    if not token:
        return False

    token.revoked_at = utcnow()
    await db.commit()
    return True


async def create_auth_code(
    user_id: uuid.UUID,
    access_token: str,
    refresh_token: str,
    db: AsyncSession,
) -> str:
    raw_code = generate_token()

    db.add(AuthCode(
        user_id=user_id,
        code_hash=hash_token(raw_code),
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=in_seconds(AUTH_CODE_TTL_SECONDS),
    ))
    await db.commit()
    return raw_code


async def consume_auth_code(raw_code: str, db: AsyncSession) -> tuple[str, str]:
    result = await db.execute(
        select(AuthCode).where(AuthCode.code_hash == hash_token(raw_code))
    )
    code = result.scalar_one_or_none()

    if not code:
        raise AuthError("Code d'authentification inconnu")
    if code.used_at is not None:
        logger.warning("Code d'authentification rejoue: user=%s", code.user_id)
        raise AuthError("Code d'authentification deja utilise")
    if code.expires_at < utcnow():
        raise AuthError("Code d'authentification expire")

    code.used_at = utcnow()
    await db.commit()

    return code.access_token, code.refresh_token
