from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import Text, and_, cast, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent_persona import build_agent_persona
from app.core.agent_profiles import AgentRole, agent_profile_registry
from app.models.galaxy import KnowledgeNode, UserNodeStatus


async def generate_participants(
    *,
    scenario_key: str,
    participant_names: list[str],
    user_context: dict[str, Any] | None,
    anchor_material: str | None = None,
    anchor_type: str | None = None,
    db: AsyncSession | None = None,
    user_id: UUID | None = None,
    topic: str | None = None,
    participants_from: str | None = None,
) -> list[dict[str, Any]]:
    profile = agent_profile_registry.get_profile(AgentRole.STUDY_BUDDY)
    resolved_names = list(participant_names)
    knowledge_context: list[dict[str, str]] = []

    if participants_from == "knowledge_graph" and db and user_id and topic:
        knowledge_context = await _fetch_graph_participants(
            db=db,
            user_id=user_id,
            topic=topic,
            limit=len(participant_names) or 3,
            prefer_scholars=scenario_key == "historical_roleplay",
        )
        if knowledge_context:
            resolved_names = [item["name"] for item in knowledge_context]

    participants: list[dict[str, Any]] = []
    for index, name in enumerate(resolved_names):
        graph_hint = knowledge_context[index] if index < len(knowledge_context) else None
        persona = build_agent_persona(
            agent_role=AgentRole.STUDY_BUDDY,
            user_context={
                **(user_context or {}),
                "participant_name": name,
                "scenario_key": scenario_key,
                "graph_anchor": graph_hint or {},
            },
            profile=profile,
        )
        participants.append(
            {
                "name": name,
                "role_hint": _resolve_role_hint(
                    scenario_key=scenario_key,
                    fallback_name=participant_names[min(index, len(participant_names) - 1)] if participant_names else name,
                    graph_hint=graph_hint,
                ),
                "persona": persona.to_dict(),
                "stance": _resolve_stance(
                    scenario_key,
                    index,
                    anchor_type=anchor_type,
                ),
                "source": "knowledge_graph" if graph_hint else "template",
                "source_node_name": (graph_hint or {}).get("name"),
                "context_anchor": _resolve_context_anchor(
                    graph_hint=graph_hint,
                    anchor_material=anchor_material,
                ),
                "strategy": _resolve_strategy(
                    scenario_key=scenario_key,
                    participant_index=index,
                    anchor_type=anchor_type,
                ),
            }
        )
    return participants


async def _fetch_graph_participants(
    *,
    db: AsyncSession,
    user_id: UUID,
    topic: str,
    limit: int,
    prefer_scholars: bool,
) -> list[dict[str, str]]:
    topic_lower = topic.strip().lower()
    if not topic_lower:
        return []

    stmt = (
        select(
            KnowledgeNode.name,
            KnowledgeNode.description,
            KnowledgeNode.keywords,
            KnowledgeNode.importance_level,
            UserNodeStatus.mastery_score,
        )
        .outerjoin(
            UserNodeStatus,
            and_(
                UserNodeStatus.node_id == KnowledgeNode.id,
                UserNodeStatus.user_id == user_id,
            ),
        )
        .where(
            or_(
                func.lower(KnowledgeNode.name).contains(topic_lower),
                func.lower(func.coalesce(KnowledgeNode.description, "")).contains(topic_lower),
                cast(KnowledgeNode.keywords, Text).ilike(f"%{topic_lower}%"),
            )
        )
        .order_by(
            desc(func.coalesce(UserNodeStatus.mastery_score, 0.0)),
            desc(KnowledgeNode.importance_level),
            KnowledgeNode.created_at.desc(),
        )
        .limit(max(limit * 4, 6))
    )
    rows = (await db.execute(stmt)).all()
    candidates = _normalize_graph_candidates(rows, prefer_scholars=prefer_scholars)

    if not candidates and prefer_scholars:
        fallback_stmt = (
            select(
                KnowledgeNode.name,
                KnowledgeNode.description,
                KnowledgeNode.keywords,
                KnowledgeNode.importance_level,
                UserNodeStatus.mastery_score,
            )
            .outerjoin(
                UserNodeStatus,
                and_(
                    UserNodeStatus.node_id == KnowledgeNode.id,
                    UserNodeStatus.user_id == user_id,
                ),
            )
            .where(cast(KnowledgeNode.keywords, Text).ilike("%node_type:scholar%"))
            .order_by(
                desc(func.coalesce(UserNodeStatus.mastery_score, 0.0)),
                desc(KnowledgeNode.importance_level),
                KnowledgeNode.created_at.desc(),
            )
            .limit(max(limit * 2, 4))
        )
        fallback_rows = (await db.execute(fallback_stmt)).all()
        candidates = _normalize_graph_candidates(fallback_rows, prefer_scholars=True)

    return candidates[:limit]


