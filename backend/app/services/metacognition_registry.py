from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.i18n import I18n


@dataclass(frozen=True)
class ConfidenceProxyDefinition:
    proxy_id: str
    title: str
    source: str
    aggregation_window: str
    known_biases: tuple[str, ...]
    forbidden_interpretations: tuple[str, ...]
    settings_attr: str


@dataclass(frozen=True)
class LanguageTemplate:
    template_id: str
    kind: str
    dim: str
    direction: str
    template: str


CONFIDENCE_PROXY_REGISTRY: dict[str, ConfidenceProxyDefinition] = {
    "revision_frequency": ConfidenceProxyDefinition(
        proxy_id="revision_frequency",
        title="Revision Frequency",
        source="tasks.updated_at vs tasks.completed_at",
        aggregation_window="last 60 completed tasks",
        known_biases=(
            "Large refactors can inflate post-completion edits.",
            "Collaborative workflows may revise more often without lower confidence.",
        ),
        forbidden_interpretations=(
            "Do not describe this as perfectionism personality.",
            "Do not describe this as procrastination identity.",
        ),
        settings_attr="AURORA_METACOG_PROXY_REVISION_FREQUENCY",
    ),
    "self_correction_rate": ConfidenceProxyDefinition(
        proxy_id="self_correction_rate",
        title="Self-correction Rate",
        source="memory_corrections vs user chat volume",
        aggregation_window="last 90 days",
        known_biases=(
            "Low chat volume makes the ratio noisy.",
            "Some corrections reflect system misunderstanding rather than user uncertainty.",
        ),
        forbidden_interpretations=(
            "Do not describe this as anxiety personality.",
            "Do not describe this as indecisive identity.",
        ),
        settings_attr="AURORA_METACOG_PROXY_SELF_CORRECTION_RATE",
    ),
    "question_to_statement_ratio": ConfidenceProxyDefinition(
        proxy_id="question_to_statement_ratio",
        title="Question to Statement Ratio",
        source="chat_messages.role=user punctuation heuristic",
        aggregation_window="last 120 user turns",
        known_biases=(
            "Some domains naturally involve more questions.",
            "Punctuation habits vary across users and devices.",
        ),
        forbidden_interpretations=(
            "Do not describe this as dependent personality.",
            "Do not describe this as low-confidence identity.",
        ),
        settings_attr="AURORA_METACOG_PROXY_QUESTION_TO_STATEMENT_RATIO",
    ),
    "time_to_first_action": ConfidenceProxyDefinition(
        proxy_id="time_to_first_action",
        title="Time to First Action",
        source="plans.created_at to earliest task action timestamp",
        aggregation_window="last 30 plans",
        known_biases=(
            "Longer setup tasks can delay first action without hesitation.",
            "Some plans are intentionally scheduled for later execution.",
        ),
        forbidden_interpretations=(
            "Do not describe this as avoidance personality.",
            "Do not describe this as laziness identity.",
        ),
        settings_attr="AURORA_METACOG_PROXY_TIME_TO_FIRST_ACTION",
    ),
    "completion_vs_estimate_delta_sign": ConfidenceProxyDefinition(
        proxy_id="completion_vs_estimate_delta_sign",
        title="Completion vs Estimate Delta Sign",
        source="tasks.actual_minutes - tasks.estimated_minutes sign",
        aggregation_window="last 60 completed tasks",
        known_biases=(
            "Task scope changes after planning can invert the sign.",
            "Interrupted tasks can skew apparent overrun.",
        ),
        forbidden_interpretations=(
            "Do not describe this as optimistic personality.",
            "Do not describe this as unrealistic identity.",
        ),
        settings_attr="AURORA_METACOG_PROXY_COMPLETION_VS_ESTIMATE_DELTA_SIGN",
    ),
}


