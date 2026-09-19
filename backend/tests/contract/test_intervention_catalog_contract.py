"""A-02 · Intervention Catalog 冻结测试（parity guard）。

冻结内容（任何变更都需要 bump ``INTERVENTION_CATALOG_VERSION`` + reviewer）：
1. 目录 key 集 == A-01 契约词表 ``AURORA_INTERVENTION_TYPES``（**双源互检**：
   本测试独立 import 契约真源比对——目录不是抄写，是结构派生）；
2. 逐 item 元数据（capability/permission/expected_outcome/任务锚点/分配要求/
   proactive/inert/标称 mode）——parametrize 全 17 项，删任一 item 元数据
   → 目录构造 fail-fast → 本文件 import 红（变异必红，卡面设计要求）；
3. 封闭词表（INTERVENTION_CAPABILITIES / INTERVENTION_PERMISSIONS）精确集
   + sha256 钉法（A-01 契约测试同款双钉）；
4. 目录整体指纹 sha256（任何元数据语义变更 → 红）；
5. 既有策略面投影一致性：A-01 ``L2_INTERVENTION_TO_CATALOG`` 值 ⊆ 目录；
   spine ``_RULE_TABLE`` 全部 strategy（含 shadow learning 动态值）在
   ``SPINE_STRATEGY_TO_INTERVENTION`` 有映射且值 ⊆ 目录（无字符串自由动作）。
"""

from __future__ import annotations

import hashlib
import json

import pytest

from app.aurora.intervention_catalog import (
    INTERVENTION_CAPABILITIES,
    INTERVENTION_CATALOG,
    INTERVENTION_CATALOG_VERSION,
    INTERVENTION_PERMISSIONS,
    SPINE_STRATEGY_TO_INTERVENTION,
    InterventionCatalogItem,
    catalog_fingerprint,
)
# 双源互检：契约词表独立 import（不是从 catalog 模块转手拿）
from app.core.aurora_decision import AURORA_INTERVENTION_TYPES


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# 1. key 集结构派生（拼写地雷不可能：卡面 coexecute/connect ≠ 契约词表）
# ---------------------------------------------------------------------------


def test_catalog_keys_equal_frozen_contract_vocabulary() -> None:
    assert set(INTERVENTION_CATALOG) == set(AURORA_INTERVENTION_TYPES)
    assert len(INTERVENTION_CATALOG) == 17


def test_card_spelling_drift_tokens_absent_from_catalog() -> None:
    """卡面拼写漂移串（A-01 验收发现的地雷）不在目录——R0 确定性拒绝的根据。"""
    assert "coexecute" not in INTERVENTION_CATALOG
    assert "connect" not in INTERVENTION_CATALOG
    # 契约冻结拼写在目录
    assert "co_execute" in INTERVENTION_CATALOG
    assert "connect_peer" in INTERVENTION_CATALOG


def test_catalog_version_pinned() -> None:
    assert INTERVENTION_CATALOG_VERSION == "aurora_intervention_catalog.v1"


# ---------------------------------------------------------------------------
# 2. 逐 item 元数据（parametrize 全员；删任一元数据 → import 红 = 必红）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(AURORA_INTERVENTION_TYPES))
def test_every_item_has_complete_metadata(name: str) -> None:
    item = INTERVENTION_CATALOG[name]
    assert isinstance(item, InterventionCatalogItem)
    # capability / permission：封闭词表子集
    assert item.capability_requirements <= INTERVENTION_CAPABILITIES
    assert item.permission_requirements <= INTERVENTION_PERMISSIONS
    # expected outcome：非空声明式结果（卡面 acceptance ①）
    assert isinstance(item.expected_outcome, str) and item.expected_outcome.strip()
    # 分配要求自洽
    if item.requires_allocation:
        assert item.allocation_modes, "requires_allocation 必须声明允许的分配 mode"
        assert item.allocation_modes <= {"human", "agent", "hybrid"}
    else:
        assert not item.allocation_modes
    # inert ⟺ {no_action, abstain}（与 A-01 _INERT_INTERVENTIONS 同集）
    assert item.is_inert == (name in {"no_action", "abstain"})
    if item.is_inert:
        assert item.nominal_execution_mode is None
        assert not item.capability_requirements and not item.permission_requirements
    else:
        assert item.nominal_execution_mode in {"human", "agent", "hybrid"}


