from google.protobuf import timestamp_pb2

from app.gen.agent.v1 import agent_service_pb2
from app.services.agent_grpc_service import AgentServiceImpl


def test_enrich_dual_stack_response_fills_event_time_from_legacy(monkeypatch):
    monkeypatch.setenv("PROTO_WRITE_DUAL", "true")
    monkeypatch.setenv("PROTO_READ_NEW_FIRST", "true")

    resp = agent_service_pb2.ChatResponse(timestamp=1730000000123)
    enriched = AgentServiceImpl._enrich_dual_stack_response(resp)

    assert enriched.HasField("event_time")
    assert enriched.event_time.ToMilliseconds() == 1730000000123


def test_enrich_dual_stack_response_fills_legacy_from_event_time(monkeypatch):
    monkeypatch.setenv("PROTO_WRITE_DUAL", "true")
    monkeypatch.setenv("PROTO_READ_NEW_FIRST", "true")

    ts = timestamp_pb2.Timestamp()
    ts.FromMilliseconds(1730000000456)
    resp = agent_service_pb2.ChatResponse(event_time=ts)
    enriched = AgentServiceImpl._enrich_dual_stack_response(resp)

    assert enriched.timestamp == 1730000000456


def test_enrich_dual_stack_response_new_only_mode(monkeypatch):
    monkeypatch.setenv("PROTO_WRITE_DUAL", "false")
    monkeypatch.setenv("PROTO_READ_NEW_FIRST", "true")

    resp = agent_service_pb2.ChatResponse(timestamp=1730000000999)
    enriched = AgentServiceImpl._enrich_dual_stack_response(resp)

    assert enriched.HasField("event_time")
    assert enriched.timestamp == 0


def test_enrich_dual_stack_response_maps_error_code_enum(monkeypatch):
    monkeypatch.setenv("PROTO_WRITE_DUAL", "true")
    monkeypatch.setenv("PROTO_READ_NEW_FIRST", "true")

    resp = agent_service_pb2.ChatResponse(
        error=agent_service_pb2.Error(code="RATE_LIMIT")
    )
    enriched = AgentServiceImpl._enrich_dual_stack_response(resp)

    assert enriched.error.error_code == agent_service_pb2.ERROR_CODE_RATE_LIMITED


def test_enrich_dual_stack_response_keeps_legacy_error_when_dual(monkeypatch):
    monkeypatch.setenv("PROTO_WRITE_DUAL", "true")
    monkeypatch.setenv("PROTO_READ_NEW_FIRST", "true")

    resp = agent_service_pb2.ChatResponse(
        error=agent_service_pb2.Error(error_code=agent_service_pb2.ERROR_CODE_TIMEOUT)
    )
    enriched = AgentServiceImpl._enrich_dual_stack_response(resp)

    assert enriched.error.code == "timeout"


def test_enrich_dual_stack_response_clears_legacy_error_when_new_only(monkeypatch):
    monkeypatch.setenv("PROTO_WRITE_DUAL", "false")
    monkeypatch.setenv("PROTO_READ_NEW_FIRST", "true")

    resp = agent_service_pb2.ChatResponse(
        error=agent_service_pb2.Error(code="INTERNAL_ERROR")
    )
    enriched = AgentServiceImpl._enrich_dual_stack_response(resp)

    assert enriched.error.error_code == agent_service_pb2.ERROR_CODE_INTERNAL
    assert enriched.error.code == ""
