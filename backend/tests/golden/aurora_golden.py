from __future__ import annotations

import json
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from itertools import combinations
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from app.aurora.runtime_v1.service import AuroraRuntimeV1Service
from app.services.checkpoint_nudge_service import CheckpointNudgeService
from app.services.task_stuck_signal_service import TaskStuckPatternAnalyzer
from app.signals.aurora_core_session import AuroraCoreSessionEntryReason

SNAPSHOT_DRIFT_SIMILARITY_THRESHOLD = 0.92
TEMPLATE_REPETITION_SIMILARITY_THRESHOLD = 0.86
TEMPLATE_OPENING_CHAR_COUNT = 14
MIN_TEMPLATE_RUN = 3
MIN_RESPONSE_CHARS = 18
MAX_RESPONSE_CHARS = 260

BANNED_EXPRESSIONS = (
    "作为一个AI",
    "作为 AI",
    "我只是一个",
    "根据系统提示",
    "根据你的输入",
    "亲爱的用户",
    "以下是",
    "首先，其次",
    "如有需要",
    "无法为你",
    "用户画像",
    "检测到风险",
)

INTERNAL_TOKEN_PATTERN = re.compile(
    r"\b("
    r"risk_false_positive|srl_phase|metacog|wake_policy|latent_thread|spine_receipt|"
    r"model_write|state_patch|entry_reason|semantic_value|source_lane|trigger_source|"
    r"checkpoint_state|decision_loop|calibration_result|AURORA\s+PLANNING\s+SIDECAR"
    r")\b",
    re.IGNORECASE,
)
REPEATED_SENTENCE_PUNCTUATION_PATTERN = re.compile(r"[。！？!?]{2,}")


@dataclass(frozen=True)
class GoldenScenario:
    scenario_id: str
    family: str
    kind: str
    title: str
    input: dict[str, Any]
    path: Path


@dataclass(frozen=True)
class QualityIssue:
    scenario_id: str
    check: str
    message: str


@dataclass(frozen=True)
class DriftResult:
    similarity: float
    threshold: float = SNAPSHOT_DRIFT_SIMILARITY_THRESHOLD

    @property
    def drift_score(self) -> float:
        return 1.0 - self.similarity

    @property
    def exceeds_threshold(self) -> bool:
        return self.similarity < self.threshold


class FixedGreetingAuroraRuntime(AuroraRuntimeV1Service):
    def __init__(self, greeting: str) -> None:
        self._fixed_greeting = greeting

    def _daily_greeting(self) -> str:
        return self._fixed_greeting


