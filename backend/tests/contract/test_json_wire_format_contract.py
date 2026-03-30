from __future__ import annotations

from google.protobuf.json_format import MessageToDict

from app.gen import agent_service_pb2


def _wire_dict(message):
    try:
        return MessageToDict(
            message,
            preserving_proto_field_name=True,
            use_integers_for_enums=False,
            always_print_fields_with_no_presence=True,
        )
    except TypeError:
        return MessageToDict(
            message,
            preserving_proto_field_name=True,
            use_integers_for_enums=False,
            including_default_value_fields=True,
        )


def test_chat_response_delta_json_keys():
    response = agent_service_pb2.ChatResponse(
        response_id="resp-1",
        created_at=1234567890,
        request_id="req-1",
        trace_id="trace-1",
        workflow_id="standard_chat",
        prompt_version="v1",
        delta="hello",
        session_id="session-1",
    )

    payload = _wire_dict(response)

    assert set(payload) >= {
        "response_id",
        "created_at",
        "request_id",
        "trace_id",
        "workflow_id",
        "prompt_version",
        "delta",
        "session_id",
    }
    assert payload["delta"] == "hello"


def test_status_update_enum_serializes_as_string():
    response = agent_service_pb2.ChatResponse(
        status_update=agent_service_pb2.AgentStatus(
            state=agent_service_pb2.AgentStatus.THINKING,
            details="planning",
        )
    )

    payload = _wire_dict(response)

    assert payload["status_update"]["state"] == "THINKING"
    assert payload["status_update"]["details"] == "planning"


def test_error_json_format_matches_flutter_parser():
    response = agent_service_pb2.ChatResponse(
        error=agent_service_pb2.Error(
            message="upstream timeout",
            retryable=True,
            error_code=agent_service_pb2.ERROR_CODE_TIMEOUT,
        )
    )

    payload = _wire_dict(response)

    assert set(payload["error"]) >= {"message", "retryable", "error_code"}
    assert payload["error"]["error_code"] == "ERROR_CODE_TIMEOUT"
    assert payload["error"]["retryable"] is True


def test_finish_reason_all_enum_values_stable():
    expected = {
        0: "NULL",
        1: "STOP",
        2: "LENGTH",
        3: "TOOL_CALLS",
        4: "CONTENT_FILTER",
        5: "ERROR",
    }

    for number, name in expected.items():
        response = agent_service_pb2.ChatResponse(
            finish_reason=number,
        )
        payload = _wire_dict(response)
        assert payload["finish_reason"] == name
