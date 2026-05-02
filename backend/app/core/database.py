"""
Sync database session helper (legacy compatibility).
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db.url import to_sync_database_url


def _sync_database_url(url: str) -> str:
    return to_sync_database_url(url)


def resolve_service_database_url() -> str:
    """Return the effective DSN after optional service-role RBAC selection."""
    return settings.DATABASE_URL


SessionLocal = None

if resolve_service_database_url():
    sync_url = _sync_database_url(resolve_service_database_url())
    engine = create_engine(
        sync_url,
        pool_pre_ping=True,
        future=True,
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
