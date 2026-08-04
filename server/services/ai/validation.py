import json
import logging
import re

logger = logging.getLogger(__name__)

CONFIRMED = "confirmed"
FALSE_POSITIVE = "false_positive"
UNCERTAIN = "uncertain"

VERDICTS = (CONFIRMED, FALSE_POSITIVE, UNCERTAIN)

DEMOTED_SEVERITY = "info"

MAX_REASON_LENGTH = 400

FENCE = re.compile(r"```(?:json)?|```")


def parse_json(raw: str) -> dict | None:
    if not raw:
        return None

    try:
        parsed = json.loads(FENCE.sub("", raw).strip())
    except json.JSONDecodeError:
        logger.warning("Reponse LLM illisible: %s", (raw or "")[:200])
        return None

    return parsed if isinstance(parsed, dict) else None


def parse_verdicts(raw: str, allowed_ids: set[str]) -> list[dict] | None:
    payload = parse_json(raw)
    if payload is None:
        return None

    entries = payload.get("verdicts")
    if not isinstance(entries, list):
        logger.warning("Reponse de tri sans liste 'verdicts'")
        return None

    accepted = {}

    for entry in entries:
        if not isinstance(entry, dict):
            logger.warning("Entree de tri ignoree: forme invalide")
            return None

        finding_id = entry.get("finding_id")
        verdict = entry.get("verdict")

        if finding_id not in allowed_ids:
            logger.error(
                "Tri rejete : identifiant inconnu %r renvoye par le LLM", finding_id,
            )
            return None

        if verdict not in VERDICTS:
            logger.error("Tri rejete : verdict inconnu %r", verdict)
            return None

        accepted.setdefault(finding_id, {
            "finding_id": finding_id,
            "verdict": verdict,
            "reason": str(entry.get("reason", ""))[:MAX_REASON_LENGTH],
        })

    return list(accepted.values())


def apply_verdicts(issues: list[dict], verdicts: list[dict]) -> list[dict]:
    by_id = {verdict["finding_id"]: verdict for verdict in verdicts}
    triaged = []

    for issue in issues:
        verdict = by_id.get(issue.get("id"))
        if verdict is None:
            triaged.append(issue)
            continue

        decided = {
            **issue,
            "verdict": verdict["verdict"],
            "verdict_reason": verdict["reason"],
        }
        if verdict["verdict"] == FALSE_POSITIVE:
            decided["original_severity"] = issue["severity"]
            decided["severity"] = DEMOTED_SEVERITY

        triaged.append(decided)

    return triaged


def reject_invented_paths(issues: list[dict], known_paths: set[str]) -> tuple[list[dict], int]:
    kept = []
    rejected = 0

    for issue in issues:
        path = issue.get("file_path")
        if path in known_paths:
            kept.append(issue)
            continue

        rejected += 1
        logger.warning(
            "Issue LLM rejetee : chemin inexistant %r (regle=%s)",
            path, issue.get("rule", issue.get("title", "?")),
        )

    return kept, rejected
