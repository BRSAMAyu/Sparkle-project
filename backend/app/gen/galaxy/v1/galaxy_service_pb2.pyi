import datetime

from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CollaborativeGalaxyUpdate(_message.Message):
    __slots__ = ("galaxy_id", "yjs_update", "user_id", "timestamp")
    GALAXY_ID_FIELD_NUMBER: _ClassVar[int]
    YJS_UPDATE_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    galaxy_id: str
    yjs_update: bytes
    user_id: str
    timestamp: int
    def __init__(self, galaxy_id: _Optional[str] = ..., yjs_update: _Optional[bytes] = ..., user_id: _Optional[str] = ..., timestamp: _Optional[int] = ...) -> None: ...

class SyncCollaborativeGalaxyRequest(_message.Message):
    __slots__ = ("galaxy_id", "partial_update", "user_id")
    GALAXY_ID_FIELD_NUMBER: _ClassVar[int]
    PARTIAL_UPDATE_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    galaxy_id: str
    partial_update: bytes
    user_id: str
    def __init__(self, galaxy_id: _Optional[str] = ..., partial_update: _Optional[bytes] = ..., user_id: _Optional[str] = ...) -> None: ...

class SyncCollaborativeGalaxyResponse(_message.Message):
    __slots__ = ("success", "server_update")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    SERVER_UPDATE_FIELD_NUMBER: _ClassVar[int]
    success: bool
    server_update: bytes
    def __init__(self, success: bool = ..., server_update: _Optional[bytes] = ...) -> None: ...

class UpdateNodeMasteryRequest(_message.Message):
    __slots__ = ("user_id", "node_id", "mastery", "version", "reason", "request_id", "revision")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    MASTERY_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    REVISION_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    node_id: str
    mastery: int
    version: _timestamp_pb2.Timestamp
    reason: str
    request_id: str
    revision: int
    def __init__(self, user_id: _Optional[str] = ..., node_id: _Optional[str] = ..., mastery: _Optional[int] = ..., version: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., reason: _Optional[str] = ..., request_id: _Optional[str] = ..., revision: _Optional[int] = ...) -> None: ...

class UpdateNodeMasteryResponse(_message.Message):
    __slots__ = ("success", "old_mastery", "new_mastery", "reason", "request_id", "current_revision")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    OLD_MASTERY_FIELD_NUMBER: _ClassVar[int]
    NEW_MASTERY_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    CURRENT_REVISION_FIELD_NUMBER: _ClassVar[int]
    success: bool
    old_mastery: int
    new_mastery: int
    reason: str
    request_id: str
    current_revision: int
    def __init__(self, success: bool = ..., old_mastery: _Optional[int] = ..., new_mastery: _Optional[int] = ..., reason: _Optional[str] = ..., request_id: _Optional[str] = ..., current_revision: _Optional[int] = ...) -> None: ...