def _normalize_graph_candidates(
    rows: list[tuple[str, str | None, list[str] | None, int | None, float | None]],
    *,
    prefer_scholars: bool,
) -> list[dict[str, str]]:
    preferred: list[dict[str, str]] = []
    general: list[dict[str, str]] = []
    seen: set[str] = set()

    for name, description, keywords, _importance, _mastery in rows:
        normalized_name = str(name or "").strip()
        if not normalized_name or normalized_name in seen:
            continue
        seen.add(normalized_name)
        item = {
            "name": normalized_name,
            "description": str(description or "").strip(),
        }
        keyword_list = [str(keyword).strip().lower() for keyword in list(keywords or []) if str(keyword).strip()]
        if "node_type:scholar" in keyword_list:
            preferred.append(item)
        else:
            general.append(item)

    if prefer_scholars:
        return preferred + general
    return general + preferred


def _resolve_role_hint(
    *,
    scenario_key: str,
    fallback_name: str,
    graph_hint: dict[str, str] | None,
) -> str:
    if graph_hint and graph_hint.get("description"):
        return graph_hint["description"][:80]
    if scenario_key == "historical_roleplay":
        return f"{fallback_name} 视角"
    return fallback_name


def _resolve_stance(
    scenario_key: str,
    index: int,
    *,
    anchor_type: str | None = None,
) -> str:
    strategy = _resolve_strategy(
        scenario_key=scenario_key,
        participant_index=index,
        anchor_type=anchor_type,
    )
    if strategy in {"using_misconception", "challenging", "opposing_perspective"}:
        return "challenging"
    if strategy in {"synthesizing", "moderating", "probing_depth"}:
        return "probing"
    if scenario_key == "knowledge_debate":
        return ["supporting", "opposing", "moderating"][min(index, 2)]
    if scenario_key == "historical_roleplay":
        return ["immersive", "contextual", "reflective"][min(index, 2)]
    if scenario_key == "socratic_dialogue":
        return "probing"
    return "probing" if index == 0 else ("supportive" if index % 2 else "challenging")


def _resolve_strategy(
    *,
    scenario_key: str,
    participant_index: int,
    anchor_type: str | None,
) -> str:
    if anchor_type == "error_record":
        strategies = ["explaining_correct", "using_misconception", "probing_depth"]
    elif anchor_type == "concept":
        strategies = ["illustrating", "challenging", "connecting"]
    elif anchor_type == "historical_source":
        strategies = ["contextualizing", "opposing_perspective", "modern_parallel"]
    else:
        if scenario_key == "error_diagnosis":
            strategies = ["explaining_correct", "using_misconception", "probing_depth"]
        elif scenario_key == "historical_roleplay":
            strategies = ["contextualizing", "opposing_perspective", "modern_parallel"]
        else:
            strategies = ["supporting", "challenging", "synthesizing"]
    return strategies[min(participant_index, len(strategies) - 1)]


def _resolve_context_anchor(
    *,
    graph_hint: dict[str, str] | None,
    anchor_material: str | None,
) -> str | None:
    graph_anchor = str((graph_hint or {}).get("description") or "").strip()
    explicit_anchor = str(anchor_material or "").strip()
    if graph_anchor and explicit_anchor:
        return f"{explicit_anchor}\n\n补充背景：{graph_anchor}"
    if explicit_anchor:
        return explicit_anchor
    return graph_anchor or None
