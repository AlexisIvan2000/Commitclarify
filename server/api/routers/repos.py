import logging

import httpx
from fastapi import APIRouter, Depends, Request

from api.dependencies import get_current_user
from core.exceptions import AuthError, ExternalServiceError, ValidationError
from core.rate_limit import limiter
from models.db_models import User
from services.authentication.auth import decrypt_github_token
from services.github.repo_fetcher import fetch_repo_files

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/repos", tags=["repos"])

MAX_PAGES = 10
PER_PAGE = 100
GITHUB_TIMEOUT = 30


@router.get("/")
@limiter.limit("30/minute")
async def list_repos(request: Request, current_user: User = Depends(get_current_user)):
    github_token = decrypt_github_token(current_user.access_token)
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
    }

    repos = []
    try:
        async with httpx.AsyncClient(timeout=GITHUB_TIMEOUT) as client:
            for page in range(1, MAX_PAGES + 1):
                response = await client.get(
                    "https://api.github.com/user/repos",
                    headers=headers,
                    params={"per_page": PER_PAGE, "page": page},
                )

                if response.status_code == 401:
                    logger.warning("Token GitHub invalide pour user=%s", current_user.login)
                    raise AuthError("Token GitHub invalide ou expiré")
                if response.status_code != 200:
                    logger.error(
                        "Erreur GitHub API (status=%d) pour user=%s",
                        response.status_code,
                        current_user.login,
                    )
                    raise ExternalServiceError("Erreur GitHub")

                page_repos = response.json()
                if not page_repos:
                    break
                repos.extend(page_repos)

    except httpx.TimeoutException:
        logger.error("Timeout GitHub API pour user=%s", current_user.login)
        raise ExternalServiceError("GitHub ne repond pas, reessayez dans quelques instants")

    logger.info("Repos listes: %d repos pour user=%s", len(repos), current_user.login)
    return [
        {
            "id": repo["id"],
            "name": repo["full_name"],
            "description": repo["description"],
            "language": repo["language"],
            "visibility": repo["visibility"],
            "url": repo["html_url"],
        }
        for repo in repos
    ]


@router.get("/{owner}/{repo}/scan")
@limiter.limit("10/minute")
async def scan_repo(
    request: Request,
    owner: str,
    repo: str,
    branch: str = "HEAD",
    current_user: User = Depends(get_current_user),
):
    github_token = decrypt_github_token(current_user.access_token)

    try:
        return await fetch_repo_files(owner, repo, github_token, branch)
    except ValueError as exc:
        raise ValidationError(str(exc))
