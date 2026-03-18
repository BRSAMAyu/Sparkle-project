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

class PlanReviewDecision(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    PLAN_REVIEW_DECISION_UNSPECIFIED: _ClassVar[PlanReviewDecision]
    APPROVE: _ClassVar[PlanReviewDecision]
    REJECT: _ClassVar[PlanReviewDecision]
    MODIFY: _ClassVar[PlanReviewDecision]
    ACKNOWLEDGE: _ClassVar[PlanReviewDecision]

class ContentReviewFeedbackType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SATISFIED: _ClassVar[ContentReviewFeedbackType]
    UNSATISFIED: _ClassVar[ContentReviewFeedbackType]
    MODIFIED: _ClassVar[ContentReviewFeedbackType]
    REPORTED_ERROR: _ClassVar[ContentReviewFeedbackType]
    SKIPPED: _ClassVar[ContentReviewFeedbackType]

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

class ErrorCode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ERROR_CODE_UNSPECIFIED: _ClassVar[ErrorCode]
    ERROR_CODE_UNKNOWN: _ClassVar[ErrorCode]
    ERROR_CODE_INVALID_ARGUMENT: _ClassVar[ErrorCode]
    ERROR_CODE_UNAUTHORIZED: _ClassVar[ErrorCode]
    ERROR_CODE_FORBIDDEN: _ClassVar[ErrorCode]
    ERROR_CODE_NOT_FOUND: _ClassVar[ErrorCode]
    ERROR_CODE_CONFLICT: _ClassVar[ErrorCode]
    ERROR_CODE_RATE_LIMITED: _ClassVar[ErrorCode]
    ERROR_CODE_UNAVAILABLE: _ClassVar[ErrorCode]
    ERROR_CODE_TIMEOUT: _ClassVar[ErrorCode]
    ERROR_CODE_INTERNAL: _ClassVar[ErrorCode]
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
PLAN_REVIEW_DECISION_UNSPECIFIED: PlanReviewDecision
APPROVE: PlanReviewDecision
REJECT: PlanReviewDecision
MODIFY: PlanReviewDecision
ACKNOWLEDGE: PlanReviewDecision
SATISFIED: ContentReviewFeedbackType
UNSATISFIED: ContentReviewFeedbackType
MODIFIED: ContentReviewFeedbackType
REPORTED_ERROR: ContentReviewFeedbackType
SKIPPED: ContentReviewFeedbackType
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
ERROR_CODE_UNSPECIFIED: ErrorCode
ERROR_CODE_UNKNOWN: ErrorCode
ERROR_CODE_INVALID_ARGUMENT: ErrorCode
ERROR_CODE_UNAUTHORIZED: ErrorCode
ERROR_CODE_FORBIDDEN: ErrorCode
ERROR_CODE_NOT_FOUND: ErrorCode
ERROR_CODE_CONFLICT: ErrorCode
ERROR_CODE_RATE_LIMITED: ErrorCode
ERROR_CODE_UNAVAILABLE: ErrorCode
ERROR_CODE_TIMEOUT: ErrorCode
ERROR_CODE_INTERNAL: ErrorCode

class ChatRequest(_message.Message):
    __slots__ = ("user_id", "session_id", "message", "tool_result", "user_profile", "extra_context", "history", "config", "request_id", "file_ids", "include_references", "active_tools", "chat_mode")
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
    CHAT_MODE_FIELD_NUMBER: _ClassVar[int]
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
    chat_mode: str
    def __init__(self, user_id: _Optional[str] = ..., session_id: _Optional[str] = ..., message: _Optional[str] = ..., tool_result: _Optional[_Union[ToolResult, _Mapping]] = ..., user_profile: _Optional[_Union[UserProfile, _Mapping]] = ..., extra_context: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ..., history: _Optional[_Iterable[_Union[ChatMessage, _Mapping]]] = ..., config: _Optional[_Union[ChatConfig, _Mapping]] = ..., request_id: _Optional[str] = ..., file_ids: _Optional[_Iterable[str]] = ..., include_references: bool = ..., active_tools: _Optional[_Iterable[str]] = ..., chat_mode: _Optional[str] = ...) -> None: ...

class UserProfile(_message.Message):
    __slots__ = ("nickname", "timezone", "language", "is_pro", "preferences", "extra_context", "level", "avatar_url")
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
    def __init__(self, nickname: _Optional[str] = ..., timezone: _Optional[str] = ..., language: _Optional[str] = ..., is_pro: bool = ..., preferences: _Optional[_Mapping[str, str]] = ..., extra_context: _Optional[str] = ..., level: _Optional[int] = ..., avatar_url: _Optional[str] = ...) -> None: ...

class ProfileRequest(_message.Message):
    __slots__ = ("user_id",)
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    def __init__(self, user_id: _Optional[str] = ...) -> None: ...

class WeeklyReportRequest(_message.Message):
    __slots__ = ("user_id", "week_id")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    WEEK_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    week_id: str
    def __init__(self, user_id: _Optional[str] = ..., week_id: _Optional[str] = ...) -> None: ...

class WeeklyReport(_message.Message):
    __slots__ = ("summary", "tasks_completed")
    SUMMARY_FIELD_NUMBER: _ClassVar[int]
    TASKS_COMPLETED_FIELD_NUMBER: _ClassVar[int]
    summary: str
    tasks_completed: int
    def __init__(self, summary: _Optional[str] = ..., tasks_completed: _Optional[int] = ...) -> None: ...

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
    __slots__ = ("response_id", "created_at", "request_id", "trace_id", "workflow_id", "prompt_version", "metadata", "delta", "tool_call", "status_update", "full_text", "error", "usage", "citations", "tool_result", "intervention", "finish_reason", "session_id", "event_time")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
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
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    EVENT_TIME_FIELD_NUMBER: _ClassVar[int]
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
    session_id: str
    event_time: _timestamp_pb2.Timestamp
    def __init__(self, response_id: _Optional[str] = ..., created_at: _Optional[int] = ..., request_id: _Optional[str] = ..., trace_id: _Optional[str] = ..., workflow_id: _Optional[str] = ..., prompt_version: _Optional[str] = ..., metadata: _Optional[_Mapping[str, str]] = ..., delta: _Optional[str] = ..., tool_call: _Optional[_Union[ToolCall, _Mapping]] = ..., status_update: _Optional[_Union[AgentStatus, _Mapping]] = ..., full_text: _Optional[str] = ..., error: _Optional[_Union[Error, _Mapping]] = ..., usage: _Optional[_Union[Usage, _Mapping]] = ..., citations: _Optional[_Union[CitationBlock, _Mapping]] = ..., tool_result: _Optional[_Union[ToolResultPayload, _Mapping]] = ..., intervention: _Optional[_Union[InterventionPayload, _Mapping]] = ..., finish_reason: _Optional[_Union[FinishReason, str]] = ..., session_id: _Optional[str] = ..., event_time: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class ResponseFeedbackRequest(_message.Message):
    __slots__ = ("user_id", "response_id", "trace_id", "feedback_type", "reasons", "free_text", "workflow_id", "prompt_version", "meta")
    class MetaEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
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
    def __init__(self, user_id: _Optional[str] = ..., response_id: _Optional[str] = ..., trace_id: _Optional[str] = ..., feedback_type: _Optional[_Union[FeedbackType, str]] = ..., reasons: _Optional[_Iterable[_Union[FeedbackReason, str]]] = ..., free_text: _Optional[str] = ..., workflow_id: _Optional[str] = ..., prompt_version: _Optional[str] = ..., meta: _Optional[_Mapping[str, str]] = ...) -> None: ...

class ResponseFeedbackResponse(_message.Message):
    __slots__ = ("success", "message", "response_id")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    RESPONSE_ID_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    response_id: str
    def __init__(self, success: bool = ..., message: _Optional[str] = ..., response_id: _Optional[str] = ...) -> None: ...

class PlanReviewRequest(_message.Message):
    __slots__ = ("user_id", "plan_id", "review_id", "decision", "user_comment", "trace_id", "workflow_id", "prompt_version", "meta")
    class MetaEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    PLAN_ID_FIELD_NUMBER: _ClassVar[int]
    REVIEW_ID_FIELD_NUMBER: _ClassVar[int]
    DECISION_FIELD_NUMBER: _ClassVar[int]
    USER_COMMENT_FIELD_NUMBER: _ClassVar[int]
    TRACE_ID_FIELD_NUMBER: _ClassVar[int]
    WORKFLOW_ID_FIELD_NUMBER: _ClassVar[int]
    PROMPT_VERSION_FIELD_NUMBER: _ClassVar[int]
    META_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    plan_id: str
    review_id: str
    decision: PlanReviewDecision
    user_comment: str
    trace_id: str
    workflow_id: str
    prompt_version: str
    meta: _containers.ScalarMap[str, str]
    def __init__(self, user_id: _Optional[str] = ..., plan_id: _Optional[str] = ..., review_id: _Optional[str] = ..., decision: _Optional[_Union[PlanReviewDecision, str]] = ..., user_comment: _Optional[str] = ..., trace_id: _Optional[str] = ..., workflow_id: _Optional[str] = ..., prompt_version: _Optional[str] = ..., meta: _Optional[_Mapping[str, str]] = ...) -> None: ...

class PlanReviewResponse(_message.Message):
    __slots__ = ("success", "message", "review_id", "updated_plan_id")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    REVIEW_ID_FIELD_NUMBER: _ClassVar[int]
    UPDATED_PLAN_ID_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    review_id: str
    updated_plan_id: str
    def __init__(self, success: bool = ..., message: _Optional[str] = ..., review_id: _Optional[str] = ..., updated_plan_id: _Optional[str] = ...) -> None: ...

class ContentReviewFeedbackRequest(_message.Message):
    __slots__ = ("user_id", "review_id", "response_id", "feedback_type", "rating", "comment", "issues_reported", "session_id", "meta")
    class MetaEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    REVIEW_ID_FIELD_NUMBER: _ClassVar[int]
    RESPONSE_ID_FIELD_NUMBER: _ClassVar[int]
    FEEDBACK_TYPE_FIELD_NUMBER: _ClassVar[int]
    RATING_FIELD_NUMBER: _ClassVar[int]
    COMMENT_FIELD_NUMBER: _ClassVar[int]
    ISSUES_REPORTED_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    META_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    review_id: str
    response_id: str
    feedback_type: ContentReviewFeedbackType
    rating: int
    comment: str
    issues_reported: _containers.RepeatedScalarFieldContainer[str]
    session_id: str
    meta: _containers.ScalarMap[str, str]
    def __init__(self, user_id: _Optional[str] = ..., review_id: _Optional[str] = ..., response_id: _Optional[str] = ..., feedback_type: _Optional[_Union[ContentReviewFeedbackType, str]] = ..., rating: _Optional[int] = ..., comment: _Optional[str] = ..., issues_reported: _Optional[_Iterable[str]] = ..., session_id: _Optional[str] = ..., meta: _Optional[_Mapping[str, str]] = ...) -> None: ...

class ContentReviewFeedbackResponse(_message.Message):
    __slots__ = ("success", "message", "feedback_id")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    FEEDBACK_ID_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    feedback_id: str
    def __init__(self, success: bool = ..., message: _Optional[str] = ..., feedback_id: _Optional[str] = ...) -> None: ...

class ReviewOverrideRequest(_message.Message):
    __slots__ = ("user_id", "review_id", "original_decision", "new_decision", "reason", "session_id", "meta")
    class MetaEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    REVIEW_ID_FIELD_NUMBER: _ClassVar[int]
    ORIGINAL_DECISION_FIELD_NUMBER: _ClassVar[int]
    NEW_DECISION_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    META_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    review_id: str
    original_decision: str
    new_decision: str
    reason: str
    session_id: str
    meta: _containers.ScalarMap[str, str]
    def __init__(self, user_id: _Optional[str] = ..., review_id: _Optional[str] = ..., original_decision: _Optional[str] = ..., new_decision: _Optional[str] = ..., reason: _Optional[str] = ..., session_id: _Optional[str] = ..., meta: _Optional[_Mapping[str, str]] = ...) -> None: ...

class ReviewOverrideResponse(_message.Message):
    __slots__ = ("success", "message", "override_id")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    OVERRIDE_ID_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    override_id: str
    def __init__(self, success: bool = ..., message: _Optional[str] = ..., override_id: _Optional[str] = ...) -> None: ...

class ReviewAppealRequest(_message.Message):
    __slots__ = ("user_id", "review_id", "appeal_reason", "issues_with_review", "session_id", "meta")
    class MetaEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    REVIEW_ID_FIELD_NUMBER: _ClassVar[int]
    APPEAL_REASON_FIELD_NUMBER: _ClassVar[int]
    ISSUES_WITH_REVIEW_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    META_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    review_id: str
    appeal_reason: str
    issues_with_review: _containers.RepeatedScalarFieldContainer[str]
    session_id: str
    meta: _containers.ScalarMap[str, str]
    def __init__(self, user_id: _Optional[str] = ..., review_id: _Optional[str] = ..., appeal_reason: _Optional[str] = ..., issues_with_review: _Optional[_Iterable[str]] = ..., session_id: _Optional[str] = ..., meta: _Optional[_Mapping[str, str]] = ...) -> None: ...

class ReviewAppealResponse(_message.Message):
    __slots__ = ("success", "appeal_id", "status", "message")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    APPEAL_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    success: bool
    appeal_id: str
    status: str
    message: str
    def __init__(self, success: bool = ..., appeal_id: _Optional[str] = ..., status: _Optional[str] = ..., message: _Optional[str] = ...) -> None: ...

class AppealStatusRequest(_message.Message):
    __slots__ = ("user_id", "appeal_id")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    APPEAL_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    appeal_id: str
    def __init__(self, user_id: _Optional[str] = ..., appeal_id: _Optional[str] = ...) -> None: ...

class AppealStatusResponse(_message.Message):
    __slots__ = ("appeal_id", "review_id", "status", "submitted_at", "appeal_reason", "resolution", "resolved_by", "resolved_at", "secondary_decision", "secondary_score")
    APPEAL_ID_FIELD_NUMBER: _ClassVar[int]
    REVIEW_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    SUBMITTED_AT_FIELD_NUMBER: _ClassVar[int]
    APPEAL_REASON_FIELD_NUMBER: _ClassVar[int]
    RESOLUTION_FIELD_NUMBER: _ClassVar[int]
    RESOLVED_BY_FIELD_NUMBER: _ClassVar[int]
    RESOLVED_AT_FIELD_NUMBER: _ClassVar[int]
    SECONDARY_DECISION_FIELD_NUMBER: _ClassVar[int]
    SECONDARY_SCORE_FIELD_NUMBER: _ClassVar[int]
    appeal_id: str
    review_id: str
    status: str
    submitted_at: str
    appeal_reason: str
    resolution: str
    resolved_by: str
    resolved_at: str
    secondary_decision: str
    secondary_score: float
    def __init__(self, appeal_id: _Optional[str] = ..., review_id: _Optional[str] = ..., status: _Optional[str] = ..., submitted_at: _Optional[str] = ..., appeal_reason: _Optional[str] = ..., resolution: _Optional[str] = ..., resolved_by: _Optional[str] = ..., resolved_at: _Optional[str] = ..., secondary_decision: _Optional[str] = ..., secondary_score: _Optional[float] = ...) -> None: ...

class ReviewFeedbackRequest(_message.Message):
    __slots__ = ("user_id", "review_id", "feedback_type", "rating", "was_helpful", "was_accurate", "inaccurate_points", "specificity_level", "comments", "tags")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    REVIEW_ID_FIELD_NUMBER: _ClassVar[int]
    FEEDBACK_TYPE_FIELD_NUMBER: _ClassVar[int]
    RATING_FIELD_NUMBER: _ClassVar[int]
    WAS_HELPFUL_FIELD_NUMBER: _ClassVar[int]
    WAS_ACCURATE_FIELD_NUMBER: _ClassVar[int]
    INACCURATE_POINTS_FIELD_NUMBER: _ClassVar[int]
    SPECIFICITY_LEVEL_FIELD_NUMBER: _ClassVar[int]
    COMMENTS_FIELD_NUMBER: _ClassVar[int]
    TAGS_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    review_id: str
    feedback_type: str
    rating: int
    was_helpful: bool
    was_accurate: bool
    inaccurate_points: _containers.RepeatedScalarFieldContainer[str]
    specificity_level: str
    comments: str
    tags: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, user_id: _Optional[str] = ..., review_id: _Optional[str] = ..., feedback_type: _Optional[str] = ..., rating: _Optional[int] = ..., was_helpful: bool = ..., was_accurate: bool = ..., inaccurate_points: _Optional[_Iterable[str]] = ..., specificity_level: _Optional[str] = ..., comments: _Optional[str] = ..., tags: _Optional[_Iterable[str]] = ...) -> None: ...

class ReviewFeedbackResponse(_message.Message):
    __slots__ = ("success", "feedback_id", "message")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    FEEDBACK_ID_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    success: bool
    feedback_id: str
    message: str
    def __init__(self, success: bool = ..., feedback_id: _Optional[str] = ..., message: _Optional[str] = ...) -> None: ...

class RegenerationRequest(_message.Message):
    __slots__ = ("user_id", "original_content_id", "review_id", "regeneration_type", "improvement_hints", "focus_areas", "custom_instructions")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    ORIGINAL_CONTENT_ID_FIELD_NUMBER: _ClassVar[int]
    REVIEW_ID_FIELD_NUMBER: _ClassVar[int]
    REGENERATION_TYPE_FIELD_NUMBER: _ClassVar[int]
    IMPROVEMENT_HINTS_FIELD_NUMBER: _ClassVar[int]
    FOCUS_AREAS_FIELD_NUMBER: _ClassVar[int]
    CUSTOM_INSTRUCTIONS_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    original_content_id: str
    review_id: str
    regeneration_type: str
    improvement_hints: _containers.RepeatedScalarFieldContainer[str]
    focus_areas: _containers.RepeatedScalarFieldContainer[str]
    custom_instructions: str
    def __init__(self, user_id: _Optional[str] = ..., original_content_id: _Optional[str] = ..., review_id: _Optional[str] = ..., regeneration_type: _Optional[str] = ..., improvement_hints: _Optional[_Iterable[str]] = ..., focus_areas: _Optional[_Iterable[str]] = ..., custom_instructions: _Optional[str] = ...) -> None: ...

class RegenerationResponse(_message.Message):
    __slots__ = ("success", "request_id", "new_content", "new_content_id", "improvement_summary", "changes_made", "score_improvement", "generation_time_ms")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    NEW_CONTENT_FIELD_NUMBER: _ClassVar[int]
    NEW_CONTENT_ID_FIELD_NUMBER: _ClassVar[int]
    IMPROVEMENT_SUMMARY_FIELD_NUMBER: _ClassVar[int]
    CHANGES_MADE_FIELD_NUMBER: _ClassVar[int]
    SCORE_IMPROVEMENT_FIELD_NUMBER: _ClassVar[int]
    GENERATION_TIME_MS_FIELD_NUMBER: _ClassVar[int]
    success: bool
    request_id: str
    new_content: str
    new_content_id: str
    improvement_summary: str
    changes_made: _containers.RepeatedScalarFieldContainer[str]
    score_improvement: float
    generation_time_ms: int
    def __init__(self, success: bool = ..., request_id: _Optional[str] = ..., new_content: _Optional[str] = ..., new_content_id: _Optional[str] = ..., improvement_summary: _Optional[str] = ..., changes_made: _Optional[_Iterable[str]] = ..., score_improvement: _Optional[float] = ..., generation_time_ms: _Optional[int] = ...) -> None: ...

class FeedbackStatisticsRequest(_message.Message):
    __slots__ = ("user_id", "period_days")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    PERIOD_DAYS_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    period_days: int
    def __init__(self, user_id: _Optional[str] = ..., period_days: _Optional[int] = ...) -> None: ...

class FeedbackStatisticsResponse(_message.Message):
    __slots__ = ("total_feedbacks", "avg_rating", "helpful_rate", "accuracy_rate", "regeneration_requests", "successful_regenerations", "period_days")
    TOTAL_FEEDBACKS_FIELD_NUMBER: _ClassVar[int]
    AVG_RATING_FIELD_NUMBER: _ClassVar[int]
    HELPFUL_RATE_FIELD_NUMBER: _ClassVar[int]
    ACCURACY_RATE_FIELD_NUMBER: _ClassVar[int]
    REGENERATION_REQUESTS_FIELD_NUMBER: _ClassVar[int]
    SUCCESSFUL_REGENERATIONS_FIELD_NUMBER: _ClassVar[int]
    PERIOD_DAYS_FIELD_NUMBER: _ClassVar[int]
    total_feedbacks: int
    avg_rating: float
    helpful_rate: float
    accuracy_rate: float
    regeneration_requests: int
    successful_regenerations: int
    period_days: int
    def __init__(self, total_feedbacks: _Optional[int] = ..., avg_rating: _Optional[float] = ..., helpful_rate: _Optional[float] = ..., accuracy_rate: _Optional[float] = ..., regeneration_requests: _Optional[int] = ..., successful_regenerations: _Optional[int] = ..., period_days: _Optional[int] = ...) -> None: ...

class GetArbitrationQueueRequest(_message.Message):
    __slots__ = ("limit", "priority_filter", "status_filter")
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    PRIORITY_FILTER_FIELD_NUMBER: _ClassVar[int]
    STATUS_FILTER_FIELD_NUMBER: _ClassVar[int]
    limit: int
    priority_filter: str
    status_filter: str
    def __init__(self, limit: _Optional[int] = ..., priority_filter: _Optional[str] = ..., status_filter: _Optional[str] = ...) -> None: ...

class ArbitrationCaseInfo(_message.Message):
    __slots__ = ("case_id", "appeal_id", "review_id", "user_id", "escalation_reason", "priority", "created_at", "status", "assigned_to", "assigned_at", "original_review_score", "secondary_review_score", "score_discrepancy", "resolution", "final_decision", "resolved_at", "resolved_by", "notes")
    CASE_ID_FIELD_NUMBER: _ClassVar[int]
    APPEAL_ID_FIELD_NUMBER: _ClassVar[int]
    REVIEW_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    ESCALATION_REASON_FIELD_NUMBER: _ClassVar[int]
    PRIORITY_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    ASSIGNED_TO_FIELD_NUMBER: _ClassVar[int]
    ASSIGNED_AT_FIELD_NUMBER: _ClassVar[int]
    ORIGINAL_REVIEW_SCORE_FIELD_NUMBER: _ClassVar[int]
    SECONDARY_REVIEW_SCORE_FIELD_NUMBER: _ClassVar[int]
    SCORE_DISCREPANCY_FIELD_NUMBER: _ClassVar[int]
    RESOLUTION_FIELD_NUMBER: _ClassVar[int]
    FINAL_DECISION_FIELD_NUMBER: _ClassVar[int]
    RESOLVED_AT_FIELD_NUMBER: _ClassVar[int]
    RESOLVED_BY_FIELD_NUMBER: _ClassVar[int]
    NOTES_FIELD_NUMBER: _ClassVar[int]
    case_id: str
    appeal_id: str
    review_id: str
    user_id: str
    escalation_reason: str
    priority: str
    created_at: str
    status: str
    assigned_to: str
    assigned_at: str
    original_review_score: float
    secondary_review_score: float
    score_discrepancy: float
    resolution: str
    final_decision: str
    resolved_at: str
    resolved_by: str
    notes: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, case_id: _Optional[str] = ..., appeal_id: _Optional[str] = ..., review_id: _Optional[str] = ..., user_id: _Optional[str] = ..., escalation_reason: _Optional[str] = ..., priority: _Optional[str] = ..., created_at: _Optional[str] = ..., status: _Optional[str] = ..., assigned_to: _Optional[str] = ..., assigned_at: _Optional[str] = ..., original_review_score: _Optional[float] = ..., secondary_review_score: _Optional[float] = ..., score_discrepancy: _Optional[float] = ..., resolution: _Optional[str] = ..., final_decision: _Optional[str] = ..., resolved_at: _Optional[str] = ..., resolved_by: _Optional[str] = ..., notes: _Optional[_Iterable[str]] = ...) -> None: ...

