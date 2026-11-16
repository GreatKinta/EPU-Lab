import os

# Non-production test-only secret. Integration tests require a dedicated *_test DB.
os.environ.setdefault("JWT_SECRET", "test-only-secret-with-at-least-thirty-two-characters")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import models  # noqa: F401
from app.core.db import Base, SessionLocal, engine
from app.core.security import issue_token, password_hash
from app.main import app
from app.modules.identity.models import User


@pytest.fixture
def db():
    if not engine.url.database.endswith("_test"):
        pytest.fail("Integration tests require a dedicated database ending in _test")
    with engine.begin() as connection:
        tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
        connection.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    with SessionLocal() as session:
        yield session
        session.rollback()


@pytest.fixture
def client(db, tmp_path, monkeypatch):
    from app.core.config import get_settings
    from app.modules.identity.router import _attempts

    _attempts.clear()
    monkeypatch.setattr(get_settings(), "upload_dir", tmp_path)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def accounts(db):
    result = {}
    hashed = password_hash.hash("test-password-12345")
    for role in ["student", "staff", "admin"]:
        user = User(email=f"{role}@example.test", full_name=role, role=role, password_hash=hashed)
        db.add(user)
        db.flush()
        result[role] = {"Authorization": f"Bearer {issue_token(user)}"}
        result[f"{role}_id"] = user.id
    db.commit()
    return result
