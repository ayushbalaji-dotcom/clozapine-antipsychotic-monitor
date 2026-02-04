import os
from pathlib import Path
import pytest
from cryptography.fernet import Fernet

# Ensure critical env vars are set before backend imports
os.environ.setdefault("FIELD_ENCRYPTION_KEY", Fernet.generate_key().decode("utf-8"))
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("AUTH_MODE", "dev_stub")
os.environ.setdefault("TASK_WINDOW_DAYS", "14")
os.environ.setdefault("SCHEDULING_HORIZON_YEARS", "5")


@pytest.fixture
def db_session(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{db_path}")

    from backend.config import get_settings
    from backend.database import reset_engine, get_engine, get_sessionmaker
    from backend.models.base import Base

    get_settings.cache_clear()
    reset_engine()
    engine = get_engine()
    Base.metadata.create_all(bind=engine)

    SessionLocal = get_sessionmaker()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
