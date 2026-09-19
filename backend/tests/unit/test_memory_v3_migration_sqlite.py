"""m01a_20260919 迁移在本地 sqlite 基座上的隔离重放（主库只读纪律）。

不连主仓 PostgreSQL：用 alembic Operations/MigrationContext 把
m01a_20260919_memory_v3_epistemic.upgrade/downgrade 单独跑在临时
sqlite 文件库上，验证：
1. 三组加法列（epistemic_class / superseded_by_id / memory_epoch 三件套）；
2. R2-F1 收紧后的回填矩阵：FACT 仅限用户陈述（user_confirmed 确认动作 /
   direct_capture+user_registered），direct_capture 机器写行
   （chat_turn/analysis 等，dev 库 183/184 主体）→ OBSERVATION，
   推断与未登记 lane → HYPOTHESIS（保守档）；
3. 可回滚性（downgrade 后列消失）。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Callable
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text

from app.models.base import Base
import app.models.memory  # noqa: F401 - register metadata
import app.models.user_memory_settings  # noqa: F401 - register metadata
import app.models.user  # noqa: F401 - register metadata (FK target)

BACKEND_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = BACKEND_ROOT / "alembic" / "versions" / "m01a_20260919_memory_v3_epistemic.py"


@pytest.fixture(name="migration_env")
def _migration_env(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'm01_test.db'}")
    # 先按 ORM 建表，再摘掉 M-01 新列，还原"迁移前基线"：
    # ORM 已领先包含 epistemic_class/superseded_by_id/epoch 三件套，
    # 基线必须与迁移前实库一致（旧 schema 无这些列）。
    Base.metadata.create_all(
        engine,
        tables=[
            Base.metadata.tables["users"],
            Base.metadata.tables["episodic_memories"],
            Base.metadata.tables["user_memory_settings"],
        ],
    )
    with engine.begin() as conn:
        conn.execute(text("DROP INDEX IF EXISTS idx_episodic_memories_epistemic_class"))
        conn.execute(text("DROP INDEX IF EXISTS idx_episodic_memories_superseded_by_id"))
        conn.execute(text("ALTER TABLE episodic_memories DROP COLUMN epistemic_class"))
        conn.execute(text("ALTER TABLE episodic_memories DROP COLUMN superseded_by_id"))
        conn.execute(text("ALTER TABLE user_memory_settings DROP COLUMN memory_epoch"))
        conn.execute(text("ALTER TABLE user_memory_settings DROP COLUMN memory_epoch_bumped_at"))
        conn.execute(text("ALTER TABLE user_memory_settings DROP COLUMN memory_epoch_reason"))

    def run_migration(op_fn: Callable[[], None]) -> None:
        with engine.connect() as conn:
            ctx = MigrationContext.configure(conn)
            with Operations.context(ctx):
                op_fn()
            conn.commit()

    yield run_migration, engine
    engine.dispose()


def _load_migration_module():
    spec = importlib.util.spec_from_file_location("m01a_20260919", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _seed_episodic(engine, lane: str, source_type: str = "chat") -> str:
    memory_id = str(uuid4())
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO episodic_memories (id, created_at, updated_at, user_id, summary, "
                "source_type, source_lane, subject_type, occurred_at, evidence_refs, evidence_score, "
                "correction_count, evidence_missing) "
                "VALUES (:id, :now, :now, :uid, :summary, :stype, :lane, 'self', :now, '[]', 0.0, 0, 0)"
            ),
            {
                "id": memory_id,
                "now": "2026-09-19 10:00:00",
                "uid": str(uuid4()),
                "summary": f"lane={lane} stype={source_type}",
                "lane": lane,
                "stype": source_type,
            },
        )
    return memory_id


def test_m01a_upgrade_adds_columns_backfills_and_downgrade_reverses(migration_env):
    run_migration, engine = migration_env
    module = _load_migration_module()

    # 迁移头契约：单父挂当前唯一 head（防止并行挂链复活双头）
    # 合入窗口重挂说明：Worker 构建时 head=ud01，合入时 E-05 已先行 apply e05，
    # 故 m01a 重挂 e05（Leader @merge-window，见 REPORT §8）
    assert module.down_revision == "e05_20260919"

    # R2-F1 期望矩阵：按 dev 库 live source_type 构成播种。
    user_statement_id = _seed_episodic(engine, "direct_capture", "user_registered")  # 唯一用户陈述
    machine_chat_id = _seed_episodic(engine, "direct_capture", "chat_turn")  # 机器写主体
    machine_analysis_id = _seed_episodic(engine, "direct_capture", "analysis")
    confirmed_id = _seed_episodic(engine, "user_confirmed", "chat_turn")  # 确认动作即用户陈述
    inferred_id = _seed_episodic(engine, "inferred_extraction", "chat")
    unknown_id = _seed_episodic(engine, "aurora_calibration_receipt", "chat")

    run_migration(module.upgrade)

    inspector = inspect(engine)
    episodic_cols = {col["name"] for col in inspector.get_columns("episodic_memories")}
    settings_cols = {col["name"] for col in inspector.get_columns("user_memory_settings")}
    assert "epistemic_class" in episodic_cols
    assert "superseded_by_id" in episodic_cols
    assert {"memory_epoch", "memory_epoch_bumped_at", "memory_epoch_reason"} <= settings_cols

    episodic_indexes = {idx["name"] for idx in inspector.get_indexes("episodic_memories")}
    assert "idx_episodic_memories_epistemic_class" in episodic_indexes
    assert "idx_episodic_memories_superseded_by_id" in episodic_indexes

    def _class_of(memory_id: str) -> str:
        with engine.connect() as conn:
            return conn.execute(
                text("SELECT epistemic_class FROM episodic_memories WHERE id = :id"), {"id": memory_id}
            ).scalar_one()

    # FACT 仅限用户陈述（user_confirmed 确认动作 / direct_capture+user_registered）
    assert _class_of(user_statement_id) == "FACT"
    assert _class_of(confirmed_id) == "FACT"
    # direct_capture 机器写行（dev 库 183/184 主体）→ OBSERVATION
    assert _class_of(machine_chat_id) == "OBSERVATION"
    assert _class_of(machine_analysis_id) == "OBSERVATION"
    # 推断 lane → HYPOTHESIS
    assert _class_of(inferred_id) == "HYPOTHESIS"
    # 未登记 lane 保守落 HYPOTHESIS（不替产品做登记裁决）
    assert _class_of(unknown_id) == "HYPOTHESIS"

    with engine.connect() as conn:
        epoch_default = conn.execute(
            text("SELECT memory_epoch FROM user_memory_settings LIMIT 1")
        ).scalar()
    # 无设置行时不返回记录；有行时 server_default=1
    assert epoch_default is None or epoch_default == 1

    # 回填语句幂等（alembic 本身保证 upgrade 只跑一次；此处验证的是
    # 手工重放回填 UPDATE 不会改写已填行）。
    backfill_sql = (
        "UPDATE episodic_memories SET epistemic_class = CASE "
        "WHEN source_lane = 'user_confirmed' THEN 'FACT' "
        "WHEN source_lane = 'direct_capture' AND source_type IN ('user_registered') THEN 'FACT' "
        "WHEN source_lane IN ('direct_capture', 'user_confirmed') THEN 'OBSERVATION' "
        "ELSE 'HYPOTHESIS' END WHERE epistemic_class IS NULL"
    )
    with engine.begin() as conn:
        conn.execute(text(backfill_sql))
        conn.execute(text(backfill_sql))
    assert _class_of(user_statement_id) == "FACT"
    assert _class_of(machine_chat_id) == "OBSERVATION"

    run_migration(module.downgrade)
    inspector = inspect(engine)
    episodic_cols = {col["name"] for col in inspector.get_columns("episodic_memories")}
    settings_cols = {col["name"] for col in inspector.get_columns("user_memory_settings")}
    assert "epistemic_class" not in episodic_cols
    assert "superseded_by_id" not in episodic_cols
    assert "memory_epoch" not in settings_cols
