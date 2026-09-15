"""
Core: execution
Phase: reflect→adapt
Stage: Signal-to-Action Spine — Skill Extraction

SkillExtractionService — 自动检测重复有效的策略，提取为 SkillEntry。

触发条件（v1.1 Section 21.1）：
- 某套任务策略连续成功（effective_count >= 3）
- 用户反馈明显正向
- 没有负向归因打断

Skill 不是 prompt，是策略资产。
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from app.signals.types import (
    PolicyEffectEntry,
    SkillEntry,
    _uid,
)

# ── 提取阈值 ──────────────────────────────────────────────────────

_EXTRACTION_THRESHOLD = 3  # 连续有效次数达到此值时触发提取
_CONFIDENCE_THRESHOLD = 0.7  # 平均置信度门槛


class SkillExtractionService:
    """
    Scans recent PolicyEffectEntries and extracts effective strategies as skills.
    """

    def scan_for_extractions(
        self,
        policy_effects: list[PolicyEffectEntry],
        *,
        user_id: str = "",
        context: dict[str, Any] | None = None,
    ) -> list[SkillEntry]:
        """
        Scan policy effects for patterns warranting skill extraction.

        Returns:
            List of newly extracted SkillEntry objects.
        """
        # Group effects by policy_key
        by_policy: dict[str, list[PolicyEffectEntry]] = {}
        for entry in policy_effects:
            key = entry.policy_key
            if key not in by_policy:
                by_policy[key] = []
            by_policy[key].append(entry)

        skills: list[SkillEntry] = []
        for policy_key, entries in by_policy.items():
            # Check for consecutive effective outcomes
            consecutive_effective = self._count_consecutive_effective(entries)
            if consecutive_effective < _EXTRACTION_THRESHOLD:
                continue

            # Check average confidence
            effective_entries = [e for e in entries if e.attribution == "effective"]
            if not effective_entries:
                continue

            avg_confidence = sum(
                e.attribution_confidence for e in effective_entries
            ) / len(effective_entries)
            if avg_confidence < _CONFIDENCE_THRESHOLD:
                continue

            # Check for no negative feedback signals
            has_negative_feedback = any(
                e.user_feedback_signal
                and e.user_feedback_signal not in ("completed", "positive")
                for e in effective_entries[-_EXTRACTION_THRESHOLD:]
            )
            if has_negative_feedback:
                continue

            # Extract skill
            skill = self._extract_skill(
                policy_key=policy_key,
                effective_entries=effective_entries,
                consecutive_count=consecutive_effective,
                context=context or {},
            )
            skills.append(skill)

            logger.info(
                "SkillExtraction: extracted {} from policy_key={} "
                "consecutive={} avg_confidence={:.2f}",
                skill.skill_id, policy_key,
                consecutive_effective, avg_confidence,
            )

        return skills

    @staticmethod
    def _count_consecutive_effective(entries: list[PolicyEffectEntry]) -> int:
        """Count consecutive effective attributions from most recent."""
        count = 0
        for entry in reversed(entries):
            if entry.attribution == "effective":
                count += 1
            else:
                break
        return count

    @staticmethod
    def _extract_skill(
        *,
        policy_key: str,
        effective_entries: list[PolicyEffectEntry],
        consecutive_count: int,
        context: dict[str, Any],
    ) -> SkillEntry:
        """Build a SkillEntry from effective policy entries."""
        # Determine scope based on context
        scope = context.get("scope", "personal")

        # Build strategy from the most recent effective entry
        latest = effective_entries[-1]
        strategy = {
            "intervention_summary": latest.intervention_summary,
            "policy_key": policy_key,
        }
        contraindications = [
            "avoid_if:user_explicitly_declines",
            "avoid_if:active_crisis_without_support",
        ]
        if policy_key in {"recover_execution_rhythm", "repair_knowledge_gap", "task_granularity_fit"}:
            contraindications.append("avoid_if:current_context=free_exploration")

        # Build applicable_when from context
        applicable_when: dict[str, Any] = {}
        if context.get("goal_mode"):
            applicable_when["goal_mode"] = context["goal_mode"]
        if context.get("state_key"):
            applicable_when["state_key"] = context["state_key"]

        # Build evidence
        evidence = {
            "effective_count": consecutive_count,
            "total_observed": len(effective_entries),
            "avg_confidence": round(
                sum(e.attribution_confidence for e in effective_entries) / len(effective_entries), 2
            ),
        }

        return SkillEntry(
            skill_id=_uid("skill"),
            scope=scope,
            source_policy_key=policy_key,
            strategy=strategy,
            applicable_when=applicable_when,
            evidence=evidence,
            privacy={"contains_personal_data": scope == "personal", "shareable": scope != "personal"},
            contraindications=contraindications,
            effective_count=consecutive_count,
            sample_size=len(effective_entries),
        )

    @staticmethod
    def should_extract(
        *,
        policy_key: str,
        policy_effects: list[PolicyEffectEntry],
    ) -> bool:
        """Quick check if a policy_key is eligible for extraction."""
        relevant = [e for e in policy_effects if e.policy_key == policy_key]
        if len(relevant) < _EXTRACTION_THRESHOLD:
            return False

        # Check last N are all effective
        recent = relevant[-_EXTRACTION_THRESHOLD:]
        return all(e.attribution == "effective" for e in recent)
