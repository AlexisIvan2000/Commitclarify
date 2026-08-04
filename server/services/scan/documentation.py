import logging
import posixpath
import re
from pathlib import PurePosixPath

from core.file_rules import ALLOWED_EXTENSIONS, ALLOWED_FILENAMES
from core.language import DEFAULT_LANGUAGE, normalize, text
from services.scan.paths import is_test_path
from services.scan.report import axis_result, make_finding, unavailable

logger = logging.getLogger(__name__)

AXIS = "readme_check"

MARKDOWN_EXTENSIONS = {".md", ".mdx", ".rst"}

ENV_EXAMPLE_NAMES = {
    ".env.example", ".env.sample", ".env.template", ".env.local.example", ".env.dist",
}

LINK_PATTERN = re.compile(r"!?\[[^\]]*\]\(\s*<?([^)>\s]+)")
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "tel:", "data:", "ftp://", "//")

ENV_PATTERNS = [
    re.compile(r"os\.getenv\(\s*['\"]([A-Za-z0-9_]+)['\"]"),
    re.compile(r"os\.environ\.get\(\s*['\"]([A-Za-z0-9_]+)['\"]"),
    re.compile(r"os\.environ\[\s*['\"]([A-Za-z0-9_]+)['\"]\s*\]"),
    re.compile(r"process\.env\.([A-Za-z0-9_]+)"),
    re.compile(r"process\.env\[\s*['\"]([A-Za-z0-9_]+)['\"]\s*\]"),
    re.compile(r"import\.meta\.env\.([A-Za-z0-9_]+)"),
    re.compile(r"ENV\[\s*['\"]([A-Za-z0-9_]+)['\"]\s*\]"),
]

ENV_NAME_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{2,}$")
ENV_DECLARATION = re.compile(r"^\s*(?:export\s+)?([A-Za-z0-9_]+)\s*=")
MARKDOWN_TOKEN = re.compile(r"\b[A-Z][A-Z0-9_]{2,}\b")

PLATFORM_ENV = {
    "NODE_ENV", "PORT", "PATH", "HOME", "PWD", "USER", "LANG", "TZ", "HOSTNAME",
    "CI", "PYTHONPATH", "PYTHONUNBUFFERED", "VIRTUAL_ENV", "TMPDIR", "SHELL",
    "MODE", "BASE_URL", "DEV", "PROD", "SSR",
}

MIN_ENV_VARS_FOR_EXAMPLE = 3


def scan_documentation(
    files: list[dict],
    language: str = DEFAULT_LANGUAGE,
    tracked_paths: list[str] | None = None,
) -> dict:
    language = normalize(language)

    documents = [
        entry for entry in files
        if PurePosixPath(entry.get("path", "")).suffix.lower() in MARKDOWN_EXTENSIONS
    ]
    if not documents:
        return unavailable(AXIS, text("recommendation.no_readme", language))

    sample = {entry.get("path", "") for entry in files if entry.get("path")}
    tracked = sample if tracked_paths is None else set(tracked_paths)
    used = _env_usage(files)
    declared = _declared_env(files)
    has_env_example = _has_env_example(tracked)

    findings = _link_findings(documents, tracked, language)
    findings += _env_findings(documents, used, declared, has_env_example, language)

    metrics = {
        "documents": len(documents),
        "env_used": len(used),
        "env_declared": len(declared),
        "has_env_example": has_env_example,
    }

    logger.info("Scan documentation: %d findings", len(findings))
    return axis_result(AXIS, findings, metrics=metrics)


def _has_env_example(paths: set[str]) -> bool:
    return any(PurePosixPath(path).name in ENV_EXAMPLE_NAMES for path in paths)


