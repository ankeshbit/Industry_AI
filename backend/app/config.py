"""
Application Configuration Module for INDUSTRIA AI (PRD v1.2)
Loads environment settings with strict validation and safe defaults.
"""

import os
from pathlib import Path

class Settings:
    PROJECT_NAME: str = "INDUSTRIA AI"
    API_V1_PREFIX: str = "/api/v1"
    
    # Tenancy Settings (PRD v1.2 §8.1, §18.4)
    # In MS1-MS2, multi-organisation access is strictly disabled by default
    MULTI_ORG_ENABLED: bool = os.getenv("MULTI_ORG_ENABLED", "false").lower() in ("true", "1")
    
    # Security & Tokens (PRD v1.2 §15, SEC-01..SEC-05)
    SECRET_KEY: str = os.getenv("SECRET_KEY", "industria-ai-dev-secret-key-change-in-production-1234567890")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    MAX_FAILED_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 15
    
    # Database (PRD v1.2 §12)
    # Default to sqlite for instant local test execution, easily overridden by PostgreSQL URL
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./industria_ai.db")
    
    # Storage (PRD v1.2 §12.3)
    # Keys always follow org/{organisation_id}/datasets/{id}/v{n}/{uuid}.csv
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    STORAGE_DIR: Path = BASE_DIR / "storage"
    MAX_UPLOAD_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
    MAX_CSV_ROWS: int = 500000

settings = Settings()

# Ensure local storage directory exists
settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
