import asyncio
import logging

from core.language import DEFAULT_LANGUAGE, PROMPT_OUTPUT_RULE, normalize, text
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

    prompt = f"""Tu es un expert en qualite logicielle strict et precis.

Analyse ces extraits de code et detecte UNIQUEMENT :
- Code duplique : deux blocs quasi-identiques dans des fichiers differents
- Logique morte ou code inatteignable

REGLES STRICTES :
- NE SIGNALE PAS les imports inutilises, bare except, fonctions longues, trop de parametres, variables inutilisees, == vs === — c'est deja couvert par les linters (Ruff/ESLint)
- Chaque issue DOIT citer le fichier exact ("file_path") ET un extrait du code concerne dans "code_hint" (copiable pour Ctrl+F)
- NE SIGNALE PAS les choix d'architecture ou de design
- NE SIGNALE PAS les fichiers de config ou de test
- NE SUPPOSE RIEN qui n'est pas dans le code fourni
- Si tu n'es pas certain a 90%+, NE SIGNALE PAS
- Maximum 3 issues

{context}

{PROMPT_OUTPUT_RULE[language]}
Si aucun probleme reel : "issues" = [].

FORMAT :
{{
  "issues": [
    {{
      "severity": "<high|medium|low>",
      "title": "<titre court>",
      "file_path": "<chemin exact du fichier>",
      "description": "<explication claire et courte>",
      "code_hint": "<extrait exact du code concerne, copiable pour recherche>"
    }}
  ]
}}"""

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

    prompt = f"""Tu es un expert en qualite logicielle strict et precis.

Voici le README du projet :
{readme_text}

Voici des extraits du code :
{code_context}

Compare les deux et detecte UNIQUEMENT les incoherences reelles :
- Features ou endpoints mentionnes dans le README mais ABSENTS du code
- Instructions d'installation incorrectes (mauvais nom de package, commande erronee)
- Documentation qui contredit clairement le code

REGLES STRICTES :
- NE SIGNALE PAS les features du code absentes du README (le README n'a pas a tout documenter)
- NE SIGNALE PAS les ameliorations possibles du README
- NE SUPPOSE PAS — base-toi uniquement sur ce qui est ecrit
- Si le README est globalement correct, reponds "clean"

{PROMPT_OUTPUT_RULE[language]}
Si tout est coherent : "status" = "clean" et "issues" = [].

FORMAT :
{{
  "status": "<issues_found|clean>",
  "issues": [
    {{
      "severity": "<critical|high|medium|low>",
      "title": "<titre court>",
      "file_path": "README.md",
      "description": "<ce qui est incoherent>",
      "code_hint": "<extrait exact du README concerne, copiable pour recherche>"
    }}
  ],
  "recommendations": [
    {{
      "priority": "<high|medium|low>",
      "message": "<recommandation actionnable>"
    }}
  ]
}}"""

    raw = await generate(prompt)
    result = parse_response(raw)
    logger.info("README check terminee: %d issues", len(result.get("issues", [])))
    return result
