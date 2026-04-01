"""
app/core/dependencies.py
─────────────────────────────────────────────────────────────────────────────
Centralized FastAPI dependency injectors.

Purpose:
  - Auto-populate `user_email` for TimeLog creation from the authenticated
    user's JWT token (no client-side trust required).
  - Auto-populate `owner_email` for Milestone creation similarly.
  - Provides a single source of truth for "who is performing this action."

Usage example:
    @router.post("/", response_model=TimeLogResponse)
    def create_timelog(
        timelog: TimeLogCreate,
        db: Session = Depends(get_db),
        current_user = Depends(require_authenticated_user),
        _: None = Depends(auto_populate_timelog_user(timelog)),
    ):
        ...

Or more idiomatically as a factory that modifies the payload in-place:
    current_user = Depends(allow_authenticated)
    timelog.user_email = current_user.email  ← preferred pattern shown below
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user, allow_authenticated


# ── Re-export for convenience ────────────────────────────────────────────────
def require_authenticated_user(current_user=Depends(get_current_user)):
    """
    Simple dependency alias — raises 401 if the token is missing/invalid.
    Returns the full ORM User object with role eagerly loaded.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
    return current_user


def get_current_user_email(current_user=Depends(get_current_user)) -> str:
    """
    Returns the email of the authenticated user.
    Used to auto-populate `user_email` fields without trusting client input.
    """
    return current_user.email


def get_current_user_id(current_user=Depends(get_current_user)) -> int:
    """
    Returns the integer primary-key ID of the authenticated user.
    """
    return current_user.id


def get_current_o365_id(current_user=Depends(get_current_user)) -> Optional[str]:
    """
    Returns the Microsoft O365 OID (object ID) of the authenticated user.
    Falls back to str(user.id) for local/dev environments without MSAL.
    """
    return current_user.o365_id or str(current_user.id)


# ── Payload Auto-Population Helpers ─────────────────────────────────────────

def auto_populate_timelog(payload, current_user):
    """
    Mutates a TimeLogCreate payload in-place:
    - Sets `user_email` from the authenticated user if the client did not provide it.

    Call this at the top of the POST endpoint handler:
        auto_populate_timelog(timelog, current_user)
    """
    if not payload.user_email:
        payload.user_email = current_user.email
    return payload


def auto_populate_milestone(payload, current_user):
    """
    Mutates a MilestoneCreate payload in-place:
    - Sets `owner_id` from the authenticated user if not provided.

    Call this at the top of the POST endpoint handler:
        auto_populate_milestone(milestone, current_user)
    """
    if not getattr(payload, "owner_id", None):
        payload.owner_id = current_user.id
    return payload
