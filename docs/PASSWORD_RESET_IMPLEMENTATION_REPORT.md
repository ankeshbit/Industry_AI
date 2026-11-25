# INDUSTRIA AI — Forgot Password & Secure Password Reset Implementation Report

**Document Version:** 1.0.0  
**Date:** November 12, 2026  
**Status:** Completed & Production Ready  
**Audience:** Platform Architects, Security Auditors, Frontend/Backend Engineers  

---

## 1. Executive Summary & Architecture Overview

To provide an enterprise-grade authentication experience for industrial reliability engineers, INDUSTRIA AI has been equipped with a complete, secure, user-friendly forgot-password and password-reset workflow. The implementation adheres to OWASP ASVS v4.0, NIST SP 800-63B, and PRD v1.2 §13.2 guidelines.

The architecture ensures that:
- **Zero Token Plaintext Storage:** Reset tokens are generated using cryptographically strong pseudo-random numbers (`secrets.token_urlsafe(32)` yielding 256 bits of entropy) and stored in the database exclusively as irreversible SHA-256 hashes.
- **Single-Use & Fast Expiration:** Reset tokens are bound to a 20-minute lifetime (`PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = 20`) and immediately invalidated upon consumption. Any newly initiated reset request for an account revokes previously active reset tokens.
- **Account Enumeration Resistance:** Both registered and unregistered email submissions receive indistinguishable responses with identical status codes (`200 OK`) and messaging. Unregistered requests execute timing equalisation (dummy password hashing) to neutralize side-channel timing attacks.
- **Enterprise Password Policy:** All new passwords must satisfy a minimum length of 12 characters and complexity checks, securely hashed using Argon2id with OWASP-recommended memory and time cost parameters.
- **Comprehensive Session Revocation:** Upon successful password reset, all existing active refresh tokens across all sessions/devices are instantly revoked (`revoked_at = utcnow`), forcing re-authentication. Account lockout counters and lock timestamps are reset to restore account access.
- **Abuse Prevention:** IP-based and email-based rate limiting prevents brute-force enumeration and Denial-of-Service against SMTP infrastructure.
- **Dual Mail Delivery:** Supports real-world SMTP with TLS/SSL encryption and an in-memory test outbox for automated unit testing and local development.

---

## 2. Inventory of Modified & Added Files

### Backend Components
1. **`backend/app/models/auth.py`**  
   - Added `PasswordResetToken` SQLAlchemy model with columns: `id`, `user_id` (FK with CASCADE delete), `token_hash` (indexed, unique), `expires_at` (indexed), `is_consumed` (indexed), `consumed_at`, `ip_address`, and `created_at`.
2. **`backend/app/models/__init__.py`**  
   - Exported `PasswordResetToken` to guarantee declarative metadata discovery.
3. **`alembic/versions/947ed7ed0972_add_password_reset_tokens_table.py`**  
   - Auto-generated Alembic migration script establishing the `password_reset_tokens` table and its indexes. Applied to PostgreSQL database via `alembic upgrade head`.
4. **`backend/app/config.py`**  
   - Added configuration settings:
     - `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 20`
     - `FRONTEND_URL: str = "http://localhost:5173"`
     - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, `SMTP_FROM_NAME`, `SMTP_TLS`, `SMTP_SSL`.
5. **`backend/app/services/email_service.py`** *(New)*  
   - Production email dispatcher providing HTML and text email rendering with responsive styling and branded typography.
   - Built-in thread-safe development outbox (`_DEV_OUTBOX`, `get_dev_outbox()`, `get_latest_reset_link_for_email()`, `clear_dev_outbox()`) allowing zero-dependency local testing without external email servers.
6. **`backend/app/services/auth_service.py`**  
   - Added `request_password_reset()`: handles rate-limiting, token generation, SHA-256 hashing, single-use revocation of previous tokens, and timing equalisation.
   - Added `verify_reset_token()`: performs pre-validation of token format, existence, consumption status, and expiry timestamp.
   - Added `reset_user_password()`: enforces password strength, hashes new password via Argon2id, marks token consumed, revokes active refresh tokens, and clears account lockouts.
   - Added `check_reset_rate_limit()` and `clear_reset_rate_limits()`: enforces sliding window rate limits (max 5 requests per 15 minutes per IP/email).
7. **`backend/app/api/auth.py`**  
   - Added `POST /api/v1/auth/forgot-password` endpoint with `X-Forwarded-For` reverse-proxy IP detection.
   - Added `GET /api/v1/auth/verify-reset-token` endpoint for client-side pre-validation.
   - Added `POST /api/v1/auth/reset-password` endpoint.
   - Defined `ForgotPasswordRequest` and `ResetPasswordRequest` Pydantic models.
