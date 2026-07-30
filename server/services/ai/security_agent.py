import logging
import re
from pathlib import Path

from services.ai.llm import format_chunks, parse_response, generate
from services.rag.embeddings import get_embedding
from services.rag.indexer import retrieve_chunks

logger = logging.getLogger(__name__)


SECRET_PATTERNS = [
    ("Cle OpenAI exposee",          r"sk-[a-zA-Z0-9_-]{20,}",                   "critical"),
    ("Cle AWS Access Key exposee",  r"AKIA[0-9A-Z]{16}",                        "critical"),
    ("Token GitHub expose",         r"ghp_[a-zA-Z0-9]{36}",                     "critical"),
    ("Token Slack expose",          r"xox[bp]-[a-zA-Z0-9-]+",                   "critical"),
    ("Cle SendGrid exposee",        r"SG\.[a-zA-Z0-9]{22,}",                    "critical"),
    ("Cle privee dans le code",     r"-----BEGIN[A-Z ]*PRIVATE KEY-----",       "critical"),
    ("String de connexion exposee", r"(postgresql|postgres|mysql|mongodb|redis|amqp|ftp|ssh)(\+\w+)?://[^:\s]+:[^@\s]+@[^/\s]+", "high"),
]

EXCLUDED_FILES = {
    ".env.example", ".env.sample", ".env.template", ".env.local.example", ".env.dist",
}
EXCLUDED_FILE_PATTERNS = re.compile(r"test_|_test\.|\.test\.|spec\.", re.IGNORECASE)
EXCLUDED_LINE_PATTERNS = re.compile(
    r'placeholder|your_|changeme|xxx|TODO|mock|fake|dummy|fixture',
    re.IGNORECASE,
)

COMMITTED_SECRET_FILES = {
    ".env": "Fichier .env commite dans le depot",
    ".env.local": "Fichier .env.local commite dans le depot",
    ".env.dev": "Fichier .env.dev commite dans le depot",
    ".env.development": "Fichier .env.development commite dans le depot",
    ".env.staging": "Fichier .env.staging commite dans le depot",
    ".env.prod": "Fichier .env.prod commite dans le depot",
    ".env.production": "Fichier .env.production commite dans le depot",
    ".env.test": "Fichier .env.test commite dans le depot",
    ".env.backup": "Sauvegarde de fichier .env commitee",
    ".env.old": "Ancien fichier .env commite",
    ".netrc": "Fichier .netrc (identifiants reseau) commite",
    ".pgpass": "Fichier .pgpass (mot de passe PostgreSQL) commite",
    "id_rsa": "Cle privee SSH commitee",
    "id_dsa": "Cle privee SSH commitee",
    "id_ecdsa": "Cle privee SSH commitee",
    "id_ed25519": "Cle privee SSH commitee",
    "credentials": "Fichier d'identifiants commite",
    "secrets": "Fichier de secrets commite",
    "service-account.json": "Cle de compte de service Google commitee",
    "serviceAccountKey.json": "Cle de compte de service Google commitee",
    "terraform.tfvars": "Variables Terraform commitees (contiennent souvent des secrets)",
    "google-services.json": "Configuration Google Services commitee",
}

COMMITTED_SECRET_SUFFIXES = {
    ".pem": "Certificat ou cle privee au format PEM commite",
    ".key": "Fichier de cle commite",
    ".p12": "Conteneur de certificat PKCS#12 commite",
    ".pfx": "Conteneur de certificat PFX commite",
    ".jks": "Keystore Java commite",
    ".keystore": "Keystore commite",
    ".ppk": "Cle privee PuTTY commitee",
}


