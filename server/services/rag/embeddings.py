import asyncio
import logging
import os
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", "/data/models")

MODEL_NAME = "all-mpnet-base-v2"
BATCH_SIZE = 256

_model = None


def _get_model() -> "SentenceTransformer":
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        logger.info("Chargement du modele d'embeddings %s...", MODEL_NAME)
        _model = SentenceTransformer(MODEL_NAME)
        logger.info("Modele d'embeddings charge")
    return _model


@lru_cache(maxsize=32)
def _cached_encode(text: str) -> tuple[float, ...]:
    return tuple(_get_model().encode(text).tolist())


async def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    model = _get_model()
    embeddings = await asyncio.to_thread(model.encode, texts, batch_size=BATCH_SIZE)
    return [e.tolist() for e in embeddings]


async def get_embedding(text: str) -> list[float]:
    return list(await asyncio.to_thread(_cached_encode, text))
