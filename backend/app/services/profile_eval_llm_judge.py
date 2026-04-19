from __future__ import annotations

import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from loguru import logger

from app.core.agent_profiles import AgentRole, ModelTier, TaskType
from app.services.llm_service import get_configured_llm_service_for_tier

JUDGE_CONTRACT_VERSION = "stage10.ev3.judge.v1"
JUDGE_PROMPT = (
    "You are Sparkle's read-only profile evaluation judge. "
    "Score the supplied metric between 0 and 1 based only on the provided evaluation_focus, "
    "metric_id, prompt_context, expected_observation, and rubric_score. "
    "Return strict JSON only with keys: score, rationale, decision_trace, judge_version. "
    "Never emit commands, writes, or profile updates. "
    "This output is stored in evaluation_records only."
)


def _normalize_score(value: Any, *, fallback: float) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(0.0, min(1.0, numeric))


class ProfileEvalLLMJudge:
    """Stage 10 real LLM judge adapter for the profile eval runner."""

    def __init__(self, *, timeout_seconds: float = 8.0):
        self.timeout_seconds = timeout_seconds

    async def a_judge(self, payload: dict[str, Any]) -> dict[str, Any]:
        rubric_score = _normalize_score(payload.get("rubric_score"), fallback=0.0)
        started = time.perf_counter()

        try:
            llm = await get_configured_llm_service_for_tier(
                AgentRole.DEEP_ANALYST,
                ModelTier.STANDARD,
                task_type=TaskType.DEEP_REASONING,
                reasoning_mode="deep",
            )
            messages = [
                {"role": "system", "content": JUDGE_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "evaluation_focus": payload.get("evaluation_focus"),
                            "metric_id": payload.get("metric_id"),
                            "prompt_context": payload.get("prompt_context") or {},
                            "expected_observation": payload.get("expected_observation") or {},
                            "rubric_score": rubric_score,
                        },
                        ensure_ascii=True,
                        sort_keys=True,
                    ),
                },
            ]
            raw = await asyncio.wait_for(
                llm.reason_json(messages, temperature=0.0),
                timeout=self.timeout_seconds,
            )
        except Exception as exc:
            logger.warning("ProfileEvalLLMJudge fallback to rubric-only: {}", exc)
            return {
                "score": rubric_score,
                "rationale": f"judge unavailable, fallback to rubric_only: {type(exc).__name__}",
                "decision_trace": "fallback:judge_runtime_unavailable",
                "judge_version": JUDGE_CONTRACT_VERSION,
                "fallback_used": True,
                "fallback_reason": type(exc).__name__,
                "latency_ms": int(round((time.perf_counter() - started) * 1000)),
            }

        if not isinstance(raw, dict):
            return {
                "score": rubric_score,
                "rationale": "judge returned non-json payload, fallback to rubric_only",
                "decision_trace": "fallback:non_json_payload",
                "judge_version": JUDGE_CONTRACT_VERSION,
                "fallback_used": True,
                "fallback_reason": "non_json_payload",
                "latency_ms": int(round((time.perf_counter() - started) * 1000)),
            }

        score = _normalize_score(raw.get("score"), fallback=rubric_score)
        return {
            "score": score,
            "rationale": str(raw.get("rationale") or "judge attached"),
            "decision_trace": raw.get("decision_trace") or "llm_attached",
            "judge_version": str(raw.get("judge_version") or JUDGE_CONTRACT_VERSION),
            "fallback_used": bool(raw.get("fallback_used", False)),
            "fallback_reason": str(raw.get("fallback_reason") or "").strip() or None,
            "model": str(getattr(llm, "reason_model", "") or getattr(llm, "chat_model", "") or ""),
            "latency_ms": int(round((time.perf_counter() - started) * 1000)),
        }

    def __call__(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.a_judge(payload))

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(lambda: asyncio.run(self.a_judge(payload)))
            return future.result()


def build_profile_eval_llm_judge(*, enabled: bool) -> ProfileEvalLLMJudge | None:
    if not enabled:
        return None
    return ProfileEvalLLMJudge()
