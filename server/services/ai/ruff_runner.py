import asyncio
import json
import logging
import tempfile
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

# Regles Ruff a verifier
RUFF_RULES = [
    "F401",   # import inutilise
    "F841",   # variable assignee mais jamais utilisee
    "E501",   # ligne trop longue (>120)
    "E722",   # bare except
    "B001",   # do not use bare except
    "B006",   # mutable default argument
    "C901",   # fonction trop complexe (cyclomatique)
    "PLR0913",  # trop de parametres
    "PLR0915",  # trop de statements
]

RUFF_LABELS = {
    "F401": "Import inutilise",
    "F841": "Variable assignee mais jamais utilisee",
    "E501": "Ligne trop longue",
    "E722": "Bare except (except sans type)",
    "B001": "Bare except (except sans type)",
    "B006": "Argument par defaut mutable",
    "C901": "Fonction trop complexe",
    "PLR0913": "Trop de parametres",
    "PLR0915": "Trop de statements dans la fonction",
}

SEVERITY_MAP = {
    "F401": "low",
    "F841": "low",
    "E501": "low",
    "E722": "medium",
    "B001": "medium",
    "B006": "medium",
    "C901": "high",
    "PLR0913": "medium",
    "PLR0915": "medium",
}

PYTHON_EXTENSIONS = {".py", ".pyw", ".pyi"}


async def run_ruff_on_files(files: list[dict]) -> list[dict]:
    """Ecrit les fichiers Python dans un dossier temp, lance Ruff, retourne les issues."""
    python_files = [
        f for f in files
        if Path(f["path"]).suffix.lower() in PYTHON_EXTENSIONS
        and f.get("content", "").strip()
    ]

    if not python_files:
        logger.info("Ruff: aucun fichier Python a analyser")
        return []

    tmp_dir = tempfile.mkdtemp(prefix="commitclarify_ruff_")
    path_map = {}

    try:
        for f in python_files:
            file_path = Path(tmp_dir) / f["path"]
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(f["content"], encoding="utf-8")
            path_map[str(file_path)] = f["path"]

        rules = ",".join(RUFF_RULES)
        proc = await asyncio.create_subprocess_exec(
            "ruff", "check",
            "--select", rules,
            "--output-format", "json",
            "--no-fix",
            "--line-length", "120",
            "--target-version", "py310",
            tmp_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()

        if not stdout.strip():
            return []

        ruff_results = json.loads(stdout.decode("utf-8"))
        issues = []

        for r in ruff_results:
            abs_path = r.get("filename", "")
            original_path = path_map.get(abs_path, abs_path)
            code = r.get("code", "")
            line = r.get("location", {}).get("row", "?")
            message = r.get("message", "")

            # Extraire la ligne de code concernee comme code_hint
            code_hint = _extract_line(abs_path, line)

            issues.append({
                "severity": SEVERITY_MAP.get(code, "low"),
                "title": RUFF_LABELS.get(code, message),
                "file_path": original_path,
                "description": f"Ligne {line} : {message}",
                "code_hint": code_hint,
                "source": "ruff",
            })

        logger.info("Ruff termine: %d issues sur %d fichiers Python", len(issues), len(python_files))
        return issues[:10]

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _extract_line(file_path: str, line_number: int) -> str:
    """Extrait une ligne specifique d'un fichier."""
    try:
        with open(file_path, encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                if i == line_number:
                    return line.strip()
    except Exception:
        pass
    return ""
