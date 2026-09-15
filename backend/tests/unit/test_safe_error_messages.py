import asyncio

from app.core.safe_error_messages import build_safe_chat_error
from app.gen.agent.v1 import agent_service_pb2


def test_build_safe_chat_error_hides_internal_details():
    message, error_code, retryable = build_safe_chat_error(
        RuntimeError("Database connection error: postgres://localhost:5432/app")
    )

    assert message == "系统暂时不可用，请稍后重试。"
    assert "postgres://" not in message
    assert error_code == agent_service_pb2.ERROR_CODE_INTERNAL
    assert retryable is True


def test_build_safe_chat_error_maps_timeouts():
    message, error_code, retryable = build_safe_chat_error(asyncio.TimeoutError())

    assert message == "系统处理超时，请稍后重试。"
    assert error_code == agent_service_pb2.ERROR_CODE_TIMEOUT
    assert retryable is True