def _resolve(document_path: str, target: str) -> str | None:
    cleaned = target.split("#")[0].split("?")[0].strip()
    if not cleaned or cleaned.lower().startswith(EXTERNAL_PREFIXES):
        return None

    if cleaned.startswith("/"):
        resolved = posixpath.normpath(cleaned.lstrip("/"))
    else:
        parent = str(PurePosixPath(document_path).parent)
        base = "" if parent == "." else parent
        resolved = posixpath.normpath(posixpath.join(base, cleaned))

    if resolved in (".", "", "/") or resolved.startswith(".."):
        return None

    return resolved


def _is_checkable(candidate: str) -> bool:
    path = PurePosixPath(candidate)
    if path.name in ALLOWED_FILENAMES:
        return True

    suffix = path.suffix.lower()
    return bool(suffix) and suffix in ALLOWED_EXTENSIONS


def _link_findings(documents: list[dict], tracked: set[str], language: str) -> list[dict]:
    findings = []

    for document in documents:
        path = document.get("path", "")

        for number, line in enumerate(document.get("content", "").splitlines(), 1):
            for target in LINK_PATTERN.findall(line):
                candidate = _resolve(path, target)
                if not candidate or candidate in tracked:
                    continue
                if not _is_checkable(candidate):
                    continue

                findings.append(make_finding(
                    AXIS,
                    "docs.broken_link",
                    "medium",
                    text("scan.docs.broken_link.title", language, target=target),
                    text("scan.docs.broken_link.description", language, target=candidate, line=number),
                    file_path=path,
                    line=number,
                    evidence=target,
                    source="links",
                    identity=candidate,
                ))

    return findings


def _env_usage(files: list[dict]) -> dict[str, tuple[str, int]]:
    usage: dict[str, tuple[str, int]] = {}

    for entry in files:
        path = entry.get("path", "")
        if PurePosixPath(path).suffix.lower() in MARKDOWN_EXTENSIONS or is_test_path(path):
            continue

        for number, line in enumerate(entry.get("content", "").splitlines(), 1):
            for pattern in ENV_PATTERNS:
                for name in pattern.findall(line):
                    if ENV_NAME_PATTERN.match(name) and name not in usage:
                        usage[name] = (path, number)

    return usage


def _declared_env(files: list[dict]) -> set[str]:
    declared = set()

    for entry in files:
        if PurePosixPath(entry.get("path", "")).name not in ENV_EXAMPLE_NAMES:
            continue

        for line in entry.get("content", "").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            match = ENV_DECLARATION.match(stripped)
            if match and ENV_NAME_PATTERN.match(match.group(1)):
                declared.add(match.group(1))

    return declared


def _mentioned_in_docs(documents: list[dict]) -> set[str]:
    mentioned = set()

    for document in documents:
        mentioned |= set(MARKDOWN_TOKEN.findall(document.get("content", "")))

    return mentioned


def _env_findings(
    documents: list[dict],
    used: dict[str, tuple[str, int]],
    declared: set[str],
    has_env_example: bool,
    language: str,
) -> list[dict]:
    findings = []
    documented = declared | _mentioned_in_docs(documents)

    for name in sorted(set(used) - documented - PLATFORM_ENV):
        path, number = used[name]
        findings.append(make_finding(
            AXIS,
            "docs.undocumented_env",
            "medium",
            text("scan.docs.undocumented_env.title", language, name=name),
            text("scan.docs.undocumented_env.description", language, name=name, line=number),
            file_path=path,
            line=number,
            evidence=name,
            source="env",
            identity=name,
        ))

    for name in sorted(declared - set(used) - PLATFORM_ENV):
        findings.append(make_finding(
            AXIS,
            "docs.unused_env",
            "low",
            text("scan.docs.unused_env.title", language, name=name),
            text("scan.docs.unused_env.description", language, name=name),
            evidence=name,
            source="env",
            identity=name,
        ))

    if len(used) >= MIN_ENV_VARS_FOR_EXAMPLE and not has_env_example:
        findings.append(make_finding(
            AXIS,
            "docs.no_env_example",
            "medium",
            text("scan.docs.no_env_example.title", language),
            text("scan.docs.no_env_example.description", language, count=len(used)),
            source="env",
        ))

    return findings
