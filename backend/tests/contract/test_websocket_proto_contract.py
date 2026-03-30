from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
GEN_DIR = REPO_ROOT / "backend" / "app" / "gen"
if str(GEN_DIR) not in sys.path:
    sys.path.insert(0, str(GEN_DIR))

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