PROCESS_SCAFFOLDING_TEMPLATES: tuple[LanguageTemplate, ...] = (
    LanguageTemplate(
        template_id="mc_process_time_more_support_factors",
        kind="process_scaffolding",
        dim="time_estimation_bias",
        direction="more_support",
        template="metacognition.process_template_time_more_support",
    ),
    LanguageTemplate(
        template_id="mc_process_time_more_support_pattern",
        kind="process_scaffolding",
        dim="time_estimation_bias",
        direction="more_support",
        template="metacognition.process_template_time_more_support_pattern",
    ),
    LanguageTemplate(
        template_id="mc_process_time_less_support_buffer",
        kind="process_scaffolding",
        dim="time_estimation_bias",
        direction="less_support",
        template="metacognition.process_template_time_less_support",
    ),
    LanguageTemplate(
        template_id="mc_process_completion_more_support",
        kind="process_scaffolding",
        dim="completion_bias",
        direction="more_support",
        template="metacognition.process_template_completion_more_support",
    ),
    LanguageTemplate(
        template_id="mc_process_completion_less_support",
        kind="process_scaffolding",
        dim="completion_bias",
        direction="less_support",
        template="metacognition.process_template_completion_less_support",
    ),
    LanguageTemplate(
        template_id="mc_process_mastery_more_support",
        kind="process_scaffolding",
        dim="mastery_bias",
        direction="more_support",
        template="metacognition.process_template_mastery_more_support",
    ),
    LanguageTemplate(
        template_id="mc_process_mastery_less_support",
        kind="process_scaffolding",
        dim="mastery_bias",
        direction="less_support",
        template="metacognition.process_template_mastery_less_support",
    ),
    LanguageTemplate(
        template_id="mc_process_cross_dim_repeat",
        kind="process_scaffolding",
        dim="shared",
        direction="repeat_pattern",
        template="metacognition.process_template_cross_dim_repeat",
    ),
)


DASHBOARD_LANGUAGE_TEMPLATES: tuple[LanguageTemplate, ...] = (
    LanguageTemplate(
        template_id="mc_dashboard_time_more_support",
        kind="dashboard_body",
        dim="time_estimation_bias",
        direction="more_support",
        template="metacognition.dashboard_template_time_more_support",
    ),
    LanguageTemplate(
        template_id="mc_dashboard_time_less_support",
        kind="dashboard_body",
        dim="time_estimation_bias",
        direction="less_support",
        template="metacognition.dashboard_template_time_less_support",
    ),
    LanguageTemplate(
        template_id="mc_dashboard_completion_more_support",
        kind="dashboard_body",
        dim="completion_bias",
        direction="more_support",
        template="metacognition.dashboard_template_completion_more_support",
    ),
    LanguageTemplate(
        template_id="mc_dashboard_completion_less_support",
        kind="dashboard_body",
        dim="completion_bias",
        direction="less_support",
        template="metacognition.dashboard_template_completion_less_support",
    ),
    LanguageTemplate(
        template_id="mc_dashboard_mastery_more_support",
        kind="dashboard_body",
        dim="mastery_bias",
        direction="more_support",
        template="metacognition.dashboard_template_mastery_more_support",
    ),
    LanguageTemplate(
        template_id="mc_dashboard_mastery_less_support",
        kind="dashboard_body",
        dim="mastery_bias",
        direction="less_support",
        template="metacognition.dashboard_template_mastery_less_support",
    ),
    LanguageTemplate(
        template_id="mc_dashboard_insufficient",
        kind="dashboard_body",
        dim="shared",
        direction="insufficient",
        template="metacognition.dashboard_insufficient",
    ),
    LanguageTemplate(
        template_id="mc_dashboard_trend_improving",
        kind="dashboard_trend",
        dim="shared",
        direction="improving",
        template="metacognition.dashboard_trend_improving",
    ),
    LanguageTemplate(
        template_id="mc_dashboard_trend_stable",
        kind="dashboard_trend",
        dim="shared",
        direction="stable",
        template="metacognition.dashboard_trend_stable",
    ),
    LanguageTemplate(
        template_id="mc_dashboard_trend_worsening",
        kind="dashboard_trend",
        dim="shared",
        direction="worsening",
        template="metacognition.dashboard_trend_worsening",
    ),
)


