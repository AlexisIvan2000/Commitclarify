import os

from dotenv import load_dotenv

load_dotenv()

JWT_KEY = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
GITHUB_CALLBACK_URL = os.getenv("GITHUB_CALLBACK_URL")

FERNET_KEY = os.getenv("FERNET_KEY")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

FRONTEND_URL = os.getenv("FRONTEND_URL")
DB_URL = os.getenv("DB_URL")

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))

DAILY_ANALYSIS_LIMIT = int(os.getenv("DAILY_ANALYSIS_LIMIT", "3"))

SCAN_RATE_PER_MINUTE = int(os.getenv("SCAN_RATE_PER_MINUTE", "4"))
SCAN_RATE_PER_HOUR = int(os.getenv("SCAN_RATE_PER_HOUR", "20"))

CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")

COOKIE_SECURE = (GITHUB_CALLBACK_URL or "").startswith("https://")

REQUIRED_SETTINGS = {
    "JWT_SECRET": JWT_KEY,
    "GITHUB_CLIENT_ID": GITHUB_CLIENT_ID,
    "GITHUB_CLIENT_SECRET": GITHUB_CLIENT_SECRET,
    "GITHUB_CALLBACK_URL": GITHUB_CALLBACK_URL,
    "FERNET_KEY": FERNET_KEY,
    "OPENAI_API_KEY": OPENAI_API_KEY,
    "FRONTEND_URL": FRONTEND_URL,
    "DB_URL": DB_URL,
}


def missing_settings() -> list[str]:
    return sorted(name for name, value in REQUIRED_SETTINGS.items() if not value)
