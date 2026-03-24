from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CandidateAction(_message.Message):
    __slots__ = ("id", "type", "trigger", "content_seed", "priority", "metadata")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    ID_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    TRIGGER_FIELD_NUMBER: _ClassVar[int]
    CONTENT_SEED_FIELD_NUMBER: _ClassVar[int]
    PRIORITY_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    id: str
    type: str
    trigger: str
    content_seed: str
    priority: float
    metadata: _containers.ScalarMap[str, str]
    def __init__(self, id: _Optional[str] = ..., type: _Optional[str] = ..., trigger: _Optional[str] = ..., content_seed: _Optional[str] = ..., priority: _Optional[float] = ..., metadata: _Optional[_Mapping[str, str]] = ...) -> None: ...

class NextActionsCandidateSet(_message.Message):
    __slots__ = ("request_id", "trace_id", "user_id", "schema_version", "idempotency_key", "candidates", "metadata")
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
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    CANDIDATES_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    request_id: str
    trace_id: str
    user_id: str
    schema_version: str
    idempotency_key: str
    candidates: _containers.RepeatedCompositeFieldContainer[CandidateAction]
    metadata: _containers.ScalarMap[str, str]
    def __init__(self, request_id: _Optional[str] = ..., trace_id: _Optional[str] = ..., user_id: _Optional[str] = ..., schema_version: _Optional[str] = ..., idempotency_key: _Optional[str] = ..., candidates: _Optional[_Iterable[_Union[CandidateAction, _Mapping]]] = ..., metadata: _Optional[_Mapping[str, str]] = ...) -> None: ...

class ContextEnvelope(_message.Message):
    __slots__ = ("context_version", "window", "focus", "comprehension", "time", "content", "pii_scrubbed")
    CONTEXT_VERSION_FIELD_NUMBER: _ClassVar[int]
    WINDOW_FIELD_NUMBER: _ClassVar[int]
    FOCUS_FIELD_NUMBER: _ClassVar[int]
    COMPREHENSION_FIELD_NUMBER: _ClassVar[int]
    TIME_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    PII_SCRUBBED_FIELD_NUMBER: _ClassVar[int]
    context_version: str
    window: str
    focus: FocusMetrics
    comprehension: ComprehensionMetrics
    time: TimeContext
    content: ContentContext
    pii_scrubbed: bool
    def __init__(self, context_version: _Optional[str] = ..., window: _Optional[str] = ..., focus: _Optional[_Union[FocusMetrics, _Mapping]] = ..., comprehension: _Optional[_Union[ComprehensionMetrics, _Mapping]] = ..., time: _Optional[_Union[TimeContext, _Mapping]] = ..., content: _Optional[_Union[ContentContext, _Mapping]] = ..., pii_scrubbed: bool = ...) -> None: ...

class FocusMetrics(_message.Message):
    __slots__ = ("planned_min", "actual_min", "interruptions", "completion")
    PLANNED_MIN_FIELD_NUMBER: _ClassVar[int]
    ACTUAL_MIN_FIELD_NUMBER: _ClassVar[int]
    INTERRUPTIONS_FIELD_NUMBER: _ClassVar[int]
    COMPLETION_FIELD_NUMBER: _ClassVar[int]
    planned_min: int
    actual_min: int
    interruptions: int
    completion: float
    def __init__(self, planned_min: _Optional[int] = ..., actual_min: _Optional[int] = ..., interruptions: _Optional[int] = ..., completion: _Optional[float] = ...) -> None: ...

class ComprehensionMetrics(_message.Message):
    __slots__ = ("translation_requests", "translation_granularity", "unknown_terms_saved")
    TRANSLATION_REQUESTS_FIELD_NUMBER: _ClassVar[int]
    TRANSLATION_GRANULARITY_FIELD_NUMBER: _ClassVar[int]
    UNKNOWN_TERMS_SAVED_FIELD_NUMBER: _ClassVar[int]
    translation_requests: int
    translation_granularity: str
    unknown_terms_saved: int
    def __init__(self, translation_requests: _Optional[int] = ..., translation_granularity: _Optional[str] = ..., unknown_terms_saved: _Optional[int] = ...) -> None: ...

class TimeContext(_message.Message):
    __slots__ = ("local_hour", "day_of_week")
    LOCAL_HOUR_FIELD_NUMBER: _ClassVar[int]
    DAY_OF_WEEK_FIELD_NUMBER: _ClassVar[int]
    local_hour: int
    day_of_week: str
    def __init__(self, local_hour: _Optional[int] = ..., day_of_week: _Optional[str] = ...) -> None: ...

class ContentContext(_message.Message):
    __slots__ = ("language", "domain")
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    DOMAIN_FIELD_NUMBER: _ClassVar[int]
    language: str
    domain: str
    def __init__(self, language: _Optional[str] = ..., domain: _Optional[str] = ...) -> None: ...

