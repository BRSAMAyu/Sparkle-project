"""
Core: execution
Phase: reflect
Stage: P1-1 Causal Timeline UI — TimelineCardRenderer

Converts CausalTrace data into user-facing timeline cards.
Two modes: compact (1-line summary) and expanded (full evidence chain).
Supports user correction actions that feed back into CausalTrace.

User-visible: "为什么给我这个任务" → 可理解的因果卡片
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ── Card Types ──────────────────────────────────────────────────────

@dataclass
class TimelineCard:
    """A user-facing causal timeline card."""
    card_id: str
    trace_id: str
    mode: str                           # "compact" | "expanded"
    headline: str                       # e.g. "根据你的学习进度调整了任务难度"
    summary: str                        # 1-2 sentence explanation
    evidence_chain: list[dict[str, Any]]   # signal → policy → directive → outcome
    user_actions: list[dict[str, str]]     # {"action": "correct", "label": "这个判断不对"}
    timestamp: str
    card_type: str = "causal"           # "causal" | "self_correction" | "divine_moment"

    def to_dict(self) -> dict[str, Any]:
        return {
            "card_id": self.card_id,
            "trace_id": self.trace_id,
            "mode": self.mode,
            "headline": self.headline,
            "summary": self.summary,
            "evidence_chain": self.evidence_chain,
            "user_actions": self.user_actions,
            "timestamp": self.timestamp,
            "card_type": self.card_type,
        }


# ── Headline Templates ─────────────────────────────────────────────

_HEADLINE_MAP: dict[str, dict[str, str]] = {
    "task_granularity_fit": {
        "recent_task_too_large": "你的任务有点大，帮你拆小了",
        "default": "根据任务完成情况调整了任务粒度",
    },
    "knowledge_transfer": {
        "transfer_failure": "检测到学习卡壳，换了更适合的方法",
        "default": "根据学习效果调整了策略",
    },
    "goal_mode": {
        "exam_rescue_detected": "检测到你正在备考，启用了冲刺模式",
        "default": "识别到你的目标，调整了规划策略",
    },
    "growth_momentum": {
        "momentum_high": "你的学习状态很好，保持住",
        "momentum_stalled": "学习节奏有点慢，帮你调整一下",
        "default": "根据学习节奏调整了任务安排",
    },
    "recall_needed": {
        "undigested_material": "有份资料还没消化完，要不要看看？",
        "task_not_started": "任务还没开始，需要帮忙吗？",
        "task_missed": "你错过了一个任务，帮你重新安排",
        "pre_exam_silence": "考前太安静了，要不要快速复习一下？",
        "default": "有个提醒想给你",
    },
    "material_utilization": {
        "material_underutilized": "你上传的资料还没用上，建议结合学习",
        "default": "资料使用情况提醒",
    },
    "deadline_pressure": {
        "default": "时间有点紧，调整了策略",
    },
    "community_cohort_pattern": {
        "cohort_mistake": "很多同学在同一个地方出错，注意避坑",
        "shared_resource": "推荐一份同学们觉得有用的资料",
        "default": "来自同伴的学习信号",
    },
}


# ── Explanation Templates ──────────────────────────────────────────

_EXPLANATION_MAP: dict[str, str] = {
    "task_granularity_fit": "系统检测到连续{consecutive}次任务超时，将任务时长上限调整为{max_minutes}分钟。",
    "knowledge_transfer": "你在「{node}」的学习效果不理想，系统切换为"例题+练习"模式。",
    "goal_mode": "系统检测到你有考试目标，自动切换到冲刺规划模式。",
    "growth_momentum": "你的成就动量{direction}，系统{action_desc}。",
    "recall_needed": "{recall_reason}",
    "material_utilization": "你上传了{material_count}份资料但只用了{used_count}份，建议在任务中结合使用。",
    "community_cohort_pattern": "{cohort_info}",
    "deadline_pressure": "距离截止还有{days_left}天，系统调整了任务密度。",
}


def _format_number(val: Any) -> str:
    if isinstance(val, float):
        return f"{val:.1f}"
    return str(val)


class TimelineCardRenderer:
    """Renders CausalTrace data into user-facing TimelineCards."""

    def render_card(
        self,
        *,
        trace_id: str,
        signal_data: dict[str, Any] | None = None,
        policy_data: dict[str, Any] | None = None,
        directives: list[dict[str, Any]] | None = None,
        receipt_data: dict[str, Any] | None = None,
        outcome_data: dict[str, Any] | None = None,
        mode: str = "compact",
        timestamp: str = "",
    ) -> TimelineCard | None:
        """
        Render a single CausalTrace into a TimelineCard.

        Returns None if there's nothing user-visible (no signal or no policy).
        """
        if not signal_data and not policy_data:
            return None

        from app.signals.types import _uid

        # Determine state_key and claim
        state_key = (signal_data or {}).get("state_key", "")
        claim = (signal_data or {}).get("claim", "")

        # Build headline
        headline = self._build_headline(state_key, claim, policy_data, directives)

        # Build summary
        summary = self._build_summary(state_key, claim, signal_data, policy_data, directives)

        # Build evidence chain
        evidence_chain = self._build_evidence_chain(
            signal_data, policy_data, directives, receipt_data, outcome_data,
        )

        # Build user actions
        user_actions = self._build_user_actions(receipt_data, outcome_data)

        # Detect card type
        card_type = self._detect_card_type(signal_data, outcome_data)

        return TimelineCard(
            card_id=_uid("tcard"),
            trace_id=trace_id,
            mode=mode,
            headline=headline,
            summary=summary,
            evidence_chain=evidence_chain,
            user_actions=user_actions,
            timestamp=timestamp,
            card_type=card_type,
        )

    def render_cards_batch(
        self,
        *,
        traces: list[dict[str, Any]],
        mode: str = "compact",
    ) -> list[TimelineCard]:
        """Render multiple traces into cards. Skips non-renderable traces."""
        cards = []
        for trace in traces:
            card = self.render_card(
                trace_id=trace.get("trace_id", ""),
                signal_data=trace.get("signal"),
                policy_data=trace.get("policy_decision"),
                directives=trace.get("directives"),
                receipt_data=trace.get("receipt"),
                outcome_data=trace.get("outcome"),
                mode=mode,
                timestamp=trace.get("created_at", ""),
            )
            if card:
                cards.append(card)
        return cards

    # ── Internal Helpers ────────────────────────────────────────────

    @staticmethod
    def _build_headline(
        state_key: str,
        claim: str,
        policy_data: dict[str, Any] | None,
        directives: list[dict[str, Any]] | None,
    ) -> str:
        templates = _HEADLINE_MAP.get(state_key, {})
        headline = templates.get(claim, templates.get("default", ""))
        if headline:
            return headline

        # Fallback: use policy strategy
        if policy_data:
            strategy = policy_data.get("primary_strategy", "")
            if strategy == "recover_execution_rhythm":
                return "根据执行节奏调整了任务安排"
            if strategy == "repair_knowledge_gap":
                return "发现知识缺口，调整了学习策略"

        return "系统做出了一个调整"

    @staticmethod
    def _build_summary(
        state_key: str,
        claim: str,
        signal_data: dict[str, Any] | None,
        policy_data: dict[str, Any] | None,
        directives: list[dict[str, Any]] | None,
    ) -> str:
        evidence = (signal_data or {}).get("evidence_summary", "")
        if evidence:
            return evidence

        # Build from policy/directive
        if policy_data:
            strategy = policy_data.get("primary_strategy", "")
            reason = policy_data.get("reason_for_user", "")
            if reason:
                return reason

        # Signal-based fallback
        if signal_data:
            return f"检测到 {claim}，系统自动调整了策略。"

        return "系统自动调整。"

    @staticmethod
    def _build_evidence_chain(
        signal_data: dict[str, Any] | None,
        policy_data: dict[str, Any] | None,
        directives: list[dict[str, Any]] | None,
        receipt_data: dict[str, Any] | None,
        outcome_data: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        chain = []

        if signal_data:
            chain.append({
                "step": "检测",
                "label": f"信号: {signal_data.get('claim', '?')}",
                "confidence": signal_data.get("confidence", 0),
                "detail": signal_data.get("evidence_summary", ""),
            })

        if policy_data:
            chain.append({
                "step": "策略",
                "label": f"策略: {policy_data.get('primary_strategy', '?')}",
                "detail": policy_data.get("reason_for_user", ""),
            })

        if directives:
            for d in directives[:3]:
                chain.append({
                    "step": "执行",
                    "label": f"指令: {d.get('target_module', d.get('directive_type', '?'))}",
                    "detail": d.get("user_visible_reason", ""),
                })

        if receipt_data:
            chain.append({
                "step": "通知",
                "label": receipt_data.get("message", ""),
                "detail": "",
            })

        if outcome_data:
            attribution = outcome_data.get("attribution", "inconclusive")
            chain.append({
                "step": "结果",
                "label": f"效果: {attribution}",
                "detail": outcome_data.get("new_hypothesis", ""),
            })

        return chain

    @staticmethod
    def _build_user_actions(
        receipt_data: dict[str, Any] | None,
        outcome_data: dict[str, Any] | None,
    ) -> list[dict[str, str]]:
        actions = []

        if receipt_data:
            for action in receipt_data.get("actions", []):
                if action == "confirm":
                    actions.append({"action": "confirm", "label": "好的，知道了"})
                elif action == "correct":
                    actions.append({"action": "correct", "label": "这个判断不对"})
                elif action == "dismiss":
                    actions.append({"action": "dismiss", "label": "不用了"})

        if not actions:
            # Default: always allow "why?" expand
            actions.append({"action": "expand", "label": "为什么？"})

        return actions

    @staticmethod
    def _detect_card_type(
        signal_data: dict[str, Any] | None,
        outcome_data: dict[str, Any] | None,
    ) -> str:
        if outcome_data and outcome_data.get("attribution") == "insufficient":
            return "self_correction"
        # Check for divine moment signals
        if signal_data:
            claim = signal_data.get("claim", "")
            state_key = signal_data.get("state_key", "")
            if claim == "pre_exam_silence" or state_key == "recall_needed":
                return "divine_moment"
        return "causal"

    @staticmethod
    def build_correction_options(
        *,
        state_key: str,
        claim: str,
    ) -> list[dict[str, str]]:
        """
        Build user correction options for a specific signal.
        These feed back into the CausalTrace via UserVisibleReceipt.
        """
        base_options = [
            {"action": "correct", "label": "这个判断不对"},
            {"action": "partial", "label": "部分正确"},
            {"action": "confirm", "label": "是对的"},
        ]

        # Add context-specific options
        if state_key == "task_granularity_fit":
            base_options.append({"action": "correct", "label": "任务大小刚好，不用调"})
        elif state_key == "knowledge_transfer":
            base_options.append({"action": "correct", "label": "是我粗心不是不会"})
        elif state_key == "growth_momentum":
            base_options.append({"action": "correct", "label": "我只是休息一下"})
        elif state_key == "recall_needed":
            base_options.append({"action": "dismiss", "label": "现在不想看"})

        return base_options
