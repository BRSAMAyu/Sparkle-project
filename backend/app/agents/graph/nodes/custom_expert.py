from __future__ import annotations

import time
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.graph.llm_factory import LLMFactory
from app.agents.graph.state import SparkleState
from app.core.agent_profiles import ModelTier
from app.core.llm_router import llm_router
from app.orchestration.agent_activity import emit_agent_activity, get_stream_callback
from app.services.custom_expert_service import is_custom_expert_id


def _resolve_runtime_custom_profile(state: SparkleState) -> tuple[str | None, dict[str, Any] | None]:
    current_target = str(state.get("active_agent") or state.get("next_step") or "").strip()
    profiles = state.get("_custom_expert_profiles") or {}
    if not isinstance(profiles, dict) or not is_custom_expert_id(current_target):
        return None, None
    payload = profiles.get(current_target)
    if not isinstance(payload, dict):
        return current_target, None
    return current_target, payload


async def custom_expert_node(state: SparkleState, config: dict | None = None) -> dict[str, Any]:
    stream_cb = get_stream_callback(config)
    started_at = time.time()
    custom_id, profile = _resolve_runtime_custom_profile(state)
    display_name = str((profile or {}).get("display_name") or custom_id or "自定义专家")
    activity_metadata = {
        "collaboration_mode": str(state.get("collaboration_mode") or ""),
        "phase": "analysis",
        "custom_expert": "true",
        "display_name": display_name,
    }
    await emit_agent_activity(
        stream_cb,
        agent_id=custom_id or "custom_expert",
        status="active",
        metadata=activity_metadata,
    )

    messages = list(state.get("messages") or [])
    collaboration_context = state.get("collaboration_context")
    if collaboration_context:
        messages.append(HumanMessage(content=f"[Custom expert context] {collaboration_context}"))

    if profile:
        system_prompt = str(profile.get("system_prompt") or "").strip()
        if system_prompt:
            messages.insert(0, SystemMessage(content=system_prompt))

    preferred_model_key = str((profile or {}).get("preferred_model_key") or "").strip() or None
    preferred_tier = str((profile or {}).get("preferred_model_tier") or "").strip() or None
    if preferred_model_key:
        llm = LLMFactory.get_llm("generation", override_model=preferred_model_key)
    elif preferred_tier:
        try:
            selection = llm_router.select_model("generation", force_tier=ModelTier(preferred_tier))
            llm = LLMFactory.get_llm("generation", override_model=selection.model_key)
        except Exception:
            llm = LLMFactory.get_llm("generation")
    else:
        llm = LLMFactory.get_llm("generation")

    response = await llm.ainvoke(messages)
    duration_ms = (time.time() - started_at) * 1000
    await emit_agent_activity(
        stream_cb,
        agent_id=custom_id or "custom_expert",
        status="completed",
        duration_ms=duration_ms,
        result_summary=str(getattr(response, "content", "") or "")[:80] or display_name,
        metadata=activity_metadata,
    )
    return {
        "messages": [response],
        "active_agent": custom_id or "custom_expert",
        "next_step": None,
    }
