from core.language import PROMPT_OUTPUT_RULE

SECURITY_ROLE = "Tu es un auditeur de securite strict et precis."
QUALITY_ROLE = "Tu es un expert en qualite logicielle strict et precis."

ISSUE_FIELDS = """      "severity": "<critical|high|medium|low>",
      "title": "<titre court>",
      "file_path": "{file_path}",
      "description": "{description}",
      "code_hint": "{code_hint}\""""

RECOMMENDATIONS_FIELD = """  "recommendations": [
    {
      "priority": "<high|medium|low>",
      "message": "<recommandation actionnable>"
    }
  ]"""


def _format_block(*sections: str) -> str:
    return "FORMAT :\n{\n" + ",\n".join(sections) + "\n}"


def _issues_section(file_path: str, description: str, code_hint: str) -> str:
    fields = ISSUE_FIELDS.format(
        file_path=file_path, description=description, code_hint=code_hint,
    )
    return '  "issues": [\n    {\n' + fields + "\n    }\n  ]"


STATUS_FIELD = '  "status": "<issues_found|clean>"'


def _assemble(*blocks: str) -> str:
    return "\n\n".join(block for block in blocks if block)


SECRETS_INSTRUCTIONS = """Analyse UNIQUEMENT les extraits de code ci-dessous. Detecte les secrets REELLEMENT hardcodes :
- Cles API avec une vraie valeur (ex: "sk-abc123...", "AKIA...")
- Mots de passe en clair dans le code (ex: password = "monpassword")
- Tokens avec une vraie valeur assignee directement
- Cles privees ou certificats colles dans le code

REGLES STRICTES :
- NE SIGNALE PAS les variables qui chargent depuis os.environ, os.getenv, process.env, dotenv
- NE SIGNALE PAS les placeholders (ex: "your-api-key-here", "xxx", "changeme")
- NE SIGNALE PAS les cles de test evidentes (ex: "test-secret-key", "secret" dans un fichier de test)
- EN REVANCHE, une valeur au format d'une vraie cle fournisseur (sk-, AKIA, ghp_, xox, SG., BEGIN PRIVATE KEY) DOIT etre signalee meme dans un fichier de test : une cle reelle commitee dans un test est tout aussi compromise
- NE SIGNALE PAS les definitions de regex ou patterns de detection (ex: r"AKIA...", r"sk-...")
- NE SIGNALE PAS les URLs publiques d'API
- EN REVANCHE, dans un fichier .env versionne (hors .env.example), toute valeur litterale non placeholder EST un secret reel : signale-la
- NE SUPPOSE RIEN qui n'est pas dans le code fourni
- Le "file_path" DOIT etre exactement celui indique dans les extraits fournis — ne jamais inventer un chemin
- Chaque issue DOIT citer un extrait exact du code comme preuve dans "code_hint" (copiable pour Ctrl+F)
- Si tu n'es pas certain a 90%+, NE SIGNALE PAS"""

GITIGNORE_INSTRUCTIONS = """Verifie que ces fichiers sensibles sont bien exclus :
- .env et ses variantes (.env.local, .env.production, etc.)
- Fichiers de cles (*.key, *.pem, *.p12, *.pfx)
- Fichiers secrets (secrets.*, credentials.*)
- Dossiers de dependances (node_modules/, venv/, __pycache__/, etc.)

REGLES STRICTES :
- Base-toi UNIQUEMENT sur le contenu reel du .gitignore fourni
- NE SUPPOSE PAS l'existence de fichiers qui ne sont pas mentionnes dans le code
- Si le .gitignore couvre les cas standards, reponds "clean\""""

QUALITY_INSTRUCTIONS = """Analyse ces extraits de code et detecte UNIQUEMENT :
- Code duplique : deux blocs quasi-identiques dans des fichiers differents
- Logique morte ou code inatteignable

REGLES STRICTES :
- NE SIGNALE PAS les imports inutilises, bare except, fonctions longues, trop de parametres, variables inutilisees, == vs === — c'est deja couvert par les linters (Ruff/ESLint)
- Chaque issue DOIT citer le fichier exact ("file_path") ET un extrait du code concerne dans "code_hint" (copiable pour Ctrl+F)
- NE SIGNALE PAS les choix d'architecture ou de design
- NE SIGNALE PAS les fichiers de config ou de test
- NE SUPPOSE RIEN qui n'est pas dans le code fourni
- Si tu n'es pas certain a 90%+, NE SIGNALE PAS
- Maximum 3 issues"""

README_INSTRUCTIONS = """Compare les deux et detecte UNIQUEMENT les incoherences reelles :
- Features ou endpoints mentionnes dans le README mais ABSENTS du code
- Instructions d'installation incorrectes (mauvais nom de package, commande erronee)
- Documentation qui contredit clairement le code

REGLES STRICTES :
- NE SIGNALE PAS les features du code absentes du README (le README n'a pas a tout documenter)
- NE SIGNALE PAS les ameliorations possibles du README
- NE SUPPOSE PAS — base-toi uniquement sur ce qui est ecrit
- Si le README est globalement correct, reponds "clean\""""


def secrets_detection(context: str, language: str) -> str:
    return _assemble(
        SECURITY_ROLE,
        SECRETS_INSTRUCTIONS,
        context,
        PROMPT_OUTPUT_RULE[language] + '\nSi aucun probleme reel : "status" = "clean" et "issues" = [].',
        _format_block(
            STATUS_FIELD,
            _issues_section(
                "<chemin du fichier>",
                "<explication claire>",
                "<extrait exact du code concerne, copiable pour recherche>",
            ),
            RECOMMENDATIONS_FIELD,
        ),
    )


def gitignore_check(context: str, language: str) -> str:
    return _assemble(
        SECURITY_ROLE,
        "Voici le contenu du .gitignore et des fichiers de configuration du projet :",
        context,
        GITIGNORE_INSTRUCTIONS,
        PROMPT_OUTPUT_RULE[language] + '\nSi tout est correct : "status" = "clean" et "issues" = [].',
        _format_block(
            STATUS_FIELD,
            _issues_section(".gitignore", "<ce qui manque concretement>", ""),
            RECOMMENDATIONS_FIELD,
        ),
    )


def quality_check(context: str, language: str) -> str:
    return _assemble(
        QUALITY_ROLE,
        QUALITY_INSTRUCTIONS,
        context,
        PROMPT_OUTPUT_RULE[language] + '\nSi aucun probleme reel : "issues" = [].',
        _format_block(
            _issues_section(
                "<chemin exact du fichier>",
                "<explication claire et courte>",
                "<extrait exact du code concerne, copiable pour recherche>",
            ),
        ),
    )


def readme_check(readme_text: str, code_context: str, language: str) -> str:
    return _assemble(
        QUALITY_ROLE,
        "Voici le README du projet :\n" + readme_text,
        "Voici des extraits du code :\n" + code_context,
        README_INSTRUCTIONS,
        PROMPT_OUTPUT_RULE[language] + '\nSi tout est coherent : "status" = "clean" et "issues" = [].',
        _format_block(
            STATUS_FIELD,
            _issues_section(
                "README.md",
                "<ce qui est incoherent>",
                "<extrait exact du README concerne, copiable pour recherche>",
            ),
            RECOMMENDATIONS_FIELD,
        ),
    )
