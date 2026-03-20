from app.tools.entity_cards import (
    build_plan_entity_card,
    build_task_entity_card,
    build_task_list_entity_card,
    wrap_widget_payload,
)


def test_build_task_entity_card_contains_unified_fields():
    payload = {
        "id": "task-1",
        "title": "复习傅里叶变换",
        "guide_content": "先梳理概念，再做 2 道题",
        "status": "PENDING",
        "plan_id": "plan-1",
        "estimated_minutes": 30,
        "priority": 2,
        "difficulty": 3,
    }

    entity = build_task_entity_card(
        payload,
        tool_name="create_task",
        tool_result_id="tool-1",
    )

    assert entity["entity_type"] == "task"
    assert entity["entity_id"] == "task-1"
    assert entity["feedback"]["tool_result_id"] == "tool-1"
    assert entity["share"]["resource_type"] == "task"
    assert entity["linked_entities"]["plan_id"] == "plan-1"


def test_wrap_widget_payload_preserves_legacy_and_entity_data():
    widget = wrap_widget_payload(
        widget_type="plan_card",
        widget_data={"id": "plan-1", "title": "高数冲刺"},
        entity_card=build_plan_entity_card(
            {
                "id": "plan-1",
                "title": "高数冲刺",
                "type": "sprint",
                "progress": 0.4,
                "task_count": 5,
            },
            tool_name="create_plan",
        ),
    )

    assert widget["id"] == "plan-1"
    assert widget["entity_type"] == "plan"
    assert widget["entity_card"]["metrics"]["task_count"] == 5


def test_build_task_list_entity_card_embeds_children():
    entity = build_task_list_entity_card(
        [
            {"id": "task-a", "title": "任务 A", "status": "PENDING"},
            {"id": "task-b", "title": "任务 B", "status": "IN_PROGRESS"},
        ],
        tool_name="generate_tasks_for_plan",
        tool_result_id="tool-list-1",
        plan_id="plan-9",
        plan_title="线代学习路径",
        rag_quality="high",
    )

    assert entity["entity_type"] == "task_list"
    assert entity["feedback"]["can_confirm_all"] is True
    assert entity["metrics"]["task_count"] == 2
    assert entity["linked_entities"]["plan_id"] == "plan-9"
    assert len(entity["children"]) == 2
