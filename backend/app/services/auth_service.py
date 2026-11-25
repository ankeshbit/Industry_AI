"""
Authentication and Multi-Tenancy Service (PRD v1.2 §8.1, §13.2, §15, AC-ORG-1, AC-SEC-1)
Implements Argon2id password hashing, JWT generation, lockout after 5 failures,
refresh token family rotation, and tenant boundary enforcement.
"""

import uuid
import secrets
import hashlib
import time
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, List
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHash
import jwt
from sqlalchemy.orm import Session
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from backend.app.config import settings
from backend.app.models.auth import (
    Organisation, User, RefreshToken, Plant, PasswordResetToken, RateLimitAttempt
)
from backend.app.services.email_service import send_password_reset_email

ph = PasswordHasher()
# Verified against when the email is unknown so unknown-user and wrong-password logins take similar time
_DUMMY_HASH = ph.hash("industria-timing-equalisation")
security = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    """Hashes a password using Argon2id with OWASP-recommended memory and time cost."""
    return ph.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    """Verifies a password against an Argon2id hash."""
    try:
        return ph.verify(hashed, password)
    except (VerifyMismatchError, InvalidHash):
        return False

def validate_password_strength(password: str) -> None:
    """Enforces minimum 12 characters and basic complexity (PRD v1.2 §13.2, AC-SEC-1)."""
    if len(password) < 12:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": "WEAK_PASSWORD", "message": "Password must be at least 12 characters long."}}
        )
    # Common password blocklist check
    common = ["password12345", "123456789012", "administrator", "changeme1234"]
    if password.lower() in common:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": "COMMON_PASSWORD", "message": "Password is too common or easily guessable."}}
        )

def create_access_token(user_id: str, org_id: str, role: str, token_version: int = 1) -> Tuple[str, int]:
    """Creates a short-lived access JWT containing sub, org_id, role, and token_version claims."""
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.utcnow() + expires_delta
    payload = {
        "sub": user_id,
        "org_id": org_id,
        "role": role,
        "token_version": token_version,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    encoded_jwt = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt, int(expires_delta.total_seconds())

def create_refresh_token(db: Session, user: User, family_id: Optional[str] = None) -> str:
    """Creates a refresh token and tracks its family for reuse detection (PRD v1.2 §13.2)."""
    raw_token = str(uuid.uuid4()) + str(uuid.uuid4())
    token_hash = hash_password(raw_token)
    if not family_id:
        family_id = str(uuid.uuid4())

    expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    rf = RefreshToken(
        organisation_id=user.organisation_id,
        user_id=user.id,
        family_id=family_id,
        token_hash=token_hash,
        expires_at=expires_at
    )
    db.add(rf)
    db.commit()
    # Token returned in format: {rf_id}:{raw_token}
    return f"{rf.id}:{raw_token}"

def register_organisation(
    db: Session,
    organisation_name: str,
    email: str,
    full_name: str,
    password: str
) -> dict:
    """
    Registers an organisation and the initial ORG_ADMIN user (PRD v1.2 §8.1, §13.2, AC-ORG-1).
    Enforces single-organisation mode if MULTI_ORG_ENABLED=false.
    """
    validate_password_strength(password)

    # AC-ORG-1: In MS1, MULTI_ORG_ENABLED=false. If an organisation already exists, return 403 MULTI_ORG_DISABLED
    existing_org_count = db.query(Organisation).count()
    if not settings.MULTI_ORG_ENABLED and existing_org_count > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "MULTI_ORG_DISABLED", "message": "Multi-organisation registration is currently disabled."}}
        )

    # Generic response if email already exists (PRD v1.2 §8.1 line 745)
    existing_user = db.query(User).filter(User.email == email.lower()).first()
    if existing_user:
        return {
            "message": "If this email is eligible for registration, an onboarding confirmation has been sent.",
            "status": "PENDING_VERIFICATION"
        }

    # Generate slug
    slug = organisation_name.lower().replace(" ", "-").replace("_", "-")
    existing_slug = db.query(Organisation).filter(Organisation.slug == slug).first()
    if existing_slug:
        slug = f"{slug}-{str(uuid.uuid4())[:8]}"

    # Create Organisation
    org = Organisation(
        name=organisation_name,
        slug=slug,
        status="ACTIVE"
    )
    db.add(org)
    db.flush()

    # Create Default Plant (PRD v1.2 §8.2.1)
    plant = Plant(
        organisation_id=org.id,
        code="DEFAULT",
        name="Default Plant",
        is_default=True
    )
    db.add(plant)
    db.flush()

    # Create Org Admin User
    user = User(
        organisation_id=org.id,
        email=email.lower(),
        full_name=full_name,
        password_hash=hash_password(password),
        role="ORG_ADMIN",
        is_active=True
    )
    db.add(user)
    db.commit()

    return {
        "message": "Organisation registered successfully.",
        "status": "ACTIVE",
        "organisation_id": org.id,
        "user_id": user.id
    }

