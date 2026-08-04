import logging
import re
from pathlib import Path

from core.language import DEFAULT_LANGUAGE, normalize, text
from services.ai import prompts
from services.ai.llm import format_chunks, parse_response, generate
from services.rag.embeddings import get_embedding
from services.rag.indexer import retrieve_chunks

logger = logging.getLogger(__name__)


SECRET_PATTERNS = [
    ("secret.openai_key",        r"sk-[a-zA-Z0-9_-]{20,}",             "critical"),
    ("secret.aws_key",           r"AKIA[0-9A-Z]{16}",                  "critical"),
    ("secret.github_token",      r"ghp_[a-zA-Z0-9]{36}",               "critical"),
    ("secret.slack_token",       r"xox[bp]-[a-zA-Z0-9-]+",             "critical"),
    ("secret.sendgrid_key",      r"SG\.[a-zA-Z0-9]{22,}",              "critical"),
    ("secret.private_key",       r"-----BEGIN[A-Z ]*PRIVATE KEY-----", "critical"),
    ("secret.connection_string", r"(postgresql|postgres|mysql|mongodb|redis|amqp|ftp|ssh)(\+\w+)?://[^:\s]+:[^@\s]+@[^/\s]+", "high"),
]

EXCLUDED_FILES = {
    ".env.example", ".env.sample", ".env.template", ".env.local.example", ".env.dist",
}
EXCLUDED_LINE_PATTERNS = re.compile(
    r'placeholder|your_|changeme|xxx|TODO|mock|fake|dummy|fixture',
    re.IGNORECASE,
)

COMMITTED_SECRET_FILES = {
    ".env": "committed.env",
    ".env.local": "committed.env",
    ".env.dev": "committed.env",
    ".env.development": "committed.env",
    ".env.staging": "committed.env",
    ".env.prod": "committed.env",
    ".env.production": "committed.env",
    ".env.test": "committed.env",
    ".env.backup": "committed.env_backup",
    ".env.old": "committed.env_backup",
    ".netrc": "committed.netrc",
    ".pgpass": "committed.pgpass",
    "id_rsa": "committed.ssh_key",
    "id_dsa": "committed.ssh_key",
    "id_ecdsa": "committed.ssh_key",
    "id_ed25519": "committed.ssh_key",
    "credentials": "committed.credentials",
    "secrets": "committed.secrets",
    "service-account.json": "committed.gcp_key",
    "serviceAccountKey.json": "committed.gcp_key",
    "terraform.tfvars": "committed.terraform",
    "google-services.json": "committed.google_services",
}

COMMITTED_SECRET_SUFFIXES = {
    ".pem": "committed.pem",
    ".key": "committed.key",
    ".p12": "committed.p12",
    ".pfx": "committed.pfx",
    ".jks": "committed.jks",
    ".keystore": "committed.keystore",
    ".ppk": "committed.ppk",
}


def _scan_committed_secret_files(files: list[dict], language: str = DEFAULT_LANGUAGE) -> list[dict]:
    issues = []

    for f in files:
        path = f.get("path", "")
        if not path:
            continue

        name = Path(path).name
        if name in EXCLUDED_FILES:
            continue

        key = COMMITTED_SECRET_FILES.get(name) or COMMITTED_SECRET_SUFFIXES.get(
            Path(path).suffix.lower()
        )
        if not key:
            continue

        issues.append({
            "severity": "critical",
            "title": text(key, language, name=name),
            "rule": key,
            "file_path": path,
            "description": text("committed.description", language),
            "code_hint": path,
            "source": "filename",
        })

    logger.info("Scan fichiers sensibles: %d issues", len(issues))
    return issues[:15]


def _scan_secrets_regex(files: list[dict], language: str = DEFAULT_LANGUAGE) -> list[dict]:
    issues = []

    for f in files:
        path = f.get("path", "")
        content = f.get("content", "")
        if not content:
            continue

        if Path(path).name in EXCLUDED_FILES:
            continue

        for line_num, line in enumerate(content.splitlines(), 1):
            if EXCLUDED_LINE_PATTERNS.search(line):
                continue

            for key, pattern, severity in SECRET_PATTERNS:
                if re.search(pattern, line):
                    issues.append({
                        "severity": severity,
                        "title": text(key, language),
                        "rule": key,
                        "file_path": path,
                        "description": text("secret.description", language, line=line_num),
                        "code_hint": line.strip()[:200],
                        "source": "regex",
                    })
                    break

    logger.info("Regex secrets scan: %d issues", len(issues))
    return issues[:15]


async def run_secrets_detection(
    collection_name: str,
    files: list[dict],
    language: str = DEFAULT_LANGUAGE,
) -> dict:
    language = normalize(language)
    logger.info("Secrets detection demarree (collection=%s, langue=%s)", collection_name, language)

    query = "hardcoded API key secret token password credential private key"

    filename_issues = _scan_committed_secret_files(files, language)
    regex_issues = _scan_secrets_regex(files, language)
    embedding = await get_embedding(query)

    chunks = retrieve_chunks(collection_name, embedding, n_results=20)
    context = format_chunks(chunks)

    prompt = prompts.secrets_detection(context, language)

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
            "message": text("recommendation.regex_secrets", language, count=len(regex_issues)),
        })
    if filename_issues:
        recommendations.insert(0, {
            "priority": "high",
            "message": text("recommendation.committed_files", language, count=len(filename_issues)),
        })

    logger.info("Secrets detection terminee: %d fichiers + %d regex + %d llm = %d issues",
                len(filename_issues), len(regex_issues), len(llm_issues), len(all_issues))
    return {
        "status": status,
        "issues": all_issues,
        "recommendations": recommendations,
    }


async def run_gitignore_check(
    collection_name: str,
    has_gitignore: bool,
    language: str = DEFAULT_LANGUAGE,
) -> dict:
    language = normalize(language)
    logger.info("Gitignore check demarree (has_gitignore=%s, langue=%s)", has_gitignore, language)

    if not has_gitignore:
        return {
            "status": "issues_found",
            "issues": [
                {
                    "severity": "high",
                    "title": text("gitignore.missing.title", language),
                    "rule": "gitignore.missing",
                    "file_path": "N/A",
                    "description": text("gitignore.missing.description", language),
                    "code_hint": "",
                }
            ],
            "recommendations": [
                {
                    "priority": "high",
                    "message": text("gitignore.missing.recommendation", language),
                }
            ]
        }

    query = "gitignore env secrets sensitive files excluded"
    embedding = await get_embedding(query)
    chunks = retrieve_chunks(collection_name, embedding, n_results=10)
    context = format_chunks(chunks)

    prompt = prompts.gitignore_check(context, language)

    raw = await generate(prompt)
    result = parse_response(raw)
    logger.info("Gitignore check terminee: %d issues", len(result.get("issues", [])))
    return result
