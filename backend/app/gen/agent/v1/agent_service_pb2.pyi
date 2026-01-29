import datetime
from collections.abc import Iterable as _Iterable
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import struct_pb2 as _struct_pb2
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper

DESCRIPTOR: _descriptor.FileDescriptor

class FeedbackType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    FEEDBACK_TYPE_UP: _ClassVar[FeedbackType]
    FEEDBACK_TYPE_DOWN: _ClassVar[FeedbackType]

class FeedbackReason(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    FEEDBACK_REASON_UNSPECIFIED: _ClassVar[FeedbackReason]
    FEEDBACK_REASON_INACCURATE: _ClassVar[FeedbackReason]
    FEEDBACK_REASON_INCOMPLETE: _ClassVar[FeedbackReason]
    FEEDBACK_REASON_VERBOSE: _ClassVar[FeedbackReason]
    FEEDBACK_REASON_FORMATTING: _ClassVar[FeedbackReason]
    FEEDBACK_REASON_MISALIGNED: _ClassVar[FeedbackReason]
    FEEDBACK_REASON_TOO_HARD: _ClassVar[FeedbackReason]
    FEEDBACK_REASON_TOO_SIMPLE: _ClassVar[FeedbackReason]

class FinishReason(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    NULL: _ClassVar[FinishReason]
    STOP: _ClassVar[FinishReason]
    LENGTH: _ClassVar[FinishReason]
    TOOL_CALLS: _ClassVar[FinishReason]
    CONTENT_FILTER: _ClassVar[FinishReason]
    ERROR: _ClassVar[FinishReason]

class InterventionLevel(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SILENT_MARKER: _ClassVar[InterventionLevel]
    TOAST: _ClassVar[InterventionLevel]
    CARD: _ClassVar[InterventionLevel]
    FULL_SCREEN_MODAL: _ClassVar[InterventionLevel]

class AgentType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    AGENT_UNKNOWN: _ClassVar[AgentType]
    ORCHESTRATOR: _ClassVar[AgentType]
    KNOWLEDGE: _ClassVar[AgentType]
    MATH: _ClassVar[AgentType]
    CODE: _ClassVar[AgentType]
    DATA_ANALYSIS: _ClassVar[AgentType]
    TRANSLATION: _ClassVar[AgentType]
    IMAGE: _ClassVar[AgentType]
    AUDIO: _ClassVar[AgentType]
    WRITING: _ClassVar[AgentType]
    REASONING: _ClassVar[AgentType]
FEEDBACK_TYPE_UP: FeedbackType
FEEDBACK_TYPE_DOWN: FeedbackType
FEEDBACK_REASON_UNSPECIFIED: FeedbackReason
FEEDBACK_REASON_INACCURATE: FeedbackReason
FEEDBACK_REASON_INCOMPLETE: FeedbackReason
FEEDBACK_REASON_VERBOSE: FeedbackReason
FEEDBACK_REASON_FORMATTING: FeedbackReason
FEEDBACK_REASON_MISALIGNED: FeedbackReason
FEEDBACK_REASON_TOO_HARD: FeedbackReason
FEEDBACK_REASON_TOO_SIMPLE: FeedbackReason
NULL: FinishReason
STOP: FinishReason
LENGTH: FinishReason
TOOL_CALLS: FinishReason
CONTENT_FILTER: FinishReason
ERROR: FinishReason
SILENT_MARKER: InterventionLevel
TOAST: InterventionLevel
CARD: InterventionLevel
FULL_SCREEN_MODAL: InterventionLevel
AGENT_UNKNOWN: AgentType
ORCHESTRATOR: AgentType
KNOWLEDGE: AgentType
MATH: AgentType
CODE: AgentType
DATA_ANALYSIS: AgentType
TRANSLATION: AgentType
IMAGE: AgentType
AUDIO: AgentType
WRITING: AgentType
REASONING: AgentType

class ChatRequest(_message.Message):
    __slots__ = ("user_id", "session_id", "message", "tool_result", "user_profile", "extra_context", "history", "config", "request_id", "file_ids", "include_references", "active_tools")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    TOOL_RESULT_FIELD_NUMBER: _ClassVar[int]
    USER_PROFILE_FIELD_NUMBER: _ClassVar[int]
    EXTRA_CONTEXT_FIELD_NUMBER: _ClassVar[int]
    HISTORY_FIELD_NUMBER: _ClassVar[int]
    CONFIG_FIELD_NUMBER: _ClassVar[int]
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    FILE_IDS_FIELD_NUMBER: _ClassVar[int]
    INCLUDE_REFERENCES_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_TOOLS_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    session_id: str
    message: str
    tool_result: ToolResult
    user_profile: UserProfile
    extra_context: _struct_pb2.Struct
    history: _containers.RepeatedCompositeFieldContainer[ChatMessage]
    config: ChatConfig
    request_id: str
    file_ids: _containers.RepeatedScalarFieldContainer[str]
    include_references: bool
    active_tools: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, user_id: str | None = ..., session_id: str | None = ..., message: str | None = ..., tool_result: ToolResult | _Mapping | None = ..., user_profile: UserProfile | _Mapping | None = ..., extra_context: _struct_pb2.Struct | _Mapping | None = ..., history: _Iterable[ChatMessage | _Mapping] | None = ..., config: ChatConfig | _Mapping | None = ..., request_id: str | None = ..., file_ids: _Iterable[str] | None = ..., include_references: bool = ..., active_tools: _Iterable[str] | None = ...) -> None: ...

class UserProfile(_message.Message):
    __slots__ = ("nickname", "timezone", "language", "is_pro", "preferences", "extra_context", "level", "avatar_url")
    class PreferencesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: str | None = ..., value: str | None = ...) -> None: ...
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    TIMEZONE_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    IS_PRO_FIELD_NUMBER: _ClassVar[int]
    PREFERENCES_FIELD_NUMBER: _ClassVar[int]
    EXTRA_CONTEXT_FIELD_NUMBER: _ClassVar[int]
    LEVEL_FIELD_NUMBER: _ClassVar[int]
    AVATAR_URL_FIELD_NUMBER: _ClassVar[int]
    nickname: str
    timezone: str
    language: str
    is_pro: bool
    preferences: _containers.ScalarMap[str, str]
    extra_context: str
    level: int
    avatar_url: str
    def __init__(self, nickname: str | None = ..., timezone: str | None = ..., language: str | None = ..., is_pro: bool = ..., preferences: _Mapping[str, str] | None = ..., extra_context: str | None = ..., level: int | None = ..., avatar_url: str | None = ...) -> None: ...

class ProfileRequest(_message.Message):
    __slots__ = ("user_id",)
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    def __init__(self, user_id: str | None = ...) -> None: ...

class WeeklyReportRequest(_message.Message):
    __slots__ = ("user_id", "week_id")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    WEEK_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    week_id: str
    def __init__(self, user_id: str | None = ..., week_id: str | None = ...) -> None: ...

class WeeklyReport(_message.Message):
    __slots__ = ("summary", "tasks_completed")
    SUMMARY_FIELD_NUMBER: _ClassVar[int]
    TASKS_COMPLETED_FIELD_NUMBER: _ClassVar[int]
    summary: str
    tasks_completed: int
    def __init__(self, summary: str | None = ..., tasks_completed: int | None = ...) -> None: ...

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
    def __init__(self, tool_call_id: str | None = ..., tool_name: str | None = ..., result_json: str | None = ..., is_error: bool = ..., error_message: str | None = ...) -> None: ...

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
    def __init__(self, model: str | None = ..., temperature: float | None = ..., max_tokens: int | None = ..., tools_enabled: bool = ...) -> None: ...

class ChatMessage(_message.Message):
    __slots__ = ("role", "content", "name", "tool_call_id", "metadata")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: str | None = ..., value: str | None = ...) -> None: ...
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
    def __init__(self, role: str | None = ..., content: str | None = ..., name: str | None = ..., tool_call_id: str | None = ..., metadata: _Mapping[str, str] | None = ...) -> None: ...