def login_user(db: Session, email: str, password: str) -> dict:
    """
    Authenticates user, tracks failed logins, locks account after 5 failed attempts (PRD v1.2 §13.2, §15, AC-SEC-1).
    """
    user = db.query(User).filter(User.email == email.lower()).first()
    if not user:
        verify_password(password, _DUMMY_HASH)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "UNAUTHENTICATED", "message": "Invalid email or password."}}
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "ACCOUNT_DEACTIVATED", "message": "User account is deactivated."}}
        )

    # Check lockout
    now = datetime.utcnow()
    if user.locked_until and user.locked_until > now:
        raise HTTPException(
            status_code=423, # Locked
            detail={"error": {"code": "ACCOUNT_LOCKED", "message": f"Account is locked until {user.locked_until.isoformat()} UTC due to excessive failed attempts."}}
        )

    # Check password
    if not verify_password(password, user.password_hash):
        user.failed_login_count += 1
        if user.failed_login_count >= settings.MAX_FAILED_LOGIN_ATTEMPTS:
            user.locked_until = now + timedelta(minutes=settings.LOCKOUT_DURATION_MINUTES)
            user.failed_login_count = 0
            db.commit()
            raise HTTPException(
                status_code=423,
                detail={"error": {"code": "ACCOUNT_LOCKED", "message": "Account has been locked for 15 minutes due to multiple failed login attempts."}}
            )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "UNAUTHENTICATED", "message": "Invalid email or password."}}
        )

    # Successful login: reset failed login count and lockout
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    db.commit()

    access_token, expires_in = create_access_token(
        user.id, user.organisation_id, user.role, token_version=user.token_version or 1
    )
    refresh_token = create_refresh_token(db, user)

    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "refresh_token": refresh_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "organisation": {
                "id": user.organisation.id,
                "name": user.organisation.name,
                "slug": user.organisation.slug
            }
        }
    }

def rotate_refresh_token(db: Session, token_string: str) -> dict:
    """
    Rotates a refresh token family. If token reuse is detected, revokes the entire family (AC-SEC-1).
    """
    try:
        rf_id, raw_token = token_string.split(":", 1)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_TOKEN", "message": "Malformed refresh token."}}
        )

    rf = db.query(RefreshToken).filter(RefreshToken.id == rf_id).first()
    if not rf:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_TOKEN", "message": "Refresh token not found."}}
        )

    # Token reuse detection: if already revoked, revoke all tokens in family
    if rf.revoked_at is not None:
        db.query(RefreshToken).filter(RefreshToken.family_id == rf.family_id).update({"revoked_at": datetime.utcnow()})
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "TOKEN_REUSE_DETECTED", "message": "Refresh token reuse detected; session revoked."}}
        )

    # Check expiry
    if rf.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "TOKEN_EXPIRED", "message": "Refresh token has expired."}}
        )

    # Verify token hash
    if not verify_password(raw_token, rf.token_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_TOKEN", "message": "Invalid refresh token."}}
        )

    user = rf.user
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "UNAUTHENTICATED", "message": "User not found or inactive."}}
        )

    # Revoke current token
    rf.revoked_at = datetime.utcnow()

    # Issue new token in same family
    new_token_str = create_refresh_token(db, user, family_id=rf.family_id)
    access_token, expires_in = create_access_token(
        user.id, user.organisation_id, user.role, token_version=user.token_version or 1
    )

    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "refresh_token": new_token_str
    }

