import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

from services.authentication.token import create_access_token, verify_access_token


# Tests JWT
def test_create_and_verify_token():
    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    payload = verify_access_token(token)
    assert payload["sub"] == str(user_id)


def test_verify_invalid_token():
    with pytest.raises(ValueError, match="invalide"):
        verify_access_token("invalid.token.here")


def test_verify_expired_token():
    from jose import jwt
    from core.config import JWT_KEY, JWT_ALGORITHM

    expired_payload = {
        "sub": str(uuid.uuid4()),
        "exp": datetime.utcnow() - timedelta(hours=1),
    }
    token = jwt.encode(expired_payload, JWT_KEY, algorithm=JWT_ALGORITHM)
    with pytest.raises(ValueError):
        verify_access_token(token)


#  Tests endpoints auth 
@pytest.mark.asyncio
async def test_get_me(client, auth_headers):
    response = await client.get("/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["login"] == "testuser"
    assert data["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_get_me_no_auth(client):
    response = await client.get("/auth/me")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_me_bad_token(client):
    response = await client.get("/auth/me", headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401