class ChatResponse(_message.Message):
    __slots__ = ("response_id", "created_at", "request_id", "trace_id", "workflow_id", "prompt_version", "metadata", "delta", "tool_call", "status_update", "full_text", "error", "usage", "citations", "tool_result", "intervention", "finish_reason", "timestamp")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: str | None = ..., value: str | None = ...) -> None: ...
    RESPONSE_ID_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    TRACE_ID_FIELD_NUMBER: _ClassVar[int]
    WORKFLOW_ID_FIELD_NUMBER: _ClassVar[int]
    PROMPT_VERSION_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    DELTA_FIELD_NUMBER: _ClassVar[int]
    TOOL_CALL_FIELD_NUMBER: _ClassVar[int]
    STATUS_UPDATE_FIELD_NUMBER: _ClassVar[int]
    FULL_TEXT_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    USAGE_FIELD_NUMBER: _ClassVar[int]
    CITATIONS_FIELD_NUMBER: _ClassVar[int]
    TOOL_RESULT_FIELD_NUMBER: _ClassVar[int]
    INTERVENTION_FIELD_NUMBER: _ClassVar[int]
    FINISH_REASON_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    response_id: str
    created_at: int
    request_id: str
    trace_id: str
    workflow_id: str
    prompt_version: str
    metadata: _containers.ScalarMap[str, str]
    delta: str
    tool_call: ToolCall
    status_update: AgentStatus
    full_text: str
    error: Error
    usage: Usage
    citations: CitationBlock
    tool_result: ToolResultPayload
    intervention: InterventionPayload
    finish_reason: FinishReason
    timestamp: int
    def __init__(self, response_id: str | None = ..., created_at: int | None = ..., request_id: str | None = ..., trace_id: str | None = ..., workflow_id: str | None = ..., prompt_version: str | None = ..., metadata: _Mapping[str, str] | None = ..., delta: str | None = ..., tool_call: ToolCall | _Mapping | None = ..., status_update: AgentStatus | _Mapping | None = ..., full_text: str | None = ..., error: Error | _Mapping | None = ..., usage: Usage | _Mapping | None = ..., citations: CitationBlock | _Mapping | None = ..., tool_result: ToolResultPayload | _Mapping | None = ..., intervention: InterventionPayload | _Mapping | None = ..., finish_reason: FinishReason | str | None = ..., timestamp: int | None = ...) -> None: ...

