"""ud01_20260919 迁移在本地 sqlite 基座上的隔离重放（主库只读纪律）。

不连主仓 PostgreSQL：用 alembic Operations/MigrationContext 把
ud01_20260919_understanding_depth_daily.upgrade/downgrade 单独跑在临时
sqlite 文件库上，验证表结构、(user_id, metric_date) 唯一约束与可回滚性。
"""

from __future__ import annotations

import importlib.util
from datetime import date
from pathlib import Path
from typing import Callable
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session

from app.models.understanding_depth import UnderstandingDepthDaily

BACKEND_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = BACKEND_ROOT / "alembic" / "versions" / "ud01_20260919_understanding_depth_daily.py"

EXPECTED_COLUMNS = {
    "id",
    "created_at",
    "updated_at",
    "deleted_at",
    "user_id",
    "metric_date",
    "score",
    "components",
    "context_pack_runs",
    "chat_turns",
}


@pytest.fixture(name="migration_env")
def _migration_env(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'ud_test.db'}")

    def run_migration(op_fn: Callable[[], None]) -> None:
        """把迁移模块的 upgrade/downgrade 绑到 sqlite 连接上隔离执行。"""
        with engine.connect() as conn:
            ctx = MigrationContext.configure(conn)
            with Operations.context(ctx):
                op_fn()
            conn.commit()

    yield run_migration, engine
    engine.dispose()


def _load_migration_module():
    spec = importlib.util.spec_from_file_location("ud01_20260919", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ud01_upgrade_creates_expected_schema_and_downgrade_drops_it(migration_env):
    run_migration, engine = migration_env
    module = _load_migration_module()

    # 迁移头契约：单父挂当前唯一 head（防止并行挂链复活双头）
    assert module.down_revision == "gfix03_20260918"

    run_migration(module.upgrade)

    inspector = inspect(engine)
    assert inspector.has_table("understanding_depth_daily")
    columns = {col["name"] for col in inspector.get_columns("understanding_depth_daily")}
    assert columns >= EXPECTED_COLUMNS
    uniques = {u["name"] for u in inspector.get_unique_constraints("understanding_depth_daily")}
    assert "uq_understanding_depth_daily_user_date" in uniques
    index_names = {ix["name"] for ix in inspector.get_indexes("understanding_depth_daily")}
    assert "idx_understanding_depth_daily_date" in index_names

    run_migration(module.downgrade)
    assert not inspect(engine).has_table("understanding_depth_daily")


def test_ud01_schema_enforces_one_row_per_user_per_day(migration_env):
    """迁移产物可直接承接 ORM 写入，且 (user_id, metric_date) 唯一约束生效。"""
    run_migration, engine = migration_env
    module = _load_migration_module()
    run_migration(module.upgrade)

    user_id = uuid4()
    day = date(2026, 9, 19)
    session = Session(bind=engine)
    session.add(
        UnderstandingDepthDaily(
            user_id=user_id,
            metric_date=day,
            score=0.42,
            components={"memory_injection": 0.5},
            context_pack_runs=2,
            chat_turns=4,
        )
    )
    session.commit()

    rows = session.execute(select(UnderstandingDepthDaily)).scalars().all()
    assert len(rows) == 1 and rows[0].score == 0.42

    session.add(
        UnderstandingDepthDaily(
            user_id=user_id,
            metric_date=day,
            score=0.9,
            components={},
            context_pack_runs=1,
            chat_turns=1,
        )
    )
    with pytest.raises(Exception):  # 唯一约束拒绝同用户同日第二行
        session.commit()
    session.rollback()
    session.close()
