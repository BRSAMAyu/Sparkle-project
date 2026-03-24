from __future__ import annotations
import asyncio
import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any

import grpc
from loguru import logger

from app.config import settings
from app.core.agent_profiles import AgentRole, ModelTier, TaskType as RouterTaskType
from app.core.cache import cache_service
from app.core.metrics import AI_PREDICTION_DURATION, AI_PREDICTION_FALLBACK_TOTAL
from google.api import annotations_pb2  # noqa: F401

from app.gen.sparkle.inference.v1 import inference_pb2
from app.services.candidate_generation_service import candidate_generation_service
from app.services.circuit_breaker import CircuitBreakerOpenException, circuit_breaker_service
from app.services.feature_extraction_service import feature_extraction_service
from app.services.llm_service import get_configured_llm_service_for_tier, llm_service
from app.services.quota import get_rate_limiter
from app.services.signal_generation_service import signal_generation_service


@dataclass
class CacheConfig:
    default_ttl_seconds: int = 300
    signal_ttl_seconds: int = 300
    embedding_ttl_seconds: int = 86400 * 7


class InferenceException(Exception):
    def __init__(self, reason: inference_pb2.ErrorReason, message: str):
        super().__init__(message)
        self.reason = reason
        self.message = message


ERROR_REASON_TO_STATUS = {
    inference_pb2.QUOTA_EXCEEDED: grpc.StatusCode.RESOURCE_EXHAUSTED,
    inference_pb2.PROVIDER_UNAVAILABLE: grpc.StatusCode.UNAVAILABLE,
    inference_pb2.SCHEMA_VIOLATION: grpc.StatusCode.INVALID_ARGUMENT,
    inference_pb2.BUDGET_EXHAUSTED: grpc.StatusCode.PERMISSION_DENIED,
    inference_pb2.TIMEOUT: grpc.StatusCode.DEADLINE_EXCEEDED,
}


