from unittest.mock import MagicMock, patch

import pytest

from services.github.client import GitHubError
from services.github.repo_fetcher import get_repo_latest_sha, get_repo_tree

TREE = {
    "truncated": False,
    "tree": [
        {"path": "app.py", "type": "blob", "sha": "a", "size": 10},
        {"path": "node_modules/left-pad/index.js", "type": "blob", "sha": "b", "size": 10},
        {"path": "assets/logo.png", "type": "blob", "sha": "c", "size": 10},
        {"path": "src", "type": "tree", "sha": "d"},
        {"path": "generated.py", "type": "blob", "sha": "e", "size": 999_999},
    ],
}


class _FakeClient:
    def __init__(self, payload: dict, status: int = 200, response_headers: dict | None = None):
        self.payload = payload
        self.status = status
        self.response_headers = response_headers or {}
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False

    async def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        response = MagicMock()
        response.status_code = self.status
        response.headers = self.response_headers
        response.json.return_value = self.payload
        return response


def _patched(payload: dict, status: int = 200, response_headers: dict | None = None):
    return patch(
        "services.github.client.httpx.AsyncClient",
        lambda *_, **__: _FakeClient(payload, status, response_headers),
    )


@pytest.mark.asyncio
async def test_redirections_are_followed():
    captured = {}

    def build(*_, **kwargs):
        captured.update(kwargs)
        return _FakeClient({"sha": "abc"})

    with patch("services.github.client.httpx.AsyncClient", build):
        await get_repo_latest_sha("owner", "repo", "token")

    assert captured["follow_redirects"] is True


@pytest.mark.asyncio
async def test_tracked_paths_keep_what_the_analysis_filter_discards():
    with _patched(TREE):
        tree = await get_repo_tree("owner", "repo", "token")

    assert [entry["path"] for entry in tree["files"]] == ["app.py"]
    assert tree["tracked_paths"] == [
        "app.py",
        "node_modules/left-pad/index.js",
        "assets/logo.png",
        "generated.py",
    ]
    assert tree["truncated"] is False


@pytest.mark.asyncio
async def test_every_discarded_file_is_counted_under_a_named_reason():
    with _patched(TREE):
        tree = await get_repo_tree("owner", "repo", "token")

    assert tree["exclusions"] == {
        "excluded_by_path": 1,
        "excluded_by_extension": 1,
        "skipped_too_large": 1,
    }
    assert sum(tree["exclusions"].values()) + len(tree["files"]) == len(tree["tracked_paths"])


@pytest.mark.asyncio
async def test_tracked_paths_exclude_directories():
    with _patched(TREE):
        tree = await get_repo_tree("owner", "repo", "token")

    assert "src" not in tree["tracked_paths"]


@pytest.mark.asyncio
async def test_truncated_flag_is_propagated():
    with _patched({"truncated": True, "tree": []}):
        tree = await get_repo_tree("owner", "repo", "token")

    assert tree["truncated"] is True
    assert tree["files"] == []
    assert tree["capped_at_limit"] is False


@pytest.mark.asyncio
async def test_missing_repository_raises():
    with _patched({}, status=404), pytest.raises(ValueError):
        await get_repo_tree("owner", "repo", "token")


FULL_TREE = {
    "truncated": False,
    "tree": [
        {"path": "app.py", "type": "blob", "sha": "a", "size": 10},
        {"path": "core/__init__.py", "type": "blob", "sha": "b", "size": 0},
        {"path": "huge.py", "type": "blob", "sha": "c", "size": 10},
        {"path": "gone.py", "type": "blob", "sha": "d", "size": 10},
        {"path": "assets/logo.png", "type": "blob", "sha": "e", "size": 10},
    ],
}

CONTENTS = {
    "app.py": (200, {"encoding": "base64", "size": 10, "content": "cHJpbnQoMSk="}),
    "core/__init__.py": (200, {"encoding": "base64", "size": 0, "content": ""}),
    "huge.py": (200, {"encoding": "none", "size": 2_000_000, "content": ""}),
    "gone.py": (404, {}),
}


