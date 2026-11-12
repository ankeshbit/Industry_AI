"""
Database Engine and Session Configuration for INDUSTRIA AI (PRD v1.2 §12)
Supports PostgreSQL for production with SQLite fallback for local test execution.
Enforces foreign key checks and provides TenantContext binding.
"""

import sqlite3
from contextvars import ContextVar
from typing import Generator, Optional
import uuid
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.engine import Engine
from backend.app.config import settings

# Thread-local / ContextVar for tenant isolation (PRD v1.2 §8.1)
current_tenant_id: ContextVar[Optional[uuid.UUID]] = ContextVar("current_tenant_id", default=None)

# Engine setup
connect_args = {}
engine_kwargs = {
    "pool_pre_ping": True,
    "echo": False,
}

if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
else:
    # Neon PostgreSQL configuration with serverless pooling & SSL support (PRD v1.2 §12)
    # - pool_pre_ping: validates connections on checkout (handles cold-starts and compute resumes)
    # - pool_recycle: proactively recycles idle connections before PgBouncer timeouts
    # - pool_size / max_overflow: bounds client connections for serverless compute limits
    engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_recycle": 300,
        "pool_timeout": 30,
    })
    if "sslmode=" not in settings.DATABASE_URL.lower():
        connect_args["sslmode"] = "require"

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    **engine_kwargs
)

# Enable SQLite foreign key support
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    # Decide from the actual DBAPI connection: other engines (e.g. test engines) must also get FK enforcement,
    # and a PostgreSQL connection must never receive a SQLite PRAGMA.
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """Dependency that yields a database session and handles rollback/close."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

