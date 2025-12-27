import datetime

from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf import struct_pb2 as _struct_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class FinishReason(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    NULL: _ClassVar[FinishReason]
    STOP: _ClassVar[FinishReason]
    LENGTH: _ClassVar[FinishReason]
    TOOL_CALLS: _ClassVar[FinishReason]
    CONTENT_FILTER: _ClassVar[FinishReason]
    ERROR: _ClassVar[FinishReason]
NULL: FinishReason
STOP: FinishReason
LENGTH: FinishReason
TOOL_CALLS: FinishReason
CONTENT_FILTER: FinishReason
ERROR: FinishReason

class ChatRequest(_message.Message):
    __slots__ = ("user_id", "session_id", "message", "tool_result", "user_profile", "extra_context", "history", "config", "request_id")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    TOOL_RESULT_FIELD_NUMBER: _ClassVar[int]
    USER_PROFILE_FIELD_NUMBER: _ClassVar[int]
    EXTRA_CONTEXT_FIELD_NUMBER: _ClassVar[int]
    HISTORY_FIELD_NUMBER: _ClassVar[int]
    CONFIG_FIELD_NUMBER: _ClassVar[int]
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    session_id: str
    message: str
    tool_result: ToolResult
    user_profile: UserProfile
    extra_context: _struct_pb2.Struct
    history: _containers.RepeatedCompositeFieldContainer[ChatMessage]
    config: ChatConfig
    request_id: str
    def __init__(self, user_id: _Optional[str] = ..., session_id: _Optional[str] = ..., message: _Optional[str] = ..., tool_result: _Optional[_Union[ToolResult, _Mapping]] = ..., user_profile: _Optional[_Union[UserProfile, _Mapping]] = ..., extra_context: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ..., history: _Optional[_Iterable[_Union[ChatMessage, _Mapping]]] = ..., config: _Optional[_Union[ChatConfig, _Mapping]] = ..., request_id: _Optional[str] = ...) -> None: ...

class UserProfile(_message.Message):
    __slots__ = ("nickname", "timezone", "language", "is_pro", "preferences")
    class PreferencesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    TIMEZONE_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    IS_PRO_FIELD_NUMBER: _ClassVar[int]
    PREFERENCES_FIELD_NUMBER: _ClassVar[int]
    nickname: str
    timezone: str
    language: str
    is_pro: bool
    preferences: _containers.ScalarMap[str, str]
    def __init__(self, nickname: _Optional[str] = ..., timezone: _Optional[str] = ..., language: _Optional[str] = ..., is_pro: bool = ..., preferences: _Optional[_Mapping[str, str]] = ...) -> None: ...

class ToolResult(_message.Message):
    __slots__ = ("tool_call_id", "tool_name", "result_json", "is_error", "error_message")
    TOOL_CALL_ID_FIELD_NUMBER: _ClassVar[int]
    TOOL_NAME_FIELD_NUMBER: _ClassVar[int]
    RESULT_JSON_FIELD_NUMBER: _ClassVar[int]
    IS_ERROR_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    tool_call_id: str
    tool_name: str
    result_json: str
    is_error: bool
    error_message: str
    def __init__(self, tool_call_id: _Optional[str] = ..., tool_name: _Optional[str] = ..., result_json: _Optional[str] = ..., is_error: bool = ..., error_message: _Optional[str] = ...) -> None: ...

class ChatConfig(_message.Message):
    __slots__ = ("model", "temperature", "max_tokens", "tools_enabled")
    MODEL_FIELD_NUMBER: _ClassVar[int]
    TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    MAX_TOKENS_FIELD_NUMBER: _ClassVar[int]
    TOOLS_ENABLED_FIELD_NUMBER: _ClassVar[int]
    model: str
    temperature: float
    max_tokens: int
    tools_enabled: bool
    def __init__(self, model: _Optional[str] = ..., temperature: _Optional[float] = ..., max_tokens: _Optional[int] = ..., tools_enabled: bool = ...) -> None: ...

class ChatMessage(_message.Message):
    __slots__ = ("role", "content", "name", "tool_call_id", "metadata")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    ROLE_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TOOL_CALL_ID_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    role: str
    content: str
    name: str
    tool_call_id: str
    metadata: _containers.ScalarMap[str, str]
    def __init__(self, role: _Optional[str] = ..., content: _Optional[str] = ..., name: _Optional[str] = ..., tool_call_id: _Optional[str] = ..., metadata: _Optional[_Mapping[str, str]] = ...) -> None: ...

class ChatResponse(_message.Message):
    __slots__ = ("response_id", "created_at", "request_id", "delta", "tool_call", "status_update", "full_text", "error", "usage", "citations", "finish_reason")
    RESPONSE_ID_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    DELTA_FIELD_NUMBER: _ClassVar[int]
    TOOL_CALL_FIELD_NUMBER: _ClassVar[int]
    STATUS_UPDATE_FIELD_NUMBER: _ClassVar[int]
    FULL_TEXT_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    USAGE_FIELD_NUMBER: _ClassVar[int]
    CITATIONS_FIELD_NUMBER: _ClassVar[int]
    FINISH_REASON_FIELD_NUMBER: _ClassVar[int]
    response_id: str
    created_at: int
    request_id: str
    delta: str
    tool_call: ToolCall
    status_update: AgentStatus
    full_text: str
    error: Error
    usage: Usage
    citations: CitationBlock
    finish_reason: FinishReason
    def __init__(self, response_id: _Optional[str] = ..., created_at: _Optional[int] = ..., request_id: _Optional[str] = ..., delta: _Optional[str] = ..., tool_call: _Optional[_Union[ToolCall, _Mapping]] = ..., status_update: _Optional[_Union[AgentStatus, _Mapping]] = ..., full_text: _Optional[str] = ..., error: _Optional[_Union[Error, _Mapping]] = ..., usage: _Optional[_Union[Usage, _Mapping]] = ..., citations: _Optional[_Union[CitationBlock, _Mapping]] = ..., finish_reason: _Optional[_Union[FinishReason, str]] = ...) -> None: ...

class CitationBlock(_message.Message):
    __slots__ = ("citations",)
    CITATIONS_FIELD_NUMBER: _ClassVar[int]
    citations: _containers.RepeatedCompositeFieldContainer[Citation]
    def __init__(self, citations: _Optional[_Iterable[_Union[Citation, _Mapping]]] = ...) -> None: ...

class Citation(_message.Message):
    __slots__ = ("id", "title", "content", "source_type", "url", "score")
    ID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    SOURCE_TYPE_FIELD_NUMBER: _ClassVar[int]
    URL_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    id: str
    title: str
    content: str
    source_type: str
    url: str
    score: float
    def __init__(self, id: _Optional[str] = ..., title: _Optional[str] = ..., content: _Optional[str] = ..., source_type: _Optional[str] = ..., url: _Optional[str] = ..., score: _Optional[float] = ...) -> None: ...

class ToolCall(_message.Message):
    __slots__ = ("id", "name", "arguments")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    arguments: str
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., arguments: _Optional[str] = ...) -> None: ...