class GetArbitrationQueueResponse(_message.Message):
    __slots__ = ("cases", "total_count")
    CASES_FIELD_NUMBER: _ClassVar[int]
    TOTAL_COUNT_FIELD_NUMBER: _ClassVar[int]
    cases: _containers.RepeatedCompositeFieldContainer[ArbitrationCaseInfo]
    total_count: int
    def __init__(self, cases: _Optional[_Iterable[_Union[ArbitrationCaseInfo, _Mapping]]] = ..., total_count: _Optional[int] = ...) -> None: ...

class AssignArbitrationCaseRequest(_message.Message):
    __slots__ = ("case_id", "arbitrator_id", "arbitrator_role")
    CASE_ID_FIELD_NUMBER: _ClassVar[int]
    ARBITRATOR_ID_FIELD_NUMBER: _ClassVar[int]
    ARBITRATOR_ROLE_FIELD_NUMBER: _ClassVar[int]
    case_id: str
    arbitrator_id: str
    arbitrator_role: str
    def __init__(self, case_id: _Optional[str] = ..., arbitrator_id: _Optional[str] = ..., arbitrator_role: _Optional[str] = ...) -> None: ...

class AssignArbitrationCaseResponse(_message.Message):
    __slots__ = ("success", "message")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    def __init__(self, success: bool = ..., message: _Optional[str] = ...) -> None: ...

