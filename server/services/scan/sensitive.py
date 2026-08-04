from pathlib import Path

EXCLUDED_FILES = {
    ".env.example", ".env.sample", ".env.template", ".env.local.example", ".env.dist",
}

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


def classify(path: str) -> str | None:
    if not path:
        return None

    name = Path(path).name
    if name in EXCLUDED_FILES:
        return None

    return COMMITTED_SECRET_FILES.get(name) or COMMITTED_SECRET_SUFFIXES.get(
        Path(path).suffix.lower()
    )
