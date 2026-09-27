"""O-06 · 统一操作面单元测试 —— 注册表完整性 / 受控翻转 / per-capability 回滚.

完整性守卫是**生成式对账**（AST 扫源码里的 KillSwitchBinding 调用 vs 注册表），
不是手抄金样表——新增绑定漏登 spec 会直接红，删绑定残留 spec 同样红。
"""

from __future__ import annotations

import ast
from pathlib import Path

import fakeredis.aioredis
import pytest

from app.config import Settings
from app.core import ops_surface
from app.core.kill_switch import TRI_STATE_MODES
from app.core.ops_surface import (
    CAPABILITY_SPECS,
    CapabilitySpec,
    InvalidModeError,
    NoRollbackPointError,
    RedisUnavailableError,
    UnknownCapabilityError,
    get_spec,
    resolve_binding,
)

_APP_DIR = Path(__file__).resolve().parents[2] / "app"


# ---------------------------------------------------------------------------
# 注册表完整性（生成式对账 + 不变量）
# ---------------------------------------------------------------------------


def _collect_binding_settings_attrs() -> set[str]:
    """AST 扫全 app/ 的 KillSwitchBinding(...) 调用，收集 settings_attr 字面量."""
    attrs: set[str] = set()
    for path in sorted(_APP_DIR.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "KillSwitchBinding":
                for kw in node.keywords:
                    if kw.arg == "settings_attr" and isinstance(kw.value, ast.Constant):
                        attrs.add(str(kw.value.value))
    return attrs


def test_registry_ids_unique_and_match_stage_feature_labels():
    ids = [spec.capability_id for spec in CAPABILITY_SPECS]
    assert len(ids) == len(set(ids)), "capability_id 必须唯一"
    for spec in CAPABILITY_SPECS:
        binding = resolve_binding(spec)
        assert (
            spec.capability_id == f"{binding.stage}.{binding.feature}"
        ), f"{spec.capability_id} 必须与 Prometheus KILL_SWITCH_MODE (stage, feature) 逐字对齐"
        assert binding.allowed_modes == TRI_STATE_MODES


def test_registry_covers_every_source_binding_and_no_ghost_specs():
    source_attrs = _collect_binding_settings_attrs()
    registry_attrs = {
        resolve_binding(spec).settings_attr for spec in CAPABILITY_SPECS if resolve_binding(spec).settings_attr
    }
    # 注意：settings_attr= 字面量还出现在非绑定场景（如 metacognition_registry 的
    # ConfidenceProxyDefinition，getattr 直读 settings）——AST 扫描限定
    # KillSwitchBinding 调用后两者不应再混淆；若本断言红，说明出现了未注册的新绑定。
    assert (
        source_attrs == registry_attrs
    ), f"未注册绑定: {sorted(source_attrs - registry_attrs)}; 幽灵 spec: {sorted(registry_attrs - source_attrs)}"


def test_registry_settings_attrs_exist_in_settings():
    for spec in CAPABILITY_SPECS:
        binding = resolve_binding(spec)
        if binding.settings_attr is not None:
            assert binding.settings_attr in Settings.model_fields, f"{binding.settings_attr} 不在 Settings 权威字段中"


def test_registry_domains_closed_vocabulary():
    for spec in CAPABILITY_SPECS:
        assert spec.domain in ops_surface.DOMAINS


def test_registry_redis_keys_unique():
    keys = [f"{spec.prefix}{resolve_binding(spec).redis_key}" for spec in CAPABILITY_SPECS]
    assert len(keys) == len(set(keys)), "prefix+redis_key 组合必须唯一（同键双 spec=双权威写入口）"


def test_registry_prefix_matches_owning_service_class_constants():
    """prefix 必须与拥有方模块的前缀常量一致（字面量 "sparkle:"/"aurora:" 除外）.

    stage37/39/slo_* 的拥有方把 prefix 硬编码为 "sparkle:" 传参、fme_l3_closure_bridge
    硬编码 "aurora:"（均无常量可对账，跳过）；其余模块必持有类级 PREFIX 或模块级
    *PREFIX 常量（如 routing_parameter_registry.REDIS_KEY_PREFIX），spec.prefix 逐字对账。
    """
    import importlib

    for spec in CAPABILITY_SPECS:
        if spec.prefix in {"sparkle:", "aurora:"}:
            continue  # 拥有方以字面量传参的家族，无常量可核对
        module = importlib.import_module(spec.module)
        candidates = set()
        for name in dir(module):
            obj = getattr(module, name)
            if isinstance(obj, type) and hasattr(obj, "PREFIX"):
                candidates.add(obj.PREFIX)
            if "PREFIX" in name and isinstance(obj, str):
                candidates.add(obj)
        if not candidates:
            continue  # 模块无常量形态，无法对账（如实跳过）
        assert (
            spec.prefix in candidates
        ), f"{spec.capability_id}: prefix {spec.prefix!r} 不在该模块前缀常量 {candidates} 中"


def test_get_spec_unknown_fails_closed():
    with pytest.raises(UnknownCapabilityError):
        get_spec("no.such.capability")
    with pytest.raises(UnknownCapabilityError):
        get_spec("")


def test_resolve_binding_type_guard():
    spec = next(s for s in CAPABILITY_SPECS if s.capability_id == "dual_core_router.mode")
    from app.core.kill_switch import KillSwitchBinding

    assert isinstance(resolve_binding(spec), KillSwitchBinding)


# ---------------------------------------------------------------------------
# 受控翻转 + 回滚（fakeredis 进程内真实 Redis 语义）
# ---------------------------------------------------------------------------


@pytest.fixture
async def fake_redis():
    # decode_responses=True 与生产 cache_service 客户端同构（cache.py:73）。
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.aclose()


def _spec(capability_id: str) -> CapabilitySpec:
    return get_spec(capability_id)


async def test_set_mode_records_history_and_flips(fake_redis):
    spec = _spec("dual_core_router.mode")
    baseline = await ops_surface.capability_snapshot(fake_redis, spec)
    result = await ops_surface.set_capability_mode(fake_redis, spec, "shadow", actor="tester", reason="unit")
    assert result["previous_mode"] == baseline["mode"]
    assert result["mode"] == "shadow"
    assert result["history_recorded"] is True
    snapshot = await ops_surface.capability_snapshot(fake_redis, spec)
    assert snapshot["mode"] == "shadow"
    history = await ops_surface.capability_history(fake_redis, spec)
    assert history[0]["action"] == "set"
    assert history[0]["from"] == baseline["mode"]
    assert history[0]["to"] == "shadow"
    assert history[0]["actor"] == "tester"
    assert history[0]["reason"] == "unit"


async def test_invalid_mode_rejected_not_coerced(fake_redis):
    """词表外 mode 必须显式拒绝——不得静默回落 fallback_mode（运维面红线）."""
    spec = _spec("dual_core_router.mode")
    before = await ops_surface.capability_snapshot(fake_redis, spec)
    with pytest.raises(InvalidModeError):
        await ops_surface.set_capability_mode(fake_redis, spec, "bogus")
    after = await ops_surface.capability_snapshot(fake_redis, spec)
    assert after["mode"] == before["mode"]
    assert await ops_surface.capability_history(fake_redis, spec) == []


async def test_mode_aliases_accepted(fake_redis):
    spec = _spec("dual_core_router.mode")
    result = await ops_surface.set_capability_mode(fake_redis, spec, "on")
    assert result["mode"] == "live"


async def test_set_mode_requires_redis():
    spec = _spec("dual_core_router.mode")
    with pytest.raises(RedisUnavailableError):
        await ops_surface.set_capability_mode(None, spec, "shadow")


async def test_rollback_restores_previous_mode_stepwise(fake_redis):
    """两次翻转后连续回滚：off→shadow→live 逐级步进，史尽后 409 语义."""
    spec = _spec("dual_core_router.mode")
    await ops_surface.set_capability_mode(fake_redis, spec, "live")  # entry: from=baseline
    await ops_surface.set_capability_mode(fake_redis, spec, "shadow")  # entry: from=live
    await ops_surface.set_capability_mode(fake_redis, spec, "off")  # entry: from=shadow

    rb1 = await ops_surface.rollback_capability(fake_redis, spec)
    assert rb1["mode"] == "shadow"  # 最近异值恢复点
    rb2 = await ops_surface.rollback_capability(fake_redis, spec)
    assert rb2["mode"] == "live"
    with pytest.raises(NoRollbackPointError):
        await ops_surface.rollback_capability(fake_redis, spec)


async def test_rollback_noop_when_already_at_restore_point(fake_redis):
    """翻转后立刻回滚、再无史：第二次回滚必须 409 而不是来回震荡."""
    spec = _spec("dual_core_router.mode")
    baseline = (await ops_surface.capability_snapshot(fake_redis, spec))["mode"]
    await ops_surface.set_capability_mode(fake_redis, spec, "shadow")
    rb = await ops_surface.rollback_capability(fake_redis, spec)
    assert rb["mode"] == baseline
    with pytest.raises(NoRollbackPointError):
        await ops_surface.rollback_capability(fake_redis, spec)


async def test_rollback_requires_redis():
    with pytest.raises(RedisUnavailableError):
        await ops_surface.rollback_capability(None, _spec("dual_core_router.mode"))


async def test_mode_switch_never_touches_user_state(fake_redis):
    """验收：shadow/live 切换不丢用户 state——翻转/回滚全程只写能力模式键."""
    spec = _spec("39.mode")
    user_state_key = "aurora:stage39:user:42:some_state"
    await fake_redis.set(user_state_key, "irreplaceable")
    mode_key = f"{spec.prefix}{resolve_binding(spec).redis_key}"

    await ops_surface.set_capability_mode(fake_redis, spec, "shadow")
    await ops_surface.rollback_capability(fake_redis, spec)

    assert await fake_redis.get(user_state_key) == "irreplaceable"
    assert await fake_redis.get(mode_key) is not None  # 模式键仍在其位（回滚恢复后的值）


async def test_history_corrupt_entries_skipped(fake_redis):
    spec = _spec("dual_core_router.mode")
    await fake_redis.lpush(ops_surface.HISTORY_KEY_TEMPLATE.format(capability_id=spec.capability_id), "{not-json")
    await ops_surface.set_capability_mode(fake_redis, spec, "shadow")
    history = await ops_surface.capability_history(fake_redis, spec)
    assert len(history) == 1


async def test_rollback_skips_corrupt_entries(fake_redis):
    spec = _spec("dual_core_router.mode")
    baseline = (await ops_surface.capability_snapshot(fake_redis, spec))["mode"]
    key = ops_surface.HISTORY_KEY_TEMPLATE.format(capability_id=spec.capability_id)
    await ops_surface.set_capability_mode(fake_redis, spec, "shadow")
    await fake_redis.lpush(key, "{corrupted")  # 混入损坏头记录
    rb = await ops_surface.rollback_capability(fake_redis, spec)
    assert rb["mode"] == baseline


async def test_history_bounded_and_ttl_set(fake_redis):
    spec = _spec("dual_core_router.mode")
    for mode in ("live", "shadow", "live", "shadow", "off"):
        await ops_surface.set_capability_mode(fake_redis, spec, mode)
    key = ops_surface.HISTORY_KEY_TEMPLATE.format(capability_id=spec.capability_id)
    assert await fake_redis.llen(key) <= ops_surface.HISTORY_MAX_ENTRIES
    ttl = await fake_redis.ttl(key)
    assert 0 < ttl <= ops_surface.HISTORY_TTL_SECONDS


# ---------------------------------------------------------------------------
# release manifest
# ---------------------------------------------------------------------------


async def test_release_manifest_snapshot_shape():
    from app.core.release_manifest import build_release_manifest

    manifest = await build_release_manifest(db=None)
    assert manifest["manifest_version"] == 1
    assert set(manifest) == {"manifest_version", "generated_at", "model", "config", "migration"}
    assert manifest["model"]["llm_model_name"]
    # release 五旗契约键集（app.config.release_flags 冻结形制）
    assert set(manifest["config"]["release_flags"]) == {
        "shop",
        "photon_transfer",
        "public_leaderboards",
        "public_community",
        "visual_elements",
    }
    assert manifest["config"]["capability_mode_count"] == len(CAPABILITY_SPECS)
    assert set(manifest["config"]["capability_settings_modes"]) == {spec.capability_id for spec in CAPABILITY_SPECS}
    # db=None → database_revision 如实缺席（不伪造）；code_head 侧 alembic.ini 在位应可解析
    assert manifest["migration"]["database_revision"] is None
    assert manifest["migration"]["error"] is not None or manifest["migration"]["code_head"] is not None


async def test_release_manifest_migration_against_sqlite_db():
    """对 sqlite 内存库：alembic_version 表缺席 → error 注记，不炸清单."""
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.core.release_manifest import build_release_manifest

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.connect() as conn:
        manifest = await build_release_manifest(db=conn)
    await engine.dispose()
    assert manifest["migration"]["database_revision"] is None
    assert "database_revision unavailable" in (manifest["migration"]["error"] or "")
