"""
Core: execution
Phase: clarify→plan
Stage: Signal-to-Action Spine P0-3 ActionableStatePacket v1

可行动状态寄存器填充器 — 从活跃信号和 directive 构建 ActionableStatePacket。

核心原则：
- 不是大画像，只存影响行动的状态位
- 每个状态都有 confidence / scope / ttl
- 不能改变行动的状态不进核心包

下游消费：task_generator 和 response layer 消费结构化字段，
而不是只消费自然语言 prompt。
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from app.signals.types import (
    ActionableSignal,
    ActionableStatePacket,
    ExecutionDirective,
    StateEntry,
    _uid,
)


class ActionableStatePacketBuilder:
    """
    从活跃信号和 directive 构建 ActionableStatePacket。

    职责：
    1. 读取用户当前活跃的 signals
    2. 读取当前活跃的 directive
    3. 构建 goal_frame, top_states, risk_flags, bottleneck, next_best_action
    """

    def build(
        self,
        *,
        user_id: str,
        active_signals: list[ActionableSignal] | None = None,
        active_directive: ExecutionDirective | None = None,
        goal_frame: dict[str, Any] | None = None,
        time_context: dict[str, Any] | None = None,
    ) -> ActionableStatePacket:
        """
        构建 ActionableStatePacket。

        Args:
            user_id: 用户 ID
            active_signals: 当前活跃的信号列表
            active_directive: 当前活跃的执行指令
            goal_frame: 目标框架 {mode, subject, deadline_days, target}
            time_context: 时间上下文
        """
        active_signals = active_signals or []
        goal_frame = goal_frame or {}

        # 从信号构建 top_states
        top_states = self._build_top_states(active_signals)

        # 从信号 + directive 构建 risk_flags
        risk_flags = self._build_risk_flags(active_signals, active_directive)

        # 确定当前瓶颈
        bottleneck = self._determine_bottleneck(active_signals)

        # 确定下一步最佳行动
        next_action = self._determine_next_action(active_signals, active_directive)

        # 构建时间上下文
        tc = self._build_time_context(time_context, active_signals)

        # 构建执行模式
        ep = self._build_execution_pattern(active_signals)

        # 构建上下文推荐
        cr = self._build_context_recommendation(active_signals, active_directive)

        packet = ActionableStatePacket(
            user_id=user_id,
            goal_frame=self._fill_goal_frame(goal_frame, active_signals),
            top_states=top_states,
            risk_flags=risk_flags,
            current_bottleneck=bottleneck,
            next_best_action=next_action,
            time_context=tc,
            execution_pattern=ep,
            context_recommendation=cr,
        )

        logger.debug(
            "ActionableStatePacket: user={} states={} flags={} bottleneck={}",
            user_id, len(top_states), len(risk_flags),
            bottleneck.get("node_id") if bottleneck else None,
        )

        return packet

    def _build_top_states(self, signals: list[ActionableSignal]) -> list[StateEntry]:
        """从信号构建 top states（按 priority 排序）。"""
        entries = []
        seen_keys = set()
        priority_order = {"high": 0, "medium": 1, "low": 2}

        sorted_signals = sorted(
            signals,
            key=lambda s: priority_order.get(s.priority, 3),
        )

        for signal in sorted_signals:
            if signal.state_key in seen_keys:
                continue
            seen_keys.add(signal.state_key)
            entries.append(StateEntry(
                state_key=signal.state_key,
                value=signal.claim,
                confidence=signal.confidence,
                scope=signal.scope,
                ttl_hours=signal.ttl_hours,
                supporting_evidence=[signal.evidence_summary] if signal.evidence_summary else [],
                can_affect=self._get_can_affect(signal.state_key),
            ))

        return entries[:10]  # 最多 10 个状态

    def _build_risk_flags(
        self,
        signals: list[ActionableSignal],
        directive: ExecutionDirective | None,
    ) -> list[str]:
        """从信号和 directive 构建风险标记。"""
        flags = []

        for signal in signals:
            if signal.priority == "high":
                flags.append(f"{signal.state_key}:{signal.claim}")
            if "deadline" in signal.state_key or "deadline" in signal.claim:
                flags.append("deadline_pressure_high")

        if directive:
            constraints = directive.hard_constraints
            if constraints.get("avoid_new_chapter"):
                flags.append("new_chapter_blocked")
            if constraints.get("max_task_duration_min"):
                flags.append(f"task_duration_capped:{constraints['max_task_duration_min']}min")

        return list(set(flags))

    def _determine_bottleneck(self, signals: list[ActionableSignal]) -> dict[str, Any] | None:
        """从信号中识别当前瓶颈。"""
        for signal in signals:
            if signal.state_key == "knowledge_transfer" and signal.claim == "transfer_failure":
                # 从 evidence_summary 中提取节点信息
                node_id = self._extract_node_id(signal.evidence_summary)
                return {
                    "node_id": node_id,
                    "type": "transfer_failure",
                    "confidence": signal.confidence,
                }
            if signal.state_key == "task_granularity_fit" and signal.claim == "recent_task_too_large":
                return {
                    "type": "task_granularity_mismatch",
                    "confidence": signal.confidence,
                }
        return None

    def _determine_next_action(
        self,
        signals: list[ActionableSignal],
        directive: ExecutionDirective | None,
    ) -> dict[str, Any] | None:
        """确定下一步最佳行动。"""
        if directive:
            return {
                "type": "apply_directive",
                "directive_id": directive.directive_id,
                "target_module": directive.target_module,
                "constraints": list(directive.hard_constraints.keys()),
            }

        high_priority = [s for s in signals if s.priority == "high"]
        if high_priority:
            top = high_priority[0]
            effects = top.possible_effects[:2] if top.possible_effects else []
            return {
                "type": "respond_to_signal",
                "strategy": effects[0] if effects else "unknown",
                "signal_id": top.signal_id,
            }

        return None

    def _fill_goal_frame(
        self,
        frame: dict[str, Any],
        signals: list[ActionableSignal],
    ) -> dict[str, Any]:
        """补充 goal_frame 中缺失的字段。"""
        for signal in signals:
            if signal.state_key == "goal_mode" and "mode" not in frame:
                if "exam_rescue" in signal.claim:
                    frame.setdefault("mode", "exam_rescue")
                    frame.setdefault("target", "minimum_pass")
        return frame

    def _extract_node_id(self, text: str) -> str:
        """从 evidence_summary 中提取节点 ID。"""
        import re
        m = re.search(r"知识节点\s+(\S+)", text)
        if m:
            return m.group(1).strip("，。、")
        return "unknown"

    def _get_can_affect(self, state_key: str) -> list[str]:
        """Get which directive types a state_key can affect."""
        from app.signals.state_register import _CAN_AFFECT_MAP
        return _CAN_AFFECT_MAP.get(state_key, [])

    def _build_time_context(
        self,
        time_context: dict[str, Any] | None,
        signals: list[ActionableSignal],
    ) -> dict[str, Any]:
        """构建时间上下文字段 (P0-3 spec)。"""
        tc = dict(time_context) if time_context else {}
        for signal in signals:
            if signal.state_key == "goal_mode" and "deadline_phase" not in tc:
                tc.setdefault("deadline_phase", "urgent" if "rescue" in signal.claim else "normal")
            if signal.state_key == "task_granularity_fit" and "task_stale_status" not in tc:
                tc.setdefault("task_stale_status", "overrun")
        return tc

    def _build_execution_pattern(self, signals: list[ActionableSignal]) -> dict[str, Any]:
        """构建执行模式字段 (P0-3 spec)。"""
        pattern: dict[str, Any] = {}
        for signal in signals:
            if signal.state_key == "task_granularity_fit":
                pattern["task_size_tendency"] = "oversized"
            elif signal.state_key == "knowledge_transfer":
                pattern["transfer_tendency"] = "failure"
            elif signal.state_key == "growth_momentum":
                pattern["momentum"] = signal.claim
        if signals:
            pattern["signal_density"] = len(signals)
        return pattern

    def _build_context_recommendation(
        self,
        signals: list[ActionableSignal],
        directive: ExecutionDirective | None,
    ) -> dict[str, Any]:
        """构建上下文推荐字段 (P0-3 spec)。"""
        rec: dict[str, Any] = {}
        if directive:
            rec["retrieval_hint"] = "targeted" if directive.hard_constraints.get("avoid_new_chapter") else "standard"
            rec["tone_hint"] = directive.hard_constraints.get("tone", "neutral")
        for signal in signals:
            if signal.state_key == "material_utilization":
                rec["material_mode"] = "underutilized"
        return rec
