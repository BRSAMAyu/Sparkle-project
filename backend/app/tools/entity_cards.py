from __future__ import annotations

from typing import Any


ENTITY_CARD_SCHEMA_VERSION = "v1"


def _compact_dict(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != [] and value != {}
    }


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


def build_share_payload(
    *,
    resource_type: str,
    resource_id: str,
    title: str,
    subtitle: str | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _compact_dict(
        {
            "resource_type": resource_type,
            "resource_id": resource_id,
            "title": title,
            "subtitle": subtitle,
            "meta": meta,
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
        execution_state="confirmed"
        if task.get("status") in {"IN_PROGRESS", "COMPLETED"}
        else "draft",
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
        secondary_actions=[
            build_entity_action(
                action_id="share_task",
                action_type="share_resource",
                label="分享卡片",
                payload={"resource_type": "task", "resource_id": task_id},
            )
        ]
        if task_id
        else None,
        share=build_share_payload(
            resource_type="task",
            resource_id=task_id,
            title=title,
            subtitle=guide_content,
        )
        if task_id
        else None,
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
        secondary_actions=[
            build_entity_action(
                action_id="share_plan",
                action_type="share_resource",
                label="分享计划",
                payload={"resource_type": "plan", "resource_id": plan_id},
            )
        ]
        if plan_id
        else None,
        share=build_share_payload(
            resource_type="plan",
            resource_id=plan_id,
            title=title,
            subtitle=description,
        )
        if plan_id
        else None,
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
        primary_action=build_entity_action(
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
        ),
        secondary_actions=[
            build_entity_action(
                action_id="share_plan",
                action_type="share_resource",
                label="分享计划",
                payload={"resource_type": "plan", "resource_id": plan_id},
            )
        ]
        if plan_id
        else None,
        share=build_share_payload(
            resource_type="plan" if plan_id else "task",
            resource_id=plan_id or str(tasks[0].get("id")) if tasks else "",
            title=title,
            subtitle=f"包含 {len(tasks)} 个可执行任务",
            meta=_compact_dict({"plan_title": plan_title, "rag_quality": rag_quality}),
        )
        if tasks
        else None,
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
        secondary_actions=[
            build_entity_action(
                action_id="share_knowledge",
                action_type="share_resource",
                label="分享知识卡",
                payload={"resource_type": "knowledge_node", "resource_id": node_id},
            )
        ]
        if node_id
        else None,
        share=build_share_payload(
            resource_type="knowledge_node",
            resource_id=node_id,
            title=title,
            subtitle=summary,
        )
        if node_id
        else None,
        feedback=build_feedback_payload(tool_result_id=tool_result_id),
        metrics=_compact_dict({"mastery_level": node.get("mastery_level")}),
        tags=[str(tag) for tag in tags] if isinstance(tags, list) else None,
        raw=node,
    )
