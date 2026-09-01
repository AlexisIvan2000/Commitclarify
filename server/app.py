import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from api.middlewares.jwt_middleware import JWTMiddleware
from api.routers import analysis, auth, repos
from core.config import FRONTEND_URL, missing_settings
from core.database import engine
from core import maintenance
from core.exceptions import register_exception_handlers
from core.rate_limit import limiter
from core.schema import upgrade_schema
from services.analysis import runs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

for noisy in ("httpx", "httpcore", "chromadb", "sentence_transformers", "openai"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Demarrage de CommitClarify...")

    absent = missing_settings()
    if absent:
        raise RuntimeError(
            "Variables d'environnement manquantes : " + ", ".join(absent)
        )

    await upgrade_schema()

    sweeper = maintenance.start()

    yield

    await maintenance.stop(sweeper)
    await runs.shutdown()
    await engine.dispose()
    logger.info("Arret de CommitClarify")


app = FastAPI(title="CommitClarify", version="0.1.0", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL] if FRONTEND_URL else [],
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
