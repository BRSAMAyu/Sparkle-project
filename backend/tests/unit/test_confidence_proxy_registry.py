from __future__ import annotations

import pytest

from app.core.i18n import I18n
from app.services.metacognition_registry import (
    CONFIDENCE_PROXY_REGISTRY,
    DASHBOARD_LANGUAGE_TEMPLATES,
    PROCESS_SCAFFOLDING_TEMPLATES,
    ensure_registered_proxies,
    render_guard_samples,
    render_template,
)


def test_confidence_proxy_registry_contains_expected_five_proxies() -> None:
    assert set(CONFIDENCE_PROXY_REGISTRY) == {
        "revision_frequency",
        "self_correction_rate",
        "question_to_statement_ratio",
        "time_to_first_action",
        "completion_vs_estimate_delta_sign",
    }


def test_every_confidence_proxy_has_forbidden_interpretations() -> None:
    for definition in CONFIDENCE_PROXY_REGISTRY.values():
        assert definition.forbidden_interpretations
        assert definition.known_biases


def test_ensure_registered_proxies_preserves_registered_values() -> None:
    selected = ensure_registered_proxies(["revision_frequency", "time_to_first_action"])
    assert selected == ("revision_frequency", "time_to_first_action")


def test_ensure_registered_proxies_rejects_unknown_proxy() -> None:
    with pytest.raises(ValueError):
        ensure_registered_proxies(["freeform_confidence_proxy"])


# ---------------------------------------------------------------------------
# PROD-LOG2 ②-1（PROD-FIX-4）：语言模板必须是 i18n key，不得把字面句子当 key
#
# 缺陷：metacognition_registry.py 第二个 DASHBOARD_LANGUAGE_TEMPLATES 定义（遮蔽
# 前一个）把中文句子当 template 塞给 I18n.t 当 key 查 → 每条消息打 "Translation
# key not found" WARNING（生产 88min 5739 条，占引擎 WARNING 93%），且 i18n 未命中
# 兜底返回 key 本身（输出碰巧正确）掩盖配置错误。
# ---------------------------------------------------------------------------


def test_every_language_template_is_a_dotted_i18n_key() -> None:
    """模板字段必须形如 i18n key：含 '.'、无空白、不含 CJK 字面句."""
    for registry in (PROCESS_SCAFFOLDING_TEMPLATES, DASHBOARD_LANGUAGE_TEMPLATES):
        for item in registry:
            assert "." in item.template, f"{item.template_id}: template 不是 i18n key: {item.template}"
            assert not any(ch.isspace() for ch in item.template), (
                f"{item.template_id}: template 含空白（不像 i18n key）: {item.template}"
            )
            assert not any("\u4e00" <= ch <= "\u9fff" for ch in item.template), (
                f"{item.template_id}: 字面句子当 key（PROD-LOG2 ②-1 同型）: {item.template}"
            )


@pytest.mark.parametrize("locale", ["zh", "en"])
def test_every_template_key_resolves_in_i18n(locale: str) -> None:
    """所有模板 key 必须在两个 locale 的 i18n 数据中命中（未命中=兜底返回 key 本身）."""
    for registry in (PROCESS_SCAFFOLDING_TEMPLATES, DASHBOARD_LANGUAGE_TEMPLATES):
        for item in registry:
            rendered = I18n.t(item.template, locale=locale)
            assert rendered != item.template, (
                f"{item.template_id}: key '{item.template}' 在 {locale} 未命中（回退返回 key 本身）"
            )


def test_render_all_dashboard_templates_emits_no_translation_warnings() -> None:
    """完整渲染 dashboard 模板不得产生任何 'Translation key not found' WARNING.

    生产面：batch 评测流每条消息触发多次，88 分钟 5739 条（引擎 WARNING 93%）。
    """
    from loguru import logger

    records: list = []
    sink_id = logger.add(lambda msg: records.append(msg.record), level="WARNING")
    try:
        for item in DASHBOARD_LANGUAGE_TEMPLATES:
            render_template(item.template_id, locale="zh", sample_size=10, display_value="2.3")
        samples = render_guard_samples(locale="zh")
        assert samples
    finally:
        logger.remove(sink_id)

    misses = [
        r["message"]
        for r in records
        if "Translation key not found" in str(r["message"])
    ]
    assert misses == [], f"渲染模板触发 i18n 未命中 WARNING: {misses[:5]}"
