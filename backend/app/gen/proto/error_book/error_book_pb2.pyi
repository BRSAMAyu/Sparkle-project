import datetime

from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

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
    def __init__(self, id: _Optional[str] = ..., user_id: _Optional[str] = ..., subject_code: _Optional[str] = ..., chapter: _Optional[str] = ..., question_text: _Optional[str] = ..., question_image_url: _Optional[str] = ..., user_answer: _Optional[str] = ..., correct_answer: _Optional[str] = ..., mastery_level: _Optional[float] = ..., review_count: _Optional[int] = ..., next_review_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., last_reviewed_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., latest_analysis: _Optional[_Union[ErrorAnalysisResult, _Mapping]] = ..., knowledge_links: _Optional[_Iterable[_Union[KnowledgeLinkBrief, _Mapping]]] = ..., created_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., updated_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

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
    def __init__(self, error_type: _Optional[str] = ..., error_type_label: _Optional[str] = ..., root_cause: _Optional[str] = ..., correct_approach: _Optional[str] = ..., similar_traps: _Optional[_Iterable[str]] = ..., recommended_knowledge: _Optional[_Iterable[str]] = ..., study_suggestion: _Optional[str] = ..., ocr_text: _Optional[str] = ...) -> None: ...

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
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., relevance: _Optional[float] = ..., is_primary: bool = ...) -> None: ...

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
    def __init__(self, user_id: _Optional[str] = ..., question_text: _Optional[str] = ..., question_image_url: _Optional[str] = ..., user_answer: _Optional[str] = ..., correct_answer: _Optional[str] = ..., subject_code: _Optional[str] = ..., chapter: _Optional[str] = ...) -> None: ...

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
    def __init__(self, user_id: _Optional[str] = ..., subject_code: _Optional[str] = ..., chapter: _Optional[str] = ..., error_type: _Optional[str] = ..., mastery_min: _Optional[float] = ..., mastery_max: _Optional[float] = ..., need_review: bool = ..., keyword: _Optional[str] = ..., page: _Optional[int] = ..., page_size: _Optional[int] = ...) -> None: ...

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
    def __init__(self, items: _Optional[_Iterable[_Union[ErrorRecord, _Mapping]]] = ..., total: _Optional[int] = ..., page: _Optional[int] = ..., page_size: _Optional[int] = ..., has_next: bool = ...) -> None: ...

class GetErrorRequest(_message.Message):
    __slots__ = ("error_id", "user_id")
    ERROR_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    error_id: str
    user_id: str
    def __init__(self, error_id: _Optional[str] = ..., user_id: _Optional[str] = ...) -> None: ...

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
    def __init__(self, error_id: _Optional[str] = ..., user_id: _Optional[str] = ..., question_text: _Optional[str] = ..., user_answer: _Optional[str] = ..., correct_answer: _Optional[str] = ..., subject_code: _Optional[str] = ..., chapter: _Optional[str] = ..., question_image_url: _Optional[str] = ...) -> None: ...

class DeleteErrorRequest(_message.Message):
    __slots__ = ("error_id", "user_id")
    ERROR_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    error_id: str
    user_id: str
    def __init__(self, error_id: _Optional[str] = ..., user_id: _Optional[str] = ...) -> None: ...

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
    def __init__(self, error_id: _Optional[str] = ..., user_id: _Optional[str] = ...) -> None: ...

class AnalyzeErrorResponse(_message.Message):
    __slots__ = ("message",)
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    message: str
    def __init__(self, message: _Optional[str] = ...) -> None: ...

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
    def __init__(self, error_id: _Optional[str] = ..., user_id: _Optional[str] = ..., performance: _Optional[str] = ..., time_spent_seconds: _Optional[int] = ...) -> None: ...

class GetReviewStatsRequest(_message.Message):
    __slots__ = ("user_id",)
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    def __init__(self, user_id: _Optional[str] = ...) -> None: ...

class ReviewStatsResponse(_message.Message):
    __slots__ = ("total_errors", "mastered_count", "need_review_count", "review_streak_days", "subject_distribution")
    class SubjectDistributionEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: int
        def __init__(self, key: _Optional[str] = ..., value: _Optional[int] = ...) -> None: ...
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
    def __init__(self, total_errors: _Optional[int] = ..., mastered_count: _Optional[int] = ..., need_review_count: _Optional[int] = ..., review_streak_days: _Optional[int] = ..., subject_distribution: _Optional[_Mapping[str, int]] = ...) -> None: ...

class GetTodayReviewsRequest(_message.Message):
    __slots__ = ("user_id", "page", "page_size")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    PAGE_FIELD_NUMBER: _ClassVar[int]
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    page: int
    page_size: int
    def __init__(self, user_id: _Optional[str] = ..., page: _Optional[int] = ..., page_size: _Optional[int] = ...) -> None: ...
