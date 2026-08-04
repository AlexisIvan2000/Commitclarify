import asyncio
import logging

from core.language import DEFAULT_LANGUAGE, normalize
from services.scan.documentation import scan_documentation
from services.scan.gitignore import scan_gitignore
from services.scan.quality import scan_quality
from services.scan.report import SCAN_VERSION, severity_counts, to_issue
from services.scan.secrets import scan_secrets

logger = logging.getLogger(__name__)

AXES = ("secrets_detection", "gitignore_check", "quality_check", "readme_check")


async def run_scan(
    files: list[dict],
    language: str = DEFAULT_LANGUAGE,
    tracked_paths: list[str] | None = None,
    coverage: dict | None = None,
) -> dict:
    language = normalize(language)

    quality_task = asyncio.create_task(scan_quality(files, language))

    results = {
        "secrets_detection": scan_secrets(files, language),
        "gitignore_check": scan_gitignore(files, language, tracked_paths),
        "readme_check": scan_documentation(files, language),
    }
    results["quality_check"] = await quality_task

    axes = {axis: results[axis] for axis in AXES}
    findings = all_findings(axes)

    logger.info(
        "Scan termine: %d findings sur %d fichiers",
        len(findings), len(files),
    )

    return {
        "scan_version": SCAN_VERSION,
        "language": language,
        "coverage": coverage or {},
        "axes": axes,
        "summary": {
            "findings": len(findings),
            "dropped": sum(result["dropped"] for result in axes.values()),
            "by_severity": severity_counts(findings),
            "axes_with_issues": [
                axis for axis, result in axes.items() if result["status"] == "issues_found"
            ],
        },
    }


def all_findings(axes: dict) -> list[dict]:
    return [finding for result in axes.values() for finding in result["findings"]]


def findings_index(scan: dict) -> dict[str, dict]:
    return {finding["id"]: finding for finding in all_findings(scan["axes"])}


def to_issues(axis_result: dict) -> list[dict]:
    return [to_issue(finding) for finding in axis_result["findings"]]
