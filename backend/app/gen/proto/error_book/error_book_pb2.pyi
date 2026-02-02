import datetime
from collections.abc import Iterable as _Iterable
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers

DESCRIPTOR: _descriptor.FileDescriptor

class ErrorRecord(_message.Message):
    __slots__ = ("id", "user_id", "subject_code", "chapter", "question_text", "question_image_url", "user_answer", "correct_answer", "mastery_level", "review_count", "next_review_at", "last_reviewed_at", "latest_analysis", "knowledge_links", "created_at", "updated_at")
    ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    SUBJECT_CODE_FIELD_NUMBER: _ClassVar[int]
    CHAPTER_FIELD_NUMBER: _ClassVar[int]
    QUESTION_TEXT_FIELD_NUMBER: _ClassVar[int]
    QUESTION_IMAGE_URL_FIELD_NUMBER: _ClassVar[int]
    USER_ANSWER_FIELD_NUMBER: _ClassVar[int]
    CORRECT_ANSWER_FIELD_NUMBER: _ClassVar[int]
    MASTERY_LEVEL_FIELD_NUMBER: _ClassVar[int]
    REVIEW_COUNT_FIELD_NUMBER: _ClassVar[int]
    NEXT_REVIEW_AT_FIELD_NUMBER: _ClassVar[int]
    LAST_REVIEWED_AT_FIELD_NUMBER: _ClassVar[int]
    LATEST_ANALYSIS_FIELD_NUMBER: _ClassVar[int]
    KNOWLEDGE_LINKS_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    id: str
    user_id: str
    subject_code: str
    chapter: str
    question_text: str
    question_image_url: str
    user_answer: str
    correct_answer: str
    mastery_level: float
    review_count: int
    next_review_at: _timestamp_pb2.Timestamp
    last_reviewed_at: _timestamp_pb2.Timestamp
    latest_analysis: ErrorAnalysisResult
    knowledge_links: _containers.RepeatedCompositeFieldContainer[KnowledgeLinkBrief]
    created_at: _timestamp_pb2.Timestamp
    updated_at: _timestamp_pb2.Timestamp
    def __init__(self, id: str | None = ..., user_id: str | None = ..., subject_code: str | None = ..., chapter: str | None = ..., question_text: str | None = ..., question_image_url: str | None = ..., user_answer: str | None = ..., correct_answer: str | None = ..., mastery_level: float | None = ..., review_count: int | None = ..., next_review_at: datetime.datetime | _timestamp_pb2.Timestamp | _Mapping | None = ..., last_reviewed_at: datetime.datetime | _timestamp_pb2.Timestamp | _Mapping | None = ..., latest_analysis: ErrorAnalysisResult | _Mapping | None = ..., knowledge_links: _Iterable[KnowledgeLinkBrief | _Mapping] | None = ..., created_at: datetime.datetime | _timestamp_pb2.Timestamp | _Mapping | None = ..., updated_at: datetime.datetime | _timestamp_pb2.Timestamp | _Mapping | None = ...) -> None: ...

class ErrorAnalysisResult(_message.Message):
    __slots__ = ("error_type", "error_type_label", "root_cause", "correct_approach", "similar_traps", "recommended_knowledge", "study_suggestion", "ocr_text")
    ERROR_TYPE_FIELD_NUMBER: _ClassVar[int]
    ERROR_TYPE_LABEL_FIELD_NUMBER: _ClassVar[int]
    ROOT_CAUSE_FIELD_NUMBER: _ClassVar[int]
    CORRECT_APPROACH_FIELD_NUMBER: _ClassVar[int]
    SIMILAR_TRAPS_FIELD_NUMBER: _ClassVar[int]
    RECOMMENDED_KNOWLEDGE_FIELD_NUMBER: _ClassVar[int]
    STUDY_SUGGESTION_FIELD_NUMBER: _ClassVar[int]
    OCR_TEXT_FIELD_NUMBER: _ClassVar[int]
    error_type: str
    error_type_label: str
    root_cause: str
    correct_approach: str
    similar_traps: _containers.RepeatedScalarFieldContainer[str]
    recommended_knowledge: _containers.RepeatedScalarFieldContainer[str]
    study_suggestion: str
    ocr_text: str
    def __init__(self, error_type: str | None = ..., error_type_label: str | None = ..., root_cause: str | None = ..., correct_approach: str | None = ..., similar_traps: _Iterable[str] | None = ..., recommended_knowledge: _Iterable[str] | None = ..., study_suggestion: str | None = ..., ocr_text: str | None = ...) -> None: ...

