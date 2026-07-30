SUPPORTED_LANGUAGES = ("fr", "en")
DEFAULT_LANGUAGE = "fr"


def normalize(value: str | None) -> str:
    if not value:
        return DEFAULT_LANGUAGE

    candidate = value.strip().lower().replace("_", "-").split("-")[0]
    return candidate if candidate in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


PROMPT_OUTPUT_RULE = {
    "fr": (
        "Reponds UNIQUEMENT en JSON valide, sans balises markdown. "
        "Tout le contenu (titres, descriptions, recommandations) DOIT etre en francais."
    ),
    "en": (
        "Reply ONLY with valid JSON, without markdown fences. "
        "All content (titles, descriptions, recommendations) MUST be written in English."
    ),
}


TEXTS: dict[str, dict[str, str]] = {
    "secret.openai_key": {
        "fr": "Cle OpenAI exposee",
        "en": "Exposed OpenAI key",
    },
    "secret.aws_key": {
        "fr": "Cle AWS Access Key exposee",
        "en": "Exposed AWS access key",
    },
    "secret.github_token": {
        "fr": "Token GitHub expose",
        "en": "Exposed GitHub token",
    },
    "secret.slack_token": {
        "fr": "Token Slack expose",
        "en": "Exposed Slack token",
    },
    "secret.sendgrid_key": {
        "fr": "Cle SendGrid exposee",
        "en": "Exposed SendGrid key",
    },
    "secret.private_key": {
        "fr": "Cle privee dans le code",
        "en": "Private key in source code",
    },
    "secret.connection_string": {
        "fr": "String de connexion exposee",
        "en": "Exposed connection string",
    },
    "secret.description": {
        "fr": "Ligne {line} : secret detecte par scan automatique",
        "en": "Line {line}: secret detected by automated scan",
    },

    "committed.env": {
        "fr": "Fichier {name} commite dans le depot",
        "en": "{name} file committed to the repository",
    },
    "committed.env_backup": {
        "fr": "Sauvegarde de fichier .env commitee ({name})",
        "en": "Backup of a .env file committed ({name})",
    },
    "committed.netrc": {
        "fr": "Fichier .netrc (identifiants reseau) commite",
        "en": ".netrc file (network credentials) committed",
    },
    "committed.pgpass": {
        "fr": "Fichier .pgpass (mot de passe PostgreSQL) commite",
        "en": ".pgpass file (PostgreSQL password) committed",
    },
    "committed.ssh_key": {
        "fr": "Cle privee SSH commitee ({name})",
        "en": "SSH private key committed ({name})",
    },
    "committed.credentials": {
        "fr": "Fichier d'identifiants commite",
        "en": "Credentials file committed",
    },
    "committed.secrets": {
        "fr": "Fichier de secrets commite",
        "en": "Secrets file committed",
    },
    "committed.gcp_key": {
        "fr": "Cle de compte de service Google commitee",
        "en": "Google service account key committed",
    },
    "committed.terraform": {
        "fr": "Variables Terraform commitees (contiennent souvent des secrets)",
        "en": "Terraform variables committed (often contain secrets)",
    },
    "committed.google_services": {
        "fr": "Configuration Google Services commitee",
        "en": "Google Services configuration committed",
    },
    "committed.pem": {
        "fr": "Certificat ou cle privee au format PEM commite",
        "en": "PEM certificate or private key committed",
    },
    "committed.key": {
        "fr": "Fichier de cle commite",
        "en": "Key file committed",
    },
    "committed.p12": {
        "fr": "Conteneur de certificat PKCS#12 commite",
        "en": "PKCS#12 certificate container committed",
    },
    "committed.pfx": {
        "fr": "Conteneur de certificat PFX commite",
        "en": "PFX certificate container committed",
    },
    "committed.jks": {
        "fr": "Keystore Java commite",
        "en": "Java keystore committed",
    },
    "committed.keystore": {
        "fr": "Keystore commite",
        "en": "Keystore committed",
    },
    "committed.ppk": {
        "fr": "Cle privee PuTTY commitee",
        "en": "PuTTY private key committed",
    },
    "committed.description": {
        "fr": (
            "Ce type de fichier ne doit jamais etre versionne : il contient des secrets "
            "par nature. Retirez-le de l'historique Git et ajoutez-le au .gitignore."
        ),
        "en": (
            "This kind of file must never be versioned: it holds secrets by design. "
            "Remove it from the Git history and add it to .gitignore."
        ),
    },

    "gitignore.missing.title": {
        "fr": "Aucun fichier .gitignore detecte",
        "en": "No .gitignore file found",
    },
    "gitignore.missing.description": {
        "fr": "Le projet ne contient pas de .gitignore. Tous les fichiers risquent d'etre versionnes.",
        "en": "The project has no .gitignore. Every file risks being committed.",
    },
    "gitignore.missing.recommendation": {
        "fr": (
            "Creer un fichier .gitignore a la racine du projet et y ajouter les fichiers "
            "sensibles (ex: .env, config.yaml, etc.)"
        ),
        "en": (
            "Create a .gitignore at the project root and add the sensitive files to it "
            "(e.g. .env, config.yaml, etc.)"
        ),
    },

    "recommendation.regex_secrets": {
        "fr": (
            "Scan automatique : {count} secret(s) detecte(s) par pattern matching "
            "— a corriger en priorite"
        ),
        "en": (
            "Automated scan: {count} secret(s) found by pattern matching "
            "— fix these first"
        ),
    },
    "recommendation.committed_files": {
        "fr": (
            "{count} fichier(s) sensible(s) versionne(s) : retirez-les de l'index "
            "(git rm --cached), ajoutez-les au .gitignore, puis faites tourner les cles concernees"
        ),
        "en": (
            "{count} sensitive file(s) committed: remove them from the index "
            "(git rm --cached), add them to .gitignore, then rotate the affected keys"
        ),
    },
    "recommendation.ruff": {
        "fr": "Ruff a detecte {count} probleme(s) — corrigez-les avec : ruff check --fix",
        "en": "Ruff found {count} issue(s) — fix them with: ruff check --fix",
    },
    "recommendation.eslint": {
        "fr": "ESLint a detecte {count} probleme(s) — corrigez-les avec : npx eslint --fix",
        "en": "ESLint found {count} issue(s) — fix them with: npx eslint --fix",
    },
    "recommendation.no_readme": {
        "fr": "Analyse README vs Code non disponible — aucun README.md detecte dans ce repository.",
        "en": "README vs Code analysis unavailable — no README.md found in this repository.",
    },

    "progress.fetching": {
        "fr": "Recuperation des fichiers...",
        "en": "Fetching files...",
    },
    "progress.fetched": {
        "fr": "{count} fichiers recuperes",
        "en": "{count} files fetched",
    },
    "progress.index_cached": {
        "fr": "Index vectoriel deja en cache",
        "en": "Vector index already cached",
    },
    "progress.indexing": {
        "fr": "Indexation en cours...",
        "en": "Indexing...",
    },
    "progress.indexed": {
        "fr": "{count} chunks indexes",
        "en": "{count} chunks indexed",
    },
    "progress.analyzing": {
        "fr": "Analyse IA en cours...",
        "en": "Running AI analysis...",
    },
    "progress.no_files": {
        "fr": "Aucun fichier analysable trouve.",
        "en": "No analyzable file found.",
    },

    "issue.at_line": {
        "fr": "Ligne {line} : {message}",
        "en": "Line {line}: {message}",
    },

    "rule.F401": {"fr": "Import inutilise", "en": "Unused import"},
    "rule.F841": {
        "fr": "Variable assignee mais jamais utilisee",
        "en": "Variable assigned but never used",
    },
    "rule.E501": {"fr": "Ligne trop longue", "en": "Line too long"},
    "rule.E722": {
        "fr": "Bare except (except sans type)",
        "en": "Bare except (except without a type)",
    },
    "rule.B006": {"fr": "Argument par defaut mutable", "en": "Mutable default argument"},
    "rule.C901": {"fr": "Fonction trop complexe", "en": "Function too complex"},
    "rule.PLR0913": {"fr": "Trop de parametres", "en": "Too many parameters"},
    "rule.PLR0915": {
        "fr": "Trop de statements dans la fonction",
        "en": "Too many statements in the function",
    },

    "rule.no-unused-vars": {
        "fr": "Variable ou import inutilise",
        "en": "Unused variable or import",
    },
    "rule.no-empty": {"fr": "Bloc vide", "en": "Empty block"},
    "rule.no-unreachable": {"fr": "Code inatteignable", "en": "Unreachable code"},
    "rule.no-duplicate-case": {
        "fr": "Case duplique dans un switch",
        "en": "Duplicate case in a switch",
    },
    "rule.no-redeclare": {"fr": "Variable re-declaree", "en": "Variable redeclared"},
    "rule.no-constant-condition": {"fr": "Condition constante", "en": "Constant condition"},
    "rule.eqeqeq": {
        "fr": "Egalite stricte requise (=== au lieu de ==)",
        "en": "Strict equality required (=== instead of ==)",
    },
    "rule.no-var": {
        "fr": "Utiliser let/const au lieu de var",
        "en": "Use let/const instead of var",
    },
    "rule.prefer-const": {
        "fr": "Utiliser const quand la variable n'est pas reassignee",
        "en": "Use const when the variable is never reassigned",
    },

    "aspect.secrets_detection": {
        "fr": "Detection de secrets",
        "en": "Secret detection",
    },
    "aspect.gitignore_check": {
        "fr": "Verification .gitignore",
        "en": ".gitignore check",
    },
    "aspect.quality_check": {"fr": "Qualite du code", "en": "Code quality"},
    "aspect.readme_check": {"fr": "README vs Code", "en": "README vs Code"},

    "result.clean": {"fr": "Aucun probleme", "en": "No issue"},
    "result.issues_found": {"fr": "Problemes detectes", "en": "Issues found"},
    "result.unavailable": {"fr": "Non disponible", "en": "Unavailable"},
    "result.error": {"fr": "Erreur pendant l'analyse", "en": "Error during analysis"},

    "pdf.title": {
        "fr": "CommitClarify — Rapport d'analyse",
        "en": "CommitClarify — Analysis report",
    },
    "pdf.repository": {"fr": "Repository : {value}", "en": "Repository: {value}"},
    "pdf.date": {"fr": "Date : {value}", "en": "Date: {value}"},
    "pdf.sha": {"fr": "SHA : {value}", "en": "SHA: {value}"},
    "pdf.status": {"fr": "Statut : {value}", "en": "Status: {value}"},
    "pdf.recommendations": {"fr": "Recommandations :", "en": "Recommendations:"},
    "pdf.file": {"fr": "Fichier : {value}", "en": "File: {value}"},
    "pdf.footer": {"fr": "Genere par CommitClarify", "en": "Generated by CommitClarify"},
}


def text(key: str, language: str | None = None, **params: object) -> str:
    entry = TEXTS.get(key)
    if entry is None:
        return key

    template = entry.get(normalize(language)) or entry[DEFAULT_LANGUAGE]
    return template.format(**params) if params else template
