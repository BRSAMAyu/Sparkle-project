import asyncio

import pytest

from app.gen.agent.v1 import agent_service_pb2
from app.orchestration.orchestrator import ChatOrchestrator


def _build_orchestrator_stub() -> ChatOrchestrator:
    return object.__new__(ChatOrchestrator)


def test_response_priority_marks_transparency_as_droppable():
    orchestrator = _build_orchestrator_stub()
    response = agent_service_pb2.ChatResponse(
        metadata={"event_type": "transparency"},
    )

    assert orchestrator._response_priority(response) == "droppable"


def test_response_priority_marks_full_text_as_critical():
    orchestrator = _build_orchestrator_stub()
    response = agent_service_pb2.ChatResponse(
        full_text="最终答案",
        finish_reason=agent_service_pb2.STOP,
    )

    assert orchestrator._response_priority(response) == "critical"


@pytest.mark.asyncio
async def test_enqueue_stream_response_skips_low_priority_under_pressure():
    orchestrator = _build_orchestrator_stub()
    queue: asyncio.Queue = asyncio.Queue(maxsize=4)
    for _ in range(3):
        queue.put_nowait(agent_service_pb2.ChatResponse(delta="x"))

    low_priority = agent_service_pb2.ChatResponse(
        metadata={"event_type": "transparency"},
    )
    await orchestrator._enqueue_stream_response(queue, low_priority)

    assert queue.qsize() == 3


@pytest.mark.asyncio
async def test_enqueue_stream_response_evicts_droppable_item_for_critical_response():
    orchestrator = _build_orchestrator_stub()
    queue: asyncio.Queue = asyncio.Queue(maxsize=1)
    queue.put_nowait(agent_service_pb2.ChatResponse(metadata={"event_type": "transparency"}))

    critical = agent_service_pb2.ChatResponse(
        full_text="最终答案",
        finish_reason=agent_service_pb2.STOP,
    )
    await orchestrator._enqueue_stream_response(queue, critical)

    assert queue.qsize() == 1
    queued = queue.get_nowait()
    assert queued.full_text == "最终答案"
