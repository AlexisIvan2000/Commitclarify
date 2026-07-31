import asyncio
import logging

from core.language import DEFAULT_LANGUAGE, normalize, text
from services.ai import prompts
from services.ai.linters import run_eslint_on_files, run_ruff_on_files
from services.ai.llm import format_chunks, parse_response, generate
from services.rag.embeddings import get_embedding
from services.rag.indexer import retrieve_chunks

logger = logging.getLogger(__name__)


async def run_quality_check(
    collection_name: str,
    files: list[dict],
    language: str = DEFAULT_LANGUAGE,
) -> dict:
    language = normalize(language)
    logger.info(
        "Quality check demarree (collection=%s, %d fichiers, langue=%s)",
        collection_name, len(files), language,
    )

    query = "function class method definition implementation logic duplicate"
    embedding_task = get_embedding(query)
    ruff_task = run_ruff_on_files(files, language)
    eslint_task = run_eslint_on_files(files, language)

    embedding, ruff_issues, eslint_issues = await asyncio.gather(
        embedding_task, ruff_task, eslint_task
    )
    linter_issues = ruff_issues + eslint_issues
    logger.info("Linters: %d ruff + %d eslint issues", len(ruff_issues), len(eslint_issues))

    chunks = retrieve_chunks(collection_name, embedding, n_results=20)
    context = format_chunks(chunks)

    prompt = prompts.quality_check(context, language)

    raw = await generate(prompt)
    llm_result = parse_response(raw)
    llm_issues = llm_result.get("issues", [])
    for issue in llm_issues:
        issue["source"] = "llm"

    all_issues = linter_issues + llm_issues
    status = "issues_found" if all_issues else "clean"

    recommendations = []
    if ruff_issues:
        recommendations.append({
            "priority": "medium",
            "message": text("recommendation.ruff", language, count=len(ruff_issues)),
        })
    if eslint_issues:
        recommendations.append({
            "priority": "medium",
            "message": text("recommendation.eslint", language, count=len(eslint_issues)),
        })

    logger.info("Quality check terminee: %d ruff + %d eslint + %d llm = %d issues",
                len(ruff_issues), len(eslint_issues), len(llm_issues), len(all_issues))
    return {
        "status": status,
        "issues": all_issues,
        "recommendations": recommendations,
    }


async def run_readme_check(
    collection_name: str,
    readme_chunks: list[dict],
    language: str = DEFAULT_LANGUAGE,
) -> dict:
    language = normalize(language)
    logger.info(
        "README check demarree (collection=%s, %d chunks readme, langue=%s)",
        collection_name, len(readme_chunks), language,
    )

    if not readme_chunks:
        return {
            "status": "unavailable",
            "issues": [],
            "recommendations": [],
            "message": text("recommendation.no_readme", language),
        }

    query = "endpoint route function feature implementation"
    embedding = await get_embedding(query)
    chunks = retrieve_chunks(collection_name, embedding, n_results=8)

    readme_text = "\n\n".join([c["content"] for c in readme_chunks])
    code_context = format_chunks(chunks)

    prompt = prompts.readme_check(readme_text, code_context, language)

    raw = await generate(prompt)
    result = parse_response(raw)
    logger.info("README check terminee: %d issues", len(result.get("issues", [])))
    return result