def _scan_committed_secret_files(files: list[dict]) -> list[dict]:
    issues = []

    for f in files:
        path = f.get("path", "")
        if not path:
            continue

        name = Path(path).name
        if name in EXCLUDED_FILES:
            continue

        title = COMMITTED_SECRET_FILES.get(name) or COMMITTED_SECRET_SUFFIXES.get(
            Path(path).suffix.lower()
        )
        if not title:
            continue

        issues.append({
            "severity": "critical",
            "title": title,
            "file_path": path,
            "description": (
                "Ce type de fichier ne doit jamais etre versionne : il contient des secrets "
                "par nature. Retirez-le de l'historique Git et ajoutez-le au .gitignore."
            ),
            "code_hint": path,
            "source": "filename",
        })

    logger.info("Scan fichiers sensibles: %d issues", len(issues))
    return issues[:15]


def _scan_secrets_regex(files: list[dict]) -> list[dict]:
    issues = []

    for f in files:
        path = f.get("path", "")
        content = f.get("content", "")
        if not content:
            continue

        filename = Path(path).name
        if filename in EXCLUDED_FILES:
            continue
        if EXCLUDED_FILE_PATTERNS.search(filename):
            continue

        for line_num, line in enumerate(content.splitlines(), 1):
            if EXCLUDED_LINE_PATTERNS.search(line):
                continue

            for title, pattern, severity in SECRET_PATTERNS:
                if re.search(pattern, line):
                    issues.append({
                        "severity": severity,
                        "title": title,
                        "file_path": path,
                        "description": f"Ligne {line_num} : secret detecte par scan automatique",
                        "code_hint": line.strip()[:200],
                        "source": "regex",
                    })
                    break  

    logger.info("Regex secrets scan: %d issues", len(issues))
    return issues[:15]


async def run_secrets_detection(collection_name: str, files: list[dict]) -> dict:
    logger.info("Secrets detection demarree (collection=%s)", collection_name)

    query = "hardcoded API key secret token password credential private key"

    filename_issues = _scan_committed_secret_files(files)
    regex_issues = _scan_secrets_regex(files)
    embedding = await get_embedding(query)

    chunks = retrieve_chunks(collection_name, embedding, n_results=20)
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
- NE SIGNALE PAS les fichiers de test (test_, _test, spec., fixtures, mocks) — les fausses cles dans les tests sont intentionnelles
- NE SIGNALE PAS les definitions de regex ou patterns de detection (ex: r"AKIA...", r"sk-...")
- NE SIGNALE PAS les URLs publiques d'API
- EN REVANCHE, dans un fichier .env versionne (hors .env.example), toute valeur litterale non placeholder EST un secret reel : signale-la
- NE SUPPOSE RIEN qui n'est pas dans le code fourni
- Le "file_path" DOIT etre exactement celui indique dans les extraits fournis — ne jamais inventer un chemin
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
    llm_result = parse_response(raw)
    llm_issues = llm_result.get("issues", [])
    for issue in llm_issues:
        issue["source"] = "llm"

  
    all_issues = filename_issues + regex_issues + llm_issues
    status = "issues_found" if all_issues else "clean"

    recommendations = llm_result.get("recommendations", [])
    if regex_issues:
        recommendations.insert(0, {
            "priority": "high",
            "message": f"Scan automatique : {len(regex_issues)} secret(s) detecte(s) par pattern matching — a corriger en priorite"
        })
    if filename_issues:
        recommendations.insert(0, {
            "priority": "high",
            "message": (
                f"{len(filename_issues)} fichier(s) sensible(s) versionne(s) : retirez-les de l'index "
                "(git rm --cached), ajoutez-les au .gitignore, puis faites tourner les cles concernees"
            )
        })

    logger.info("Secrets detection terminee: %d fichiers + %d regex + %d llm = %d issues",
                len(filename_issues), len(regex_issues), len(llm_issues), len(all_issues))
    return {
        "status": status,
        "issues": all_issues,
        "recommendations": recommendations,
    }


async def run_gitignore_check(collection_name: str, has_gitignore: bool) -> dict:
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
    chunks = retrieve_chunks(collection_name, embedding, n_results=10)
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