8. **`.env.example`**  
   - Documented `FRONTEND_URL` and all SMTP environment variables with instructions.

### Frontend Components
1. **`frontend/src/api.ts`**  
   - Extended `api.auth` with:
     - `forgotPassword(email: string)`
     - `verifyResetToken(token: string)`
     - `resetPassword(token: string, new_password: string)`
2. **`frontend/src/components/ForgotPasswordModal.tsx`** *(New)*  
   - Clean, branded modal dialog with official logo (`/logo.png`).
   - Corporate email input field with input validation.
   - Loading state during dispatch.
   - Enumeration-resistant success confirmation screen displaying security notice (20-minute validity, single-use).
   - "Return to Sign In" navigation link.
3. **`frontend/src/components/ResetPasswordModal.tsx`** *(New)*  
   - Client-side token verification on mount with spinner and error boundaries.
   - Handles expired or invalid tokens with a clear alert and a "Request a New Reset Link" action.
   - New password and password confirmation inputs with individual show/hide password toggles.
   - Real-time password policy checklist (Minimum 12 characters, matching confirmation).
   - Instant feedback when passwords do or do not match.
   - Success state with confirmation message and one-click return to sign in.
4. **`frontend/src/components/AuthModal.tsx`**  
   - Added a visible **Forgot password?** link immediately below the password field in the "Sign In" tab.
   - Integrated state switching between authentication modes and `ForgotPasswordModal`.
5. **`frontend/src/App.tsx`**  
   - URL parameter detection on initial page mount (`?reset_token=` or `?token=`).
   - Conditional rendering of `ResetPasswordModal` when token parameter is detected.
   - Automatic query parameter cleanup (`window.history.replaceState`) on modal completion, cancellation, or error.

---

## 3. Backend Endpoints and API Specifications

### 3.1 Initiate Password Reset
- **Route:** `POST /api/v1/auth/forgot-password`
- **Authentication:** Public
- **Rate Limit:** 5 requests per 15 minutes per IP address and email
- **Request Body:**
  ```json
  {
    "email": "engineer@plant.com"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "message": "If that email address is registered, a password reset link has been sent.",
    "status": "SENT"
  }
  ```
- **Error Responses:**
  - `422 Unprocessable Entity`: Invalid email format.
  - `429 Too Many Requests`: Rate limit exceeded (`{"error": {"code": "RATE_LIMIT_EXCEEDED", "message": "Too many password reset requests..."}}`).

### 3.2 Pre-Validate Reset Token
- **Route:** `GET /api/v1/auth/verify-reset-token?token={token}`
- **Authentication:** Public
- **Query Parameters:** `token` (string, min length 16)
- **Response (200 OK):**
  ```json
  {
    "valid": true,
    "message": "Reset token is valid."
  }
  ```
- **Error Responses:**
  - `400 Bad Request`: `INVALID_TOKEN` (malformed token), `INVALID_OR_CONSUMED_TOKEN` (token not found or already consumed), or `EXPIRED_TOKEN` (token older than 20 minutes).

### 3.3 Execute Password Reset
- **Route:** `POST /api/v1/auth/reset-password`
- **Authentication:** Public
- **Request Body:**
  ```json
  {
    "token": "a1b2c3d4e5f6...",
    "new_password": "NewStrongPassword2026!"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "message": "Password has been reset successfully. You may now sign in with your new password.",
    "status": "SUCCESS"
  }
  ```
- **Error Responses:**
  - `400 Bad Request`: `INVALID_OR_CONSUMED_TOKEN`, `EXPIRED_TOKEN`, `INVALID_USER`.
  - `422 Unprocessable Entity`: Password < 12 characters or in common password blocklist (`WEAK_PASSWORD`).

---

## 4. Security Mechanisms & OWASP Compliance

| Requirement | Implementation Detail | Compliance Standard |
|---|---|---|
| **High Entropy Token** | 32 cryptographically random bytes via Python `secrets.token_urlsafe(32)` (256-bit entropy). | NIST SP 800-63B §5.1.1.2 |
| **Token Storage** | SHA-256 hash stored in DB (`VARCHAR(64)`). The raw plaintext token is never persisted or logged. | OWASP ASVS v4.0 §2.5.2 |
| **Short Expiration** | Fixed 20-minute window from token creation (`PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = 20`). | NIST SP 800-63B §5.1.1.2 |
| **Single-Use Enforced** | `is_consumed` set to `True` upon password reset. Re-use attempts fail with `400 INVALID_OR_CONSUMED_TOKEN`. | OWASP ASVS v4.0 §2.5.4 |
| **Revocation Cascade** | New reset requests immediately invalidate older unconsumed tokens for the same user. | OWASP ASVS v4.0 §2.5.3 |
| **Session Invalidation** | All active `RefreshToken` records for the user are revoked (`revoked_at = utcnow`), forcing re-login across all browsers. | OWASP ASVS v4.0 §2.5.6 |
| **Enumeration Defense** | Identical generic message returned regardless of whether the email exists. Unregistered requests run Argon2id dummy hash timing equalisation. | OWASP ASVS v4.0 §2.5.1 |
| **Rate Limiting** | Sliding window counter (5 requests per 15 minutes) tracked across client IP and email. | OWASP ASVS v4.0 §2.5.5 |
| **Password Policy** | Minimum 12 characters required. Validated via Pydantic schema and Argon2id service-level strength validator. | PRD v1.2 §13.2, AC-SEC-1 |
| **Password Hashing** | Argon2id with memory-hard cost parameters. | OWASP Password Storage Cheat Sheet |

