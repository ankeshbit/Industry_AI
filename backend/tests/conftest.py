"""
Pytest Fixtures for INDUSTRIA AI Backend Tests (PRD v1.2)
Provides isolated test database, seed data, FastAPI TestClient, and tenant fixtures.
"""

import os
import tempfile
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.config import settings
from backend.app.database import Base, get_db
from backend.app.seed import seed_database
from backend.app.main import app
from backend.app.models.auth import Organisation, User, Plant
from backend.app.services.auth_service import hash_password, create_access_token

@pytest.fixture(scope="session")
def test_db_path():
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_industria.db")
    yield db_path
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception:
            pass

@pytest.fixture(scope="function")
def db_session(test_db_path):
    engine = create_engine(
        f"sqlite:///{test_db_path}",
        connect_args={"check_same_thread": False}
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Drop and recreate all tables for clean test isolation
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    session = TestingSessionLocal()
    seed_database(session)
    
    yield session
    
    session.close()

@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def tenant_fixture(db_session):
    """Creates Org A with default plant and Org Admin user, returns user and auth headers."""
    org = Organisation(name="Acme Precision Machining", slug="acme-precision", status="ACTIVE")
    db_session.add(org)
    db_session.flush()

    plant = Plant(organisation_id=org.id, code="DEFAULT", name="Default Plant", is_default=True)
    db_session.add(plant)
    db_session.flush()

    user = User(
        organisation_id=org.id,
        email="admin@acmeprecision.com",
        full_name="Alice Admin",
        password_hash=hash_password("SuperSecretPassword123!"),
        role="ORG_ADMIN",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()

    token, _ = create_access_token(user.id, org.id, user.role)
    headers = {"Authorization": f"Bearer {token}"}
    return {
        "org": org,
        "plant": plant,
        "user": user,
        "headers": headers
    }

@pytest.fixture(scope="function")
def two_tenants_fixture(db_session):
    """Creates two distinct organisations for tenant isolation testing (AC-ORG-2)."""
    # Tenant 1
    org1 = Organisation(name="Tenant One Inc", slug="tenant-one", status="ACTIVE")
    db_session.add(org1)
    db_session.flush()

    plant1 = Plant(organisation_id=org1.id, code="DEFAULT", name="Plant One", is_default=True)
    db_session.add(plant1)
    db_session.flush()

    user1 = User(
        organisation_id=org1.id,
        email="user1@tenantone.com",
        full_name="User One",
        password_hash=hash_password("PasswordOne123!"),
        role="ORG_ADMIN",
        is_active=True
    )
    db_session.add(user1)

    # Tenant 2
    org2 = Organisation(name="Tenant Two Inc", slug="tenant-two", status="ACTIVE")
    db_session.add(org2)
    db_session.flush()

    plant2 = Plant(organisation_id=org2.id, code="DEFAULT", name="Plant Two", is_default=True)
    db_session.add(plant2)
    db_session.flush()

    user2 = User(
        organisation_id=org2.id,
        email="user2@tenanttwo.com",
        full_name="User Two",
        password_hash=hash_password("PasswordTwo123!"),
        role="ORG_ADMIN",
        is_active=True
    )
    db_session.add(user2)
    db_session.commit()

    token1, _ = create_access_token(user1.id, org1.id, user1.role)
    token2, _ = create_access_token(user2.id, org2.id, user2.role)

    return {
        "tenant1": {"org": org1, "user": user1, "headers": {"Authorization": f"Bearer {token1}"}},
        "tenant2": {"org": org2, "user": user2, "headers": {"Authorization": f"Bearer {token2}"}}
    }