class KnowledgeLinkBrief(_message.Message):
    __slots__ = ("id", "name", "relevance", "is_primary")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    RELEVANCE_FIELD_NUMBER: _ClassVar[int]
    IS_PRIMARY_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    relevance: float
    is_primary: bool
    def __init__(self, id: str | None = ..., name: str | None = ..., relevance: float | None = ..., is_primary: bool = ...) -> None: ...

class CreateErrorRequest(_message.Message):
    __slots__ = ("user_id", "question_text", "question_image_url", "user_answer", "correct_answer", "subject_code", "chapter")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    QUESTION_TEXT_FIELD_NUMBER: _ClassVar[int]
    QUESTION_IMAGE_URL_FIELD_NUMBER: _ClassVar[int]
    USER_ANSWER_FIELD_NUMBER: _ClassVar[int]
    CORRECT_ANSWER_FIELD_NUMBER: _ClassVar[int]
    SUBJECT_CODE_FIELD_NUMBER: _ClassVar[int]
    CHAPTER_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    question_text: str
    question_image_url: str
    user_answer: str
    correct_answer: str
    subject_code: str
    chapter: str
    def __init__(self, user_id: str | None = ..., question_text: str | None = ..., question_image_url: str | None = ..., user_answer: str | None = ..., correct_answer: str | None = ..., subject_code: str | None = ..., chapter: str | None = ...) -> None: ...

class ListErrorsRequest(_message.Message):
    __slots__ = ("user_id", "subject_code", "chapter", "error_type", "mastery_min", "mastery_max", "need_review", "keyword", "page", "page_size")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    SUBJECT_CODE_FIELD_NUMBER: _ClassVar[int]
    CHAPTER_FIELD_NUMBER: _ClassVar[int]
    ERROR_TYPE_FIELD_NUMBER: _ClassVar[int]
    MASTERY_MIN_FIELD_NUMBER: _ClassVar[int]
    MASTERY_MAX_FIELD_NUMBER: _ClassVar[int]
    NEED_REVIEW_FIELD_NUMBER: _ClassVar[int]
    KEYWORD_FIELD_NUMBER: _ClassVar[int]
    PAGE_FIELD_NUMBER: _ClassVar[int]
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    subject_code: str
    chapter: str
    error_type: str
    mastery_min: float
    mastery_max: float
    need_review: bool
    keyword: str
    page: int
    page_size: int
    def __init__(self, user_id: str | None = ..., subject_code: str | None = ..., chapter: str | None = ..., error_type: str | None = ..., mastery_min: float | None = ..., mastery_max: float | None = ..., need_review: bool = ..., keyword: str | None = ..., page: int | None = ..., page_size: int | None = ...) -> None: ...

class ListErrorsResponse(_message.Message):
    __slots__ = ("items", "total", "page", "page_size", "has_next")
    ITEMS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_FIELD_NUMBER: _ClassVar[int]
    PAGE_FIELD_NUMBER: _ClassVar[int]
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    HAS_NEXT_FIELD_NUMBER: _ClassVar[int]
    items: _containers.RepeatedCompositeFieldContainer[ErrorRecord]
    total: int
    page: int
    page_size: int
    has_next: bool
    def __init__(self, items: _Iterable[ErrorRecord | _Mapping] | None = ..., total: int | None = ..., page: int | None = ..., page_size: int | None = ..., has_next: bool = ...) -> None: ...

class GetErrorRequest(_message.Message):
    __slots__ = ("error_id", "user_id")
    ERROR_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    error_id: str
    user_id: str
    def __init__(self, error_id: str | None = ..., user_id: str | None = ...) -> None: ...

