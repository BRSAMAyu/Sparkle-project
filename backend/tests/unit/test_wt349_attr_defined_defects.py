"""wt349 mypy 烧减批 6 —— attr-defined 家族真缺陷修复的红测回归钉。

每个用例对应 REPORT「真缺陷雷达」一节的一项修复：在修复前这些用例
以 AttributeError / TypeError / ImportError 形式红，修复后转绿；
保留在库中防止同形缺陷回归。
"""

from __future__ import annotations

import inspect
from datetime import UTC, datetime, timedelta

from app.core.policy_patch import PolicyPatch, reorder_nominations
from app.services.node_sector_service import normalize_sector_weights


def test_normalize_sector_weights_accepts_dict_weights() -> None:
    """sector 权重 dict 分支曾把 dict_items 赋给 list 再 append（必 AttributeError）。"""
    raw = {"TECH": 40, "WISDOM": 60}
    parsed = normalize_sector_weights(raw)
    # 归一化输出：占比四舍五入成 int 百分比；两个板块都在场即代表 dict 分支走通
    assert isinstance(parsed, dict)
    assert set(parsed) == {"TECH", "WISDOM"}
    assert sum(parsed.values()) == 100


def test_normalize_sector_weights_accepts_list_payloads() -> None:
    raw = [{"sector": "tech", "weight": 30}, {"name": "wisdom", "value": 70}]
    parsed = normalize_sector_weights(raw)
    assert set(parsed) == {"TECH", "WISDOM"}
    assert sum(parsed.values()) == 100


def test_planning_intent_type_tolerates_non_dict_constraints() -> None:
    """_planning_constraints 是松散键：非 dict 值此前 `(x or {}).get` 崩溃路径。"""
    from app.agents.graph.nodes.collaboration import _planning_intent_type

    state = {
        "messages": [],
        "user_id": "u",
        "session_id": "s",
        "user_profile": None,
        "current_plan": None,
        "planning_status": None,
        "intent_data": None,
        "collaboration_agents": None,
        "collaboration_order": None,
        "collaboration_index": None,
        "mode_name": "exam_sprint",
        "mode_constraints": None,
        "synthesis_policy": None,
        "review_feedback": None,
        "require_approval": False,
        "approval_context": None,
        "approval_result": None,
        "error": None,
        "review_context": None,
        "review_history": None,
        "enable_deep_review": False,
        "review_config": None,
    }
    # route_intent 缺失 → 回落 mode_name
    assert _planning_intent_type(state) == "exam_sprint"
    # 非 dict 约束（脏数据）→ 与缺失同路径，不抛 AttributeError
    dirty = dict(state)
    dirty["_planning_constraints"] = "garbage"
    assert _planning_intent_type(dirty) == "exam_sprint"
    # dict 约束带 route_intent → 直接采用
    with_route = dict(state)
    with_route["_planning_constraints"] = {"route_intent": "error_repair"}
    assert _planning_intent_type(with_route) == "error_repair"


def test_route_intent_helper_matches_collaboration_semantics() -> None:
    """graph 节点统一的 `_route_intent_from_constraints`：dict/缺失/脏值三态。"""
    from app.agents.graph.nodes.time_tutor import _route_intent_from_constraints

    assert _route_intent_from_constraints({"_planning_constraints": {"route_intent": "drill"}}) == "drill"
    assert _route_intent_from_constraints({}) is None
    assert _route_intent_from_constraints({"_planning_constraints": "garbage"}) is None


def test_stt_provider_transcribe_stream_contract_is_async_generator() -> None:
    """ABC 曾以协程式声明（体内无 yield）——调用方 `async for` 其返回值。"""
    from app.services.stt.providers.base import STTProvider

    assert inspect.isasyncgenfunction(STTProvider.transcribe_stream)


def test_get_db_is_async_generator() -> None:
    """get_db/get_db_no_commit 体内 yield（async-gen），原注解谎言致
    `db = await db_gen.__anext__()` 报 AsyncSession 无 __anext__。"""
    from app.db.session import get_db, get_db_no_commit

    assert inspect.isasyncgenfunction(get_db)
    assert inspect.isasyncgenfunction(get_db_no_commit)


def test_document_quality_metrics_are_registered() -> None:
    """DOC_* 五个指标此前从未注册 → document_service 上报恒 ImportError 被吞。"""
    import app.core.metrics as metrics

    for name in (
        "DOC_QUALITY_CHECK_COUNT",
        "DOC_QUALITY_SCORE",
        "DOC_GARBLED_RATIO",
        "DOC_OCR_CONFIDENCE",
        "DOC_QUALITY_ISSUES",
    ):
        assert hasattr(metrics, name), name


def test_policy_patch_evidence_refs_are_growable_lists() -> None:
    """evidence 收集期声明 tuple 却 append（首次正/负关联证据必 AttributeError）。"""
    now = datetime.now(UTC)

    def make_record(intervention: str, *, positive: bool) -> object:
        class _Rec:
            pass

        rec = _Rec()
        rec.intervention = intervention
        rec.has_positive_association_evidence = positive
        rec.has_negative_association_evidence = not positive
        rec.evidence_count = 2
        rec.record_id = f"rec-{intervention}-{positive}"
        return rec

    patch = PolicyPatch(
        patch_id="p1",
        user_id="u1",
        surface="intervention_preference",
        payload={"intervention": "spaced_review", "direction": "prefer"},
        state="active",
        created_at=now - timedelta(days=1),
    )

    outcome = reorder_nominations(
        ["spaced_review", "mock_exam", "rest_day"],
        [patch],
        now=now,
        evidence_records=[make_record("spaced_review", positive=True)],
    )
    # prefer 方向 + 真实正向证据 → 该干预被移到序首（此路径此前必 AttributeError）
    assert outcome.nominated[0] == "spaced_review"
    assert outcome.moves and outcome.moves[0].evidence_refs


def test_purge_task_no_longer_references_nonexistent_streak_model() -> None:
    """UserStreakDays 笔误使 GDPR 硬删除任务 import 恒败——回归钉：源码中
    不允许再出现不存在的模型名，且真实模型名可导入。"""
    import inspect as _inspect

    import app.core.celery_tasks as tasks
    from app.models import achievement as achievement_models

    assert hasattr(achievement_models, "UserStreakDay")
    assert not hasattr(achievement_models, "UserStreakDays")
    src = _inspect.getsource(tasks.purge_deleted_account)
    assert "UserStreakDays" not in src
