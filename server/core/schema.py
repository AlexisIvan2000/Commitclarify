import asyncio
import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from core.database import engine

logger = logging.getLogger(__name__)

SERVER_ROOT = Path(__file__).resolve().parents[1]
BASELINE_REVISION = "0001_baseline"


def _alembic_config() -> Config:
    config = Config(str(SERVER_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(SERVER_ROOT / "migrations"))
    return config


def _table_names(connection) -> list[str]:
    return inspect(connection).get_table_names()


async def upgrade_schema() -> None:
    async with engine.connect() as connection:
        tables = await connection.run_sync(_table_names)

    if "alembic_version" not in tables and "users" in tables:
        logger.info(
            "Base existante sans historique Alembic, marquage de la revision %s",
            BASELINE_REVISION,
        )
        await asyncio.to_thread(command.stamp, _alembic_config(), BASELINE_REVISION)

    await asyncio.to_thread(command.upgrade, _alembic_config(), "head")
    logger.info("Schema de base de donnees a jour")
