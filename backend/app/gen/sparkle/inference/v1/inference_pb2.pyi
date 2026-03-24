from google.api import annotations_pb2 as _annotations_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class TaskType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    TASK_TYPE_UNSPECIFIED: _ClassVar[TaskType]
    SHORT_INFERENCE: _ClassVar[TaskType]
    HEAVY_JOB: _ClassVar[TaskType]
    SIGNAL_EXTRACTION: _ClassVar[TaskType]
    OCR: _ClassVar[TaskType]
    TRANSLATE: _ClassVar[TaskType]
    EMBEDDING: _ClassVar[TaskType]
    RERANK: _ClassVar[TaskType]
    PREDICT_NEXT_ACTIONS: _ClassVar[TaskType]
    VERIFY_PLAN: _ClassVar[TaskType]

class Priority(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    PRIORITY_UNSPECIFIED: _ClassVar[Priority]
    P0: _ClassVar[Priority]
    P1: _ClassVar[Priority]
    P2: _ClassVar[Priority]

class ResponseFormat(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    RESPONSE_FORMAT_UNSPECIFIED: _ClassVar[ResponseFormat]
    JSON_OBJECT: _ClassVar[ResponseFormat]
    TEXT: _ClassVar[ResponseFormat]

class ErrorReason(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ERROR_REASON_UNSPECIFIED: _ClassVar[ErrorReason]
    QUOTA_EXCEEDED: _ClassVar[ErrorReason]
    PROVIDER_UNAVAILABLE: _ClassVar[ErrorReason]
    SCHEMA_VIOLATION: _ClassVar[ErrorReason]
    BUDGET_EXHAUSTED: _ClassVar[ErrorReason]
    TIMEOUT: _ClassVar[ErrorReason]

class ArtifactScope(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ARTIFACT_SCOPE_UNSPECIFIED: _ClassVar[ArtifactScope]
    PRIVATE: _ClassVar[ArtifactScope]
    SHARED: _ClassVar[ArtifactScope]
    PUBLIC: _ClassVar[ArtifactScope]
TASK_TYPE_UNSPECIFIED: TaskType
SHORT_INFERENCE: TaskType
HEAVY_JOB: TaskType
SIGNAL_EXTRACTION: TaskType
OCR: TaskType
TRANSLATE: TaskType
EMBEDDING: TaskType
RERANK: TaskType
PREDICT_NEXT_ACTIONS: TaskType
VERIFY_PLAN: TaskType
PRIORITY_UNSPECIFIED: Priority
P0: Priority
P1: Priority
P2: Priority
RESPONSE_FORMAT_UNSPECIFIED: ResponseFormat
JSON_OBJECT: ResponseFormat
TEXT: ResponseFormat
ERROR_REASON_UNSPECIFIED: ErrorReason
QUOTA_EXCEEDED: ErrorReason
PROVIDER_UNAVAILABLE: ErrorReason
SCHEMA_VIOLATION: ErrorReason
BUDGET_EXHAUSTED: ErrorReason
TIMEOUT: ErrorReason
ARTIFACT_SCOPE_UNSPECIFIED: ArtifactScope
PRIVATE: ArtifactScope
SHARED: ArtifactScope
PUBLIC: ArtifactScope

class Message(_message.Message):
    __slots__ = ("role", "content")
    ROLE_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    role: str
    content: str
    def __init__(self, role: _Optional[str] = ..., content: _Optional[str] = ...) -> None: ...

class ToolDefinition(_message.Message):
    __slots__ = ("name", "description", "schema_json")
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_JSON_FIELD_NUMBER: _ClassVar[int]
    name: str
    description: str
    schema_json: str
    def __init__(self, name: _Optional[str] = ..., description: _Optional[str] = ..., schema_json: _Optional[str] = ...) -> None: ...

class Budgets(_message.Message):
    __slots__ = ("max_output_tokens", "max_input_tokens", "max_cost_level")
    MAX_OUTPUT_TOKENS_FIELD_NUMBER: _ClassVar[int]
    MAX_INPUT_TOKENS_FIELD_NUMBER: _ClassVar[int]
    MAX_COST_LEVEL_FIELD_NUMBER: _ClassVar[int]
    max_output_tokens: int
    max_input_tokens: int
    max_cost_level: str
    def __init__(self, max_output_tokens: _Optional[int] = ..., max_input_tokens: _Optional[int] = ..., max_cost_level: _Optional[str] = ...) -> None: ...

class InferenceRequest(_message.Message):
    __slots__ = ("request_id", "trace_id", "user_id", "task_type", "priority", "schema_version", "output_schema", "prompt_version", "idempotency_key", "budgets", "messages", "tools", "response_format", "metadata", "file_ids", "artifact_scope")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    TRACE_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    TASK_TYPE_FIELD_NUMBER: _ClassVar[int]
    PRIORITY_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    OUTPUT_SCHEMA_FIELD_NUMBER: _ClassVar[int]
    PROMPT_VERSION_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    BUDGETS_FIELD_NUMBER: _ClassVar[int]
    MESSAGES_FIELD_NUMBER: _ClassVar[int]
    TOOLS_FIELD_NUMBER: _ClassVar[int]
    RESPONSE_FORMAT_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    FILE_IDS_FIELD_NUMBER: _ClassVar[int]
    ARTIFACT_SCOPE_FIELD_NUMBER: _ClassVar[int]
    request_id: str
    trace_id: str
    user_id: str
    task_type: TaskType
    priority: Priority
    schema_version: str
    output_schema: str
    prompt_version: str
    idempotency_key: str
    budgets: Budgets
    messages: _containers.RepeatedCompositeFieldContainer[Message]
    tools: _containers.RepeatedCompositeFieldContainer[ToolDefinition]
    response_format: ResponseFormat
    metadata: _containers.ScalarMap[str, str]
    file_ids: _containers.RepeatedScalarFieldContainer[str]
    artifact_scope: ArtifactScope
    def __init__(self, request_id: _Optional[str] = ..., trace_id: _Optional[str] = ..., user_id: _Optional[str] = ..., task_type: _Optional[_Union[TaskType, str]] = ..., priority: _Optional[_Union[Priority, str]] = ..., schema_version: _Optional[str] = ..., output_schema: _Optional[str] = ..., prompt_version: _Optional[str] = ..., idempotency_key: _Optional[str] = ..., budgets: _Optional[_Union[Budgets, _Mapping]] = ..., messages: _Optional[_Iterable[_Union[Message, _Mapping]]] = ..., tools: _Optional[_Iterable[_Union[ToolDefinition, _Mapping]]] = ..., response_format: _Optional[_Union[ResponseFormat, str]] = ..., metadata: _Optional[_Mapping[str, str]] = ..., file_ids: _Optional[_Iterable[str]] = ..., artifact_scope: _Optional[_Union[ArtifactScope, str]] = ...) -> None: ...

class InferenceResponse(_message.Message):
    __slots__ = ("request_id", "trace_id", "ok", "provider", "model_id", "content", "error_reason", "error_message", "prompt_tokens", "completion_tokens")
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    TRACE_ID_FIELD_NUMBER: _ClassVar[int]
    OK_FIELD_NUMBER: _ClassVar[int]
    PROVIDER_FIELD_NUMBER: _ClassVar[int]
    MODEL_ID_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    ERROR_REASON_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    PROMPT_TOKENS_FIELD_NUMBER: _ClassVar[int]
    COMPLETION_TOKENS_FIELD_NUMBER: _ClassVar[int]
    request_id: str
    trace_id: str
    ok: bool
    provider: str
    model_id: str
    content: str
    error_reason: ErrorReason
    error_message: str
    prompt_tokens: int
    completion_tokens: int
    def __init__(self, request_id: _Optional[str] = ..., trace_id: _Optional[str] = ..., ok: bool = ..., provider: _Optional[str] = ..., model_id: _Optional[str] = ..., content: _Optional[str] = ..., error_reason: _Optional[_Union[ErrorReason, str]] = ..., error_message: _Optional[str] = ..., prompt_tokens: _Optional[int] = ..., completion_tokens: _Optional[int] = ...) -> None: ...

class TranslationSegment(_message.Message):
    __slots__ = ("id", "text")
    ID_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    id: str
    text: str
    def __init__(self, id: _Optional[str] = ..., text: _Optional[str] = ...) -> None: ...

class TranslationInput(_message.Message):
    __slots__ = ("segments", "source_lang", "target_lang", "domain", "style", "glossary_id", "segmenter_version")
    SEGMENTS_FIELD_NUMBER: _ClassVar[int]
    SOURCE_LANG_FIELD_NUMBER: _ClassVar[int]
    TARGET_LANG_FIELD_NUMBER: _ClassVar[int]
    DOMAIN_FIELD_NUMBER: _ClassVar[int]
    STYLE_FIELD_NUMBER: _ClassVar[int]
    GLOSSARY_ID_FIELD_NUMBER: _ClassVar[int]
    SEGMENTER_VERSION_FIELD_NUMBER: _ClassVar[int]
    segments: _containers.RepeatedCompositeFieldContainer[TranslationSegment]
    source_lang: str
    target_lang: str
    domain: str
    style: str
    glossary_id: str
    segmenter_version: str
    def __init__(self, segments: _Optional[_Iterable[_Union[TranslationSegment, _Mapping]]] = ..., source_lang: _Optional[str] = ..., target_lang: _Optional[str] = ..., domain: _Optional[str] = ..., style: _Optional[str] = ..., glossary_id: _Optional[str] = ..., segmenter_version: _Optional[str] = ...) -> None: ...

class AlignmentSpan(_message.Message):
    __slots__ = ("source_start", "source_end", "target_start", "target_end", "type")
    SOURCE_START_FIELD_NUMBER: _ClassVar[int]
    SOURCE_END_FIELD_NUMBER: _ClassVar[int]
    TARGET_START_FIELD_NUMBER: _ClassVar[int]
    TARGET_END_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    source_start: int
    source_end: int
    target_start: int
    target_end: int
    type: str
    def __init__(self, source_start: _Optional[int] = ..., source_end: _Optional[int] = ..., target_start: _Optional[int] = ..., target_end: _Optional[int] = ..., type: _Optional[str] = ...) -> None: ...

class TranslatedSegment(_message.Message):
    __slots__ = ("id", "translation", "notes", "spans")
    ID_FIELD_NUMBER: _ClassVar[int]
    TRANSLATION_FIELD_NUMBER: _ClassVar[int]
    NOTES_FIELD_NUMBER: _ClassVar[int]
    SPANS_FIELD_NUMBER: _ClassVar[int]
    id: str
    translation: str
    notes: _containers.RepeatedScalarFieldContainer[str]
    spans: _containers.RepeatedCompositeFieldContainer[AlignmentSpan]
    def __init__(self, id: _Optional[str] = ..., translation: _Optional[str] = ..., notes: _Optional[_Iterable[str]] = ..., spans: _Optional[_Iterable[_Union[AlignmentSpan, _Mapping]]] = ...) -> None: ...

class TranslationOutput(_message.Message):
    __slots__ = ("segments", "provider", "model_id", "cache_hit", "latency_ms")
    SEGMENTS_FIELD_NUMBER: _ClassVar[int]
    PROVIDER_FIELD_NUMBER: _ClassVar[int]
    MODEL_ID_FIELD_NUMBER: _ClassVar[int]
    CACHE_HIT_FIELD_NUMBER: _ClassVar[int]
    LATENCY_MS_FIELD_NUMBER: _ClassVar[int]
    segments: _containers.RepeatedCompositeFieldContainer[TranslatedSegment]
    provider: str
    model_id: str
    cache_hit: bool
    latency_ms: int
    def __init__(self, segments: _Optional[_Iterable[_Union[TranslatedSegment, _Mapping]]] = ..., provider: _Optional[str] = ..., model_id: _Optional[str] = ..., cache_hit: bool = ..., latency_ms: _Optional[int] = ...) -> None: ...