class ResponseFeedbackRequest(_message.Message):
    __slots__ = ("user_id", "response_id", "trace_id", "feedback_type", "reasons", "free_text", "workflow_id", "prompt_version", "meta")
    class MetaEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: str | None = ..., value: str | None = ...) -> None: ...
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    RESPONSE_ID_FIELD_NUMBER: _ClassVar[int]
    TRACE_ID_FIELD_NUMBER: _ClassVar[int]
    FEEDBACK_TYPE_FIELD_NUMBER: _ClassVar[int]
    REASONS_FIELD_NUMBER: _ClassVar[int]
    FREE_TEXT_FIELD_NUMBER: _ClassVar[int]
    WORKFLOW_ID_FIELD_NUMBER: _ClassVar[int]
    PROMPT_VERSION_FIELD_NUMBER: _ClassVar[int]
    META_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    response_id: str
    trace_id: str
    feedback_type: FeedbackType
    reasons: _containers.RepeatedScalarFieldContainer[FeedbackReason]
    free_text: str
    workflow_id: str
    prompt_version: str
    meta: _containers.ScalarMap[str, str]
    def __init__(self, user_id: str | None = ..., response_id: str | None = ..., trace_id: str | None = ..., feedback_type: FeedbackType | str | None = ..., reasons: _Iterable[FeedbackReason | str] | None = ..., free_text: str | None = ..., workflow_id: str | None = ..., prompt_version: str | None = ..., meta: _Mapping[str, str] | None = ...) -> None: ...

class ResponseFeedbackResponse(_message.Message):
    __slots__ = ("success", "message", "response_id")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    RESPONSE_ID_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    response_id: str
    def __init__(self, success: bool = ..., message: str | None = ..., response_id: str | None = ...) -> None: ...

class CitationBlock(_message.Message):
    __slots__ = ("citations",)
    CITATIONS_FIELD_NUMBER: _ClassVar[int]
    citations: _containers.RepeatedCompositeFieldContainer[Citation]
    def __init__(self, citations: _Iterable[Citation | _Mapping] | None = ...) -> None: ...

