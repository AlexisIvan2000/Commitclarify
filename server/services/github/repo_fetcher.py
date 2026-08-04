import asyncio
import base64
import logging
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


def _is_relevant(path: str, size: int) -> bool:
    p = Path(path)

    if set(p.parts[:-1]) & EXCLUDED_DIRS:
        return False

    if size > MAX_FILE_SIZE:
        return False

    if p.name in ALLOWED_FILENAMES:
        return True

    return p.suffix.lower() in ALLOWED_EXTENSIONS


async def get_repo_tree(
    owner: str,
    repo: str,
    github_token: str,
    branch: str = "HEAD",
) -> tuple[list[dict], bool, list[str]]:
    data = await get_json(
        f"{API_ROOT}/repos/{owner}/{repo}/git/trees/{branch}",
        github_token,
        f"L'arbre de {owner}/{repo}@{branch}",
        params={"recursive": "1"},
    )

    truncated = data.get("truncated", False)

    blobs = [item for item in data.get("tree", []) if item["type"] == "blob"]
    tracked_paths = [item["path"] for item in blobs]

    files = [
        {
            "path": item["path"],
            "sha":  item["sha"],
            "size": item.get("size", 0),
        }
        for item in blobs
        if _is_relevant(item["path"], item.get("size", 0))
    ]

    # Limiter le nombre de fichiers
    files = files[:MAX_REPO_FILES]

    logger.info(
        "Arbre repo %s/%s: %d fichiers filtres sur %d versionnes (truncated=%s)",
        owner, repo, len(files), len(tracked_paths), truncated,
    )
    return files, truncated, tracked_paths


async def _fetch_file_content(
    client: httpx.AsyncClient,
    owner: str,
    repo: str,
    file: dict,
    headers: dict,
) -> Optional[dict]:
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file['path']}"

    try:
        response = await client.get(url, headers=headers, timeout=15)

        if response.status_code != 200:
            return None

        data = response.json()
        encoded = data.get("content", "")
        if not encoded:
            return None

        content = base64.b64decode(encoded.replace("\n", "")).decode("utf-8", errors="replace")

        # Ignorer les fichiers minifiés ou générés (trop de caractères sur peu de lignes)
        lines = content.split("\n")
        if len(lines) > MAX_FILE_LINES:
            return None
        if len(lines) <= 3 and len(content) > 5000:
            return None

        return {
            "path":     file["path"],
            "sha":      file["sha"],
            "size":     file["size"],
            "content":  content,
            "language": Path(file["path"]).suffix.lstrip(".") or "text",
        }

    except Exception:
        return None


async def fetch_repo_files(
    owner: str,
    repo: str,
    github_token: str,
    branch: str = "HEAD",
) -> dict:
   

    repo_sha = await get_repo_latest_sha(owner, repo, github_token, branch)

    filtered_files, truncated, tracked_paths = await get_repo_tree(owner, repo, github_token, branch)

    if not filtered_files:
        return {
            "sha": repo_sha,
            "files": [],
            "readme": None,
            "truncated": truncated,
            "tracked_paths": tracked_paths,
            "stats": {"total_detected": 0, "fetched": 0, "skipped": 0, "tracked": len(tracked_paths)},
        }

    headers = github_headers(github_token)

    results = []
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        for i in range(0, len(filtered_files), BATCH_SIZE):
            batch = filtered_files[i:i + BATCH_SIZE]
            tasks = [
                _fetch_file_content(client, owner, repo, f, headers)
                for f in batch
            ]
            batch_results = await asyncio.gather(*tasks)
            results.extend([r for r in batch_results if r is not None])

    readme = next(
        (f for f in results if Path(f["path"]).name.lower() == "readme.md"),
        None
    )

    logger.info("Fetch %s/%s termine: %d/%d fichiers recuperes", owner, repo, len(results), len(filtered_files))
    return {
        "sha":           repo_sha,
        "files":         results,
        "readme":        readme,
        "truncated":     truncated,
        "tracked_paths": tracked_paths,
        "stats":         {
            "total_detected": len(filtered_files),
            "fetched":        len(results),
            "skipped":        len(filtered_files) - len(results),
            "tracked":        len(tracked_paths),
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
