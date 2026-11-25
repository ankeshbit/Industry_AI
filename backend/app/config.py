"""
Application Configuration Module for INDUSTRIA AI (PRD v1.2)
Loads environment settings with strict validation and safe defaults.
"""

import os
from pathlib import Path

_DEFAULT_SECRET_KEY = "industria-ai-dev-secret-key-change-in-production-1234567890"
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

    # Storage (PRD v1.2 §12.3)
    # Keys always follow org/{organisation_id}/datasets/{id}/v{n}/{uuid}.csv
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    STORAGE_DIR: Path = BASE_DIR / "storage"
    MAX_UPLOAD_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
    MAX_CSV_ROWS: int = 500000

settings = Settings()

# JWTs are signed with SECRET_KEY: running production with the publicly known default lets anyone forge tokens.
if settings.APP_ENV == "production" and settings.SECRET_KEY == _DEFAULT_SECRET_KEY:
    raise RuntimeError("SECRET_KEY must be set to a strong secret when APP_ENV=production.")

# Ensure local storage directory exists
settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