class AgentStatus(_message.Message):
    __slots__ = ("state", "details")
    class State(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        UNKNOWN: _ClassVar[AgentStatus.State]
        THINKING: _ClassVar[AgentStatus.State]
        SEARCHING: _ClassVar[AgentStatus.State]
        EXECUTING_TOOL: _ClassVar[AgentStatus.State]
        GENERATING: _ClassVar[AgentStatus.State]
    UNKNOWN: AgentStatus.State
    THINKING: AgentStatus.State
    SEARCHING: AgentStatus.State
    EXECUTING_TOOL: AgentStatus.State
    GENERATING: AgentStatus.State
    STATE_FIELD_NUMBER: _ClassVar[int]
    DETAILS_FIELD_NUMBER: _ClassVar[int]
    state: AgentStatus.State
    details: str
    def __init__(self, state: _Optional[_Union[AgentStatus.State, str]] = ..., details: _Optional[str] = ...) -> None: ...

class Error(_message.Message):
    __slots__ = ("code", "message", "retryable", "details")
    class DetailsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    CODE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    RETRYABLE_FIELD_NUMBER: _ClassVar[int]
    DETAILS_FIELD_NUMBER: _ClassVar[int]
    code: str
    message: str
    retryable: bool
    details: _containers.ScalarMap[str, str]
    def __init__(self, code: _Optional[str] = ..., message: _Optional[str] = ..., retryable: bool = ..., details: _Optional[_Mapping[str, str]] = ...) -> None: ...

class Usage(_message.Message):
    __slots__ = ("prompt_tokens", "completion_tokens", "total_tokens", "cost_micro_usd")
    PROMPT_TOKENS_FIELD_NUMBER: _ClassVar[int]
    COMPLETION_TOKENS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_TOKENS_FIELD_NUMBER: _ClassVar[int]
    COST_MICRO_USD_FIELD_NUMBER: _ClassVar[int]
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_micro_usd: int
    def __init__(self, prompt_tokens: _Optional[int] = ..., completion_tokens: _Optional[int] = ..., total_tokens: _Optional[int] = ..., cost_micro_usd: _Optional[int] = ...) -> None: ...

class MemoryQuery(_message.Message):
    __slots__ = ("user_id", "query_text", "limit", "min_score", "filter", "hybrid_alpha")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    QUERY_TEXT_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    MIN_SCORE_FIELD_NUMBER: _ClassVar[int]
    FILTER_FIELD_NUMBER: _ClassVar[int]
    HYBRID_ALPHA_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    query_text: str
    limit: int
    min_score: float
    filter: MemoryFilter
    hybrid_alpha: float
    def __init__(self, user_id: _Optional[str] = ..., query_text: _Optional[str] = ..., limit: _Optional[int] = ..., min_score: _Optional[float] = ..., filter: _Optional[_Union[MemoryFilter, _Mapping]] = ..., hybrid_alpha: _Optional[float] = ...) -> None: ...

class MemoryFilter(_message.Message):
    __slots__ = ("tags", "start_time", "end_time", "source_types")
    TAGS_FIELD_NUMBER: _ClassVar[int]
    START_TIME_FIELD_NUMBER: _ClassVar[int]
    END_TIME_FIELD_NUMBER: _ClassVar[int]
    SOURCE_TYPES_FIELD_NUMBER: _ClassVar[int]
    tags: _containers.RepeatedScalarFieldContainer[str]
    start_time: _timestamp_pb2.Timestamp
    end_time: _timestamp_pb2.Timestamp
    source_types: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, tags: _Optional[_Iterable[str]] = ..., start_time: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., end_time: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., source_types: _Optional[_Iterable[str]] = ...) -> None: ...

class MemoryResult(_message.Message):
    __slots__ = ("items", "total_found")
    ITEMS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_FOUND_FIELD_NUMBER: _ClassVar[int]
    items: _containers.RepeatedCompositeFieldContainer[MemoryItem]
    total_found: int
    def __init__(self, items: _Optional[_Iterable[_Union[MemoryItem, _Mapping]]] = ..., total_found: _Optional[int] = ...) -> None: ...

class MemoryItem(_message.Message):
    __slots__ = ("id", "content", "score", "created_at", "metadata")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    ID_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    id: str
    content: str
    score: float
    created_at: _timestamp_pb2.Timestamp
    metadata: _containers.ScalarMap[str, str]
    def __init__(self, id: _Optional[str] = ..., content: _Optional[str] = ..., score: _Optional[float] = ..., created_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., metadata: _Optional[_Mapping[str, str]] = ...) -> None: ...
