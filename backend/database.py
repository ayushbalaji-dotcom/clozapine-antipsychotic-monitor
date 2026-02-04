from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .config import get_settings
from .models.base import Base

_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is not None:
        return _engine
    settings = get_settings()
    connect_args = {}
    if settings.DATABASE_URL.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    kwargs = {
        "pool_pre_ping": True,
        "future": True,
        "connect_args": connect_args,
    }
    if not settings.DATABASE_URL.startswith("sqlite"):
        kwargs["pool_size"] = settings.DB_POOL_SIZE
    _engine = create_engine(settings.DATABASE_URL, **kwargs)
    return _engine


def get_sessionmaker():
    global _SessionLocal
    if _SessionLocal is not None:
        return _SessionLocal
    _SessionLocal = sessionmaker(bind=get_engine(), autocommit=False, autoflush=False)
    return _SessionLocal


def reset_engine() -> None:
    global _engine, _SessionLocal
    _engine = None
    _SessionLocal = None


def init_db() -> None:
    Base.metadata.create_all(bind=get_engine())


def get_db():
    SessionLocal = get_sessionmaker()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
