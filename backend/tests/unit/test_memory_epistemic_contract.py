"""M-01 Epistemic 契约不变量（纯契约层，无 DB）。

验证契约与既有资产的一致性：
- lane 注册表与 ConflictResolverService.KNOWN_SOURCE_LANES 同源；
- aurora_calibration_receipt 保留位存在但未被登记（V3-FIX-06 裁决=迁移写入点：
  本 lane 保留为未登记红线样例，live 写入点已改用登记 lane 并加守卫）；
- 状态机优先级、类型派生、provenance 分类、守卫谓词真值表。
"""

import re
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from app.services.conflict_resolver_service import ConflictResolverService
from app.services.memory_epistemic_contract import (
    EPOCH_BUMP_CORRECTION_ACTIONS,
    EPISODIC_EPISTEMIC_CLASSES,
    EXPLICIT_SOURCE_LANES,
    MEMORY_EPISTEMIC_CONTRACT_VERSION,
    RESERVED_UNREGISTERED_LANES,
    USER_STATEMENT_SOURCE_TYPES,
    EpistemicClass,
    MemoryRecordStatus,
    classify_episodic_class,
    derive_status,
    inferred_lane_may_supersede_lane,
    inferred_may_supersede,
    lane_priority,
    preference_write_provenance,
)


def test_contract_version_pinned():
    assert MEMORY_EPISTEMIC_CONTRACT_VERSION == "memory-v3.m01.v1"


def test_explicit_lanes_registered_as_explicit_tier_in_resolver():
    for lane in EXPLICIT_SOURCE_LANES:
        assert lane in ConflictResolverService.KNOWN_SOURCE_LANES
        assert ConflictResolverService.KNOWN_SOURCE_LANES[lane] == "explicit"


def test_lane_priority_ordering_matches_resolver_tiers():
    # explicit > rule(inferred_extraction) > llm > working_memory > unknown
    assert lane_priority("direct_capture") > lane_priority("inferred_extraction")
    assert lane_priority("inferred_extraction") > lane_priority("llm_extraction")
    assert lane_priority("llm_extraction") > lane_priority("working_memory")
    assert lane_priority("working_memory") > lane_priority("some_unregistered_lane")
    assert lane_priority(None) == lane_priority("some_unregistered_lane")


def test_aurora_calibration_receipt_reserved_but_not_registered():
    """红线用例：给位置、不裁决。

    V3-FIX-06 裁决=迁移写入点：correction_feedback 的 live 写入已改用登记 lane
    working_memory（test_calibration_receipt 回归锁），本 lane 保留在
    RESERVED_UNREGISTERED_LANES 作为未登记回退（unknown 档）的红线样例；
    若未来任何写方要复用该 lane，必须先在 KNOWN_SOURCE_LANES 登记位次。
    """
    assert "aurora_calibration_receipt" in RESERVED_UNREGISTERED_LANES
    assert "aurora_calibration_receipt" not in ConflictResolverService.KNOWN_SOURCE_LANES
    # 未登记 lane 在 epistemic 分类上保守落 HYPOTHESIS
    assert classify_episodic_class("aurora_calibration_receipt") == EpistemicClass.HYPOTHESIS.value


def test_all_app_source_lane_literals_are_registered():
    """V3-FIX-06 回归锁（登记完备性守卫）：app 代码中所有 source_lane 字面量
    必须已在仲裁登记表登记。

    未登记 lane 静默回退 unknown(0) 最低档（D2 契约）——写侧新引入未登记
    lane 字面量即令仲裁位次未定义。本守卫为字面量级扫描（动态拼接的 lane
    不在扫描面），与 write-point 回归锁（test_calibration_receipt）互补。
    """
    app_root = Path(__file__).resolve().parents[2] / "app"
    # 匹配 kwargs/赋值/带注解默认值三种形态；== 比较与 .get("source_lane") 不匹配
    pattern = re.compile(r'source_lane(?::\s*[A-Za-z\[\]| ,.]+?)?\s*=\s*"([a-z0-9_]+)"')
    offenders: list[str] = []
    scanned = 0
    for path in sorted(app_root.rglob("*.py")):
        if "__pycache__" in path.parts or "gen" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for match in pattern.finditer(text):
            scanned += 1
            lane = match.group(1)
            if lane not in ConflictResolverService.KNOWN_SOURCE_LANES:
                offenders.append(f"{path.relative_to(app_root)}: {lane}")
    assert scanned > 0, "扫描面意外为空（守卫自检失败）"
    assert not offenders, f"未登记 lane 字面量（先登记位次或改用登记 lane）: {offenders}"


