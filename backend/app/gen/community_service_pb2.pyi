import datetime

from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf import empty_pb2 as _empty_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class FriendshipStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    FRIENDSHIP_STATUS_UNSPECIFIED: _ClassVar[FriendshipStatus]
    PENDING: _ClassVar[FriendshipStatus]
    ACCEPTED: _ClassVar[FriendshipStatus]
    BLOCKED: _ClassVar[FriendshipStatus]

class GroupType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    GROUP_TYPE_UNSPECIFIED: _ClassVar[GroupType]
    SQUAD: _ClassVar[GroupType]
    SPRINT: _ClassVar[GroupType]
    OFFICIAL: _ClassVar[GroupType]

class GroupRole(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    GROUP_ROLE_UNSPECIFIED: _ClassVar[GroupRole]
    OWNER: _ClassVar[GroupRole]
    ADMIN: _ClassVar[GroupRole]
    MEMBER: _ClassVar[GroupRole]

class MessageType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    MESSAGE_TYPE_UNSPECIFIED: _ClassVar[MessageType]
    TEXT: _ClassVar[MessageType]
    TASK_SHARE: _ClassVar[MessageType]
    PLAN_SHARE: _ClassVar[MessageType]
    FRAGMENT_SHARE: _ClassVar[MessageType]
    CAPSULE_SHARE: _ClassVar[MessageType]
    PRISM_SHARE: _ClassVar[MessageType]
    FILE_SHARE: _ClassVar[MessageType]
    PROGRESS: _ClassVar[MessageType]
    ACHIEVEMENT: _ClassVar[MessageType]
    CHECKIN: _ClassVar[MessageType]
    SYSTEM: _ClassVar[MessageType]
    BROADCAST: _ClassVar[MessageType]

class SearchVisibility(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SEARCH_VISIBILITY_UNSPECIFIED: _ClassVar[SearchVisibility]
    EVERYONE: _ClassVar[SearchVisibility]
    FRIENDS: _ClassVar[SearchVisibility]
    NOBODY: _ClassVar[SearchVisibility]
FRIENDSHIP_STATUS_UNSPECIFIED: FriendshipStatus
PENDING: FriendshipStatus
ACCEPTED: FriendshipStatus
BLOCKED: FriendshipStatus
GROUP_TYPE_UNSPECIFIED: GroupType
SQUAD: GroupType
SPRINT: GroupType
OFFICIAL: GroupType
GROUP_ROLE_UNSPECIFIED: GroupRole
OWNER: GroupRole
ADMIN: GroupRole
MEMBER: GroupRole
MESSAGE_TYPE_UNSPECIFIED: MessageType
TEXT: MessageType
TASK_SHARE: MessageType
PLAN_SHARE: MessageType
FRAGMENT_SHARE: MessageType
CAPSULE_SHARE: MessageType
PRISM_SHARE: MessageType
FILE_SHARE: MessageType
PROGRESS: MessageType
ACHIEVEMENT: MessageType
CHECKIN: MessageType
SYSTEM: MessageType
BROADCAST: MessageType
SEARCH_VISIBILITY_UNSPECIFIED: SearchVisibility
EVERYONE: SearchVisibility
FRIENDS: SearchVisibility
NOBODY: SearchVisibility

class UUID(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: str
    def __init__(self, value: _Optional[str] = ...) -> None: ...

class UserBrief(_message.Message):
    __slots__ = ("id", "username", "nickname", "avatar_url", "flame_level", "flame_brightness", "status")
    ID_FIELD_NUMBER: _ClassVar[int]
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    AVATAR_URL_FIELD_NUMBER: _ClassVar[int]
    FLAME_LEVEL_FIELD_NUMBER: _ClassVar[int]
    FLAME_BRIGHTNESS_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    id: UUID
    username: str
    nickname: str
    avatar_url: str
    flame_level: int
    flame_brightness: float
    status: str
    def __init__(self, id: _Optional[_Union[UUID, _Mapping]] = ..., username: _Optional[str] = ..., nickname: _Optional[str] = ..., avatar_url: _Optional[str] = ..., flame_level: _Optional[int] = ..., flame_brightness: _Optional[float] = ..., status: _Optional[str] = ...) -> None: ...

class FriendRequest(_message.Message):
    __slots__ = ("target_user_id", "message")
    TARGET_USER_ID_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    target_user_id: UUID
    message: str
    def __init__(self, target_user_id: _Optional[_Union[UUID, _Mapping]] = ..., message: _Optional[str] = ...) -> None: ...

class FriendResponse(_message.Message):
    __slots__ = ("friendship_id", "accept")
    FRIENDSHIP_ID_FIELD_NUMBER: _ClassVar[int]
    ACCEPT_FIELD_NUMBER: _ClassVar[int]
    friendship_id: UUID
    accept: bool
    def __init__(self, friendship_id: _Optional[_Union[UUID, _Mapping]] = ..., accept: bool = ...) -> None: ...

class FriendshipInfo(_message.Message):
    __slots__ = ("friend", "status", "match_reason", "initiated_by_me")
    class MatchReasonEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    FRIEND_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    MATCH_REASON_FIELD_NUMBER: _ClassVar[int]
    INITIATED_BY_ME_FIELD_NUMBER: _ClassVar[int]
    friend: UserBrief
    status: FriendshipStatus
    match_reason: _containers.ScalarMap[str, str]
    initiated_by_me: bool
    def __init__(self, friend: _Optional[_Union[UserBrief, _Mapping]] = ..., status: _Optional[_Union[FriendshipStatus, str]] = ..., match_reason: _Optional[_Mapping[str, str]] = ..., initiated_by_me: bool = ...) -> None: ...

class BlockUserRequest(_message.Message):
    __slots__ = ("target_user_id", "reason")
    TARGET_USER_ID_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    target_user_id: UUID
    reason: str
    def __init__(self, target_user_id: _Optional[_Union[UUID, _Mapping]] = ..., reason: _Optional[str] = ...) -> None: ...

class BlockUserInfo(_message.Message):
    __slots__ = ("blocked_user", "reason", "created_at")
    BLOCKED_USER_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    blocked_user: UserBrief
    reason: str
    created_at: _timestamp_pb2.Timestamp
    def __init__(self, blocked_user: _Optional[_Union[UserBrief, _Mapping]] = ..., reason: _Optional[str] = ..., created_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class GroupCreate(_message.Message):
    __slots__ = ("name", "description", "type", "focus_tags", "deadline", "sprint_goal", "max_members", "is_public", "join_requires_approval")
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    FOCUS_TAGS_FIELD_NUMBER: _ClassVar[int]
    DEADLINE_FIELD_NUMBER: _ClassVar[int]
    SPRINT_GOAL_FIELD_NUMBER: _ClassVar[int]
    MAX_MEMBERS_FIELD_NUMBER: _ClassVar[int]
    IS_PUBLIC_FIELD_NUMBER: _ClassVar[int]
    JOIN_REQUIRES_APPROVAL_FIELD_NUMBER: _ClassVar[int]
    name: str
    description: str
    type: GroupType
    focus_tags: _containers.RepeatedScalarFieldContainer[str]
    deadline: _timestamp_pb2.Timestamp
    sprint_goal: str
    max_members: int
    is_public: bool
    join_requires_approval: bool
    def __init__(self, name: _Optional[str] = ..., description: _Optional[str] = ..., type: _Optional[_Union[GroupType, str]] = ..., focus_tags: _Optional[_Iterable[str]] = ..., deadline: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., sprint_goal: _Optional[str] = ..., max_members: _Optional[int] = ..., is_public: bool = ..., join_requires_approval: bool = ...) -> None: ...

class GroupInfo(_message.Message):
    __slots__ = ("id", "name", "description", "avatar_url", "type", "focus_tags", "deadline", "sprint_goal", "days_remaining", "member_count", "total_flame_power", "today_checkin_count", "total_tasks_completed", "max_members", "is_public", "join_requires_approval", "my_role")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    AVATAR_URL_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    FOCUS_TAGS_FIELD_NUMBER: _ClassVar[int]
    DEADLINE_FIELD_NUMBER: _ClassVar[int]
    SPRINT_GOAL_FIELD_NUMBER: _ClassVar[int]
    DAYS_REMAINING_FIELD_NUMBER: _ClassVar[int]
    MEMBER_COUNT_FIELD_NUMBER: _ClassVar[int]
    TOTAL_FLAME_POWER_FIELD_NUMBER: _ClassVar[int]
    TODAY_CHECKIN_COUNT_FIELD_NUMBER: _ClassVar[int]
    TOTAL_TASKS_COMPLETED_FIELD_NUMBER: _ClassVar[int]
    MAX_MEMBERS_FIELD_NUMBER: _ClassVar[int]
    IS_PUBLIC_FIELD_NUMBER: _ClassVar[int]
    JOIN_REQUIRES_APPROVAL_FIELD_NUMBER: _ClassVar[int]
    MY_ROLE_FIELD_NUMBER: _ClassVar[int]
    id: UUID
    name: str
    description: str
    avatar_url: str
    type: GroupType
    focus_tags: _containers.RepeatedScalarFieldContainer[str]
    deadline: _timestamp_pb2.Timestamp
    sprint_goal: str
    days_remaining: int
    member_count: int
    total_flame_power: int
    today_checkin_count: int
    total_tasks_completed: int
    max_members: int
    is_public: bool
    join_requires_approval: bool
    my_role: GroupRole
    def __init__(self, id: _Optional[_Union[UUID, _Mapping]] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., avatar_url: _Optional[str] = ..., type: _Optional[_Union[GroupType, str]] = ..., focus_tags: _Optional[_Iterable[str]] = ..., deadline: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., sprint_goal: _Optional[str] = ..., days_remaining: _Optional[int] = ..., member_count: _Optional[int] = ..., total_flame_power: _Optional[int] = ..., today_checkin_count: _Optional[int] = ..., total_tasks_completed: _Optional[int] = ..., max_members: _Optional[int] = ..., is_public: bool = ..., join_requires_approval: bool = ..., my_role: _Optional[_Union[GroupRole, str]] = ...) -> None: ...

class GroupMemberInfo(_message.Message):
    __slots__ = ("user", "role", "flame_contribution", "tasks_completed", "checkin_streak", "joined_at", "last_active_at")
    USER_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    FLAME_CONTRIBUTION_FIELD_NUMBER: _ClassVar[int]
    TASKS_COMPLETED_FIELD_NUMBER: _ClassVar[int]
    CHECKIN_STREAK_FIELD_NUMBER: _ClassVar[int]
    JOINED_AT_FIELD_NUMBER: _ClassVar[int]
    LAST_ACTIVE_AT_FIELD_NUMBER: _ClassVar[int]
    user: UserBrief
    role: GroupRole
    flame_contribution: int
    tasks_completed: int
    checkin_streak: int
    joined_at: _timestamp_pb2.Timestamp
    last_active_at: _timestamp_pb2.Timestamp
    def __init__(self, user: _Optional[_Union[UserBrief, _Mapping]] = ..., role: _Optional[_Union[GroupRole, str]] = ..., flame_contribution: _Optional[int] = ..., tasks_completed: _Optional[int] = ..., checkin_streak: _Optional[int] = ..., joined_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., last_active_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class MessageSend(_message.Message):
    __slots__ = ("message_type", "content", "content_data", "reply_to_id", "thread_root_id", "mention_user_ids", "nonce")
    MESSAGE_TYPE_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    CONTENT_DATA_FIELD_NUMBER: _ClassVar[int]
    REPLY_TO_ID_FIELD_NUMBER: _ClassVar[int]
    THREAD_ROOT_ID_FIELD_NUMBER: _ClassVar[int]
    MENTION_USER_IDS_FIELD_NUMBER: _ClassVar[int]
    NONCE_FIELD_NUMBER: _ClassVar[int]
    message_type: MessageType
    content: str
    content_data: str
    reply_to_id: UUID
    thread_root_id: UUID
    mention_user_ids: _containers.RepeatedCompositeFieldContainer[UUID]
    nonce: str
    def __init__(self, message_type: _Optional[_Union[MessageType, str]] = ..., content: _Optional[str] = ..., content_data: _Optional[str] = ..., reply_to_id: _Optional[_Union[UUID, _Mapping]] = ..., thread_root_id: _Optional[_Union[UUID, _Mapping]] = ..., mention_user_ids: _Optional[_Iterable[_Union[UUID, _Mapping]]] = ..., nonce: _Optional[str] = ...) -> None: ...

class MessageInfo(_message.Message):
    __slots__ = ("id", "sender", "message_type", "content", "content_data", "reply_to_id", "thread_root_id", "mention_user_ids", "reactions", "is_revoked", "revoked_at", "edited_at", "created_at")
    class ReactionsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    ID_FIELD_NUMBER: _ClassVar[int]
    SENDER_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_TYPE_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    CONTENT_DATA_FIELD_NUMBER: _ClassVar[int]
    REPLY_TO_ID_FIELD_NUMBER: _ClassVar[int]
    THREAD_ROOT_ID_FIELD_NUMBER: _ClassVar[int]
    MENTION_USER_IDS_FIELD_NUMBER: _ClassVar[int]
    REACTIONS_FIELD_NUMBER: _ClassVar[int]
    IS_REVOKED_FIELD_NUMBER: _ClassVar[int]
    REVOKED_AT_FIELD_NUMBER: _ClassVar[int]
    EDITED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    id: UUID
    sender: UserBrief
    message_type: MessageType
    content: str
    content_data: str
    reply_to_id: UUID
    thread_root_id: UUID
    mention_user_ids: _containers.RepeatedCompositeFieldContainer[UUID]
    reactions: _containers.ScalarMap[str, str]
    is_revoked: bool
    revoked_at: _timestamp_pb2.Timestamp
    edited_at: _timestamp_pb2.Timestamp
    created_at: _timestamp_pb2.Timestamp
    def __init__(self, id: _Optional[_Union[UUID, _Mapping]] = ..., sender: _Optional[_Union[UserBrief, _Mapping]] = ..., message_type: _Optional[_Union[MessageType, str]] = ..., content: _Optional[str] = ..., content_data: _Optional[str] = ..., reply_to_id: _Optional[_Union[UUID, _Mapping]] = ..., thread_root_id: _Optional[_Union[UUID, _Mapping]] = ..., mention_user_ids: _Optional[_Iterable[_Union[UUID, _Mapping]]] = ..., reactions: _Optional[_Mapping[str, str]] = ..., is_revoked: bool = ..., revoked_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., edited_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., created_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class PrivateMessageSend(_message.Message):
    __slots__ = ("target_user_id", "message_type", "content", "content_data", "reply_to_id", "thread_root_id", "mention_user_ids", "nonce")
    TARGET_USER_ID_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_TYPE_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    CONTENT_DATA_FIELD_NUMBER: _ClassVar[int]
    REPLY_TO_ID_FIELD_NUMBER: _ClassVar[int]
    THREAD_ROOT_ID_FIELD_NUMBER: _ClassVar[int]
    MENTION_USER_IDS_FIELD_NUMBER: _ClassVar[int]
    NONCE_FIELD_NUMBER: _ClassVar[int]
    target_user_id: UUID
    message_type: MessageType
    content: str
    content_data: str
    reply_to_id: UUID
    thread_root_id: UUID
    mention_user_ids: _containers.RepeatedCompositeFieldContainer[UUID]
    nonce: str
    def __init__(self, target_user_id: _Optional[_Union[UUID, _Mapping]] = ..., message_type: _Optional[_Union[MessageType, str]] = ..., content: _Optional[str] = ..., content_data: _Optional[str] = ..., reply_to_id: _Optional[_Union[UUID, _Mapping]] = ..., thread_root_id: _Optional[_Union[UUID, _Mapping]] = ..., mention_user_ids: _Optional[_Iterable[_Union[UUID, _Mapping]]] = ..., nonce: _Optional[str] = ...) -> None: ...

class PrivateMessageInfo(_message.Message):
    __slots__ = ("id", "sender", "receiver", "message_type", "content", "content_data", "reply_to_id", "thread_root_id", "mention_user_ids", "reactions", "is_revoked", "revoked_at", "edited_at", "is_read", "read_at", "created_at")
    class ReactionsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    ID_FIELD_NUMBER: _ClassVar[int]
    SENDER_FIELD_NUMBER: _ClassVar[int]
    RECEIVER_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_TYPE_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    CONTENT_DATA_FIELD_NUMBER: _ClassVar[int]
    REPLY_TO_ID_FIELD_NUMBER: _ClassVar[int]
    THREAD_ROOT_ID_FIELD_NUMBER: _ClassVar[int]
    MENTION_USER_IDS_FIELD_NUMBER: _ClassVar[int]
    REACTIONS_FIELD_NUMBER: _ClassVar[int]
    IS_REVOKED_FIELD_NUMBER: _ClassVar[int]
    REVOKED_AT_FIELD_NUMBER: _ClassVar[int]
    EDITED_AT_FIELD_NUMBER: _ClassVar[int]
    IS_READ_FIELD_NUMBER: _ClassVar[int]
    READ_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    id: UUID
    sender: UserBrief
    receiver: UserBrief
    message_type: MessageType
    content: str
    content_data: str
    reply_to_id: UUID
    thread_root_id: UUID
    mention_user_ids: _containers.RepeatedCompositeFieldContainer[UUID]
    reactions: _containers.ScalarMap[str, str]
    is_revoked: bool
    revoked_at: _timestamp_pb2.Timestamp
    edited_at: _timestamp_pb2.Timestamp
    is_read: bool
    read_at: _timestamp_pb2.Timestamp
    created_at: _timestamp_pb2.Timestamp
    def __init__(self, id: _Optional[_Union[UUID, _Mapping]] = ..., sender: _Optional[_Union[UserBrief, _Mapping]] = ..., receiver: _Optional[_Union[UserBrief, _Mapping]] = ..., message_type: _Optional[_Union[MessageType, str]] = ..., content: _Optional[str] = ..., content_data: _Optional[str] = ..., reply_to_id: _Optional[_Union[UUID, _Mapping]] = ..., thread_root_id: _Optional[_Union[UUID, _Mapping]] = ..., mention_user_ids: _Optional[_Iterable[_Union[UUID, _Mapping]]] = ..., reactions: _Optional[_Mapping[str, str]] = ..., is_revoked: bool = ..., revoked_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., edited_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., is_read: bool = ..., read_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., created_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class CheckinRequest(_message.Message):
    __slots__ = ("group_id", "message", "today_duration_minutes")
    GROUP_ID_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    TODAY_DURATION_MINUTES_FIELD_NUMBER: _ClassVar[int]
    group_id: UUID
    message: str
    today_duration_minutes: int
    def __init__(self, group_id: _Optional[_Union[UUID, _Mapping]] = ..., message: _Optional[str] = ..., today_duration_minutes: _Optional[int] = ...) -> None: ...

class CheckinResponse(_message.Message):
    __slots__ = ("success", "new_streak", "flame_earned", "rank_in_group", "group_checkin_count")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    NEW_STREAK_FIELD_NUMBER: _ClassVar[int]
    FLAME_EARNED_FIELD_NUMBER: _ClassVar[int]
    RANK_IN_GROUP_FIELD_NUMBER: _ClassVar[int]
    GROUP_CHECKIN_COUNT_FIELD_NUMBER: _ClassVar[int]
    success: bool
    new_streak: int
    flame_earned: int
    rank_in_group: int
    group_checkin_count: int
    def __init__(self, success: bool = ..., new_streak: _Optional[int] = ..., flame_earned: _Optional[int] = ..., rank_in_group: _Optional[int] = ..., group_checkin_count: _Optional[int] = ...) -> None: ...

class UserPrivacySettings(_message.Message):
    __slots__ = ("searchable_by",)
    SEARCHABLE_BY_FIELD_NUMBER: _ClassVar[int]
    searchable_by: SearchVisibility
    def __init__(self, searchable_by: _Optional[_Union[SearchVisibility, str]] = ...) -> None: ...

class SearchUsersRequest(_message.Message):
    __slots__ = ("keyword", "limit")
    KEYWORD_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    keyword: str
    limit: int
    def __init__(self, keyword: _Optional[str] = ..., limit: _Optional[int] = ...) -> None: ...

class SearchGroupsRequest(_message.Message):
    __slots__ = ("keyword", "type", "limit")
    KEYWORD_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    keyword: str
    type: GroupType
    limit: int
    def __init__(self, keyword: _Optional[str] = ..., type: _Optional[_Union[GroupType, str]] = ..., limit: _Optional[int] = ...) -> None: ...

class JoinGroupRequest(_message.Message):
    __slots__ = ("group_id", "message")
    GROUP_ID_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    group_id: UUID
    message: str
    def __init__(self, group_id: _Optional[_Union[UUID, _Mapping]] = ..., message: _Optional[str] = ...) -> None: ...

class SendGroupMessageRequest(_message.Message):
    __slots__ = ("group_id", "message")
    GROUP_ID_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    group_id: UUID
    message: MessageSend
    def __init__(self, group_id: _Optional[_Union[UUID, _Mapping]] = ..., message: _Optional[_Union[MessageSend, _Mapping]] = ...) -> None: ...

class GetGroupMessagesRequest(_message.Message):
    __slots__ = ("group_id", "before_id", "limit")
    GROUP_ID_FIELD_NUMBER: _ClassVar[int]
    BEFORE_ID_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    group_id: UUID
    before_id: UUID
    limit: int
    def __init__(self, group_id: _Optional[_Union[UUID, _Mapping]] = ..., before_id: _Optional[_Union[UUID, _Mapping]] = ..., limit: _Optional[int] = ...) -> None: ...

class StreamGroupMessagesRequest(_message.Message):
    __slots__ = ("group_id", "after_id")
    GROUP_ID_FIELD_NUMBER: _ClassVar[int]
    AFTER_ID_FIELD_NUMBER: _ClassVar[int]
    group_id: UUID
    after_id: UUID
    def __init__(self, group_id: _Optional[_Union[UUID, _Mapping]] = ..., after_id: _Optional[_Union[UUID, _Mapping]] = ...) -> None: ...

class RevokeMessageRequest(_message.Message):
    __slots__ = ("message_id", "group_id")
    MESSAGE_ID_FIELD_NUMBER: _ClassVar[int]
    GROUP_ID_FIELD_NUMBER: _ClassVar[int]
    message_id: UUID
    group_id: UUID
    def __init__(self, message_id: _Optional[_Union[UUID, _Mapping]] = ..., group_id: _Optional[_Union[UUID, _Mapping]] = ...) -> None: ...

class MarkMessagesReadRequest(_message.Message):
    __slots__ = ("group_id", "up_to_message_id")
    GROUP_ID_FIELD_NUMBER: _ClassVar[int]
    UP_TO_MESSAGE_ID_FIELD_NUMBER: _ClassVar[int]
    group_id: UUID
    up_to_message_id: UUID
    def __init__(self, group_id: _Optional[_Union[UUID, _Mapping]] = ..., up_to_message_id: _Optional[_Union[UUID, _Mapping]] = ...) -> None: ...

class MarkMessagesReadResponse(_message.Message):
    __slots__ = ("updated_count", "up_to_message_id")
    UPDATED_COUNT_FIELD_NUMBER: _ClassVar[int]
    UP_TO_MESSAGE_ID_FIELD_NUMBER: _ClassVar[int]
    updated_count: int
    up_to_message_id: UUID
    def __init__(self, updated_count: _Optional[int] = ..., up_to_message_id: _Optional[_Union[UUID, _Mapping]] = ...) -> None: ...

class GetPrivateMessagesRequest(_message.Message):
    __slots__ = ("friend_id", "before_id", "limit")
    FRIEND_ID_FIELD_NUMBER: _ClassVar[int]
    BEFORE_ID_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    friend_id: UUID
    before_id: UUID
    limit: int
    def __init__(self, friend_id: _Optional[_Union[UUID, _Mapping]] = ..., before_id: _Optional[_Union[UUID, _Mapping]] = ..., limit: _Optional[int] = ...) -> None: ...
