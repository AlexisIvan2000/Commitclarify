import pytest
from unittest.mock import patch, AsyncMock, MagicMock


#  Tests list_repos
MOCK_GITHUB_REPOS = [
    {
        "id": 1,
        "full_name": "testuser/my-repo",
        "description": "A test repo",
        "language": "Python",
        "visibility": "public",
        "html_url": "https://github.com/testuser/my-repo",
    }
]


@pytest.mark.asyncio
@patch("api.routers.repos.decrypt_github_token", return_value="fake-github-token")
async def test_list_repos(mock_decrypt, client, auth_headers):
    # httpx response.json() est synchrone → MagicMock, pas AsyncMock
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_GITHUB_REPOS

    mock_response_empty = MagicMock()
    mock_response_empty.status_code = 200
    mock_response_empty.json.return_value = []

    with patch("api.routers.repos.httpx.AsyncClient") as MockClient:
        mock_client_instance = AsyncMock()
        mock_client_instance.get.side_effect = [mock_response, mock_response_empty]
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = mock_client_instance

        response = await client.get("/repos/", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "testuser/my-repo"


@pytest.mark.asyncio
async def test_list_repos_no_auth(client):
    response = await client.get("/repos/")
    assert response.status_code in (401, 403)


# Tests scan_repo 
@pytest.mark.asyncio
@patch("api.routers.repos.decrypt_github_token", return_value="fake-github-token")
@patch("api.routers.repos.fetch_repo_files", new_callable=AsyncMock)
async def test_scan_repo(mock_fetch, mock_decrypt, client, auth_headers):
    mock_fetch.return_value = {
        "files": [{"path": "main.py", "content": "print('hello')"}],
        "stats": {"fetched": 1, "skipped": 0, "total": 1},
        "truncated": False,
    }
    response = await client.get("/repos/owner/repo/scan", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["stats"]["fetched"] == 1