class LLMDispatcher:
    def __init__(self, cache_config: CacheConfig | None = None):
        self.cache_config = cache_config or CacheConfig()

    async def run(self, request: inference_pb2.InferenceRequest) -> inference_pb2.InferenceResponse:
        self._validate_request(request)

        # Special handling for PREDICT_NEXT_ACTIONS
        if request.task_type == inference_pb2.PREDICT_NEXT_ACTIONS:
            return await self._handle_predict_next_actions(request)

        cache_key = self._cache_key(request)
        cached = await self._cache_get(cache_key)
        if cached:
            return inference_pb2.InferenceResponse(
                request_id=request.request_id,
                trace_id=request.trace_id,
                ok=True,
                provider="cache",
                model_id=cached.get("model_id", ""),
                content=cached.get("content", ""),
            )

        limiter = await get_rate_limiter()
        estimated_tokens = self._estimate_tokens(request)
        quota = await limiter.check_and_decr(request.user_id, estimated_tokens)
        if not quota.allowed:
            return self._error_response(
                request,
                inference_pb2.QUOTA_EXCEEDED,
                "Quota exceeded",
            )

        provider_name = settings_provider_name()
        try:
            # 1. Check Circuit Breaker
            await circuit_breaker_service.check(provider_name)

            model_id = self._select_model(request)
            messages = [
                {"role": msg.role, "content": msg.content}
                for msg in request.messages
            ]

            # 2. Call LLM
            content = await llm_service.chat(messages, model=model_id)

            # 3. Record Success
            await circuit_breaker_service.record_success(provider_name)

            response = inference_pb2.InferenceResponse(
                request_id=request.request_id,
                trace_id=request.trace_id,
                ok=True,
                provider=provider_name,
                model_id=model_id,
                content=content,
            )
            await self._cache_set(cache_key, {"content": content, "model_id": model_id}, request)
            return response

        except CircuitBreakerOpenException:
            logger.warning(f"Circuit open for {provider_name}")
            return self._error_response(request, inference_pb2.PROVIDER_UNAVAILABLE, "Service temporarily unavailable (Circuit Open)")
        except InferenceException as exc:
            return self._error_response(request, exc.reason, exc.message)
        except grpc.RpcError as exc:
            # Record failure for network/availability issues
            await circuit_breaker_service.record_failure(provider_name)

            reason = inference_pb2.PROVIDER_UNAVAILABLE
            if exc.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
                reason = inference_pb2.TIMEOUT
            return self._error_response(request, reason, exc.details() or "gRPC error")
        except Exception as exc:
            # Record failure for unknown exceptions (likely provider issues)
            await circuit_breaker_service.record_failure(provider_name)

            logger.exception("Inference failed")
            return self._error_response(request, inference_pb2.PROVIDER_UNAVAILABLE, str(exc))

    async def _handle_predict_next_actions(
        self,
        request: inference_pb2.InferenceRequest
    ) -> inference_pb2.InferenceResponse:
        """
        Handle PREDICT_NEXT_ACTIONS task type.

        Pipeline:
        1. Parse ContextEnvelope from metadata
        2. Feature extraction (objective metrics)
        3. Signal generation (decision-ready signals)
        4. Candidate generation (actionable suggestions with constraints)

        Args:
            request: InferenceRequest with ContextEnvelope in metadata

        Returns:
            InferenceResponse with candidate actions in content (JSON)
        """
        start_time = time.perf_counter()
        prediction_source = "rules"
        prediction_tier = "rules"
        used_fallback = False
        try:
            # 1. Parse ContextEnvelope from metadata
            envelope_json = request.metadata.get("context_envelope")
            if not envelope_json:
                return self._error_response(
                    request,
                    inference_pb2.SCHEMA_VIOLATION,
                    "Missing context_envelope in metadata"
                )

            try:
                envelope = json.loads(envelope_json)
            except json.JSONDecodeError as e:
                return self._error_response(
                    request,
                    inference_pb2.SCHEMA_VIOLATION,
                    f"Invalid context_envelope JSON: {str(e)}"
                )

            logger.info(
                f"PREDICT_NEXT_ACTIONS request: user={request.user_id}, "
                f"window={envelope.get('window', 'unknown')}"
            )

            # 2. Feature extraction
            features = feature_extraction_service.extract(envelope)
            logger.debug(
                f"Features extracted: rhythm.deviating={features.rhythm.deviating_from_plan}, "
                f"friction.density={features.friction.translation_density}, "
                f"energy.fatigue={features.energy.late_night_fatigue}"
            )

            # 3. Signal generation
            signals = signal_generation_service.generate(features)
            logger.info(
                f"Signals generated: count={len(signals.signals)}, "
                f"types={[s.type for s in signals.signals]}"
            )

            # 4. Candidate generation with constraints
            candidates = await candidate_generation_service.generate_candidates(
                user_id=request.user_id,
                signals=signals
            )
            logger.info(
                f"Candidates generated: count={len(candidates)}, "
                f"types={[c.action_type for c in candidates]}"
            )

            response_data = {
                "candidates": [c.to_dict() for c in candidates],
                "features": features.to_dict(),
                "signals": signals.to_dict(),
                "pipeline_version": "v2",
                "prediction_source": "rules",
                "prediction_tier": "rules",
                "fallback_used": False,
            }

            llm_enrichment = await self._try_llm_predict_next_actions(
                user_id=request.user_id,
                envelope=envelope,
                features=features.to_dict(),
                signals=signals.to_dict(),
                rule_candidates=response_data["candidates"],
            )
            if llm_enrichment is not None:
                prediction_source = str(llm_enrichment.get("prediction_source") or "free_fast_llm")
                prediction_tier = str(llm_enrichment.get("prediction_tier") or "free_fast")
                response_data.update(llm_enrichment)
            else:
                used_fallback = True
                if not response_data["candidates"]:
                    response_data["candidates"] = self._build_minimum_rule_candidates(envelope)
            response_data["fallback_used"] = used_fallback

            latency_ms = int((time.perf_counter() - start_time) * 1000)
            AI_PREDICTION_DURATION.labels(
                source=prediction_source,
                tier=prediction_tier,
                fallback="true" if used_fallback else "false",
            ).observe(max(latency_ms / 1000.0, 0.0))
            response_data["latency_ms"] = latency_ms

            return inference_pb2.InferenceResponse(
                request_id=request.request_id,
                trace_id=request.trace_id,
                ok=True,
                provider="signals_pipeline" if used_fallback else prediction_source,
                model_id="sig_v2" if used_fallback else prediction_tier,
                content=json.dumps(response_data, ensure_ascii=False),
            )

        except Exception as exc:
            logger.exception("PREDICT_NEXT_ACTIONS failed")
            AI_PREDICTION_DURATION.labels(
                source=prediction_source,
                tier=prediction_tier,
                fallback="true",
            ).observe(max((time.perf_counter() - start_time), 0.0))
            return self._error_response(
                request,
                inference_pb2.PROVIDER_UNAVAILABLE,
                f"Signal generation failed: {str(exc)}"
            )

    async def _try_llm_predict_next_actions(
        self,
        *,
        user_id: str,
        envelope: dict[str, Any],
        features: dict[str, Any],
        signals: dict[str, Any],
        rule_candidates: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        prompt_messages = [
            {
                "role": "system",
                "content": (
                    "你是用户行为预测助手。请基于当前上下文给出 0-3 条轻量、具体、低打扰的下一步建议。"
                    "输出必须是 JSON 对象，格式为 "
                    "{\"summary\": string, \"candidates\": [{\"action_type\": string, \"title\": string, "
                    "\"reason\": string, \"confidence\": number, \"timing_hint\": string, "
                    "\"payload_seed\": string, \"metadata\": object}] }。"
                    "如果规则候选已经足够合适，可以保留或微调；不要输出空泛建议。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "user_id": user_id,
                        "context_envelope": envelope,
                        "features": features,
                        "signals": signals,
                        "rule_candidates": rule_candidates,
                    },
                    ensure_ascii=False,
                ),
            },
        ]

        attempts = [
            (
                ModelTier.FREE,
                "free_llm",
                float(getattr(settings, "AI_PREDICTION_FREE_TIMEOUT_SECONDS", 1.5)),
            ),
            (
                ModelTier.FREE_FAST,
                "free_fast_llm",
                float(getattr(settings, "AI_PREDICTION_FREE_FAST_TIMEOUT_SECONDS", 2.5)),
            ),
        ]
        previous_source: str | None = None
        for tier, source, timeout_seconds in attempts:
            try:
                service = await get_configured_llm_service_for_tier(
                    AgentRole.RETRIEVAL,
                    tier,
                    task_type=RouterTaskType.ROUTING,
                    reasoning_mode="fast",
                )
                payload = await asyncio.wait_for(
                    service.chat_json(
                        prompt_messages,
                        temperature=0.2,
                        max_tokens=450,
                    ),
                    timeout=timeout_seconds,
                )
                normalized = self._normalize_prediction_payload(payload)
                if normalized is None:
                    raise ValueError("empty_or_invalid_prediction_payload")
                normalized["prediction_source"] = source
                normalized["prediction_tier"] = tier.value
                normalized["fallback_used"] = False
                if previous_source is not None and previous_source != source:
                    AI_PREDICTION_FALLBACK_TOTAL.labels(
                        from_source=previous_source,
                        to_source=source,
                    ).inc()
                return normalized
            except Exception as exc:
                logger.warning(
                    f"Prediction LLM attempt failed: source={source} tier={tier.value} err={exc}"
                )
                previous_source = source
                continue

        if previous_source is not None:
            AI_PREDICTION_FALLBACK_TOTAL.labels(
                from_source=previous_source,
                to_source="rules",
            ).inc()
        return None

    def _build_minimum_rule_candidates(self, envelope: dict[str, Any]) -> list[dict[str, Any]]:
        focus = envelope.get("focus", {}) if isinstance(envelope, dict) else {}
        comprehension = envelope.get("comprehension", {}) if isinstance(envelope, dict) else {}
        content = envelope.get("content", {}) if isinstance(envelope, dict) else {}

        unknown_terms = int(comprehension.get("unknown_terms_saved") or 0)
        planned_min = int(focus.get("planned_min") or 0)
        actual_min = int(focus.get("actual_min") or 0)
        interruptions = int(focus.get("interruptions") or 0)
        completion = float(focus.get("completion") or 0.0)
        domain = str(content.get("domain") or "general")

        if unknown_terms > 0:
            return [
                {
                    "id": "",
                    "action_type": "review_terms",
                    "title": "查看刚保存的术语",
                    "reason": "你刚完成一轮学习，先回看术语能把新知识更快固定下来。",
                    "confidence": 0.74,
                    "timing_hint": "now",
                    "payload_seed": "review_saved_terms",
                    "metadata": {
                        "count": unknown_terms,
                        "domain": domain,
                    },
                }
            ]

        if planned_min > 0 and actual_min < planned_min:
            return [
                {
                    "id": "",
                    "action_type": "plan_split",
                    "title": "把下一轮任务拆成 20 分钟小步",
                    "reason": "这次实际时长低于计划时长，下一轮拆小会更容易连续完成。",
                    "confidence": 0.71,
                    "timing_hint": "after_current_task",
                    "payload_seed": "split_next_learning_block",
                    "metadata": {
                        "planned_min": planned_min,
                        "actual_min": actual_min,
                        "completion": completion,
                    },
                }
            ]

        if interruptions >= 2:
            return [
                {
                    "id": "",
                    "action_type": "break",
                    "title": "先做一个 3 分钟重置",
                    "reason": "刚才学习中断偏多，短暂重置能减少下一轮分心。",
                    "confidence": 0.68,
                    "timing_hint": "now",
                    "payload_seed": "reset_after_interruptions",
                    "metadata": {
                        "interruptions": interruptions,
                    },
                }
            ]

        return [
            {
                "id": "",
                "action_type": "review",
                "title": "用 5 分钟回顾刚完成的内容",
                "reason": "趁记忆还新鲜做一次短回顾，能提升后续保留率。",
                "confidence": 0.66,
                "timing_hint": "in_5min",
                "payload_seed": "quick_post_session_review",
                "metadata": {
                    "domain": domain,
                },
            }
        ]

    def _normalize_prediction_payload(self, payload: Any) -> dict[str, Any] | None:
        if not isinstance(payload, dict):
            return None

        raw_candidates = payload.get("candidates")
        if not isinstance(raw_candidates, list):
            return None

        candidates: list[dict[str, Any]] = []
        for item in raw_candidates[:3]:
            if not isinstance(item, dict):
                continue
            action_type = str(item.get("action_type") or "").strip()
            title = str(item.get("title") or "").strip()
            reason = str(item.get("reason") or "").strip()
            if not action_type or not title or not reason:
                continue
            try:
                confidence = float(item.get("confidence") or 0.0)
            except (TypeError, ValueError):
                confidence = 0.0
            confidence = min(max(confidence, 0.0), 1.0)
            candidates.append(
                {
                    "id": str(item.get("id") or ""),
                    "action_type": action_type,
                    "title": title,
                    "reason": reason,
                    "confidence": confidence,
                    "timing_hint": str(item.get("timing_hint") or "now"),
                    "payload_seed": str(item.get("payload_seed") or action_type),
                    "metadata": item.get("metadata") if isinstance(item.get("metadata"), dict) else {},
                }
            )

        if not candidates:
            return None

        return {
            "summary": str(payload.get("summary") or "").strip(),
            "candidates": candidates,
        }

    def _validate_request(self, request: inference_pb2.InferenceRequest) -> None:
        if not request.request_id or not request.trace_id:
            raise InferenceException(inference_pb2.SCHEMA_VIOLATION, "Missing request_id or trace_id")
        if request.task_type == inference_pb2.TASK_TYPE_UNSPECIFIED:
            raise InferenceException(inference_pb2.SCHEMA_VIOLATION, "Missing task_type")
        if request.budgets.max_output_tokens == 0:
            raise InferenceException(inference_pb2.SCHEMA_VIOLATION, "max_output_tokens required")
        if not request.schema_version and not request.output_schema:
            raise InferenceException(inference_pb2.SCHEMA_VIOLATION, "schema_version or output_schema required")

    def _estimate_tokens(self, request: inference_pb2.InferenceRequest) -> int:
        prompt_chars = sum(len(msg.content) for msg in request.messages)
        estimated_in = max(1, prompt_chars // 4)
        return estimated_in + int(request.budgets.max_output_tokens)

    def _select_model(self, request: inference_pb2.InferenceRequest) -> str:
        if request.task_type in (inference_pb2.HEAVY_JOB, inference_pb2.VERIFY_PLAN):
            return llm_service.reason_model
        return llm_service.chat_model

    def _cache_key(self, request: inference_pb2.InferenceRequest) -> str:
        payload = {
            "user_id": request.user_id,
            "task_type": int(request.task_type),
            "messages": [
                {"role": msg.role, "content": msg.content}
                for msg in request.messages
            ],
            "tools": [
                {"name": tool.name, "description": tool.description, "schema_json": tool.schema_json}
                for tool in request.tools
            ],
            "response_format": int(request.response_format),
            "metadata": dict(request.metadata),
            "file_ids": list(request.file_ids),
            "artifact_scope": int(request.artifact_scope),
        }
        raw = json.dumps(payload, ensure_ascii=True, sort_keys=True)
        content_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        model_id = self._select_model(request)
        schema_key = request.schema_version or request.output_schema
        return f"inference:{model_id}:{request.prompt_version}:{schema_key}:{content_hash}"

    async def _cache_get(self, key: str) -> dict[str, Any] | None:
        if not cache_service.redis:
            await cache_service.init_redis()
        if not cache_service.redis:
            return None
        return await cache_service.get(key)

    async def _cache_set(self, key: str, value: dict[str, Any], request: inference_pb2.InferenceRequest) -> None:
        if not cache_service.redis:
            await cache_service.init_redis()
        if not cache_service.redis:
            return
        ttl = self._cache_ttl(request)
        await cache_service.set(key, value, ttl=ttl)

    def _cache_ttl(self, request: inference_pb2.InferenceRequest) -> int:
        if request.task_type == inference_pb2.SIGNAL_EXTRACTION:
            return self.cache_config.signal_ttl_seconds
        if request.task_type == inference_pb2.EMBEDDING:
            return self.cache_config.embedding_ttl_seconds
        return self.cache_config.default_ttl_seconds

    def _error_response(
        self,
        request: inference_pb2.InferenceRequest,
        reason: inference_pb2.ErrorReason,
        message: str,
    ) -> inference_pb2.InferenceResponse:
        return inference_pb2.InferenceResponse(
            request_id=request.request_id,
            trace_id=request.trace_id,
            ok=False,
            error_reason=reason,
            error_message=message,
        )


def settings_provider_name() -> str:
    return settings.LLM_PROVIDER or "default"
