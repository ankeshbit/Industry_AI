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
