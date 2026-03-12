import asyncio
import base64
import json
import logging
import httpx
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Charger la config depuis extensions.json
_config_path = Path(__file__).resolve().parent.parent.parent / "models" / "extensions.json"
with open(_config_path) as _f:
    _config = json.load(_f)

# Aplatir toutes les extensions en un seul set
ALLOWED_EXTENSIONS = {
    ext
    for group in _config["ALLOWED_EXTENSIONS"].values()
    for ext in group
}

ALLOWED_FILENAMES = set(_config["ALLOWED_FILENAMES"])
EXCLUDED_DIRS = set(_config["EXCLUDED_DIRS"])

MAX_FILE_SIZE = _config["LIMITS"]["MAX_FILE_SIZE"]
BATCH_SIZE = _config["LIMITS"]["BATCH_SIZE"]
MAX_FILE_LINES = _config["LIMITS"]["MAX_FILE_LINES"]
MAX_REPO_FILES = _config["LIMITS"]["MAX_REPO_FILES"]


def _is_relevant(path: str, size: int) -> bool:
    """Vérifie si un fichier doit être inclus ou ignoré."""
    p = Path(path)

    # Exclure les dossiers blacklistés
    parts = set(p.parts[:-1])
    if parts & EXCLUDED_DIRS:
        return False

    # Cas spéciaux par nom exact
    if p.name in ALLOWED_FILENAMES:
        return True

    # Vérifier l'extension
    if p.suffix.lower() not in ALLOWED_EXTENSIONS:
        return False

    # Taille max
    if size > MAX_FILE_SIZE:
        return False

    return True


async def get_repo_tree(
    owner: str,
    repo: str,
    github_token: str,
    branch: str = "HEAD",
) -> tuple[list[dict], bool]:
    """
    Récupère l'arbre complet du repo en un seul appel.
    Retourne la liste des fichiers filtrés avec path + sha + size.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, headers=headers, params={"recursive": "1"})

    if response.status_code == 404:
        logger.warning("Repo introuvable: %s/%s", owner, repo)
        raise ValueError(f"Repository {owner}/{repo} introuvable ou inaccessible.")
    if response.status_code == 409:
        logger.warning("Repo vide: %s/%s", owner, repo)
        raise ValueError("Le repository est vide.")
    if response.status_code != 200:
        logger.error("Erreur GitHub tree API: status=%d pour %s/%s", response.status_code, owner, repo)
        raise ValueError(f"Erreur GitHub tree: {response.status_code}")

    data = response.json()
    truncated = data.get("truncated", False)

    files = [
        {
            "path": item["path"],
            "sha":  item["sha"],
            "size": item.get("size", 0),
        }
        for item in data.get("tree", [])
        if item["type"] == "blob"
        and _is_relevant(item["path"], item.get("size", 0))
    ]

    # Limiter le nombre de fichiers
    files = files[:MAX_REPO_FILES]

    logger.info("Arbre repo %s/%s: %d fichiers filtres (truncated=%s)", owner, repo, len(files), truncated)
    return files, truncated


async def _fetch_file_content(
    client: httpx.AsyncClient,
    owner: str,
    repo: str,
    file: dict,
    headers: dict,
) -> Optional[dict]:
    """Télécharge le contenu d'un fichier et le décode depuis base64."""
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
    """
    Point d'entrée principal.
    Retourne : { sha, files: [...], stats: {...} }
    """

    repo_sha = await get_repo_latest_sha(owner, repo, github_token)

    filtered_files, truncated = await get_repo_tree(owner, repo, github_token, branch)

    if not filtered_files:
        return {"sha": repo_sha, "files": [], "readme": None, "truncated": truncated, "stats": {"total_detected": 0, "fetched": 0, "skipped": 0}}

    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
    }

    results = []
    async with httpx.AsyncClient(timeout=30) as client:
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
        "sha":       repo_sha,
        "files":     results,
        "readme":    readme,
        "truncated": truncated,
        "stats":     {
            "total_detected": len(filtered_files),
            "fetched":        len(results),
            "skipped":        len(filtered_files) - len(results),
        },
    }


async def get_repo_latest_sha(
    owner: str,
    repo: str,
    github_token: str,
) -> str:
    """Récupère le SHA du dernier commit — utilisé pour le cache."""
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/commits/HEAD",
            headers={
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github+json",
            }
        )
    if response.status_code != 200:
        raise ValueError("Impossible de récupérer le SHA du repo.")
    return response.json()["sha"]
