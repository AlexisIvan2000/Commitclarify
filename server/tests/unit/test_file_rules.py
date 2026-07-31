import pytest

from core.file_rules import MAX_FILE_SIZE
from services.ai.security_agent import _scan_committed_secret_files
from services.github.repo_fetcher import _is_relevant


@pytest.mark.parametrize("path", [
    ".env",
    ".env.local",
    ".env.production",
    "config/.env",
    "id_rsa",
    "id_ed25519",
    "certs/private.pem",
    "app.key",
    ".netrc",
    ".pgpass",
    "terraform.tfvars",
    "service-account.json",
])
def test_secret_bearing_files_are_fetched(path):
    assert _is_relevant(path, 1000), f"{path} doit etre recupere pour etre scanne"


@pytest.mark.parametrize("path", [
    "node_modules/pkg/index.js",
    "dist/bundle.js",
    ".venv/lib/site.py",
    "__pycache__/mod.pyc",
    "logo.png",
    "video.mp4",
])
def test_irrelevant_files_are_skipped(path):
    assert not _is_relevant(path, 1000)


def test_size_limit_applies_to_allowed_filenames():
    assert _is_relevant("package-lock.json", 1000)
    assert not _is_relevant("package-lock.json", MAX_FILE_SIZE + 1)


def test_size_limit_applies_to_extensions():
    assert not _is_relevant("src/main.py", MAX_FILE_SIZE + 1)


def test_committed_env_file_is_flagged_critical():
    issues = _scan_committed_secret_files([{"path": ".env", "content": "SECRET=abc"}])

    assert len(issues) == 1
    assert issues[0]["severity"] == "critical"
    assert issues[0]["source"] == "filename"
    assert issues[0]["file_path"] == ".env"


def test_private_key_is_flagged():
    issues = _scan_committed_secret_files([{"path": "deploy/id_rsa", "content": "..."}])
    assert len(issues) == 1
    assert "SSH" in issues[0]["title"]


def test_env_example_is_not_flagged():
    issues = _scan_committed_secret_files([
        {"path": ".env.example", "content": "SECRET=your_key_here"},
        {"path": "src/main.py", "content": "x = 1"},
        {"path": "key.pub", "content": "ssh-rsa AAAA"},
    ])
    assert issues == []
