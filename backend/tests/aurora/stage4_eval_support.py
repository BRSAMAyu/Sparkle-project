from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from math import ceil
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping
from uuid import UUID

from app.aurora.schemas import SignalSnapshot

_POLICY_VERSION = "aurora_policy@v1.0"
_SCENARIO_PACK_ID = "exam_prep_14d@v1.0"
_BENCHMARK_USER_ID = UUID("11111111-1111-1111-1111-111111111111")
_BENCHMARK_TIME = datetime(2026, 4, 19, 12, 0, 0)


@dataclass(frozen=True)
class Stage4BenchmarkCase:
    """One evaluation case used by the Stage 4 corpora."""

    case_id: str
    category: str
    routing_target: str
    trigger_point: str
    current_node: str
    snapshot: SignalSnapshot | None
    candidate_node: str | None = None
    expected_status: str = "ok"
    expected_decision_types: tuple[str, ...] = ("stay", "transition", "no_op")
    notes: str = ""


@dataclass(frozen=True)
class TierTaggedBenchmarkEvent:
    """Normalized event shape that tests and dashboards can consume."""

    corpus_id: str
    case_id: str
    tier: str
    trigger_point: str
    routing_target: str
    status: str
    latency_ms: float
    decision_type: str
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Stage4CorpusPlaceholder:
    corpus_id: str
    minimum_size: int
    distribution: Mapping[str, int]
    purpose: str
    status: str = "placeholder"


@dataclass(frozen=True)
class P1GuardrailViolation:
    file_path: str
    line_no: int
    import_stmt: str
    message: str


@dataclass(frozen=True)
class P1GuardrailReport:
    mode: str
    checked_files: tuple[str, ...]
    missing_targets: tuple[str, ...]
    violations: tuple[P1GuardrailViolation, ...]

    @property
    def has_findings(self) -> bool:
        return bool(self.violations)

    def render(self) -> str:
        headline = f"P1 guardrail ({self.mode}) checked {len(self.checked_files)} files"
        if not self.violations:
            return headline + " and found no violations."
        lines = [headline + f" and found {len(self.violations)} violations:"]
        for violation in self.violations:
            lines.append(f"- {violation.file_path}:{violation.line_no} {violation.message} [{violation.import_stmt}]")
        return "\n".join(lines)


BenchmarkRunner = Callable[[Stage4BenchmarkCase], TierTaggedBenchmarkEvent | Mapping[str, Any]]


def _snapshot(
    snapshot_hash: str,
    user_message: str | None,
    *,
    core_extra: Mapping[str, Any] | None = None,
    enhanced_extra: Mapping[str, Any] | None = None,
    optional_extra: Mapping[str, Any] | None = None,
) -> SignalSnapshot:
    core_signals: dict[str, Any] = {}
    if user_message is not None:
        core_signals["user_message"] = user_message
    if core_extra:
        core_signals.update(core_extra)
    return SignalSnapshot(
        snapshot_hash=snapshot_hash,
        user_id=_BENCHMARK_USER_ID,
        collected_at=_BENCHMARK_TIME,
        scenario_pack_id=_SCENARIO_PACK_ID,
        policy_version=_POLICY_VERSION,
        core_signals=core_signals,
        enhanced_signals=dict(enhanced_extra or {}),
        optional_signals=dict(optional_extra or {}),
        total_tokens=900,
        budget_limit=4000,
    )


