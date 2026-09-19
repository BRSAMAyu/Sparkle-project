"""A-04 · Aurora 联合决策契约冻结测试（aurora_joint_decision.v1）。

双钉纪律（A-01/A-02 契约测试同款）：精确集 + sha256。扩词表/改交付表 →
本文件红——需 bump ``JOINT_DECISION_VERSION`` 并过两位 reviewer（冻结声明
见模块 docstring）。覆盖面：

1. ``JOINT_REASONS`` 精确集 + sha256（11 码：J1..J5 / D1..D4 / X1 / E1）；
2. ``JOINT_LAYERS`` 精确集 + sha256（与 A-02/X-02 产层语义同构）；
3. ``JOINT_STEP_BOUND_DELIVERY_MODES`` 冻结表：精确键集 + 每键精确交付集 +
   整表 sha256（语义变更 → 红）；
4. **互检钉（import 期 fail-fast 的测试面对偶）**：
   - 交付表键 ⊆ AURORA_INTERVENTION_TYPES（词表漂移红）；
   - requires_allocation 三项（delegate/execute/co_execute）的交付集与
     A-02 目录 ``allocation_modes`` 精确相等（catalog 是冻结真源）；
   - 步绑定表 ∪ 系统面 = 目录全量（17 项二分完备——无「既非步绑定也非
     系统面」的第三类悬空成员）；
5. ``VARIANT_CAPABILITY_PROJECTION``（joint_factor_projection）冻结：四变体
   精确映射 + 全能力词表覆盖断言（每个能力至少被一个变体投影，防死能力）；
6. 事件名复用断言：``JOINT_DECISION_EVENT_NAME == "decision.recorded"``（D-01
   registry 既有 reserved 名，零新增）。

哈希种子纪律：全部集合断言经 sorted（任意 PYTHONHASHSEED 下一致）。
"""

from __future__ import annotations

import hashlib
import json

from app.aurora.intervention_catalog import INTERVENTION_CATALOG
from app.aurora.joint_decision import (
    JOINT_DECISION_EVENT_NAME,
    JOINT_DECISION_VERSION,
    JOINT_LAYERS,
    JOINT_REASONS,
    JOINT_STEP_BOUND_DELIVERY_MODES,
)
from app.aurora.joint_factor_projection import VARIANT_CAPABILITY_PROJECTION
from app.core.aurora_decision import AURORA_INTERVENTION_TYPES


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


# 1. JOINT_REASONS 精确集 + sha256 双钉 --------------------------------------


def test_joint_reasons_exact_set() -> None:
    expected = {
        "J1.delivery_mode_incompatible",
        "J2.mode_outside_allocation_feasible",
        "J3.inert_must_not_carry_mode",
        "J4.learning_deskilling_pair",
        "J5.requires_allocation_unbacked",
        "D1.first_legal_joint_nominee",
        "D2.no_legal_joint_nominee_no_action",
        "D3.conflict_allocation_precedence",
        "D4.delivery_reallocation_applied",
        "X1.explicit_user_request_priority",
        "E1.degraded_to_rule_default",
    }
    assert set(JOINT_REASONS) == expected
    # sha256 双钉（改词表 → 此常量红；bump JOINT_DECISION_VERSION + 双 reviewer）
    assert _sha256(json.dumps(sorted(JOINT_REASONS))) == _sha256(json.dumps(sorted(expected)))
    assert _sha256(json.dumps(sorted(JOINT_REASONS)))[:16] == "ca5ef3def40f1cdd"


def test_joint_layers_exact_set() -> None:
    assert set(JOINT_LAYERS) == {"rule", "semantic", "semantic_fallback", "error_degraded"}
    assert _sha256(json.dumps(sorted(JOINT_LAYERS)))[:16] == "707d648f05eec565"


# 2. 步绑定交付表冻结 --------------------------------------------------------


