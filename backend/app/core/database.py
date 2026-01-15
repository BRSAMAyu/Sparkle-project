"""
Sync database session helper (legacy compatibility).
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db.url import to_sync_database_url


def _sync_database_url(url: str) -> str:
    return to_sync_database_url(url)


SessionLocal = None

if settings.DATABASE_URL:
    sync_url = _sync_database_url(settings.DATABASE_URL)
    engine = create_engine(
        sync_url,
        pool_pre_ping=True,
        future=True,
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
