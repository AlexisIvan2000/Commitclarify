import logging
import re
from pathlib import Path

from core.language import DEFAULT_LANGUAGE, normalize, text
from services.scan.paths import is_test_path
from services.scan.report import axis_result, make_finding
from services.scan.sensitive import EXCLUDED_FILES, classify

logger = logging.getLogger(__name__)

AXIS = "secrets_detection"

SECRET_PATTERNS = [
    ("secret.openai_key",        r"sk-[a-zA-Z0-9_-]{20,}",             "critical"),
    ("secret.aws_key",           r"AKIA[0-9A-Z]{16}",                  "critical"),
    ("secret.github_token",      r"ghp_[a-zA-Z0-9]{36}",               "critical"),
    ("secret.slack_token",       r"xox[bp]-[a-zA-Z0-9-]+",             "critical"),
    ("secret.sendgrid_key",      r"SG\.[a-zA-Z0-9]{22,}",              "critical"),
    ("secret.private_key",       r"-----BEGIN[A-Z ]*PRIVATE KEY-----", "critical"),
    ("secret.connection_string", r"(postgresql|postgres|mysql|mongodb|redis|amqp|ftp|ssh)(\+\w+)?://[^:\s]+:[^@\s]+@[^/\s]+", "high"),
]

COMPILED_PATTERNS = [(key, re.compile(pattern), severity) for key, pattern, severity in SECRET_PATTERNS]

EXCLUDED_LINE_PATTERNS = re.compile(
    r"placeholder|your_|changeme|xxx|TODO|mock|fake|dummy|fixture",
    re.IGNORECASE,
)

MAX_EVIDENCE_LENGTH = 200


def scan_secrets(files: list[dict], language: str = DEFAULT_LANGUAGE) -> dict:
    language = normalize(language)

    findings = _committed_files(files, language) + _regex_matches(files, language)

    logger.info("Scan secrets: %d findings", len(findings))
    return axis_result(AXIS, findings)


def _committed_files(files: list[dict], language: str) -> list[dict]:
    findings = []

    for entry in files:
        path = entry.get("path", "")
        rule = classify(path)
        if not rule:
            continue

        findings.append(make_finding(
            AXIS,
            rule,
            "critical",
            text(rule, language, name=Path(path).name),
            text("committed.description", language),
            file_path=path,
            evidence=path,
            source="filename",
            context="test" if is_test_path(path) else None,
        ))

    return findings


def _regex_matches(files: list[dict], language: str) -> list[dict]:
    findings = []

    for entry in files:
        path = entry.get("path", "")
        content = entry.get("content", "")
        if not content:
            continue

        if Path(path).name in EXCLUDED_FILES:
            continue

        context = "test" if is_test_path(path) else None

        for number, line in enumerate(content.splitlines(), 1):
            if EXCLUDED_LINE_PATTERNS.search(line):
                continue

            for rule, pattern, severity in COMPILED_PATTERNS:
                match = pattern.search(line)
                if not match:
                    continue

                findings.append(make_finding(
                    AXIS,
                    rule,
                    severity,
                    text(rule, language),
                    text("secret.description", language, line=number),
                    file_path=path,
                    line=number,
                    evidence=line.strip()[:MAX_EVIDENCE_LENGTH],
                    source="regex",
                    identity=match.group(0),
                    context=context,
                ))
                break

    return findings
