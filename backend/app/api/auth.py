"""
Authentication Endpoints for INDUSTRIA AI (PRD v1.2 §13.2, §15, AC-ORG-1, AC-SEC-1)
"""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.config import settings
from backend.app.models.auth import User
from backend.app.api.deps import get_current_user
from backend.app.services.auth_service import (
    register_organisation, login_user, rotate_refresh_token
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
users_router = APIRouter(tags=["Users"])

class RegisterRequest(BaseModel):
    organisation_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    password: str = Field(..., min_length=12)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

@router.get("/config", status_code=status.HTTP_200_OK)
def get_auth_config():
    """
    Returns public client authentication configuration (PRD v1.2 §13.2).
    Allows frontend to dynamically switch between Supabase and Local authentication.
    """
    return {
        "auth_provider": "supabase" if settings.is_supabase_enabled else "local",
        "supabase_url": settings.SUPABASE_URL if settings.is_supabase_enabled else None,
        "supabase_anon_key": settings.SUPABASE_ANON_KEY if settings.is_supabase_enabled else None,
        "multi_org_enabled": settings.MULTI_ORG_ENABLED,
    }

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """
    Registers a new organisation, default plant, and ORG_ADMIN user (PRD v1.2 §8.1, §13.2, AC-ORG-1).
    Refuses registration with 403 MULTI_ORG_DISABLED if an organisation already exists in single-org mode.
    """
    return register_organisation(
        db=db,
        organisation_name=req.organisation_name,
        email=req.email,
        full_name=req.full_name,
        password=req.password
    )

@router.post("/login", status_code=status.HTTP_200_OK)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticates user and returns access JWT and rotating refresh token (PRD v1.2 §13.2, AC-SEC-1).
    Locks account for 15 minutes after 5 consecutive failed attempts.
    """
    return login_user(db=db, email=req.email, password=req.password)

@router.post("/refresh", status_code=status.HTTP_200_OK)
def refresh(req: RefreshRequest, db: Session = Depends(get_db)):
    """
    Rotates a refresh token family. Detects token reuse and revokes entire session (AC-SEC-1).
    """
    return rotate_refresh_token(db=db, token_string=req.refresh_token)

@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(req: RefreshRequest, db: Session = Depends(get_db)):
    """
    Revokes the refresh token.
    """
    try:
        rf_id, _ = req.refresh_token.split(":", 1)
        from backend.app.models.auth import RefreshToken
        from datetime import datetime
        rf = db.query(RefreshToken).filter(RefreshToken.id == rf_id).first()
        if rf:
            rf.revoked_at = datetime.utcnow()
            db.commit()
    except Exception:
        pass
    return {"message": "Logged out successfully."}

@router.get("/users/me", status_code=status.HTTP_200_OK)
@router.get("/me", status_code=status.HTTP_200_OK)
@users_router.get("/users/me", status_code=status.HTTP_200_OK)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Returns profile information of current authenticated user.
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "organisation": {
            "id": current_user.organisation.id,
            "name": current_user.organisation.name,
            "slug": current_user.organisation.slug
        }
    }