class UpdateErrorRequest(_message.Message):
    __slots__ = ("error_id", "user_id", "question_text", "user_answer", "correct_answer", "subject_code", "chapter", "question_image_url")
    ERROR_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    QUESTION_TEXT_FIELD_NUMBER: _ClassVar[int]
    USER_ANSWER_FIELD_NUMBER: _ClassVar[int]
    CORRECT_ANSWER_FIELD_NUMBER: _ClassVar[int]
    SUBJECT_CODE_FIELD_NUMBER: _ClassVar[int]
    CHAPTER_FIELD_NUMBER: _ClassVar[int]
    QUESTION_IMAGE_URL_FIELD_NUMBER: _ClassVar[int]
    error_id: str
    user_id: str
    question_text: str
    user_answer: str
    correct_answer: str
    subject_code: str
    chapter: str
    question_image_url: str
    def __init__(self, error_id: str | None = ..., user_id: str | None = ..., question_text: str | None = ..., user_answer: str | None = ..., correct_answer: str | None = ..., subject_code: str | None = ..., chapter: str | None = ..., question_image_url: str | None = ...) -> None: ...

class DeleteErrorRequest(_message.Message):
    __slots__ = ("error_id", "user_id")
    ERROR_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    error_id: str
    user_id: str
    def __init__(self, error_id: str | None = ..., user_id: str | None = ...) -> None: ...

class DeleteErrorResponse(_message.Message):
    __slots__ = ("success",)
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    success: bool
    def __init__(self, success: bool = ...) -> None: ...

class AnalyzeErrorRequest(_message.Message):
    __slots__ = ("error_id", "user_id")
    ERROR_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    error_id: str
    user_id: str
    def __init__(self, error_id: str | None = ..., user_id: str | None = ...) -> None: ...

class AnalyzeErrorResponse(_message.Message):
    __slots__ = ("message",)
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    message: str
    def __init__(self, message: str | None = ...) -> None: ...

class SubmitReviewRequest(_message.Message):
    __slots__ = ("error_id", "user_id", "performance", "time_spent_seconds")
    ERROR_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    PERFORMANCE_FIELD_NUMBER: _ClassVar[int]
    TIME_SPENT_SECONDS_FIELD_NUMBER: _ClassVar[int]
    error_id: str
    user_id: str
    performance: str
    time_spent_seconds: int
    def __init__(self, error_id: str | None = ..., user_id: str | None = ..., performance: str | None = ..., time_spent_seconds: int | None = ...) -> None: ...

class GetReviewStatsRequest(_message.Message):
    __slots__ = ("user_id",)
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    def __init__(self, user_id: str | None = ...) -> None: ...

class ReviewStatsResponse(_message.Message):
    __slots__ = ("total_errors", "mastered_count", "need_review_count", "review_streak_days", "subject_distribution")
    class SubjectDistributionEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: int
        def __init__(self, key: str | None = ..., value: int | None = ...) -> None: ...
    TOTAL_ERRORS_FIELD_NUMBER: _ClassVar[int]
    MASTERED_COUNT_FIELD_NUMBER: _ClassVar[int]
    NEED_REVIEW_COUNT_FIELD_NUMBER: _ClassVar[int]
    REVIEW_STREAK_DAYS_FIELD_NUMBER: _ClassVar[int]
    SUBJECT_DISTRIBUTION_FIELD_NUMBER: _ClassVar[int]
    total_errors: int
    mastered_count: int
    need_review_count: int
    review_streak_days: int
    subject_distribution: _containers.ScalarMap[str, int]
    def __init__(self, total_errors: int | None = ..., mastered_count: int | None = ..., need_review_count: int | None = ..., review_streak_days: int | None = ..., subject_distribution: _Mapping[str, int] | None = ...) -> None: ...

class GetTodayReviewsRequest(_message.Message):
    __slots__ = ("user_id", "page", "page_size")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    PAGE_FIELD_NUMBER: _ClassVar[int]
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    page: int
    page_size: int
    def __init__(self, user_id: str | None = ..., page: int | None = ..., page_size: int | None = ...) -> None: ...
