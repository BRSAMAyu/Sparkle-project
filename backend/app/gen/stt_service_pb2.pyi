import datetime

from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class AudioFormat(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    AUDIO_FORMAT_UNSPECIFIED: _ClassVar[AudioFormat]
    AUDIO_FORMAT_PCM: _ClassVar[AudioFormat]
    AUDIO_FORMAT_WAV: _ClassVar[AudioFormat]
    AUDIO_FORMAT_MP3: _ClassVar[AudioFormat]
    AUDIO_FORMAT_M4A: _ClassVar[AudioFormat]
    AUDIO_FORMAT_OGG: _ClassVar[AudioFormat]
    AUDIO_FORMAT_WEBM: _ClassVar[AudioFormat]
    AUDIO_FORMAT_OPUS: _ClassVar[AudioFormat]

class LanguageCode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    LANGUAGE_CODE_UNSPECIFIED: _ClassVar[LanguageCode]
    LANGUAGE_CODE_ZH_CN: _ClassVar[LanguageCode]
    LANGUAGE_CODE_ZH_TW: _ClassVar[LanguageCode]
    LANGUAGE_CODE_EN_US: _ClassVar[LanguageCode]
    LANGUAGE_CODE_EN_GB: _ClassVar[LanguageCode]
    LANGUAGE_CODE_JA_JP: _ClassVar[LanguageCode]
    LANGUAGE_CODE_KO_KR: _ClassVar[LanguageCode]

class STTErrorCode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    STT_ERROR_CODE_UNSPECIFIED: _ClassVar[STTErrorCode]
    STT_ERROR_CODE_AUDIO_TOO_LARGE: _ClassVar[STTErrorCode]
    STT_ERROR_CODE_UNSUPPORTED_FORMAT: _ClassVar[STTErrorCode]
    STT_ERROR_CODE_INVALID_SAMPLE_RATE: _ClassVar[STTErrorCode]
    STT_ERROR_CODE_NO_SPEECH_DETECTED: _ClassVar[STTErrorCode]
    STT_ERROR_CODE_RECOGNITION_FAILED: _ClassVar[STTErrorCode]
    STT_ERROR_CODE_PROVIDER_UNAVAILABLE: _ClassVar[STTErrorCode]
    STT_ERROR_CODE_RATE_LIMITED: _ClassVar[STTErrorCode]
    STT_ERROR_CODE_UNAUTHORIZED: _ClassVar[STTErrorCode]
    STT_ERROR_CODE_INTERNAL_ERROR: _ClassVar[STTErrorCode]
AUDIO_FORMAT_UNSPECIFIED: AudioFormat
AUDIO_FORMAT_PCM: AudioFormat
AUDIO_FORMAT_WAV: AudioFormat
AUDIO_FORMAT_MP3: AudioFormat
AUDIO_FORMAT_M4A: AudioFormat
AUDIO_FORMAT_OGG: AudioFormat
AUDIO_FORMAT_WEBM: AudioFormat
AUDIO_FORMAT_OPUS: AudioFormat
LANGUAGE_CODE_UNSPECIFIED: LanguageCode
LANGUAGE_CODE_ZH_CN: LanguageCode
LANGUAGE_CODE_ZH_TW: LanguageCode
LANGUAGE_CODE_EN_US: LanguageCode
LANGUAGE_CODE_EN_GB: LanguageCode
LANGUAGE_CODE_JA_JP: LanguageCode
LANGUAGE_CODE_KO_KR: LanguageCode
STT_ERROR_CODE_UNSPECIFIED: STTErrorCode
STT_ERROR_CODE_AUDIO_TOO_LARGE: STTErrorCode
STT_ERROR_CODE_UNSUPPORTED_FORMAT: STTErrorCode
STT_ERROR_CODE_INVALID_SAMPLE_RATE: STTErrorCode
STT_ERROR_CODE_NO_SPEECH_DETECTED: STTErrorCode
STT_ERROR_CODE_RECOGNITION_FAILED: STTErrorCode
STT_ERROR_CODE_PROVIDER_UNAVAILABLE: STTErrorCode
STT_ERROR_CODE_RATE_LIMITED: STTErrorCode
STT_ERROR_CODE_UNAUTHORIZED: STTErrorCode
STT_ERROR_CODE_INTERNAL_ERROR: STTErrorCode

class AudioChunk(_message.Message):
    __slots__ = ("data", "sample_rate", "format", "language", "user_id", "session_id", "end_of_stream")
    DATA_FIELD_NUMBER: _ClassVar[int]
    SAMPLE_RATE_FIELD_NUMBER: _ClassVar[int]
    FORMAT_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    END_OF_STREAM_FIELD_NUMBER: _ClassVar[int]
    data: bytes
    sample_rate: int
    format: str
    language: str
    user_id: str
    session_id: str
    end_of_stream: bool
    def __init__(self, data: _Optional[bytes] = ..., sample_rate: _Optional[int] = ..., format: _Optional[str] = ..., language: _Optional[str] = ..., user_id: _Optional[str] = ..., session_id: _Optional[str] = ..., end_of_stream: bool = ...) -> None: ...

class TranscriptionResult(_message.Message):
    __slots__ = ("text", "is_final", "confidence", "sequence", "timestamp", "session_id", "error")
    TEXT_FIELD_NUMBER: _ClassVar[int]
    IS_FINAL_FIELD_NUMBER: _ClassVar[int]
    CONFIDENCE_FIELD_NUMBER: _ClassVar[int]
    SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    text: str
    is_final: bool
    confidence: float
    sequence: int
    timestamp: _timestamp_pb2.Timestamp
    session_id: str
    error: TranscriptionError
    def __init__(self, text: _Optional[str] = ..., is_final: bool = ..., confidence: _Optional[float] = ..., sequence: _Optional[int] = ..., timestamp: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., session_id: _Optional[str] = ..., error: _Optional[_Union[TranscriptionError, _Mapping]] = ...) -> None: ...

class TranscriptionError(_message.Message):
    __slots__ = ("code", "message", "recoverable")
    CODE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    RECOVERABLE_FIELD_NUMBER: _ClassVar[int]
    code: str
    message: str
    recoverable: bool
    def __init__(self, code: _Optional[str] = ..., message: _Optional[str] = ..., recoverable: bool = ...) -> None: ...

class TranscribeRequest(_message.Message):
    __slots__ = ("audio_data", "filename", "language", "format", "user_id", "enable_enhancement", "sample_rate")
    AUDIO_DATA_FIELD_NUMBER: _ClassVar[int]
    FILENAME_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    FORMAT_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    ENABLE_ENHANCEMENT_FIELD_NUMBER: _ClassVar[int]
    SAMPLE_RATE_FIELD_NUMBER: _ClassVar[int]
    audio_data: bytes
    filename: str
    language: str
    format: str
    user_id: str
    enable_enhancement: bool
    sample_rate: int
    def __init__(self, audio_data: _Optional[bytes] = ..., filename: _Optional[str] = ..., language: _Optional[str] = ..., format: _Optional[str] = ..., user_id: _Optional[str] = ..., enable_enhancement: bool = ..., sample_rate: _Optional[int] = ...) -> None: ...

class TranscribeResponse(_message.Message):
    __slots__ = ("text", "duration_seconds", "confidence", "detected_language", "enhanced_text", "words", "metadata", "error")
    TEXT_FIELD_NUMBER: _ClassVar[int]
    DURATION_SECONDS_FIELD_NUMBER: _ClassVar[int]
    CONFIDENCE_FIELD_NUMBER: _ClassVar[int]
    DETECTED_LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    ENHANCED_TEXT_FIELD_NUMBER: _ClassVar[int]
    WORDS_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    text: str
    duration_seconds: float
    confidence: float
    detected_language: str
    enhanced_text: str
    words: _containers.RepeatedCompositeFieldContainer[WordTimestamp]
    metadata: TranscriptionMetadata
    error: TranscriptionError
    def __init__(self, text: _Optional[str] = ..., duration_seconds: _Optional[float] = ..., confidence: _Optional[float] = ..., detected_language: _Optional[str] = ..., enhanced_text: _Optional[str] = ..., words: _Optional[_Iterable[_Union[WordTimestamp, _Mapping]]] = ..., metadata: _Optional[_Union[TranscriptionMetadata, _Mapping]] = ..., error: _Optional[_Union[TranscriptionError, _Mapping]] = ...) -> None: ...

class WordTimestamp(_message.Message):
    __slots__ = ("word", "start_time", "end_time", "confidence")
    WORD_FIELD_NUMBER: _ClassVar[int]
    START_TIME_FIELD_NUMBER: _ClassVar[int]
    END_TIME_FIELD_NUMBER: _ClassVar[int]
    CONFIDENCE_FIELD_NUMBER: _ClassVar[int]
    word: str
    start_time: float
    end_time: float
    confidence: float
    def __init__(self, word: _Optional[str] = ..., start_time: _Optional[float] = ..., end_time: _Optional[float] = ..., confidence: _Optional[float] = ...) -> None: ...

class TranscriptionMetadata(_message.Message):
    __slots__ = ("provider", "model", "processing_time_ms", "file_size_bytes", "channels", "sample_rate")
    PROVIDER_FIELD_NUMBER: _ClassVar[int]
    MODEL_FIELD_NUMBER: _ClassVar[int]
    PROCESSING_TIME_MS_FIELD_NUMBER: _ClassVar[int]
    FILE_SIZE_BYTES_FIELD_NUMBER: _ClassVar[int]
    CHANNELS_FIELD_NUMBER: _ClassVar[int]
    SAMPLE_RATE_FIELD_NUMBER: _ClassVar[int]
    provider: str
    model: str
    processing_time_ms: int
    file_size_bytes: int
    channels: int
    sample_rate: int
    def __init__(self, provider: _Optional[str] = ..., model: _Optional[str] = ..., processing_time_ms: _Optional[int] = ..., file_size_bytes: _Optional[int] = ..., channels: _Optional[int] = ..., sample_rate: _Optional[int] = ...) -> None: ...

class EnhanceRequest(_message.Message):
    __slots__ = ("text", "user_id", "options")
    TEXT_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    OPTIONS_FIELD_NUMBER: _ClassVar[int]
    text: str
    user_id: str
    options: EnhancementOptions
    def __init__(self, text: _Optional[str] = ..., user_id: _Optional[str] = ..., options: _Optional[_Union[EnhancementOptions, _Mapping]] = ...) -> None: ...

class EnhancementOptions(_message.Message):
    __slots__ = ("add_punctuation", "correct_typos", "format_speakers", "language")
    ADD_PUNCTUATION_FIELD_NUMBER: _ClassVar[int]
    CORRECT_TYPOS_FIELD_NUMBER: _ClassVar[int]
    FORMAT_SPEAKERS_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    add_punctuation: bool
    correct_typos: bool
    format_speakers: bool
    language: str
    def __init__(self, add_punctuation: bool = ..., correct_typos: bool = ..., format_speakers: bool = ..., language: _Optional[str] = ...) -> None: ...

class EnhanceResponse(_message.Message):
    __slots__ = ("enhanced_text", "original_text", "changes_count", "processing_time_ms")
    ENHANCED_TEXT_FIELD_NUMBER: _ClassVar[int]
    ORIGINAL_TEXT_FIELD_NUMBER: _ClassVar[int]
    CHANGES_COUNT_FIELD_NUMBER: _ClassVar[int]
    PROCESSING_TIME_MS_FIELD_NUMBER: _ClassVar[int]
    enhanced_text: str
    original_text: str
    changes_count: int
    processing_time_ms: int
    def __init__(self, enhanced_text: _Optional[str] = ..., original_text: _Optional[str] = ..., changes_count: _Optional[int] = ..., processing_time_ms: _Optional[int] = ...) -> None: ...
