import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, Optional

from loguru import logger
import grpc

from app.core.cache import cache_service
from app.config import settings
from app.services.llm_service import llm_service
from app.services.quota import get_rate_limiter
from app.services.circuit_breaker import circuit_breaker_service, CircuitBreakerOpenException
from app.gen.sparkle.inference.v1 import inference_pb2
from app.services.feature_extraction_service import feature_extraction_service
from app.services.signal_generation_service import signal_generation_service
from app.services.candidate_generation_service import candidate_generation_service


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
    def __init__(self, cache_config: Optional[CacheConfig] = None):
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

        except CircuitBreakerOpenException as exc:
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

            # 5. Format response
            response_data = {
                "candidates": [c.to_dict() for c in candidates],
                "features": features.to_dict(),
                "signals": signals.to_dict(),
                "pipeline_version": "v2",
            }

            return inference_pb2.InferenceResponse(
                request_id=request.request_id,
                trace_id=request.trace_id,
                ok=True,
                provider="signals_pipeline",
                model_id="sig_v2",
                content=json.dumps(response_data, ensure_ascii=False),
            )

        except Exception as exc:
            logger.exception("PREDICT_NEXT_ACTIONS failed")
            return self._error_response(
                request,
                inference_pb2.PROVIDER_UNAVAILABLE,
                f"Signal generation failed: {str(exc)}"
            )

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
        }
        raw = json.dumps(payload, ensure_ascii=True, sort_keys=True)
        content_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        model_id = self._select_model(request)
        schema_key = request.schema_version or request.output_schema
        return f"inference:{model_id}:{request.prompt_version}:{schema_key}:{content_hash}"

    async def _cache_get(self, key: str) -> Optional[Dict[str, Any]]:
        if not cache_service.redis:
            await cache_service.init_redis()
        if not cache_service.redis:
            return None
        return await cache_service.get(key)

    async def _cache_set(self, key: str, value: Dict[str, Any], request: inference_pb2.InferenceRequest) -> None:
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
