from __future__ import annotations

from collections.abc import Iterable

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_EXTENSION_AVAILABILITY_CACHE: dict[str, bool] = {}
_MISSING_EXTENSION_LOGGED: set[str] = set()

_ALLOWED_EXTENSIONS = frozenset({
    "vector",
    "age",
    "pg_stat_statements",
    "pg_trgm",
    "btree_gin",
    "uuid-ossp",
})


async def ensure_database_extensions(
    session: AsyncSession,
    extensions: Iterable[str],
) -> dict[str, bool]:
    results: dict[str, bool] = {}

    for extension in extensions:
        available = await _ensure_database_extension(session, extension)
        results[extension] = available
        _EXTENSION_AVAILABILITY_CACHE[extension] = available

    return results


async def is_database_extension_available(
    session: AsyncSession,
    extension: str,
    *,
    refresh: bool = False,
) -> bool:
    if not refresh and extension in _EXTENSION_AVAILABILITY_CACHE:
        return _EXTENSION_AVAILABILITY_CACHE[extension]

    installed = await _extension_installed(session, extension)
    _EXTENSION_AVAILABILITY_CACHE[extension] = installed

    if not installed and extension not in _MISSING_EXTENSION_LOGGED:
        logger.warning(f"Database extension '{extension}' is unavailable; related features will use fallback paths")
        _MISSING_EXTENSION_LOGGED.add(extension)

    return installed


async def is_vector_extension_available(session: AsyncSession, *, refresh: bool = False) -> bool:
    return await is_database_extension_available(session, "vector", refresh=refresh)


async def _ensure_database_extension(session: AsyncSession, extension: str) -> bool:
    if extension not in _ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Unknown database extension '{extension}'. "
            f"Allowed extensions: {sorted(_ALLOWED_EXTENSIONS)}"
        )
    if await _extension_installed(session, extension):
        return True

    available_result = await session.execute(
        text("SELECT EXISTS(SELECT 1 FROM pg_available_extensions WHERE name = :name)"),
        {"name": extension},
    )
    if not bool(available_result.scalar()):
        if extension not in _MISSING_EXTENSION_LOGGED:
            logger.warning(f"Database extension '{extension}' is not available in the current PostgreSQL image")
            _MISSING_EXTENSION_LOGGED.add(extension)
        return False

    try:
        await session.execute(text(f"CREATE EXTENSION IF NOT EXISTS {extension}"))
        await session.commit()
    except Exception as exc:
        await session.rollback()
        logger.warning(f"Failed to create database extension '{extension}': {exc}")
        return False

    return await _extension_installed(session, extension)


async def _extension_installed(session: AsyncSession, extension: str) -> bool:
    result = await session.execute(
        text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = :name)"),
        {"name": extension},
    )
    return bool(result.scalar())