class SubmitArbitrationDecisionRequest(_message.Message):
    __slots__ = ("case_id", "decision", "explanation", "arbitrator_id", "arbitrator_role", "feedback_for_model")
    CASE_ID_FIELD_NUMBER: _ClassVar[int]
    DECISION_FIELD_NUMBER: _ClassVar[int]
    EXPLANATION_FIELD_NUMBER: _ClassVar[int]
    ARBITRATOR_ID_FIELD_NUMBER: _ClassVar[int]
    ARBITRATOR_ROLE_FIELD_NUMBER: _ClassVar[int]
    FEEDBACK_FOR_MODEL_FIELD_NUMBER: _ClassVar[int]
    case_id: str
    decision: str
    explanation: str
    arbitrator_id: str
    arbitrator_role: str
    feedback_for_model: str
    def __init__(self, case_id: _Optional[str] = ..., decision: _Optional[str] = ..., explanation: _Optional[str] = ..., arbitrator_id: _Optional[str] = ..., arbitrator_role: _Optional[str] = ..., feedback_for_model: _Optional[str] = ...) -> None: ...

class SubmitArbitrationDecisionResponse(_message.Message):
    __slots__ = ("success", "decision_id", "message")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    DECISION_ID_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    success: bool
    decision_id: str
    message: str
    def __init__(self, success: bool = ..., decision_id: _Optional[str] = ..., message: _Optional[str] = ...) -> None: ...

class GetArbitrationQueueStatsRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArbitrationQueueStatsInfo(_message.Message):
    __slots__ = ("total_pending", "total_assigned", "total_in_review", "total_resolved_today", "avg_resolution_time_hours", "by_priority", "by_reason")
    class ByPriorityEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: int
        def __init__(self, key: _Optional[str] = ..., value: _Optional[int] = ...) -> None: ...
    class ByReasonEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: int
        def __init__(self, key: _Optional[str] = ..., value: _Optional[int] = ...) -> None: ...
    TOTAL_PENDING_FIELD_NUMBER: _ClassVar[int]
    TOTAL_ASSIGNED_FIELD_NUMBER: _ClassVar[int]
    TOTAL_IN_REVIEW_FIELD_NUMBER: _ClassVar[int]
    TOTAL_RESOLVED_TODAY_FIELD_NUMBER: _ClassVar[int]
    AVG_RESOLUTION_TIME_HOURS_FIELD_NUMBER: _ClassVar[int]
    BY_PRIORITY_FIELD_NUMBER: _ClassVar[int]
    BY_REASON_FIELD_NUMBER: _ClassVar[int]
    total_pending: int
    total_assigned: int
    total_in_review: int
    total_resolved_today: int
    avg_resolution_time_hours: float
    by_priority: _containers.ScalarMap[str, int]
    by_reason: _containers.ScalarMap[str, int]
    def __init__(self, total_pending: _Optional[int] = ..., total_assigned: _Optional[int] = ..., total_in_review: _Optional[int] = ..., total_resolved_today: _Optional[int] = ..., avg_resolution_time_hours: _Optional[float] = ..., by_priority: _Optional[_Mapping[str, int]] = ..., by_reason: _Optional[_Mapping[str, int]] = ...) -> None: ...

