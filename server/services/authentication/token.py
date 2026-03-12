import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta

from jose import jwt, JWTError

logger = logging.getLogger(__name__)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.db_models import RefreshToken
from core.config import JWT_KEY, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS


def create_access_token(user_id: uuid.UUID) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": str(user_id), "exp": expire},
        JWT_KEY,
        algorithm=JWT_ALGORITHM,
    )


async def create_refresh_token(user_id: uuid.UUID, db: AsyncSession) -> str:
    raw_token  = secrets.token_hex(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    db.add(RefreshToken(
        user_id    = user_id,
        token_hash = token_hash,
        expires_at = expires_at
    ))
    await db.commit()
    return raw_token


def verify_access_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            JWT_KEY,
            algorithms=[JWT_ALGORITHM],
        )
    except JWTError:
        raise ValueError("Token invalide ou expiré")


async def revoke_refresh_token(raw_token: str, db: AsyncSession) -> bool:
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at == None
        )
    )
    token = result.scalar_one_or_none()
    if not token:
        return False

    token.revoked_at = datetime.utcnow()
    await db.commit()
    return True