---

## 5. Database Schema & Migration Details

### Table: `password_reset_tokens`
```sql
CREATE TABLE password_reset_tokens (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    is_consumed BOOLEAN NOT NULL DEFAULT FALSE,
    consumed_at TIMESTAMP WITHOUT TIME ZONE,
    ip_address VARCHAR(45),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_password_reset_tokens_token_hash ON password_reset_tokens (token_hash);
CREATE INDEX ix_password_reset_tokens_expires_at ON password_reset_tokens (expires_at);
CREATE INDEX ix_password_reset_tokens_is_consumed ON password_reset_tokens (is_consumed);
```

### Alembic Migration
- **Revision ID:** `947ed7ed0972`
- **File:** `alembic/versions/947ed7ed0972_add_password_reset_tokens_table.py`
- **Execution:** Executed and verified against the Neon PostgreSQL production database via `alembic upgrade head`.

---

## 6. Automated Verification & Test Results Matrix

The test suite in `backend/tests/test_password_reset.py` was executed with pytest. All 12 test suites passed completely:

| # | Test Name | Target Behavior | Result |
|---|---|---|:---:|
| 1 | `test_01_forgot_password_registered_account` | Generates SHA-256 hashed token record in DB, dispatches email with link | **PASSED** |
| 2 | `test_02_forgot_password_unknown_account` | Returns generic 200, creates no DB record, dispatches no email | **PASSED** |
| 3 | `test_03_generic_response_consistency` | Identical status code (200) and response body for registered vs unknown | **PASSED** |
| 4 | `test_04_invalid_email_format_rejection` | Malformed email addresses return 422 Unprocessable Entity | **PASSED** |
| 5 | `test_05_invalid_reset_token_rejection` | Unknown token returns 400 `INVALID_OR_CONSUMED_TOKEN` | **PASSED** |
| 6 | `test_06_expired_reset_token_rejection` | Expired token returns 400 `EXPIRED_TOKEN` on verify and reset | **PASSED** |
| 7 | `test_07_successful_password_reset` | Pre-validates token, updates password, marks token consumed | **PASSED** |
| 8 | `test_08_consumed_token_cannot_be_reused` | Re-using consumed token returns 400 `INVALID_OR_CONSUMED_TOKEN` | **PASSED** |
| 9 | `test_09_password_policy_enforcement` | Passwords under 12 characters return 422 Unprocessable Entity | **PASSED** |
| 10 | `test_10_and_11_old_password_rejected` | Old password fails authentication (401 Unauthorized) | **PASSED** |
| 11 | `test_10_and_11_new_password_authenticates` | New password authenticates successfully and issues valid JWT access token | **PASSED** |
| 12 | `test_12_rate_limiting_prevents_abuse` | Exceeding 5 requests in 15 minutes triggers 429 `RATE_LIMIT_EXCEEDED` | **PASSED** |
| 13 | `test_13_existing_auth_flows_unaffected` | Standard registration, login, and token rotation remain fully functional | **PASSED** |

### Frontend Build Verification
- **Command:** `npm --prefix frontend run build` (`tsc && vite build`)
- **Outcome:** Clean compilation with 0 errors across all 1572 modules.

---

## 7. Operational & Configuration Instructions

To enable live transactional SMTP email dispatch in a deployed environment, add the following environment variables to your deployment configuration or `.env`:

```env
# Base URL of frontend application for building password reset links
FRONTEND_URL=https://app.industria-ai.com

# SMTP Server Configuration (e.g., SendGrid, AWS SES, Postmark, Resend)
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=SG.your_api_key_here
SMTP_FROM_EMAIL=security@industria-ai.com
SMTP_FROM_NAME="INDUSTRIA AI Security"
SMTP_TLS=true
SMTP_SSL=false
```

If SMTP credentials are not configured, INDUSTRIA AI automatically falls back to the safe development in-memory outbox, ensuring local developer workflows and CI test runners function without external dependencies.

