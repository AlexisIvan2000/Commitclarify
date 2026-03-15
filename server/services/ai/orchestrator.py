import asyncio
import logging

from services.ai.security_agent import run_secrets_detection, run_gitignore_check
from services.ai.consistency_agent import run_quality_check, run_readme_check

logger = logging.getLogger(__name__)

# Point d'entrée unique pour lancer toutes les analyses AI en parallèle
async def run_analysis(collection_name: str, readme_chunks: list[dict], has_gitignore: bool, files: list[dict] = None) -> dict:
    secrets, gitignore, quality, readme = await asyncio.gather(
        run_secrets_detection(collection_name, files or []),
        run_gitignore_check(collection_name, has_gitignore),
        run_quality_check(collection_name, files or []),
        run_readme_check(collection_name, readme_chunks),
    )

    return {
        "secrets_detection": secrets,
        "gitignore_check": gitignore,
        "quality_check": quality,
        "readme_check": readme,
    }