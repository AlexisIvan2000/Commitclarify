import logging
from functools import lru_cache

import httpx
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import FERNET_KEY, GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET
from core.exceptions import AuthError, ExternalServiceError, ValidationError
from models.db_models import User

logger = logging.getLogger(__name__)

GITHUB_TIMEOUT = 15


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    return Fernet(FERNET_KEY)


async def github_exchange_code(code: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=GITHUB_TIMEOUT) as client:
            response = await client.post(
                "https://github.com/login/oauth/access_token",
                data={
                    "client_id": GITHUB_CLIENT_ID,
                    "client_secret": GITHUB_CLIENT_SECRET,
                    "code": code,
                },
                headers={"Accept": "application/json"},
            )
    except httpx.HTTPError as exc:
        logger.error("GitHub injoignable pendant l'echange OAuth: %s", exc)
        raise ExternalServiceError("GitHub est injoignable, reessayez dans quelques instants")

    if response.status_code != 200:
        logger.error("Echange OAuth: status=%d", response.status_code)
        raise ExternalServiceError("GitHub a refuse l'echange du code OAuth")

    data = response.json()
    if "access_token" not in data:
        logger.warning("Echec echange code OAuth: %s", data.get("error_description", data))
        raise ValidationError(f"GitHub OAuth error: {data.get('error_description', data)}")

    logger.info("Code OAuth echange avec succes")
    return data["access_token"]


async def github_get_user(access_token: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=GITHUB_TIMEOUT) as client:
            response = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
            )
    except httpx.HTTPError as exc:
        logger.error("GitHub injoignable pendant la lecture du profil: %s", exc)
        raise ExternalServiceError("GitHub est injoignable, reessayez dans quelques instants")

    if response.status_code == 401:
        raise AuthError("Le token GitHub a ete refuse")
    if response.status_code != 200:
        logger.error("Lecture profil GitHub: status=%d", response.status_code)
        raise ExternalServiceError("Impossible de lire le profil GitHub")

    payload = response.json()
    if "id" not in payload or "login" not in payload:
        logger.error("Profil GitHub incomplet: cles=%s", sorted(payload)[:10])
        raise ExternalServiceError("Reponse GitHub inattendue")

    return payload


async def upsert_user(github_user: dict, access_token: str, db: AsyncSession) -> User:
    encrypted_token = _fernet().encrypt(access_token.encode()).decode()

    result = await db.execute(select(User).where(User.github_id == github_user["id"]))
    user = result.scalars().first()

    if user:
        logger.info("Utilisateur existant mis a jour: %s", github_user["login"])
        user.login = github_user["login"]
        user.username = github_user.get("name") or github_user["login"]
        user.avatar_url = github_user.get("avatar_url")
        user.email = github_user.get("email")
        user.access_token = encrypted_token
    else:
        logger.info("Nouvel utilisateur cree: %s", github_user["login"])
        user = User(
            github_id=github_user["id"],
            login=github_user["login"],
            username=github_user.get("name") or github_user["login"],
            avatar_url=github_user.get("avatar_url"),
            email=github_user.get("email"),
            access_token=encrypted_token,
        )
        db.add(user)

    await db.commit()
    await db.refresh(user)
    return user


def decrypt_github_token(encrypted_token: str) -> str:
    try:
        return _fernet().decrypt(encrypted_token.encode()).decode()
    except InvalidToken:
        logger.error("Token GitHub indechiffrable (FERNET_KEY a change ?)")
        raise AuthError("Session GitHub invalide, reconnectez-vous")
