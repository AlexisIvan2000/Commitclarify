import asyncio
import logging
from functools import lru_cache
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Modele local — zero API, zero quota
_model = SentenceTransformer("all-MiniLM-L6-v2")

BATCH_SIZE = 256

# Cache pour les queries fixes des agents (toujours les memes strings)
@lru_cache(maxsize=32)
def _cached_encode(text: str) -> tuple[float, ...]:
    return tuple(_model.encode(text).tolist())


async def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Genere les embeddings pour une liste de textes via le modele local."""
    embeddings = await asyncio.to_thread(_model.encode, texts, batch_size=BATCH_SIZE)
    return [e.tolist() for e in embeddings]


async def get_embedding(text: str) -> list[float]:
    """Genere l'embedding d'un seul texte (cache pour les queries repetees)."""
    return list(_cached_encode(text))
