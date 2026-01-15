"""
Database URL helpers.
Normalize async/sync driver usage for SQLAlchemy and Alembic.
"""
from sqlalchemy.engine import make_url


def to_async_database_url(url: str) -> str:
    if not url:
        return url
    parsed = make_url(url)
    driver = parsed.drivername

    if driver in ("postgres", "postgresql"):
        driver = "postgresql+asyncpg"
    elif driver.startswith("postgresql+") and not driver.endswith("asyncpg"):
        driver = "postgresql+asyncpg"
    elif driver == "sqlite":
        driver = "sqlite+aiosqlite"

    return str(parsed.set(drivername=driver))


def to_sync_database_url(url: str) -> str:
    if not url:
        return url
    parsed = make_url(url)
    driver = parsed.drivername

    if driver.startswith("postgresql"):
        driver = "postgresql"
    elif driver == "postgres":
        driver = "postgresql"
    elif driver == "sqlite+aiosqlite":
        driver = "sqlite"

    return str(parsed.set(drivername=driver))