def build_corpus_v1_cases() -> tuple[Stage4BenchmarkCase, ...]:
    """Materialized Stage 4 Corpus V1 content.

    Coverage contract from the dispatch plan:
    - casual direct question
    - workflow-eligible planning request
    - task-assistant-eligible request
    - escalation-trigger cases
    - no-op / fallback / miss cases
    """

    direct_cases = (
        Stage4BenchmarkCase(
            case_id="v1_direct_knowledge",
            category="casual_direct",
            routing_target="direct",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=_snapshot("ss_v1_direct_01", "热力学第二定律和熵增是不是一回事？"),
        ),
        Stage4BenchmarkCase(
            case_id="v1_direct_chat",
            category="casual_direct",
            routing_target="direct",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=_snapshot("ss_v1_direct_02", "今天状态一般，先陪我简单聊两句。"),
        ),
        Stage4BenchmarkCase(
            case_id="v1_direct_fact",
            category="casual_direct",
            routing_target="direct",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=_snapshot("ss_v1_direct_03", "帮我解释一下数据库索引的作用，用最短的话。"),
        ),
        Stage4BenchmarkCase(
            case_id="v1_direct_checkin",
            category="casual_direct",
            routing_target="direct",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=_snapshot("ss_v1_direct_04", "我刚学了二十分钟，状态还行。"),
        ),
    )
    workflow_cases = (
        Stage4BenchmarkCase(
            case_id="v1_workflow_plan_week",
            category="workflow_plan",
            routing_target="workflow",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=_snapshot("ss_v1_workflow_01", "帮我把这周复习计划拆成每天三步。"),
            candidate_node="day4_deep_analysis",
        ),
        Stage4BenchmarkCase(
            case_id="v1_workflow_replan_conflict",
            category="workflow_plan",
            routing_target="workflow",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=_snapshot(
                "ss_v1_workflow_02",
                "考试提前了，原来的备考节奏不行了，帮我重排。",
                core_extra={"commitment_conflict": "deadline_moved_up"},
            ),
            candidate_node="day4_deep_analysis",
        ),
        Stage4BenchmarkCase(
            case_id="v1_workflow_goal_clarify",
            category="workflow_plan",
            routing_target="workflow",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=_snapshot("ss_v1_workflow_03", "我想用 14 天把数据库真正补起来，先帮我定路径。"),
            candidate_node="day4_deep_analysis",
        ),
        Stage4BenchmarkCase(
            case_id="v1_workflow_checkpoint",
            category="workflow_plan",
            routing_target="workflow",
            trigger_point="pre-node-routing",
            current_node="day5_error_repair",
            snapshot=_snapshot("ss_v1_workflow_04", "我想重新看一下接下来 5 天的大方向和 checkpoint。"),
            candidate_node="day6_targeted_drill",
        ),
    )
    task_assistant_cases = (
        Stage4BenchmarkCase(
            case_id="v1_task_assistant_execute_now",
            category="task_assistant",
            routing_target="task_assistant",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=_snapshot("ss_v1_task_01", "我现在就开始做这一章，第一步你直接带我进入。"),
        ),
        Stage4BenchmarkCase(
            case_id="v1_task_assistant_current_card",
            category="task_assistant",
            routing_target="task_assistant",
            trigger_point="pre-node-routing",
            current_node="day5_error_repair",
            snapshot=_snapshot(
                "ss_v1_task_02",
                "不用重做计划，我就想把当前这张任务卡顺下来。",
                optional_extra={"task_card_id": "task-card-02"},
            ),
        ),
        Stage4BenchmarkCase(
            case_id="v1_task_assistant_drill",
            category="task_assistant",
            routing_target="task_assistant",
            trigger_point="pre-node-routing",
            current_node="day6_targeted_drill",
            snapshot=_snapshot("ss_v1_task_03", "你直接陪我做这一轮 targeted drill。"),
        ),
        Stage4BenchmarkCase(
            case_id="v1_task_assistant_warm_start",
            category="task_assistant",
            routing_target="task_assistant",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=_snapshot("ss_v1_task_04", "现在只需要把我带进任务，不要再讲大道理。"),
        ),
    )
    escalation_cases = (
        Stage4BenchmarkCase(
            case_id="v1_escalation_explicit_planning_request",
            category="escalation",
            routing_target="workflow",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=_snapshot("ss_v1_escalation_01", "别直答了，帮我规划成一个真正能执行的流程。"),
            notes="approved trigger: explicit planning request",
        ),
        Stage4BenchmarkCase(
            case_id="v1_escalation_structural_turns",
            category="escalation",
            routing_target="workflow",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=_snapshot(
                "ss_v1_escalation_02",
                "那如果我把这三块拆开，你觉得顺序怎么定？",
                optional_extra={"structural_topic_turns": 2},
            ),
            notes="approved trigger: 2+ structural-topic turns",
        ),
        Stage4BenchmarkCase(
            case_id="v1_escalation_frustration_signal",
            category="escalation",
            routing_target="workflow",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=_snapshot(
                "ss_v1_escalation_03",
                "我真的有点做不下去了，这样聊完全帮不到我。",
                enhanced_extra={"frustration_signal": True},
            ),
            notes="approved trigger: frustration/blockage signal",
        ),
        Stage4BenchmarkCase(
            case_id="v1_escalation_combined",
            category="escalation",
            routing_target="workflow",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=_snapshot(
                "ss_v1_escalation_04",
                "连续两轮都没说到点上，还是帮我把执行路径重新搭一下。",
                optional_extra={"structural_topic_turns": 2},
                enhanced_extra={"frustration_signal": True},
            ),
        ),
    )
    fallback_cases = (
        Stage4BenchmarkCase(
            case_id="v1_fallback_missing_snapshot",
            category="fallback_or_miss",
            routing_target="direct",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=None,
            expected_status="fallback",
            expected_decision_types=("no_op",),
        ),
        Stage4BenchmarkCase(
            case_id="v1_fallback_sparse_signals",
            category="fallback_or_miss",
            routing_target="direct",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=_snapshot("ss_v1_fallback_02", None),
            expected_status="ok",
            notes="miss, not failure",
        ),
        Stage4BenchmarkCase(
            case_id="v1_fallback_stay_on_low_materiality",
            category="fallback_or_miss",
            routing_target="direct",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=_snapshot("ss_v1_fallback_03", "嗯，先这样。"),
            expected_status="ok",
        ),
        Stage4BenchmarkCase(
            case_id="v1_fallback_partner_stale",
            category="fallback_or_miss",
            routing_target="direct",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=_snapshot(
                "ss_v1_fallback_04",
                "今天先不展开。",
                optional_extra={"partner_report": {"status": "stale"}},
            ),
            expected_status="ok",
        ),
    )
    corpus = direct_cases + workflow_cases + task_assistant_cases + escalation_cases + fallback_cases
    assert len(corpus) == 20
    return corpus


