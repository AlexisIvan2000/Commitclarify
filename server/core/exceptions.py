import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    status_code = 500
    code = "internal_error"
    default_message = "Erreur interne du serveur"

    def __init__(self, message: str | None = None, code: str | None = None):
        self.message = message or self.default_message
        self.code = code or type(self).code
        super().__init__(self.message)


class ValidationError(AppError):
    status_code = 400
    code = "validation_error"
    default_message = "Requete invalide"


class AuthError(AppError):
    status_code = 401
    code = "unauthorized"
    default_message = "Authentification requise"


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"
    default_message = "Ressource introuvable"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"
    default_message = "Operation deja en cours ou deja effectuee"


class QuotaExceededError(AppError):
    status_code = 429
    code = "quota_exceeded"
    default_message = "Quota atteint"


class RateLimitedError(AppError):
    status_code = 429
    code = "rate_limited"
    default_message = "Trop de requetes"

    def __init__(
        self,
        message: str | None = None,
        code: str | None = None,
        retry_after: float = 60.0,
    ):
        super().__init__(message, code)
        self.retry_after = max(1, round(retry_after))

    @property
    def headers(self) -> dict[str, str]:
        return {"Retry-After": str(self.retry_after)}


class ExternalServiceError(AppError):
    status_code = 502
    code = "external_service_error"
    default_message = "Service externe indisponible"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError):
        if exc.status_code >= 500:
            logger.error(
                "%s sur %s: %s", type(exc).__name__, request.url.path, exc.message, exc_info=exc,
            )
        else:
            logger.info("%s sur %s: %s", type(exc).__name__, request.url.path, exc.message)

        content = {"detail": exc.message, "code": exc.code}
        retry_after = getattr(exc, "retry_after", None)

        if retry_after is not None:
            content["retry_after"] = retry_after

        return JSONResponse(
            status_code=exc.status_code,
            content=content,
            headers=getattr(exc, "headers", None),
        )
