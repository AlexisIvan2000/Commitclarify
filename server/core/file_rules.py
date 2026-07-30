import json
from pathlib import Path

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "models" / "extensions.json"

with open(_CONFIG_PATH, encoding="utf-8") as _f:
    _CONFIG = json.load(_f)

_EXTENSION_GROUPS = _CONFIG["ALLOWED_EXTENSIONS"]

ALLOWED_EXTENSIONS = {ext for group in _EXTENSION_GROUPS.values() for ext in group}
CONFIG_EXTENSIONS = set(_EXTENSION_GROUPS["config"])
DOC_EXTENSIONS = set(_EXTENSION_GROUPS["docs"])

ALLOWED_FILENAMES = set(_CONFIG["ALLOWED_FILENAMES"])
EXCLUDED_DIRS = set(_CONFIG["EXCLUDED_DIRS"])

MAX_FILE_SIZE = _CONFIG["LIMITS"]["MAX_FILE_SIZE"]
MAX_FILE_LINES = _CONFIG["LIMITS"]["MAX_FILE_LINES"]
MAX_REPO_FILES = _CONFIG["LIMITS"]["MAX_REPO_FILES"]
BATCH_SIZE = _CONFIG["LIMITS"]["BATCH_SIZE"]
