from __future__ import annotations

import asyncio
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from typing import Any

from loguru import logger

from app.core.agent_profiles import AgentRole, ModelTier, TaskType
from app.services.llm_service import get_configured_llm_service_for_tier

JUDGE_CONTRACT_VERSION = "stage11.ev4.judge.v1"
JUDGE_PROMPT_VERSION = "stage11.ev4.judge.v1"
JUDGE_PROMPT = (
    "You are Sparkle's read-only profile evaluation judge. "
    "Score the supplied metric between 0 and 1 based only on the provided evaluation_focus, "
    "metric_id, prompt_context, expected_observation, and rubric_score. "
    "Return strict JSON only with keys: score, rationale, decision_trace, judge_version. "
    "Never emit commands, writes, profile updates, preference edits, strategy updates, or tool invocations. "
    "This output is stored in evaluation_records only."
)


def _normalize_score(value: Any, *, fallback: float) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(0.0, min(1.0, numeric))


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class ProfileEvalJudgeConfig:
    judge_weight: float = 0.3
    timeout_ms: int = 8000
    budget_tokens: int = 1200
    prompt_version: str = JUDGE_PROMPT_VERSION
    enabled: bool = True

    def __post_init__(self) -> None:
        if not 0.1 <= float(self.judge_weight) <= 0.9:
            raise ValueError("judge_weight must stay within [0.1, 0.9]")
        if not 1000 <= int(self.timeout_ms) <= 15000:
            raise ValueError("timeout_ms must stay within [1000, 15000]")
        if not 256 <= int(self.budget_tokens) <= 4096:
            raise ValueError("budget_tokens must stay within [256, 4096]")
        if not str(self.prompt_version).strip():
            raise ValueError("prompt_version must be non-empty")

    @property
    def rubric_weight(self) -> float:
        return round(1.0 - float(self.judge_weight), 3)

    def as_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["rubric_weight"] = self.rubric_weight
        return payload


def build_profile_eval_judge_config(
    *,
    enabled: bool = True,
    judge_weight: float | None = None,
    timeout_ms: int | None = None,
    budget_tokens: int | None = None,
    prompt_version: str | None = None,
) -> ProfileEvalJudgeConfig:
    return ProfileEvalJudgeConfig(
        enabled=enabled,
        judge_weight=judge_weight if judge_weight is not None else _env_float("SPARKLE_PROFILE_EVAL_JUDGE_WEIGHT", 0.3),
        timeout_ms=timeout_ms if timeout_ms is not None else _env_int("SPARKLE_PROFILE_EVAL_JUDGE_TIMEOUT_MS", 8000),
        budget_tokens=budget_tokens
        if budget_tokens is not None
        else _env_int("SPARKLE_PROFILE_EVAL_JUDGE_BUDGET_TOKENS", 1200),
        prompt_version=(prompt_version or os.getenv("SPARKLE_PROFILE_EVAL_JUDGE_PROMPT_VERSION") or JUDGE_PROMPT_VERSION),
    )


class ProfileEvalLLMJudge:
    """Stage 11 real LLM judge adapter for the profile eval runner."""

    def __init__(self, *, config: ProfileEvalJudgeConfig | None = None):
        self.config = config or build_profile_eval_judge_config()

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
                            "judge_config": self.config.as_payload(),
                        },
                        ensure_ascii=True,
                        sort_keys=True,
                    ),
                },
            ]
            raw = await asyncio.wait_for(
                llm.reason_json(messages, temperature=0.0, max_tokens=self.config.budget_tokens),
                timeout=self.config.timeout_ms / 1000.0,
            )
        except Exception as exc:
            logger.warning("ProfileEvalLLMJudge fallback to rubric-only: {}", exc)
            return {
                "score": rubric_score,
                "rationale": f"judge unavailable, fallback to rubric_only: {type(exc).__name__}",
                "decision_trace": "fallback:judge_runtime_unavailable",
                "judge_version": JUDGE_CONTRACT_VERSION,
                "prompt_version": self.config.prompt_version,
                "fallback_used": True,
                "fallback_reason": type(exc).__name__,
                "latency_ms": int(round((time.perf_counter() - started) * 1000)),
                "judge_weight": self.config.judge_weight,
                "rubric_weight": self.config.rubric_weight,
                "timeout_ms": self.config.timeout_ms,
                "budget_tokens": self.config.budget_tokens,
            }

        if not isinstance(raw, dict):
            return {
                "score": rubric_score,
                "rationale": "judge returned non-json payload, fallback to rubric_only",
                "decision_trace": "fallback:non_json_payload",
                "judge_version": JUDGE_CONTRACT_VERSION,
                "prompt_version": self.config.prompt_version,
                "fallback_used": True,
                "fallback_reason": "non_json_payload",
                "latency_ms": int(round((time.perf_counter() - started) * 1000)),
                "judge_weight": self.config.judge_weight,
                "rubric_weight": self.config.rubric_weight,
                "timeout_ms": self.config.timeout_ms,
                "budget_tokens": self.config.budget_tokens,
            }

        score = _normalize_score(raw.get("score"), fallback=rubric_score)
        return {
            "score": score,
            "rationale": str(raw.get("rationale") or "judge attached"),
            "decision_trace": raw.get("decision_trace") or "llm_attached",
            "judge_version": str(raw.get("judge_version") or JUDGE_CONTRACT_VERSION),
            "prompt_version": self.config.prompt_version,
            "fallback_used": bool(raw.get("fallback_used", False)),
            "fallback_reason": str(raw.get("fallback_reason") or "").strip() or None,
            "model": str(getattr(llm, "reason_model", "") or getattr(llm, "chat_model", "") or ""),
            "latency_ms": int(round((time.perf_counter() - started) * 1000)),
            "judge_weight": self.config.judge_weight,
            "rubric_weight": self.config.rubric_weight,
            "timeout_ms": self.config.timeout_ms,
            "budget_tokens": self.config.budget_tokens,
        }

    def __call__(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.a_judge(payload))

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(lambda: asyncio.run(self.a_judge(payload)))
            return future.result()


def build_profile_eval_llm_judge(
    *,
    enabled: bool,
    config: ProfileEvalJudgeConfig | None = None,
) -> ProfileEvalLLMJudge | None:
    effective_config = config or build_profile_eval_judge_config(enabled=enabled)
    if not enabled or not effective_config.enabled:
        return None
    return ProfileEvalLLMJudge(config=effective_config)
