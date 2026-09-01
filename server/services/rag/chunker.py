import logging
import uuid
from functools import lru_cache
from pathlib import Path

from core.file_rules import CONFIG_EXTENSIONS, DOC_EXTENSIONS

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _splitter_class():
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    return RecursiveCharacterTextSplitter

CHUNK_CONFIG = {
    "code": {
        "chunk_size": 1500,
        "chunk_overlap": 200,
    },
    "config": {
        "chunk_size": 800,
        "chunk_overlap": 100,
    },
    "docs": {
        "chunk_size": 1000,
        "chunk_overlap": 300,
    },
}


def _get_chunk_config(path: str) -> dict:
    suffix = Path(path).suffix.lower()
    if suffix in CONFIG_EXTENSIONS:
        return CHUNK_CONFIG["config"]
    if suffix in DOC_EXTENSIONS:
        return CHUNK_CONFIG["docs"]
    return CHUNK_CONFIG["code"]


def _get_separators(language: str) -> list[str]:
    separators_by_lang = {
        "python": ["\nclass ", "\ndef ", "\n\n", "\n", " ", ""],
        "js":     ["\nfunction ", "\nconst ", "\nclass ", "\n\n", "\n", " ", ""],
        "ts":     ["\nfunction ", "\nconst ", "\nclass ", "\ninterface ", "\n\n", "\n", " ", ""],
        "jsx":    ["\nfunction ", "\nconst ", "\nexport ", "\n\n", "\n", " ", ""],
        "tsx":    ["\nfunction ", "\nconst ", "\nexport ", "\n\n", "\n", " ", ""],
        "java":   ["\npublic ", "\nprivate ", "\nprotected ", "\nclass ", "\n\n", "\n", " ", ""],
        "go":     ["\nfunc ", "\ntype ", "\n\n", "\n", " ", ""],
        "rs":     ["\nfn ", "\nimpl ", "\nstruct ", "\n\n", "\n", " ", ""],
        "dart":   ["\nclass ", "\nvoid ", "\nFuture", "\n\n", "\n", " ", ""],
    }
    return separators_by_lang.get(language.lower(), ["\n\n", "\n", " ", ""])


def chunk_files(files: list[dict]) -> dict:
    """
    Découpe la liste de fichiers en chunks prêts pour ChromaDB.

    Retourne :
    {
        "code_chunks":   [...],   # tous les fichiers sauf README
        "readme_chunks": [...],   # README séparé (peut être vide)
        "stats": {
            "total_files":  int,
            "total_chunks": int,
            "readme_found": bool,
        }
    }
    """
    code_chunks = []
    readme_chunks = []

    for file in files:
        if Path(file["path"]).name.lower() == "readme.md":
            readme_chunks = _chunk_single_file(
                file=file,
                config=CHUNK_CONFIG["docs"],
                separators=["\n## ", "\n### ", "\n\n", "\n", " ", ""],
                file_type="readme",
            )
            continue

        config = _get_chunk_config(file["path"])
        separators = _get_separators(file["language"])

        chunks = _chunk_single_file(
            file=file,
            config=config,
            separators=separators,
            file_type="code",
        )
        code_chunks.extend(chunks)

    logger.info("Chunking: %d fichiers -> %d code chunks + %d readme chunks",
                 len(files), len(code_chunks), len(readme_chunks))
    return {
        "code_chunks": code_chunks,
        "readme_chunks": readme_chunks,
        "stats": {
            "total_files": len(files),
            "total_chunks": len(code_chunks) + len(readme_chunks),
            "readme_found": len(readme_chunks) > 0,
        }
    }


def _chunk_single_file(
    file: dict,
    config: dict,
    separators: list[str],
    file_type: str,
) -> list[dict]:
    
    content = file["content"]
    path = file["path"]
    language = file["language"]
    sha = file["sha"]

    if not content.strip():
        return []

    splitter = _splitter_class()(
        chunk_size=config["chunk_size"],
        chunk_overlap=config["chunk_overlap"],
        separators=separators,
        length_function=len,
        is_separator_regex=False,
    )

    raw_chunks = splitter.split_text(content)

    
    raw_chunks = [c for c in raw_chunks if len(c.strip()) > 50]

    chunks = []
    for i, chunk_content in enumerate(raw_chunks):
        chunks.append({
            "content": chunk_content,
            "metadata": {
                "chunk_id": str(uuid.uuid4()),
                "file_path": path,
                "file_sha": sha,
                "language": language,
                "file_type": file_type,
                "chunk_index": i,
                "total_chunks": len(raw_chunks),
                "file_name": Path(path).name,
                "directory": str(Path(path).parent),
            }
        })

    return chunks
