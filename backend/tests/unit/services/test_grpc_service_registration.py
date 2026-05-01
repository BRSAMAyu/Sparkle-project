from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import grpc
import pytest
import pytest_asyncio
from grpc_reflection.v1alpha import reflection, reflection_pb2, reflection_pb2_grpc

GEN_ROOT = Path(__file__).resolve().parents[3] / "app" / "gen"
for path in (GEN_ROOT, GEN_ROOT / "stt" / "v1"):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.append(path_str)

from sparkle.inference.v1 import inference_pb2_grpc

from app.gen import community_service_pb2, stt_service_pb2, stt_service_pb2_grpc
from app.gen.sparkle.inference.v1 import inference_pb2
from grpc_server import DEPRECATED_PROTO_SERVICE_NAMES, register_grpc_services, registered_grpc_service_names


class _DummySessionContext:
    async def __aenter__(self):
        return SimpleNamespace()

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


def _dummy_session_factory():
    return _DummySessionContext()


class _FakeOrchestrator:
    redis = None


class _FakeSTTService:
    provider = SimpleNamespace()
    backup_provider = None
    stream_provider = None

    async def enhance_transcript(self, text: str) -> str:
        return f"{text}!"

    async def transcribe_file(self, file_path: str, language: str | None = None):
        return {"text": f"transcribed:{language or 'auto'}", "error": False}


class _FakeInferenceDispatcher:
    async def run(self, request):
        return inference_pb2.InferenceResponse(
            request_id=request.request_id,
            trace_id=request.trace_id,
            ok=True,
            provider="fake",
            model_id="fake-model",
            content="ok",
        )


@pytest_asyncio.fixture
async def grpc_channel():
    server = grpc.aio.server()
    register_grpc_services(
        server,
        orchestrator=_FakeOrchestrator(),
        db_session_factory=_dummy_session_factory,
        stt_service=_FakeSTTService(),
        inference_dispatcher=_FakeInferenceDispatcher(),
    )
    reflection.enable_server_reflection((*registered_grpc_service_names(), reflection.SERVICE_NAME), server)
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    channel = grpc.aio.insecure_channel(f"127.0.0.1:{port}")
    try:
        yield channel
    finally:
        await channel.close()
        await server.stop(0)


@pytest.mark.asyncio
async def test_reflection_lists_all_registered_grpc_services(grpc_channel):
    stub = reflection_pb2_grpc.ServerReflectionStub(grpc_channel)
    request = reflection_pb2.ServerReflectionRequest(list_services="")

    responses = [response async for response in stub.ServerReflectionInfo(iter([request]))]
    listed = {service.name for service in responses[0].list_services_response.service}

    assert set(registered_grpc_service_names()).issubset(listed)
    assert "sparkle.community.CommunityService" not in listed


@pytest.mark.asyncio
async def test_registered_stt_service_serves_enhance_transcript(grpc_channel):
    stub = stt_service_pb2_grpc.STTServiceStub(grpc_channel)

    response = await stub.EnhanceTranscript(stt_service_pb2.EnhanceRequest(text="hello", user_id="user-1"))

    assert response.original_text == "hello"
    assert response.enhanced_text == "hello!"
    assert response.changes_count == 1


@pytest.mark.asyncio
async def test_registered_inference_service_serves_run_inference(grpc_channel):
    stub = inference_pb2_grpc.InferenceServiceStub(grpc_channel)

    response = await stub.RunInference(
        inference_pb2.InferenceRequest(
            request_id="req-1",
            trace_id="trace-1",
            user_id="user-1",
            task_type=inference_pb2.SHORT_INFERENCE,
            schema_version="test.v1",
            budgets=inference_pb2.Budgets(max_output_tokens=8),
        )
    )

    assert response.ok is True
    assert response.content == "ok"


def test_community_proto_is_explicitly_deprecated_rest_only():
    service = community_service_pb2.DESCRIPTOR.services_by_name["CommunityService"]

    assert service.GetOptions().deprecated is True
    assert "sparkle.community.CommunityService" in DEPRECATED_PROTO_SERVICE_NAMES