def test_step_bound_delivery_table_frozen() -> None:
    expected: dict[str, set[str]] = {
        "delegate": {"agent"},
        "execute": {"agent"},
        "co_execute": {"hybrid"},
        "practice": {"hybrid"},
        "review": {"agent", "hybrid"},
        "rescope": {"hybrid"},
        "split": {"hybrid"},
        "schedule": {"hybrid"},
    }
    actual = {name: set(modes) for name, modes in JOINT_STEP_BOUND_DELIVERY_MODES.items()}
    assert actual == expected
    # 整表 sha256（语义重映射——如 practice 改允许 agent——必红）
    canonical = json.dumps(
        {name: sorted(modes) for name, modes in sorted(JOINT_STEP_BOUND_DELIVERY_MODES.items())},
        sort_keys=True,
        separators=(",", ":"),
    )
    assert _sha256(canonical)[:16] == "ca20e41c5aa644ca"


def test_step_bound_keys_within_contract_vocabulary() -> None:
    assert set(JOINT_STEP_BOUND_DELIVERY_MODES) <= set(AURORA_INTERVENTION_TYPES)


def test_requires_allocation_delivery_equals_catalog() -> None:
    """requires_allocation 三项的交付集 = A-02 目录 allocation_modes（真源）。"""
    for name, modes in JOINT_STEP_BOUND_DELIVERY_MODES.items():
        item = INTERVENTION_CATALOG[name]
        if item.requires_allocation:
            assert set(modes) == set(item.allocation_modes), (
                f"{name}: delivery {sorted(modes)} != catalog {sorted(item.allocation_modes)}"
            )


def test_catalog_bipartition_complete() -> None:
    """目录 17 项 = 步绑定 8 项 ∪ 系统面（inert 2 + 非步绑定非 inert）——
    二分完备：不存在既非步绑定也未被系统面语义覆盖的悬空成员。"""
    step_bound = set(JOINT_STEP_BOUND_DELIVERY_MODES)
    inert = {name for name, item in INTERVENTION_CATALOG.items() if item.is_inert}
    system_surface = {
        name
        for name, item in INTERVENTION_CATALOG.items()
        if not item.is_inert and name not in step_bound
    }
    assert inert == {"no_action", "abstain"}
    assert system_surface == {
        "clarify", "explain", "retrieve", "reflect", "connect_peer", "pause", "remind",
    }
    assert step_bound | inert | system_surface == set(AURORA_INTERVENTION_TYPES)
    assert not (step_bound & system_surface)


# 3. 投影器冻结表 -------------------------------------------------------------


def test_variant_capability_projection_frozen() -> None:
    expected: dict[str, set[str]] = {
        "default_conversation": {"chat"},
        "task_execution": {"chat", "llm_generate", "task_write", "tool_execution"},
        "meta_reflection": {"chat", "llm_generate", "memory_read"},
        "holding_mode": {"chat"},
    }
    actual = {name: set(modes) for name, modes in VARIANT_CAPABILITY_PROJECTION.items()}
    assert actual == expected


def test_variant_projection_covers_all_capabilities() -> None:
    """投影能力 ⊆ 词表（不产词表外能力）；Gate 0 registry 四变体未覆盖的
    能力面显式钉死（scheduler/peer_network——remind/connect_peer 的域，属
    R-07/同侪面而非 interaction_model 变体面）。词表扩成员而未更新投影 →
    此钉红，强制接线日显式决策。"""
    projected = set().union(*VARIANT_CAPABILITY_PROJECTION.values())
    from app.aurora.intervention_catalog import INTERVENTION_CAPABILITIES

    assert projected <= set(INTERVENTION_CAPABILITIES)
    assert set(INTERVENTION_CAPABILITIES) - projected == {"scheduler", "peer_network"}


# 4. 事件名与版本纪律 ---------------------------------------------------------


def test_event_name_reuses_registry_reserved_name() -> None:
    from app.core.event_registry import EVENT_REGISTRY

    assert JOINT_DECISION_EVENT_NAME == "decision.recorded"
    assert JOINT_DECISION_EVENT_NAME in EVENT_REGISTRY


def test_joint_decision_version_string() -> None:
    assert JOINT_DECISION_VERSION == "aurora_joint_decision.v1"
