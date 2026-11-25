"""
FastAPI Dependencies for INDUSTRIA AI (PRD v1.2 §8.1, §13.1)
Provides DB session, current authenticated user, and strict tenant context.
"""

from typing import Generator, Tuple, Optional, Dict, Any
import re
import uuid
from datetime import datetime
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import httpx
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db, SessionLocal
from backend.app.models.auth import User, Organisation

security = HTTPBearer(auto_error=False)

def _verify_supabase_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verifies a Supabase-issued JWT either locally via secret or against Supabase GoTrue Auth API.
    """
    if not settings.is_supabase_enabled:
        return None

    # Method 1: Local JWT verification if SUPABASE_JWT_SECRET is configured
    if settings.SUPABASE_JWT_SECRET:
        try:
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_aud": False}
            )
            if payload.get("sub") and payload.get("email"):
                return {
                    "id": payload.get("sub"),
                    "email": payload.get("email"),
                    "user_metadata": payload.get("user_metadata") or {}
                }
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": {"code": "TOKEN_EXPIRED", "message": "Supabase access token has expired."}}
            )
        except (jwt.PyJWTError, Exception):
            pass

    # Method 2: Verification against Supabase GoTrue Auth API
    if settings.SUPABASE_URL:
        try:
            url = f"{settings.SUPABASE_URL}/auth/v1/user"
            headers = {
                "Authorization": f"Bearer {token}",
                "apikey": settings.SUPABASE_ANON_KEY or settings.SUPABASE_JWT_SECRET or ""
            }
            with httpx.Client(timeout=4.0) as client:
                resp = client.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "id": data.get("id"),
                        "email": data.get("email"),
                        "user_metadata": data.get("user_metadata") or {}
                    }
        except Exception:
            pass

    return None

def _get_or_create_supabase_user(db: Session, sb_user: Dict[str, Any]) -> User:
    """
    Resolves or auto-provisions a database User and Organisation for an authenticated Supabase user.
    - Prevents unauthorized account takeover by verifying email confirmation before linking.
    - Prevents accidental multi-organisation joining in single-org mode (MS1).
    - Deterministically assigns ORG_ADMIN to newly provisioned organisation creators.
    """
    email = sb_user.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "INVALID_SUPABASE_USER", "message": "Supabase user missing email."}}
        )

    normalized_email = email.strip().lower()
    user = db.query(User).filter(User.email == normalized_email).first()
    if user:
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": {"code": "ACCOUNT_DEACTIVATED", "message": "Account is deactivated."}}
            )

        # Unauthorized Account Linking Protection:
        # If the local account is not Supabase-managed, verify that Supabase has verified email ownership
        if user.password_hash != "SUPABASE_MANAGED_AUTH":
            is_email_confirmed = bool(
                sb_user.get("email_confirmed_at")
                or sb_user.get("confirmed_at")
                or (sb_user.get("user_metadata") or {}).get("email_verified")
            )
            if not is_email_confirmed:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"error": {"code": "UNVERIFIED_EMAIL", "message": "Supabase email must be verified before linking to an existing account."}}
                )

        return user

    # Auto-provision new user and organisation
    user_metadata = sb_user.get("user_metadata") or {}
    full_name = user_metadata.get("full_name") or (normalized_email.split("@")[0].replace(".", " ").title())
    org_name = user_metadata.get("organisation_name") or f"{full_name}'s Organisation"
    slug = re.sub(r"[^a-z0-9]+", "-", org_name.lower()).strip("-") or f"org-{uuid.uuid4().hex[:6]}"

    # Prevent accidental organisation assignment in single-org mode:
    if not settings.MULTI_ORG_ENABLED:
        existing_org_count = db.query(Organisation).count()
        if existing_org_count > 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": {"code": "MULTI_ORG_DISABLED", "message": "Multi-organisation registration is currently disabled."}}
            )

    org = db.query(Organisation).filter(Organisation.slug == slug).first()
    if not org:
        org = Organisation(name=org_name, slug=slug, status="ACTIVE")
        db.add(org)
        db.flush()

        # Create default plant for newly provisioned organisation (PRD §8.2.1)
        from backend.app.models.auth import Plant
        plant = Plant(
            organisation_id=org.id,
            code="DEFAULT",
            name="Default Plant",
            is_default=True
        )
        db.add(plant)
        db.flush()

    new_user = User(
        id=sb_user.get("id") or str(uuid.uuid4()),
        organisation_id=org.id,
        email=normalized_email,
        full_name=full_name,
        password_hash="SUPABASE_MANAGED_AUTH",
        role="ORG_ADMIN",  # Deterministic: Creator of organisation is ORG_ADMIN
        is_active=True,
        email_verified_at=datetime.utcnow()
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Authenticates Bearer JWT (Local HS256 or Supabase) and returns active User within their Organisation."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "UNAUTHENTICATED", "message": "Missing bearer authentication token."}}
        )

    token = credentials.credentials

    # Step 1: Attempt local application JWT verification
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        org_id = payload.get("org_id")
        jwt_token_version = payload.get("token_version")
        if user_id and org_id:
            user = db.query(User).filter(
                User.id == user_id,
                User.organisation_id == org_id
            ).first()
            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"error": {"code": "ACCOUNT_DEACTIVATED", "message": "User account is deactivated or not found."}}
                )

            if user.organisation and user.organisation.status != "ACTIVE":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"error": {"code": "ORGANISATION_INACTIVE", "message": "Organisation is inactive or suspended."}}
                )

            # Session Invalidation / Token Version Enforcement:
            # If the token contains a token_version that doesn't match the user's current version,
            # it was revoked (e.g. via password reset or explicit session termination).
            expected_version = user.token_version or 1
            if jwt_token_version is not None and jwt_token_version != expected_version:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"error": {"code": "TOKEN_REVOKED", "message": "Session has been invalidated. Please log in again."}}
                )

            return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "TOKEN_EXPIRED", "message": "Access token has expired."}}
        )
    except jwt.PyJWTError:
        pass  # Proceed to Supabase check

    # Step 2: Attempt Supabase authentication verification if enabled
    if settings.is_supabase_enabled:
        sb_user = _verify_supabase_token(token)
        if sb_user:
            return _get_or_create_supabase_user(db, sb_user)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error": {"code": "INVALID_TOKEN", "message": "Invalid access token."}}
    )

def get_tenant_context(
    current_user: User = Depends(get_current_user)
) -> Tuple[User, Organisation]:
    """Returns the authenticated user and organisation ensuring tenant isolation (PRD v1.2 §8.1)."""
    return current_user, current_user.organisation


def require_roles(*allowed_roles: str):
    """
    Factory returning a FastAPI dependency that enforces role-based access control (RBAC).
    Verifies that the authenticated current_user possesses one of the allowed_roles.
    Raises HTTP 403 FORBIDDEN if the user's role is not allowed.
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "FORBIDDEN",
                        "message": f"Action requires one of roles: {', '.join(allowed_roles)}. User role is '{current_user.role}'."
                    }
                }
            )
        return current_user
    return role_checker


# Declarative role dependency tiers (PRD v1.2 §5.1)
require_org_admin = require_roles("ORG_ADMIN")
require_machine_write = require_roles("ORG_ADMIN", "ENGINEER")
require_dataset_write = require_roles("ORG_ADMIN", "ENGINEER", "ANALYST")
require_analysis_write = require_roles("ORG_ADMIN", "ENGINEER", "ANALYST")