class GetArbitrationQueueStatsResponse(_message.Message):
    __slots__ = ("stats",)
    STATS_FIELD_NUMBER: _ClassVar[int]
    stats: ArbitrationQueueStatsInfo
    def __init__(self, stats: _Optional[_Union[ArbitrationQueueStatsInfo, _Mapping]] = ...) -> None: ...

class CitationBlock(_message.Message):
    __slots__ = ("citations",)
    CITATIONS_FIELD_NUMBER: _ClassVar[int]
    citations: _containers.RepeatedCompositeFieldContainer[Citation]
    def __init__(self, citations: _Optional[_Iterable[_Union[Citation, _Mapping]]] = ...) -> None: ...

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
    def __init__(self, id: _Optional[str] = ..., title: _Optional[str] = ..., content: _Optional[str] = ..., source_type: _Optional[str] = ..., url: _Optional[str] = ..., score: _Optional[float] = ..., file_id: _Optional[str] = ..., page_number: _Optional[int] = ..., chunk_index: _Optional[int] = ..., section_title: _Optional[str] = ...) -> None: ...

class ToolCall(_message.Message):
    __slots__ = ("id", "name", "arguments")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    arguments: str
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., arguments: _Optional[str] = ...) -> None: ...

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
    def __init__(self, tool_name: _Optional[str] = ..., success: bool = ..., data: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ..., error_message: _Optional[str] = ..., suggestion: _Optional[str] = ..., widget_type: _Optional[str] = ..., widget_data: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ..., tool_call_id: _Optional[str] = ...) -> None: ...

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
    def __init__(self, type: _Optional[str] = ..., id: _Optional[str] = ..., schema_version: _Optional[str] = ..., user_deleted: bool = ...) -> None: ...

