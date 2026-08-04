import logging
import uuid
from typing import NamedTuple

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.clock import utcnow
from models.db import ScanCache

logger = logging.getLogger(__name__)


class ScanKey(NamedTuple):
    repo_id: int
    commit_sha: str
    scan_version: int
    config_hash: str
    language: str


def _matching(key: ScanKey):
    return select(ScanCache).where(
        ScanCache.repo_id == key.repo_id,
        ScanCache.commit_sha == key.commit_sha,
        ScanCache.scan_version == key.scan_version,
        ScanCache.config_hash == key.config_hash,
        ScanCache.language == key.language,
    )


async def get(key: ScanKey, db: AsyncSession) -> dict | None:
    result = await db.execute(_matching(key))
    row = result.scalar_one_or_none()

    if row is None:
        return None

    logger.info("Scan servi depuis le cache: repo=%s sha=%s", key.repo_id, key.commit_sha[:12])
    return row.payload


async def put(key: ScanKey, payload: dict, db: AsyncSession) -> bool:
    entry = ScanCache(
        id=uuid.uuid4(),
        repo_id=key.repo_id,
        commit_sha=key.commit_sha,
        scan_version=key.scan_version,
        config_hash=key.config_hash,
        language=key.language,
        payload=payload,
        created_at=utcnow(),
    )

    try:
        async with db.begin_nested():
            db.add(entry)
    except IntegrityError:
        logger.info(
            "Scan deja mis en cache par une execution concurrente: repo=%s sha=%s",
            key.repo_id, key.commit_sha[:12],
        )
        return False

    return True


async def invalidate_repository(repo_id: int, db: AsyncSession) -> int:
    result = await db.execute(select(ScanCache).where(ScanCache.repo_id == repo_id))
    rows = result.scalars().all()

    for row in rows:
        await db.delete(row)

    return len(rows)
