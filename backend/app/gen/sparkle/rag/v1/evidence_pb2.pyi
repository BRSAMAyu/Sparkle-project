from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class EvidenceNode(_message.Message):
    __slots__ = ("node_id", "source_id", "snippet", "score", "source_uri", "metadata", "source_type")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    SOURCE_ID_FIELD_NUMBER: _ClassVar[int]
    SNIPPET_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    SOURCE_URI_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    SOURCE_TYPE_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    source_id: str
    snippet: str
    score: float
    source_uri: str
    metadata: _containers.ScalarMap[str, str]
    source_type: str
    def __init__(self, node_id: _Optional[str] = ..., source_id: _Optional[str] = ..., snippet: _Optional[str] = ..., score: _Optional[float] = ..., source_uri: _Optional[str] = ..., metadata: _Optional[_Mapping[str, str]] = ..., source_type: _Optional[str] = ...) -> None: ...

class EvidencePack(_message.Message):
    __slots__ = ("request_id", "trace_id", "nodes", "metadata")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    TRACE_ID_FIELD_NUMBER: _ClassVar[int]
    NODES_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    request_id: str
    trace_id: str
    nodes: _containers.RepeatedCompositeFieldContainer[EvidenceNode]
    metadata: _containers.ScalarMap[str, str]
    def __init__(self, request_id: _Optional[str] = ..., trace_id: _Optional[str] = ..., nodes: _Optional[_Iterable[_Union[EvidenceNode, _Mapping]]] = ..., metadata: _Optional[_Mapping[str, str]] = ...) -> None: ...
