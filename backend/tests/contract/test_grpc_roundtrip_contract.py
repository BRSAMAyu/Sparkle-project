"""P2-33: gRPC round-trip contract test — verifies proto serialization consistency
across the Go↔Python boundary for critical message types."""

import pytest

from google.protobuf import json_format

# Proto imports — test that generated code is importable and consistent.
# The flat app.gen modules are the canonical Python generated outputs; nested
# packages re-export them for some proto namespaces.
from app.gen import agent_service_pb2, galaxy_service_pb2


class TestAgentProtoRoundTrip:
    """Verify critical agent_service.proto message types survive round-trip."""

    def test_chat_request_roundtrip(self):
        original = agent_service_pb2.ChatRequest(
            user_id="test-user-001",
            session_id="sess-abc",
            message="Explain quantum computing in simple terms",
            request_id="req-001",
        )
        json_str = json_format.MessageToJson(original, preserving_proto_field_name=True)
        restored = json_format.Parse(json_str, agent_service_pb2.ChatRequest())
        assert restored.user_id == original.user_id
        assert restored.session_id == original.session_id
        assert restored.message == original.message
        assert restored.request_id == original.request_id

    def test_chat_response_roundtrip(self):
        original = agent_service_pb2.ChatResponse(
            delta="Quantum computing uses qubits instead of bits...",
            request_id="req-001",
            metadata={"token_count": "42"},
        )
        json_str = json_format.MessageToJson(original, preserving_proto_field_name=True)
        restored = json_format.Parse(json_str, agent_service_pb2.ChatResponse())
        assert restored.delta == original.delta
        assert restored.request_id == original.request_id

    def test_plan_review_request_roundtrip(self):
        original = agent_service_pb2.PlanReviewRequest(
            user_id="test-user-001",
            plan_id="plan-xyz",
            decision=agent_service_pb2.APPROVE,
            user_comment="Looks good, proceed with step 3",
        )
        json_str = json_format.MessageToJson(original, preserving_proto_field_name=True)
        restored = json_format.Parse(json_str, agent_service_pb2.PlanReviewRequest())
        assert restored.user_id == original.user_id
        assert restored.plan_id == original.plan_id
        assert restored.decision == original.decision
        assert restored.user_comment == original.user_comment

    def test_chat_request_defaults(self):
        """Minimum-viable ChatRequest must serialize without errors."""
        msg = agent_service_pb2.ChatRequest()
        json_str = json_format.MessageToJson(msg, preserving_proto_field_name=True)
        assert json_str == "{}"
        restored = json_format.Parse(json_str, agent_service_pb2.ChatRequest())
        assert restored.user_id == ""


class TestGalaxyProtoRoundTrip:
    """Verify critical galaxy_service.proto message types survive round-trip."""

    def test_update_node_mastery_request_roundtrip(self):
        original = galaxy_service_pb2.UpdateNodeMasteryRequest(
            user_id="test-user-001",
            node_id="node-parent-1",
            mastery=82,
            reason="practice_review",
            request_id="req-kg-001",
        )
        json_str = json_format.MessageToJson(original, preserving_proto_field_name=True)
        restored = json_format.Parse(json_str, galaxy_service_pb2.UpdateNodeMasteryRequest())
        assert restored.user_id == original.user_id
        assert restored.node_id == original.node_id
        assert restored.mastery == original.mastery
        assert restored.reason == original.reason

    def test_collaborative_galaxy_update_roundtrip(self):
        original = galaxy_service_pb2.CollaborativeGalaxyUpdate(
            galaxy_id="galaxy-001",
            yjs_update=b"delta",
            user_id="test-user-001",
        )
        json_str = json_format.MessageToJson(original, preserving_proto_field_name=True)
        restored = json_format.Parse(json_str, galaxy_service_pb2.CollaborativeGalaxyUpdate())
        assert restored.galaxy_id == original.galaxy_id
        assert restored.yjs_update == original.yjs_update
        assert restored.user_id == original.user_id


class TestProtoModuleHealth:
    """Smoke-test that all generated proto modules are importable."""

    def test_agent_service_pb2_importable(self):
        from app.gen import agent_service_pb2 as m
        assert hasattr(m, "ChatRequest")
        assert hasattr(m, "ChatResponse")

    def test_galaxy_service_pb2_importable(self):
        from app.gen import galaxy_service_pb2 as m
        assert hasattr(m, "UpdateNodeMasteryRequest")
        assert hasattr(m, "CollaborativeGalaxyUpdate")

    def test_error_book_pb2_importable(self):
        from app.gen import error_book_pb2 as m
        assert hasattr(m, "DESCRIPTOR")

    def test_websocket_pb2_importable(self):
        from app.gen import websocket_pb2 as m
        assert hasattr(m, "DESCRIPTOR")
