import asyncio
import json
import logging
import tempfile
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

JS_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx"}

SEVERITY_MAP = {
    1: "low",       # ESLint "warn"
    2: "medium",    # ESLint "error"
}

# Regles ESLint a activer (equivalent des RUFF_RULES)
ESLINT_RULES = {
    "no-unused-vars": "Variable ou import inutilise",
    "no-undef": "Variable non definie",
    "no-empty": "Bloc vide",
    "no-unreachable": "Code inatteignable",
    "no-duplicate-case": "Case duplique dans un switch",
    "no-redeclare": "Variable re-declaree",
    "no-constant-condition": "Condition constante",
    "eqeqeq": "Egalite stricte requise (=== au lieu de ==)",
    "no-var": "Utiliser let/const au lieu de var",
    "prefer-const": "Utiliser const quand la variable n'est pas reassignee",
}

# Cree un fichier de config ESLint flat dans le dossier temporaire.
def _build_eslint_config(tmp_dir: str) -> str:
    rules = {}
    for rule in ESLINT_RULES:
        rules[rule] = "error"

    config = [
        {
            "rules": rules,
        }
    ]

    config_path = Path(tmp_dir) / "eslint.config.mjs"
    config_content = f"export default {json.dumps(config, indent=2)};\n"
    config_path.write_text(config_content, encoding="utf-8")
    return str(config_path)

# Ecrit les fichiers JS/TS dans un dossier temp, lance ESLint, retourne les issues.
async def run_eslint_on_files(files: list[dict]) -> list[dict]:
    js_files = [
        f for f in files
        if Path(f["path"]).suffix.lower() in JS_EXTENSIONS
        and f.get("content", "").strip()
    ]

    if not js_files:
        logger.info("ESLint: aucun fichier JS/TS a analyser")
        return []

    tmp_dir = tempfile.mkdtemp(prefix="commitclarify_eslint_")
    path_map = {}

    try:
        for f in js_files:
            file_path = Path(tmp_dir) / f["path"]
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(f["content"], encoding="utf-8")
            path_map[str(file_path)] = f["path"]

        _build_eslint_config(tmp_dir)

        try:
            proc = await asyncio.create_subprocess_exec(
                "npx", "eslint",
                "--format", "json",
                "--no-eslintrc",
                "--config", str(Path(tmp_dir) / "eslint.config.mjs"),
                *[str(Path(tmp_dir) / f["path"]) for f in js_files],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
        except FileNotFoundError:
            logger.warning("ESLint: npx non disponible — skip")
            return []

        if not stdout.strip():
            return []

        try:
            eslint_results = json.loads(stdout.decode("utf-8"))
        except json.JSONDecodeError:
            logger.warning("ESLint: impossible de parser la sortie JSON")
            return []

        issues = []
        for file_result in eslint_results:
            abs_path = file_result.get("filePath", "")
            original_path = path_map.get(abs_path, abs_path)

            for msg in file_result.get("messages", []):
                rule_id = msg.get("ruleId") or ""
                severity_int = msg.get("severity", 1)
                line = msg.get("line", "?")
                message = msg.get("message", "")

                code_hint = _extract_line(abs_path, line)

                issues.append({
                    "severity": SEVERITY_MAP.get(severity_int, "low"),
                    "title": ESLINT_RULES.get(rule_id, message),
                    "file_path": original_path,
                    "description": f"Ligne {line} : {message}",
                    "code_hint": code_hint,
                    "source": "eslint",
                })

        logger.info("ESLint termine: %d issues sur %d fichiers JS/TS", len(issues), len(js_files))
        return issues[:10]

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

# Extrait une ligne specifique d'un fichier
def _extract_line(file_path: str, line_number: int) -> str:
    try:
        with open(file_path, encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                if i == line_number:
                    return line.strip()
    except Exception:
        pass
    return ""