def build_corpus_v2_cases() -> tuple[Stage4BenchmarkCase, ...]:
    """Materialized Stage 4 Corpus V2 content (Agent H / WS-B.2).

    Coverage contract from the dispatch plan:
    - routing_mode assignment (basic classification)
    - mid-flight upgrades (escalation from direct to workflow)
    - flags-off stability

    Distribution: 10 direct, 10 workflow (incl. escalation), 10 task_assistant.
    Minimum size: 30.
    """

    # ------------------------------------------------------------------
    # Direct (10): no escalation triggers, no planning/task markers
    # ------------------------------------------------------------------
    v2_direct_cases = (
        Stage4BenchmarkCase(
            case_id="v2_direct_simple_question",
            category="corpus_v2_direct",
            routing_target="direct",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=_snapshot("ss_v2_direct_01", "什么是牛顿第三定律？"),
        ),
        Stage4BenchmarkCase(
            case_id="v2_direct_casual_chat",
            category="corpus_v2_direct",
            routing_target="direct",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=_snapshot("ss_v2_direct_02", "今天天气不错。"),
        ),
        Stage4BenchmarkCase(
            case_id="v2_direct_acknowledgment",
            category="corpus_v2_direct",
            routing_target="direct",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=_snapshot("ss_v2_direct_03", "好的，我明白了。"),
        ),
        Stage4BenchmarkCase(
            case_id="v2_direct_brief_followup",
            category="corpus_v2_direct",
            routing_target="direct",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=_snapshot("ss_v2_direct_04", "那第二点呢？"),
        ),
        Stage4BenchmarkCase(
            case_id="v2_direct_status_report",
            category="corpus_v2_direct",
            routing_target="direct",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=_snapshot("ss_v2_direct_05", "我刚学了一章，状态还行。"),
        ),
        Stage4BenchmarkCase(
            case_id="v2_direct_simple_definition",
            category="corpus_v2_direct",
            routing_target="direct",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=_snapshot("ss_v2_direct_06", "什么是递归？"),
        ),
        Stage4BenchmarkCase(
            case_id="v2_direct_agreement",
            category="corpus_v2_direct",
            routing_target="direct",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=_snapshot("ss_v2_direct_07", "你说得对。"),
        ),
        Stage4BenchmarkCase(
            case_id="v2_direct_single_structural_turn",
            category="corpus_v2_direct",
            routing_target="direct",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=_snapshot(
                "ss_v2_direct_08",
                "帮我看看这个思路对不对。",
                optional_extra={"structural_topic_turns": 1},
            ),
            notes="1 structural turn — below escalation threshold",
        ),
        Stage4BenchmarkCase(
            case_id="v2_direct_simple_calculation",
            category="corpus_v2_direct",
            routing_target="direct",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=_snapshot("ss_v2_direct_09", "3×7等于多少？"),
        ),
        Stage4BenchmarkCase(
            case_id="v2_direct_mild_frustration_no_escalation",
            category="corpus_v2_direct",
            routing_target="direct",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=_snapshot("ss_v2_direct_10", "有点难，但还能继续。"),
            notes="mild difficulty but no blockage signal",
        ),
    )

    # ------------------------------------------------------------------
    # Workflow (10): standard + escalation-triggered mid-flight upgrades
    # ------------------------------------------------------------------
    v2_workflow_cases = (
        Stage4BenchmarkCase(
            case_id="v2_workflow_standard_plan",
            category="corpus_v2_workflow",
            routing_target="workflow",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=_snapshot("ss_v2_workflow_01", "帮我制定两周的复习计划。"),
        ),
        Stage4BenchmarkCase(
            case_id="v2_workflow_replan_adjust",
            category="corpus_v2_workflow",
            routing_target="workflow",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=_snapshot("ss_v2_workflow_02", "计划需要调整，时间不够了，帮我重排。"),
        ),
        Stage4BenchmarkCase(
            case_id="v2_workflow_goal_breakdown",
            category="corpus_v2_workflow",
            routing_target="workflow",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=_snapshot("ss_v2_workflow_03", "把这个目标拆成可执行的步骤。"),
        ),
        Stage4BenchmarkCase(
            case_id="v2_workflow_escalation_explicit",
            category="corpus_v2_workflow_escalation",
            routing_target="workflow",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=_snapshot("ss_v2_workflow_04", "别直答了，帮我做成方案一步步跟着做。"),
            notes="WS-B.2 escalation: explicit planning request",
        ),
        Stage4BenchmarkCase(
            case_id="v2_workflow_escalation_structural_2",
            category="corpus_v2_workflow_escalation",
            routing_target="workflow",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=_snapshot(
                "ss_v2_workflow_05",
                "继续刚才的讨论。",
                optional_extra={"structural_topic_turns": 2},
            ),
            notes="WS-B.2 escalation: 2 structural-topic turns",
        ),
        Stage4BenchmarkCase(
            case_id="v2_workflow_escalation_structural_3",
            category="corpus_v2_workflow_escalation",
            routing_target="workflow",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=_snapshot(
                "ss_v2_workflow_06",
                "还有呢？",
                optional_extra={"structural_topic_turns": 3},
            ),
            notes="WS-B.2 escalation: 3 structural-topic turns",
        ),
        Stage4BenchmarkCase(
            case_id="v2_workflow_escalation_frustration_text",
            category="corpus_v2_workflow_escalation",
            routing_target="workflow",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=_snapshot("ss_v2_workflow_07", "做不下去了，完全帮不到我。"),
            notes="WS-B.2 escalation: frustration text markers",
        ),
        Stage4BenchmarkCase(
            case_id="v2_workflow_escalation_frustration_signal",
            category="corpus_v2_workflow_escalation",
            routing_target="workflow",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=_snapshot(
                "ss_v2_workflow_08",
                "这条路走不通了。",
                enhanced_extra={"frustration_signal": True},
            ),
            notes="WS-B.2 escalation: enhanced frustration_signal",
        ),
        Stage4BenchmarkCase(
            case_id="v2_workflow_escalation_combined",
            category="corpus_v2_workflow_escalation",
            routing_target="workflow",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=_snapshot(
                "ss_v2_workflow_09",
                "别只是回答了，我需要一个能执行的方案。",
                optional_extra={"structural_topic_turns": 2},
                enhanced_extra={"frustration_signal": True},
            ),
            notes="WS-B.2 escalation: combined triggers",
        ),
        Stage4BenchmarkCase(
            case_id="v2_workflow_escalation_text_plan",
            category="corpus_v2_workflow_escalation",
            routing_target="workflow",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=_snapshot("ss_v2_workflow_10", "别直接给答案了，我需要一个跟着做的方案。"),
            notes="WS-B.2 escalation: explicit planning (alternate text)",
        ),
    )

    # ------------------------------------------------------------------
    # Task Assistant (10): task-specific requests, no escalation
    # ------------------------------------------------------------------
    v2_task_assistant_cases = (
        Stage4BenchmarkCase(
            case_id="v2_task_execute_now",
            category="corpus_v2_task_assistant",
            routing_target="task_assistant",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=_snapshot("ss_v2_task_01", "我现在就开始做这一章，直接带我进入。"),
        ),
        Stage4BenchmarkCase(
            case_id="v2_task_current_card",
            category="corpus_v2_task_assistant",
            routing_target="task_assistant",
            trigger_point="pre-node-routing",
            current_node="day5_error_repair",
            snapshot=_snapshot(
                "ss_v2_task_02",
                "不用重做计划，我就想把当前这张任务卡顺下来。",
                optional_extra={"task_card_id": "task-card-02"},
            ),
        ),
        Stage4BenchmarkCase(
            case_id="v2_task_drill",
            category="corpus_v2_task_assistant",
            routing_target="task_assistant",
            trigger_point="pre-node-routing",
            current_node="day6_targeted_drill",
            snapshot=_snapshot("ss_v2_task_03", "你直接陪我做这一轮 targeted drill。"),
        ),
        Stage4BenchmarkCase(
            case_id="v2_task_warm_start",
            category="corpus_v2_task_assistant",
            routing_target="task_assistant",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=_snapshot("ss_v2_task_04", "现在只需要把我带进任务，不要再讲大道理。"),
        ),
        Stage4BenchmarkCase(
            case_id="v2_task_step_start",
            category="corpus_v2_task_assistant",
            routing_target="task_assistant",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=_snapshot("ss_v2_task_05", "开始做这个任务。"),
        ),
        Stage4BenchmarkCase(
            case_id="v2_task_no_preach",
            category="corpus_v2_task_assistant",
            routing_target="task_assistant",
            trigger_point="pre-node-routing",
            current_node="day4_deep_analysis",
            snapshot=_snapshot("ss_v2_task_06", "别光讲道理，直接带我进入任务。"),
        ),
        Stage4BenchmarkCase(
            case_id="v2_task_card_reference",
            category="corpus_v2_task_assistant",
            routing_target="task_assistant",
            trigger_point="pre-node-routing",
            current_node="day5_error_repair",
            snapshot=_snapshot(
                "ss_v2_task_07",
                "当前任务下一步是什么？",
                optional_extra={"task_card_id": "task-card-05"},
            ),
        ),
        Stage4BenchmarkCase(
            case_id="v2_task_direct_guide",
            category="corpus_v2_task_assistant",
            routing_target="task_assistant",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=_snapshot("ss_v2_task_08", "直接带我进入这一章的练习。"),
        ),
        Stage4BenchmarkCase(
            case_id="v2_task_drill_session",
            category="corpus_v2_task_assistant",
            routing_target="task_assistant",
            trigger_point="pre-node-routing",
            current_node="day6_targeted_drill",
            snapshot=_snapshot("ss_v2_task_09", "陪我做 drill，从第一步开始。"),
        ),
        Stage4BenchmarkCase(
            case_id="v2_task_step_complete",
            category="corpus_v2_task_assistant",
            routing_target="task_assistant",
            trigger_point="pre-node-routing",
            current_node="day3_execution",
            snapshot=_snapshot("ss_v2_task_10", "当前任务做完了，带我进入下一步。"),
        ),
    )

    corpus = v2_direct_cases + v2_workflow_cases + v2_task_assistant_cases
    assert len(corpus) == 30
    return corpus


