"""
Sync database session helper (legacy compatibility).
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings


def _sync_database_url(url: str) -> str:
    if url.startswith("postgresql+asyncpg"):
        return url.replace("postgresql+asyncpg", "postgresql", 1)
    if url.startswith("postgresql+psycopg"):
        return url.replace("postgresql+psycopg", "postgresql", 1)
    return url


SessionLocal = None

if settings.DATABASE_URL:
    sync_url = _sync_database_url(settings.DATABASE_URL)
    engine = create_engine(
        sync_url,
        pool_pre_ping=True,
        future=True,
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
