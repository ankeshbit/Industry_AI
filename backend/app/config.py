"""
Application Configuration Module for INDUSTRIA AI (PRD v1.2)
Loads environment settings with strict validation and safe defaults.
"""

import os
from pathlib import Path

_DEFAULT_SECRET_KEY = "industria-ai-dev-secret-key-change-in-production-1234567890"
_INSECURE_SECRETS = {
    _DEFAULT_SECRET_KEY,
    "change-this-to-a-secure-random-secret-in-production",
    "secret",
    "password",
    "admin",
    "industria",
}
# Load .env file from project root if available
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(dotenv_path=_env_path, override=False)
except ImportError:
    pass

class Settings:
    PROJECT_NAME: str = "INDUSTRIA AI"
    API_V1_PREFIX: str = "/api/v1"
    
    # Tenancy Settings (PRD v1.2 §8.1, §18.4)
    # In MS1-MS2, multi-organisation access is strictly disabled by default
    MULTI_ORG_ENABLED: bool = os.getenv("MULTI_ORG_ENABLED", "false").lower() in ("true", "1")
    
    # Security & Tokens (PRD v1.2 §15, SEC-01..SEC-05)
    APP_ENV: str = os.getenv("APP_ENV", "development").lower()
    SECRET_KEY: str = os.getenv("SECRET_KEY", _DEFAULT_SECRET_KEY)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    MAX_FAILED_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 15

    # Rate Limiting & Reverse Proxy Security Settings
    TRUSTED_PROXIES: list = [
        p.strip() for p in os.getenv("TRUSTED_PROXIES", "127.0.0.1,::1,localhost,testclient").split(",") if p.strip()
    ]
    RATE_LIMIT_RESET_IP_MAX: int = int(os.getenv("RATE_LIMIT_RESET_IP_MAX", "5"))
    RATE_LIMIT_RESET_IP_WINDOW_SECONDS: int = int(os.getenv("RATE_LIMIT_RESET_IP_WINDOW_SECONDS", "900"))  # 15 min
    RATE_LIMIT_RESET_EMAIL_MAX: int = int(os.getenv("RATE_LIMIT_RESET_EMAIL_MAX", "3"))
    RATE_LIMIT_RESET_EMAIL_WINDOW_SECONDS: int = int(os.getenv("RATE_LIMIT_RESET_EMAIL_WINDOW_SECONDS", "900"))  # 15 min

    # Password Reset & Email Settings
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 20
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "noreply@industria-ai.com")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "INDUSTRIA AI")
    SMTP_TLS: bool = os.getenv("SMTP_TLS", "true").lower() in ("true", "1")
    SMTP_SSL: bool = os.getenv("SMTP_SSL", "false").lower() in ("true", "1")
    
    # Supabase Authentication Settings (Hybrid Auth)
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "").rstrip("/")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "")
    
    @property
    def is_supabase_enabled(self) -> bool:
        return bool(self.SUPABASE_URL and (self.SUPABASE_JWT_SECRET or self.SUPABASE_ANON_KEY))
    
    # Database (PRD v1.2 §12)
    # Supports PostgreSQL / Neon PostgreSQL with connection pooling and SSL, or SQLite fallback
    _raw_db_url: str = os.getenv("DATABASE_URL", "sqlite:///./industria_ai.db")
    if _raw_db_url.startswith("postgres://"):
        _raw_db_url = _raw_db_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif _raw_db_url.startswith("postgresql://") and not _raw_db_url.startswith("postgresql+"):
        _raw_db_url = _raw_db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    DATABASE_URL: str = _raw_db_url
    
    # Job Queue & Execution Settings (PRD v1.2 §8.5)
    JOB_EXECUTION_MODE: str = os.getenv("JOB_EXECUTION_MODE", "inline").lower()  # "inline" or "async"
    JOB_HEARTBEAT_INTERVAL_SECONDS: float = float(os.getenv("JOB_HEARTBEAT_INTERVAL_SECONDS", "2.0"))
    JOB_STALE_TIMEOUT_SECONDS: int = int(os.getenv("JOB_STALE_TIMEOUT_SECONDS", "60"))
    JOB_MAX_ATTEMPTS: int = int(os.getenv("JOB_MAX_ATTEMPTS", "3"))

    # CORS Origins (PRD v1.2 §11.1, SEC-05)
    _raw_cors: str = os.getenv("CORS_ORIGINS", "")
    if _raw_cors:
        CORS_ORIGINS: list = [origin.strip() for origin in _raw_cors.split(",") if origin.strip()]
    elif os.getenv("APP_ENV", "development").lower() == "production":
        CORS_ORIGINS: list = [os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")]
    else:
        CORS_ORIGINS: list = [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "*"
        ]

    # Storage (PRD v1.2 §12.3)
    # Keys always follow org/{organisation_id}/datasets/{id}/v{n}/{uuid}.csv
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    STORAGE_DIR: Path = BASE_DIR / "storage"
    MAX_UPLOAD_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
    MAX_CSV_ROWS: int = 500000
    MAX_CSV_COLUMNS: int = int(os.getenv("MAX_CSV_COLUMNS", "200"))

    def get_redacted_database_url(self) -> str:
        """Returns DATABASE_URL with user credentials redacted for safe logging and telemetry."""
        url = self.DATABASE_URL
        if "@" in url and "://" in url:
            scheme, rest = url.split("://", 1)
            auth, host = rest.split("@", 1)
            if ":" in auth:
                user, _ = auth.split(":", 1)
                return f"{scheme}://{user}:***@{host}"
            return f"{scheme}://***@{host}"
        return url

    def validate_configuration(self) -> None:
        """
        Validates required environment variables and production security thresholds.
        Fails fast at startup if insecure settings or default credentials are used in production.
        """
        if self.APP_ENV == "production":
            # 1. Enforce strong, non-default SECRET_KEY (minimum 32 characters)
            if not self.SECRET_KEY or self.SECRET_KEY in _INSECURE_SECRETS:
                raise RuntimeError(
                    "CRITICAL SECURITY CONFIGURATION ERROR: SECRET_KEY must be set to a strong, "
                    "unique secret in production. Default development keys are strictly forbidden."
                )
            if len(self.SECRET_KEY) < 32:
                raise RuntimeError(
                    f"CRITICAL SECURITY CONFIGURATION ERROR: Production SECRET_KEY length ({len(self.SECRET_KEY)}) "
                    "is below minimum required length of 32 characters."
                )

            # 2. Database validation
            if "sqlite" in self.DATABASE_URL.lower():
                raise RuntimeError(
                    "CRITICAL CONFIGURATION ERROR: SQLite database is not permitted in production. "
                    "Configure a resilient PostgreSQL instance with SSL enabled via DATABASE_URL."
                )
            if "industria_dev_password" in self.DATABASE_URL:
                raise RuntimeError(
                    "CRITICAL SECURITY CONFIGURATION ERROR: Default development password detected in production DATABASE_URL. "
                    "Set a secure, unique password in your production environment."
                )

            # 3. CORS validation
            if "*" in self.CORS_ORIGINS:
                raise RuntimeError(
                    "CRITICAL SECURITY CONFIGURATION ERROR: Wildcard '*' CORS origin is strictly forbidden in production. "
                    "Configure specific allowed frontend origins via CORS_ORIGINS."
                )

            # 4. Supabase validation if enabled
            if self.is_supabase_enabled:
                if not self.SUPABASE_JWT_SECRET and not self.SUPABASE_ANON_KEY:
                    raise RuntimeError(
                        "CRITICAL SECURITY CONFIGURATION ERROR: Supabase authentication enabled in production but missing "
                        "SUPABASE_JWT_SECRET."
                    )

settings = Settings()

# Validate configuration on import
settings.validate_configuration()

# Ensure local storage directory exists
settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
