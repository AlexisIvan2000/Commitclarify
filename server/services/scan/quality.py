import ast
import asyncio
import logging
import re
from pathlib import PurePosixPath

from core.language import DEFAULT_LANGUAGE, normalize, text
from services.ai.linters import run_eslint_on_files, run_ruff_on_files
from services.scan import ecosystems
from services.scan.paths import is_ci_path, is_test_path
from services.scan.report import axis_result, make_finding

logger = logging.getLogger(__name__)

AXIS = "quality_check"

COMPLEXITY_THRESHOLD = 10
COMPLEXITY_HIGH_FACTOR = 2

PYTHON_EXTENSIONS = {".py", ".pyw"}

PINNED_REQUIREMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\s*(==|@)")
IGNORED_REQUIREMENT = re.compile(r"^\s*(#|-r|--|$)")

MIN_REQUIREMENTS_FOR_PINNING = 3
PINNING_RATIO_THRESHOLD = 0.8

LOCKFILE_VARIANTS = {
    False: ("quality.no_lockfile", "medium"),
    True: ("quality.pinned_without_lockfile", "info"),
}

ALL_SOURCE_EXTENSIONS = {
    extension
    for extensions in ecosystems.SOURCE_EXTENSIONS.values()
    for extension in extensions
}


async def scan_quality(files: list[dict], language: str = DEFAULT_LANGUAGE) -> dict:
    language = normalize(language)

    ruff_issues, eslint_issues = await asyncio.gather(
        run_ruff_on_files(files, language),
        run_eslint_on_files(files, language),
    )
    linter_issues = [issue for issue in ruff_issues + eslint_issues if issue["rule"] != "C901"]

    complexity_findings, scores = _complexity_findings(files, language)
    unpinned = _unpinned_requirements(files)
    metrics = _metrics(files, scores, len(linter_issues), _has_pinned_requirements(files, unpinned))

    findings = (
        _linter_findings(linter_issues)
        + complexity_findings
        + _metric_findings(metrics, unpinned, language)
    )

    logger.info("Scan qualite: %d findings, %d fonctions analysees", len(findings), len(scores))
    return axis_result(AXIS, findings, metrics=metrics)


def _linter_findings(issues: list[dict]) -> list[dict]:
    return [
        make_finding(
            AXIS,
            issue["rule"],
            issue["severity"],
            issue["title"],
            issue["description"],
            file_path=issue["file_path"],
            evidence=issue["code_hint"],
            source=issue["source"],
            identity=issue["code_hint"] or f"{issue['rule']}#{index}",
        )
        for index, issue in enumerate(issues)
    ]


def _complexity_of(node: ast.AST) -> int:
    score = 1
    stack = list(ast.iter_child_nodes(node))

    while stack:
        current = stack.pop()

        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue

        if isinstance(current, (ast.If, ast.IfExp, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler)):
            score += 1
        elif isinstance(current, ast.BoolOp):
            score += len(current.values) - 1
        elif isinstance(current, ast.comprehension):
            score += 1 + len(current.ifs)
        elif isinstance(current, ast.match_case):
            score += 1

        stack.extend(ast.iter_child_nodes(current))

    return score


def _complexity_findings(files: list[dict], language: str) -> tuple[list[dict], list[int]]:
    findings = []
    scores = []

    for entry in files:
        path = entry.get("path", "")
        if PurePosixPath(path).suffix.lower() not in PYTHON_EXTENSIONS:
            continue

        try:
            tree = ast.parse(entry.get("content", ""))
        except (SyntaxError, ValueError):
            continue

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            score = _complexity_of(node)
            scores.append(score)
            if score <= COMPLEXITY_THRESHOLD:
                continue

            severity = "high" if score > COMPLEXITY_THRESHOLD * COMPLEXITY_HIGH_FACTOR else "medium"
            findings.append(make_finding(
                AXIS,
                "quality.complex_function",
                severity,
                text("scan.quality.complex_function.title", language, name=node.name),
                text(
                    "scan.quality.complex_function.description",
                    language,
                    name=node.name,
                    score=score,
                    threshold=COMPLEXITY_THRESHOLD,
                ),
                file_path=path,
                line=node.lineno,
                evidence=f"def {node.name}(...)",
                source="ast",
            ))

    return findings, scores