def build_stage4_corpus_placeholders() -> tuple[Stage4CorpusPlaceholder, ...]:
    return (
        Stage4CorpusPlaceholder(
            corpus_id="Corpus V2",
            minimum_size=30,
            distribution={"direct": 10, "workflow": 10, "task_assistant": 10},
            purpose="routing_mode assignment, mid-flight upgrades, flags-off stability (MATERIALIZED)",
            status="materialized",
        ),
        Stage4CorpusPlaceholder(
            corpus_id="Corpus V3",
            minimum_size=15,
            distribution={"learning": 3, "training": 3, "error_fix": 3, "reflection": 3, "planning": 3},
            purpose="TaskGuidance quality across human-guide and AI-guide surfaces",
        ),
        Stage4CorpusPlaceholder(
            corpus_id="Corpus V4",
            minimum_size=100,
            distribution={"direct": 30, "workflow": 30, "task_assistant": 30, "boundary": 10},
            purpose="activation-prep replay coverage and Stage 3 stability validation",
        ),
    )


def coerce_tier_tagged_event(
    case: Stage4BenchmarkCase,
    raw: TierTaggedBenchmarkEvent | Mapping[str, Any],
    *,
    corpus_id: str = "Corpus V1",
) -> TierTaggedBenchmarkEvent:
    if isinstance(raw, TierTaggedBenchmarkEvent):
        return raw
    return TierTaggedBenchmarkEvent(
        corpus_id=str(raw.get("corpus_id") or corpus_id),
        case_id=str(raw.get("case_id") or case.case_id),
        tier=str(raw.get("tier") or "inline"),
        trigger_point=str(raw.get("trigger_point") or case.trigger_point),
        routing_target=str(raw.get("routing_target") or case.routing_target),
        status=str(raw.get("status") or case.expected_status),
        latency_ms=float(raw.get("latency_ms") or 0.0),
        decision_type=str(raw.get("decision_type") or "unknown"),
        metadata=dict(raw.get("metadata") or {}),
    )


