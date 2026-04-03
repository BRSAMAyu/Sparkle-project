from __future__ import annotations

import re

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

_TONE_EXPECTATIONS = {
    "CURIOUS": ("我发现", "要不要", "像是", "试"),
    "SUPPORTIVE": ("我们", "一起", "我帮你", "陪你", "可以", "要不要", "就够了", "会顺很多", "变轻一点"),
    "DIRECT": ("我建议", "根据目前的情况", "根据现在的信号", "根据现在的负荷", "根据现在的节奏"),
    "MICRO_RESTART": ("先", "只", "一步", "小", "分钟"),
}

_VARIABLES = {
    "task_name": "热力学错题复盘",
    "suggested_step": "先画出可逆过程和不可逆过程的边界线",
    "break_duration": 10,
    "focus_duration": 45,
    "alternative_task": "先看一个例子",
    "relaxation_activity": "做两分钟呼吸调整",
    "switch_count": 4,
    "concept_a": "可逆过程",
    "concept_b": "不可逆过程",
    "weak_concept": "熵增判断",
    "estimated_minutes": 10,
    "estimated_time": 10,
    "completed_count": 3,
}


def _all_variants(registry: TemplateRegistry):
    registry.ensure_loaded()
    for entries in registry._templates.values():
        for entry in entries:
            for variant in entry.variants:
                yield entry, variant


def _extract_placeholders(text: str) -> set[str]:
    return set(re.findall(r"{([^{}]+)}", text))


@pytest.mark.asyncio
async def test_phase3_templates_are_tone_aware_and_language_safe():
    service = TemplateService(TemplateRegistry())

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
            rendered = service.render(template, _VARIABLES)
            rendered_texts.append(rendered)

            assert template.tone == tone
            assert not service.forbidden_pattern_hits(rendered), rendered

    assert len(rendered_texts) == 20


def test_all_intervention_templates_pass_language_audit():
    registry = TemplateRegistry()
    service = TemplateService(registry)

    audited = 0
    for entry, variant in _all_variants(registry):
        placeholders = _extract_placeholders(variant.content)
        missing = placeholders - _VARIABLES.keys()
        assert not missing, f"{variant.variant_id} is missing sample variables: {sorted(missing)}"

        rendered = service.render(
            template=type(
                "SelectedTemplateLike",
                (),
                {
                    "content": variant.content,
                },
            )(),
            variables=_VARIABLES,
        )
        assert not service.forbidden_pattern_hits(rendered), (
            f"{entry.intent_type}/{variant.variant_id} failed audit: {rendered}"
        )
        audited += 1

    assert audited >= 40


@pytest.mark.asyncio
async def test_core_tone_variants_remain_distinct_and_on_style():
    service = TemplateService(TemplateRegistry())

    for intent_type, tones in _INTENT_BY_TONE.items():
        support_level = 4 if intent_type in {"concept_gap_focus", "micro_restart", "overload_lighten_path"} else 3
        rendered_by_tone: dict[str, str] = {}

        for tone in tones:
            template = await service.select_variant(
                intent_type=intent_type,
                support_level=support_level,
                user_id=f"{intent_type}-{tone}-audit-user",
                preferred_tone=tone,
            )
            rendered = service.render(template, _VARIABLES)
            rendered_by_tone[tone] = rendered

            assert any(marker in rendered for marker in _TONE_EXPECTATIONS[tone]), rendered
            assert not service.forbidden_pattern_hits(rendered), rendered

        assert len(set(rendered_by_tone.values())) == len(tones), rendered_by_tone
