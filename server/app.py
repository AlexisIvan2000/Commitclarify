import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from core.config import FRONTEND_URL
from core.database import engine, Base
from core.rate_limit import limiter
from api.routers import auth, repos
from api import analysis
from api.middlewares.jwt_middleware import JWTMiddleware

# --- Logging centralisé ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
# Réduire le bruit des librairies tierces
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("chromadb").setLevel(logging.WARNING)
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Demarrage de CommitClarify...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Base de donnees initialisee")
    yield
    await engine.dispose()
    logger.info("Arret de CommitClarify")


app = FastAPI(title="CommitClarify", version="0.1.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(JWTMiddleware)

@app.get("/")
async def health_check():
    return {"status": "ok", "service": "CommitClarify"}


app.include_router(auth.router)
app.include_router(repos.router)
app.include_router(analysis.router)
