import pytest

from app.services.custom_expert_service import (
    CustomExpertService,
    is_custom_expert_id,
    make_custom_expert_id,
)


@pytest.mark.asyncio
async def test_create_and_serialize_custom_expert(db_session, test_user):
    service = CustomExpertService(db_session)

    expert = await service.create_custom_expert(
        user_id=str(test_user.id),
        name="政策拆解官",
        description="把政策文本拆成用户可执行步骤",
        system_prompt="你是政策拆解专家，专门把复杂政策翻译成可执行清单。",
        base_expert_id="deep_analyst",
        preferred_model_key="glm_5_max",
        preferred_model_tier="reasoning",
    )
    await db_session.commit()

    payload = service.serialize_runtime_profile(expert)
    assert payload["display_name"] == "政策拆解官"
    assert payload["base_expert_id"] == "deep_analyst"
    assert payload["preferred_model_key"] == "glm_5_max"
    assert payload["entry_chat_mode"].startswith("expert::custom_expert:")
    assert is_custom_expert_id(payload["id"]) is True
    assert make_custom_expert_id(expert.id) == payload["id"]


@pytest.mark.asyncio
async def test_create_custom_team_round_trip(db_session, test_user):
    service = CustomExpertService(db_session)
    expert = await service.create_custom_expert(
        user_id=str(test_user.id),
        name="讲题官",
        description="讲题",
        system_prompt="把题目讲清楚。",
    )
    await db_session.flush()
    custom_id = make_custom_expert_id(expert.id)
    team = await service.create_custom_team(
        user_id=str(test_user.id),
        name="讲题团队",
        expert_ids=["deep_analyst", custom_id],
        answer_expert_ids=[custom_id],
        collaboration_mode="debate",
    )
    await db_session.commit()

    payload = service.serialize_team(team)
    assert payload["expert_ids"] == ["deep_analyst", custom_id]
    assert payload["answer_expert_ids"] == [custom_id]
    assert payload["collaboration_mode"] == "debate"
