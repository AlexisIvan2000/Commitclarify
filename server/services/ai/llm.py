import json
import re
import asyncio
import logging

from openai import AsyncOpenAI
from core.config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=OPENAI_API_KEY)
MODEL = "gpt-4o-mini"

MAX_RETRIES = 3


def format_chunks(chunks: list[dict]) -> str:
    """Formate les chunks pour injection dans un prompt."""
    return "\n\n".join([
        f"### {c['metadata']['file_path']}\n{c['content']}"
        for c in chunks
    ])


REQUIRED_ISSUE_FIELDS = {"severity", "title", "file_path", "description"}


def parse_response(raw: str) -> dict:
    """Parse la reponse JSON du LLM, valide le schema, filtre les issues incompletes."""
    clean = re.sub(r"```json|```", "", raw).strip()
    try:
        result = json.loads(clean)
    except json.JSONDecodeError:
        logger.warning("Impossible de parser la reponse LLM: %s", clean[:200])
        return {
            "status": "error",
            "issues": [],
            "recommendations": [],
            "error": "Reponse LLM invalide (JSON malformed)",
        }

    # Validation de schema — filtrer les issues avec des champs manquants
    raw_issues = result.get("issues", [])
    valid_issues = []
    for issue in raw_issues:
        missing = REQUIRED_ISSUE_FIELDS - set(issue.keys())
        if missing:
            logger.warning("Issue LLM filtree (champs manquants: %s): %s",
                           ", ".join(missing), issue.get("title", "?"))
            continue
        valid_issues.append(issue)

    result["issues"] = valid_issues
    return result

# Appel au LLM avec retry automatique sur les erreurs de rate limit.
async def generate(prompt: str, max_tokens: int = 1024) -> str:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = await client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content
            logger.debug("LLM reponse recue (%d chars)", len(content) if content else 0)
            return content
        except Exception as e:
            if "429" in str(e) and attempt < MAX_RETRIES:
                wait = attempt * 15
                logger.warning("Rate limit atteint, retry dans %ds (tentative %d/%d)", wait, attempt, MAX_RETRIES)
                await asyncio.sleep(wait)
            else:
                raise