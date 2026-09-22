"""photidem_20260923 迁移在本地 sqlite 基座上的隔离重放（主库只读纪律）.

不连主库 PostgreSQL：用 alembic Operations/MigrationContext 把
photidem_20260923_photon_daily_first_idem_unique 的 upgrade/downgrade 单独跑在
临时 sqlite 文件库上，验证 photon_transaction_history 每日首胜幂等键唯一部分
索引的 schema 变更：

- upgrade 收敛索引管辖域（related_item_id LIKE 'daily_first:%'）内的存量重复
  (user_id, related_item_id) 组，保留最早一行（created_at 最小 = 首个真实发放
  事件；后来者是并发 check-then-insert 竞态双发的虚增「可兑换基数」污染）；
- 管辖域外的存量行（NULL、裸 achievement_id / contract_id、guest_welcome
  跨用户同键、achievement_combo:<hex16>、purchase 裸 item_id 合法重复）一概
  不动——部分索引谓词外零影响；
- upgrade 后唯一部分索引存在且生效：同键二次 INSERT 违约、
  ON CONFLICT DO NOTHING RETURNING 丢行（写侧生产契约）；
- downgrade 后索引移除、存量行存活，round-trip 幂等可重入。

迁移语义（为什么是部分索引而不是全列唯一、为什么 combo 域不并入）见迁移文件
docstring 与 v3-output/PHOTON-IDEM/REPORT.md。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text

BACKEND_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = BACKEND_ROOT / "alembic" / "versions" / "photidem_20260923_photon_daily_first_idem_unique.py"

INDEX_NAME = "uq_photon_tx_daily_first_idem"

# 迁移前 schema：photon_transaction_history 裸表（无幂等唯一索引）。
# 主表 PK 是 uuid（VARCHAR(36) 镜像）——PG 无 min(uuid) 聚合，迁移因此采用
# (created_at, CAST(id AS TEXT)) 字典序收敛写法，本 DDL 与该语义对齐。
BASE_DDL = """
CREATE TABLE photon_transaction_history (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    transaction_type VARCHAR(50) NOT NULL,
    amount INTEGER NOT NULL,
    balance_before INTEGER NOT NULL,
    balance_after INTEGER NOT NULL,
    source VARCHAR(255),
    related_item_id VARCHAR(50),
    extra_data JSON,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP
)
"""

U1 = "11111111-1111-1111-1111-111111111111"
U2 = "22222222-2222-2222-2222-222222222222"
U3 = "33333333-3333-3333-3333-333333333333"


def _insert_tx(
    conn,
    *,
    tx_id: str,
    user: str,
    related: str | None,
    tx_type: str = "grant_daily_first",
    amount: int = 30,
    before: int = 0,
    after: int = 30,
    created: str = "2026-09-22 10:00:00",
) -> None:
    conn.exec_driver_sql(
        "INSERT INTO photon_transaction_history "
        "(id, user_id, transaction_type, amount, balance_before, balance_after, "
        "source, related_item_id, extra_data, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, 'daily_first', ?, NULL, ?, ?)",
        (tx_id, user, tx_type, amount, before, after, related, created, created),
    )


@pytest.fixture(name="migration_env")
def _migration_env(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'photon_idem_migration.db'}")

    # 迁移前基座：裸表 + 存量行（含索引管辖域内的重复组与域外各形态）
    with engine.begin() as conn:
        conn.exec_driver_sql(BASE_DDL)
        # 管辖域内：同用户同日重复组（10:00 首个真实发放生效在前；
        # 11:00 并发双发污染在后——并发竞态下胜者 0→30、败者又 +30）
        _insert_tx(conn, tx_id="a" * 36, user=U1, related="daily_first:2026-09-22",
                   before=0, after=30, created="2026-09-22 10:00:00")
        _insert_tx(conn, tx_id="b" * 36, user=U1, related="daily_first:2026-09-22",
                   before=30, after=60, created="2026-09-22 11:00:00")
        # 管辖域内：唯一行（跨用户同日、同用户次日——都必须存活）
        _insert_tx(conn, tx_id="c" * 36, user=U2, related="daily_first:2026-09-22",
                   created="2026-09-22 12:00:00")
        _insert_tx(conn, tx_id="d" * 36, user=U1, related="daily_first:2026-09-23",
                   created="2026-09-23 09:00:00")
        # 管辖域外：NULL（transfer/redeem_pro 形态，含同 NULL 重复组）
        _insert_tx(conn, tx_id="e" * 36, user=U1, related=None, tx_type="transfer_in",
                   amount=100, before=0, after=100, created="2026-09-20 10:00:00")
        _insert_tx(conn, tx_id="f" * 36, user=U1, related=None, tx_type="transfer_in",
                   amount=100, before=100, after=200, created="2026-09-21 10:00:00")
        # 管辖域外：裸 achievement_id 重复对（重试补发形态）
        _insert_tx(conn, tx_id="0" * 36, user=U1, related="ach_x", tx_type="grant_achievement",
                   amount=10, before=0, after=10, created="2026-09-20 10:00:00")
        _insert_tx(conn, tx_id="1" * 36, user=U1, related="ach_x", tx_type="grant_achievement",
                   amount=10, before=10, after=20, created="2026-09-20 11:00:00")
        # 管辖域外：guest_welcome 跨用户同键（per-user 域内各自唯一）
        _insert_tx(conn, tx_id="2" * 36, user=U2, related="guest_welcome",
                   tx_type="grant_achievement", amount=1000, before=0, after=1000)
        _insert_tx(conn, tx_id="3" * 36, user=U3, related="guest_welcome",
                   tx_type="grant_achievement", amount=1000, before=0, after=1000)
        # 管辖域外：combo 键（uuid4 生成器唯一，裁决不并入索引）
        _insert_tx(conn, tx_id="4" * 36, user=U1, related="achievement_combo:aaaabbbbccccdddd",
                   tx_type="grant_bonus", amount=30, before=0, after=30)
        # 管辖域外：purchase 裸 item_id 合法重复购买
        _insert_tx(conn, tx_id="5" * 36, user=U1, related="consumable_exp_boost_1x_001",
                   tx_type="purchase", amount=-300, before=300, after=0)
        _insert_tx(conn, tx_id="6" * 36, user=U1, related="consumable_exp_boost_1x_001",
                   tx_type="purchase", amount=-300, before=300, after=0)

    def run_migration(op_fn) -> None:
        # begin()：SQLAlchemy 2.x 无 commit 不落盘（DDL 亦在事务内），迁移必须在事务内执行
        with engine.begin() as conn:
            ctx = MigrationContext.configure(conn)
            with Operations.context(ctx):
                op_fn()

    def load_upgrade_downgrade():
        spec = importlib.util.spec_from_file_location("photidem_migration", MIGRATION_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.upgrade, module.downgrade

    yield engine, run_migration, load_upgrade_downgrade
    engine.dispose()


def _index_names(engine) -> set[str]:
    insp = inspect(engine)
    return {idx["name"] for idx in insp.get_indexes("photon_transaction_history")}


def _scoped_rows(engine) -> list[tuple]:
    with engine.connect() as conn:
        return [
            tuple(r)
            for r in conn.execute(
                text(
                    "SELECT user_id, related_item_id, balance_before, balance_after "
                    "FROM photon_transaction_history "
                    "WHERE related_item_id LIKE 'daily_first:%' "
                    "ORDER BY created_at, CAST(id AS TEXT)"
                )
            ).fetchall()
        ]


def test_upgrade_dedupes_daily_first_domain_keeping_earliest(migration_env):
    engine, run_migration, load_upgrade_downgrade = migration_env
    upgrade, _ = load_upgrade_downgrade()

    # 迁移前：管辖域内 4 行（U1 同日重复组 + U2 同日唯一 + U1 次日唯一）
    assert len(_scoped_rows(engine)) == 4

    run_migration(upgrade)

    # 重复收敛：U1 同日组保留最早一行（10:00 首个真实发放 0→30）；
    # 11:00 的双发污染（30→60）被删除——「可兑换基数」还原诚实值
    rows = _scoped_rows(engine)
    assert rows == [
        (U1, "daily_first:2026-09-22", 0, 30),
        (U2, "daily_first:2026-09-22", 0, 30),
        (U1, "daily_first:2026-09-23", 0, 30),
    ], "保留最早、删除后来者；跨用户同日与同用户次日必须原样存活"
    assert INDEX_NAME in _index_names(engine)


def test_upgrade_leaves_out_of_scope_rows_untouched(migration_env):
    engine, run_migration, load_upgrade_downgrade = migration_env
    upgrade, _ = load_upgrade_downgrade()

    run_migration(upgrade)

    with engine.connect() as conn:
        null_rows = conn.execute(
            text("SELECT COUNT(*) FROM photon_transaction_history WHERE related_item_id IS NULL")
        ).scalar()
        bare_dup = conn.execute(
            text(
                "SELECT COUNT(*) FROM photon_transaction_history "
                "WHERE related_item_id IN ('ach_x', 'consumable_exp_boost_1x_001')"
            )
        ).scalar()
        guest_welcome = conn.execute(
            text(
                "SELECT COUNT(DISTINCT user_id) FROM photon_transaction_history "
                "WHERE related_item_id = 'guest_welcome'"
            )
        ).scalar()
        combo = conn.execute(
            text(
                "SELECT COUNT(*) FROM photon_transaction_history "
                "WHERE related_item_id LIKE 'achievement_combo:%'"
            )
        ).scalar()
    # 管辖域外零影响：NULL 重复组、域外既有重复对、跨用户同键、combo 全部原样
    assert null_rows == 2
    assert bare_dup == 4, "域外重复对（重试补发/合法重复购买）不属于本索引管辖"
    assert guest_welcome == 2
    assert combo == 1


def test_upgrade_enforces_uniqueness_and_on_conflict_contract(migration_env):
    engine, run_migration, load_upgrade_downgrade = migration_env
    upgrade, _ = load_upgrade_downgrade()

    run_migration(upgrade)

    with engine.begin() as conn:
        # 同键裸 INSERT 违约（同用户同日键）
        with pytest.raises(Exception):
            _insert_tx(conn, tx_id="7" * 36, user=U1, related="daily_first:2026-09-22",
                       created="2026-09-22 15:00:00")
    # 跨用户同日键不违约（per-user 语义）
    with engine.begin() as conn:
        _insert_tx(conn, tx_id="8" * 36, user=U3, related="daily_first:2026-09-22",
                   created="2026-09-22 15:00:00")
    # 写侧生产契约：ON CONFLICT DO NOTHING RETURNING 丢行（PhotonService 同款）
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "INSERT INTO photon_transaction_history "
                "(id, user_id, transaction_type, amount, balance_before, balance_after, "
                "source, related_item_id, extra_data, created_at, updated_at) "
                "VALUES (:id, :u, 'grant_daily_first', 30, 0, 30, 'daily_first', :q, NULL, "
                "'2026-09-22 16:00:00', '2026-09-22 16:00:00') "
                "ON CONFLICT DO NOTHING RETURNING id"
            ),
            {"id": "9" * 36, "u": U1, "q": "daily_first:2026-09-22"},
        )
        assert result.scalar_one_or_none() is None, "冲突时 RETURNING 必须无行（写侧据此判定 duplicate）"
    # 非冲突键 RETURNING 返回新行 id
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "INSERT INTO photon_transaction_history "
                "(id, user_id, transaction_type, amount, balance_before, balance_after, "
                "source, related_item_id, extra_data, created_at, updated_at) "
                "VALUES (:id, :u, 'grant_daily_first', 30, 0, 30, 'daily_first', :q, NULL, "
                "'2026-09-24 09:00:00', '2026-09-24 09:00:00') "
                "ON CONFLICT DO NOTHING RETURNING id"
            ),
            {"id": "a" * 35 + "b", "u": U1, "q": "daily_first:2026-09-24"},
        )
        assert result.scalar_one_or_none() == "a" * 35 + "b"
    # 域外重复写不受索引约束
    with engine.begin() as conn:
        _insert_tx(conn, tx_id="g" * 36, user=U2, related="ach_x", tx_type="grant_achievement",
                   amount=10, before=0, after=10, created="2026-09-23 10:00:00")
        _insert_tx(conn, tx_id="h" * 36, user=U2, related="ach_x", tx_type="grant_achievement",
                   amount=10, before=10, after=20, created="2026-09-23 11:00:00")  # 不违约


def test_round_trip_downgrade_and_reentrant(migration_env):
    engine, run_migration, load_upgrade_downgrade = migration_env
    upgrade, downgrade = load_upgrade_downgrade()

    run_migration(upgrade)
    assert INDEX_NAME in _index_names(engine)
    scoped_after_upgrade = _scoped_rows(engine)

    run_migration(downgrade)
    assert INDEX_NAME not in _index_names(engine)
    # downgrade 不回填被收敛的污染行；存量数据行原样存活
    assert _scoped_rows(engine) == scoped_after_upgrade

    # 可重入：再次 upgrade 幂等（无重复可删 + IF NOT EXISTS）
    run_migration(upgrade)
    assert INDEX_NAME in _index_names(engine)
    assert _scoped_rows(engine) == scoped_after_upgrade
