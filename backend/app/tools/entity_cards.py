from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

ENTITY_CARD_SCHEMA_VERSION = "v1"
REQUIRED_ENTITY_CARD_FIELDS = {"schema_version", "entity_type", "title"}
ACTION_TYPES_REQUIRING_ROUTE = {"open_detail", "continue_chat"}


def _compact_dict(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None and value != [] and value != {}}


def build_entity_action(
    *,
    action_id: str,
    action_type: str,
    label: str,
    route: str | None = None,
    style: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _compact_dict(
        {
            "id": action_id,
            "type": action_type,
            "label": label,
            "route": route,
            "style": style,
            "payload": payload,
        }
    )


def validate_entity_card(entity_card: dict[str, Any]) -> list[str]:
    """Return schema/action issues that would make a card inert in clients."""

    issues: list[str] = []
    for field in sorted(REQUIRED_ENTITY_CARD_FIELDS):
        if not str(entity_card.get(field) or "").strip():
            issues.append(f"missing_{field}")

    entity_type = str(entity_card.get("entity_type") or "").strip()
    entity_id = str(entity_card.get("entity_id") or "").strip()
    if not entity_type:
        return issues

    if entity_type not in {"task_list", "learning_path", "prediction"} and not entity_id:
        issues.append("missing_entity_id")

    primary_action = entity_card.get("primary_action")
    if not isinstance(primary_action, dict):
        issues.append("missing_primary_action")
    else:
        action_type = str(primary_action.get("type") or "").strip()
        route = str(primary_action.get("route") or "").strip()
        if not str(primary_action.get("label") or "").strip():
            issues.append("missing_primary_action_label")
        if action_type in ACTION_TYPES_REQUIRING_ROUTE and not route:
            issues.append("missing_primary_action_route")
        if route and not route.startswith("/"):
            issues.append("invalid_primary_action_route")

    share = entity_card.get("share")
    if share is not None:
        if not isinstance(share, dict):
            issues.append("invalid_share_payload")
        elif not str(share.get("resource_type") or "").strip() or not str(share.get("resource_id") or "").strip():
            issues.append("incomplete_share_payload")

    for index, action in enumerate(entity_card.get("secondary_actions") or []):
        if not isinstance(action, dict):
            issues.append(f"invalid_secondary_action_{index}")
            continue
        if not str(action.get("label") or "").strip():
            issues.append(f"missing_secondary_action_label_{index}")

    return issues


def build_share_payload(
    *,
    resource_type: str,
    resource_id: str,
    title: str,
    subtitle: str | None = None,
    meta: dict[str, Any] | None = None,
    owner: dict[str, Any] | None = None,
    visibility: str | None = None,
    preview: dict[str, Any] | None = None,
    source_receipt: dict[str, Any] | None = None,
    adoption_action: dict[str, Any] | None = None,
    expires_at: str | None = None,
    revoked_at: str | None = None,
    availability: str | None = None,
) -> dict[str, Any]:
    return _compact_dict(
        {
            "resource_type": resource_type,
            "resource_id": resource_id,
            "title": title,
            "subtitle": subtitle,
            "meta": meta,
            "owner": owner,
            "visibility": visibility,
            "preview": preview,
            "source_receipt": source_receipt,
            "adoption_action": adoption_action,
            "expires_at": expires_at,
            "revoked_at": revoked_at,
            "availability": availability,
        }
    )


def build_feedback_payload(
    *,
    tool_result_id: str | None,
    confirmation_required: bool = False,
    can_confirm_all: bool = False,
) -> dict[str, Any] | None:
    if not tool_result_id:
        return None
    return _compact_dict(
        {
            "tool_result_id": tool_result_id,
            "confirmation_required": confirmation_required,
            "can_confirm_all": can_confirm_all,
        }
    )


def build_entity_card(
    *,
    entity_type: str,
    entity_id: str | None,
    title: str,
    summary: str | None = None,
    status: str | None = None,
    execution_state: str | None = None,
    source: dict[str, Any] | None = None,
    primary_action: dict[str, Any] | None = None,
    secondary_actions: list[dict[str, Any]] | None = None,
    share: dict[str, Any] | None = None,
    feedback: dict[str, Any] | None = None,
    linked_entities: dict[str, Any] | None = None,
    metrics: dict[str, Any] | None = None,
    tags: list[str] | None = None,
    children: list[dict[str, Any]] | None = None,
    raw: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _compact_dict(
        {
            "schema_version": ENTITY_CARD_SCHEMA_VERSION,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "title": title,
            "summary": summary,
            "status": status,
            "execution_state": execution_state,
            "source": source,
            "primary_action": primary_action,
            "secondary_actions": secondary_actions,
            "share": share,
            "feedback": feedback,
            "linked_entities": linked_entities,
            "metrics": metrics,
            "tags": tags,
            "children": children,
            "raw": raw,
        }
    )


def wrap_widget_payload(
    *,
    widget_type: str,
    widget_data: dict[str, Any],
    entity_card: dict[str, Any],
) -> dict[str, Any]:
    return {
        **widget_data,
        "entity_card": entity_card,
        "entity_type": entity_card.get("entity_type"),
    }


def build_task_entity_card(
    task: dict[str, Any],
    *,
    tool_name: str,
    tool_result_id: str | None = None,
    source_channel: str = "ai_tool",
) -> dict[str, Any]:
    task_id = str(task.get("id")) if task.get("id") is not None else None
    title = task.get("title") or "未命名任务"
    guide_content = task.get("guide_content") or task.get("description")
    plan_id = task.get("plan_id")
    return build_entity_card(
        entity_type="task",
        entity_id=task_id,
        title=title,
        summary=guide_content,
        status=task.get("status"),
        execution_state="confirmed" if task.get("status") in {"IN_PROGRESS", "COMPLETED"} else "draft",
        source=_compact_dict(
            {
                "channel": source_channel,
                "tool_name": tool_name,
            }
        ),
        primary_action=build_entity_action(
            action_id="open_task",
            action_type="open_detail",
            label="查看任务",
            route=f"/tasks/{task_id}" if task_id else None,
        ),
        secondary_actions=(
            [
                build_entity_action(
                    action_id="share_task",
                    action_type="share_resource",
                    label="分享卡片",
                    payload={"resource_type": "task", "resource_id": task_id},
                )
            ]
            if task_id
            else None
        ),
        share=(
            build_share_payload(
                resource_type="task",
                resource_id=task_id,
                title=title,
                subtitle=guide_content,
            )
            if task_id
            else None
        ),
        feedback=build_feedback_payload(
            tool_result_id=tool_result_id,
            confirmation_required=bool(tool_result_id),
        ),
        linked_entities=_compact_dict({"plan_id": str(plan_id) if plan_id else None}),
        metrics=_compact_dict(
            {
                "estimated_minutes": task.get("estimated_minutes"),
                "priority": task.get("priority"),
                "difficulty": task.get("difficulty"),
            }
        ),
        tags=[str(tag) for tag in task.get("tags", [])] if isinstance(task.get("tags"), list) else None,
        raw=task,
    )


def build_plan_entity_card(
    plan: dict[str, Any],
    *,
    tool_name: str,
    tool_result_id: str | None = None,
    source_channel: str = "ai_tool",
) -> dict[str, Any]:
    plan_id = str(plan.get("id") or plan.get("plan_id")) if (plan.get("id") or plan.get("plan_id")) else None
    title = plan.get("title") or plan.get("name") or "未命名计划"
    description = plan.get("description")
    return build_entity_card(
        entity_type="plan",
        entity_id=plan_id,
        title=title,
        summary=description,
        status=plan.get("type") or plan.get("plan_type"),
        execution_state="active" if plan.get("is_active", True) else "draft",
        source=_compact_dict({"channel": source_channel, "tool_name": tool_name}),
        primary_action=build_entity_action(
            action_id="open_plan",
            action_type="open_detail",
            label="查看计划",
            route=f"/plans/{plan_id}" if plan_id else None,
        ),
        secondary_actions=(
            [
                build_entity_action(
                    action_id="share_plan",
                    action_type="share_resource",
                    label="分享计划",
                    payload={"resource_type": "plan", "resource_id": plan_id},
                )
            ]
            if plan_id
            else None
        ),
        share=(
            build_share_payload(
                resource_type="plan",
                resource_id=plan_id,
                title=title,
                subtitle=description,
            )
            if plan_id
            else None
        ),
        feedback=build_feedback_payload(tool_result_id=tool_result_id),
        linked_entities=_compact_dict(
            {
                "subject": plan.get("subject"),
                "source": plan.get("source"),
            }
        ),
        metrics=_compact_dict(
            {
                "progress": plan.get("progress"),
                "task_count": plan.get("task_count"),
                "target_mastery": plan.get("target_mastery"),
            }
        ),
        raw=plan,
    )


def build_task_list_entity_card(
    tasks: list[dict[str, Any]],
    *,
    tool_name: str,
    tool_result_id: str | None = None,
    plan_id: str | None = None,
    plan_title: str | None = None,
    source_channel: str = "ai_tool",
    rag_quality: str | None = None,
) -> dict[str, Any]:
    children = [
        build_task_entity_card(
            task,
            tool_name=tool_name,
            tool_result_id=tool_result_id,
            source_channel=source_channel,
        )
        for task in tasks
    ]
    title = plan_title or f"{len(tasks)} 个可执行任务"
    return build_entity_card(
        entity_type="task_list",
        entity_id=tool_result_id,
        title=title,
        summary="AI 已将建议整理成可执行任务列表",
        status="batch",
        execution_state="draft",
        source=_compact_dict({"channel": source_channel, "tool_name": tool_name}),
        primary_action=(
            build_entity_action(
                action_id="open_plan",
                action_type="open_detail",
                label="查看计划",
                route=f"/plans/{plan_id}" if plan_id else None,
            )
            if plan_id
            else build_entity_action(
                action_id="open_tasks",
                action_type="open_detail",
                label="查看任务",
                route="/tasks",
            )
        ),
        secondary_actions=(
            [
                build_entity_action(
                    action_id="share_plan",
                    action_type="share_resource",
                    label="分享计划",
                    payload={"resource_type": "plan", "resource_id": plan_id},
                )
            ]
            if plan_id
            else None
        ),
        share=(
            build_share_payload(
                resource_type="plan" if plan_id else "task",
                resource_id=plan_id or str(tasks[0].get("id")) if tasks else "",
                title=title,
                subtitle=f"包含 {len(tasks)} 个可执行任务",
                meta=_compact_dict({"plan_title": plan_title, "rag_quality": rag_quality}),
            )
            if tasks
            else None
        ),
        feedback=build_feedback_payload(
            tool_result_id=tool_result_id,
            confirmation_required=bool(tool_result_id),
            can_confirm_all=bool(tool_result_id),
        ),
        linked_entities=_compact_dict({"plan_id": plan_id, "plan_title": plan_title}),
        metrics=_compact_dict({"task_count": len(tasks), "rag_quality": rag_quality}),
        children=children,
        raw={"tasks": tasks},
    )


def build_knowledge_entity_card(
    node: dict[str, Any],
    *,
    tool_name: str,
    tool_result_id: str | None = None,
    source_channel: str = "ai_tool",
) -> dict[str, Any]:
    node_id = str(node.get("id")) if node.get("id") is not None else None
    title = node.get("title") or node.get("name") or "未命名知识节点"
    summary = node.get("summary") or node.get("description")
    tags = node.get("tags")
    return build_entity_card(
        entity_type="knowledge_node",
        entity_id=node_id,
        title=title,
        summary=summary,
        status="mastery",
        execution_state="active",
        source=_compact_dict({"channel": source_channel, "tool_name": tool_name}),
        primary_action=build_entity_action(
            action_id="open_knowledge",
            action_type="open_detail",
            label="查看知识点",
            route=f"/galaxy?nodeId={node_id}" if node_id else "/galaxy",
        ),
        secondary_actions=(
            [
                build_entity_action(
                    action_id="share_knowledge",
                    action_type="share_resource",
                    label="分享知识卡",
                    payload={"resource_type": "knowledge_node", "resource_id": node_id},
                )
            ]
            if node_id
            else None
        ),
        share=(
            build_share_payload(
                resource_type="knowledge_node",
                resource_id=node_id,
                title=title,
                subtitle=summary,
            )
            if node_id
            else None
        ),
        feedback=build_feedback_payload(tool_result_id=tool_result_id),
        metrics=_compact_dict({"mastery_level": node.get("mastery_level")}),
        tags=[str(tag) for tag in tags] if isinstance(tags, list) else None,
        raw=node,
    )


def build_review_entity_card(
    review: dict[str, Any],
    *,
    tool_name: str,
    tool_result_id: str | None = None,
    source_channel: str = "ai_tool",
) -> dict[str, Any]:
    review_id = (
        str(review.get("id") or review.get("review_id")) if (review.get("id") or review.get("review_id")) else None
    )
    plan_id = str(review.get("plan_id")) if review.get("plan_id") else None
    subject = review.get("subject") or review.get("subject_code")
    title = review.get("title") or review.get("name") or "复盘建议"
    summary = review.get("summary") or review.get("description") or review.get("diagnosis")
    route_query = _compact_dict(
        {
            "mode": review.get("mode") or "today",
            "subject": subject,
            "plan_id": plan_id,
            "review_id": review_id,
        }
    )
    route = f"/review?{urlencode(route_query)}" if route_query else "/review?mode=today"
    return build_entity_card(
        entity_type="review",
        entity_id=review_id,
        title=title,
        summary=summary,
        status=review.get("status") or review.get("decision"),
        execution_state=review.get("execution_state") or "suggested",
        source=_compact_dict({"channel": source_channel, "tool_name": tool_name}),
        primary_action=build_entity_action(
            action_id="open_review",
            action_type="open_detail",
            label="开始复盘",
            route=route,
        ),
        secondary_actions=(
            [
                build_entity_action(
                    action_id="share_review",
                    action_type="share_resource",
                    label="分享复盘",
                    payload={"resource_type": "review", "resource_id": review_id},
                )
            ]
            if review_id
            else None
        ),
        share=(
            build_share_payload(
                resource_type="review",
                resource_id=review_id,
                title=title,
                subtitle=summary,
                meta=_compact_dict({"plan_id": plan_id, "subject": subject}),
            )
            if review_id
            else None
        ),
        feedback=build_feedback_payload(tool_result_id=tool_result_id),
        linked_entities=_compact_dict({"plan_id": plan_id, "subject": subject}),
        metrics=_compact_dict(
            {
                "score": review.get("score") or review.get("overall_score"),
                "due_count": review.get("due_count"),
                "weak_node_count": review.get("weak_node_count"),
            }
        ),
        tags=[str(tag) for tag in review.get("tags", [])] if isinstance(review.get("tags"), list) else None,
        raw=review,
    )


def build_vocabulary_entity_card(
    vocabulary: dict[str, Any],
    *,
    tool_name: str,
    tool_result_id: str | None = None,
    source_channel: str = "ai_tool",
) -> dict[str, Any]:
    word = str(vocabulary.get("word") or vocabulary.get("term") or "").strip()
    word_id = (
        str(vocabulary.get("id") or vocabulary.get("word_id"))
        if (vocabulary.get("id") or vocabulary.get("word_id"))
        else None
    )
    title = vocabulary.get("title") or word or "词汇卡片"
    summary = vocabulary.get("definition") or vocabulary.get("translation") or vocabulary.get("summary")
    route_query = _compact_dict({"word": word or None})
    route = f"/tools/vocabulary_lookup?{urlencode(route_query)}" if route_query else "/tools/vocabulary_lookup"
    return build_entity_card(
        entity_type="vocabulary",
        entity_id=word_id or word or None,
        title=title,
        summary=summary,
        status=vocabulary.get("status") or ("saved" if vocabulary.get("in_wordbook") else "lookup"),
        execution_state=vocabulary.get("execution_state") or "suggested",
        source=_compact_dict({"channel": source_channel, "tool_name": tool_name}),
        primary_action=build_entity_action(
            action_id="open_vocabulary",
            action_type="open_detail",
            label="查看词汇",
            route=route,
            payload=_compact_dict({"word": word or None, "word_id": word_id}),
        ),
        secondary_actions=[
            build_entity_action(
                action_id="review_wordbook",
                action_type="open_detail",
                label="去单词本复习",
                route="/tools/wordbook",
                payload={"tool_id": "wordbook"},
            )
        ],
        share=(
            build_share_payload(
                resource_type="vocabulary",
                resource_id=word_id or word,
                title=title,
                subtitle=summary,
                meta=_compact_dict({"word": word or None, "part_of_speech": vocabulary.get("part_of_speech")}),
            )
            if (word_id or word)
            else None
        ),
        feedback=build_feedback_payload(tool_result_id=tool_result_id),
        linked_entities=_compact_dict(
            {
                "knowledge_node_id": vocabulary.get("knowledge_node_id"),
                "source_translation_id": vocabulary.get("source_translation_id"),
            }
        ),
        metrics=_compact_dict(
            {
                "importance": vocabulary.get("importance"),
                "review_count": vocabulary.get("review_count"),
            }
        ),
        tags=[str(tag) for tag in vocabulary.get("tags", [])] if isinstance(vocabulary.get("tags"), list) else None,
        raw=vocabulary,
    )


def build_seed_entity_card(
    seed: dict[str, Any],
    *,
    tool_name: str,
    tool_result_id: str | None = None,
    source_channel: str = "ai_tool",
) -> dict[str, Any]:
    seed_id = (
        str(seed.get("id") or seed.get("library_id") or seed.get("seed_id"))
        if (seed.get("id") or seed.get("library_id") or seed.get("seed_id"))
        else None
    )
    title = seed.get("title") or seed.get("name") or "种子内容"
    summary = seed.get("summary") or seed.get("description") or seed.get("content")
    return build_entity_card(
        entity_type="seed",
        entity_id=seed_id,
        title=title,
        summary=summary,
        status=seed.get("status") or seed.get("category"),
        execution_state=seed.get("execution_state") or "adoptable",
        source=_compact_dict({"channel": source_channel, "tool_name": tool_name}),
        primary_action=build_entity_action(
            action_id="open_seed",
            action_type="open_detail",
            label="查看种子",
            route=f"/seed-libraries/{seed_id}" if seed_id else "/seed-libraries",
        ),
        secondary_actions=(
            [
                build_entity_action(
                    action_id="adopt_seed",
                    action_type="adopt_resource",
                    label="采纳种子",
                    payload={"resource_type": "seed", "resource_id": seed_id},
                ),
                build_entity_action(
                    action_id="share_seed",
                    action_type="share_resource",
                    label="分享种子",
                    payload={"resource_type": "seed", "resource_id": seed_id},
                ),
            ]
            if seed_id
            else None
        ),
        share=(
            build_share_payload(
                resource_type="seed",
                resource_id=seed_id,
                title=title,
                subtitle=summary,
                meta=_compact_dict({"category": seed.get("category"), "difficulty": seed.get("difficulty")}),
            )
            if seed_id
            else None
        ),
        feedback=build_feedback_payload(tool_result_id=tool_result_id),
        linked_entities=_compact_dict(
            {
                "plan_id": seed.get("plan_id"),
                "task_id": seed.get("task_id"),
                "knowledge_node_id": seed.get("knowledge_node_id"),
            }
        ),
        metrics=_compact_dict(
            {
                "adoption_count": seed.get("adoption_count"),
                "rating": seed.get("rating"),
            }
        ),
        tags=[str(tag) for tag in seed.get("tags", [])] if isinstance(seed.get("tags"), list) else None,
        raw=seed,
    )


def build_learning_path_entity_card(
    *,
    plan: dict[str, Any],
    tasks: list[dict[str, Any]],
    target_name: str,
    tool_name: str,
    tool_result_id: str | None = None,
    source_channel: str = "learning_path",
) -> dict[str, Any]:
    plan_card = build_plan_entity_card(
        plan,
        tool_name=tool_name,
        tool_result_id=tool_result_id,
        source_channel=source_channel,
    )
    task_list_card = build_task_list_entity_card(
        tasks,
        tool_name=tool_name,
        tool_result_id=tool_result_id,
        plan_id=str(plan.get("id") or plan.get("plan_id") or ""),
        plan_title=str(plan.get("name") or plan.get("title") or f"学习路径：{target_name}"),
        source_channel=source_channel,
    )
    plan_id = plan_card.get("entity_id")
    return build_entity_card(
        entity_type="learning_path",
        entity_id=plan_id,
        title=f"学习路径：{target_name}",
        summary=plan_card.get("summary") or "AI 已生成学习路径与可执行任务",
        status="generated",
        execution_state="draft",
        source=_compact_dict({"channel": source_channel, "tool_name": tool_name}),
        primary_action=build_entity_action(
            action_id="open_learning_path_plan",
            action_type="open_detail",
            label="查看学习计划",
            route=f"/plans/{plan_id}" if plan_id else "/plans",
        ),
        secondary_actions=(
            [
                build_entity_action(
                    action_id="share_learning_path",
                    action_type="share_resource",
                    label="分享学习路径",
                    payload={"resource_type": "plan", "resource_id": plan_id},
                )
            ]
            if plan_id
            else None
        ),
        share=(
            build_share_payload(
                resource_type="plan",
                resource_id=plan_id or "",
                title=f"学习路径：{target_name}",
                subtitle=plan_card.get("summary"),
                meta=_compact_dict({"task_count": len(tasks), "target_name": target_name}),
            )
            if plan_id
            else None
        ),
        feedback=build_feedback_payload(
            tool_result_id=tool_result_id,
            confirmation_required=bool(tool_result_id),
            can_confirm_all=bool(tool_result_id),
        ),
        linked_entities=_compact_dict({"plan_id": plan_id, "target_name": target_name}),
        metrics=_compact_dict({"task_count": len(tasks)}),
        children=[plan_card, task_list_card],
        raw=_compact_dict({"plan": plan, "tasks": tasks, "target_name": target_name}),
    )


def build_prediction_entity_card(
    *,
    prediction_id: str,
    title: str,
    summary: str,
    action_type: str,
    suggested_prompt: str,
    predicted_window: str,
    confidence: float,
    surface: str | None,
    reasons: list[str] | None = None,
    source: str | None = None,
    tier: str | None = None,
    recommended_actions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    primary_route = "/chat"
    if recommended_actions:
        first_route = recommended_actions[0].get("target_route")
        if isinstance(first_route, str) and first_route.strip():
            primary_route = first_route

    return build_entity_card(
        entity_type="prediction",
        entity_id=prediction_id,
        title=title,
        summary=summary,
        status=predicted_window,
        execution_state="suggested",
        source=_compact_dict({"channel": "prediction", "source": source, "tier": tier}),
        primary_action=build_entity_action(
            action_id="apply_prediction",
            action_type="continue_chat" if primary_route == "/chat" else "open_detail",
            label="按预测继续",
            route=primary_route,
            payload=_compact_dict(
                {
                    "prediction_id": prediction_id,
                    "predicted_action_type": action_type,
                    "suggested_prompt": suggested_prompt,
                    "surface": surface,
                }
            ),
        ),
        secondary_actions=(
            [
                build_entity_action(
                    action_id="view_prediction_reason",
                    action_type="show_explanation",
                    label="查看原因",
                    payload={"reasons": reasons or []},
                )
            ]
            if reasons
            else None
        ),
        linked_entities=_compact_dict(
            {
                "predicted_action_type": action_type,
                "surface": surface,
            }
        ),
        metrics=_compact_dict(
            {
                "confidence": round(confidence, 3),
                "recommended_action_count": len(recommended_actions or []),
            }
        ),
        tags=[reason for reason in (reasons or [])[:3] if reason],
        raw=_compact_dict(
            {
                "prediction_id": prediction_id,
                "predicted_action_type": action_type,
                "suggested_prompt": suggested_prompt,
                "predicted_window": predicted_window,
                "recommended_actions": recommended_actions,
            }
        ),
    )


def build_shared_resource_entity_card(
    *,
    shared_resource_id: str,
    resource_type: str,
    resource_id: str | None,
    title: str,
    summary: str | None = None,
    permission: str | None = None,
    comment: str | None = None,
    meta: dict[str, Any] | None = None,
    target_group_id: str | None = None,
    target_user_id: str | None = None,
    owner: dict[str, Any] | None = None,
    visibility: str | None = None,
    expires_at: str | None = None,
    revoked_at: str | None = None,
    availability: str | None = None,
) -> dict[str, Any]:
    adoptable_resource_types = {
        "plan",
        "task",
        "knowledge_node",
        "seed_library",
        "seed_item",
        "cognitive_fragment",
        "curiosity_capsule",
        "cognitive_prism_pattern",
        "achievement",
        "vocabulary_set",
        "review_result",
    }
    default_route = (
        f"/plans/{resource_id}"
        if resource_type == "plan" and resource_id
        else (
            f"/tasks/{resource_id}"
            if resource_type == "task" and resource_id
            else f"/galaxy?nodeId={resource_id}" if resource_type == "knowledge_node" and resource_id else "/community"
        )
    )
    adoption_action = (
        build_entity_action(
            action_id="adopt_shared_resource",
            action_type="adopt_resource",
            label="采纳到我的空间",
            route=f"/community/shared-resources/{shared_resource_id}/adopt",
            payload={
                "shared_resource_id": shared_resource_id,
                "resource_type": resource_type,
                "resource_id": resource_id,
            },
        )
        if resource_type in adoptable_resource_types and availability not in {"revoked", "expired", "private"}
        else None
    )
    preview = _compact_dict(
        {
            "title": title,
            "summary": summary,
            "comment": comment,
            "meta": meta,
        }
    )
    source_receipt = _compact_dict(
        {
            "channel": "community_share",
            "shared_resource_id": shared_resource_id,
            "resource_type": resource_type,
            "source_resource_id": resource_id,
            "target_group_id": target_group_id,
            "target_user_id": target_user_id,
        }
    )
    return build_entity_card(
        entity_type="shared_resource",
        entity_id=shared_resource_id,
        title=title,
        summary=comment or summary,
        status=permission,
        execution_state=availability or "shared",
        source=_compact_dict(
            {
                "channel": "community_share",
                "resource_type": resource_type,
                "owner": owner,
                "visibility": visibility,
                "source_receipt": source_receipt,
            }
        ),
        primary_action=build_entity_action(
            action_id="open_shared_resource",
            action_type="open_detail",
            label="查看资源",
            route=default_route,
        ),
        secondary_actions=[adoption_action] if adoption_action else None,
        share=build_share_payload(
            resource_type=resource_type,
            resource_id=resource_id or shared_resource_id,
            title=title,
            subtitle=summary,
            meta=meta,
            owner=owner,
            visibility=visibility,
            preview=preview,
            source_receipt=source_receipt,
            adoption_action=adoption_action,
            expires_at=expires_at,
            revoked_at=revoked_at,
            availability=availability or "available",
        ),
        linked_entities=_compact_dict(
            {
                "resource_type": resource_type,
                "resource_id": resource_id,
                "target_group_id": target_group_id,
                "target_user_id": target_user_id,
                "shared_resource_id": shared_resource_id,
            }
        ),
        metrics=_compact_dict({"permission": permission, "availability": availability or "available"}),
        raw=_compact_dict(
            {
                "shared_resource_id": shared_resource_id,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "comment": comment,
                "meta": meta,
                "expires_at": expires_at,
                "revoked_at": revoked_at,
            }
        ),
    )


def build_unavailable_shared_resource_entity_card(
    *,
    shared_resource_id: str,
    resource_type: str,
    title: str,
    reason: str,
    owner: dict[str, Any] | None = None,
    visibility: str | None = None,
    expires_at: str | None = None,
    revoked_at: str | None = None,
) -> dict[str, Any]:
    return build_shared_resource_entity_card(
        shared_resource_id=shared_resource_id,
        resource_type=resource_type,
        resource_id=None,
        title=title,
        summary=reason,
        permission="view",
        meta={"unavailable_reason": reason},
        owner=owner,
        visibility=visibility,
        expires_at=expires_at,
        revoked_at=revoked_at,
        availability="revoked" if revoked_at else "expired" if expires_at else "private",
    )
