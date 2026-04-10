from __future__ import annotations

import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, get_current_user
from app.models.user import User
from app.schemas.auth import MSCallbackRequest, TokenResponse
from app.services.user_service import upsert_o365_user

router = APIRouter()
logger = logging.getLogger(__name__)

def _build_token_response(user: User) -> TokenResponse:
    access_token = create_access_token(
        subject=user.id,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    role_data = {"id": user.role.id, "name": user.role.name} if user.role else None
    return TokenResponse(
        access_token = access_token,
        token_type   = "bearer",
        user_id      = user.id,
        public_id    = user.public_id,
        email        = user.email,
        first_name   = user.first_name,
        last_name    = user.last_name,
        display_name = user.display_name,
        role         = role_data,
        is_external  = user.is_external,
        is_synced    = user.is_synced,
    )

@router.post("/redirect", response_model=TokenResponse)
async def ms_callback(payload: MSCallbackRequest, db: AsyncSession = Depends(get_db)):
    if not all([settings.AZURE_TENANT_ID, settings.AZURE_CLIENT_ID, settings.AZURE_CLIENT_SECRET]):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Microsoft SSO is not configured on this server.",
        )

    token_url = f"https://login.microsoftonline.com/{settings.AZURE_TENANT_ID}/oauth2/v2.0/token"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                token_url,
                data={
                    "grant_type":    "authorization_code",
                    "code":          payload.code,
                    "redirect_uri":  payload.redirect_uri,
                    "client_id":     settings.AZURE_CLIENT_ID,
                    "client_secret": settings.AZURE_CLIENT_SECRET,
                    "scope":         "openid profile email User.Read",
                },
                timeout=15.0,
            )
            resp.raise_for_status()
            ms_tokens = resp.json()
    except httpx.HTTPStatusError as exc:
        logger.error("MS token exchange failed: %s", exc.response.text)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Microsoft rejected the token exchange: {exc.response.text}")
    except httpx.HTTPError as exc:
        logger.error("MS token exchange network error: %s", exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to reach Microsoft.")

    try:
        async with httpx.AsyncClient() as client:
            graph_resp = await client.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": f"Bearer {ms_tokens['access_token']}"},
                timeout=10.0,
            )
            graph_resp.raise_for_status()
            ms_user = graph_resp.json()
    except httpx.HTTPError as exc:
        logger.error("MS Graph fetch failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to fetch profile from Microsoft.")

    user = await upsert_o365_user(
        db           = db,
        o365_id      = ms_user.get("id"),
        email        = ms_user.get("mail") or ms_user.get("userPrincipalName"),
        first_name   = ms_user.get("givenName", ""),
        last_name    = ms_user.get("surname", ""),
        display_name = ms_user.get("displayName"),
    )

    if user.is_deleted or not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")

    return _build_token_response(user)

@router.get("/me")
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return {
        "id":           current_user.id,
        "public_id":    current_user.public_id,
        "email":        current_user.email,
        "first_name":   current_user.first_name,
        "last_name":    current_user.last_name,
        "display_name": current_user.display_name,
        "role":         {"id": current_user.role.id, "name": current_user.role.name} if current_user.role else None,
        "is_external":  current_user.is_external,
        "is_synced":    current_user.is_synced,
    }
