from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
GEN_DIR = REPO_ROOT / "backend" / "app" / "gen"
if str(GEN_DIR) not in sys.path:
    sys.path.insert(0, str(GEN_DIR))

from app.gen.agent.v1 import agent_service_pb2
from app.gen import websocket_pb2


def test_websocket_envelope_field_numbers_are_stable():
    message_descriptor = websocket_pb2.WebSocketMessage.DESCRIPTOR
    fields = {field.name: field.number for field in message_descriptor.fields}

    assert fields == {
        "version": 1,
        "type": 2,
        "payload": 3,
        "trace_id": 4,
        "request_id": 5,
        "event_time": 7,
    }


def test_websocket_chat_message_contract_keeps_session_user_message_triplet():
    chat_descriptor = websocket_pb2.ChatMessage.DESCRIPTOR
    field_names = [field.name for field in chat_descriptor.fields]

    assert field_names[:3] == ["session_id", "user_id", "message"]
    assert "tool_calls" in field_names


def test_websocket_ack_and_nack_contracts_keep_error_fields():
    ack_fields = {field.name for field in websocket_pb2.MessageAck.DESCRIPTOR.fields}
    nack_fields = {field.name for field in websocket_pb2.MessageNack.DESCRIPTOR.fields}

    assert {"message_id", "status", "timestamp", "error_code", "error_message"} <= ack_fields
    assert {"message_id", "error_code", "error_message", "retry_after_ms", "permanent"} <= nack_fields


def test_agent_chat_request_contract_keeps_input_and_context_fields_stable():
    descriptor = agent_service_pb2.ChatRequest.DESCRIPTOR
    field_numbers = {field.name: field.number for field in descriptor.fields}

    assert field_numbers == {
        "user_id": 1,
        "session_id": 2,
        "message": 3,
        "user_profile": 4,
        "extra_context": 5,
        "history": 6,
        "tool_result": 7,
        "config": 8,
        "request_id": 9,
        "file_ids": 10,
        "include_references": 11,
        "active_tools": 12,
        "chat_mode": 13,
        "use_document_context": 14,
        "document_filter": 15,
    }
    assert descriptor.oneofs_by_name["input"].fields[0].name == "message"
    assert descriptor.oneofs_by_name["input"].fields[1].name == "tool_result"


def test_agent_chat_response_contract_keeps_streaming_metadata_layout_stable():
    descriptor = agent_service_pb2.ChatResponse.DESCRIPTOR
    field_numbers = {field.name: field.number for field in descriptor.fields}

    assert field_numbers["response_id"] == 1
    assert field_numbers["created_at"] == 2
    assert field_numbers["request_id"] == 10
    assert field_numbers["citations"] == 11
    assert field_numbers["tool_result"] == 12
    assert field_numbers["intervention"] == 14
    assert field_numbers["trace_id"] == 15
    assert field_numbers["workflow_id"] == 16
    assert field_numbers["prompt_version"] == 17
    assert field_numbers["metadata"] == 18
    assert field_numbers["event_time"] == 19
    assert field_numbers["session_id"] == 20

    content_fields = [field.name for field in descriptor.oneofs_by_name["content"].fields]
    assert content_fields == [
        "delta",
        "tool_call",
        "status_update",
        "full_text",
        "error",
        "usage",
        "citations",
        "tool_result",
        "intervention",
    ]
