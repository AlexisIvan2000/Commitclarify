import asyncio
import logging
import os
from functools import lru_cache
from sentence_transformers import SentenceTransformer

os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", "/data/models")

logger = logging.getLogger(__name__)

# Modele local — zero API, zero quota
_model = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info("Chargement du modele d'embeddings...")
        _model = SentenceTransformer("all-mpnet-base-v2")
        logger.info("Modele d'embeddings charge")
    return _model

BATCH_SIZE = 256

# Cache pour les queries fixes des agents (toujours les memes strings)
@lru_cache(maxsize=32)
def _cached_encode(text: str) -> tuple[float, ...]:
    return tuple(_get_model().encode(text).tolist())


async def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Genere les embeddings pour une liste de textes via le modele local."""
    model = _get_model()
    embeddings = await asyncio.to_thread(model.encode, texts, batch_size=BATCH_SIZE)
    return [e.tolist() for e in embeddings]


async def get_embedding(text: str) -> list[float]:
    """Genere l'embedding d'un seul texte (cache pour les queries repetees)."""
    return list(_cached_encode(text))
