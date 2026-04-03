from __future__ import annotations

import pytest

from app.services.template_registry import TemplateRegistry
from app.services.template_service import TemplateService


_INTENT_BY_TONE = {
    "plan_path_soft_replan": ["CURIOUS", "SUPPORTIVE", "DIRECT", "MICRO_RESTART"],
    "concept_gap_focus": ["CURIOUS", "SUPPORTIVE", "DIRECT", "MICRO_RESTART"],
    "micro_restart": ["CURIOUS", "SUPPORTIVE", "DIRECT", "MICRO_RESTART"],
    "overload_lighten_path": ["CURIOUS", "SUPPORTIVE", "DIRECT", "MICRO_RESTART"],
    "recover_self_efficacy": ["CURIOUS", "SUPPORTIVE", "DIRECT", "MICRO_RESTART"],
}


@pytest.mark.asyncio
async def test_phase3_templates_are_tone_aware_and_language_safe():
    service = TemplateService(TemplateRegistry())
    variables = {
        "concept_a": "可逆过程",
        "concept_b": "绝热过程",
        "weak_concept": "熵增判断",
        "estimated_minutes": 10,
        "suggested_step": "先写出一个最小例子",
        "completed_count": 3,
    }

    rendered_texts: list[str] = []
    for intent_type, tones in _INTENT_BY_TONE.items():
        support_level = 4 if intent_type in {"concept_gap_focus", "micro_restart", "overload_lighten_path"} else 3
        for tone in tones:
            template = await service.select_variant(
                intent_type=intent_type,
                support_level=support_level,
                user_id="template-test-user",
                preferred_tone=tone,
            )
            rendered = service.render(template, variables)
            rendered_texts.append(rendered)

            assert template.tone == tone
            assert not service.forbidden_pattern_hits(rendered), rendered

    assert len(rendered_texts) == 20
