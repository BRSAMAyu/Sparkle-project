from __future__ import annotations

import sys
from pathlib import Path

import grpc
from loguru import logger

_GEN_ROOT = Path(__file__).resolve().parents[1] / "gen"
_gen_root_str = str(_GEN_ROOT)
if _gen_root_str not in sys.path:
    sys.path.append(_gen_root_str)

from sparkle.inference.v1 import inference_pb2_grpc

from app.services.llm_dispatcher import ERROR_REASON_TO_STATUS, LLMDispatcher


class InferenceGrpcServiceImpl(inference_pb2_grpc.InferenceServiceServicer):
    """gRPC adapter for the unified LLM dispatcher."""

    def __init__(self, dispatcher: LLMDispatcher | None = None):
        self.dispatcher = dispatcher or LLMDispatcher()

    async def RunInference(self, request, context):
        try:
            response = await self.dispatcher.run(request)
            if not response.ok and response.error_reason in ERROR_REASON_TO_STATUS:
                context.set_code(ERROR_REASON_TO_STATUS[response.error_reason])
                context.set_details(response.error_message or "Inference request failed")
            return response
        except Exception:
            logger.exception("gRPC RunInference failed")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Inference request failed")
            from app.gen.sparkle.inference.v1 import inference_pb2

            return inference_pb2.InferenceResponse(
                request_id=request.request_id,
                trace_id=request.trace_id,
                ok=False,
                error_reason=inference_pb2.PROVIDER_UNAVAILABLE,
                error_message="Inference request failed",
            )
