import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from models.db_models import User
from repositories import analysis as analysis_repo, user as user_repo
from services.rag.indexer import delete_collection

logger = logging.getLogger(__name__)


async def delete_account(user: User, db: AsyncSession) -> None:
    vector_refs = await analysis_repo.list_vector_refs(user.id, db)

    user_id = str(user.id)
    login = user.login
    github_id = user.github_id

    await user_repo.purge_account(user, db)
    await db.commit()

    await _purge_vector_collections(user_id, vector_refs)

    logger.info("Compte supprime: user=%s (github_id=%s)", login, github_id)


async def _purge_vector_collections(user_id: str, vector_refs) -> None:
    for ref in vector_refs:
        if not ref.repo_sha:
            continue
        try:
            await asyncio.to_thread(delete_collection, user_id, ref.repo_name, ref.repo_sha)
        except Exception as exc:
            logger.warning("Purge collection %s echouee: %s", ref.repo_name, exc)
