import logging
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

API_ROOT = "https://api.github.com"

USER_AGENT = "CommitClarify"
API_VERSION = "2022-11-28"


class GitHubError(ValueError):
    def __init__(self, message: str, *, status: int, url: str):
        super().__init__(message)
        self.status = status
        self.url = url


def headers(github_token: str) -> dict:
    return {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": API_VERSION,
        "User-Agent": USER_AGENT,
    }


def _reset_time(response: httpx.Response) -> str:
    raw = response.headers.get("x-ratelimit-reset")
    try:
        moment = datetime.fromtimestamp(int(raw), tz=timezone.utc)
    except (TypeError, ValueError):
        return "heure inconnue"

    return moment.strftime("%H:%M UTC")


def _rate_limited(response: httpx.Response) -> bool:
    return response.headers.get("x-ratelimit-remaining") == "0"


def _message(response: httpx.Response, subject: str) -> str:
    status = response.status_code

    if status == 401:
        return "Token GitHub invalide ou expire."

    if status in (403, 429) and _rate_limited(response):
        return f"Quota d'appels GitHub epuise, reinitialisation a {_reset_time(response)}."

    if status == 403:
        return (
            "Acces refuse par GitHub : permissions insuffisantes du token, ou autorisation SSO "
            "d'organisation manquante."
        )

    if status == 404:
        return (
            f"{subject} introuvable ou hors du perimetre du token. Un token a portee restreinte "
            "(fine-grained) renvoie 404 pour tout depot non selectionne, meme public."
        )

    if status == 409:
        return "Le repository est vide."

    return f"Erreur GitHub ({status}) sur {subject}."


def ensure_success(response: httpx.Response, url: str, subject: str) -> None:
    if response.status_code == 200:
        return

    logger.error(
        "GitHub %s -> %d (quota restant=%s, reset=%s)",
        url,
        response.status_code,
        response.headers.get("x-ratelimit-remaining", "?"),
        response.headers.get("x-ratelimit-reset", "?"),
    )

    raise GitHubError(_message(response, subject), status=response.status_code, url=url)


async def get_json(
    url: str,
    github_token: str,
    subject: str,
    *,
    params: dict | None = None,
    timeout: int = 30,
) -> dict:
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.get(url, headers=headers(github_token), params=params)

    ensure_success(response, url, subject)
    return response.json()