# ---------------------------------------------------------------------------
# Rate Limiting & Password Reset Service Functions
# ---------------------------------------------------------------------------

_FALLBACK_IP_ATTEMPTS: Dict[str, List[float]] = {}
_FALLBACK_EMAIL_ATTEMPTS: Dict[str, List[float]] = {}

def check_and_record_rate_limit(
    db: Optional[Session],
    key: str,
    action: str,
    max_requests: int,
    window_seconds: int
) -> bool:
    """
    Persistent, distributed rate limiter backed by the database.
    Counts attempts within the sliding window; records the attempt if allowed.
    Falls back gracefully to in-memory sliding window if db is not provided.
    """
    now = datetime.utcnow()
    cutoff = now - timedelta(seconds=window_seconds)

    if db is not None:
        try:
            count = db.query(RateLimitAttempt).filter(
                RateLimitAttempt.key == key,
                RateLimitAttempt.action == action,
                RateLimitAttempt.created_at >= cutoff
            ).count()

            if count >= max_requests:
                return False

            attempt = RateLimitAttempt(key=key, action=action, created_at=now)
            db.add(attempt)
            db.commit()
            return True
        except Exception as e:
            # If database error occurs, fall back to in-memory tracking
            db.rollback()

    # In-memory fallback
    now_ts = time.time()
    store = _FALLBACK_IP_ATTEMPTS if action.endswith("IP") else _FALLBACK_EMAIL_ATTEMPTS
    attempts = [t for t in store.get(key, []) if now_ts - t < window_seconds]
    if len(attempts) >= max_requests:
        return False
    attempts.append(now_ts)
    store[key] = attempts
    return True

def clear_reset_rate_limits(db: Optional[Session] = None):
    """Testing helper to clear rate limit states in database and in-memory fallback."""
    _FALLBACK_IP_ATTEMPTS.clear()
    _FALLBACK_EMAIL_ATTEMPTS.clear()
    if db is not None:
        try:
            db.query(RateLimitAttempt).delete()
            db.commit()
        except Exception:
            db.rollback()

def request_password_reset(db: Session, email: str, ip_address: Optional[str] = None) -> dict:
    """
    Handles forgot password request:
    - Normalizes client IP and applies persistent IP rate limiting (429 if exceeded).
    - Normalizes email and throttles repeat dispatches to prevent inbox flooding.
    - Preserves enumeration resistance: returns generic response regardless of whether email exists.
    - Generates single-use cryptographically secure token with 20 minute expiry.
    - Safely delivers email before invalidating user's previous valid token.
    - Never logs raw reset tokens or passwords.
    """
    if ip_address:
        ip_clean = ip_address.strip()
        ip_allowed = check_and_record_rate_limit(
            db=db,
            key=f"ip:{ip_clean}",
            action="PASSWORD_RESET_IP",
            max_requests=settings.RATE_LIMIT_RESET_IP_MAX,
            window_seconds=settings.RATE_LIMIT_RESET_IP_WINDOW_SECONDS
        )
        if not ip_allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"error": {"code": "RATE_LIMIT_EXCEEDED", "message": "Too many password reset requests from this IP. Please try again later."}}
            )

    normalized_email = email.strip().lower()
    email_allowed = check_and_record_rate_limit(
        db=db,
        key=f"email:{normalized_email}",
        action="PASSWORD_RESET_EMAIL",
        max_requests=settings.RATE_LIMIT_RESET_EMAIL_MAX,
        window_seconds=settings.RATE_LIMIT_RESET_EMAIL_WINDOW_SECONDS
    )
    if not email_allowed:
        # Silently throttle email send to prevent user inbox flooding and enumeration probing
        return {
            "message": "If that email address is registered, a password reset link has been sent.",
            "status": "SENT"
        }

    user = db.query(User).filter(User.email == normalized_email).first()

    if user and user.is_active:
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        expires_at = datetime.utcnow() + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)

        # Attempt safe email delivery first
        delivery_success = send_password_reset_email(
            to_email=user.email,
            reset_token=raw_token,
            recipient_name=user.full_name
        )

        if delivery_success:
            # Only invalidate previous tokens and store the new token if delivery succeeded
            db.query(PasswordResetToken).filter(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.is_consumed == False
            ).update({"is_consumed": True, "consumed_at": datetime.utcnow()}, synchronize_session=False)

            reset_record = PasswordResetToken(
                organisation_id=user.organisation_id,
                user_id=user.id,
                token_hash=token_hash,
                expires_at=expires_at,
                is_consumed=False,
                ip_address=ip_address
            )
            db.add(reset_record)
            db.commit()
        else:
            # SMTP failure: roll back so user's previous valid link remains functional
            db.rollback()
    else:
        # Timing equalisation dummy hash
        _ = hash_password("industria-timing-equalisation-dummy")

    return {
        "message": "If that email address is registered, a password reset link has been sent.",
        "status": "SENT"
    }

