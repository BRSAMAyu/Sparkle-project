"""
Intervention Outcome Verifier — Checks whether interventions were effective.

This implements the verification pipeline for the growth loop:
  After outcome_window_days, examine plan health recovery, knowledge mastery
  improvement, or behavioral change to determine EFFECTIVE vs INEFFECTIVE.

Phase 2: Basic pipeline (plan health recovery, mastery improvement).
Phase 3: Deepened with parameter compiler tracking, decision log verification,
  risk register updates, and strategy learning feedback.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card_protocol import (
    InterventionRecord,
    InterventionOutcomeStatus,
    InterventionAcceptanceStatus,
    InterventionTriggerType,
)
from app.services.intervention_record_service import InterventionRecordService
from app.services.card_service import CardService
from app.services.intervention_strategy_learner import InterventionStrategyLearner
from app.services.task_reflection_service import TaskReflectionService
from app.core.event_bus import EventBus


class InterventionOutcomeVerifier:
    """Verifies intervention outcomes by examining post-intervention evidence.

    Runs as a periodic job (or on-demand) to resolve PENDING outcomes whose
    outcome_window has closed.
    """

    def __init__(self, db: AsyncSession, event_bus: EventBus | None = None):
        self.db = db
        self.event_bus = event_bus
        self.record_service = InterventionRecordService(db, event_bus)
        self.card_service = CardService(db, event_bus)
        self.strategy_learner = InterventionStrategyLearner(db)

    async def verify_all_pending(self) -> dict:
        """Verify all pending interventions whose outcome window has closed.

        Returns summary: {"resolved": N, "effective": N, "ineffective": N, "unknown": N}
        """
        return await self.verify_pending_due()

    async def verify_pending_due(
        self,
        *,
        eligible_acceptance_statuses: set[InterventionAcceptanceStatus] | None = None,
        min_record_age: timedelta | None = None,
    ) -> dict:
        """Verify pending interventions that match an optional scheduled sweep."""
        now = datetime.utcnow()
        summary = {"resolved": 0, "effective": 0, "ineffective": 0, "unknown": 0}

        stmt = select(InterventionRecord).where(
            InterventionRecord.outcome_status == InterventionOutcomeStatus.PENDING,
            InterventionRecord.not_deleted_filter(),
        )
        if eligible_acceptance_statuses is not None:
            stmt = stmt.where(
                InterventionRecord.acceptance_status.in_(tuple(eligible_acceptance_statuses))
            )
        result = await self.db.execute(stmt)
        records = list(result.scalars().all())

        for record in records:
            if record.created_at is None:
                continue
            if min_record_age is not None and (now - record.created_at) < min_record_age:
                continue
            deadline = record.created_at + timedelta(days=record.outcome_window_days)
            if now < deadline:
                continue

            outcome, evidence = await self._evaluate_outcome(record)
            if outcome is None:
                continue

            await self.record_service.resolve_outcome(
                record.id, outcome, evidence_payload=evidence
            )

            # Phase 3: Update decision log, risk register, and strategy learning
            await self._phase3_post_evaluation(record, outcome, evidence)

            summary["resolved"] += 1
            if outcome == InterventionOutcomeStatus.EFFECTIVE:
                summary["effective"] += 1
            elif outcome == InterventionOutcomeStatus.INEFFECTIVE:
                summary["ineffective"] += 1
            else:
                summary["unknown"] += 1

        if summary["resolved"] > 0:
            await self.db.commit()

        if summary["resolved"] > 0:
            logger.info(
                "InterventionOutcomeVerifier: resolved {} interventions "
                "(effective={}, ineffective={}, unknown={})",
                summary["resolved"],
                summary["effective"],
                summary["ineffective"],
                summary["unknown"],
            )
        return summary

    async def verify_engaged_pending(self, *, min_record_age: timedelta | None = None) -> dict:
        """Verify engaged interventions for the scheduled 4-hour sweep."""
        return await self.verify_pending_due(
            eligible_acceptance_statuses={
                InterventionAcceptanceStatus.DELIVERED,
                InterventionAcceptanceStatus.SEEN,
                InterventionAcceptanceStatus.ACCEPTED,
                InterventionAcceptanceStatus.ACTED,
                InterventionAcceptanceStatus.DISMISSED,
                InterventionAcceptanceStatus.SNOOZED,
            },
            min_record_age=min_record_age or timedelta(hours=24),
        )

    async def verify_full_pending(self) -> dict:
        """Verify all pending interventions for the nightly full sweep."""
        return await self.verify_pending_due()

    async def _evaluate_outcome(
        self, record: InterventionRecord
    ) -> tuple[InterventionOutcomeStatus | None, dict]:
        """Evaluate a single intervention's outcome.

        Returns (outcome, evidence) or (None, {}) if insufficient data.
        """
        evidence: dict = {"record_id": str(record.id), "evaluation_method": ""}

        if self._has_system_applied_action(record):
            improvement = await self._check_improvement(record)
            evidence["evaluation_method"] = "system_applied_and_measured"
            evidence["improvement"] = improvement
            if (
                improvement.get("plan_health_recovered")
                or improvement.get("mastery_improved")
                or improvement.get("parameter_strategy_effective")
            ):
                return InterventionOutcomeStatus.EFFECTIVE, evidence
            if improvement.get("has_sufficient_data"):
                return InterventionOutcomeStatus.INEFFECTIVE, evidence
            return InterventionOutcomeStatus.UNKNOWN, evidence

        # 1. If user never engaged -> INEFFECTIVE
        if record.acceptance_status in (
            InterventionAcceptanceStatus.CREATED,
            InterventionAcceptanceStatus.DELIVERED,
            InterventionAcceptanceStatus.DISMISSED,
        ):
            evidence["evaluation_method"] = "no_engagement"
            evidence["final_acceptance"] = record.acceptance_status.value
            return InterventionOutcomeStatus.INEFFECTIVE, evidence

        # 2. If user ACTED -> check for improvement
        if record.acceptance_status == InterventionAcceptanceStatus.ACTED:
            improvement = await self._check_improvement(record)
            evidence["evaluation_method"] = "acted_and_measured"
            evidence["improvement"] = improvement

            if (
                improvement.get("plan_health_recovered")
                or improvement.get("mastery_improved")
                or improvement.get("parameter_strategy_effective")
            ):
                return InterventionOutcomeStatus.EFFECTIVE, evidence
            if improvement.get("has_sufficient_data"):
                return InterventionOutcomeStatus.INEFFECTIVE, evidence
            return InterventionOutcomeStatus.UNKNOWN, evidence

        # 3. If user ACCEPTED but didn't act -> UNKNOWN
        if record.acceptance_status == InterventionAcceptanceStatus.ACCEPTED:
            improvement = await self._check_improvement(record)
            evidence["evaluation_method"] = "accepted_no_action"
            evidence["improvement"] = improvement
            if (
                improvement.get("plan_health_recovered")
                or improvement.get("mastery_improved")
                or improvement.get("parameter_strategy_effective")
            ):
                return InterventionOutcomeStatus.EFFECTIVE, evidence
            return InterventionOutcomeStatus.UNKNOWN, evidence

        # 4. SEEN or SNOOZED -> check passive improvement
        if record.acceptance_status in (
            InterventionAcceptanceStatus.SEEN,
            InterventionAcceptanceStatus.SNOOZED,
        ):
            improvement = await self._check_improvement(record)
            evidence["evaluation_method"] = "passive_improvement_check"
            evidence["improvement"] = improvement

            if improvement.get("plan_health_recovered") or improvement.get("parameter_strategy_effective"):
                return InterventionOutcomeStatus.EFFECTIVE, evidence
            return InterventionOutcomeStatus.UNKNOWN, evidence

        return None, {}

    async def _check_improvement(self, record: InterventionRecord) -> dict:
        """Check whether the condition that triggered the intervention improved.

        Phase 2 basic + Phase 3 parameter tracking.
        """
        improvement: dict = {"has_sufficient_data": False}
        parameter_payload = self._parameter_compilation_payload(record)
        if parameter_payload:
            improvement["parameter_compilation_present"] = True
            improvement["parameter_compilation_result"] = parameter_payload.get("result")
            improvement["compiled_parameters_applied"] = bool(parameter_payload.get("applied"))
            improvement["affected_task_count"] = int(parameter_payload.get("affected_task_count") or 0)
            improvement["inserted_task_count"] = int(parameter_payload.get("inserted_task_count") or 0)
            improvement["hidden_task_count"] = int(parameter_payload.get("hidden_task_count") or 0)
            improvement["decision_log_entry_id"] = parameter_payload.get("decision_log_entry_id")

        # For PLAN_RISK / OVERLOAD / STALL: check plan card health
        if record.trigger_type in (
            InterventionTriggerType.PLAN_RISK,
            InterventionTriggerType.OVERLOAD,
            InterventionTriggerType.STALL_PATTERN,
        ):
            legacy_plan_id: str | None = parameter_payload.get("plan_id") if parameter_payload else None
            if record.plan_card_id:
                plan_card = await self.card_service.get_card(record.plan_card_id)
                if plan_card:
                    meta = plan_card.metadata_ or {}
                    legacy_plan_id = legacy_plan_id or meta.get("legacy_plan_id")
                    last_adjustment = meta.get("latest_adjustment_evidence", {})
                    last_replan = meta.get("replan_event", {})
                    if self._event_is_newer_than_record(last_adjustment, record):
                        improvement["plan_health_recovered"] = True
                        improvement["recovery_detail"] = last_adjustment
                    elif self._event_is_newer_than_record(last_replan, record):
                        improvement["plan_health_recovered"] = True
                        improvement["recovery_detail"] = last_replan
                    improvement["has_sufficient_data"] = True

            # Phase 3: Check if compiled parameters were consumed
            try:
                from app.services.plan_state_service import PlanStateService
                pss = PlanStateService(self.db, redis=None)
                if legacy_plan_id and record.user_id:
                    from uuid import UUID as UUIDType

                    state = await pss.get_plan_state(
                        record.user_id, UUIDType(legacy_plan_id)
                    )
                    if state:
                        adaptive = dict((state.facts or {}).get("adaptive_adjustments", {}))
                        comp_meta = dict(adaptive.get("compilation_meta", {}))
                        if comp_meta:
                            improvement["compiled_parameters_applied"] = True
                            improvement["compilation_trigger"] = comp_meta.get("trigger")
                            improvement["compilation_compass_version"] = comp_meta.get("compass_version")
                            improvement["compilation_strategy_version"] = comp_meta.get("strategy_map_version")
                            improvement["compilation_decision_log_entry_id"] = comp_meta.get("decision_log_entry_id")

                        feedback_window = self._feedback_after_record(
                            state.feedback_log or [],
                            record,
                        )
                        if feedback_window:
                            categories = [
                                entry.get("content", "")
                                for entry in feedback_window
                                if isinstance(entry, dict)
                            ]
                            negative_feedback = [
                                entry for entry in feedback_window
                                if self._feedback_is_negative(entry)
                            ]
                            improvement["post_intervention_feedback_count"] = len(feedback_window)
                            improvement["post_intervention_negative_feedback_count"] = len(negative_feedback)
                            improvement["post_intervention_feedback_categories"] = categories[:5]
                            improvement["has_sufficient_data"] = True

                        if improvement.get("compiled_parameters_applied"):
                            improvement["has_sufficient_data"] = True
                            patched_task_count = (
                                improvement.get("affected_task_count", 0)
                                + improvement.get("inserted_task_count", 0)
                                + improvement.get("hidden_task_count", 0)
                            )
                            no_negative_feedback = (
                                improvement.get("post_intervention_feedback_count", 0) > 0
                                and improvement.get("post_intervention_negative_feedback_count", 0) == 0
                            )
                            repeated_negative_feedback = improvement.get(
                                "post_intervention_negative_feedback_count", 0
                            ) >= 2
                            improvement["parameter_strategy_effective"] = bool(
                                patched_task_count > 0 and no_negative_feedback
                            )
                            improvement["parameter_strategy_ineffective"] = bool(
                                patched_task_count > 0
                                and repeated_negative_feedback
                                and not improvement.get("plan_health_recovered")
                            )
            except Exception as exc:
                logger.debug("Phase3 parameter check failed (non-fatal): {}", exc)

        # For CONCEPT_GAP: check knowledge card mastery state
        if record.trigger_type == InterventionTriggerType.CONCEPT_GAP:
            if record.knowledge_card_id:
                knowledge_card = await self.card_service.get_card(record.knowledge_card_id)
                if knowledge_card:
                    meta = knowledge_card.metadata_ or {}
                    mastery_state = meta.get("mastery_state", "unknown")
                    if mastery_state not in ("at_risk", "unknown"):
                        improvement["mastery_improved"] = True
                        improvement["new_mastery_state"] = mastery_state
                    improvement["has_sufficient_data"] = True

        return improvement

    async def _phase3_post_evaluation(
        self,
        record: InterventionRecord,
        outcome: InterventionOutcomeStatus,
        evidence: dict,
    ) -> None:
        """Phase 3: Update decision log, risk register, and strategy learning."""
        await self.strategy_learner.record_outcome(
            user_id=record.user_id,
            intervention_id=record.id,
            outcome_status=outcome,
            context_snapshot=self._strategy_context_snapshot(record, evidence),
        )

        if not record.plan_card_id:
            return

        effective = outcome == InterventionOutcomeStatus.EFFECTIVE

        # 1. Update decision log
        await self._update_decision_log(record, effective, evidence)

        # 2. Update risk register
        await self._update_risk_register(record, effective, evidence)

        # 3. Strategy learning feedback
        await self._strategy_learning_feedback(record, effective)

        # 3.5 Check for pattern of ineffective interventions (3+)
        if not effective:
            stmt = select(InterventionRecord).where(
                InterventionRecord.plan_card_id == record.plan_card_id,
                InterventionRecord.trigger_type == record.trigger_type,
                InterventionRecord.outcome_status == InterventionOutcomeStatus.INEFFECTIVE,
                InterventionRecord.not_deleted_filter(),
            )
            ineffective_records = list((await self.db.execute(stmt)).scalars().all())
            if len(ineffective_records) >= 3:
                try:
                    from app.services.card_protocol.strategy_map_manager import StrategyMapManager
                    strategy = StrategyMapManager(self.db, self.event_bus)
                    await strategy.propose_update(
                        record.plan_card_id,
                        updates={},  # Prompt a strategy learning review by the system
                        evidence={
                            "source": "outcome_verifier",
                            "reason": f"Detected 3+ ineffective interventions for trigger {record.trigger_type.value if record.trigger_type else 'unknown'}",
                            "ineffective_count": len(ineffective_records)
                        }
                    )
                except Exception as exc:
                    logger.debug("Phase3 ineffective pattern check failed (non-fatal): {}", exc)

        # 3.6 Phase E: compute planning drift and raise a MISALIGNMENT intervention if needed
        await self._phase_e_drift_check(record)

        # 4. Phase 4: materialize the latest main-chain reflection state
        try:
            from app.services.card_protocol.main_chain_artifact_service import MainChainArtifactService

            artifact_service = MainChainArtifactService(self.db, self.event_bus)
            await artifact_service.refresh_active_phase_pack(
                plan_card_id=record.plan_card_id,
                generated_reason=f"intervention_outcome:{outcome.value.lower()}",
            )
            await artifact_service.refresh_reflection_report(
                plan_card_id=record.plan_card_id,
                generated_reason=f"intervention_outcome:{outcome.value.lower()}",
                linked_intervention_id=str(record.id),
            )
        except Exception as exc:
            logger.debug("Phase4 reflection materialization failed (non-fatal): {}", exc)

        await self._request_reflection_follow_up(record, outcome, evidence)

    async def _phase_e_drift_check(self, record: InterventionRecord) -> None:
        """Phase E: detect long-horizon drift and create MISALIGNMENT interventions."""
        if not record.plan_card_id:
            return
        try:
            from app.models.card_protocol import DeliveryChannel, DeliveryStrategy
            from app.services.card_protocol.planning_memory_service import PlanningMemoryService

            planning_memory = PlanningMemoryService(self.db, self.event_bus)

            # Check for 2+ consecutive phases with low alignment score
            context = await planning_memory.load_planning_context(
                plan_card_id=record.plan_card_id, user_id=record.user_id
            )
            archive = context.phase_archive
            active_phase = context.active_phase
            all_phases = archive + ([active_phase] if active_phase else [])
            low_alignment_count = 0
            for phase in reversed(all_phases):
                if not phase: continue
                alignment = (phase.get("feedback_gate") or {}).get("alignment_score")
                if alignment is not None and float(alignment) < 0.5:
                    low_alignment_count += 1
                else:
                    if alignment is not None:
                        break

            is_consecutive_low_alignment = low_alignment_count >= 2

            drift = await planning_memory.compute_drift_score(plan_card_id=record.plan_card_id)
            if drift.drift_score <= 0.5 and not is_consecutive_low_alignment:
                return

            # Avoid stacking duplicate unresolved misalignment interventions.
            stmt = select(InterventionRecord).where(
                InterventionRecord.plan_card_id == record.plan_card_id,
                InterventionRecord.trigger_type == InterventionTriggerType.MISALIGNMENT,
                InterventionRecord.outcome_status == InterventionOutcomeStatus.PENDING,
                InterventionRecord.not_deleted_filter(),
            )
            existing = (await self.db.execute(stmt)).scalars().first()
            if existing:
                return

            await self.record_service.create_record(
                user_id=record.user_id,
                trigger_type=InterventionTriggerType.MISALIGNMENT,
                delivery_strategy=DeliveryStrategy.SUPPORTIVE,
                delivery_channel=DeliveryChannel.IN_APP,
                plan_card_id=record.plan_card_id,
                phase_card_id=record.phase_card_id,
                diagnosis_payload={
                    "source": "planning_memory_drift_check",
                    "drift_score": drift.drift_score,
                    "indicators": drift.drift_indicators,
                    "recommendation": drift.recommendation,
                    "supporting_metrics": drift.supporting_metrics,
                },
                outcome_window_days=7,
            )
        except Exception as exc:
            logger.debug("PhaseE drift check failed (non-fatal): {}", exc)

    async def _request_reflection_follow_up(
        self,
        record: InterventionRecord,
        outcome: InterventionOutcomeStatus,
        evidence: dict[str, Any],
    ) -> None:
        category = self._derive_reflection_category(record, outcome, evidence)
        if category is None or record.user_id is None:
            return

        payload = {
            "event_type": "reflection_trigger_requested",
            "user_id": str(record.user_id),
            "category": category,
            "intervention_id": str(record.id),
            "plan_card_id": str(record.plan_card_id) if record.plan_card_id else "",
            "trigger_type": record.trigger_type.value if record.trigger_type else "",
            "acceptance_status": record.acceptance_status.value if record.acceptance_status else "",
            "outcome_status": outcome.value,
            "window_days": int(record.outcome_window_days or 0),
            "decision_id": (
                evidence.get("improvement", {}) or {}
            ).get("decision_log_entry_id")
            or (
                evidence.get("improvement", {}) or {}
            ).get("compilation_decision_log_entry_id")
            or evidence.get("decision_log_entry_id"),
            "timestamp": datetime.utcnow().isoformat(),
        }
        try:
            if self.event_bus is not None:
                await self.event_bus.publish("reflection_trigger_requested", payload)
            await TaskReflectionService(self.db).handle_triggered_reflection(
                user_id=record.user_id,
                category=category,
                trigger_payload=payload,
            )
        except Exception as exc:
            logger.debug("Stage25 reflection request failed (non-fatal): {}", exc)

    @staticmethod
    def _derive_reflection_category(
        record: InterventionRecord,
        outcome: InterventionOutcomeStatus,
        evidence: dict[str, Any],
    ) -> str | None:
        if (
            outcome == InterventionOutcomeStatus.INEFFECTIVE
            and record.acceptance_status in {
                InterventionAcceptanceStatus.ACCEPTED,
                InterventionAcceptanceStatus.ACTED,
                InterventionAcceptanceStatus.SEEN,
            }
        ):
            return "intervention_ineffective"

        improvement = evidence.get("improvement", {}) if isinstance(evidence, dict) else {}
        negative_feedback_count = int(improvement.get("post_intervention_negative_feedback_count") or 0)
        if record.trigger_type == InterventionTriggerType.STALL_PATTERN and (
            outcome in {InterventionOutcomeStatus.INEFFECTIVE, InterventionOutcomeStatus.UNKNOWN}
            or negative_feedback_count >= 2
        ):
            return "plan_stall"
        if record.trigger_type == InterventionTriggerType.OVERLOAD and (
            outcome in {InterventionOutcomeStatus.INEFFECTIVE, InterventionOutcomeStatus.UNKNOWN}
            or negative_feedback_count >= 1
        ):
            return "overload"
        return None

    async def _update_decision_log(
        self,
        record: InterventionRecord,
        effective: bool,
        evidence: dict,
    ) -> None:
        """Update decision log confirmation status based on outcome."""
        try:
            from app.services.card_protocol.decision_log_service import DecisionLogService
            decision_log = DecisionLogService(self.db, self.event_bus)

            # Find entry linked to this intervention
            intervention_id = str(record.id)
            entries = await decision_log.find_entry_by_intervention(
                record.plan_card_id, intervention_id
            )

            if not entries:
                # Try finding by trigger match
                all_entries = await decision_log.get_pending_confirmations(record.plan_card_id)
                for entry in all_entries:
                    if entry.get("trigger", "").lower() in str(record.trigger_type.value).lower():
                        entries = entry
                        break

            if not entries:
                return

            entry_id = entries.get("id")
            if not entry_id:
                return

            if effective:
                await decision_log.confirm_entry(
                    record.plan_card_id,
                    entry_id,
                    evidence=evidence,
                )
            else:
                await decision_log.contradict_entry(
                    record.plan_card_id,
                    entry_id,
                    evidence=evidence,
                )
        except Exception as exc:
            logger.debug("DecisionLog update failed (non-fatal): {}", exc)

    async def _update_risk_register(
        self,
        record: InterventionRecord,
        effective: bool,
        evidence: dict,
    ) -> None:
        """Update risk register based on intervention outcome."""
        try:
            from app.services.card_protocol.risk_register_service import RiskRegisterService
            risk_service = RiskRegisterService(self.db, self.event_bus)

            trigger_type = record.trigger_type.value if record.trigger_type else ""
            await risk_service.update_from_outcome(
                plan_card_id=record.plan_card_id,
                trigger_type=trigger_type,
                effective=effective,
                evidence=evidence,
            )
        except Exception as exc:
            logger.debug("RiskRegister update failed (non-fatal): {}", exc)

    async def _strategy_learning_feedback(
        self,
        record: InterventionRecord,
        effective: bool,
    ) -> None:
        """Phase 3: Feed outcome back into strategy map for learning.

        If an intervention was effective, reinforce the parameters.
        If ineffective, weaken them (suggest a different approach).
        """
        if not record.plan_card_id:
            return

        # Only learn from interventions where user engaged
        if (
            not self._has_system_applied_action(record)
            and record.acceptance_status in (
            InterventionAcceptanceStatus.CREATED,
            InterventionAcceptanceStatus.DELIVERED,
            InterventionAcceptanceStatus.DISMISSED,
            )
        ):
            return

        try:
            from app.services.card_protocol.strategy_map_manager import StrategyMapManager
            strategy = StrategyMapManager(self.db, self.event_bus)

            params = await strategy.get_parameters(record.plan_card_id)
            if not params:
                return

            trigger = record.trigger_type.value if record.trigger_type else ""
            strategy_trigger = StrategyMapManager.resolve_trigger(
                replanner_trigger=trigger,
            )
            if not strategy_trigger:
                return

            rules = dict(params.get("adaptation_rules", {}))
            rule = rules.get(strategy_trigger, {})
            if not rule:
                return

            action = rule.get("action", "")
            rule_params = dict(rule.get("params", {}))

            if effective:
                # Effective: the rule worked — keep or slightly reduce aggressiveness
                if action == "extend_timeline" and "multiplier" in rule_params:
                    current = float(rule_params["multiplier"])
                    delta = 0.08 if self._parameter_compilation_result(record) == "patched" else 0.05
                    rule_params["multiplier"] = round(max(1.0, current - delta), 2)
                    rules[strategy_trigger] = {"action": action, "params": rule_params}
                    await strategy.propose_update(
                        record.plan_card_id,
                        {"adaptation_rules": rules},
                        evidence={
                            "source": "outcome_verifier",
                            "outcome": "EFFECTIVE",
                            "parameter_compilation_result": self._parameter_compilation_result(record),
                        },
                    )
            else:
                # Ineffective: increase aggressiveness for next time
                if action == "extend_timeline" and "multiplier" in rule_params:
                    current = float(rule_params["multiplier"])
                    delta = 0.15 if self._parameter_compilation_result(record) == "compiled_only" else 0.1
                    rule_params["multiplier"] = round(min(2.0, current + delta), 2)
                    rules[strategy_trigger] = {"action": action, "params": rule_params}
                    await strategy.propose_update(
                        record.plan_card_id,
                        {"adaptation_rules": rules},
                        evidence={
                            "source": "outcome_verifier",
                            "outcome": "INEFFECTIVE",
                            "parameter_compilation_result": self._parameter_compilation_result(record),
                        },
                    )
        except Exception as exc:
            logger.debug("Strategy learning feedback failed (non-fatal): {}", exc)

    @staticmethod
    def _parameter_compilation_payload(record: InterventionRecord) -> dict[str, Any]:
        payload = (record.action_payload or {}).get("parameter_compilation")
        if isinstance(payload, dict):
            return payload
        return {}

    @classmethod
    def _strategy_context_snapshot(
        cls,
        record: InterventionRecord,
        evidence: dict[str, Any],
    ) -> dict[str, Any]:
        improvement = dict(evidence.get("improvement") or {})
        diagnosis = dict(record.diagnosis_payload or {})
        context = dict(diagnosis.get("context") or {})
        cohort_profile = cls._extract_cohort_profile(diagnosis)
        return {
            "evaluation_method": evidence.get("evaluation_method"),
            "plan_health_recovered": improvement.get("plan_health_recovered"),
            "mastery_improved": improvement.get("mastery_improved"),
            "parameter_strategy_effective": improvement.get("parameter_strategy_effective"),
            "parameter_compilation_result": cls._parameter_compilation_result(record),
            "pattern_name": diagnosis.get("pattern_name"),
            "pattern_type": diagnosis.get("pattern_type"),
            "reasons": diagnosis.get("reasons") or [],
            "completed_count": context.get("completed_count"),
            "goal_type": cohort_profile.get("goal_type"),
            "knowledge_level": cohort_profile.get("knowledge_level"),
            "learning_style": cohort_profile.get("learning_style"),
        }

    @staticmethod
    def _extract_cohort_profile(diagnosis: dict[str, Any]) -> dict[str, Any]:
        raw = diagnosis.get("cohort_profile")
        if isinstance(raw, dict):
            profile = dict(raw)
        else:
            profile = {}
        context = diagnosis.get("context")
        if isinstance(context, dict):
            for key in ("goal_type", "knowledge_level", "learning_style"):
                if not profile.get(key) and context.get(key) is not None:
                    profile[key] = context.get(key)
        for key in ("goal_type", "knowledge_level", "learning_style"):
            if not profile.get(key) and diagnosis.get(key) is not None:
                profile[key] = diagnosis.get(key)
        return profile

    @classmethod
    def _parameter_compilation_result(cls, record: InterventionRecord) -> str | None:
        return cls._parameter_compilation_payload(record).get("result")

    @staticmethod
    def _feedback_after_record(
        feedback_log: list[dict[str, Any]],
        record: InterventionRecord,
    ) -> list[dict[str, Any]]:
        created_at = record.created_at
        if not created_at:
            return []
        if created_at.tzinfo is not None:
            created_at = created_at.replace(tzinfo=None)

        entries: list[dict[str, Any]] = []
        for item in feedback_log:
            if not isinstance(item, dict):
                continue
            timestamp = item.get("timestamp")
            parsed = InterventionOutcomeVerifier._parse_timestamp(timestamp)
            if parsed and parsed >= created_at:
                entries.append(item)
        return entries

    @staticmethod
    def _feedback_is_negative(entry: dict[str, Any]) -> bool:
        content = str(entry.get("content", "")).lower()
        applied = entry.get("applied_adjustment")
        if isinstance(applied, dict):
            if applied.get("aborted") is True:
                return True
            if applied.get("quality_score") is not None and float(applied.get("quality_score") or 0) < 0.5:
                return True
        negative_markers = ("too hard", "failed", "aborted", "卡住", "太难", "超时")
        return any(marker in content for marker in negative_markers)

    @staticmethod
    def _parse_timestamp(value: Any) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None
        if parsed.tzinfo is not None:
            return parsed.replace(tzinfo=None)
        return parsed

    @staticmethod
    def _event_is_newer_than_record(
        event_payload: dict | None, record: InterventionRecord
    ) -> bool:
        if not event_payload or not record.created_at:
            return False

        timestamp_value = event_payload.get("timestamp")
        if not timestamp_value:
            return False

        try:
            event_time = datetime.fromisoformat(timestamp_value.replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return False

        if event_time.tzinfo is not None:
            event_time = event_time.replace(tzinfo=None)

        created_at = record.created_at
        if created_at.tzinfo is not None:
            created_at = created_at.replace(tzinfo=None)
        return event_time >= created_at

    @staticmethod
    def _has_system_applied_action(record: InterventionRecord) -> bool:
        """Detect interventions whose delivery pipeline already changed execution.

        Phase 3 allows some interventions to auto-compile parameters and patch the
        plan before the user explicitly responds. These should be evaluated on the
        resulting evidence, not treated as "no engagement" failures by default.
        """
        action_payload = dict(record.action_payload or {})
        parameter_compilation = dict(action_payload.get("parameter_compilation") or {})
        if parameter_compilation.get("applied") is True:
            return True
        return False
