"""d03_20260920 迁移在本地 sqlite 基座上的隔离重放（主库只读纪律）。

不连主仓 PostgreSQL：用 alembic Operations/MigrationContext 把
d03_20260920_understanding_dimensions.upgrade/downgrade 单独跑在临时
sqlite 文件库上，验证两表结构、唯一约束与可回滚性。
"""

from __future__ import annotations

import importlib.util
from datetime import date, datetime
from pathlib import Path
from typing import Callable
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

BACKEND_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = BACKEND_ROOT / "alembic" / "versions" / "d03_20260920_understanding_dimensions.py"

DIMENSION_COLUMNS = {
    "id",
    "created_at",
    "updated_at",
    "deleted_at",
    "user_id",
    "metric_date",
    "dimensions",
    "anchors",
    "window_days",
    "schema_version",
}
CALIBRATION_COLUMNS = {
    "id",
    "created_at",
    "updated_at",
    "deleted_at",
    "user_id",
    "ran_at",
    "window_days",
    "coverage_map",
    "drift_report",
    "overall_status",
    "schema_version",
}


@pytest.fixture(name="migration_env")
def _migration_env(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'd03_test.db'}")

    def run_migration(op_fn: Callable[[], None]) -> None:
        with engine.connect() as conn:
            ctx = MigrationContext.configure(conn)
            with Operations.context(ctx):
                op_fn()
            conn.commit()

    yield run_migration, engine
    engine.dispose()


def _load_migration_module():
    spec = importlib.util.spec_from_file_location("d03_20260920", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_d03_upgrade_creates_expected_schema_and_downgrade_drops_it(migration_env):
    run_migration, engine = migration_env
    module = _load_migration_module()

    run_migration(module.upgrade)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert {"understanding_dimension_daily", "understanding_calibration_runs"} <= tables
    assert {c["name"] for c in inspector.get_columns("understanding_dimension_daily")} == DIMENSION_COLUMNS
    assert {c["name"] for c in inspector.get_columns("understanding_calibration_runs")} == CALIBRATION_COLUMNS

    run_migration(module.downgrade)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert "understanding_dimension_daily" not in tables
    assert "understanding_calibration_runs" not in tables


def test_d03_schema_enforces_one_row_per_user_per_day(migration_env):
    run_migration, engine = migration_env
    module = _load_migration_module()
    run_migration(module.upgrade)

    user_id = str(uuid4())
    now = datetime(2026, 9, 20)
    with Session(engine) as session:
        session.execute(
            __import__("sqlalchemy").text(
                "INSERT INTO understanding_dimension_daily "
                "(id, created_at, updated_at, user_id, metric_date, dimensions, anchors, window_days, schema_version) "
                "VALUES (:id, :ts, :ts, :uid, :d, '{}', '{}', 7, 'understanding.dimensions.v1')"
            ),
            {"id": str(uuid4()), "ts": now, "uid": user_id, "d": date(2026, 9, 19)},
        )
        session.commit()
        with pytest.raises(Exception):  # noqa: B017 — sqlite 抛 IntegrityError
            session.execute(
                __import__("sqlalchemy").text(
                    "INSERT INTO understanding_dimension_daily "
                    "(id, created_at, updated_at, user_id, metric_date, dimensions, anchors, window_days, schema_version) "
                    "VALUES (:id, :ts, :ts, :uid, :d, '{}', '{}', 7, 'understanding.dimensions.v1')"
                ),
                {"id": str(uuid4()), "ts": now, "uid": user_id, "d": date(2026, 9, 19)},
            )
            session.commit()


def test_d03_orm_model_matches_migration_columns(migration_env):
    """ORM 声明与迁移列集一致（防漂移：改模型不改迁移 → 红）。"""
    from app.models.understanding_dimensions import UnderstandingCalibrationRun, UnderstandingDimensionDaily

    run_migration, engine = migration_env
    module = _load_migration_module()
    run_migration(module.upgrade)

    inspector = inspect(engine)
    orm_daily = {c.name for c in UnderstandingDimensionDaily.__table__.columns}
    orm_calib = {c.name for c in UnderstandingCalibrationRun.__table__.columns}
    assert orm_daily == {c["name"] for c in inspector.get_columns("understanding_dimension_daily")}
    assert orm_calib == {c["name"] for c in inspector.get_columns("understanding_calibration_runs")}


def test_d03_down_revision_parents_on_chain_tail():
    module = _load_migration_module()
    # 合入时按主仓实际链尾重挂（worktree 基线时为 x06，合入时链已到 x03b）
    assert module.down_revision == "x03b_20260920"
    assert module.revision == "d03_20260920"
