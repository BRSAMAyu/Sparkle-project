"""Unified experience packets for the vertical goal-realization loop.

These packets intentionally aggregate existing Sparkle systems instead of
creating another state store. They give Aurora, planning, RAG, memory, graph,
cards, and UI receipts one compact per-turn contract.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

MemoryClaimKind = Literal["confirmed", "inferred", "temporary", "correction_derived"]


def _clean_str(value: Any) -> str:
    return str(value or "").strip()


def _compact_dict(data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if value not in (None, "", [], {})}


def _compact_list(values: Any, limit: int = 5) -> list[Any]:
    if not isinstance(values, list | tuple):
        return []
    result: list[Any] = []
    for item in values:
        if item in (None, "", [], {}):
            continue
        result.append(item)
        if len(result) >= limit:
            break
    return result


@dataclass(frozen=True)
class AuroraExperiencePacket:
    current_read: str
    confidence: float
    uncertainty_level: str
    evidence: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    recent_corrections: list[dict[str, Any]] = field(default_factory=list)
    next_tone: str = "grounded_support"
    next_strategy: str = "goal_realization"
    user_visible_hint: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _compact_dict(asdict(self))


@dataclass(frozen=True)
class KnowledgeSourceReceipt:
    context_plan_mode: str
    answer_basis: str
    loaded_sources: list[dict[str, Any]] = field(default_factory=list)
    skipped_sources: list[dict[str, Any]] = field(default_factory=list)
    excluded_sources: list[dict[str, Any]] = field(default_factory=list)
    source_uncertainty: str = ""
    correction_hint: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _compact_dict(asdict(self))


@dataclass(frozen=True)
class GraphDecisionTrace:
    decision_scope: str
    graph_state: str
    weak_nodes: list[dict[str, Any]] = field(default_factory=list)
    prerequisite_blockers: list[dict[str, Any]] = field(default_factory=list)
    recommended_nodes: list[dict[str, Any]] = field(default_factory=list)
    affects: list[str] = field(default_factory=list)
    trace_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _compact_dict(asdict(self))


@dataclass(frozen=True)
class GoalRealizationContext:
    active_goal: dict[str, Any] | None
    plan_health: dict[str, Any]
    next_actions: list[dict[str, Any]]
    memory_claims: list[dict[str, Any]]
    context_plan: dict[str, Any]
    aurora: dict[str, Any]
    source_receipt: dict[str, Any]
    graph_trace: dict[str, Any]
    card_protocol: dict[str, Any]
    user_visible_summary: str

    def to_dict(self) -> dict[str, Any]:
        return _compact_dict(asdict(self))


def _memory_claim_kind(item: dict[str, Any]) -> MemoryClaimKind:
    if bool(item.get("correction_count")):
        return "correction_derived"
    if bool(item.get("user_confirmed")):
        return "confirmed"
    if _clean_str(item.get("source_lane")) == "inferred_extraction":
        return "inferred"
    return "temporary"


def _build_memory_claims(user_context_payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw_items: list[Any] = []
    raw_items.extend(_compact_list(user_context_payload.get("episodic_memories"), limit=4))
    raw_items.extend(_compact_list(user_context_payload.get("past_session_memory"), limit=2))
    cognitive = user_context_payload.get("cognitive_context")
    if isinstance(cognitive, dict):
        raw_items.extend(_compact_list(cognitive.get("episodic_memories"), limit=3))

    claims: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        summary = _clean_str(item.get("summary") or item.get("text") or item.get("title"))
        if not summary or summary in seen:
            continue
        seen.add(summary)
        claims.append(
            _compact_dict(
                {
                    "id": _clean_str(item.get("id")),
                    "summary": summary,
                    "kind": _memory_claim_kind(item),
                    "confidence": item.get("confidence") or item.get("evidence_score"),
                    "correction_count": item.get("correction_count"),
                    "can_correct": True,
                }
            )
        )
        if len(claims) >= 5:
            break
    return claims


def _build_aurora_packet(user_context_payload: dict[str, Any]) -> AuroraExperiencePacket:
    cognitive = user_context_payload.get("cognitive_context")
    presence = user_context_payload.get("aurora_everyday_presence")
    if not isinstance(presence, dict) and isinstance(cognitive, dict):
        presence = cognitive.get("aurora_everyday_presence")
    presence = presence if isinstance(presence, dict) else {}

    recent_corrections = _compact_list(
        user_context_payload.get("recent_corrections")
        or (cognitive.get("recent_corrections") if isinstance(cognitive, dict) else []),
        limit=3,
    )
    uncertainty = _clean_str(presence.get("uncertainty_level")) or "medium"
    confidence = {"low": 0.72, "medium": 0.58, "high": 0.42}.get(uncertainty, 0.55)
    current_read = _clean_str(presence.get("summary") or presence.get("chat_hint"))
    if not current_read:
        current_read = "我会先按当前目标、最近记忆和知识图谱状态来帮你推进。"

    open_questions: list[str] = []
    if uncertainty in {"medium", "high"}:
        open_questions.append("我现在的判断是否抓住了真正卡点？")
    next_step = _clean_str(presence.get("next_step_suggestion"))
    if next_step:
        open_questions.append(f"下一步是否先做：{next_step}")

    return AuroraExperiencePacket(
        current_read=current_read,
        confidence=confidence,
        uncertainty_level=uncertainty,
        evidence=[_clean_str(item) for item in _compact_list(presence.get("evidence_chain"), limit=4)],
        open_questions=open_questions[:3],
        recent_corrections=[item for item in recent_corrections if isinstance(item, dict)],
        next_tone="humble_confirming" if uncertainty == "high" else "grounded_support",
        next_strategy="diagnose_before_advice" if uncertainty == "high" else "goal_realization",
        user_visible_hint=_clean_str(presence.get("chat_hint") or current_read),
    )


def _build_source_receipt(user_context_payload: dict[str, Any], state_context: dict[str, Any]) -> KnowledgeSourceReceipt:
    context_plan = state_context.get("context_plan") or user_context_payload.get("context_plan") or {}
    if not isinstance(context_plan, dict):
        context_plan = {}
    retrieval = (
        state_context.get("document_context_retrieval")
        or user_context_payload.get("document_context_retrieval")
        or {}
    )
    receipt = retrieval.get("context_receipt") if isinstance(retrieval, dict) else None
    receipt = receipt if isinstance(receipt, dict) else state_context.get("context_receipt")
    receipt = receipt if isinstance(receipt, dict) else {}

    loaded = receipt.get("loaded") or receipt.get("used") or []
    skipped = receipt.get("skipped") or []
    excluded = receipt.get("excluded") or receipt.get("excluded_names") or []
    mode = _clean_str(context_plan.get("retrieval_mode") or retrieval.get("mode")) or "no_retrieval"
    answer_basis = _clean_str(receipt.get("answer_basis")) or ("source_grounded" if loaded else "general_reasoning")

    return KnowledgeSourceReceipt(
        context_plan_mode=mode,
        answer_basis=answer_basis,
        loaded_sources=[item for item in _compact_list(loaded, limit=5) if isinstance(item, dict)],
        skipped_sources=[item for item in _compact_list(skipped, limit=5) if isinstance(item, dict)],
        excluded_sources=[
            item if isinstance(item, dict) else {"title": _clean_str(item), "reason": "excluded"}
            for item in _compact_list(excluded, limit=5)
        ],
        source_uncertainty=_clean_str(receipt.get("source_uncertainty")),
        correction_hint=_clean_str(receipt.get("correction_hint") or receipt.get("reason_for_user")),
    )


def _build_graph_trace(user_context_payload: dict[str, Any], state_context: dict[str, Any]) -> GraphDecisionTrace:
    learning_gaps = user_context_payload.get("learning_gaps_summary")
    learning_gaps = learning_gaps if isinstance(learning_gaps, dict) else {}
    weak_nodes = _compact_list(
        learning_gaps.get("weak_nodes") or learning_gaps.get("top_gaps") or learning_gaps.get("bottlenecks"),
        limit=5,
    )
    recommended = _compact_list(
        learning_gaps.get("recommended_nodes") or learning_gaps.get("next_nodes") or learning_gaps.get("focus_nodes"),
        limit=5,
    )
    retrieval = state_context.get("document_context_retrieval") or user_context_payload.get("document_context_retrieval")
    entities = retrieval.get("entities") if isinstance(retrieval, dict) else []
    affects = ["next_task", "rag_scope", "plan_feasibility", "aurora_read"]
    trace_reason = "图谱会影响下一步任务、资料检索范围、计划可行性和 Aurora 当前判断。"
    if entities:
        trace_reason = f"本轮资料检索识别到 {len(entities)} 个图谱实体，已纳入目标实现判断。"

    return GraphDecisionTrace(
        decision_scope="goal_realization_turn",
        graph_state="active" if weak_nodes or recommended or entities else "available",
        weak_nodes=[item for item in weak_nodes if isinstance(item, dict)],
        recommended_nodes=[item for item in recommended if isinstance(item, dict)],
        affects=affects,
        trace_reason=trace_reason,
    )


def build_goal_realization_context(
    *,
    user_context_payload: dict[str, Any] | None,
    state_context: dict[str, Any] | None,
) -> GoalRealizationContext | None:
    if not isinstance(user_context_payload, dict):
        return None
    state_context = state_context if isinstance(state_context, dict) else {}

    active_goals = _compact_list(user_context_payload.get("active_goals"), limit=3)
    active_goal = active_goals[0] if active_goals and isinstance(active_goals[0], dict) else None
    next_actions = [item for item in _compact_list(user_context_payload.get("next_actions"), limit=5) if isinstance(item, dict)]
    plan_health = _compact_dict(
        {
            "active_plan_count": len(_compact_list(user_context_payload.get("active_plans"), limit=10)),
            "has_next_action": bool(next_actions),
            "document_context_loaded": bool(user_context_payload.get("document_context")),
        }
    )

    aurora = _build_aurora_packet(user_context_payload).to_dict()
    source_receipt = _build_source_receipt(user_context_payload, state_context).to_dict()
    graph_trace = _build_graph_trace(user_context_payload, state_context).to_dict()
    memory_claims = _build_memory_claims(user_context_payload)
    context_plan = state_context.get("context_plan") or user_context_payload.get("context_plan") or {}
    context_plan = context_plan if isinstance(context_plan, dict) else {}

    goal_title = _clean_str((active_goal or {}).get("title") or (active_goal or {}).get("name"))
    summary_parts = []
    if goal_title:
        summary_parts.append(f"当前目标：{goal_title}")
    if aurora.get("current_read"):
        summary_parts.append(f"Aurora 判断：{aurora['current_read']}")
    if source_receipt.get("answer_basis") == "source_grounded":
        summary_parts.append("本轮回答会优先使用已选资料并给出来源。")
    if graph_trace.get("graph_state") == "active":
        summary_parts.append("知识图谱会参与下一步选择。")
    user_visible_summary = "；".join(summary_parts) or "Sparkle 会把目标、记忆、资料和知识图谱合在一起推进这一轮。"

    return GoalRealizationContext(
        active_goal=active_goal,
        plan_health=plan_health,
        next_actions=next_actions,
        memory_claims=memory_claims,
        context_plan=context_plan,
        aurora=aurora,
        source_receipt=source_receipt,
        graph_trace=graph_trace,
        card_protocol={
            "canonical": True,
            "required_types": [
                "plan",
                "task",
                "knowledge_node",
                "source_document",
                "review",
                "vocabulary",
                "shared_resource",
            ],
        },
        user_visible_summary=user_visible_summary,
    )


def attach_goal_realization_context(
    *,
    user_context_payload: dict[str, Any] | None,
    state_context: dict[str, Any] | None,
) -> dict[str, Any] | None:
    packet = build_goal_realization_context(
        user_context_payload=user_context_payload,
        state_context=state_context,
    )
    if packet is None or not isinstance(user_context_payload, dict):
        return user_context_payload

    payload = packet.to_dict()
    user_context_payload["goal_realization_context"] = payload
    user_context_payload["aurora_experience_packet"] = payload.get("aurora")
    user_context_payload["knowledge_source_receipt"] = payload.get("source_receipt")
    user_context_payload["graph_decision_trace"] = payload.get("graph_trace")
    if isinstance(state_context, dict):
        state_context["goal_realization_context"] = payload
        state_context["aurora_experience_packet"] = payload.get("aurora")
        state_context["knowledge_source_receipt"] = payload.get("source_receipt")
        state_context["graph_decision_trace"] = payload.get("graph_trace")
    return user_context_payload
