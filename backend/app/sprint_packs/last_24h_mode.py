"""Helpers for detecting and applying exam sprint last-24h mode."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, date, datetime
from typing import Any

from app.sprint_packs.sprint_pack_loader import load_pack, query_nodes_by_priority

DEFAULT_LAST_24H_FORBIDDEN_ACTIONS = (
    "不学习全新的知识点",
    "不做耗时超过15分钟的单题",
    "不熬夜复习",
)

DEFAULT_LAST_24H_SUMMARY = "今天不再学新内容，只做高频速览、错题回看和 30 分钟短模拟。"
DEFAULT_LAST_24H_MOCK = {
    "duration_minutes": 30,
    "question_count": 8,
    "instruction": "做 6-8 题覆盖主要题型的压缩模拟，做完只归因，不再展开新章节。",
}


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _strip(value: Any) -> str:
    return str(value or "").strip()


def parse_exam_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(UTC)
        return value.date()
    if isinstance(value, date):
        return value
    text = _strip(value)
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def extract_exam_date(*sources: Any) -> date | None:
    for source in sources:
        if source in (None, "", [], {}):
            continue
        parsed = parse_exam_date(source)
        if parsed is not None:
            return parsed
        if isinstance(source, dict):
            for key in ("exam_date", "target_date"):
                parsed = parse_exam_date(source.get(key))
                if parsed is not None:
                    return parsed
            exam_urgency = source.get("exam_urgency")
            if isinstance(exam_urgency, dict):
                parsed = parse_exam_date(exam_urgency.get("exam_date") or exam_urgency.get("target_date"))
                if parsed is not None:
                    return parsed
    return None


def calculate_days_left(exam_date: date | None, *, now: datetime | None = None) -> int | None:
    if exam_date is None:
        return None
    current = now or _utcnow()
    return max((exam_date - current.date()).days, 0)


def is_last_24h_window(
    *,
    exam_date: date | None = None,
    days_left: int | None = None,
    now: datetime | None = None,
) -> bool:
    if exam_date is not None:
        current = now or _utcnow()
        exam_start = datetime.combine(exam_date, datetime.min.time(), tzinfo=UTC)
        if exam_start <= current:
            return True
        if (exam_start - current).total_seconds() <= 24 * 60 * 60:
            return True
    if days_left is not None and int(days_left) <= 1:
        return True
    return False


def _normalize_focus_nodes(pack: dict[str, Any], last_24h_strategy: dict[str, Any]) -> list[dict[str, Any]]:
    nodes_by_id = {_strip(node.get("node_id")): node for node in pack.get("knowledge_nodes", [])}
    focus_nodes: list[dict[str, Any]] = []

    for raw_item in list(last_24h_strategy.get("focus") or []):
        item = dict(raw_item) if isinstance(raw_item, dict) else {"node_id": raw_item}
        node_id = _strip(item.get("node_id"))
        if not node_id:
            continue
        node = dict(nodes_by_id.get(node_id) or {})
        focus_nodes.append(
            {
                "node_id": node_id,
                "label": _strip(item.get("label") or node.get("label") or node_id),
                "recommended_action": _strip(
                    item.get("recommended_action") or node.get("recommended_action") or "快速闭卷回忆核心判断点"
                ),
                "exam_weight": float(node.get("exam_weight", item.get("exam_weight") or 0.0)),
                "frequency": float(node.get("frequency", item.get("frequency") or 0.0)),
            }
        )

    if focus_nodes:
        return focus_nodes

    fallback = query_nodes_by_priority(pack, days_left=1, path_mode="minimum_pass")[:6]
    return [
        {
            "node_id": _strip(node.get("node_id")),
            "label": _strip(node.get("label") or node.get("node_id")),
            "recommended_action": _strip(node.get("recommended_action") or "快速闭卷回忆核心判断点"),
            "exam_weight": float(node.get("exam_weight", 0.0)),
            "frequency": float(node.get("frequency", 0.0)),
        }
        for node in fallback
        if _strip(node.get("node_id"))
    ]


def build_last_24h_strategy_payload(
    *,
    subject: str,
    exam_date: date | None,
    days_left: int | None,
) -> dict[str, Any]:
    pack = load_pack(subject)
    if not pack:
        return {
            "label": "考前24小时策略",
            "description": DEFAULT_LAST_24H_SUMMARY,
            "focus": [],
            "forbidden_actions": list(DEFAULT_LAST_24H_FORBIDDEN_ACTIONS),
            "mock_exam": dict(DEFAULT_LAST_24H_MOCK),
        }

    raw = deepcopy(dict(pack.get("last_24h_strategy") or {}))
    raw["focus"] = _normalize_focus_nodes(pack, raw)
    raw["forbidden_actions"] = list(raw.get("forbidden_actions") or DEFAULT_LAST_24H_FORBIDDEN_ACTIONS)
    raw["mock_exam"] = dict(raw.get("mock_exam") or DEFAULT_LAST_24H_MOCK)
    if exam_date is not None:
        raw["exam_date"] = exam_date.isoformat()
    if days_left is not None:
        raw["days_left"] = int(days_left)
    return raw


def apply_last_24h_policy_overrides(
    policy: dict[str, Any] | None,
    *,
    subject: str,
    exam_date: date | None,
    days_left: int | None,
) -> dict[str, Any]:
    updated = deepcopy(dict(policy or {}))
    last_24h_strategy = build_last_24h_strategy_payload(
        subject=subject,
        exam_date=exam_date,
        days_left=days_left,
    )

    retrieval_policy = dict(updated.get("retrieval_policy") or {})
    retrieval_policy.update(
        {
            "daily_retrieval_required": True,
            "default_task_shape": "high_yield_review_error_book_short_mock",
            "spaced_retrieval": "same_day_compact_refresh",
            "allow_deep_learn": False,
            "deep_learn_budget": "none",
            "output_gate": "every_block_requires_visible_output",
            "success_gate": "no_new_topics_visible_output_required",
            "density_mode": "final_day_compact",
            "max_primary_targets_per_day": 3,
            "minimum_output": "高频速览、错题回看或 30 分钟短模拟",
            "new_topic_allowed": False,
        }
    )

    strategy = dict(updated.get("strategy") or {})
    pedagogy = dict(strategy.get("pedagogy") or {})
    pedagogy.update(
        {
            "worked_example_first": True,
            "retrieval_practice": True,
            "spaced_review": True,
            "error_analysis_required": True,
            "new_topic_allowed": False,
        }
    )
    planning = dict(strategy.get("planning") or {})
    planning.update(
        {
            "continue_original_plan": False,
            "replan_scope": "today_only",
            "drop_low_roi_topics": True,
            "new_topic_allowed": False,
        }
    )
    strategy["pedagogy"] = pedagogy
    strategy["planning"] = planning

    standard_layer_contract = dict(updated.get("standard_layer_contract") or {})
    must_not_include = [
        _strip(item)
        for item in list(standard_layer_contract.get("must_not_include") or [])
        if _strip(item)
    ]
    if "new_chapter_introduction" not in must_not_include:
        must_not_include.append("new_chapter_introduction")
    standard_layer_contract["must_not_include"] = must_not_include
    standard_layer_contract.setdefault("response_type", "task_help")

    updated.update(
        {
            "sprint_mode": "last_24h_cram",
            "triage_level": "emergency",
            "days_left": int(days_left) if days_left is not None else updated.get("days_left"),
            "time_constraint_days": int(days_left) if days_left is not None else updated.get("time_constraint_days"),
            "exam_date": exam_date.isoformat() if exam_date is not None else updated.get("exam_date"),
            "last_24h_mode": True,
            "summary": DEFAULT_LAST_24H_SUMMARY,
            "headline": "今天不再学新内容",
            "focus": DEFAULT_LAST_24H_SUMMARY,
            "non_negotiables": list(last_24h_strategy.get("forbidden_actions") or DEFAULT_LAST_24H_FORBIDDEN_ACTIONS),
            "rules": list(last_24h_strategy.get("forbidden_actions") or DEFAULT_LAST_24H_FORBIDDEN_ACTIONS),
            "new_topic_allowed": False,
            "drop_low_roi_topics": True,
            "error_analysis_required": True,
            "retrieval_policy": retrieval_policy,
            "strategy": strategy,
            "standard_layer_contract": standard_layer_contract,
            "last_24h_strategy": last_24h_strategy,
        }
    )
    return updated
