import logging
import uuid

import chromadb
from chromadb.config import Settings
from services.rag.embeddings import get_embeddings_batch

logger = logging.getLogger(__name__)

# Persistant sur disque — les collections survivent aux redémarrages
chroma_client = chromadb.PersistentClient(
    path="./chroma_db",
    settings=Settings(anonymized_telemetry=False)
)

COLLECTION_PREFIX = "cc"  # CommitClarify


def build_collection_name(user_id: str, repo_name: str, sha: str) -> str:
    """
    Construit le nom de la collection ChromaDB.
    ChromaDB impose : 3-63 chars, alphanumérique + tirets, pas de points.
    """
    # Nettoyer le repo_name (ex: "alexis/mon-repo" → "alexis-mon-repo")
    clean_repo = repo_name.replace("/", "-").replace("_", "-").lower()
    short_sha  = sha[:8]

    name = f"{COLLECTION_PREFIX}-{user_id[:8]}-{clean_repo}-{short_sha}"

    # Tronquer si trop long (limite ChromaDB : 63 chars)
    return name[:63]


def collection_exists(user_id: str, repo_name: str, sha: str) -> bool:
    """Vérifie si une collection existe déjà pour ce SHA — cache check."""
    name = build_collection_name(user_id, repo_name, sha)
    existing = [c.name for c in chroma_client.list_collections()]
    return name in existing


def get_collection(user_id: str, repo_name: str, sha: str):
    """Récupère une collection existante."""
    name = build_collection_name(user_id, repo_name, sha)
    return chroma_client.get_collection(name)


def delete_collection(user_id: str, repo_name: str, sha: str) -> None:
    """Supprime une collection — utile pour forcer une re-analyse."""
    name = build_collection_name(user_id, repo_name, sha)
    try:
        chroma_client.delete_collection(name)
    except Exception:
        pass  # Collection inexistante — pas grave


async def index_chunks(
    user_id:   str,
    repo_name: str,
    sha:       str,
    chunks:    list[dict],
) -> dict:
    
    # Point d'entrée principal.
    # Vectorise et indexe les chunks dans ChromaDB.

    # Retourne :
    # {
    #     "collection_name": str,
    #     "cached":          bool,   # True si déjà indexé
    #     "chunks_indexed":  int,
    # }
   
    collection_name = build_collection_name(user_id, repo_name, sha)

    #  Cache hit — collection déjà indexée pour ce SHA
    if collection_exists(user_id, repo_name, sha):
        logger.info("Cache hit: collection=%s", collection_name)
        return {
            "collection_name": collection_name,
            "cached":          True,
            "chunks_indexed":  0,
        }

    # Nouvelle collection 
    collection = chroma_client.create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},  # distance cosinus pour le code
    )

    if not chunks:
        return {
            "collection_name": collection_name,
            "cached":          False,
            "chunks_indexed":  0,
        }

    #  Vectorisation par batch 
    texts = [chunk["content"] for chunk in chunks]
    embeddings = await get_embeddings_batch(texts)

    # Insertion dans ChromaDB 
    # ChromaDB accepte max 5461 items par appel — on insère par batch de 500
    INSERT_BATCH = 500

    for i in range(0, len(chunks), INSERT_BATCH):
        batch_chunks     = chunks[i:i + INSERT_BATCH]
        batch_embeddings = embeddings[i:i + INSERT_BATCH]

        collection.add(
            ids        = [chunk["metadata"]["chunk_id"] for chunk in batch_chunks],
            embeddings = batch_embeddings,
            documents  = [chunk["content"] for chunk in batch_chunks],
            metadatas  = [chunk["metadata"] for chunk in batch_chunks],
        )

    logger.info("Indexation terminee: %d chunks dans %s", len(chunks), collection_name)
    return {
        "collection_name": collection_name,
        "cached":          False,
        "chunks_indexed":  len(chunks),
    }


def retrieve_chunks(
    collection_name: str,
    query:           str,
    query_embedding: list[float],
    n_results:       int = 15,
    filter_metadata: dict | None = None,
) -> list[dict]:
    """
    Recherche les chunks les plus pertinents pour une requête.
    Utilisé par les agents d'analyse.

    Retourne une liste de chunks avec leur contenu et métadonnées.
    """
    collection = chroma_client.get_collection(collection_name)

    kwargs = {
        "query_embeddings": [query_embedding],
        "n_results":        n_results,
        "include":          ["documents", "metadatas", "distances"],
    }

    # Filtre optionnel sur les métadonnées
    # ex: {"language": "python"} pour ne chercher que dans les fichiers Python
    if filter_metadata:
        kwargs["where"] = filter_metadata

    results = collection.query(**kwargs)

    # Reformater pour faciliter l'usage dans les agents
    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        chunks.append({
            "content":    doc,
            "metadata":   meta,
            "similarity": round(1 - dist, 4),  # distance cosinus → score similarité
        })

    # Trier par similarité décroissante
    chunks.sort(key=lambda x: x["similarity"], reverse=True)

    return chunks

