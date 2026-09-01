import asyncio
import hashlib
import logging
import os
from collections.abc import Callable
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", "/data/models")

MODEL_NAME = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
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


def model_tag() -> str:
    return hashlib.sha1(MODEL_NAME.encode("utf-8")).hexdigest()[:4]


async def get_embeddings_batch(
    texts: list[str],
    on_progress: Callable[[int, int], None] | None = None,
) -> list[list[float]]:
    model = _get_model()
    total = len(texts)
    vectors: list[list[float]] = []

    for start in range(0, total, BATCH_SIZE):
        batch = texts[start:start + BATCH_SIZE]
        encoded = await asyncio.to_thread(model.encode, batch, batch_size=BATCH_SIZE)
        vectors.extend(vector.tolist() for vector in encoded)

        if on_progress is not None:
            on_progress(len(vectors), total)

    return vectors


async def get_embedding(text: str) -> list[float]:
    return list(await asyncio.to_thread(_cached_encode, text))
