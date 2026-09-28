"""V4-I01 · ``episode_resume_view.v1`` 契约守卫（纯函数，零 IO）。

冻结面（V4-B05 合同 §5 + §4/§4.1 why_now 字段位 + §9 反例；卡 V4-I01）：
- 视图字段集封闭：恰为 RESUME_VIEW_FIELDS（§5 全字段 + why_now 字段位投影）；
- why_now v1 行 = null 语义：v1 行缺字段位不臆测回填，且除 why_now 外
  payload 与「无 why_now」逐键相等（§8 双读：v1 路径行为不变）；
- why_now 子结构校验失败 → 字段级降级（仅 why_now null + 原因，§4.1），
  过期 why-now 不当作当前原因复用（§4）；
- ``last_valid_outcome.truth_class`` 与 D-02 ``TruthClass`` 全 5 值 1:1
  （demo 透传不排除，R1-C4）；词表外值 fail-loud；
- ``expires_at`` 过期 / memory epoch 变更 → stale 可判定（§5 freshness +
  §9 反例「过期 EpisodeResumeView 自动接续」）；
- 无历史不造分数：视图不存在任何进度/精通/分钟数字段（结构封闭检查钉死）。
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.core.episode_resume_view import (
    CONTEXT_SELECTION_REF_SCHEME,
    EPISODE_RESUME_VIEW_SCHEMA_VERSION,
    RESUME_DEGRADE_REASONS,
    RESUME_VIEW_FIELDS,
    STEP_REF_SCHEMES,
    TRUTH_CLASS_VALUES,
    WHY_NOW_CONFIDENCE_BANDS,
    assemble_resume_view,
    normalize_why_now,
    resume_view_stale_reason,
    validate_resume_view_shape,
)
from app.core.outcome_ledger import TruthClass

_NOW = datetime(2026, 9, 28, 8, 55, 0)
_RECEIPT_REF = "context_selection://csr_01JBG7V4B05EXAMPLE000000"


def _base_kwargs() -> dict:
    return {
        "goal_id": "7a1c9e02-88b1-4d2e-b3c4-998877665544",
        "task_id": "3f2b9c1e-4d55-4a10-9e2a-112233445566",
        "run_id": None,
        "last_outcome": {
            "outcome_id": "outc_9d41c2aa77bb00ff1122",
            "truth_class": "actual",
            "recorded_at": datetime(2026, 9, 27, 21, 4, 0),
        },
        "last_step": {
            "step_ref": "subtask://st_5566aabb",
            "description": "完成「示例→自己做→检查」计划中的自己做步",
            "confirmed_at": datetime(2026, 9, 27, 21, 4, 0),
            "version_token": "2026-09-27T21:04:00.000000",
        },
        "pending_step": {
            "description": "独立完成 1 道同型题并通过自查清单",
            "cognitive_ownership": "user_core",
            "execution_mode": "hybrid",
        },
        "why_now": None,
        "computed_at": _NOW,
        "expires_at": _NOW + timedelta(seconds=30 * 60),
        "context_receipt_ref": _RECEIPT_REF,
        "memory_epoch": 42,
    }


def _view(**overrides) -> dict:
    return assemble_resume_view(**{**_base_kwargs(), **overrides})


# ---------------------------------------------------------------------------
# 冻结结构
# ---------------------------------------------------------------------------


def test_frozen_field_set_matches_b05_section5_plus_why_now():
    assert {
        "schema_version",
        "goal_ref",
        "task_ref",
        "run_ref",
        "last_valid_outcome",
        "last_confirmed_step",
        "pending_human_step",
        "why_now",
        "expires_at",
        "freshness",
    } == RESUME_VIEW_FIELDS


def test_assembled_view_shape_and_values():
    view = _view()
    assert validate_resume_view_shape(view) == ()
    assert view["schema_version"] == EPISODE_RESUME_VIEW_SCHEMA_VERSION == "episode_resume_view.v1"
    assert view["goal_ref"] == "goal://7a1c9e02-88b1-4d2e-b3c4-998877665544"
    assert view["task_ref"] == "task://3f2b9c1e-4d55-4a10-9e2a-112233445566"
    assert view["run_ref"] is None  # 无在途 run
    assert view["last_valid_outcome"] == {
        "outcome_ref": "outcome://outc_9d41c2aa77bb00ff1122",
        "truth_class": "actual",
        "recorded_at": "2026-09-27T21:04:00",
    }
    assert view["last_confirmed_step"]["step_ref"] == "subtask://st_5566aabb"
    assert view["pending_human_step"] == {
        "description": "独立完成 1 道同型题并通过自查清单",
        "cognitive_ownership": "user_core",
        "execution_mode": "hybrid",
    }
    assert view["why_now"] is None  # v1 行缺省补位
    assert view["expires_at"] == "2026-09-28T09:25:00"
    assert view["freshness"] == {
        "context_receipt_ref": _RECEIPT_REF,
        "computed_at": "2026-09-28T08:55:00",
        "memory_epoch_at_compute": 42,
    }


def test_run_ref_present_when_inflight_run():
    view = _view(run_id="abc123")
    assert view["run_ref"] == "run://abc123"


def test_shape_check_rejects_extra_or_missing_fields():
    view = _view()
    drifted = dict(view)
    drifted["progress"] = 0.5  # 无历史不造分数：任何进度/分数类字段都是结构漂移
    assert any("unknown fields" in v for v in validate_resume_view_shape(drifted))
    trimmed = {k: v for k, v in view.items() if k != "freshness"}
    assert any("missing fields" in v for v in validate_resume_view_shape(trimmed))


# ---------------------------------------------------------------------------
# truth_class 与 D-02 全 5 值 1:1（demo 透传）
# ---------------------------------------------------------------------------


def test_truth_class_vocabulary_is_d02_full_five_values():
    assert {member.value for member in TruthClass} == TRUTH_CLASS_VALUES
    assert {"actual", "self_reported", "estimated", "demo", "unknown"} == TRUTH_CLASS_VALUES


def test_demo_truth_class_passthrough_not_excluded():
    view = _view(last_outcome={"outcome_id": "outc_demo", "truth_class": "demo", "recorded_at": _NOW})
    assert view["last_valid_outcome"]["truth_class"] == "demo"  # R1-C4：透传不排除


def test_unknown_truth_class_fails_loud():
    with pytest.raises(ValueError, match="TruthClass"):
        _view(last_outcome={"outcome_id": "x", "truth_class": "mastered", "recorded_at": _NOW})


# ---------------------------------------------------------------------------
# step_ref / receipt ref 封闭 scheme
# ---------------------------------------------------------------------------


def test_step_ref_scheme_closed():
    assert {"task", "subtask"} == STEP_REF_SCHEMES
    with pytest.raises(ValueError, match="step_ref"):
        _view(last_step={"step_ref": "run://r1", "description": "x", "confirmed_at": _NOW, "version_token": None})
    with pytest.raises(ValueError, match="step_ref"):
        _view(last_step={"step_ref": "subtask://", "description": "x", "confirmed_at": _NOW, "version_token": None})


def test_task_level_step_ref_allowed():
    view = _view(
        last_step={
            "step_ref": "task://3f2b9c1e-4d55-4a10-9e2a-112233445566",
            "description": "任务标题",
            "confirmed_at": _NOW,
            "version_token": None,
        }
    )
    assert view["last_confirmed_step"]["step_ref"].startswith("task://")


def test_context_receipt_ref_scheme_enforced():
    assert CONTEXT_SELECTION_REF_SCHEME == "context_selection"
    with pytest.raises(ValueError, match="context_receipt_ref"):
        _view(context_receipt_ref="outcome://outc_x")  # 跨 scheme 绑定拒绝（I3 同纪律）


# ---------------------------------------------------------------------------
# why_now：v1 行 null 语义 + 字段级降级（§4 / §4.1）
# ---------------------------------------------------------------------------


def test_why_now_v1_row_is_null_no_fabrication():
    """v1 行（无 why_now 字段位）→ null；且除 why_now 键外与无-why_now 构建逐键相等。"""
    v1_row_view = _view(why_now=None)
    assert v1_row_view["why_now"] is None
    baseline = dict(v1_row_view)
    baseline.pop("why_now")
    rebuilt = dict(_view())
    rebuilt.pop("why_now")
    assert baseline == rebuilt  # v1 路径行为不变（§8 双读）


def test_why_now_valid_v11_shape_round_trips():
    payload, reason = normalize_why_now(
        {
            "statement": "距考试 9 天，此步解锁真题限时训练",
            "basis_refs": ["goal://7a1c9e02", "memory://episodic/m1"],
            "expires_at": _NOW + timedelta(hours=6),
            "confidence_band": "medium",
        },
        now=_NOW,
    )
    assert reason is None
    assert payload == {
        "statement": "距考试 9 天，此步解锁真题限时训练",
        "basis_refs": ["goal://7a1c9e02", "memory://episodic/m1"],
        "expires_at": "2026-09-28T14:55:00",
        "confidence_band": "medium",
    }
    view = _view(why_now=payload)
    assert view["why_now"] == payload


def test_why_now_null_semantics_all_tasks_without_field():
    payload, reason = normalize_why_now(None, now=_NOW)
    assert payload is None and reason is None  # 正常态，非降级


@pytest.mark.parametrize(
    ("raw", "reason_prefix"),
    [
        ({"statement": "s"}, "why_now_basis_refs_empty"),  # 无依据的 why-now = 伪依据
        ({"statement": "s", "basis_refs": ["evil://x"]}, "why_now_basis_ref_unknown_scheme"),
        ({"statement": "", "basis_refs": ["task://t"]}, "why_now_statement_invalid"),
        ({"statement": "x" * 201, "basis_refs": ["task://t"]}, "why_now_statement_invalid"),
        ({"statement": "s", "basis_refs": ["task://t"], "confidence_band": "99%"}, "why_now_confidence_band_invalid"),
        ({"statement": "s", "basis_refs": ["task://t"], "extra": 1}, "why_now_unknown_keys"),
        (
            {"statement": "s", "basis_refs": ["task://t"], "confidence_band": "high", "expires_at": "昨天"},
            "why_now_expires_at_invalid",
        ),
        ("not-a-dict", "why_now_not_object"),
    ],
)
def test_why_now_field_level_degrade_reasons(raw, reason_prefix):
    payload, reason = normalize_why_now(raw, now=_NOW)
    assert payload is None
    assert reason is not None and reason.startswith(reason_prefix)


def test_why_now_expired_not_reused_as_current_reason():
    payload, reason = normalize_why_now(
        {
            "statement": "上周的原因",
            "basis_refs": ["task://t"],
            "expires_at": _NOW - timedelta(minutes=1),
            "confidence_band": "high",
        },
        now=_NOW,
    )
    assert payload is None
    assert reason == "why_now_expired"  # §4：过期后不得当作当前原因复用


def test_why_now_degrade_leaves_rest_of_view_byte_identical():
    """§4.1 字段级降级：仅 why_now 置 null，视图其余字段不受影响。"""
    good, reason = normalize_why_now(
        {
            "statement": "s",
            "basis_refs": ["task://t"],
            "expires_at": None,
            "confidence_band": "low",
        },
        now=_NOW,
    )
    assert reason is None and good is not None
    with_good = _view(why_now=good)
    degraded, reason = normalize_why_now({"statement": "s", "basis_refs": []}, now=_NOW)
    assert degraded is None and reason is not None
    with_degraded = _view(why_now=None)
    assert with_good.pop("why_now") is not None
    assert with_degraded.pop("why_now") is None
    assert with_good == with_degraded


def test_confidence_band_vocabulary_frozen():
    assert {"high", "medium", "low", "unknown"} == WHY_NOW_CONFIDENCE_BANDS


# ---------------------------------------------------------------------------
# 过期 / epoch 陈旧判定（§5 freshness + §9 反例）
# ---------------------------------------------------------------------------


def test_stale_reason_none_when_fresh():
    view = _view()
    assert resume_view_stale_reason(view, now=_NOW + timedelta(minutes=29), current_memory_epoch=42) is None


def test_stale_reason_expires_at_passed():
    view = _view()
    assert (
        resume_view_stale_reason(view, now=_NOW + timedelta(minutes=30, seconds=1), current_memory_epoch=42)
        == "expires_at_passed"
    )


def test_stale_reason_memory_epoch_changed():
    view = _view()
    assert resume_view_stale_reason(view, now=_NOW, current_memory_epoch=43) == "memory_epoch_changed"


def test_stale_reason_on_garbled_view_fails_closed():
    assert resume_view_stale_reason({"expires_at": "not-a-date"}, now=_NOW) == "expires_at_passed"
    assert resume_view_stale_reason({"expires_at": None}, now=_NOW) == "expires_at_passed"
    assert resume_view_stale_reason("garbage", now=_NOW) == "expires_at_passed"  # 非视图 → 视为过期，不强行接续


# ---------------------------------------------------------------------------
# 降级词表封闭 + 装配输入 fail-loud
# ---------------------------------------------------------------------------


def test_degrade_reasons_vocabulary_frozen():
    assert {
        "object_not_found",
        "cross_object_access",
        "goal_unresolved",
        "goal_changed_requires_calibration",
        "context_receipt_missing",
    } == RESUME_DEGRADE_REASONS


def test_assemble_rejects_empty_ids_and_bad_epoch():
    with pytest.raises(ValueError, match="goal_ref"):
        _view(goal_id="")
    with pytest.raises(ValueError, match="task_ref"):
        _view(task_id="")
    with pytest.raises(ValueError, match="memory_epoch"):
        _view(memory_epoch=-1)
    with pytest.raises(ValueError, match="expires_at"):
        _view(expires_at=_NOW - timedelta(seconds=1))
    with pytest.raises(ValueError, match="outcome_id"):
        _view(last_outcome={"outcome_id": "", "truth_class": "actual", "recorded_at": _NOW})
    with pytest.raises(ValueError, match="description"):
        _view(pending_step={"description": "", "cognitive_ownership": "user_core", "execution_mode": "human"})