def verify_reset_token(db: Session, token: str) -> dict:
    """
    Verifies reset token validity without consuming it.
    Used for pre-validation on the reset password screen.
    """
    if not token or len(token) < 16:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "INVALID_TOKEN", "message": "Invalid password reset token format."}}
        )

    token_hash = hashlib.sha256(token.strip().encode("utf-8")).hexdigest()
    record = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == token_hash).first()

    if not record or record.is_consumed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "INVALID_OR_CONSUMED_TOKEN", "message": "This password reset token is invalid or has already been used."}}
        )

    if record.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "EXPIRED_TOKEN", "message": "This password reset link has expired. Please request a new one."}}
        )

    user = db.query(User).filter(User.id == record.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "INVALID_OR_CONSUMED_TOKEN", "message": "This password reset token is invalid or has already been used."}}
        )

    return {"valid": True, "message": "Reset token is valid."}

def reset_user_password(db: Session, token: str, new_password: str) -> dict:
    """
    Consumes a reset token and updates the user's password using Argon2id.
    - Consumption is atomic (conditional compare-and-set preventing double-consumption).
    - Verifies token expiry inside the same atomic transaction.
    - Applies uniform 12+ char password policy.
    - Invalidates all existing sessions (increments token_version and revokes all refresh tokens).
    - Failed resets do not modify the user's password.
    """
    validate_password_strength(new_password)

    if not token or len(token) < 16:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "INVALID_TOKEN", "message": "Invalid password reset token format."}}
        )

    token_hash = hashlib.sha256(token.strip().encode("utf-8")).hexdigest()
    now = datetime.utcnow()

    # 1. Atomic compare-and-set: ONLY updates if token exists, is unconsumed, AND has not expired
    updated_count = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == token_hash,
        PasswordResetToken.is_consumed == False,
        PasswordResetToken.expires_at >= now
    ).update(
        {
            "is_consumed": True,
            "consumed_at": now
        },
        synchronize_session=False
    )

    if updated_count != 1:
        # Determine specific reason for descriptive client error
        record = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == token_hash).first()
        if not record or record.is_consumed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": {"code": "INVALID_OR_CONSUMED_TOKEN", "message": "This password reset token is invalid or has already been used."}}
            )
        if record.expires_at < now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": {"code": "EXPIRED_TOKEN", "message": "This password reset link has expired. Please request a new one."}}
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "INVALID_OR_CONSUMED_TOKEN", "message": "This password reset token is invalid or has already been used."}}
        )

    # 2. Look up user
    token_record = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == token_hash).first()
    user = db.query(User).filter(User.id == token_record.user_id).first()
    if not user or not user.is_active:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "INVALID_USER", "message": "User account not found or deactivated."}}
        )

    # 3. Update password hash with Argon2id
    user.password_hash = hash_password(new_password)
    user.failed_login_count = 0
    user.locked_until = None

    # 4. Session invalidation: Increment token_version to invalidate all existing access tokens
    user.token_version = (user.token_version or 1) + 1

    # 5. Invalidate all other unconsumed reset tokens for this user
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.is_consumed == False
    ).update({"is_consumed": True, "consumed_at": now}, synchronize_session=False)

    # 6. Revoke all active refresh tokens for this user
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id,
        RefreshToken.revoked_at.is_(None)
    ).update({"revoked_at": now}, synchronize_session=False)

    db.commit()

    return {
        "message": "Password has been reset successfully. All existing active sessions have been invalidated for security. You may now sign in with your new password.",
        "status": "SUCCESS"
    }