class Citation(_message.Message):
    __slots__ = ("id", "title", "content", "source_type", "url", "score", "file_id", "page_number", "chunk_index", "section_title")
    ID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    SOURCE_TYPE_FIELD_NUMBER: _ClassVar[int]
    URL_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    FILE_ID_FIELD_NUMBER: _ClassVar[int]
    PAGE_NUMBER_FIELD_NUMBER: _ClassVar[int]
    CHUNK_INDEX_FIELD_NUMBER: _ClassVar[int]
    SECTION_TITLE_FIELD_NUMBER: _ClassVar[int]
    id: str
    title: str
    content: str
    source_type: str
    url: str
    score: float
    file_id: str
    page_number: int
    chunk_index: int
    section_title: str
    def __init__(self, id: str | None = ..., title: str | None = ..., content: str | None = ..., source_type: str | None = ..., url: str | None = ..., score: float | None = ..., file_id: str | None = ..., page_number: int | None = ..., chunk_index: int | None = ..., section_title: str | None = ...) -> None: ...

class ToolCall(_message.Message):
    __slots__ = ("id", "name", "arguments")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    arguments: str
    def __init__(self, id: str | None = ..., name: str | None = ..., arguments: str | None = ...) -> None: ...

class ToolResultPayload(_message.Message):
    __slots__ = ("tool_name", "success", "data", "error_message", "suggestion", "widget_type", "widget_data", "tool_call_id")
    TOOL_NAME_FIELD_NUMBER: _ClassVar[int]
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    SUGGESTION_FIELD_NUMBER: _ClassVar[int]
    WIDGET_TYPE_FIELD_NUMBER: _ClassVar[int]
    WIDGET_DATA_FIELD_NUMBER: _ClassVar[int]
    TOOL_CALL_ID_FIELD_NUMBER: _ClassVar[int]
    tool_name: str
    success: bool
    data: _struct_pb2.Struct
    error_message: str
    suggestion: str
    widget_type: str
    widget_data: _struct_pb2.Struct
    tool_call_id: str
    def __init__(self, tool_name: str | None = ..., success: bool = ..., data: _struct_pb2.Struct | _Mapping | None = ..., error_message: str | None = ..., suggestion: str | None = ..., widget_type: str | None = ..., widget_data: _struct_pb2.Struct | _Mapping | None = ..., tool_call_id: str | None = ...) -> None: ...

class EvidenceRef(_message.Message):
    __slots__ = ("type", "id", "schema_version", "user_deleted")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    USER_DELETED_FIELD_NUMBER: _ClassVar[int]
    type: str
    id: str
    schema_version: str
    user_deleted: bool
    def __init__(self, type: str | None = ..., id: str | None = ..., schema_version: str | None = ..., user_deleted: bool = ...) -> None: ...

class CoolDownPolicy(_message.Message):
    __slots__ = ("policy", "until_ms")
    POLICY_FIELD_NUMBER: _ClassVar[int]
    UNTIL_MS_FIELD_NUMBER: _ClassVar[int]
    policy: str
    until_ms: int
    def __init__(self, policy: str | None = ..., until_ms: int | None = ...) -> None: ...

class InterventionReason(_message.Message):
    __slots__ = ("trigger_event_id", "explanation_text", "confidence", "evidence_refs", "decision_trace")
    TRIGGER_EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    EXPLANATION_TEXT_FIELD_NUMBER: _ClassVar[int]
    CONFIDENCE_FIELD_NUMBER: _ClassVar[int]
    EVIDENCE_REFS_FIELD_NUMBER: _ClassVar[int]
    DECISION_TRACE_FIELD_NUMBER: _ClassVar[int]
    trigger_event_id: str
    explanation_text: str
    confidence: float
    evidence_refs: _containers.RepeatedCompositeFieldContainer[EvidenceRef]
    decision_trace: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, trigger_event_id: str | None = ..., explanation_text: str | None = ..., confidence: float | None = ..., evidence_refs: _Iterable[EvidenceRef | _Mapping] | None = ..., decision_trace: _Iterable[str] | None = ...) -> None: ...

