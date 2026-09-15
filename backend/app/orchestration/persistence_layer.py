from __future__ import annotations

import contextlib
import json
import uuid
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.gen.agent.v1 import agent_service_pb2
from app.models.chat import ChatMessage, MessageRole
from app.orchestration.schemas import ExecutablePlan
from app.services.llm_service import llm_service
from app.services.memory_inferred_write_lane import MemoryInferredWriteLaneService


class PersistenceLayerMixin:
    """Mixin that groups persistence / side-effect helpers used by ChatOrchestrator."""

    # ------------------------------------------------------------------
    # persist assistant message
    # ------------------------------------------------------------------
    async def _persist_assistant_message(
        self,
        *,
        active_db: AsyncSession | None,
        user_id: str,
        session_id: str,
        full_response: str,
    ) -> None:
        if not active_db or not full_response:
            return
        try:
            assistant_msg = ChatMessage(
                user_id=uuid.UUID(str(user_id)),
                session_id=self._coerce_session_uuid(session_id),
                role=MessageRole.ASSISTANT,
                content=full_response,
                model_name=getattr(llm_service, "default_model", None),
            )
            active_db.add(assistant_msg)
            await active_db.commit()
            MemoryInferredWriteLaneService.enqueue_from_session(
                user_id=uuid.UUID(str(user_id)),
                session_id=self._coerce_session_uuid(session_id),
                assistant_message_id=str(assistant_msg.id),
                assistant_message=full_response,
            )
        except Exception as e:
            logger.warning(f"Failed to persist assistant chat message: {e}")
            with contextlib.suppress(Exception):
                await active_db.rollback()

    # ------------------------------------------------------------------
    # record routing decision
    # ------------------------------------------------------------------
    async def _record_decision(
        self,
        *,
        active_db: AsyncSession | None,
        user_id: str,
        user_context_payload: dict[str, Any] | None,
        llm_profile_meta: dict[str, Any],
        full_response: str,
    ) -> None:
        try:
            from app.services.decision_record_service import DecisionRecordService

            if active_db is None or not active_db.is_active:
                return

            def get_val(d, key, default):
                if not isinstance(d, dict):
                    return default
                if key in d:
                    return d[key]
                quoted_key = f'"{key}"'
                if quoted_key in d:
                    return d[quoted_key]
                return default

            pref_snapshot = {
                "verbosity": get_val(llm_profile_meta, "verbosity_target", "balanced"),
                "temperature": get_val(llm_profile_meta, "temperature", 0.7),
                "tone": get_val(llm_profile_meta, "tone", "encouraging"),
            }
            decision_service = DecisionRecordService(active_db)
            await decision_service.record_decision(
                user_id=uuid.UUID(str(user_id)),
                module="ai",
                action="generate_response",
                preference_version=(user_context_payload or {}).get("preference_version", 0),
                preferences_snapshot=pref_snapshot,
                outcome=f"Generated response with {len(full_response)} chars",
            )
        except Exception as e:
            logger.warning(f"Failed to record decision: {e}")
            logger.debug(f"llm_profile_meta type: {type(llm_profile_meta)}, content: {llm_profile_meta}")

    # ------------------------------------------------------------------
    # load recent execution feedback
    # ------------------------------------------------------------------
    async def _load_recent_execution_feedback(
        self,
        *,
        active_db: AsyncSession | None,
        user_id: str,
        plan_id: str | None,
    ) -> dict[str, Any] | None:
        if not active_db or not plan_id:
            return None
        try:
            from app.services.plan_state_service import PlanStateService

            plan_state_service = PlanStateService(active_db, self.redis)
            plan_state = await plan_state_service.get_plan_state(
                uuid.UUID(user_id),
                uuid.UUID(plan_id),
            )
            if not plan_state or not plan_state.feedback_log:
                return None

            for entry in reversed(plan_state.feedback_log):
                feedback = self._extract_execution_feedback_from_log_entry(entry)
                if feedback is not None:
                    return feedback
        except Exception as e:
            logger.warning(f"Failed to load recent execution feedback: {e}")
        return None

    # ------------------------------------------------------------------
    # publish execution feedback
    # ------------------------------------------------------------------
    async def _publish_execution_feedback(
        self,
        *,
        active_db: AsyncSession | None,
        executable_plan: ExecutablePlan,
        plan_result: Any,
        validation_result: Any,
        user_id: str,
        session_id: str,
    ) -> list[dict[str, Any]]:
        if not active_db:
            return []
        try:
            from app.orchestration.adaptive_replanner import AdaptiveReplanner
            from app.orchestration.step_feedback_collector import StepFeedbackCollector

            collector = StepFeedbackCollector()
            feedback = collector.collect(
                plan=executable_plan,
                plan_result=plan_result,
                validation_result=validation_result,
                user_id=user_id,
                session_id=session_id,
            )
            replanner = AdaptiveReplanner(active_db, redis=self.redis)
            records = await replanner.on_plan_execution_completed(
                user_id=uuid.UUID(user_id),
                plan_id=uuid.UUID(str(executable_plan.plan_id)),
                feedback=feedback,
            )
            return [record.to_dict() if hasattr(record, "to_dict") else record for record in (records or [])]
        except Exception as e:
            logger.warning(f"Failed to publish execution feedback: {e}", exc_info=True)
            return []

    # ------------------------------------------------------------------
    # extract execution feedback from log entry (static)
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_execution_feedback_from_log_entry(entry: dict[str, Any]) -> dict[str, Any] | None:
        if not isinstance(entry, dict):
            return None

        entry_type = str(entry.get("type", "")).strip()
        if entry_type == "plan_execution_feedback":
            feedback = {
                "slow_tools": entry.get("slow_tools", []) or [],
                "failed_tools": entry.get("failed_tools", []) or [],
                "unreliable_dependencies": entry.get("unreliable_dependencies", []) or [],
                "quality_score": entry.get("quality_score"),
            }
            if any(feedback.get(k) for k in ("slow_tools", "failed_tools", "unreliable_dependencies")) or feedback.get("quality_score") is not None:
                return feedback
            return None

        if entry_type == "plan_execution":
            adjustment = entry.get("applied_adjustment") or {}
            if not isinstance(adjustment, dict):
                return None
            feedback = {
                "slow_tools": adjustment.get("slow_tools", []) or [],
                "failed_tools": adjustment.get("failed_tools", []) or [],
                "unreliable_dependencies": adjustment.get("unreliable_dependencies", []) or [],
                "quality_score": adjustment.get("quality_score"),
            }
            if any(feedback.get(k) for k in ("slow_tools", "failed_tools", "unreliable_dependencies")) or feedback.get("quality_score") is not None:
                return feedback
        return None

    # ------------------------------------------------------------------
    # notify pending milestone proposals
    # ------------------------------------------------------------------
    async def _notify_pending_milestone_proposals(
        self,
        user_id: str,
        stream_callback,
    ) -> None:
        """
        Check and send pending milestone proposals to user.
        Called at the start of StreamChat to notify users of pending proposals.
        """
        from app.core.pending_actions import pending_actions_store

        try:
            actions = await pending_actions_store.get_all_by_user(user_id)

            # Find milestone proposals
            milestone_proposals = [
                a for a in actions
                if a.get("tool_name") == "milestone_task_proposal"
            ]

            if not milestone_proposals:
                return

            logger.info(f"Found {len(milestone_proposals)} pending milestone proposal(s) for user {user_id}")

            for proposal_action in milestone_proposals:
                preview = proposal_action.get("preview_data", {})
                if not preview:
                    continue

                await stream_callback(agent_service_pb2.ChatResponse(
                    delta=f"\U0001f389 \u606d\u559c\u8fbe\u6210\u91cc\u7a0b\u7891\uff01\u4e3a\u4f60\u63a8\u8350 {preview.get('suggested_count', 0)} \u4e2a\u65b0\u4efb\u52a1",
                    metadata={
                        "widget_event": "milestone_proposal",
                        "proposal_id": preview.get("proposal_id"),
                        "action_id": proposal_action.get("action_id"),
                        "plan_id": preview.get("plan_id"),
                        "milestone_id": preview.get("milestone_id"),
                        "task_count": preview.get("suggested_count", 0),
                        "reasoning": preview.get("reasoning", ""),
                        "tasks": json.dumps(preview.get("proposed_tasks", [])),
                    }
                ))

        except Exception as e:
            logger.warning(f"Failed to notify milestone proposals: {e}")
