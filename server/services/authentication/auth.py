import logging

import httpx
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.db_models import User
from core.config import GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, FERNET_KEY

fernet = Fernet(FERNET_KEY)


# Echange le code d'autorisation GitHub contre un token d'accès
async def github_exchange_code(code: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )
        data = response.json()
        if "access_token" not in data:
            logger.warning("Echec echange code OAuth: %s", data.get("error_description", data))
            raise ValueError(f"GitHub OAuth error: {data.get('error_description', data)}")

        logger.info("Code OAuth echange avec succes")
        return data["access_token"]


# Récupère les informations de l'utilisateur à partir du token d'accès
async def github_get_user(access_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )

    return response.json()


# Crée ou met à jour l'utilisateur dans la base de données
async def upsert_user(github_user: dict, access_token: str, db: AsyncSession) -> User:
    encrypted_token = fernet.encrypt(access_token.encode()).decode()

    result = await db.execute(select(User).where(User.github_id == github_user["id"]))
    user = result.scalars().first()

    if user:
        logger.info("Utilisateur existant mis a jour: %s", github_user["login"])
        user.login = github_user["login"]
        user.username = github_user["name"] or github_user["login"]
        user.avatar_url = github_user.get("avatar_url")
        user.email = github_user.get("email")
        user.access_token = encrypted_token
    else:
        logger.info("Nouvel utilisateur cree: %s", github_user["login"])
        user = User(
            github_id=github_user["id"],
            login=github_user["login"],
            username=github_user["name"] or github_user["login"],
            avatar_url=github_user.get("avatar_url"),
            email=github_user.get("email"),
            access_token=encrypted_token,
        )
        db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def decrypt_github_token(encrypted_token: str) -> str:
    return fernet.decrypt(encrypted_token.encode()).decode()