def run_corpus_v1_with_runner(runner: BenchmarkRunner) -> tuple[TierTaggedBenchmarkEvent, ...]:
    return tuple(coerce_tier_tagged_event(case, runner(case)) for case in build_corpus_v1_cases())


def summarize_tier_tagged_events(events: Iterable[TierTaggedBenchmarkEvent]) -> dict[str, Any]:
    items = tuple(events)
    latencies = sorted(event.latency_ms for event in items)
    if latencies:
        p95_index = max(0, ceil(len(latencies) * 0.95) - 1)
        p95_latency_ms = latencies[p95_index]
    else:
        p95_latency_ms = 0.0

    by_tier: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for event in items:
        by_tier[event.tier] = by_tier.get(event.tier, 0) + 1
        by_status[event.status] = by_status.get(event.status, 0) + 1
    return {
        "total": len(items),
        "by_tier": by_tier,
        "by_status": by_status,
        "p95_latency_ms": p95_latency_ms,
    }


def build_p1_guardrail_report(repo_root: Path | None = None) -> P1GuardrailReport:
    """Hard-fail scan for obvious cross-tier seam violations.

    Stage 4 posture after audit v3 requires this guardrail to fail tests/CI
    whenever a forbidden cross-tier import reappears.
    """

    root = repo_root or Path(__file__).resolve().parents[3]
    inline_paths = [
        root / "backend/app/aurora/engine.py",
        *sorted((root / "backend/app/aurora/decision_fns").glob("*.py")),
    ]
    nearline_candidates = [
        root / "backend/app/aurora/tasks.py",
        root / "backend/app/task_guidance",
        root / "backend/app/task_assistant",
    ]
    long_horizon_candidates = [root / "backend/app/learning"]

    checked_files: list[str] = []
    missing_targets: list[str] = []
    violations: list[P1GuardrailViolation] = []

    def _iter_py_files(path: Path) -> Iterable[Path]:
        if path.is_file():
            yield path
        elif path.is_dir():
            yield from sorted(path.rglob("*.py"))
        else:
            missing_targets.append(str(path))

    inline_forbidden = (
        "from app.task_guidance",
        "import app.task_guidance",
        "from app.task_assistant",
        "import app.task_assistant",
        "from app.learning",
        "import app.learning",
    )
    deferred_forbidden = (
        "from app.aurora.engine",
        "import app.aurora.engine",
        "from app.aurora.decision_fns",
        "import app.aurora.decision_fns",
        "from app.orchestration",
        "import app.orchestration",
    )

    def _scan(files: Iterable[Path], forbidden_prefixes: tuple[str, ...], message: str) -> None:
        for file_path in files:
            checked_files.append(str(file_path))
            for line_no, line in enumerate(file_path.read_text().splitlines(), start=1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                for prefix in forbidden_prefixes:
                    if stripped.startswith(prefix):
                        violations.append(
                            P1GuardrailViolation(
                                file_path=str(file_path.relative_to(root)),
                                line_no=line_no,
                                import_stmt=stripped,
                                message=message,
                            )
                        )

    _scan(inline_paths, inline_forbidden, "inline tier may not import nearline/long-horizon implementation modules")
    _scan(
        [file for path in nearline_candidates for file in _iter_py_files(path)],
        deferred_forbidden,
        "nearline tier must communicate through primitives / prior_outputs, not inline implementations",
    )
    _scan(
        [file for path in long_horizon_candidates for file in _iter_py_files(path)],
        deferred_forbidden,
        "long-horizon tier must communicate through persisted primitives, not inline implementations",
    )

    return P1GuardrailReport(
        mode="hard-fail",
        checked_files=tuple(sorted(set(checked_files))),
        missing_targets=tuple(sorted(set(missing_targets))),
        violations=tuple(violations),
    )
