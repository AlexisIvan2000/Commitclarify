import asyncio
import base64
import logging
from collections import Counter
from pathlib import Path
from typing import Optional

import httpx

from core.file_rules import (
    ALLOWED_EXTENSIONS,
    ALLOWED_FILENAMES,
    BATCH_SIZE,
    EXCLUDED_DIRS,
    MAX_FILE_LINES,
    MAX_FILE_SIZE,
    MAX_REPO_FILES,
)
from services.github.client import API_ROOT, get_json
from services.github.client import headers as github_headers

logger = logging.getLogger(__name__)


EXCLUDED_BY_PATH = "excluded_by_path"
EXCLUDED_BY_EXTENSION = "excluded_by_extension"
SKIPPED_TOO_LARGE = "skipped_too_large"

EMPTY_FILES = "empty_files"
SKIPPED_TOO_MANY_LINES = "skipped_too_many_lines"
SKIPPED_MINIFIED = "skipped_minified"

FETCH_HTTP_ERROR = "fetch_http_error"
FETCH_CONTENT_UNAVAILABLE = "fetch_content_unavailable"
FETCH_UNEXPECTED_PAYLOAD = "fetch_unexpected_payload"
FETCH_EXCEPTION = "fetch_exception"

DELIBERATE_SKIPS = frozenset({EMPTY_FILES, SKIPPED_TOO_MANY_LINES, SKIPPED_MINIFIED})


def _rejection_reason(path: str, size: int) -> Optional[str]:
    p = Path(path)

    if set(p.parts[:-1]) & EXCLUDED_DIRS:
        return EXCLUDED_BY_PATH

    if size > MAX_FILE_SIZE:
        return SKIPPED_TOO_LARGE

    if p.name in ALLOWED_FILENAMES:
        return None

    if p.suffix.lower() in ALLOWED_EXTENSIONS:
        return None

    return EXCLUDED_BY_EXTENSION


def _is_relevant(path: str, size: int) -> bool:
    return _rejection_reason(path, size) is None


async def get_repo_tree(
    owner: str,
    repo: str,
    github_token: str,
    branch: str = "HEAD",
) -> dict:
    data = await get_json(
        f"{API_ROOT}/repos/{owner}/{repo}/git/trees/{branch}",
        github_token,
        f"L'arbre de {owner}/{repo}@{branch}",
        params={"recursive": "1"},
    )

    blobs = [item for item in data.get("tree", []) if item["type"] == "blob"]

    eligible = []
    exclusions = Counter()

    for item in blobs:
        reason = _rejection_reason(item["path"], item.get("size", 0))
        if reason:
            exclusions[reason] += 1
            continue

        eligible.append({
            "path": item["path"],
            "sha":  item["sha"],
            "size": item.get("size", 0),
        })

    capped = len(eligible) > MAX_REPO_FILES

    logger.info(
        "Arbre repo %s/%s: %d eligibles sur %d versionnes (truncated=%s, exclusions=%s)",
        owner, repo, len(eligible), len(blobs), data.get("truncated", False), dict(exclusions),
    )

    return {
        "files": eligible[:MAX_REPO_FILES],
        "truncated": data.get("truncated", False),
        "tracked_paths": [item["path"] for item in blobs],
        "exclusions": dict(exclusions),
        "capped_at_limit": capped,
    }


def _empty_payload_reason(payload: dict) -> str:
    encoding = payload.get("encoding")

    if encoding == "none":
        return FETCH_CONTENT_UNAVAILABLE

    if encoding == "base64" and payload.get("size") == 0:
        return EMPTY_FILES

    return FETCH_UNEXPECTED_PAYLOAD


async def _fetch_file_content(
    client: httpx.AsyncClient,
    owner: str,
    repo: str,
    file: dict,
    headers: dict,
) -> tuple[Optional[dict], Optional[str]]:
    url = f"{API_ROOT}/repos/{owner}/{repo}/contents/{file['path']}"

    try:
        response = await client.get(url, headers=headers, timeout=15)

        if response.status_code != 200:
            logger.warning(
                "Contenu non recupere (%d) pour %s", response.status_code, file["path"],
            )
            return None, FETCH_HTTP_ERROR

        payload = response.json()
        encoded = payload.get("content", "")
        if not encoded:
            return None, _empty_payload_reason(payload)

        content = base64.b64decode(encoded.replace("\n", "")).decode("utf-8", errors="replace")

        # Ignorer les fichiers minifiés ou générés (trop de caractères sur peu de lignes)
        lines = content.split("\n")
        if len(lines) > MAX_FILE_LINES:
            return None, SKIPPED_TOO_MANY_LINES
        if len(lines) <= 3 and len(content) > 5000:
            return None, SKIPPED_MINIFIED

        return {
            "path":     file["path"],
            "sha":      file["sha"],
            "size":     file["size"],
            "content":  content,
            "language": Path(file["path"]).suffix.lstrip(".") or "text",
        }, None

    except Exception as exc:
        logger.warning("Echec de recuperation de %s: %s", file["path"], exc)
        return None, FETCH_EXCEPTION


async def fetch_repo_files(
    owner: str,
    repo: str,
    github_token: str,
    branch: str = "HEAD",
) -> dict:
   

    repo_sha = await get_repo_latest_sha(owner, repo, github_token, branch)

    tree = await get_repo_tree(owner, repo, github_token, branch)
    eligible = tree["files"]

    if not eligible:
        return _repo_data(repo_sha, [], tree, Counter())

    headers = github_headers(github_token)

    results = []
    failures = Counter()

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        for i in range(0, len(eligible), BATCH_SIZE):
            batch = eligible[i:i + BATCH_SIZE]
            tasks = [
                _fetch_file_content(client, owner, repo, f, headers)
                for f in batch
            ]
            for entry, reason in await asyncio.gather(*tasks):
                if entry is None:
                    failures[reason] += 1
                else:
                    results.append(entry)

    logger.info(
        "Fetch %s/%s termine: %d/%d fichiers recuperes (echecs=%s)",
        owner, repo, len(results), len(eligible), dict(failures),
    )

    return _repo_data(repo_sha, results, tree, failures)


def _repo_data(repo_sha: str, files: list[dict], tree: dict, outcomes: Counter) -> dict:
    eligible_count = len(tree["files"])
    readme = next(
        (f for f in files if Path(f["path"]).name.lower() == "readme.md"),
        None,
    )

    excluded = Counter(tree["exclusions"])
    failures = Counter()

    for reason, count in outcomes.items():
        target = excluded if reason in DELIBERATE_SKIPS else failures
        target[reason] += count

    return {
        "sha":           repo_sha,
        "files":         files,
        "readme":        readme,
        "truncated":     tree["truncated"],
        "tracked_paths": tree["tracked_paths"],
        "stats":         {
            "total_detected":  eligible_count,
            "fetched":         len(files),
            "skipped":         eligible_count - len(files),
            "tracked":         len(tree["tracked_paths"]),
            "excluded":        dict(excluded),
            "fetch_failures":  dict(failures),
            "capped_at_limit": tree["capped_at_limit"],
        },
    }


async def get_repo_latest_sha(
    owner: str,
    repo: str,
    github_token: str,
    branch: str = "HEAD",
) -> str:
    commit = await get_json(
        f"{API_ROOT}/repos/{owner}/{repo}/commits/{branch}",
        github_token,
        f"Le dernier commit de {owner}/{repo}@{branch}",
        timeout=15,
    )

    return commit["sha"]
