"""
FastAPI Dependencies for INDUSTRIA AI (PRD v1.2 §8.1, §13.1)
Provides DB session, current authenticated user, and strict tenant context.
"""

from typing import Generator, Tuple
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db, SessionLocal
from backend.app.models.auth import User, Organisation

security = HTTPBearer(auto_error=False)

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Authenticates the Bearer JWT and returns the active User within their Organisation."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "UNAUTHENTICATED", "message": "Missing bearer authentication token."}}
        )

    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        org_id = payload.get("org_id")
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "TOKEN_EXPIRED", "message": "Access token has expired."}}
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_TOKEN", "message": "Invalid access token."}}
        )

    user = db.query(User).filter(
        User.id == user_id,
        User.organisation_id == org_id
    ).first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "UNAUTHENTICATED", "message": "User not found or account is deactivated."}}
        )

    return user

def get_tenant_context(
    current_user: User = Depends(get_current_user)
) -> Tuple[User, Organisation]:
    """Returns the authenticated user and organisation ensuring tenant isolation (PRD v1.2 §8.1)."""
    return current_user, current_user.organisation

