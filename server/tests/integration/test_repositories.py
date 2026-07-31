import uuid

import pytest
from sqlalchemy import func, select

from core.clock import in_days, utcnow
from models.db_models import Analysis, AnalysisResult, AuthCode, RefreshToken, User
from repositories import analysis as analysis_repo, token as token_repo, user as user_repo


async def _count(model, db) -> int:
    result = await db.execute(select(func.count()).select_from(model))
    return result.scalar() or 0


@pytest.mark.asyncio
async def test_get_owned_refuses_another_users_analysis(db, test_user):
    intruder = User(
        id=uuid.uuid4(),
        github_id=999999,
        login="intrus",
        username="Intrus",
        access_token="chiffre",
    )
    db.add(intruder)

    analysis = analysis_repo.stage(test_user.id, "owner/repo", "fr", db)
    await db.commit()

    assert await analysis_repo.get_owned(analysis.id, test_user.id, db) is not None
    assert await analysis_repo.get_owned(analysis.id, intruder.id, db) is None


@pytest.mark.asyncio
async def test_replace_results_is_idempotent(db, test_user):
    analysis = analysis_repo.stage(test_user.id, "owner/repo", "fr", db)
    await db.commit()

    payload = {"secrets_detection": {"status": "clean", "issues": [], "recommendations": []}}

    await analysis_repo.replace_results(analysis.id, payload, db)
    await db.commit()
    await analysis_repo.replace_results(analysis.id, payload, db)
    await db.commit()

    assert await _count(AnalysisResult, db) == 1


@pytest.mark.asyncio
async def test_purge_account_removes_every_trace(db, test_user):
    analysis = analysis_repo.stage(test_user.id, "owner/repo", "fr", db)
    await db.commit()

    await analysis_repo.replace_results(
        analysis.id,
        {"quality_check": {"status": "clean", "issues": [], "recommendations": []}},
        db,
    )
    token_repo.stage_refresh_token(test_user.id, "hash-refresh", in_days(30), db)
    token_repo.stage_auth_code(test_user.id, "hash-code", "a", "r", in_days(1), db)
    await db.commit()

    assert await _count(AnalysisResult, db) == 1
    assert await _count(RefreshToken, db) == 1
    assert await _count(AuthCode, db) == 1

    await user_repo.purge_account(test_user, db)
    await db.commit()

    assert await _count(AnalysisResult, db) == 0
    assert await _count(RefreshToken, db) == 0
    assert await _count(AuthCode, db) == 0
    assert await _count(Analysis, db) == 0
    assert await _count(User, db) == 0


@pytest.mark.asyncio
async def test_remove_all_for_user_reports_the_count(db, test_user):
    analysis_repo.stage(test_user.id, "owner/a", "fr", db)
    analysis_repo.stage(test_user.id, "owner/b", "en", db)
    await db.commit()

    removed = await analysis_repo.remove_all_for_user(test_user.id, db)
    await db.commit()

    assert removed == 2
    assert await _count(Analysis, db) == 0


@pytest.mark.asyncio
async def test_quota_counter_only_sees_today(db, test_user):
    analysis_repo.stage_run(test_user.github_id, db)
    await db.commit()

    assert await analysis_repo.count_runs_today(test_user.github_id, db) == 1
    assert await analysis_repo.count_runs_today(test_user.github_id + 1, db) == 0


@pytest.mark.asyncio
async def test_live_refresh_token_ignores_revoked(db, test_user):
    token_repo.stage_refresh_token(test_user.id, "hash-vivant", in_days(30), db)
    await db.commit()

    stored = await token_repo.get_live_refresh_token("hash-vivant", db)
    assert stored is not None

    stored.revoked_at = utcnow()
    await db.commit()

    assert await token_repo.get_live_refresh_token("hash-vivant", db) is None
