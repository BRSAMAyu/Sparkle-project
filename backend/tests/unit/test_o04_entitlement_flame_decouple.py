"""O-04 · Paid Entitlement 与 Flame/Gameification 解耦（灵魂红线回归）。

红线：**改变 flame 不得改变付费能力**（flame 是游戏化，entitlement 是商业
——`is_pro = flame_level >= 3` 的历史派生正是本卡要杀的缺陷）。

覆盖四层：
1. 判级单一实现（core/entitlement）：flame 扫荡不变量 + 未知值宁降不升
2. 引擎上下文面：user_service.get_context 的 is_pro 派生（真源 entitlement）
3. 请求链路：llm_router ceiling 钳制随 entitlement 即时生效；C-06 预算矩阵
   R-RISK-1 最小接线（请求级 tier ContextVar）；metrics 有界 plan 维度
4. 存量迁移安全默认：ent01_20260919 在 sqlite 隔离基座重放（主库只读纪律）
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from prometheus_client import REGISTRY
from sqlalchemy import create_engine, inspect, text

from app.core.agent_profiles import AgentRole, ModelTier
from app.core.entitlement import (
    ENTITLEMENT_FREE,
    ENTITLEMENT_PRO,
    entitlement_grants_pro,
    normalize_entitlement,
    request_tier_label,
)
from app.core.llm_router import (
    LLMRouter,
    reset_request_user_tier,
    set_request_user_tier,
)
from app.models.user import User
from app.services.personalization.preference_service import PreferenceService
from app.services.user_service import UserService

BACKEND_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = BACKEND_ROOT / "alembic" / "versions" / "ent01_20260919_add_user_entitlement.py"

METRIC_FREE_DOWNGRADE = "sparkle_llm_router_free_tier_downgrade_total"
METRIC_SELECTION = "sparkle_llm_router_selection_total"


@pytest.fixture(autouse=True)
def _clean_user_tier():
    token = set_request_user_tier(None)
    yield
    reset_request_user_tier(token)


@pytest.fixture(autouse=True)
def _deterministic_env(monkeypatch):
    """清空 .env 泄漏的 key/tier 覆盖，使路由池确定（test_llm_router_free_tier 同款）。"""
    from app.config import settings as _s

    for key in [k for k in vars(_s) if k.endswith("_API_KEY") or k.startswith("LLM_TIER_")]:
        monkeypatch.setattr(_s, key, "")


# ---------------------------------------------------------------------------
# 1. 判级单一实现：flame 永不入判级；未知值宁降不升
# ---------------------------------------------------------------------------


def test_flame_sweep_never_changes_entitlement_verdict():
    """灵魂测试：flame 1→10 全程，entitlement 决定一切、flame 无从介入。"""
    for flame in range(1, 11):
        assert entitlement_grants_pro(ENTITLEMENT_FREE) is False, f"flame={flame}"
        assert entitlement_grants_pro(ENTITLEMENT_PRO) is True, f"flame={flame}"


def test_unknown_or_missing_entitlement_degrades_to_free():
    """迁移漏用户 / 脏值一律 free（宁降不升，成本 fail-safe）。"""
    for raw in (None, "", "   ", "premium", "paid", "enterprise", "未知"):
        assert entitlement_grants_pro(raw) is False, f"raw={raw!r}"
        assert normalize_entitlement(raw) == ENTITLEMENT_FREE, f"raw={raw!r}"
    # 值域内的容错归一：trim + 大小写
    assert normalize_entitlement(" PRO ") == ENTITLEMENT_PRO
    assert normalize_entitlement("Pro") == ENTITLEMENT_PRO


def test_user_model_entitlement_column_defaults_free():
    """真源列的安全默认：ORM default 与 DB server_default 双双 'free'（存量行自动回填）。"""
    column = User.__table__.columns["entitlement"]
    assert column.default.arg == "free"
    assert column.server_default.arg == "free"
    assert column.nullable is False


def test_request_tier_label_is_bounded_vocabulary():
    """metrics plan 维度词表封闭：free | pro | unknown（未标记=内部调用面）。"""
    assert request_tier_label(None) == "unknown"
    assert request_tier_label("") == "unknown"
    assert request_tier_label("flame15") == "unknown"
    assert request_tier_label("free") == "free"
    assert request_tier_label(" PRO ") == "pro"


# ---------------------------------------------------------------------------
# 2. 引擎上下文面：get_context 的 is_pro 派生（无 DB，纯依赖注入）
# ---------------------------------------------------------------------------


def _user_like(*, entitlement: str | None, flame_level: int) -> SimpleNamespace:
    return SimpleNamespace(
        entitlement=entitlement,
        flame_level=flame_level,
        flame_brightness=0.5,
        depth_preference=0.5,
        curiosity_preference=0.5,
        nickname="tester",
        username="tester",
    )


async def _get_context_for(user_like: SimpleNamespace) -> object:
    service = UserService(db_session=None, redis_client=None)
    service.get_user_by_id = AsyncMock(return_value=user_like)
    service._get_push_preference = AsyncMock(return_value=None)
    with patch.object(PreferenceService, "get_preferences", new=AsyncMock(return_value=None)):
        return await service.get_context("00000000-0000-0000-0000-000000000001")


@pytest.mark.asyncio
async def test_get_context_flame_sweep_keeps_is_pro_false_for_free_plan():
    """flame 1→10（free entitlement）→ is_pro 恒 False：改 flame 不改付费能力。"""
    for flame in range(1, 11):
        context = await _get_context_for(_user_like(entitlement="free", flame_level=flame))
        assert context is not None
        assert context.is_pro is False, f"flame={flame}"
        # flame 仅以展示层字段进入 preferences
        assert context.preferences["flame_level"] == flame


@pytest.mark.asyncio
async def test_get_context_missing_entitlement_field_degrades_to_free():
    """存量行/旧代码路径缺 entitlement 属性（getattr None）→ 安全 free，不抛异常。"""
    context = await _get_context_for(_user_like(entitlement=None, flame_level=15))
    assert context is not None
    assert context.is_pro is False


# ---------------------------------------------------------------------------
# 3. 请求链路：entitlement 变化立即生效（无缓存屏障）+ R-RISK-1 接线 + metrics
# ---------------------------------------------------------------------------


def test_entitlement_upgrade_immediately_relaxes_llm_ceiling():
    """付费状态 free→pro 后 ceiling 钳制立即解除：同一 router 实例、无重载。"""
    router = LLMRouter()

    set_request_user_tier("free")
    clamped = router.select_model(AgentRole.GENERATION, force_tier=ModelTier.MAX)
    assert clamped.free_tier_downgrade is True
    assert clamped.config.tier == ModelTier.FAST

    # entitlement free → pro（网关 snapshot → gRPC is_pro → ContextVar）
    set_request_user_tier("pro")
    upgraded = router.select_model(AgentRole.GENERATION, force_tier=ModelTier.MAX)
    assert upgraded.free_tier_downgrade is False
    assert upgraded.config.tier in (ModelTier.MAX, ModelTier.PRO)


def test_request_tier_wires_into_context_budget_dimensions(monkeypatch):
    """C-06 R-RISK-1 最小接线：context_data 缺 entitlement 时回落请求级 tier。"""
    from app.agents.standard_workflow import _resolve_budget_dimensions

    # 3a. 无任何信号 → settings 默认 free（成本 fail-safe）
    monkeypatch.setattr("app.config.settings.DEFAULT_CONTEXT_ENTITLEMENT", "free")
    set_request_user_tier(None)
    tier, decision = _resolve_budget_dimensions({"chat_mode": "standard"})
    assert tier == "free" and decision == "chat"

    # 3b. 请求级 tier=pro（真源 users.entitlement）→ 预算层 pro（接线生效）
    set_request_user_tier("pro")
    tier, _ = _resolve_budget_dimensions({"chat_mode": "standard"})
    assert tier == "pro"

    # 3c. 显式 context_data entitlement 优先（网关未来正向通道不被劫持）
    tier, _ = _resolve_budget_dimensions({"entitlement": "free"})
    assert tier == "free"

    # 3d. 显式 context_data entitlement=pro 在未标记请求面同样生效
    set_request_user_tier(None)
    tier, _ = _resolve_budget_dimensions({"user_context": {"entitlement": "pro"}})
    assert tier == "pro"


def test_downgrade_metric_carries_bounded_plan_label():
    """metrics 能区分 plan：钳制事件必须带 plan=free，可按付费层归因。"""
    router = LLMRouter()
    labels = {"agent_role": "generation", "from_tier": "max", "to_tier": "fast"}

    set_request_user_tier("free")
    before_free = REGISTRY.get_sample_value(METRIC_FREE_DOWNGRADE, {**labels, "plan": "free"}) or 0.0
    selection = router.select_model(AgentRole.GENERATION, force_tier=ModelTier.MAX)
    assert selection.free_tier_downgrade is True
    after_free = REGISTRY.get_sample_value(METRIC_FREE_DOWNGRADE, {**labels, "plan": "free"}) or 0.0
    assert after_free == pytest.approx(before_free + 1)

    # pro plan 的选择不产生任何 plan=free 的新增钳制
    set_request_user_tier("pro")
    router.select_model(AgentRole.GENERATION, force_tier=ModelTier.MAX)
    assert (REGISTRY.get_sample_value(METRIC_FREE_DOWNGRADE, {**labels, "plan": "free"}) or 0.0) == after_free


def test_selection_metric_distinguishes_plan():
    """选型计数按 plan 切片：free / pro / unknown（内部调用面）三态可观测。"""
    router = LLMRouter()

    def _selection_labels(selection) -> dict[str, str]:
        return {
            "agent_role": selection.agent_role.value,
            "model_key": selection.model_key,
            "provider": selection.config.provider.value,
            "tier": selection.config.tier.value,
            "task_type": "none",
            "complexity": "unknown",
            "fallback": "false",
        }

    set_request_user_tier("pro")
    pro_labels = _selection_labels(router.select_model(AgentRole.GENERATION))
    set_request_user_tier("free")
    free_labels = _selection_labels(router.select_model(AgentRole.GENERATION))
    set_request_user_tier(None)
    unknown_labels = _selection_labels(router.select_model(AgentRole.GENERATION))

    assert (REGISTRY.get_sample_value(METRIC_SELECTION, {**pro_labels, "plan": "pro"}) or 0.0) >= 1.0
    assert (REGISTRY.get_sample_value(METRIC_SELECTION, {**free_labels, "plan": "free"}) or 0.0) >= 1.0
    assert (REGISTRY.get_sample_value(METRIC_SELECTION, {**unknown_labels, "plan": "unknown"}) or 0.0) >= 1.0


# ---------------------------------------------------------------------------
# 4. 存量迁移安全默认：ent01_20260919 sqlite 隔离重放（主库只读纪律）
# ---------------------------------------------------------------------------


def _load_migration_module():
    spec = importlib.util.spec_from_file_location("ent01_20260919", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(name="pre_entitlement_sqlite")
def _pre_entitlement_sqlite(tmp_path):
    """bare sqlite：预置迁移前的 users 表 + 两条存量行（含 flame=15 游客）。"""
    engine = create_engine(f"sqlite:///{tmp_path / 'ent_test.db'}")
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE users (id VARCHAR(36) PRIMARY KEY, username VARCHAR(50), "
                "flame_level INTEGER NOT NULL DEFAULT 1)"
            )
        )
        conn.execute(text("INSERT INTO users (id, username, flame_level) VALUES ('g-1', 'guest', 15)"))
        conn.execute(text("INSERT INTO users (id, username, flame_level) VALUES ('u-1', 'email_user', 1)"))
    yield engine
    engine.dispose()


def test_ent01_migration_backfills_all_existing_users_to_free(pre_entitlement_sqlite):
    """迁移漏用户不可能：ADD COLUMN NOT NULL DEFAULT 'free' 自动回填全部存量行
    （含 flame=15 游客——宁降不升，游客不得被历史 flame 静默升级）。"""
    engine = pre_entitlement_sqlite
    module = _load_migration_module()
    assert module.down_revision == "ud01_20260919"  # 迁移链契约：单父挂当前 head

    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            module.upgrade()
        conn.commit()

    inspector = inspect(engine)
    column = next(c for c in inspector.get_columns("users") if c["name"] == "entitlement")
    assert column["nullable"] is False

    with engine.connect() as conn:
        rows = conn.execute(text("SELECT id, entitlement FROM users ORDER BY id")).all()
    assert rows == [("g-1", "free"), ("u-1", "free")]


def test_ent01_migration_is_reversible(pre_entitlement_sqlite):
    engine = pre_entitlement_sqlite
    module = _load_migration_module()

    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            module.upgrade()
            module.downgrade()
        conn.commit()

    column_names = {c["name"] for c in inspect(engine).get_columns("users")}
    assert "entitlement" not in column_names
