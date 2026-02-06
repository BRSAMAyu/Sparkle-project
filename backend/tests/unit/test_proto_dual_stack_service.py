from app.gen.agent.v1 import agent_service_pb2
from app.services.agent_grpc_service import AgentServiceImpl


def test_normalize_v2_response_keeps_existing_event_time():
    resp = agent_service_pb2.ChatResponse()
    resp.event_time.FromMilliseconds(1730000000456)
    enriched = AgentServiceImpl._normalize_v2_response(resp)
    assert enriched.HasField("event_time")
    assert enriched.event_time.ToMilliseconds() == 1730000000456


def test_normalize_v2_response_defaults_missing_event_time():
    resp = agent_service_pb2.ChatResponse()
    enriched = AgentServiceImpl._normalize_v2_response(resp)
    assert enriched.HasField("event_time")
    assert enriched.event_time.ToMilliseconds() > 0


def test_normalize_v2_response_keeps_explicit_error_code():
    resp = agent_service_pb2.ChatResponse(
        error=agent_service_pb2.Error(error_code=agent_service_pb2.ERROR_CODE_TIMEOUT)
    )
    enriched = AgentServiceImpl._normalize_v2_response(resp)
    assert enriched.error.error_code == agent_service_pb2.ERROR_CODE_TIMEOUT


def test_normalize_v2_response_defaults_unspecified_error_code_to_unknown():
    resp = agent_service_pb2.ChatResponse(
        error=agent_service_pb2.Error(message="boom", retryable=True)
    )
    enriched = AgentServiceImpl._normalize_v2_response(resp)
    assert enriched.error.error_code == agent_service_pb2.ERROR_CODE_UNKNOWN
