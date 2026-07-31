import logging
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_current_user
from core.config import (
    COOKIE_SECURE,
    FRONTEND_URL,
    GITHUB_CALLBACK_URL,
    GITHUB_CLIENT_ID,
)
from core.database import get_db
from core.exceptions import AppError, AuthError
from core.rate_limit import limiter
from core.security import (
    OAUTH_STATE_COOKIE,
    OAUTH_STATE_TTL_SECONDS,
    generate_url_safe_token,
    tokens_match,
)
from models.db import User
from models.schemas import AuthCodeRequest, RefreshTokenRequest, TokenResponse, UserResponse
from services.authentication.account import delete_account as purge_account
from services.authentication.auth import github_exchange_code, github_get_user, upsert_user
from services.authentication.token import (
    consume_auth_code,
    create_access_token,
    create_auth_code,
    create_refresh_token,
    get_active_refresh_token,
    revoke_refresh_token,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

GITHUB_SCOPES = "read:user user:email repo"


def _frontend_redirect(**params: str) -> RedirectResponse:
    return RedirectResponse(url=f"{FRONTEND_URL}/auth/callback?{urlencode(params)}")


@router.get("/github/login")
@limiter.limit("10/minute")
async def login_github(request: Request):
    state = generate_url_safe_token()

    github_auth_url = (
        "https://github.com/login/oauth/authorize?"
        + urlencode({
            "client_id": GITHUB_CLIENT_ID,
            "redirect_uri": GITHUB_CALLBACK_URL,
            "scope": GITHUB_SCOPES,
            "state": state,
        })
    )

    response = RedirectResponse(url=github_auth_url)
    response.set_cookie(
        OAUTH_STATE_COOKIE,
        state,
        max_age=OAUTH_STATE_TTL_SECONDS,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/auth",
    )
    return response


@router.get("/callback")
@limiter.limit("10/minute")
async def callback_github(
    request: Request,
    code: str,
    state: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    expected_state = request.cookies.get(OAUTH_STATE_COOKIE)

    if not tokens_match(state, expected_state):
        logger.warning("State OAuth invalide ou absent (CSRF probable)")
        response = _frontend_redirect(error="state_invalide")
        response.delete_cookie(OAUTH_STATE_COOKIE, path="/auth")
        return response

    try:
        github_token = await github_exchange_code(code)
        github_user = await github_get_user(github_token)
        user = await upsert_user(github_user, github_token, db)
    except AppError as exc:
        logger.warning("Echec OAuth callback: %s", exc.message)
        response = _frontend_redirect(error="echec_authentification")
        response.delete_cookie(OAUTH_STATE_COOKIE, path="/auth")
        return response

    auth_code = await create_auth_code(
        user_id=user.id,
        access_token=create_access_token(user.id),
        refresh_token=await create_refresh_token(user.id, db),
        db=db,
    )

    logger.info("Connexion reussie: user=%s (github_id=%s)", user.login, user.github_id)

    response = _frontend_redirect(code=auth_code)
    response.delete_cookie(OAUTH_STATE_COOKIE, path="/auth")
    return response


@router.post("/exchange", response_model=TokenResponse)
@limiter.limit("10/minute")
async def exchange_auth_code(
    request: Request,
    body: AuthCodeRequest,
    db: AsyncSession = Depends(get_db),
):
    access_token, refresh_token = await consume_auth_code(body.code, db)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
async def refresh_token(
    request: Request,
    body: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    stored = await get_active_refresh_token(body.refresh_token, db)
    if not stored:
        raise AuthError("Refresh token invalide ou expire")

    await revoke_refresh_token(body.refresh_token, db)

    return TokenResponse(
        access_token=create_access_token(stored.user_id),
        refresh_token=await create_refresh_token(stored.user_id, db),
    )


@router.post("/logout")
@limiter.limit("10/minute")
async def logout(
    request: Request,
    body: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await revoke_refresh_token(body.refresh_token, db)
    logger.info("Deconnexion: user=%s", current_user.login)
    return {"detail": "Déconnexion réussie"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.delete("/account")
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await purge_account(current_user, db)
    return {"detail": "Compte supprime"}
