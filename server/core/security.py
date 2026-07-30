import hashlib
import secrets

OAUTH_STATE_COOKIE = "cc_oauth_state"
OAUTH_STATE_TTL_SECONDS = 600
AUTH_CODE_TTL_SECONDS = 120


def generate_token(nbytes: int = 32) -> str:
    return secrets.token_hex(nbytes)

def generate_url_safe_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)

def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()

def tokens_match(left: str | None, right: str | None) -> bool:
    if not left or not right:
        return False
    return secrets.compare_digest(left, right)