class _FakeApi:
    def __init__(self):
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False

    async def get(self, url, **kwargs):
        self.calls.append(url)
        response = MagicMock()
        response.headers = {}

        if "/commits/" in url:
            response.status_code = 200
            response.json.return_value = {"sha": "deadbeef"}
        elif "/git/trees/" in url:
            response.status_code = 200
            response.json.return_value = FULL_TREE
        else:
            path = url.split("/contents/", 1)[1]
            status, payload = CONTENTS[path]
            response.status_code = status
            response.json.return_value = payload

        return response


@pytest.fixture
def fake_api():
    api = _FakeApi()
    with (
        patch("services.github.client.httpx.AsyncClient", lambda *_, **__: api),
        patch("services.github.repo_fetcher.httpx.AsyncClient", lambda *_, **__: api),
    ):
        yield api


@pytest.mark.asyncio
async def test_empty_files_are_not_counted_as_fetch_failures(fake_api):
    from services.github.repo_fetcher import fetch_repo_files

    data = await fetch_repo_files("owner", "repo", "token")
    stats = data["stats"]

    assert stats["excluded"]["empty_files"] == 1
    assert "empty_files" not in stats["fetch_failures"]


@pytest.mark.asyncio
async def test_real_errors_stay_in_fetch_failures(fake_api):
    from services.github.repo_fetcher import fetch_repo_files

    stats = (await fetch_repo_files("owner", "repo", "token"))["stats"]

    assert stats["fetch_failures"] == {
        "fetch_http_error": 1,
        "fetch_content_unavailable": 1,
    }


@pytest.mark.asyncio
async def test_every_tracked_file_is_accounted_for_exactly_once(fake_api):
    from services.github.repo_fetcher import fetch_repo_files

    data = await fetch_repo_files("owner", "repo", "token")
    stats = data["stats"]

    accounted = (
        stats["fetched"]
        + sum(stats["excluded"].values())
        + sum(stats["fetch_failures"].values())
    )

    assert accounted == stats["tracked"] == 5
    assert stats["fetched"] == 1
    assert [entry["path"] for entry in data["files"]] == ["app.py"]


@pytest.mark.asyncio
@pytest.mark.parametrize("status,expected", [
    (401, "invalide ou expire"),
    (403, "permissions insuffisantes"),
    (404, "hors du perimetre du token"),
    (409, "vide"),
    (500, "Erreur GitHub (500)"),
])
async def test_each_status_gets_its_own_message(status, expected):
    with _patched({}, status=status), pytest.raises(GitHubError) as error:
        await get_repo_latest_sha("owner", "repo", "token")

    assert expected in str(error.value)
    assert error.value.status == status
    assert "/repos/owner/repo/commits/HEAD" in error.value.url


@pytest.mark.asyncio
async def test_exhausted_quota_is_distinguished_from_a_permission_denial():
    quota = {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1780000000"}

    with _patched({}, status=403, response_headers=quota), pytest.raises(GitHubError) as error:
        await get_repo_latest_sha("owner", "repo", "token")

    assert "Quota d'appels GitHub epuise" in str(error.value)
    assert "UTC" in str(error.value)


@pytest.mark.asyncio
async def test_the_requested_branch_reaches_the_commit_endpoint():
    client = _FakeClient({"sha": "abc123"})

    with patch("services.github.client.httpx.AsyncClient", lambda *_, **__: client):
        sha = await get_repo_latest_sha("owner", "repo", "token", "develop")

    assert sha == "abc123"
    assert client.calls[0][0].endswith("/repos/owner/repo/commits/develop")


@pytest.mark.asyncio
async def test_requests_carry_a_user_agent_and_an_api_version():
    client = _FakeClient({"sha": "abc123"})

    with patch("services.github.client.httpx.AsyncClient", lambda *_, **__: client):
        await get_repo_latest_sha("owner", "repo", "token")

    sent = client.calls[0][1]["headers"]
    assert sent["User-Agent"] == "CommitClarify"
    assert sent["X-GitHub-Api-Version"] == "2022-11-28"
    assert sent["Authorization"] == "Bearer token"
