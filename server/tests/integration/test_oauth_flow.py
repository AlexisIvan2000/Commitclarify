import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from core.clock import utcnow
from core.exceptions import AuthError
from core.security import OAUTH_STATE_COOKIE, hash_token
from models.db_models import AuthCode
from services.authentication.token import consume_auth_code, create_auth_code

GITHUB_USER = {
    "id": 123456,
    "login": "testuser",
    "name": "Test User",
    "avatar_url": "https://example.com/a.png",
    "email": "test@example.com",
}


@pytest.mark.asyncio
async def test_login_sets_state_cookie_and_redirects_to_github(client):
    response = await client.get("/auth/github/login", follow_redirects=False)

    assert response.status_code == 307
    assert "github.com/login/oauth/authorize" in response.headers["location"]
    assert "state=" in response.headers["location"]
    assert OAUTH_STATE_COOKIE in response.cookies


@pytest.mark.asyncio
async def test_callback_without_state_is_rejected(client):
    response = await client.get(
        "/auth/callback", params={"code": "gh_code"}, follow_redirects=False
    )

    assert response.status_code == 307
    assert "error=state_invalide" in response.headers["location"]


@pytest.mark.asyncio
async def test_callback_with_mismatched_state_is_rejected(client):
    client.cookies.set(OAUTH_STATE_COOKIE, "le-bon-state")

    response = await client.get(
        "/auth/callback",
        params={"code": "gh_code", "state": "un-autre-state"},
        follow_redirects=False,
    )

    assert response.status_code == 307
    assert "error=state_invalide" in response.headers["location"]


@pytest.mark.asyncio
@patch("api.routers.auth.upsert_user", new_callable=AsyncMock)
@patch("api.routers.auth.github_get_user", new_callable=AsyncMock, return_value=GITHUB_USER)
@patch("api.routers.auth.github_exchange_code", new_callable=AsyncMock, return_value="gh_token")
async def test_callback_returns_code_not_tokens(
    mock_exchange, mock_get_user, mock_upsert, client, test_user
):
    mock_upsert.return_value = test_user
    client.cookies.set(OAUTH_STATE_COOKIE, "state-partage")

    response = await client.get(
        "/auth/callback",
        params={"code": "gh_code", "state": "state-partage"},
        follow_redirects=False,
    )

    location = response.headers["location"]
    assert response.status_code == 307
    assert "code=" in location
    assert "access_token=" not in location
    assert "refresh_token=" not in location


@pytest.mark.asyncio
async def test_exchange_returns_tokens_once(client, db, test_user):
    code = await create_auth_code(test_user.id, "jwt-access", "raw-refresh", db)

    first = await client.post("/auth/exchange", json={"code": code})
    assert first.status_code == 200
    assert first.json()["access_token"] == "jwt-access"
    assert first.json()["refresh_token"] == "raw-refresh"

    replay = await client.post("/auth/exchange", json={"code": code})
    assert replay.status_code == 401


@pytest.mark.asyncio
async def test_exchange_rejects_unknown_code(client):
    response = await client.post("/auth/exchange", json={"code": "code-inexistant"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_auth_code_is_stored_hashed(db, test_user):
    code = await create_auth_code(test_user.id, "a", "r", db)

    result = await db.execute(select(AuthCode).where(AuthCode.user_id == test_user.id))
    stored = result.scalar_one()

    assert stored.code_hash != code
    assert stored.code_hash == hash_token(code)


@pytest.mark.asyncio
async def test_expired_auth_code_is_refused(db, test_user):
    code = await create_auth_code(test_user.id, "a", "r", db)

    result = await db.execute(select(AuthCode).where(AuthCode.user_id == test_user.id))
    stored = result.scalar_one()
    stored.expires_at = utcnow().replace(year=2000)
    await db.commit()

    with pytest.raises(AuthError):
        await consume_auth_code(code, db)


@pytest.mark.asyncio
async def test_exchange_endpoint_is_public(client):
    response = await client.post("/auth/exchange", json={"code": str(uuid.uuid4())})
    assert response.status_code == 401
    assert "Authorization" not in response.json().get("detail", "")
