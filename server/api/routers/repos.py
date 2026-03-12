import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
import httpx

logger = logging.getLogger(__name__)

from api.dependencies import get_current_user
from core.rate_limit import limiter
from models.db_models import User
from services.authentication.auth import decrypt_github_token
from services.github.repo_fetcher import fetch_repo_files

router = APIRouter(prefix="/repos", tags=["repos"])

# Endpoint pour lister les repos GitHub de l'utilisateur connecté
@router.get("/")
@limiter.limit("30/minute")
async def list_repos(request: Request, current_user: User = Depends(get_current_user)):
    github_token = decrypt_github_token(current_user.access_token)

    repos = []
    page = 1
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            while page <= 10:
                response = await client.get(
                    "https://api.github.com/user/repos",
                    headers={
                        "Authorization": f"Bearer {github_token}",
                        "Accept": "application/vnd.github+json",
                    },
                    params={"per_page": 100, "page": page},
                )
                if response.status_code == 401:
                    logger.warning("Token GitHub invalide pour user=%s", current_user.login)
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token GitHub invalide ou expiré",
                    )
                if response.status_code != 200:
                    logger.error("Erreur GitHub API (status=%d) pour user=%s", response.status_code, current_user.login)
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="Erreur GitHub",
                    )
                data = response.json()
                if not data:
                    break
                repos.extend(data)
                page += 1
    except httpx.TimeoutException:
        logger.error("Timeout GitHub API pour user=%s", current_user.login)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="GitHub ne repond pas, reessayez dans quelques instants",
        )

    logger.info("Repos listés: %d repos pour user=%s", len(repos), current_user.login)
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

# Endpoint pour scanner un repo spécifique
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
        result = await fetch_repo_files(owner, repo, github_token, branch)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return result
