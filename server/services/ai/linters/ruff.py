import json
import logging
from pathlib import Path

from services.ai.linters.base import (
    MAX_ISSUES_PER_LINTER,
    extract_line,
    materialized_files,
    run_tool,
    select_files,
)

logger = logging.getLogger(__name__)

PYTHON_EXTENSIONS = {".py", ".pyw", ".pyi"}

RULES = {
    "F401": ("Import inutilise", "low"),
    "F841": ("Variable assignee mais jamais utilisee", "low"),
    "E501": ("Ligne trop longue", "low"),
    "E722": ("Bare except (except sans type)", "medium"),
    "B006": ("Argument par defaut mutable", "medium"),
    "C901": ("Fonction trop complexe", "high"),
    "PLR0913": ("Trop de parametres", "medium"),
    "PLR0915": ("Trop de statements dans la fonction", "medium"),
}


async def run_ruff_on_files(files: list[dict]) -> list[dict]:
    python_files = select_files(files, PYTHON_EXTENSIONS)
    if not python_files:
        logger.info("Ruff: aucun fichier Python a analyser")
        return []

    with materialized_files(python_files, "commitclarify_ruff_") as (tmp_dir, path_map):
        stdout = await run_tool(
            "ruff",
            [
                "ruff", "check",
                "--select", ",".join(RULES),
                "--output-format", "json",
                "--no-fix",
                "--isolated",
                "--line-length", "120",
                "--target-version", "py310",
                tmp_dir,
            ],
        )

        if not stdout:
            return []

        try:
            results = json.loads(stdout)
        except json.JSONDecodeError:
            logger.error("Ruff: sortie JSON illisible: %s", stdout[:300])
            return []

        issues = []
        for r in results:
            abs_path = str(Path(r.get("filename", "")))
            code = r.get("code", "")
            line = r.get("location", {}).get("row", "?")
            message = r.get("message", "")
            label, severity = RULES.get(code, (message, "low"))

            issues.append({
                "severity": severity,
                "title": label,
                "file_path": path_map.get(abs_path, r.get("filename", "")),
                "description": f"Ligne {line} : {message}",
                "code_hint": extract_line(abs_path, line),
                "source": "ruff",
            })

        logger.info("Ruff termine: %d issues sur %d fichiers Python", len(issues), len(python_files))
        return issues[:MAX_ISSUES_PER_LINTER]
