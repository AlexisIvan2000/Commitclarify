import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    status_code = 500
    default_message = "Erreur interne du serveur"

    def __init__(self, message: str | None = None):
        self.message = message or self.default_message
        super().__init__(self.message)


class ValidationError(AppError):
    status_code = 400
    default_message = "Requete invalide"


class AuthError(AppError):
    status_code = 401
    default_message = "Authentification requise"


class NotFoundError(AppError):
    status_code = 404
    default_message = "Ressource introuvable"


class ConflictError(AppError):
    status_code = 409
    default_message = "Operation deja en cours ou deja effectuee"


class QuotaExceededError(AppError):
    status_code = 429
    default_message = "Quota atteint"


class ExternalServiceError(AppError):
    status_code = 502
    default_message = "Service externe indisponible"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError):
        if exc.status_code >= 500:
            logger.error("%s sur %s: %s", type(exc).__name__, request.url.path, exc.message, exc_info=exc)
        else:
            logger.info("%s sur %s: %s", type(exc).__name__, request.url.path, exc.message)

        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})
