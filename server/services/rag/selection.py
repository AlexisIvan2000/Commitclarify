from pathlib import PurePosixPath

from core.file_rules import CONFIG_EXTENSIONS, DOC_EXTENSIONS
from services.scan.ecosystems import SOURCE_EXTENSIONS
from services.scan.paths import is_test_path

MAX_INDEXED_CHUNKS = 1200

ALL_SOURCE_EXTENSIONS = {
    extension
    for extensions in SOURCE_EXTENSIONS.values()
    for extension in extensions
}

GENERATED_MARKERS = (
    "vendor/", "vendored/", "third_party/", "thirdparty/", "generated/",
    "__generated__/", "node_modules/", "dist/", "build/", "out/",
    ".min.", "-min.", ".bundle.", ".lock", "-lock.", ".snap",
    "migrations/", "fixtures/", "__snapshots__/", "locales/", "i18n/",
)

DOC = 0
SOURCE = 1
CONFIG = 2
TEST = 3
GENERATED = 4

TIER_NAMES = {
    DOC: "documentation",
    SOURCE: "source",
    CONFIG: "configuration",
    TEST: "tests",
    GENERATED: "genere_ou_vendored",
}


def _looks_generated(path: str) -> bool:
    lowered = path.lower()
    return any(marker in lowered for marker in GENERATED_MARKERS)


def tier_of(chunk: dict) -> int:
    metadata = chunk.get("metadata") or {}
    path = metadata.get("file_path") or ""
    suffix = PurePosixPath(path).suffix.lower()

    if metadata.get("file_type") == "readme" or suffix in DOC_EXTENSIONS:
        return DOC
    if _looks_generated(path):
        return GENERATED
    if is_test_path(path):
        return TEST
    if suffix in ALL_SOURCE_EXTENSIONS:
        return SOURCE
    if suffix in CONFIG_EXTENSIONS:
        return CONFIG

    return CONFIG


def _rank(chunk: dict) -> tuple:
    metadata = chunk.get("metadata") or {}
    return (
        tier_of(chunk),
        metadata.get("chunk_index", 0),
        metadata.get("file_path") or "",
    )


def select_chunks(chunks: list[dict], limit: int = MAX_INDEXED_CHUNKS) -> dict:
    ordered = sorted(chunks, key=_rank)
    kept = ordered[:limit]
    dropped = ordered[limit:]

    by_tier = {}
    for chunk in dropped:
        name = TIER_NAMES[tier_of(chunk)]
        by_tier[name] = by_tier.get(name, 0) + 1

    return {
        "chunks": kept,
        "total": len(chunks),
        "indexed": len(kept),
        "dropped": len(dropped),
        "dropped_by_tier": by_tier,
        "complete": not dropped,
    }
