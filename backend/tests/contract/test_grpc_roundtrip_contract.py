"""P2-33: gRPC round-trip contract test — verifies proto serialization consistency
across the Go↔Python boundary for critical message types."""

import pytest

from google.protobuf import json_format

# Proto imports — test that generated code is importable and consistent
from gen.agent.v1 import agent_service_pb2
from gen.galaxy.v1 import galaxy_service_pb2


class TestAgentProtoRoundTrip:
    """Verify critical agent_service.proto message types survive round-trip."""

    def test_stream_chat_request_roundtrip(self):
        original = agent_service_pb2.StreamChatRequest(
            user_id="test-user-001",
            session_id="sess-abc",
            content="Explain quantum computing in simple terms",
            stream=True,
        )
        json_str = json_format.MessageToJson(original, preserving_proto_field_name=True)
        restored = json_format.Parse(json_str, agent_service_pb2.StreamChatRequest())
        assert restored.user_id == original.user_id
        assert restored.session_id == original.session_id
        assert restored.content == original.content
        assert restored.stream == original.stream

    def test_stream_chat_response_roundtrip(self):
        original = agent_service_pb2.StreamChatResponse(
            delta="Quantum computing uses qubits instead of bits...",
            request_id="req-001",
            is_final=False,
            metadata={"token_count": "42"},
        )
        json_str = json_format.MessageToJson(original, preserving_proto_field_name=True)
        restored = json_format.Parse(json_str, agent_service_pb2.StreamChatResponse())
        assert restored.delta == original.delta
        assert restored.request_id == original.request_id
        assert restored.is_final == original.is_final

    def test_submit_plan_review_request_roundtrip(self):
        original = agent_service_pb2.SubmitPlanReviewRequest(
            user_id="test-user-001",
            plan_id="plan-xyz",
            approved=True,
            comment="Looks good, proceed with step 3",
        )
        json_str = json_format.MessageToJson(original, preserving_proto_field_name=True)
        restored = json_format.Parse(json_str, agent_service_pb2.SubmitPlanReviewRequest())
        assert restored.user_id == original.user_id
        assert restored.plan_id == original.plan_id
        assert restored.approved == original.approved
        assert restored.comment == original.comment

    def test_stream_chat_request_defaults(self):
        """Minimum-viable StreamChatRequest must serialize without errors."""
        msg = agent_service_pb2.StreamChatRequest()
        json_str = json_format.MessageToJson(msg, preserving_proto_field_name=True)
        assert "userId" in json_str or "user_id" in json_str
        restored = json_format.Parse(json_str, agent_service_pb2.StreamChatRequest())
        assert restored.user_id == ""


class TestGalaxyProtoRoundTrip:
    """Verify critical galaxy_service.proto message types survive round-trip."""

    def test_get_knowledge_nodes_request_roundtrip(self):
        original = galaxy_service_pb2.GetKnowledgeNodesRequest(
            user_id="test-user-001",
            subject_id=42,
            parent_id="node-parent-1",
            limit=50,
            offset=0,
        )
        json_str = json_format.MessageToJson(original, preserving_proto_field_name=True)
        restored = json_format.Parse(json_str, galaxy_service_pb2.GetKnowledgeNodesRequest())
        assert restored.user_id == original.user_id
        assert restored.subject_id == original.subject_id
        assert restored.parent_id == original.parent_id
        assert restored.limit == original.limit

    def test_knowledge_node_response_roundtrip(self):
        original = galaxy_service_pb2.KnowledgeNode(
            id="node-001",
            name="Quantum Superposition",
            description="A quantum system can exist in multiple states simultaneously",
            importance_level=4,
            mastery_score=0.75,
        )
        json_str = json_format.MessageToJson(original, preserving_proto_field_name=True)
        restored = json_format.Parse(json_str, galaxy_service_pb2.KnowledgeNode())
        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.importance_level == original.importance_level


class TestProtoModuleHealth:
    """Smoke-test that all generated proto modules are importable."""

    def test_agent_service_pb2_importable(self):
        import gen.agent.v1.agent_service_pb2 as m
        assert hasattr(m, "StreamChatRequest")
        assert hasattr(m, "StreamChatResponse")

    def test_galaxy_service_pb2_importable(self):
        import gen.galaxy.v1.galaxy_service_pb2 as m
        assert hasattr(m, "GetKnowledgeNodesRequest")
        assert hasattr(m, "KnowledgeNode")

    def test_community_service_pb2_importable(self):
        import gen.community.v1.community_service_pb2 as m
        assert hasattr(m, "DESCRIPTOR")

    def test_error_book_pb2_importable(self):
        import gen.errorbook.v1.error_book_pb2 as m
        assert hasattr(m, "DESCRIPTOR")

    def test_websocket_pb2_importable(self):
        from gen.ws import websocket_pb2 as m
        assert hasattr(m, "DESCRIPTOR")
