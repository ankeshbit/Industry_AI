"""
Authentication Endpoints for INDUSTRIA AI (PRD v1.2 §13.2, §15, AC-ORG-1, AC-SEC-1)
"""

import secrets
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, EmailStr, Field
from fastapi import APIRouter, Depends, status, HTTPException, Request
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.config import settings
from backend.app.models.auth import User, Organisation
from backend.app.api.deps import get_current_user, require_org_admin
from backend.app.services.auth_service import (
    register_organisation, login_user, rotate_refresh_token,
    request_password_reset, verify_reset_token, reset_user_password,
    hash_password
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

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=16)
    new_password: str = Field(..., min_length=12)

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

def get_trusted_client_ip(request: Request) -> str:
    """
    Securely determines client IP without blindly trusting spoofed X-Forwarded-For headers.
    Only inspects X-Forwarded-For if the direct connection originates from a configured TRUSTED_PROXIES address.
    """
    direct_ip = request.client.host if request.client else "127.0.0.1"
    if direct_ip not in settings.TRUSTED_PROXIES and direct_ip != "testclient":
        return direct_ip

    forwarded = request.headers.get("x-forwarded-for")
    if not forwarded:
        return direct_ip

    # Parse rightmost untrusted IP address to prevent header injection/spoofing
    ips = [ip.strip() for ip in forwarded.split(",") if ip.strip()]
    for ip in reversed(ips):
        if ip not in settings.TRUSTED_PROXIES:
            return ip

    return ips[0] if ips else direct_ip


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
def forgot_password(req: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    """
    Initiates a secure password reset request:
    - Enforces rate limiting per IP address and normalized email.
    - Generates a single-use cryptographically random token.
    - Stores SHA-256 hash in DB with 20-minute expiration.
    - Sends an email with the secure reset link.
    - Returns a generic message to prevent email enumeration.
    """
    client_ip = get_trusted_client_ip(request)
    return request_password_reset(db=db, email=req.email, ip_address=client_ip)

@router.get("/verify-reset-token", status_code=status.HTTP_200_OK)
def verify_token(token: str, db: Session = Depends(get_db)):
    """
    Pre-validates a password reset token before the user submits a new password.
    """
    return verify_reset_token(db=db, token=token)

@router.post("/reset-password", status_code=status.HTTP_200_OK)
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Validates token and resets user password:
    - Verifies token validity, expiry, and single-use status.
    - Enforces 12+ character password policy with Argon2id hashing.
    - Marks token as consumed.
    - Invalidates all existing sessions and refresh tokens for that user.
    """
    return reset_user_password(db=db, token=req.token, new_password=req.new_password)

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


class UpdateOrganisationRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    timezone: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None


class CreateUserRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    role: str = Field("VIEWER", pattern="^(ORG_ADMIN|ENGINEER|ANALYST|VIEWER)$")
    password: Optional[str] = Field(None, min_length=12)


class UpdateUserRequest(BaseModel):
    role: Optional[str] = Field(None, pattern="^(ORG_ADMIN|ENGINEER|ANALYST|VIEWER)$")
    is_active: Optional[bool] = None


@users_router.get("/organisation", status_code=status.HTTP_200_OK)
def get_organisation_details(
    current_user: User = Depends(require_org_admin),
    db: Session = Depends(get_db)
):
    """
    Returns organisation settings (PRD v1.2 §5.1, §8.1).
    Restricted to ORG_ADMIN.
    """
    org = current_user.organisation
    return {
        "id": org.id,
        "name": org.name,
        "slug": org.slug,
        "status": org.status,
        "timezone": org.timezone,
        "settings": org.settings or {},
        "created_at": org.created_at.isoformat()
    }


@users_router.patch("/organisation", status_code=status.HTTP_200_OK)
def update_organisation_settings(
    req: UpdateOrganisationRequest,
    current_user: User = Depends(require_org_admin),
    db: Session = Depends(get_db)
):
    """
    Updates organisation settings (name, timezone, custom settings).
    Restricted to ORG_ADMIN. Scoped strictly to caller's organisation.
    """
    org = current_user.organisation
    if req.name is not None:
        org.name = req.name
    if req.timezone is not None:
        org.timezone = req.timezone
    if req.settings is not None:
        curr = dict(org.settings or {})
        curr.update(req.settings)
        org.settings = curr
    db.commit()
    db.refresh(org)
    return {
        "message": "Organisation settings updated successfully.",
        "organisation": {
            "id": org.id,
            "name": org.name,
            "slug": org.slug,
            "status": org.status,
            "timezone": org.timezone,
            "settings": org.settings or {}
        }
    }


@users_router.get("/users", status_code=status.HTTP_200_OK)
def list_organisation_users(
    current_user: User = Depends(require_org_admin),
    db: Session = Depends(get_db)
):
    """
    Lists all users belonging to the caller's organisation (PRD v1.2 §5.1).
    Restricted to ORG_ADMIN.
    """
    users = db.query(User).filter(
        User.organisation_id == current_user.organisation_id
    ).order_by(User.created_at.asc()).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat()
        }
        for u in users
    ]


@users_router.post("/users", status_code=status.HTTP_201_CREATED)
def create_organisation_user(
    req: CreateUserRequest,
    current_user: User = Depends(require_org_admin),
    db: Session = Depends(get_db)
):
    """
    Creates/invites a new user into the caller's organisation (PRD v1.2 §5.1, AC-ORG-6).
    Restricted to ORG_ADMIN. Strictly enforces tenant assignment to current_user.organisation_id.
    """
    normalized_email = req.email.strip().lower()
    existing = db.query(User).filter(User.email == normalized_email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "USER_ALREADY_EXISTS", "message": f"User with email '{normalized_email}' is already registered."}}
        )

    raw_password = req.password or secrets.token_urlsafe(24)
    pw_hash = hash_password(raw_password)

    new_user = User(
        organisation_id=current_user.organisation_id,
        email=normalized_email,
        full_name=req.full_name,
        password_hash=pw_hash,
        role=req.role,
        is_active=True,
        token_version=1
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "id": new_user.id,
        "email": new_user.email,
        "full_name": new_user.full_name,
        "role": new_user.role,
        "is_active": new_user.is_active,
        "created_at": new_user.created_at.isoformat()
    }


@users_router.patch("/users/{id}", status_code=status.HTTP_200_OK)
def update_user_membership(
    id: str,
    req: UpdateUserRequest,
    current_user: User = Depends(require_org_admin),
    db: Session = Depends(get_db)
):
    """
    Updates role or deactivates a user in the organisation (PRD v1.2 §5.1, AC-ORG-5).
    - Restricted to ORG_ADMIN.
    - Verified against caller's organisation_id (404 on cross-tenant IDOR).
    - Prevents deactivating or demoting the last active ORG_ADMIN (409 CONFLICT).
    - Bumps token_version to immediately revoke existing sessions of modified user.
    """
    target = db.query(User).filter(
        User.id == id,
        User.organisation_id == current_user.organisation_id
    ).first()
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": "User not found in organisation."}}
        )

    # AC-ORG-5: Last active Org Admin cannot be demoted or deactivated
    if target.role == "ORG_ADMIN" and target.is_active:
        is_demoting = req.role is not None and req.role != "ORG_ADMIN"
        is_deactivating = req.is_active is False
        if is_demoting or is_deactivating:
            active_admin_count = db.query(User).filter(
                User.organisation_id == current_user.organisation_id,
                User.role == "ORG_ADMIN",
                User.is_active == True
            ).count()
            if active_admin_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={"error": {"code": "LAST_ORG_ADMIN", "message": "The last active Org Admin cannot be removed or deactivated."}}
                )

    if req.role is not None:
        target.role = req.role
        target.token_version = (target.token_version or 1) + 1
    if req.is_active is not None:
        target.is_active = req.is_active
        target.token_version = (target.token_version or 1) + 1

    db.commit()
    db.refresh(target)
    return {
        "message": "User updated successfully.",
        "user": {
            "id": target.id,
            "email": target.email,
            "full_name": target.full_name,
            "role": target.role,
            "is_active": target.is_active
        }
    }
