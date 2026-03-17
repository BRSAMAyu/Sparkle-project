from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncGenerator
from typing import Any

from loguru import logger

from app.core.business_metrics import HITL_REQUESTED
from app.core.pending_actions import pending_actions_store
from app.gen.agent.v1 import agent_service_pb2
from app.orchestration.orchestration_trace import OrchestrationTrace
from app.orchestration.schemas import ExecutablePlan, StateSnapshot
from app.orchestration.statechart_engine import WorkflowState


class ObservabilityMixin:
    """Mixin providing observability, tracing, and HITL helpers for the orchestrator."""

    def _roundtrip_ms(self, started_at: float) -> float:
        """Calculate elapsed milliseconds from a perf_counter start time."""
        return max((time.perf_counter() - started_at) * 1000.0, 0.0)

    def _sync_orchestration_trace(
        self,
        *,
        state: WorkflowState,
        orchestration_trace: OrchestrationTrace | None,
        user_context_payload: dict[str, Any] | None = None,
    ) -> None:
        if orchestration_trace is None:
            return
        payload = orchestration_trace.to_metadata()
        state.context_data["orchestration_trace"] = payload
        if isinstance(user_context_payload, dict):
            user_context_payload["orchestration_trace"] = payload

    async def _emit_orchestration_trace(
        self,
        *,
        state: WorkflowState,
        orchestration_trace: OrchestrationTrace | None,
        stream_callback,
    ) -> None:
        if orchestration_trace is None or not orchestration_trace.steps:
            return
        payload = orchestration_trace.to_metadata()
        state.context_data["orchestration_trace"] = payload
        try:
            await stream_callback(
                agent_service_pb2.ChatResponse(
                    metadata={
                        "event_type": "orchestration_trace",
                        "trace": json.dumps(payload, ensure_ascii=False),
                    }
                )
            )
        except Exception as exc:
            logger.debug(f"Failed to emit orchestration trace: {exc}")

    async def _stream_hitl_escalation(
        self,
        *,
        conflict,
        executable_plan: ExecutablePlan,
        snapshot: StateSnapshot | None,
        user_id: str,
        stream_callback,
    ) -> None:
        tool_calls_payload = [{"id": tc.id, "name": tc.name, "params": tc.params} for tc in executable_plan.tool_calls]
        action_id = await pending_actions_store.save(
            tool_name="__plan_version_conflict__",
            arguments={
                "plan_id": executable_plan.plan_id,
                "snapshot_id": snapshot.snapshot_id if snapshot else None,
                "tool_calls": tool_calls_payload,
                "reason": "version_conflict",
                "conflicted_domains": list(conflict.conflicted_domains),
            },
            user_id=user_id,
            description="检测到状态变更，是否继续执行该计划？",
            preview_data={
                "plan_id": executable_plan.plan_id,
                "conflicted_domains": list(conflict.conflicted_domains),
                "affected_domains": list(conflict.affected_domains),
                "tool_calls": tool_calls_payload,
            },
        )
        HITL_REQUESTED.labels(reason="version_conflict").inc()
        await stream_callback(agent_service_pb2.ChatResponse(
            delta=("\n\n⚠️ 检测到状态变化，需要确认后继续执行。\n" f"action_id={action_id}"),
            metadata={"requires_hitl": "true", "action_id": action_id, "reason": "version_conflict"},
        ))

    async def _stream_discard_notice(self, stream_callback) -> None:
        await stream_callback(agent_service_pb2.ChatResponse(
            delta="\n\n⚠️ 检测到状态变化，计划已过期。请重试。",
        ))

    def _extract_llm_profile_meta(self, user_context_payload: dict[str, Any] | None) -> dict[str, Any]:
        llm_profile_meta = {}
        if not isinstance(user_context_payload, dict):
            return llm_profile_meta
        llm_profile = user_context_payload.get("llm_profile")
        if not llm_profile:
            return llm_profile_meta
        if isinstance(llm_profile, str):
            try:
                llm_profile_meta = json.loads(llm_profile)
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Failed to parse llm_profile JSON string: {llm_profile[:100] if llm_profile else 'None'}")
                llm_profile_meta = {}
        elif isinstance(llm_profile, dict):
            llm_profile_meta = llm_profile
        else:
            logger.warning(f"Unexpected llm_profile type: {type(llm_profile)}")
        return llm_profile_meta

    async def _drain_queue(
        self,
        queue: asyncio.Queue,
        timeout: float = 5.0,
    ) -> AsyncGenerator[agent_service_pb2.ChatResponse, None]:
        """
        Drain all queued responses with exception protection.

        Ensures all queued messages are yielded even if errors occur during processing.
        Uses finally block to guarantee queue cleanup.

        Args:
            queue: The asyncio.Queue to drain
            timeout: Maximum time to wait for each queue item (default 5.0 seconds)

        Yields:
            ChatResponse items from the queue
        """
        processed_count = 0
        try:
            while not queue.empty():
                try:
                    # Add timeout to prevent indefinite blocking
                    item = await asyncio.wait_for(queue.get(), timeout=timeout)
                    processed_count += 1
                    yield item
                except asyncio.TimeoutError:
                    logger.warning(f"Queue drain timeout after {processed_count} items")
                    break
                except Exception as e:
                    logger.error(f"Error processing queued item: {e}")
                    # Continue processing remaining items
        finally:
            # Mark all processed items as done
            for _ in range(processed_count):
                try:
                    queue.task_done()
                except Exception:
                    pass
