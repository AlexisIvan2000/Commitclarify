import logging
from pathlib import PurePosixPath

import pathspec

from core.language import DEFAULT_LANGUAGE, normalize, text
from services.scan import ecosystems
from services.scan.report import axis_result, make_finding
from services.scan.sensitive import classify

logger = logging.getLogger(__name__)

AXIS = "gitignore_check"

GITIGNORE_NAME = ".gitignore"

ENV_SAMPLE = ".env"


def scan_gitignore(
    files: list[dict],
    language: str = DEFAULT_LANGUAGE,
    tracked_paths: list[str] | None = None,
) -> dict:
    language = normalize(language)

    paths = tracked_paths if tracked_paths is not None else [f.get("path", "") for f in files]
    paths = [path for path in paths if path]

    specs = _build_specs(files)
    if not specs:
        return axis_result(AXIS, [_missing_finding(language)], metrics={"gitignore_files": 0})

    findings = _tracked_findings(specs, paths, language)
    findings += _rule_findings(specs, paths, language)

    metrics = {
        "gitignore_files": len(specs),
        "rules": _rule_count(files),
        "tracked_but_ignored": sum(1 for f in findings if f["rule"] == "gitignore.tracked_ignored"),
        "unprotected": sum(1 for f in findings if f["rule"] == "gitignore.unprotected"),
    }

    logger.info("Scan gitignore: %d findings", len(findings))
    return axis_result(AXIS, findings, metrics=metrics)


def _missing_finding(language: str) -> dict:
    return make_finding(
        AXIS,
        "gitignore.missing",
        "high",
        text("gitignore.missing.title", language),
        text("gitignore.missing.description", language),
    )


def _build_specs(files: list[dict]) -> list[tuple[str, pathspec.GitIgnoreSpec]]:
    specs = []

    for entry in files:
        path = entry.get("path", "")
        if PurePosixPath(path).name != GITIGNORE_NAME:
            continue

        parent = str(PurePosixPath(path).parent)
        base = "" if parent == "." else f"{parent}/"
        lines = entry.get("content", "").splitlines()
        specs.append((base, pathspec.GitIgnoreSpec.from_lines(lines)))

    return specs


def _rule_count(files: list[dict]) -> int:
    total = 0

    for entry in files:
        if PurePosixPath(entry.get("path", "")).name != GITIGNORE_NAME:
            continue
        for line in entry.get("content", "").splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                total += 1

    return total


def _matches(specs: list[tuple[str, pathspec.GitIgnoreSpec]], candidate: str) -> bool:
    return any(
        candidate.startswith(base) and spec.match_file(candidate[len(base):])
        for base, spec in specs
    )


def _ancestor_directories(path: str) -> list[str]:
    parts = path.split("/")[:-1]
    return ["/".join(parts[:depth + 1]) + "/" for depth in range(len(parts))]


def _is_ignored(specs: list[tuple[str, pathspec.GitIgnoreSpec]], path: str) -> bool:
    if any(_matches(specs, ancestor) for ancestor in _ancestor_directories(path)):
        return True

    return _matches(specs, path)


def _tracked_findings(
    specs: list[tuple[str, pathspec.GitIgnoreSpec]],
    paths: list[str],
    language: str,
) -> list[dict]:
    findings = []

    for path in paths:
        name = PurePosixPath(path).name
        sensitive = classify(path)
        ignored = _is_ignored(specs, path)

        if sensitive and not ignored:
            findings.append(make_finding(
                AXIS,
                "gitignore.unprotected",
                "critical",
                text("scan.gitignore.unprotected.title", language, name=name),
                text("scan.gitignore.unprotected.description", language, name=name),
                file_path=path,
                evidence=path,
            ))
        elif ignored and name != GITIGNORE_NAME:
            findings.append(make_finding(
                AXIS,
                "gitignore.tracked_ignored",
                "high" if sensitive else "medium",
                text("scan.gitignore.tracked_ignored.title", language, name=name),
                text("scan.gitignore.tracked_ignored.description", language, name=name),
                file_path=path,
                evidence=path,
            ))

    return findings


def _rule_findings(
    specs: list[tuple[str, pathspec.GitIgnoreSpec]],
    paths: list[str],
    language: str,
) -> list[dict]:
    findings = []
    expected = {ENV_SAMPLE: ENV_SAMPLE}

    for ecosystem in sorted(ecosystems.detect(paths)):
        for sample in ecosystems.DEPENDENCY_SAMPLES.get(ecosystem, ()):
            expected.setdefault(sample.split("/")[0], sample)

    for label, sample in expected.items():
        if any(_is_ignored(specs, f"{base}{sample}") for base, _ in specs):
            continue

        findings.append(make_finding(
            AXIS,
            "gitignore.rule_missing",
            "medium",
            text("scan.gitignore.rule_missing.title", language, rule=label),
            text("scan.gitignore.rule_missing.description", language, rule=label),
            evidence=label,
        ))

    return findings