class InterventionRequest(_message.Message):
    __slots__ = ("id", "dedupe_key", "topic", "created_at_ms", "expires_at_ms", "is_retractable", "supersedes_id", "schema_version", "policy_version", "model_version", "reason", "level", "on_reject", "content")
    ID_FIELD_NUMBER: _ClassVar[int]
    DEDUPE_KEY_FIELD_NUMBER: _ClassVar[int]
    TOPIC_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_MS_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_MS_FIELD_NUMBER: _ClassVar[int]
    IS_RETRACTABLE_FIELD_NUMBER: _ClassVar[int]
    SUPERSEDES_ID_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    POLICY_VERSION_FIELD_NUMBER: _ClassVar[int]
    MODEL_VERSION_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    LEVEL_FIELD_NUMBER: _ClassVar[int]
    ON_REJECT_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    id: str
    dedupe_key: str
    topic: str
    created_at_ms: int
    expires_at_ms: int
    is_retractable: bool
    supersedes_id: str
    schema_version: str
    policy_version: str
    model_version: str
    reason: InterventionReason
    level: InterventionLevel
    on_reject: CoolDownPolicy
    content: _struct_pb2.Struct
    def __init__(self, id: str | None = ..., dedupe_key: str | None = ..., topic: str | None = ..., created_at_ms: int | None = ..., expires_at_ms: int | None = ..., is_retractable: bool = ..., supersedes_id: str | None = ..., schema_version: str | None = ..., policy_version: str | None = ..., model_version: str | None = ..., reason: InterventionReason | _Mapping | None = ..., level: InterventionLevel | str | None = ..., on_reject: CoolDownPolicy | _Mapping | None = ..., content: _struct_pb2.Struct | _Mapping | None = ...) -> None: ...

class InterventionPayload(_message.Message):
    __slots__ = ("request",)
    REQUEST_FIELD_NUMBER: _ClassVar[int]
    request: InterventionRequest
    def __init__(self, request: InterventionRequest | _Mapping | None = ...) -> None: ...

class AgentStatus(_message.Message):
    __slots__ = ("state", "details", "current_agent_name", "active_agent")
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
    CURRENT_AGENT_NAME_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_AGENT_FIELD_NUMBER: _ClassVar[int]
    state: AgentStatus.State
    details: str
    current_agent_name: str
    active_agent: AgentType
    def __init__(self, state: AgentStatus.State | str | None = ..., details: str | None = ..., current_agent_name: str | None = ..., active_agent: AgentType | str | None = ...) -> None: ...

class Error(_message.Message):
    __slots__ = ("code", "message", "retryable", "details")
    class DetailsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: str | None = ..., value: str | None = ...) -> None: ...
    CODE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    RETRYABLE_FIELD_NUMBER: _ClassVar[int]
    DETAILS_FIELD_NUMBER: _ClassVar[int]
    code: str
    message: str
    retryable: bool
    details: _containers.ScalarMap[str, str]
    def __init__(self, code: str | None = ..., message: str | None = ..., retryable: bool = ..., details: _Mapping[str, str] | None = ...) -> None: ...

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
    def __init__(self, prompt_tokens: int | None = ..., completion_tokens: int | None = ..., total_tokens: int | None = ..., cost_micro_usd: int | None = ...) -> None: ...

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
    def __init__(self, user_id: str | None = ..., query_text: str | None = ..., limit: int | None = ..., min_score: float | None = ..., filter: MemoryFilter | _Mapping | None = ..., hybrid_alpha: float | None = ...) -> None: ...

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
    def __init__(self, tags: _Iterable[str] | None = ..., start_time: datetime.datetime | _timestamp_pb2.Timestamp | _Mapping | None = ..., end_time: datetime.datetime | _timestamp_pb2.Timestamp | _Mapping | None = ..., source_types: _Iterable[str] | None = ...) -> None: ...

class MemoryResult(_message.Message):
    __slots__ = ("items", "total_found")
    ITEMS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_FOUND_FIELD_NUMBER: _ClassVar[int]
    items: _containers.RepeatedCompositeFieldContainer[MemoryItem]
    total_found: int
    def __init__(self, items: _Iterable[MemoryItem | _Mapping] | None = ..., total_found: int | None = ...) -> None: ...

class MemoryItem(_message.Message):
    __slots__ = ("id", "content", "score", "created_at", "metadata")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: str | None = ..., value: str | None = ...) -> None: ...
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
    def __init__(self, id: str | None = ..., content: str | None = ..., score: float | None = ..., created_at: datetime.datetime | _timestamp_pb2.Timestamp | _Mapping | None = ..., metadata: _Mapping[str, str] | None = ...) -> None: ...