def load_scenarios(fixtures_dir: Path) -> list[GoldenScenario]:
    scenarios: list[GoldenScenario] = []
    for path in sorted(fixtures_dir.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        scenarios.append(
            GoldenScenario(
                scenario_id=str(raw["id"]),
                family=str(raw["family"]),
                kind=str(raw["kind"]),
                title=str(raw.get("title") or raw["id"]),
                input=dict(raw.get("input") or {}),
                path=path,
            )
        )
    return scenarios


def render_scenario(scenario: GoldenScenario) -> str:
    renderers = {
        "daily_start": _render_daily_start,
        "checkpoint_return": _render_checkpoint_return,
        "core_session_opening": _render_core_session_opening,
        "memory_reference": _render_memory_reference,
        "task_stuck": _render_task_stuck,
        "push_copy": _render_push_copy,
        "correction_reply": _render_correction_reply,
    }
    renderer = renderers.get(scenario.kind)
    if renderer is None:
        raise ValueError(f"No golden renderer for kind={scenario.kind!r}")
    return normalize_snapshot_text(renderer(scenario.input))


def snapshot_path_for(scenario: GoldenScenario, snapshots_dir: Path) -> Path:
    return snapshots_dir / f"{scenario.scenario_id}.txt"


def normalize_snapshot_text(text: str) -> str:
    lines = [" ".join(line.split()) for line in str(text or "").splitlines()]
    return "\n".join(line for line in lines if line).strip()


def update_snapshot(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{normalize_snapshot_text(text)}\n", encoding="utf-8")


def load_snapshot(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Missing golden snapshot: {path}")
    return normalize_snapshot_text(path.read_text(encoding="utf-8"))


def detect_snapshot_drift(expected: str, actual: str) -> DriftResult:
    similarity = SequenceMatcher(None, normalize_snapshot_text(expected), normalize_snapshot_text(actual)).ratio()
    return DriftResult(similarity=similarity)


def collect_quality_issues(scenario: GoldenScenario, response: str) -> list[QualityIssue]:
    text = normalize_snapshot_text(response)
    issues: list[QualityIssue] = []
    for expression in BANNED_EXPRESSIONS:
        if expression in text:
            issues.append(
                QualityIssue(
                    scenario_id=scenario.scenario_id,
                    check="banned_expression",
                    message=f"Contains banned expression: {expression}",
                )
            )
    token_match = INTERNAL_TOKEN_PATTERN.search(text)
    if token_match is not None:
        issues.append(
            QualityIssue(
                scenario_id=scenario.scenario_id,
                check="internal_token",
                message=f"Leaks internal token: {token_match.group(0)}",
            )
        )
    punctuation_match = REPEATED_SENTENCE_PUNCTUATION_PATTERN.search(text)
    if punctuation_match is not None:
        issues.append(
            QualityIssue(
                scenario_id=scenario.scenario_id,
                check="copy_polish",
                message=f"Repeated sentence punctuation: {punctuation_match.group(0)}",
            )
        )
    if len(text) < MIN_RESPONSE_CHARS:
        issues.append(
            QualityIssue(
                scenario_id=scenario.scenario_id,
                check="length_warning",
                message=f"Response is very short: {len(text)} chars",
            )
        )
    if len(text) > MAX_RESPONSE_CHARS:
        issues.append(
            QualityIssue(
                scenario_id=scenario.scenario_id,
                check="length_warning",
                message=f"Response is very long: {len(text)} chars",
            )
        )
    return issues


def find_template_repetition(
    scenarios: list[GoldenScenario],
    responses: dict[str, str],
) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    by_family: dict[str, list[GoldenScenario]] = {}
    for scenario in scenarios:
        by_family.setdefault(scenario.family, []).append(scenario)

    for family, family_scenarios in by_family.items():
        if len(family_scenarios) < MIN_TEMPLATE_RUN:
            continue

        opening_counts: dict[str, list[str]] = {}
        for scenario in family_scenarios:
            text = normalize_snapshot_text(responses[scenario.scenario_id])
            opening = text[:TEMPLATE_OPENING_CHAR_COUNT]
            opening_counts.setdefault(opening, []).append(scenario.scenario_id)
        for opening, ids in opening_counts.items():
            if opening and len(ids) >= MIN_TEMPLATE_RUN:
                issues.append(
                    QualityIssue(
                        scenario_id=",".join(ids),
                        check="template_repetition",
                        message=f"{family} repeats the same opening {opening!r} across {len(ids)} variants",
                    )
                )

        for trio in combinations(family_scenarios, MIN_TEMPLATE_RUN):
            texts = [normalize_snapshot_text(responses[item.scenario_id]) for item in trio]
            similarities = [
                SequenceMatcher(None, left, right).ratio()
                for left, right in combinations(texts, 2)
            ]
            average_similarity = sum(similarities) / len(similarities)
            if average_similarity >= TEMPLATE_REPETITION_SIMILARITY_THRESHOLD:
                ids = ",".join(item.scenario_id for item in trio)
                issues.append(
                    QualityIssue(
                        scenario_id=ids,
                        check="template_repetition",
                        message=(
                            f"{family} variants are too similar "
                            f"({average_similarity:.2f} >= {TEMPLATE_REPETITION_SIMILARITY_THRESHOLD:.2f})"
                        ),
                    )
                )
    return issues


def _render_daily_start(data: dict[str, Any]) -> str:
    service = FixedGreetingAuroraRuntime(str(data["greeting"]))
    plan = SimpleNamespace(subject=data["subject"], name=data.get("plan_name") or data["subject"])
    completion_rate = data.get("completion_rate")
    completion_rate = None if completion_rate is None else float(completion_rate)
    return service._daily_startup_message(
        plan=plan,
        day_index=int(data["day_index"]),
        today_focus=str(data["today_focus"]),
        estimated_minutes=int(data["estimated_minutes"]),
        completion_rate=completion_rate,
        adjustment_reason=str(data["adjustment_reason"]),
        day_recommendation=str(data.get("day_recommendation") or ""),
        display_name=str(data.get("display_name") or ""),
        calendar_note=str(data.get("calendar_note") or ""),
    )


def _render_checkpoint_return(data: dict[str, Any]) -> str:
    service = object.__new__(CheckpointNudgeService)
    plan = SimpleNamespace(name=data["plan_name"])
    opening, _variant = service._checkpoint_opening(
        plan=plan,
        checkpoint_day=int(data["checkpoint_day"]),
        checkpoint_description=str(data.get("checkpoint_description") or ""),
        previous_summary=str(data.get("previous_summary") or ""),
        open_threads=list(data.get("open_threads") or []),
        unclosed_questions=list(data.get("unclosed_questions") or []),
        progress_facts=list(data.get("progress_facts") or []),
        previous_openings=list(data.get("previous_openings") or []),
    )
    return opening


def _render_core_session_opening(data: dict[str, Any]) -> str:
    reason = AuroraCoreSessionEntryReason(
        trigger_source=str(data["trigger_source"]),
        observed_signals=list(data.get("observed_signals") or []),
        suggested_agenda_preview=list(data.get("suggested_agenda_preview") or []),
        why_now=str(data.get("why_now") or ""),
        estimated_minutes=int(data.get("estimated_minutes") or 3),
    )
    agenda = "；".join(reason.suggested_agenda_preview[:3])
    agenda_tail = f"这次我会先{agenda}。" if agenda else ""
    return f"{reason.opening_message()}{agenda_tail}"


def _render_memory_reference(data: dict[str, Any]) -> str:
    memory = str(data["memory"])
    current = str(data["current_need"])
    next_step = str(data["next_step"])
    confidence = float(data.get("confidence", 1.0))
    confirmed = bool(data.get("user_confirmed", False))
    source = str(data.get("source_label") or "你告诉我的")
    time_ago = str(data.get("time_ago") or "之前")
    if confirmed:
        return f"{time_ago}你提到的「{memory}」我接上了。现在先围绕{current}走，不重新铺开；下一步做{next_step}。"
    if confidence < 0.7:
        return f"我印象里{time_ago}有个线索和「{memory}」有关，不过这点还需要你确认。先把它当作参考，我们从{next_step}开始。"
    return f"结合{source}那条线索：「{memory}」，这轮先服务于{current}。我会把下一步收在{next_step}，不额外加负担。"


def _render_task_stuck(data: dict[str, Any]) -> str:
    pattern = {
        "description": str(data["description"]),
        "task_titles": list(data.get("task_titles") or []),
        "dominant_issue": str(data.get("dominant_issue") or "stuck"),
    }
    payload = TaskStuckPatternAnalyzer.build_micro_session_payload(
        pattern,
        next_task_title=str(data.get("next_task_title") or ""),
    )
    reason = AuroraCoreSessionEntryReason.from_dict(payload["entry_reason"])
    opening = reason.opening_message() if reason else str(data["description"])
    changes = list(payload["calibration_result_preview"]["next_changes"])
    return f"{opening}{changes[0]}；{changes[1]}。你可以直接拒绝，我就先按原计划安静陪跑。"


def _render_push_copy(data: dict[str, Any]) -> str:
    return f"{data['lead']} {data['body']} {data['action']}"


def _render_correction_reply(data: dict[str, Any]) -> str:
    correction_type = str(data["correction_type"])
    original = str(data["original_assumption"])
    correction = str(data["user_correction"])
    next_change = str(data["next_change"])
    if correction_type == "memory_denial":
        return f"收到，这条我先撤回：不是「{original}」。后面我会按「{correction}」来接，不再直接引用刚才那条记忆。"
    return f"好，我把刚才的语气收回来。你要的是「{correction}」，不是「{original}」。接下来{next_change}。"
