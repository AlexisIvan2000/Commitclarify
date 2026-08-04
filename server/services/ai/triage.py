import logging

from core.language import DEFAULT_LANGUAGE, normalize
from services.ai import prompts
from services.ai.llm import generate
from services.ai.validation import apply_verdicts, parse_verdicts

logger = logging.getLogger(__name__)

MAX_FINDINGS_PER_CALL = 30

BUILDERS = {
    "secrets_detection": prompts.secrets_triage,
    "gitignore_check": prompts.gitignore_triage,
}


def allowed_ids(issues: list[dict]) -> set[str]:
    return {issue["id"] for issue in issues if issue.get("id")}


async def triage_axis(
    axis: str,
    issues: list[dict],
    language: str = DEFAULT_LANGUAGE,
) -> dict:
    language = normalize(language)
    identifiers = allowed_ids(issues)

    if not identifiers:
        return {"status": "clean", "issues": issues, "verdicts": [], "recommendations": []}

    submitted = [issue for issue in issues if issue.get("id")][:MAX_FINDINGS_PER_CALL]
    prompt = BUILDERS[axis](submitted, language)

    raw = await generate(prompt, max_tokens=2048)
    verdicts = parse_verdicts(raw, allowed_ids(submitted))

    if verdicts is None:
        logger.error(
            "Tri %s rejete : les detections restent affichees sans verdict", axis,
        )
        return {
            "status": "error",
            "issues": issues,
            "verdicts": [],
            "recommendations": [],
            "error": "Tri LLM invalide",
        }

    triaged = apply_verdicts(issues, verdicts)
    logger.info(
        "Tri %s: %d verdicts sur %d detections soumises",
        axis, len(verdicts), len(submitted),
    )

    return {
        "status": "issues_found" if triaged else "clean",
        "issues": triaged,
        "verdicts": verdicts,
        "recommendations": [],
    }