def test_classify_episodic_class_rules():
    # R2-F1 收紧：FACT 仅限用户陈述。
    # user_confirmed lane：确认动作本身就是用户陈述 -> FACT。
    assert classify_episodic_class("user_confirmed") == EpistemicClass.FACT.value
    # direct_capture + 用户陈述 source_type -> FACT（大小写不敏感）。
    assert (
        classify_episodic_class("direct_capture", source_type="user_registered") == EpistemicClass.FACT.value
    )
    assert (
        classify_episodic_class("direct_capture", source_type="USER_REGISTERED") == EpistemicClass.FACT.value
    )
    # direct_capture + 机器写（chat_turn/analysis/reflection/...）-> OBSERVATION。
    assert classify_episodic_class("direct_capture", source_type="chat_turn") == (
        EpistemicClass.OBSERVATION.value
    )
    assert classify_episodic_class("direct_capture", source_type="analysis") == (
        EpistemicClass.OBSERVATION.value
    )
    # source_type 未知/缺失时保守落 OBSERVATION（不冒领事实档）。
    assert classify_episodic_class("direct_capture") == EpistemicClass.OBSERVATION.value
    assert classify_episodic_class("direct_capture", source_type=None) == EpistemicClass.OBSERVATION.value
    assert classify_episodic_class("direct_capture", source_type="") == EpistemicClass.OBSERVATION.value
    # 推断/未知 lane -> HYPOTHESIS。
    assert classify_episodic_class("inferred_extraction") == EpistemicClass.HYPOTHESIS.value
    assert classify_episodic_class("llm_extractor") == EpistemicClass.HYPOTHESIS.value
    assert classify_episodic_class(None) == EpistemicClass.HYPOTHESIS.value
    # 显式列优先（未来写方：OBSERVATION / EXPERIENCE）
    assert (
        classify_episodic_class("direct_capture", explicit_class="OBSERVATION")
        == EpistemicClass.OBSERVATION.value
    )
    assert (
        classify_episodic_class("inferred_extraction", explicit_class="EXPERIENCE")
        == EpistemicClass.EXPERIENCE.value
    )
    # 非法值回退 lane+source_type 派生；CONFIRMED_PREFERENCE 不是 episodic 合法类
    assert classify_episodic_class("direct_capture", explicit_class="bogus", source_type="user_registered") == (
        EpistemicClass.FACT.value
    )
    assert classify_episodic_class("direct_capture", explicit_class="bogus") == (
        EpistemicClass.OBSERVATION.value
    )
    assert classify_episodic_class("direct_capture", explicit_class="CONFIRMED_PREFERENCE") == (
        EpistemicClass.OBSERVATION.value
    )
    assert "CONFIRMED_PREFERENCE" not in EPISODIC_EPISTEMIC_CLASSES


def test_user_statement_source_types_evidence_based():
    """用户陈述集与 dev 库实证一致：仅 user_registered（机器写型不进集合）。"""
    assert USER_STATEMENT_SOURCE_TYPES == {"user_registered"}
    for machine_type in ("chat_turn", "analysis", "reflection", "error_analysis", "practice_outcome"):
        assert machine_type not in USER_STATEMENT_SOURCE_TYPES


def test_derive_status_precedence():
    now = datetime(2026, 9, 19, 12, 0, 0)

    def record(**kwargs):
        base = {
            "revoked_at": None,
            "retracted_at": None,
            "archived_at": None,
            "replaced_by_id": None,
            "superseded_by_id": None,
            "expires_at": None,
            "resolved_at": None,
        }
        base.update(kwargs)
        return SimpleNamespace(**base)

    assert derive_status(record()) == MemoryRecordStatus.ACTIVE.value
    # revoked 最高优先
    assert derive_status(record(revoked_at=now, retracted_at=now, replaced_by_id="x")) == (
        MemoryRecordStatus.REVOKED.value
    )
    # supersede 高于 retraction（链有后继记录）
    assert derive_status(record(retracted_at=now, replaced_by_id="x")) == (
        MemoryRecordStatus.SUPERSEDED.value
    )
    assert derive_status(record(retracted_at=now)) == MemoryRecordStatus.RETRACTED.value
    assert derive_status(record(archived_at=now)) == MemoryRecordStatus.ARCHIVED.value
    assert derive_status(record(expires_at=datetime(2026, 9, 1)), now=now) == MemoryRecordStatus.EXPIRED.value
    assert derive_status(record(expires_at=datetime(2026, 9, 30)), now=now) == MemoryRecordStatus.ACTIVE.value
    assert derive_status(record(resolved_at=now)) == MemoryRecordStatus.RESOLVED.value
    # episodic supersede 链
    assert derive_status(record(superseded_by_id="winner")) == MemoryRecordStatus.SUPERSEDED.value


def test_preference_write_provenance_classification():
    assert (
        preference_write_provenance(source_type="user_state", evidence_refs=[{"type": "user_state", "id": "ui"}])
        == "explicit"
    )
    assert preference_write_provenance(source_type="ai_inferred", evidence_refs=[]) == "inferred"
    assert (
        preference_write_provenance(
            source_type=None, evidence_refs=[{"type": "user_state", "id": "a"}, {"type": "ai_inferred", "id": "b"}]
        )
        == "inferred"
    )
    assert preference_write_provenance(source_type=None, evidence_refs=[]) == "explicit"
    assert preference_write_provenance(source_type=None, evidence_refs=None) == "explicit"


def test_inferred_may_supersede_truth_table():
    assert inferred_may_supersede("explicit", "inferred") is False  # 守卫核心
    assert inferred_may_supersede("explicit", "explicit") is True  # 用户纠错
    assert inferred_may_supersede("inferred", "inferred") is True  # 推断演化
    assert inferred_may_supersede("inferred", "explicit") is True  # 空链首写无 head 判定前


def test_inferred_lane_supersede_guard_truth_table():
    assert inferred_lane_may_supersede_lane("inferred_extraction", "direct_capture") is False
    assert inferred_lane_may_supersede_lane("direct_capture", "inferred_extraction") is True
    assert inferred_lane_may_supersede_lane("inferred_extraction", "inferred_extraction") is True
    assert inferred_lane_may_supersede_lane("llm_extraction", "working_memory") is True


def test_epoch_bump_action_set_covers_destructive_actions_only():
    assert EPOCH_BUMP_CORRECTION_ACTIONS == {"delete", "reject", "no_longer_applicable"}
    assert "confirm" not in EPOCH_BUMP_CORRECTION_ACTIONS
    assert "lower_confidence" not in EPOCH_BUMP_CORRECTION_ACTIONS
