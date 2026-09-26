from __future__ import annotations

import contextlib
import json
import uuid
from typing import Any, Callable

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time_utils import utcnow
from app.gen.agent.v1 import agent_service_pb2
from app.models.chat import ChatMessage, ChatSession, MessageRole
from app.orchestration.schemas import ExecutablePlan
from app.services.llm_service import llm_service
from app.services.memory_inferred_write_lane import MemoryInferredWriteLaneService


# B-01（V13「发了但看不见」）：WS/gRPC 主链此前只写 chat_messages、从不写
# chat_sessions 头——网关 Redis persister（chat_history_persister.go 的
# chatSessionUpsertSQL）是 WS 路径唯一的 session 头写入者，但
# CHAT_PERSISTER_ENABLED 默认 false（engine 是 single authoritative writer），
# 于是 onboarding→chat 的第一个 session 在 chat_sessions 永远缺行：
# 网关 GET /api/v1/chat/sessions（getRecentSessionsFromDB）只读该表 →
# 空列表 → 移动端重启后拿不到 conversationId，历史不可达。
# 修法与 REST api/v1/chat.py save_chat_message 的 get-or-create 同构：
# 幂等补建头行；零 UUID（context_builder 对 legacy label 的降级产物）
# 跳过——它跨用户共用主键，且 sessions 列表查询本就排除它。
async def ensure_chat_session_header(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> None:
    """Idempotently ensure the chat_sessions header row exists (B-01)."""
    if session_id == uuid.UUID(int=0):
        return
    now = utcnow()
    session_meta = await db.get(ChatSession, session_id)
    if session_meta is None:
        db.add(ChatSession(id=session_id, user_id=user_id, is_active=True, last_message_at=now))
    else:
        session_meta.is_active = True
        session_meta.last_message_at = now


class PersistenceLayerMixin:
    """Mixin that groups persistence / side-effect helpers used by ChatOrchestrator."""
    redis: Any
    _coerce_session_uuid: Callable[..., Any]

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
        user_message: str | None = None,
    ) -> None:
        if not active_db or not full_response:
            return
        try:
            # 共享 gRPC 流 session 可能已被本轮更早的无关异常（如计划执行写
            # plan_states 的 FK violation）滚进 poisoned 状态，直接复用会让
            # 聊天持久化以 "transaction has been rolled back" 陪葬，记忆写入
            # lane 随之失去触发点。assistant 消息无外键依赖共享事务内未提交
            # 行（user 消息由网关侧先独立落库），改用独立 session 自持提交。
            from app.db.session import AsyncSessionLocal

            async with AsyncSessionLocal() as persist_session:
                # B-01：turn 收尾在独立 session 内幂等补建 session 头，与
                # assistant 行同事务提交——即使共享流 session 回滚（此路径
                # 存在的既有语义），消息与头也不出现"有消息无会话"的孤儿态。
                try:
                    await ensure_chat_session_header(
                        persist_session,
                        user_id=uuid.UUID(str(user_id)),
                        session_id=self._coerce_session_uuid(session_id),
                    )
                except Exception as header_err:
                    logger.warning(f"Failed to ensure chat session header (non-fatal): {header_err}")
                assistant_msg = ChatMessage(
                    user_id=uuid.UUID(str(user_id)),
                    session_id=self._coerce_session_uuid(session_id),
                    role=MessageRole.ASSISTANT,
                    content=full_response,
                    model_name=getattr(llm_service, "default_model", None),
                )
                persist_session.add(assistant_msg)
                await persist_session.flush()
                # NBP-1（2026-09-22）：WS/gRPC 轮次收尾的推断写账统一走与
                # REST api/v1/chat.py save_chat_message 同一个捕获面
                # enqueue_from_chat_turn（单一事实源）。调用方在手用户原文时
                # 必须传入 user_message——否则只能靠 enqueue_from_session 的
                # DB 回捞（_load_latest_user_turn），而 WS 链路的 user 行由
                # 网关 Redis persister 异步落库，一次性后台任务稳输竞态
                # （missing_user_turn → 本轮声明事实永久丢失，LOOP2 B1 实锤
                # 0 条）。无 user_message 的旧调用方保持原行为零变化。
                resolved_user_message = str(user_message or "").strip()
                if resolved_user_message:
                    MemoryInferredWriteLaneService.enqueue_from_chat_turn(
                        user_id=uuid.UUID(str(user_id)),
                        session_id=self._coerce_session_uuid(session_id),
                        user_message=resolved_user_message,
                        assistant_message=full_response,
                        user_message_id=str(assistant_msg.id),
                        assistant_message_id=str(assistant_msg.id),
                    )
                else:
                    MemoryInferredWriteLaneService.enqueue_from_session(
                        user_id=uuid.UUID(str(user_id)),
                        session_id=self._coerce_session_uuid(session_id),
                        assistant_message_id=str(assistant_msg.id),
                        assistant_message=full_response,
                    )
                await persist_session.commit()
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
            logger.opt(exception=e).warning(f"Failed to publish execution feedback: {e}")
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

                # V3-FIX-264：metadata 是 proto map<string,string>（agent_service.proto:214），
                # preview_data 是任意 dict——缺键/None/int 直传会在 protobuf 赋值期
                # TypeError: bad argument type for built-in operation，被下方 except
                # 吞成 warning，里程碑通知静默丢失。全值 str 化缺省策略：
                # proposal_id 为引用键，空串即规范缺席值（proto3 map 无法表达缺席；
                # 本通知为展示面，确认流走 action_id/pending_actions，不依赖此键，
                # 空串与真实 ID（uuid/rp-/ap- 前缀）可区分，非静默吞数据）。
                suggested_count = preview.get("suggested_count") or 0
                await stream_callback(agent_service_pb2.ChatResponse(
                    delta=f"\U0001f389 \u606d\u559c\u8fbe\u6210\u91cc\u7a0b\u7891\uff01\u4e3a\u4f60\u63a8\u8350 {suggested_count} \u4e2a\u65b0\u4efb\u52a1",
                    metadata={
                        "widget_event": "milestone_proposal",
                        "proposal_id": str(preview.get("proposal_id") or ""),
                        "action_id": str(proposal_action.get("action_id") or ""),
                        "plan_id": str(preview.get("plan_id") or ""),
                        "milestone_id": str(preview.get("milestone_id") or ""),
                        "task_count": str(suggested_count),
                        "reasoning": str(preview.get("reasoning") or ""),
                        "tasks": json.dumps(preview.get("proposed_tasks") or []),
                    }
                ))

        except Exception as e:
            logger.warning(f"Failed to notify milestone proposals: {e}")
