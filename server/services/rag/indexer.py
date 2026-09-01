import logging
from collections.abc import Callable

import chromadb
from chromadb.config import Settings

from core.config import CHROMA_PATH
from services.rag.embeddings import get_embeddings_batch, model_tag

logger = logging.getLogger(__name__)

chroma_client = chromadb.PersistentClient(
    path=CHROMA_PATH,
    settings=Settings(anonymized_telemetry=False),
)

COLLECTION_PREFIX = "cc"
MAX_COLLECTION_NAME = 63
INSERT_BATCH = 500


def build_collection_name(user_id: str, repo_name: str, sha: str) -> str:
    head = f"{COLLECTION_PREFIX}-{model_tag()}-{user_id[:8]}-{sha[:8]}"
    clean_repo = repo_name.replace("/", "-").replace("_", "-").lower()
    budget = MAX_COLLECTION_NAME - len(head) - 1

    if budget < 1:
        return head[:MAX_COLLECTION_NAME]

    return f"{head}-{clean_repo[:budget]}".rstrip("-")


def collection_exists(user_id: str, repo_name: str, sha: str) -> bool:
    name = build_collection_name(user_id, repo_name, sha)
    return name in {c.name for c in chroma_client.list_collections()}


def get_collection(user_id: str, repo_name: str, sha: str):
    return chroma_client.get_collection(build_collection_name(user_id, repo_name, sha))


def delete_collection(user_id: str, repo_name: str, sha: str) -> None:
    name = build_collection_name(user_id, repo_name, sha)
    try:
        chroma_client.delete_collection(name)
        logger.info("Collection supprimee: %s", name)
    except Exception:
        logger.debug("Collection deja absente: %s", name)


async def index_chunks(
    user_id: str,
    repo_name: str,
    sha: str,
    chunks: list[dict],
    on_progress: Callable[[int, int], None] | None = None,
) -> dict:
    collection_name = build_collection_name(user_id, repo_name, sha)

    if collection_exists(user_id, repo_name, sha):
        logger.info("Cache hit: collection=%s", collection_name)
        return {"collection_name": collection_name, "cached": True, "chunks_indexed": 0}

    collection = chroma_client.create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    if not chunks:
        return {"collection_name": collection_name, "cached": False, "chunks_indexed": 0}

    embeddings = await get_embeddings_batch(
        [chunk["content"] for chunk in chunks], on_progress=on_progress,
    )

    for i in range(0, len(chunks), INSERT_BATCH):
        batch = chunks[i:i + INSERT_BATCH]
        collection.add(
            ids=[chunk["metadata"]["chunk_id"] for chunk in batch],
            embeddings=embeddings[i:i + INSERT_BATCH],
            documents=[chunk["content"] for chunk in batch],
            metadatas=[chunk["metadata"] for chunk in batch],
        )

    logger.info("Indexation terminee: %d chunks dans %s", len(chunks), collection_name)
    return {"collection_name": collection_name, "cached": False, "chunks_indexed": len(chunks)}


def retrieve_chunks(
    collection_name: str,
    query_embedding: list[float],
    n_results: int = 15,
    filter_metadata: dict | None = None,
) -> list[dict]:
    collection = chroma_client.get_collection(collection_name)

    kwargs = {
        "query_embeddings": [query_embedding],
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }
    if filter_metadata:
        kwargs["where"] = filter_metadata

    results = collection.query(**kwargs)

    chunks = [
        {
            "content": doc,
            "metadata": meta,
            "similarity": round(1 - dist, 4),
        }
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        )
    ]

    chunks.sort(key=lambda c: c["similarity"], reverse=True)
    return chunks
