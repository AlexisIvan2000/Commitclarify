import json
import logging
import shutil
from functools import lru_cache
from pathlib import Path

from core.language import DEFAULT_LANGUAGE, text
from services.ai.linters.base import (
    MAX_ISSUES_PER_LINTER,
    extract_line,
    materialized_files,
    run_tool,
    select_files,
)

logger = logging.getLogger(__name__)

JS_EXTENSIONS = {".js", ".mjs", ".cjs", ".jsx"}

SERVER_ROOT = Path(__file__).resolve().parents[3]

RULES = {
    "no-unused-vars": "low",
    "no-empty": "low",
    "no-unreachable": "medium",
    "no-duplicate-case": "medium",
    "no-redeclare": "medium",
    "no-constant-condition": "medium",
    "eqeqeq": "low",
    "no-var": "low",
    "prefer-const": "low",
}

CONFIG_FILENAME = "cc-eslint.config.mjs"

CONFIG_TEMPLATE = """export default [
  {{
    files: ["**/*.js", "**/*.mjs", "**/*.cjs", "**/*.jsx"],
    languageOptions: {{
      ecmaVersion: "latest",
      sourceType: "module",
      parserOptions: {{ ecmaFeatures: {{ jsx: true }} }},
    }},
    linterOptions: {{ reportUnusedDisableDirectives: false }},
    rules: {rules},
  }},
];
"""


@lru_cache(maxsize=1)
def find_eslint() -> str | None:
    for candidate in ("eslint.cmd", "eslint"):
        local = SERVER_ROOT / "node_modules" / ".bin" / candidate
        if local.exists():
            return str(local)

    resolved = shutil.which("eslint")
    if resolved:
        return resolved

    logger.error(
        "ESLint introuvable (ni %s/node_modules/.bin, ni PATH) — lancez `npm install` "
        "dans le dossier server pour activer l'analyse JS/TS",
        SERVER_ROOT,
    )
    return None


def _write_config(tmp_dir: str) -> None:
    rules = json.dumps({rule: "error" for rule in RULES}, indent=6)
    (Path(tmp_dir) / CONFIG_FILENAME).write_text(
        CONFIG_TEMPLATE.format(rules=rules), encoding="utf-8"
    )


async def run_eslint_on_files(files: list[dict], language: str = DEFAULT_LANGUAGE) -> list[dict]:
    js_files = select_files(files, JS_EXTENSIONS)
    if not js_files:
        logger.info("ESLint: aucun fichier JS a analyser")
        return []

    eslint = find_eslint()
    if not eslint:
        return []

    with materialized_files(js_files, "commitclarify_eslint_") as (tmp_dir, path_map):
        _write_config(tmp_dir)

        stdout = await run_tool(
            "eslint",
            [
                eslint,
                "--format", "json",
                "--config", CONFIG_FILENAME,
                "--no-config-lookup",
                *[f["path"] for f in js_files],
            ],
            cwd=tmp_dir,
        )

        if not stdout:
            return []

        try:
            results = json.loads(stdout)
        except json.JSONDecodeError:
            logger.error("ESLint: sortie JSON illisible: %s", stdout[:300])
            return []

        issues = []
        parse_failures = 0

        for file_result in results:
            abs_path = str(Path(file_result.get("filePath", "")))
            original_path = path_map.get(abs_path, file_result.get("filePath", ""))

            for msg in file_result.get("messages", []):
                rule_id = msg.get("ruleId")
                if rule_id not in RULES:
                    if msg.get("fatal"):
                        parse_failures += 1
                    continue

                line = msg.get("line", "?")

                issues.append({
                    "severity": RULES[rule_id],
                    "title": text(f"rule.{rule_id}", language),
                    "rule": rule_id,
                    "file_path": original_path,
                    "line": line if isinstance(line, int) else None,
                    "description": text(
                        "issue.at_line", language, line=line, message=msg.get("message", ""),
                    ),
                    "code_hint": extract_line(abs_path, line),
                    "source": "eslint",
                })

        if parse_failures:
            logger.info("ESLint: %d fichier(s) non parsables ignore(s)", parse_failures)

        logger.info("ESLint termine: %d issues sur %d fichiers JS", len(issues), len(js_files))
        return issues[:MAX_ISSUES_PER_LINTER]
