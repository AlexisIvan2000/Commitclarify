import hashlib
import json

from core.file_rules import (
    ALLOWED_EXTENSIONS,
    ALLOWED_FILENAMES,
    BATCH_SIZE,
    EXCLUDED_DIRS,
    MAX_FILE_LINES,
    MAX_FILE_SIZE,
    MAX_REPO_FILES,
)
from services.scan.documentation import MIN_ENV_VARS_FOR_EXAMPLE, PLATFORM_ENV
from services.scan.quality import (
    COMPLEXITY_THRESHOLD,
    MIN_REQUIREMENTS_FOR_PINNING,
    PINNING_RATIO_THRESHOLD,
)
from services.scan.report import MAX_FINDINGS_PER_AXIS
from services.scan.secrets import MAX_EVIDENCE_LENGTH, SECRET_PATTERNS

CONFIG_HASH_LENGTH = 16


def effective_config() -> dict:
    return {
        "allowed_extensions": sorted(ALLOWED_EXTENSIONS),
        "allowed_filenames": sorted(ALLOWED_FILENAMES),
        "excluded_dirs": sorted(EXCLUDED_DIRS),
        "limits": {
            "max_file_size": MAX_FILE_SIZE,
            "max_file_lines": MAX_FILE_LINES,
            "max_repo_files": MAX_REPO_FILES,
            "batch_size": BATCH_SIZE,
        },
        "secret_patterns": sorted(list(entry) for entry in SECRET_PATTERNS),
        "max_evidence_length": MAX_EVIDENCE_LENGTH,
        "max_findings_per_axis": MAX_FINDINGS_PER_AXIS,
        "complexity_threshold": COMPLEXITY_THRESHOLD,
        "min_requirements_for_pinning": MIN_REQUIREMENTS_FOR_PINNING,
        "pinning_ratio_threshold": PINNING_RATIO_THRESHOLD,
        "min_env_vars_for_example": MIN_ENV_VARS_FOR_EXAMPLE,
        "platform_env": sorted(PLATFORM_ENV),
    }


def compute_config_hash() -> str:
    payload = json.dumps(effective_config(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:CONFIG_HASH_LENGTH]


CONFIG_HASH = compute_config_hash()