class FeatureExtractResult(_message.Message):
    __slots__ = ("version", "rhythm", "friction", "energy", "risk")
    VERSION_FIELD_NUMBER: _ClassVar[int]
    RHYTHM_FIELD_NUMBER: _ClassVar[int]
    FRICTION_FIELD_NUMBER: _ClassVar[int]
    ENERGY_FIELD_NUMBER: _ClassVar[int]
    RISK_FIELD_NUMBER: _ClassVar[int]
    version: str
    rhythm: LearningRhythm
    friction: UnderstandingFriction
    energy: EnergyState
    risk: TaskRisk
    def __init__(self, version: _Optional[str] = ..., rhythm: _Optional[_Union[LearningRhythm, _Mapping]] = ..., friction: _Optional[_Union[UnderstandingFriction, _Mapping]] = ..., energy: _Optional[_Union[EnergyState, _Mapping]] = ..., risk: _Optional[_Union[TaskRisk, _Mapping]] = ...) -> None: ...

class LearningRhythm(_message.Message):
    __slots__ = ("deviating_from_plan", "interruption_frequency")
    DEVIATING_FROM_PLAN_FIELD_NUMBER: _ClassVar[int]
    INTERRUPTION_FREQUENCY_FIELD_NUMBER: _ClassVar[int]
    deviating_from_plan: bool
    interruption_frequency: int
    def __init__(self, deviating_from_plan: bool = ..., interruption_frequency: _Optional[int] = ...) -> None: ...

class UnderstandingFriction(_message.Message):
    __slots__ = ("translation_density", "escalating_granularity")
    TRANSLATION_DENSITY_FIELD_NUMBER: _ClassVar[int]
    ESCALATING_GRANULARITY_FIELD_NUMBER: _ClassVar[int]
    translation_density: int
    escalating_granularity: bool
    def __init__(self, translation_density: _Optional[int] = ..., escalating_granularity: bool = ...) -> None: ...

class EnergyState(_message.Message):
    __slots__ = ("late_night_fatigue", "short_session_trend")
    LATE_NIGHT_FATIGUE_FIELD_NUMBER: _ClassVar[int]
    SHORT_SESSION_TREND_FIELD_NUMBER: _ClassVar[int]
    late_night_fatigue: bool
    short_session_trend: bool
    def __init__(self, late_night_fatigue: bool = ..., short_session_trend: bool = ...) -> None: ...

class TaskRisk(_message.Message):
    __slots__ = ("consecutive_failures", "procrastination_detected")
    CONSECUTIVE_FAILURES_FIELD_NUMBER: _ClassVar[int]
    PROCRASTINATION_DETECTED_FIELD_NUMBER: _ClassVar[int]
    consecutive_failures: bool
    procrastination_detected: bool
    def __init__(self, consecutive_failures: bool = ..., procrastination_detected: bool = ...) -> None: ...

class Signals(_message.Message):
    __slots__ = ("version", "signals")
    VERSION_FIELD_NUMBER: _ClassVar[int]
    SIGNALS_FIELD_NUMBER: _ClassVar[int]
    version: str
    signals: _containers.RepeatedCompositeFieldContainer[Signal]
    def __init__(self, version: _Optional[str] = ..., signals: _Optional[_Iterable[_Union[Signal, _Mapping]]] = ...) -> None: ...

class Signal(_message.Message):
    __slots__ = ("type", "confidence", "reason", "metadata")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    TYPE_FIELD_NUMBER: _ClassVar[int]
    CONFIDENCE_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    type: str
    confidence: float
    reason: str
    metadata: _containers.ScalarMap[str, str]
    def __init__(self, type: _Optional[str] = ..., confidence: _Optional[float] = ..., reason: _Optional[str] = ..., metadata: _Optional[_Mapping[str, str]] = ...) -> None: ...

class CandidateActionV2(_message.Message):
    __slots__ = ("id", "action_type", "title", "reason", "confidence", "timing_hint", "payload_seed", "metadata")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    ID_FIELD_NUMBER: _ClassVar[int]
    ACTION_TYPE_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    CONFIDENCE_FIELD_NUMBER: _ClassVar[int]
    TIMING_HINT_FIELD_NUMBER: _ClassVar[int]
    PAYLOAD_SEED_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    id: str
    action_type: str
    title: str
    reason: str
    confidence: float
    timing_hint: str
    payload_seed: str
    metadata: _containers.ScalarMap[str, str]
    def __init__(self, id: _Optional[str] = ..., action_type: _Optional[str] = ..., title: _Optional[str] = ..., reason: _Optional[str] = ..., confidence: _Optional[float] = ..., timing_hint: _Optional[str] = ..., payload_seed: _Optional[str] = ..., metadata: _Optional[_Mapping[str, str]] = ...) -> None: ...
