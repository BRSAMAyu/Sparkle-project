import importlib.util
from pathlib import Path

from app.config.settings import Settings


SECRET_KEY = "fv06-test-secret-key-with-enough-entropy"


def _load_migration():
    path = Path(__file__).parent / "alembic" / "versions" / "c17_20260502_create_service_roles.py"
    spec = importlib.util.spec_from_file_location("fv06_rbac_migration", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_engine_uses_engine_dsn_when_rbac_enabled() -> None:
    settings = Settings(
        _env_file=None,
        SECRET_KEY=SECRET_KEY,
        SPARKLE_RBAC_ENABLED=True,
        SERVICE_ROLE="grpc",
        DATABASE_URL="postgresql+asyncpg://postgres:legacy@sparkle_db:5432/sparkle",
        SPARKLE_ENGINE_DATABASE_URL="postgresql+asyncpg://sparkle_engine:pw@sparkle_db:5432/sparkle?sslmode=require",
    )

    assert "sparkle_engine" in settings.DATABASE_URL
    assert "sslmode=require" in settings.DATABASE_URL


def test_celery_uses_celery_dsn_when_rbac_enabled() -> None:
    settings = Settings(
        _env_file=None,
        SECRET_KEY=SECRET_KEY,
        SPARKLE_RBAC_ENABLED=True,
        SERVICE_ROLE="worker",
        DATABASE_URL="postgresql+asyncpg://postgres:legacy@sparkle_db:5432/sparkle",
        SPARKLE_ENGINE_DATABASE_URL="postgresql+asyncpg://sparkle_engine:pw@sparkle_db:5432/sparkle",
        SPARKLE_CELERY_DATABASE_URL="postgresql+asyncpg://sparkle_celery:pw@sparkle_db:5432/sparkle",
    )

    assert "sparkle_celery" in settings.DATABASE_URL


def test_legacy_database_url_remains_when_rbac_disabled() -> None:
    settings = Settings(
        _env_file=None,
        SECRET_KEY=SECRET_KEY,
        SPARKLE_RBAC_ENABLED=False,
        SERVICE_ROLE="api",
        DATABASE_URL="postgresql+asyncpg://postgres:legacy@sparkle_db:5432/sparkle",
        SPARKLE_ENGINE_DATABASE_URL="postgresql+asyncpg://sparkle_engine:pw@sparkle_db:5432/sparkle",
    )

    assert "postgres:legacy" in settings.DATABASE_URL


def test_rbac_migration_declares_all_service_roles() -> None:
    migration = _load_migration()

    assert set(migration.SERVICE_ROLES) == {
        "sparkle_gateway",
        "sparkle_engine",
        "sparkle_celery",
        "sparkle_readonly",
    }


def test_gateway_role_contract_is_narrower_than_engine_contract() -> None:
    migration = _load_migration()

    assert "chat_messages" in migration.GATEWAY_RW_TABLES
    assert "event_outbox" in migration.GATEWAY_RW_TABLES
    assert "users" in migration.GATEWAY_RO_TABLES
    assert "memory_" in migration.ENGINE_PREFIXES
    assert "knowledge_" in migration.ENGINE_PREFIXES
    assert "event_outbox" in migration.CELERY_EXTRA_RW_TABLES
    assert "memory_" not in migration.GATEWAY_RW_TABLES
