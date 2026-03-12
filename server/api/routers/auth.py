import hashlib
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete as sql_delete

from core.config import GITHUB_CLIENT_ID, GITHUB_CALLBACK_URL, FRONTEND_URL
from core.database import get_db
from core.rate_limit import limiter
from api.dependencies import get_current_user
from models.schemas import UserResponse, TokenResponse, RefreshTokenRequest
from models.db_models import User, RefreshToken, Analysis, AnalysisResult

logger = logging.getLogger(__name__)
from services.authentication.auth import github_exchange_code, github_get_user, upsert_user
from services.authentication.token import (
    create_access_token,
    create_refresh_token,
    verify_access_token,
    revoke_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/github/login")
@limiter.limit("10/minute")
async def login_github(request: Request):
    """Redirige vers la page d'autorisation GitHub."""
    github_auth_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri={GITHUB_CALLBACK_URL}"
        f"&scope=read:user user:email repo"
    )
    return RedirectResponse(url=github_auth_url)


@router.get("/callback")
@limiter.limit("5/minute")
async def callback_github(request: Request, code: str, db: AsyncSession = Depends(get_db)):
    """Callback OAuth GitHub : échange le code contre des tokens."""
    try:
        access_token = await github_exchange_code(code)
        github_user = await github_get_user(access_token)
        user = await upsert_user(github_user, access_token, db)
    except ValueError as e:
        logger.warning("Echec OAuth callback: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    jwt_access = create_access_token(user.id)
    jwt_refresh = await create_refresh_token(user.id, db)

    logger.info("Connexion reussie: user=%s (github_id=%s)", user.login, user.github_id)
    return RedirectResponse(url=f"{FRONTEND_URL}/auth/callback?access_token={jwt_access}&refresh_token={jwt_refresh}")


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("5/minute")
async def refresh_token(request: Request, body: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """Rafraîchit l'access token via le refresh token."""
    token_hash = hashlib.sha256(body.refresh_token.encode()).hexdigest()
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
        )
    )
    stored = result.scalar_one_or_none()

    if not stored or stored.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token invalide ou expiré")

    # Révoquer l'ancien et créer un nouveau (rotation)
    await revoke_refresh_token(body.refresh_token, db)

    new_access = create_access_token(stored.user_id)
    new_refresh = await create_refresh_token(stored.user_id, db)

    return TokenResponse(access_token=new_access, refresh_token=new_refresh)


@router.post("/logout")
@limiter.limit("10/minute")
async def logout(
    request: Request,
    body: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Révoque le refresh token de l'utilisateur."""
    await revoke_refresh_token(body.refresh_token, db)
    logger.info("Deconnexion: user=%s", current_user.login)
    return {"detail": "Déconnexion réussie"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Retourne le profil de l'utilisateur connecté."""
    return current_user


@router.delete("/account")
async def delete_account(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Supprime le compte utilisateur et toutes ses donnees (sauf analysis_log pour le rate limit)."""
    # Récupérer les IDs des analyses de l'utilisateur
    result = await db.execute(
        select(Analysis.id).where(Analysis.user_id == current_user.id)
    )
    analysis_ids = [row[0] for row in result.all()]

    # Supprimer analysis_results d'abord (FK vers analyses)
    if analysis_ids:
        await db.execute(
            sql_delete(AnalysisResult).where(AnalysisResult.analysis_id.in_(analysis_ids))
        )

    # Supprimer refresh tokens
    await db.execute(
        sql_delete(RefreshToken).where(RefreshToken.user_id == current_user.id)
    )

    # Supprimer analyses
    await db.execute(
        sql_delete(Analysis).where(Analysis.user_id == current_user.id)
    )

    # Supprimer l'utilisateur
    await db.delete(current_user)
    await db.commit()

    logger.info("Compte supprime: user=%s (github_id=%s)", current_user.login, current_user.github_id)
    return {"detail": "Compte supprime"}
