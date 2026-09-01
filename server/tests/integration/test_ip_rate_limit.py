import pytest

from core.rate_limit import limiter


@pytest.fixture(autouse=True)
def fresh_counters():
    limiter._storage.reset()
    yield
    limiter._storage.reset()


@pytest.mark.asyncio
async def test_the_login_route_is_capped_per_address(client):
    statuses = [
        (await client.get("/auth/github/login", follow_redirects=False)).status_code
        for _ in range(12)
    ]

    assert statuses.count(307) == 10
    assert statuses[-1] == 429


@pytest.mark.asyncio
async def test_the_repo_listing_is_capped_per_address(client, auth_headers):
    statuses = [
        (await client.get("/repos/", headers=auth_headers)).status_code
        for _ in range(32)
    ]

    assert statuses[-1] == 429


@pytest.mark.asyncio
async def test_an_undecorated_route_is_not_capped_by_address(client, auth_headers):
    statuses = [
        (await client.get("/analyze/history", headers=auth_headers)).status_code
        for _ in range(70)
    ]

    assert set(statuses) == {200}
