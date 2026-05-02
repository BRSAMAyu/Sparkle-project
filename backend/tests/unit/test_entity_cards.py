from app.tools.entity_cards import (
    build_knowledge_entity_card,
    build_learning_path_entity_card,
    build_plan_entity_card,
    build_prediction_entity_card,
    build_review_entity_card,
    build_seed_entity_card,
    build_shared_resource_entity_card,
    build_task_entity_card,
    build_task_list_entity_card,
    build_unavailable_shared_resource_entity_card,
    build_vocabulary_entity_card,
    validate_entity_card,
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


def test_build_learning_path_entity_card_links_plan_and_tasks():
    entity = build_learning_path_entity_card(
        plan={
            "id": "plan-lp-1",
            "name": "学习路径：概率论",
            "description": "先补基础再进目标节点",
            "type": "growth",
        },
        tasks=[
            {"id": "task-1", "title": "复习排列组合", "status": "PENDING"},
            {"id": "task-2", "title": "完成条件概率练习", "status": "PENDING"},
        ],
        target_name="概率论",
        tool_name="generate_learning_path_plan",
    )

    assert entity["entity_type"] == "learning_path"
    assert entity["linked_entities"]["target_name"] == "概率论"
    assert len(entity["children"]) == 2
    assert entity["children"][0]["entity_type"] == "plan"
    assert entity["children"][1]["entity_type"] == "task_list"


def test_build_prediction_entity_card_contains_action_metadata():
    entity = build_prediction_entity_card(
        prediction_id="prediction-1",
        title="系统预测你接下来会继续重点任务",
        summary="建议先推进 25 分钟。",
        action_type="resume_priority_task",
        suggested_prompt="帮我继续今天的重点任务",
        predicted_window="next_2h",
        confidence=0.82,
        surface="dashboard",
        reasons=["当前还有高优先级任务"],
        source="rules",
        tier="rules",
        recommended_actions=[
            {
                "id": "prediction-1:primary",
                "action_type": "resume_priority_task",
                "target_route": "/chat",
            }
        ],
    )

    assert entity["entity_type"] == "prediction"
    assert entity["metrics"]["confidence"] == 0.82
    assert entity["primary_action"]["payload"]["suggested_prompt"] == "帮我继续今天的重点任务"


def test_ai_conversation_card_protocol_builders_validate_core_journeys():
    cards = [
        build_task_entity_card(
            {"id": "task-1", "title": "做一组错题", "status": "PENDING"},
            tool_name="create_task",
        ),
        build_plan_entity_card(
            {"id": "plan-1", "title": "7 天概率论冲刺", "type": "sprint"},
            tool_name="create_plan",
        ),
        build_knowledge_entity_card(
            {"id": "node-1", "title": "条件概率", "mastery_level": 42},
            tool_name="create_knowledge_node",
        ),
        build_shared_resource_entity_card(
            shared_resource_id="share-1",
            resource_type="plan",
            resource_id="plan-1",
            title="可采纳的冲刺计划",
            permission="adoptable",
        ),
        build_review_entity_card(
            {
                "review_id": "review-1",
                "title": "今天复盘条件概率",
                "plan_id": "plan-1",
                "score": 0.7,
            },
            tool_name="create_review",
        ),
        build_vocabulary_entity_card(
            {
                "word_id": "word-1",
                "word": "derive",
                "definition": "to obtain from a source",
                "in_wordbook": True,
            },
            tool_name="vocabulary_lookup",
        ),
        build_seed_entity_card(
            {
                "library_id": "seed-1",
                "name": "概率论高频错题种子",
                "description": "可生成复盘任务的题型包",
            },
            tool_name="seed_library",
        ),
    ]

    for card in cards:
        assert validate_entity_card(card) == [], card
        assert card["schema_version"] == "v1"
        assert card["primary_action"]["route"].startswith("/")

    assert cards[3]["secondary_actions"][0]["type"] == "adopt_resource"
    assert cards[4]["primary_action"]["route"].startswith("/review?")
    assert cards[5]["primary_action"]["route"].startswith("/tools/vocabulary_lookup")
    assert cards[6]["primary_action"]["route"] == "/seed-libraries/seed-1"


def test_entity_card_validation_catches_inert_actions():
    invalid = {
        "schema_version": "v1",
        "entity_type": "task",
        "entity_id": "task-1",
        "title": "No route",
        "primary_action": {
            "id": "open_task",
            "type": "open_detail",
            "label": "Open",
        },
    }

    assert "missing_primary_action_route" in validate_entity_card(invalid)


def test_shared_resource_entity_cards_preserve_first_class_share_protocol():
    shareable_types = [
        "plan",
        "task",
        "achievement",
        "knowledge_node",
        "seed_library",
        "vocabulary_set",
        "review_result",
    ]

    for resource_type in shareable_types:
        entity = build_shared_resource_entity_card(
            shared_resource_id=f"share-{resource_type}",
            resource_type=resource_type,
            resource_id=f"{resource_type}-1",
            title=f"{resource_type} card",
            summary="可采纳的上下文",
            permission="adopt",
            owner={"user_id": "user-1", "display_name": "Ada"},
            visibility="group",
            availability="available",
        )

        share = entity["share"]
        assert share["resource_type"] == resource_type
        assert share["owner"]["user_id"] == "user-1"
        assert share["visibility"] == "group"
        assert share["preview"]["title"] == f"{resource_type} card"
        assert share["source_receipt"]["shared_resource_id"] == f"share-{resource_type}"
        assert share["adoption_action"]["payload"]["resource_type"] == resource_type
        assert entity["secondary_actions"][0]["type"] == "adopt_resource"


def test_unavailable_shared_resource_degrades_without_adoption_action():
    entity = build_unavailable_shared_resource_entity_card(
        shared_resource_id="share-revoked",
        resource_type="plan",
        title="这张分享已不可用",
        reason="分享已撤回，无法继续采纳。",
        owner={"user_id": "user-1", "display_name": "Ada"},
        visibility="direct",
        revoked_at="2026-05-02T09:00:00",
    )

    assert entity["execution_state"] == "revoked"
    assert entity["share"]["availability"] == "revoked"
    assert "secondary_actions" not in entity
