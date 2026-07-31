import uuid

import pytest
from sqlalchemy import select

from core.clock import utcnow
from core.language import DEFAULT_LANGUAGE
from models.db import Analysis


@pytest.mark.asyncio
async def test_start_analysis_stores_the_requested_language(client, auth_headers, db):
    response = await client.post("/analyze/owner/repo?language=en", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["language"] == "en"

    stored = await db.execute(select(Analysis).where(Analysis.repo_name == "owner/repo"))
    assert stored.scalar_one().language == "en"


@pytest.mark.asyncio
async def test_start_analysis_falls_back_on_unsupported_language(client, auth_headers):
    response = await client.post("/analyze/owner/repo?language=klingon", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["language"] == DEFAULT_LANGUAGE


@pytest.mark.asyncio
async def test_conflict_carries_a_stable_code(client, auth_headers, db, test_user):
    analysis = Analysis(
        id=uuid.uuid4(),
        user_id=test_user.id,
        repo_name="owner/repo",
        status="completed",
        created_at=utcnow(),
    )
    db.add(analysis)
    await db.commit()

    response = await client.get(f"/analyze/{analysis.id}/stream", headers=auth_headers)

    assert response.status_code == 409
    assert response.json()["code"] == "analysis_finished"
