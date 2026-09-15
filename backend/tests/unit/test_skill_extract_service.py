import pytest

from app.services.skill_extract_service import SkillExtractService


@pytest.mark.asyncio
async def test_skill_extract_requires_rule_trigger_and_parses_draft(monkeypatch):
    monkeypatch.setattr("app.services.skill_extract_service.settings.SPARKLE_SKILL_EXTRACT_ENABLED", True)

    async def _fake_llm(_messages, **_kwargs):
        return {
            "name": "Exam Triage",
            "pattern_template": "Start with scope, blockers, and the smallest next step.",
            "activation_conditions": [{"kind": "intent_keywords", "value": ["exam"]}],
            "examples": ["先缩小范围，再推进。"],
            "rejected": False,
        }

    service = SkillExtractService(llm_json=_fake_llm)
    assert service.matches_explicit_trigger("以后这样做，记住这种方式") is True

    draft = await service.generate_draft(
        trigger_type="explicit_phrase",
        consent_text="以后这样做，记住这种方式",
        user_message="我快考试了，不知道先做什么。",
        assistant_message="先把考试范围缩到三个模块，再定明天第一步。",
        seconds_since_response=30,
    )

    assert draft.name == "Exam Triage"
    assert draft.activation_conditions[0].kind == "intent_keywords"


@pytest.mark.asyncio
async def test_skill_extract_rejects_non_rule_trigger(monkeypatch):
    monkeypatch.setattr("app.services.skill_extract_service.settings.SPARKLE_SKILL_EXTRACT_ENABLED", True)
    service = SkillExtractService(llm_json=None)

    with pytest.raises(ValueError, match="trigger rejected"):
        await service.generate_draft(
            trigger_type="explicit_phrase",
            consent_text="这个挺好",
            user_message="test",
            assistant_message="test",
            seconds_since_response=10,
        )