class CoolDownPolicy(_message.Message):
    __slots__ = ("policy", "until_ms")
    POLICY_FIELD_NUMBER: _ClassVar[int]
    UNTIL_MS_FIELD_NUMBER: _ClassVar[int]
    policy: str
    until_ms: int
    def __init__(self, policy: _Optional[str] = ..., until_ms: _Optional[int] = ...) -> None: ...

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
    def __init__(self, trigger_event_id: _Optional[str] = ..., explanation_text: _Optional[str] = ..., confidence: _Optional[float] = ..., evidence_refs: _Optional[_Iterable[_Union[EvidenceRef, _Mapping]]] = ..., decision_trace: _Optional[_Iterable[str]] = ...) -> None: ...

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
    def __init__(self, id: _Optional[str] = ..., dedupe_key: _Optional[str] = ..., topic: _Optional[str] = ..., created_at_ms: _Optional[int] = ..., expires_at_ms: _Optional[int] = ..., is_retractable: bool = ..., supersedes_id: _Optional[str] = ..., schema_version: _Optional[str] = ..., policy_version: _Optional[str] = ..., model_version: _Optional[str] = ..., reason: _Optional[_Union[InterventionReason, _Mapping]] = ..., level: _Optional[_Union[InterventionLevel, str]] = ..., on_reject: _Optional[_Union[CoolDownPolicy, _Mapping]] = ..., content: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...) -> None: ...

