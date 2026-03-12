import logging

from services.ai.llm import format_chunks, parse_response, generate
from services.rag.embeddings import get_embedding
from services.rag.indexer import retrieve_chunks

logger = logging.getLogger(__name__)


async def run_secrets_detection(collection_name: str) -> dict:
    """Detecte les secrets et donnees sensibles hardcodes dans un repo."""
    logger.info("Secrets detection demarree (collection=%s)", collection_name)
    query = "hardcoded API key secret token password credential private key"
    embedding = await get_embedding(query)
    chunks = retrieve_chunks(collection_name, query, embedding, n_results=10)
    context = format_chunks(chunks)

    prompt = f"""Tu es un auditeur de securite strict et precis.

Analyse UNIQUEMENT les extraits de code ci-dessous. Detecte les secrets REELLEMENT hardcodes :
- Cles API avec une vraie valeur (ex: "sk-abc123...", "AKIA...")
- Mots de passe en clair dans le code (ex: password = "monpassword")
- Tokens avec une vraie valeur assignee directement
- Cles privees ou certificats colles dans le code

REGLES STRICTES :
- NE SIGNALE PAS les variables qui chargent depuis os.environ, os.getenv, process.env, dotenv
- NE SIGNALE PAS les placeholders (ex: "your-api-key-here", "xxx", "changeme")
- NE SIGNALE PAS les cles de test evidentes (ex: "test-secret-key", "secret" dans un fichier de test)
- NE SIGNALE PAS les URLs publiques d'API
- NE SUPPOSE RIEN qui n'est pas dans le code fourni
- Chaque issue DOIT citer un extrait exact du code comme preuve dans "code_hint" (copiable pour Ctrl+F)
- Si tu n'es pas certain a 90%+, NE SIGNALE PAS

{context}

Reponds UNIQUEMENT en JSON valide, sans balises markdown. Tout le contenu (titres, descriptions, recommandations) DOIT etre en francais.
Si aucun probleme reel : "status" = "clean" et "issues" = [].

FORMAT :
{{
  "status": "<issues_found|clean>",
  "issues": [
    {{
      "severity": "<critical|high|medium|low>",
      "title": "<titre court>",
      "file_path": "<chemin du fichier>",
      "description": "<explication claire>",
      "code_hint": "<extrait exact du code concerne, copiable pour recherche>"
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
    logger.info("Secrets detection terminee: %d issues", len(result.get("issues", [])))
    return result


async def run_gitignore_check(collection_name: str, has_gitignore: bool) -> dict:
    """Verifie que les fichiers sensibles sont bien exclus du depot via un .gitignore."""
    logger.info("Gitignore check demarree (has_gitignore=%s)", has_gitignore)
    if not has_gitignore:
        return {
            "status": "issues_found",
            "issues": [
                {
                    "severity": "high",
                    "title": "Aucun fichier .gitignore detecte",
                    "file_path": "N/A",
                    "description": "Le projet ne contient pas de .gitignore. Tous les fichiers risquent d'etre versionnes.",
                    "code_hint": ""
                }
            ],
            "recommendations": [
                {
                    "priority": "high",
                    "message": "Creer un fichier .gitignore a la racine du projet et y ajouter les fichiers sensibles (ex: .env, config.yaml, etc.)"
                }
            ]
        }

    query = "gitignore env secrets sensitive files excluded"
    embedding = await get_embedding(query)
    chunks = retrieve_chunks(collection_name, query, embedding, n_results=10)
    context = format_chunks(chunks)

    prompt = f"""Tu es un auditeur de securite strict et precis.

Voici le contenu du .gitignore et des fichiers de configuration du projet :

{context}

Verifie que ces fichiers sensibles sont bien exclus :
- .env et ses variantes (.env.local, .env.production, etc.)
- Fichiers de cles (*.key, *.pem, *.p12, *.pfx)
- Fichiers secrets (secrets.*, credentials.*)
- Dossiers de dependances (node_modules/, venv/, __pycache__/, etc.)

REGLES STRICTES :
- Base-toi UNIQUEMENT sur le contenu reel du .gitignore fourni
- NE SUPPOSE PAS l'existence de fichiers qui ne sont pas mentionnes dans le code
- Si le .gitignore couvre les cas standards, reponds "clean"

Reponds UNIQUEMENT en JSON valide, sans balises markdown. Tout le contenu (titres, descriptions, recommandations) DOIT etre en francais.
Si tout est correct : "status" = "clean" et "issues" = [].

FORMAT :
{{
  "status": "<issues_found|clean>",
  "issues": [
    {{
      "severity": "<critical|high|medium|low>",
      "title": "<titre court>",
      "file_path": ".gitignore",
      "description": "<ce qui manque concretement>",
      "code_hint": ""
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
    logger.info("Gitignore check terminee: %d issues", len(result.get("issues", [])))
    return result
