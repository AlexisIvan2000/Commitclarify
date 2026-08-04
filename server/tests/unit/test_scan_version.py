import hashlib
from pathlib import Path

from services.scan import SCAN_VERSION

SERVICES = Path(__file__).resolve().parents[2] / "services"

RESULT_DEFINING_MODULES = sorted(
    path
    for package in ("scan", "github")
    for path in (SERVICES / package).glob("*.py")
    if path.name != "__init__.py"
)

EXPECTED_VERSION_AND_DIGEST = (4, "a9c30bfd2d35d3b5")

BUMP_INSTRUCTIONS = (
    "Ce qui determine le resultat d'un scan a change.\n"
    "services/scan definit les regles, services/github definit ce que les regles voient : "
    "les deux peuvent modifier la sortie.\n"
    "Si le resultat d'un meme depot peut differer, incrementez SCAN_VERSION dans "
    "services/scan/report.py — sinon les scans deja en cache resteront servis obsoletes.\n"
    "Puis reportez ici le couple affiche par l'echec."
)


def rules_digest() -> str:
    digest = hashlib.sha256()

    for path in RESULT_DEFINING_MODULES:
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_text(encoding="utf-8").replace("\r\n", "\n").encode("utf-8"))

    return digest.hexdigest()[:16]


def test_the_result_defining_modules_are_actually_found():
    names = {path.name for path in RESULT_DEFINING_MODULES}

    assert {"secrets.py", "gitignore.py", "quality.py", "documentation.py"} <= names
    assert {"repo_fetcher.py", "client.py"} <= names


def test_changing_the_rules_forces_a_conscious_version_bump():
    assert (SCAN_VERSION, rules_digest()) == EXPECTED_VERSION_AND_DIGEST, BUMP_INSTRUCTIONS