DASHBOARD_LANGUAGE_TEMPLATES: tuple[LanguageTemplate, ...] = (
    LanguageTemplate(
        template_id="mc_dashboard_time_more_support",
        kind="dashboard_body",
        dim="time_estimation_bias",
        direction="more_support",
        template="你过去 {sample_size} 次对完成时间估得偏乐观 {display_value} 小时。",
    ),
    LanguageTemplate(
        template_id="mc_dashboard_time_less_support",
        kind="dashboard_body",
        dim="time_estimation_bias",
        direction="less_support",
        template="你过去 {sample_size} 次通常比自己的时间预估更早完成 {display_value} 小时。",
    ),
    LanguageTemplate(
        template_id="mc_dashboard_completion_more_support",
        kind="dashboard_body",
        dim="completion_bias",
        direction="more_support",
        template="你过去 {sample_size} 次对完成比例估得偏乐观 {display_value} 个百分点。",
    ),
    LanguageTemplate(
        template_id="mc_dashboard_completion_less_support",
        kind="dashboard_body",
        dim="completion_bias",
        direction="less_support",
        template="你过去 {sample_size} 次对完成比例估得偏保守 {display_value} 个百分点。",
    ),
    LanguageTemplate(
        template_id="mc_dashboard_mastery_more_support",
        kind="dashboard_body",
        dim="mastery_bias",
        direction="more_support",
        template="你过去 {sample_size} 次对掌握度估得偏乐观 {display_value} 个百分点。",
    ),
    LanguageTemplate(
        template_id="mc_dashboard_mastery_less_support",
        kind="dashboard_body",
        dim="mastery_bias",
        direction="less_support",
        template="你过去 {sample_size} 次对掌握度估得偏保守 {display_value} 个百分点。",
    ),
    LanguageTemplate(
        template_id="mc_dashboard_insufficient",
        kind="dashboard_body",
        dim="shared",
        direction="insufficient",
        template="样本不足，继续观察中。",
    ),
    LanguageTemplate(
        template_id="mc_dashboard_trend_improving",
        kind="dashboard_trend",
        dim="shared",
        direction="improving",
        template="最近几周正在变稳。",
    ),
    LanguageTemplate(
        template_id="mc_dashboard_trend_stable",
        kind="dashboard_trend",
        dim="shared",
        direction="stable",
        template="最近几周基本稳定。",
    ),
    LanguageTemplate(
        template_id="mc_dashboard_trend_worsening",
        kind="dashboard_trend",
        dim="shared",
        direction="worsening",
        template="最近几周的波动又放大了一些。",
    ),
)


def get_confidence_proxy(proxy_id: str) -> ConfidenceProxyDefinition:
    try:
        return CONFIDENCE_PROXY_REGISTRY[proxy_id]
    except KeyError as exc:
        raise ValueError(f"Unregistered confidence proxy: {proxy_id}") from exc


def ensure_registered_proxies(
    proxy_ids: list[str] | tuple[str, ...],
) -> tuple[str, ...]:
    return tuple(get_confidence_proxy(proxy_id).proxy_id for proxy_id in proxy_ids)


def list_templates(
    *, kind: str, dim: str | None = None, direction: str | None = None
) -> tuple[LanguageTemplate, ...]:
    registry = (
        PROCESS_SCAFFOLDING_TEMPLATES
        if kind == "process_scaffolding"
        else DASHBOARD_LANGUAGE_TEMPLATES
    )
    return tuple(
        item
        for item in registry
        if (dim is None or item.dim == dim or item.dim == "shared")
        and (direction is None or item.direction == direction)
    )


def render_template(template_id: str, locale: str = "zh", **values: Any) -> str:
    for registry in (PROCESS_SCAFFOLDING_TEMPLATES, DASHBOARD_LANGUAGE_TEMPLATES):
        for item in registry:
            if item.template_id == template_id:
                return I18n.t(item.template, locale=locale, **values)
    raise ValueError(f"Unknown metacognition template: {template_id}")


def render_guard_samples(locale: str = "zh") -> tuple[str, ...]:
    samples = []
    for item in PROCESS_SCAFFOLDING_TEMPLATES:
        samples.append(
            I18n.t(item.template, locale=locale, predicted_value="2.0", actual_value="4.0", repeat_count=3)
        )
    for item in DASHBOARD_LANGUAGE_TEMPLATES:
        samples.append(
            I18n.t(item.template, locale=locale, sample_size=10, display_value="2.3")
        )
    return tuple(samples)