def test_actionable_items_with_metadata_never_free_strings() -> None:
    """无「字符串自由动作」：可行动干预都声明能力/权限前提与结果。"""
    for name, item in INTERVENTION_CATALOG.items():
        if not item.is_inert:
            assert item.capability_requirements, f"{name} 未声明能力前提"
            assert item.expected_outcome.strip()


def test_item_name_field_matches_key() -> None:
    for name, item in INTERVENTION_CATALOG.items():
        assert item.name == name


# ---------------------------------------------------------------------------
# 3. 封闭词表双钉（精确集 + sha256）
# ---------------------------------------------------------------------------


def test_capability_vocabulary_frozen() -> None:
    expected = {
        "chat",
        "llm_generate",
        "memory_read",
        "task_write",
        "scheduler",
        "peer_network",
        "tool_execution",
    }
    assert set(INTERVENTION_CAPABILITIES) == expected
    # sha256 钉法（A-01 同款双钉；改词表 → 此常量红，需 bump 版本 + reviewer）
    assert _sha256(json.dumps(sorted(INTERVENTION_CAPABILITIES))) == (
        _sha256(json.dumps(sorted(expected)))
    )
    assert _sha256(json.dumps(sorted(INTERVENTION_CAPABILITIES)))[:16] == "79cb8cd787feff73"


def test_permission_vocabulary_frozen() -> None:
    expected = {
        "memory_read",
        "plan_adjust",
        "task_execute",
        "model_write",
        "peer_contact",
        "proactive_contact",
    }
    assert set(INTERVENTION_PERMISSIONS) == expected
    assert _sha256(json.dumps(sorted(INTERVENTION_PERMISSIONS)))[:16] == "1187ca43db517456"


# ---------------------------------------------------------------------------
# 4. 目录整体指纹（任何元数据变更 → 红；变更合法时随版本 bump 更新钉值）
# ---------------------------------------------------------------------------


def test_catalog_fingerprint_pinned() -> None:
    assert catalog_fingerprint() == "1494d1cd698e02a5"


def test_catalog_fingerprint_stable_and_deterministic() -> None:
    assert catalog_fingerprint() == catalog_fingerprint()


# ---------------------------------------------------------------------------
# 5. 既有策略面投影一致性（映射现有 policies，卡面 Work 1 机制化面）
# ---------------------------------------------------------------------------


def test_l2_frozen_mapping_values_within_catalog() -> None:
    """A-01 冻结的 L2 映射值必须仍是目录成员（跨卡一致性）。"""
    from app.aurora.runtime_v1.l2_intervention import L2_INTERVENTION_TO_CATALOG

    for l2_name, catalog_name in L2_INTERVENTION_TO_CATALOG.items():
        assert catalog_name in INTERVENTION_CATALOG, f"L2 {l2_name} -> {catalog_name} 不在目录"


def test_spine_rule_table_strategies_fully_mapped() -> None:
    """spine _RULE_TABLE 全部 primary/secondary strategy（含 shadow 动态切换值）
    都有目录投影——全覆盖、零自由串残留。"""
    from app.signals.policy_engine import _RULE_TABLE

    strategies: set[str] = set()
    for entries in _RULE_TABLE.values():
        for rule in entries.values():
            primary = rule.get("primary_strategy")
            secondary = rule.get("secondary_strategy")
            if isinstance(primary, str):
                strategies.add(primary)
            if isinstance(secondary, str):
                strategies.add(secondary)
    strategies.add("switch_to_worked_example")  # _apply_shadow_learning 的动态切换值

    mapped = set(SPINE_STRATEGY_TO_INTERVENTION)
    assert strategies == mapped, f"映射失配：缺 {sorted(strategies - mapped)}，多 {sorted(mapped - strategies)}"
    for strategy, catalog_name in SPINE_STRATEGY_TO_INTERVENTION.items():
        assert catalog_name in INTERVENTION_CATALOG, f"策略 {strategy} 投影到目录外 {catalog_name!r}"


def test_spine_projection_covers_full_catalog_semantic_families() -> None:
    """投影值覆盖主要语义族（rescope/practice/retrieve/clarify/pause/remind/
    review/connect_peer/explain/split/no_action）——目录不是空转清单。"""
    projected = set(SPINE_STRATEGY_TO_INTERVENTION.values())
    assert {
        "rescope",
        "practice",
        "retrieve",
        "clarify",
        "pause",
        "remind",
        "review",
        "connect_peer",
        "explain",
        "split",
        "no_action",
    } <= projected