class InterventionPayload(_message.Message):
    __slots__ = ("request",)
    REQUEST_FIELD_NUMBER: _ClassVar[int]
    request: InterventionRequest
    def __init__(self, request: _Optional[_Union[InterventionRequest, _Mapping]] = ...) -> None: ...

class AgentStatus(_message.Message):
    __slots__ = ("state", "details", "current_agent_name", "active_agent")
    class State(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        UNKNOWN: _ClassVar[AgentStatus.State]
        THINKING: _ClassVar[AgentStatus.State]
        SEARCHING: _ClassVar[AgentStatus.State]
        EXECUTING_TOOL: _ClassVar[AgentStatus.State]
        GENERATING: _ClassVar[AgentStatus.State]
        IDLE: _ClassVar[AgentStatus.State]
    UNKNOWN: AgentStatus.State
    THINKING: AgentStatus.State
    SEARCHING: AgentStatus.State
    EXECUTING_TOOL: AgentStatus.State
    GENERATING: AgentStatus.State
    IDLE: AgentStatus.State
    STATE_FIELD_NUMBER: _ClassVar[int]
    DETAILS_FIELD_NUMBER: _ClassVar[int]
    CURRENT_AGENT_NAME_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_AGENT_FIELD_NUMBER: _ClassVar[int]
    state: AgentStatus.State
    details: str
    current_agent_name: str
    active_agent: AgentType
    def __init__(self, state: _Optional[_Union[AgentStatus.State, str]] = ..., details: _Optional[str] = ..., current_agent_name: _Optional[str] = ..., active_agent: _Optional[_Union[AgentType, str]] = ...) -> None: ...

class Error(_message.Message):
    __slots__ = ("message", "retryable", "details", "error_code")
    class DetailsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    RETRYABLE_FIELD_NUMBER: _ClassVar[int]
    DETAILS_FIELD_NUMBER: _ClassVar[int]
    ERROR_CODE_FIELD_NUMBER: _ClassVar[int]
    message: str
    retryable: bool
    details: _containers.ScalarMap[str, str]
    error_code: ErrorCode
    def __init__(self, message: _Optional[str] = ..., retryable: bool = ..., details: _Optional[_Mapping[str, str]] = ..., error_code: _Optional[_Union[ErrorCode, str]] = ...) -> None: ...

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
