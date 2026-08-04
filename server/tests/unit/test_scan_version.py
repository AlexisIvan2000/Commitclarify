import hashlib
from pathlib import Path

from services.scan import SCAN_VERSION

SCAN_PACKAGE = Path(__file__).resolve().parents[2] / "services" / "scan"

RULE_MODULES = sorted(
    path for path in SCAN_PACKAGE.glob("*.py") if path.name != "__init__.py"
)

EXPECTED_VERSION_AND_DIGEST = (1, "1563e6a4d313bee7")

BUMP_INSTRUCTIONS = (
    "Les regles du scan ont change.\n"
    "Si la detection ou la forme de la sortie changent, incrementez SCAN_VERSION dans "
    "services/scan/report.py — sinon les scans deja en cache resteront servis avec des "
    "resultats obsoletes.\n"
    "Puis reportez ici le couple affiche par l'echec."
)


def rules_digest() -> str:
    digest = hashlib.sha256()

    for path in RULE_MODULES:
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_text(encoding="utf-8").replace("\r\n", "\n").encode("utf-8"))

    return digest.hexdigest()[:16]


def test_the_rule_modules_are_actually_found():
    names = {path.name for path in RULE_MODULES}

    assert {"secrets.py", "gitignore.py", "quality.py", "documentation.py"} <= names


def test_changing_the_rules_forces_a_conscious_version_bump():
    assert (SCAN_VERSION, rules_digest()) == EXPECTED_VERSION_AND_DIGEST, BUMP_INSTRUCTIONS
