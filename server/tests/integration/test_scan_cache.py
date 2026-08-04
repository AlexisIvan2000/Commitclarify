import pytest
from sqlalchemy import func, select

from models.db import ScanCache
from repositories import scan_cache
from repositories.scan_cache import ScanKey

KEY = ScanKey(repo_id=424242, commit_sha="a" * 40, scan_version=5, config_hash="h" * 16, language="fr")

PAYLOAD = {"scan_version": 5, "axes": {}, "summary": {"findings": 0}}


async def _count(db) -> int:
    result = await db.execute(select(func.count()).select_from(ScanCache))
    return result.scalar_one()


@pytest.mark.asyncio
async def test_a_miss_returns_none(db):
    assert await scan_cache.get(KEY, db) is None


@pytest.mark.asyncio
async def test_what_is_stored_is_what_is_read_back(db):
    await scan_cache.put(KEY, PAYLOAD, db)
    await db.commit()

    assert await scan_cache.get(KEY, db) == PAYLOAD


@pytest.mark.asyncio
async def test_each_part_of_the_key_discriminates(db):
    await scan_cache.put(KEY, PAYLOAD, db)
    await db.commit()

    others = [
        KEY._replace(repo_id=1),
        KEY._replace(commit_sha="b" * 40),
        KEY._replace(scan_version=KEY.scan_version + 1),
        KEY._replace(config_hash="z" * 16),
        KEY._replace(language="en"),
    ]

    for other in others:
        assert await scan_cache.get(other, db) is None, other


@pytest.mark.asyncio
async def test_a_concurrent_write_does_not_raise_and_does_not_duplicate(db):
    assert await scan_cache.put(KEY, PAYLOAD, db) is True
    await db.commit()

    assert await scan_cache.put(KEY, {"scan_version": 5, "axes": {}}, db) is False
    await db.commit()

    assert await _count(db) == 1
    assert await scan_cache.get(KEY, db) == PAYLOAD


@pytest.mark.asyncio
async def test_the_session_survives_a_rejected_write(db):
    await scan_cache.put(KEY, PAYLOAD, db)
    await db.commit()

    await scan_cache.put(KEY, PAYLOAD, db)
    await scan_cache.put(KEY._replace(language="en"), PAYLOAD, db)
    await db.commit()

    assert await _count(db) == 2


@pytest.mark.asyncio
async def test_invalidating_a_repository_clears_every_language(db):
    await scan_cache.put(KEY, PAYLOAD, db)
    await scan_cache.put(KEY._replace(language="en"), PAYLOAD, db)
    await db.commit()

    removed = await scan_cache.invalidate_repository(KEY.repo_id, db)
    await db.commit()

    assert removed == 2
    assert await _count(db) == 0
