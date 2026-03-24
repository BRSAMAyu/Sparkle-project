import datetime

import agent_service_pb2 as _agent_service_pb2
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class WebSocketMessage(_message.Message):
    __slots__ = ("version", "type", "payload", "trace_id", "request_id", "event_time")
    VERSION_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    PAYLOAD_FIELD_NUMBER: _ClassVar[int]
    TRACE_ID_FIELD_NUMBER: _ClassVar[int]
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    EVENT_TIME_FIELD_NUMBER: _ClassVar[int]
    version: str
    type: str
    payload: bytes
    trace_id: str
    request_id: str
    event_time: _timestamp_pb2.Timestamp
    def __init__(self, version: _Optional[str] = ..., type: _Optional[str] = ..., payload: _Optional[bytes] = ..., trace_id: _Optional[str] = ..., request_id: _Optional[str] = ..., event_time: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class ChatMessage(_message.Message):
    __slots__ = ("session_id", "user_id", "message", "tool_calls")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    TOOL_CALLS_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    user_id: str
    message: str
    tool_calls: _containers.RepeatedCompositeFieldContainer[_agent_service_pb2.ToolCall]
    def __init__(self, session_id: _Optional[str] = ..., user_id: _Optional[str] = ..., message: _Optional[str] = ..., tool_calls: _Optional[_Iterable[_Union[_agent_service_pb2.ToolCall, _Mapping]]] = ...) -> None: ...

class UpdateNodeMasteryRequest(_message.Message):
    __slots__ = ("node_id", "mastery", "request_id", "revision", "event_time")
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    MASTERY_FIELD_NUMBER: _ClassVar[int]
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    REVISION_FIELD_NUMBER: _ClassVar[int]
    EVENT_TIME_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    mastery: int
    request_id: str
    revision: int
    event_time: _timestamp_pb2.Timestamp
    def __init__(self, node_id: _Optional[str] = ..., mastery: _Optional[int] = ..., request_id: _Optional[str] = ..., revision: _Optional[int] = ..., event_time: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class InterventionPushMessage(_message.Message):
    __slots__ = ("intervention_id", "level", "content", "actions", "expires_at")
    INTERVENTION_ID_FIELD_NUMBER: _ClassVar[int]
    LEVEL_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    ACTIONS_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_FIELD_NUMBER: _ClassVar[int]
    intervention_id: str
    level: str
    content: InterventionContent
    actions: _containers.RepeatedCompositeFieldContainer[InterventionAction]
    expires_at: int
    def __init__(self, intervention_id: _Optional[str] = ..., level: _Optional[str] = ..., content: _Optional[_Union[InterventionContent, _Mapping]] = ..., actions: _Optional[_Iterable[_Union[InterventionAction, _Mapping]]] = ..., expires_at: _Optional[int] = ...) -> None: ...

class InterventionContent(_message.Message):
    __slots__ = ("rendered_message", "intent_type", "template_id", "scaffolding_level", "context_variables")
    class ContextVariablesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    RENDERED_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    INTENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_ID_FIELD_NUMBER: _ClassVar[int]
    SCAFFOLDING_LEVEL_FIELD_NUMBER: _ClassVar[int]
    CONTEXT_VARIABLES_FIELD_NUMBER: _ClassVar[int]
    rendered_message: str
    intent_type: str
    template_id: str
    scaffolding_level: int
    context_variables: _containers.ScalarMap[str, str]
    def __init__(self, rendered_message: _Optional[str] = ..., intent_type: _Optional[str] = ..., template_id: _Optional[str] = ..., scaffolding_level: _Optional[int] = ..., context_variables: _Optional[_Mapping[str, str]] = ...) -> None: ...

class InterventionAction(_message.Message):
    __slots__ = ("id", "label", "type")
    ID_FIELD_NUMBER: _ClassVar[int]
    LABEL_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    id: str
    label: str
    type: str
    def __init__(self, id: _Optional[str] = ..., label: _Optional[str] = ..., type: _Optional[str] = ...) -> None: ...

class MessageAck(_message.Message):
    __slots__ = ("message_id", "status", "timestamp", "error_code", "error_message")
    MESSAGE_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    ERROR_CODE_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    message_id: str
    status: str
    timestamp: int
    error_code: str
    error_message: str
    def __init__(self, message_id: _Optional[str] = ..., status: _Optional[str] = ..., timestamp: _Optional[int] = ..., error_code: _Optional[str] = ..., error_message: _Optional[str] = ...) -> None: ...

class MessageNack(_message.Message):
    __slots__ = ("message_id", "error_code", "error_message", "retry_after_ms", "permanent")
    MESSAGE_ID_FIELD_NUMBER: _ClassVar[int]
    ERROR_CODE_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    RETRY_AFTER_MS_FIELD_NUMBER: _ClassVar[int]
    PERMANENT_FIELD_NUMBER: _ClassVar[int]
    message_id: str
    error_code: str
    error_message: str
    retry_after_ms: int
    permanent: bool
    def __init__(self, message_id: _Optional[str] = ..., error_code: _Optional[str] = ..., error_message: _Optional[str] = ..., retry_after_ms: _Optional[int] = ..., permanent: bool = ...) -> None: ...

class HeartbeatPing(_message.Message):
    __slots__ = ("timestamp", "client_id")
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    CLIENT_ID_FIELD_NUMBER: _ClassVar[int]
    timestamp: int
    client_id: str
    def __init__(self, timestamp: _Optional[int] = ..., client_id: _Optional[str] = ...) -> None: ...

class HeartbeatPong(_message.Message):
    __slots__ = ("client_timestamp", "server_timestamp")
    CLIENT_TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    SERVER_TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    client_timestamp: int
    server_timestamp: int
    def __init__(self, client_timestamp: _Optional[int] = ..., server_timestamp: _Optional[int] = ...) -> None: ...
