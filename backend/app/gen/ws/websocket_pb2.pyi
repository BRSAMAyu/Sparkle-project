from collections.abc import Iterable as _Iterable
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar

import agent_service_pb2 as _agent_service_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf.internal import containers as _containers

DESCRIPTOR: _descriptor.FileDescriptor

class WebSocketMessage(_message.Message):
    __slots__ = ("version", "type", "payload", "trace_id", "request_id", "timestamp")
    VERSION_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    PAYLOAD_FIELD_NUMBER: _ClassVar[int]
    TRACE_ID_FIELD_NUMBER: _ClassVar[int]
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    version: str
    type: str
    payload: bytes
    trace_id: str
    request_id: str
    timestamp: int
    def __init__(self, version: str | None = ..., type: str | None = ..., payload: bytes | None = ..., trace_id: str | None = ..., request_id: str | None = ..., timestamp: int | None = ...) -> None: ...

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
    def __init__(self, session_id: str | None = ..., user_id: str | None = ..., message: str | None = ..., tool_calls: _Iterable[_agent_service_pb2.ToolCall | _Mapping] | None = ...) -> None: ...

class UpdateNodeMasteryRequest(_message.Message):
    __slots__ = ("node_id", "mastery", "timestamp", "request_id", "revision")
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    MASTERY_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    REVISION_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    mastery: int
    timestamp: int
    request_id: str
    revision: int
    def __init__(self, node_id: str | None = ..., mastery: int | None = ..., timestamp: int | None = ..., request_id: str | None = ..., revision: int | None = ...) -> None: ...

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
    def __init__(self, intervention_id: str | None = ..., level: str | None = ..., content: InterventionContent | _Mapping | None = ..., actions: _Iterable[InterventionAction | _Mapping] | None = ..., expires_at: int | None = ...) -> None: ...

class InterventionContent(_message.Message):
    __slots__ = ("rendered_message", "intent_type", "template_id", "scaffolding_level", "context_variables")
    class ContextVariablesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: str | None = ..., value: str | None = ...) -> None: ...
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
    def __init__(self, rendered_message: str | None = ..., intent_type: str | None = ..., template_id: str | None = ..., scaffolding_level: int | None = ..., context_variables: _Mapping[str, str] | None = ...) -> None: ...

class InterventionAction(_message.Message):
    __slots__ = ("id", "label", "type")
    ID_FIELD_NUMBER: _ClassVar[int]
    LABEL_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    id: str
    label: str
    type: str
    def __init__(self, id: str | None = ..., label: str | None = ..., type: str | None = ...) -> None: ...
