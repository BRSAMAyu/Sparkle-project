import datetime
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import timestamp_pb2 as _timestamp_pb2

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
    def __init__(self, galaxy_id: str | None = ..., yjs_update: bytes | None = ..., user_id: str | None = ..., timestamp: int | None = ...) -> None: ...

class SyncCollaborativeGalaxyRequest(_message.Message):
    __slots__ = ("galaxy_id", "partial_update", "user_id")
    GALAXY_ID_FIELD_NUMBER: _ClassVar[int]
    PARTIAL_UPDATE_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    galaxy_id: str
    partial_update: bytes
    user_id: str
    def __init__(self, galaxy_id: str | None = ..., partial_update: bytes | None = ..., user_id: str | None = ...) -> None: ...

class SyncCollaborativeGalaxyResponse(_message.Message):
    __slots__ = ("success", "server_update")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    SERVER_UPDATE_FIELD_NUMBER: _ClassVar[int]
    success: bool
    server_update: bytes
    def __init__(self, success: bool = ..., server_update: bytes | None = ...) -> None: ...

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
    def __init__(self, user_id: str | None = ..., node_id: str | None = ..., mastery: int | None = ..., version: datetime.datetime | _timestamp_pb2.Timestamp | _Mapping | None = ..., reason: str | None = ..., request_id: str | None = ..., revision: int | None = ...) -> None: ...

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
    def __init__(self, success: bool = ..., old_mastery: int | None = ..., new_mastery: int | None = ..., reason: str | None = ..., request_id: str | None = ..., current_revision: int | None = ...) -> None: ...
