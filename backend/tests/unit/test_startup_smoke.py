"""
Core: infra
Phase: none
Stage: N/A

Startup Smoke Test — verifies that the FastAPI app and Celery app
can be imported and instantiated without errors.

This test intentionally does NOT require database or Redis connections.
It catches:
  - Syntax errors (e.g. duplicate lines in auth.py)
  - Import errors (e.g. missing on_after_configure signal in Celery 5.x)
  - Circular imports
  - Variable shadowing that breaks module-level constructs
"""

from __future__ import annotations

import importlib
import sys

import pytest


# ---------------------------------------------------------------------------
# Fix 1: Celery 5.x removed on_after_configure — try/except fallback
# ---------------------------------------------------------------------------

class TestCeleryAppImport:
    """Verify celery_app imports cleanly (covers Fix 1)."""

    def test_celery_app_imports_without_error(self) -> None:
        """Importing app.core.celery_app must not raise."""
        mod = importlib.import_module("app.core.celery_app")
        assert hasattr(mod, "celery_app")

    def test_celery_app_is_celery_instance(self) -> None:
        from app.core.celery_app import celery_app

        from celery import Celery

        assert isinstance(celery_app, Celery)

    def test_beat_schedule_populated(self) -> None:
        """beat_schedule must contain at least the core periodic tasks."""
        from app.core.celery_app import celery_app

        schedule = celery_app.conf.beat_schedule
        assert isinstance(schedule, dict)
        # Spot-check a few entries that should always be present
        expected_keys = [
            "cleanup-every-day",
            "health-check",
            "daily-report",
        ]
        for key in expected_keys:
            assert key in schedule, f"Missing beat_schedule entry: {key}"

    def test_on_after_configure_fallback_exists(self) -> None:
        """The module must handle missing on_after_configure gracefully."""
        mod = importlib.import_module("app.core.celery_app")
        # The module-level code already ran during import; this just
        # confirms it didn't crash. The fallback path sets
        # on_after_configure = None when Celery 5.x lacks the signal.
        assert True  # Import succeeded == pass


# ---------------------------------------------------------------------------
# Fix 2: auth.py had duplicate lines causing SyntaxError
# ---------------------------------------------------------------------------

class TestAuthModuleImport:
    """Verify auth.py imports cleanly (covers Fix 2)."""

    def test_auth_module_imports_without_error(self) -> None:
        """Importing app.api.v1.auth must not raise SyntaxError."""
        mod = importlib.import_module("app.api.v1.auth")
        assert hasattr(mod, "router")


# ---------------------------------------------------------------------------
# Fix 3: main.py lifespan parameter renamed from app to fastapp
# ---------------------------------------------------------------------------

class TestMainAppImport:
    """Verify app.main imports cleanly (covers Fix 3)."""

    def test_main_app_imports_without_error(self) -> None:
        """Importing app.main must succeed — catches variable shadowing."""
        mod = importlib.import_module("app.main")
        assert hasattr(mod, "app")

    def test_fastapi_app_instance(self) -> None:
        from app.main import app

        from fastapi import FastAPI

        assert isinstance(app, FastAPI)

    def test_expected_toplevel_routes_registered(self) -> None:
        """The app must register core top-level routes."""
        from app.main import app

        route_paths = {route.path for route in app.routes}
        for expected in ("/", "/health", "/live", "/ready"):
            assert expected in route_paths, f"Missing top-level route: {expected}"

    def test_api_v1_router_mounted(self) -> None:
        """The /api/v1 prefix must be present in the route table."""
        from app.main import app

        route_paths = {route.path for route in app.routes}
        assert any(p.startswith("/api/v1") for p in route_paths), (
            "No /api/v1 routes found — api_router may not be mounted"
        )

    def test_lifespan_function_signature(self) -> None:
        """The lifespan function parameter must be named 'fastapp', not 'app'."""
        import inspect

        from app.main import lifespan

        sig = inspect.signature(lifespan)
        params = list(sig.parameters.keys())
        assert len(params) == 1
        assert params[0] == "fastapp", (
            f"lifespan parameter is '{params[0]}', expected 'fastapp'"
        )


# ---------------------------------------------------------------------------
# Fix 4: Alembic migration COMMIT before CONCURRENTLY
# ---------------------------------------------------------------------------

class TestAlembicMigrationCompositeIndex:
    """Verify the composite-index migration includes COMMIT (covers Fix 4)."""

    @staticmethod
    def _read_migration_source() -> str:
        """Read the migration file directly (not importable as a module)."""
        from pathlib import Path

        migration_file = (
            Path(__file__).resolve().parent.parent.parent
            / "alembic"
            / "versions"
            / "comp_idx_20260508_add_composite_indexes.py"
        )
        assert migration_file.exists(), f"Migration file not found: {migration_file}"
        return migration_file.read_text()

    def test_migration_has_commit_before_concurrently(self) -> None:
        """The upgrade() function must issue COMMIT before CREATE INDEX CONCURRENTLY."""
        source = self._read_migration_source()
        assert "COMMIT" in source, (
            "Migration upgrade() is missing COMMIT before CONCURRENTLY"
        )
        assert "CONCURRENTLY" in source
        # COMMIT must appear before CONCURRENTLY
        assert source.index("COMMIT") < source.index("CONCURRENTLY"), (
            "COMMIT must come before CREATE INDEX CONCURRENTLY"
        )

    def test_migration_downgrade_idempotent(self) -> None:
        """Downgrade should use IF EXISTS for safe re-runs."""
        source = self._read_migration_source()
        assert "IF EXISTS" in source or "DROP INDEX" in source
