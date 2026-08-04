import shutil
import subprocess

import pytest

from services.scan.gitignore import _build_specs, _is_ignored

GITIGNORE = """build/
!build/keep.md
.env*
!.env.example
*.log
!important.log
node_modules/
/root.txt
docs/**/tmp/
secrets/
!secrets/README.md
"""

PATHS = [
    "build/keep.md",
    "build/out.js",
    ".env",
    ".env.example",
    ".env.production",
    "a/b/c.log",
    "important.log",
    "nested/important.log",
    "node_modules/left-pad/index.js",
    "root.txt",
    "sub/root.txt",
    "docs/guide/tmp/note.md",
    "docs/guide/note.md",
    "secrets/README.md",
    "secrets/key.pem",
    "src/app.py",
]

needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git absent")


@pytest.fixture(scope="module")
def repository(tmp_path_factory):
    path = tmp_path_factory.mktemp("gitignore_reference")
    subprocess.run(["git", "init", "-q", "."], cwd=path, check=True, capture_output=True)
    (path / ".gitignore").write_text(GITIGNORE, encoding="utf-8")

    for entry in PATHS:
        target = path / entry
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x", encoding="utf-8")

    return path


def git_ignores(repository, path: str) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", "-q", path],
        cwd=repository,
        capture_output=True,
    )
    return result.returncode == 0


@needs_git
@pytest.mark.parametrize("path", PATHS)
def test_matcher_agrees_with_git(repository, path):
    specs = _build_specs([{"path": ".gitignore", "content": GITIGNORE}])

    assert _is_ignored(specs, path) == git_ignores(repository, path)