def _metrics(
    files: list[dict],
    scores: list[int],
    linter_issues: int,
    pinned_requirements: bool,
) -> dict:
    paths = [entry.get("path", "") for entry in files if entry.get("path")]
    detected = ecosystems.detect(paths)

    return {
        "ecosystems": sorted(detected),
        **_file_counts(paths),
        "missing_lockfiles": ecosystems.missing_lockfiles(paths, detected),
        "pinned_requirements": pinned_requirements,
        "linter_issues": linter_issues,
        "complexity": _complexity_metrics(scores),
    }


def _file_counts(paths: list[str]) -> dict:
    source_paths = [
        path for path in paths
        if PurePosixPath(path).suffix.lower() in ALL_SOURCE_EXTENSIONS
    ]
    test_paths = [path for path in source_paths if is_test_path(path)]
    ci_paths = [path for path in paths if is_ci_path(path)]
    production_count = len(source_paths) - len(test_paths)

    return {
        "source_files": len(source_paths),
        "test_files": len(test_paths),
        "test_ratio": round(len(test_paths) / production_count, 2) if production_count else 0.0,
        "ci_files": ci_paths,
        "has_ci": bool(ci_paths),
    }


def _complexity_metrics(scores: list[int]) -> dict:
    over_threshold = [score for score in scores if score > COMPLEXITY_THRESHOLD]

    return {
        "threshold": COMPLEXITY_THRESHOLD,
        "analyzed_functions": len(scores),
        "over_threshold": len(over_threshold),
        "max": max(scores, default=0),
        "average": round(sum(scores) / len(scores), 1) if scores else 0.0,
        "languages": ["python"],
    }


def _pinning_ratio(content: str) -> tuple[int, int]:
    total = 0
    pinned = 0

    for line in content.splitlines():
        stripped = line.strip()
        if IGNORED_REQUIREMENT.match(stripped):
            continue
        total += 1
        if PINNED_REQUIREMENT.match(stripped):
            pinned += 1

    return pinned, total


def _requirements_files(files: list[dict]) -> list[dict]:
    return [
        entry for entry in files
        if PurePosixPath(entry.get("path", "")).name == "requirements.txt"
    ]


def _unpinned_requirements(files: list[dict]) -> list[tuple[str, int, int]]:
    unpinned = []

    for entry in _requirements_files(files):
        pinned, total = _pinning_ratio(entry.get("content", ""))
        if total >= MIN_REQUIREMENTS_FOR_PINNING and pinned / total < PINNING_RATIO_THRESHOLD:
            unpinned.append((entry["path"], pinned, total))

    return unpinned


def _has_pinned_requirements(files: list[dict], unpinned: list[tuple[str, int, int]]) -> bool:
    unpinned_paths = {path for path, _, _ in unpinned}

    return any(
        entry["path"] not in unpinned_paths
        and _pinning_ratio(entry.get("content", ""))[1] >= MIN_REQUIREMENTS_FOR_PINNING
        for entry in _requirements_files(files)
    )


def _lockfile_findings(metrics: dict, language: str) -> list[dict]:
    findings = []

    for ecosystem in metrics["missing_lockfiles"]:
        softened = ecosystem == "python" and metrics["pinned_requirements"]
        rule, severity = LOCKFILE_VARIANTS[softened]

        findings.append(make_finding(
            AXIS,
            rule,
            severity,
            text(f"scan.{rule}.title", language, ecosystem=ecosystem),
            text(f"scan.{rule}.description", language, ecosystem=ecosystem),
            source="metrics",
            identity=ecosystem,
        ))

    return findings


def _metric_findings(
    metrics: dict,
    unpinned: list[tuple[str, int, int]],
    language: str,
) -> list[dict]:
    findings = []

    if metrics["source_files"] and not metrics["test_files"]:
        findings.append(make_finding(
            AXIS,
            "quality.no_tests",
            "medium",
            text("scan.quality.no_tests.title", language),
            text("scan.quality.no_tests.description", language, count=metrics["source_files"]),
            source="metrics",
        ))

    if metrics["source_files"] and not metrics["has_ci"]:
        findings.append(make_finding(
            AXIS,
            "quality.no_ci",
            "low",
            text("scan.quality.no_ci.title", language),
            text("scan.quality.no_ci.description", language),
            source="metrics",
        ))

    findings += _lockfile_findings(metrics, language)

    for path, pinned, total in unpinned:
        findings.append(make_finding(
            AXIS,
            "quality.unpinned_dependencies",
            "low",
            text("scan.quality.unpinned.title", language),
            text("scan.quality.unpinned.description", language, pinned=pinned, total=total),
            file_path=path,
            source="metrics",
        ))

    return findings
