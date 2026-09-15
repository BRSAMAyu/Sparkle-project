from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.websocket import ConnectionManager
from app.models.notification import Notification
from app.models.user import User


class _SessionFactory:
    def __init__(self, session):
        self._session = session

    def __call__(self):
        return self

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeWebSocket:
    def __init__(self) -> None:
        self.accepted = False
        self.sent: list[str] = []
        self.user_id: str | None = None

    async def accept(self):
        self.accepted = True

    async def send_text(self, payload: str):
        self.sent.append(payload)


class _FakeRedis:
    def __init__(self, items: list[str] | None = None) -> None:
        self._queue = list(items or [])
        self._presence: dict[str, str] = {}

    async def setex(self, key: str, _: int, value: str):
        self._presence[key] = value

    async def lpop(self, key: str):
        if not self._queue:
            return None
        return self._queue.pop(0)

    async def lpush(self, key: str, value: str):
        self._queue.insert(0, value)


@pytest.mark.asyncio
async def test_offline_websocket_message_creates_notification(db_session, monkeypatch):
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.commit()

    updates: list[tuple[str, dict]] = []

    async def _enqueue(self, user_id_value, payload):
        updates.append((str(user_id_value), payload))

    monkeypatch.setattr(
        "app.core.websocket.AsyncSessionLocal",
        _SessionFactory(db_session),
    )
    monkeypatch.setattr(
        "app.core.websocket.SystemUpdateService.enqueue",
        _enqueue,
    )

    manager = ConnectionManager()
    await manager._trigger_offline_push(
        str(user_id),
        {
            "type": "chat_message",
            "sender_name": "Sparkle",
            "content": "你有一条新的计划建议",
        },
    )

    result = await db_session.execute(
        select(Notification).where(Notification.user_id == user_id)
    )
    notifications = result.scalars().all()

    assert len(notifications) == 1
    assert notifications[0].title == "Sparkle 发来新消息"
    assert notifications[0].content == "你有一条新的计划建议"
    assert updates[-1][0] == str(user_id)
    assert updates[-1][1]["category"] == "notification"


@pytest.mark.asyncio
async def test_connect_user_replays_offline_queue_messages():
    manager = ConnectionManager()
    manager.redis = _FakeRedis(
        [
            '{"user_id":"u1","message_id":"m1","message":{"type":"notification","content":"hello"}}',
            '{"user_id":"u1","message_id":"m2","message":{"type":"notification","content":"world"}}',
        ]
    )
    websocket = _FakeWebSocket()

    await manager.connect_user(websocket, "u1")

    assert websocket.accepted is True
    assert len(websocket.sent) == 2
    assert '"content": "hello"' in websocket.sent[0]
    assert '"content": "world"' in websocket.sent[1]
