import hashlib

SCAN_VERSION = 2

SEVERITY_ORDER = ("critical", "high", "medium", "low", "info")

LEGACY_SEVERITIES = {"info": "low"}

MAX_FINDINGS_PER_AXIS = 30

FINGERPRINT_LENGTH = 12
EMPTY_FINGERPRINT = "-"


def fingerprint(identity: str) -> str:
    normalized = " ".join(identity.split())
    if not normalized:
        return EMPTY_FINGERPRINT

    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:FINGERPRINT_LENGTH]


def build_id(axis: str, rule: str, file_path: str | None, content_fingerprint: str) -> str:
    return ":".join([axis, rule, file_path or "-", content_fingerprint])


def make_finding(
    axis: str,
    rule: str,
    severity: str,
    title: str,
    description: str,
    *,
    file_path: str | None = None,
    line: int | None = None,
    evidence: str = "",
    source: str = "scan",
    identity: str | None = None,
    context: str | None = None,
) -> dict:
    content_fingerprint = fingerprint(identity if identity is not None else evidence)

    return {
        "id": build_id(axis, rule, file_path, content_fingerprint),
        "axis": axis,
        "rule": rule,
        "severity": severity if severity in SEVERITY_ORDER else "low",
        "title": title,
        "description": description,
        "file_path": file_path,
        "line": line,
        "evidence": evidence,
        "locations": [{"line": line, "evidence": evidence}],
        "occurrences": 1,
        "source": source,
        "context": context,
    }


def _severity_rank(finding: dict) -> int:
    return SEVERITY_ORDER.index(finding["severity"])


def _location_key(location: dict) -> tuple:
    return location["line"], location["evidence"]


def _merged(findings: list[dict]) -> list[dict]:
    merged: dict[str, dict] = {}

    for finding in findings:
        known = merged.get(finding["id"])
        if known is None:
            merged[finding["id"]] = {**finding, "locations": list(finding["locations"])}
            continue

        seen = {_location_key(location) for location in known["locations"]}
        known["locations"].extend(
            location for location in finding["locations"]
            if _location_key(location) not in seen
        )

    for finding in merged.values():
        finding["occurrences"] = len(finding["locations"])

    return list(merged.values())


def axis_result(
    axis: str,
    findings: list[dict],
    *,
    metrics: dict | None = None,
    status: str | None = None,
    limit: int = MAX_FINDINGS_PER_AXIS,
) -> dict:
    unique = sorted(_merged(findings), key=_severity_rank)
    kept = unique[:limit]

    return {
        "axis": axis,
        "status": status or ("issues_found" if unique else "clean"),
        "findings": kept,
        "dropped": len(unique) - len(kept),
        "metrics": metrics or {},
    }


def unavailable(axis: str, reason: str, metrics: dict | None = None) -> dict:
    return {
        "axis": axis,
        "status": "unavailable",
        "findings": [],
        "dropped": 0,
        "metrics": metrics or {},
        "message": reason,
    }


def to_issue(finding: dict) -> dict:
    return {
        "severity": LEGACY_SEVERITIES.get(finding["severity"], finding["severity"]),
        "title": finding["title"],
        "rule": finding["rule"],
        "file_path": finding["file_path"] or "N/A",
        "description": finding["description"],
        "code_hint": finding["evidence"],
        "source": finding["source"],
        "occurrences": finding["occurrences"],
        "locations": finding["locations"],
    }


def severity_counts(findings: list[dict]) -> dict:
    counts = {severity: 0 for severity in SEVERITY_ORDER}
    for finding in findings:
        counts[finding["severity"]] += 1
    return counts
