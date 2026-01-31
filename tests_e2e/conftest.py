"""
E2E Test Configuration and Shared Fixtures
==========================================

Provides test infrastructure for end-to-end testing across Flutter → Go → Python → DB
"""
import asyncio
import os
import pytest
import pytest_asyncio
import json
from datetime import datetime, timedelta
from typing import AsyncGenerator, Dict, Any, Generator
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

# Add backend to path
import sys
from pathlib import Path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

# Try to import with fallbacks
try:
    # Prefer the real model Base used by the app
    from app.db.session import Base
except ImportError:
    # Fallback for older layouts
    try:
        from app.db.base import Base
    except ImportError:
        # Create a simple Base if not available
        from sqlalchemy.ext.declarative import declarative_base
        Base = declarative_base()

try:
    from app.models.user import User
    from app.models.plan import Plan, PlanType
    from app.models.task import Task, TaskStatus, TaskType
    from app.models.chat import ChatMessage, ChatSession
    from app.config import settings
except ImportError as e:
    # If models aren't available, we'll define placeholders
    print(f"Warning: Could not import models: {e}")

    # Define placeholder models for testing
    from sqlalchemy import Column, String, DateTime, Integer, Float, Boolean, ForeignKey, Text
    from sqlalchemy.orm import relationship
    import uuid
    from datetime import datetime

    class User(Base):
        __tablename__ = "users"
        id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
        username = Column(String, unique=True, nullable=False)
        email = Column(String, unique=True, nullable=False)
        hashed_password = Column(String)
        is_active = Column(Boolean, default=True)

    class PlanType:
        SPRINT = "sprint"
        MARATHON = "marathon"

    class Plan(Base):
        __tablename__ = "plans"
        id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
        user_id = Column(String, ForeignKey("users.id"))
        name = Column(String)
        type = Column(String)
        subject = Column(String)
        description = Column(Text)
        target_date = Column(DateTime)
        is_active = Column(Boolean, default=True)
        progress = Column(Float, default=0.0)

    class TaskStatus:
        PENDING = "pending"
        IN_PROGRESS = "in_progress"
        COMPLETED = "completed"
        CANCELLED = "cancelled"

    class TaskType:
        LEARNING = "learning"
        TRAINING = "training"
        REVIEW = "review"
        PRACTICE = "practice"

    class Task(Base):
        __tablename__ = "tasks"
        id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
        user_id = Column(String, ForeignKey("users.id"))
        plan_id = Column(String, ForeignKey("plans.id"))
        title = Column(String)
        type = Column(String)
        description = Column(Text)
        status = Column(String, default=TaskStatus.PENDING)
        estimated_minutes = Column(Integer)
        difficulty = Column(Integer)
        order = Column(Integer)
        priority = Column(String)

    class MessageRole:
        USER = "user"
        ASSISTANT = "assistant"
        SYSTEM = "system"

    class ChatMessage(Base):
        __tablename__ = "chat_messages"
        id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
        session_id = Column(String, ForeignKey("chat_sessions.id"))
        user_id = Column(String, ForeignKey("users.id"))
        role = Column(String)
        content = Column(Text)
        timestamp = Column(DateTime, default=datetime.utcnow)

    class ChatSession(Base):
        __tablename__ = "chat_sessions"
        id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
        user_id = Column(String, ForeignKey("users.id"))
        title = Column(String)
        is_active = Column(Boolean, default=True)
        created_at = Column(DateTime, default=datetime.utcnow)


# =============================================================================
# Test Database Configuration
# =============================================================================

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    # Use the same database as production
    "postgresql+asyncpg://postgres:change-me@localhost:5432/sparkle"
)

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine(event_loop):
    """Create test database engine - uses existing schema"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a simple test database session."""
    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    session = async_session_maker()
    try:
        yield session
    finally:
        await session.close()


# =============================================================================
# Mock Services
# =============================================================================

@pytest.fixture
def mock_llm_service():
    """Mock LLM service for testing"""
    class MockLLMResponse:
        def __init__(self, content: str, tool_calls: list = None):
            self.content = content
            self.tool_calls = tool_calls or []

        async def chunks(self):
            """Yield streaming chunks"""
            words = self.content.split()
            for i, word in enumerate(words):
                is_last = i == len(words) - 1
                yield {
                    "delta": word + (" " if not is_last else ""),
                    "finish_reason": None if not is_last else "stop"
                }

    class MockLLMService:
        def __init__(self):
            self.next_stream_response = None

        async def chat_stream(self, messages, **kwargs):
            """Mock streaming chat"""
            response_content = "This is a mocked LLM response for testing."
            return MockLLMResponse(response_content)

        async def chat_stream_with_tools(
            self,
            system_prompt: str,
            user_message: str,
            tools: list[dict[str, Any]],
            user_context: dict[str, Any] | None = None,
            temperature: float = 0.7,
        ):
            """Mock streamed tool-aware chat by yielding StreamChunk text."""
            from app.services.llm_service import StreamChunk
            if self.next_stream_response is not None:
                response_content = self.next_stream_response
                self.next_stream_response = None
            elif "翻译" in user_message or "Hello" in user_message:
                response_content = "你好，世界"
            elif "计划" in user_message and ("创建" in user_message or "制定" in user_message):
                response_content = "请问你想学习什么科目？"
            elif "难" in user_message:
                response_content = "Python不难，循序渐进就好。"
            else:
                response_content = "This is a mocked tool-aware response."
            for word in response_content.split():
                yield StreamChunk(type="text", content=word + " ")
            yield StreamChunk(type="text", content="")

        async def chat_json(self, messages, **kwargs):
            """Mock JSON response"""
            return {
                "reasoning": "Mock reasoning",
                "tasks": [
                    {
                        "title": "Mock Task 1",
                        "type": "learning",
                        "estimated_minutes": 30,
                        "difficulty": 3
                    }
                ]
            }

    return MockLLMService()


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing"""
    class MockRedis:
        def __init__(self):
            self._data = {}
            self._expired = {}

        async def get(self, key: str):
            if key in self._expired and datetime.now() > self._expired[key]:
                del self._data[key]
                del self._expired[key]
                return None
            return self._data.get(key)

        async def set(self, key: str, value: Any, ex: int = None, nx: bool = False, px: int | None = None):
            if nx and key in self._data:
                return False
            self._data[key] = value
            if ex:
                self._expired[key] = datetime.now() + timedelta(seconds=ex)
            elif px:
                self._expired[key] = datetime.now() + timedelta(milliseconds=px)
            return True

        async def delete(self, *keys):
            for key in keys:
                self._data.pop(key, None)
                self._expired.pop(key, None)
            return len(keys)

        async def exists(self, key: str):
            return key in self._data

        async def expire(self, key: str, seconds: int):
            if key in self._data:
                self._expired[key] = datetime.now() + timedelta(seconds=seconds)
            return True

        async def setex(self, key: str, seconds: int, value: Any):
            return await self.set(key, value, ex=seconds)

        async def eval(self, script: str, numkeys: int, *keys_and_args):
            """Mock Lua script execution for lock release pattern."""
            # Parse keys and args
            keys = list(keys_and_args[:numkeys])
            args = list(keys_and_args[numkeys:])

            # Handle lock release pattern: if get(key) == value then del(key)
            if "get" in script and "del" in script and len(keys) >= 1:
                key = keys[0]
                expected_value = args[0] if args else None
                current_value = self._data.get(key)

                if current_value == expected_value:
                    self._data.pop(key, None)
                    return 1
                return 0

            return 1

        async def lrange(self, key: str, start: int, end: int):
            data = self._data.get(key, [])
            if not isinstance(data, list):
                return []
            if end == -1:
                return data[start:]
            return data[start:end + 1]

        async def rpush(self, key: str, *values):
            if key not in self._data or not isinstance(self._data[key], list):
                self._data[key] = []
            self._data[key].extend(values)
            return len(self._data[key])

        async def llen(self, key: str):
            data = self._data.get(key, [])
            return len(data) if isinstance(data, list) else 0

        async def ltrim(self, key: str, start: int, end: int):
            data = self._data.get(key, [])
            if isinstance(data, list):
                self._data[key] = data[start:end + 1]
            return True

        async def sadd(self, key: str, *values):
            if key not in self._data or not isinstance(self._data[key], set):
                self._data[key] = set()
            before = len(self._data[key])
            self._data[key].update(values)
            return len(self._data[key]) - before

        async def smembers(self, key: str):
            data = self._data.get(key, set())
            return data if isinstance(data, set) else set()

        async def zadd(self, key: str, mapping: Dict[Any, float]):
            if key not in self._data or not isinstance(self._data[key], dict):
                self._data[key] = {}
            self._data[key].update(mapping)
            return len(mapping)

        async def zrange(self, key: str, start: int, end: int, withscores: bool = False):
            data = self._data.get(key, {})
            if not isinstance(data, dict):
                return []
            items = sorted(data.items(), key=lambda x: x[1])
            sliced = items[start:] if end == -1 else items[start:end + 1]
            return sliced if withscores else [item[0] for item in sliced]

        async def keys(self, pattern: str = "*"):
            return [k for k in self._data.keys() if pattern == "*" or pattern.replace("*", "") in k]

        async def expire(self, key: str, seconds: int):
            if key in self._data:
                self._expired[key] = datetime.now() + timedelta(seconds=seconds)
            return True

        async def hset(self, key: str, field: str = None, value=None, mapping: dict = None):
            if key not in self._data or not isinstance(self._data[key], dict):
                self._data[key] = {}
            if mapping:
                self._data[key].update(mapping)
            elif field:
                self._data[key][field] = value
            return 1

        async def hget(self, key: str, field: str):
            data = self._data.get(key, {})
            if isinstance(data, dict):
                return data.get(field)
            return None

        async def hgetall(self, key: str):
            data = self._data.get(key, {})
            return data if isinstance(data, dict) else {}

        async def hdel(self, key: str, *fields):
            data = self._data.get(key, {})
            if isinstance(data, dict):
                for field in fields:
                    data.pop(field, None)
            return len(fields)

        async def flushdb(self):
            self._data.clear()
            self._expired.clear()
            return True

        # Pub/Sub methods
        async def publish(self, channel: str, message: Any):
            # Mock publish - just store
            pub_key = f"pubsub:{channel}"
            if pub_key not in self._data:
                self._data[pub_key] = []
            self._data[pub_key].append({
                "message": message,
                "timestamp": datetime.now().isoformat()
            })
            return 1

        async def subscribe(self, channel: str):
            # Mock subscribe - return a mock pubsub object
            class MockPubSub:
                def __init__(self, redis_mock, channel):
                    self.redis = redis_mock
                    self.channel = channel

                async def get_message(self, timeout=0):
                    pub_key = f"pubsub:{self.channel}"
                    if pub_key in self.redis._data and self.redis._data[pub_key]:
                        return self.redis._data[pub_key].pop(0)
                    return None

            return MockPubSub(self, channel)

        def pipeline(self):
            class MockPipeline:
                def __init__(self, redis_mock):
                    self.redis = redis_mock
                    self._ops = []

                def set(self, *args, **kwargs):
                    self._ops.append(("set", args, kwargs))
                    return self

                def get(self, *args, **kwargs):
                    self._ops.append(("get", args, kwargs))
                    return self

                def lrange(self, *args, **kwargs):
                    self._ops.append(("lrange", args, kwargs))
                    return self

                def ltrim(self, *args, **kwargs):
                    self._ops.append(("ltrim", args, kwargs))
                    return self

                async def execute(self):
                    results = []
                    for op, args, kwargs in self._ops:
                        if op == "set":
                            results.append(await self.redis.set(*args, **kwargs))
                        elif op == "get":
                            results.append(await self.redis.get(*args, **kwargs))
                        elif op == "lrange":
                            results.append(await self.redis.lrange(*args, **kwargs))
                        elif op == "ltrim":
                            results.append(await self.redis.ltrim(*args, **kwargs))
                    self._ops.clear()
                    return results

            return MockPipeline(self)

    return MockRedis()


@pytest.fixture
def mock_websocket_client():
    """Mock WebSocket client for testing"""
    class MockWebSocketClient:
        def __init__(self):
            self.connected = False
            self.messages_sent = []
            self.messages_received = []
            self.disconnect_handlers = []

        async def connect(self, url: str, headers: dict = None):
            self.connected = True
            return True

        async def send(self, message: dict):
            self.messages_sent.append(message)
            return True

        async def receive(self) -> dict:
            if self.messages_received:
                return self.messages_received.pop(0)
            # Wait for message (mock)
            await asyncio.sleep(0.1)
            return None

        async def disconnect(self):
            self.connected = False
            for handler in self.disconnect_handlers:
                await handler()
            return True

        def on_disconnect(self, handler):
            self.disconnect_handlers.append(handler)

        # Helper for testing
        def mock_server_response(self, message: dict):
            """Simulate server pushing a message"""
            self.messages_received.append(message)

    return MockWebSocketClient()


# =============================================================================
# Test Data Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user"""
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"testuser_{user_id.hex[:8]}",
        email=f"test_{user_id.hex[:8]}@example.com",
        hashed_password="hashed_password",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()  # Use flush instead of commit for test isolation
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_chat_session(db_session: AsyncSession, test_user: User) -> ChatSession:
    """Create a test chat session"""
    session = ChatSession(
        id=uuid4(),
        user_id=test_user.id,
        title="Test Chat Session",
        is_active=True,
    )
    db_session.add(session)
    await db_session.flush()
    await db_session.refresh(session)
    return session


@pytest.fixture
def sample_plan_data() -> Dict[str, Any]:
    """Sample plan data for testing"""
    return {
        "name": "Python学习计划",
        "type": PlanType.SPRINT,
        "subject": "编程",
        "description": "学习Python基础",
        "target_date": (datetime.now() + timedelta(days=7)).isoformat(),
        "goals": ["掌握Python基础语法", "能够编写简单程序"],
    }


@pytest.fixture
def sample_task_data() -> Dict[str, Any]:
    """Sample task data for testing"""
    return {
        "title": "学习Python变量",
        "type": TaskType.LEARNING,
        "description": "学习Python变量的定义和使用",
        "estimated_minutes": 30,
        "difficulty": 3,
        "priority": "high",
    }


@pytest_asyncio.fixture
async def test_plan_with_tasks(
    db_session: AsyncSession,
    test_user: User,
    sample_plan_data: Dict[str, Any],
    sample_task_data: Dict[str, Any],
) -> Plan:
    """Create a test plan with associated tasks"""
    # Create plan
    plan = Plan(
        id=uuid4(),
        user_id=test_user.id,
        name=sample_plan_data["name"],
        type=sample_plan_data["type"],
        subject=sample_plan_data["subject"],
        description=sample_plan_data["description"],
        target_date=datetime.fromisoformat(sample_plan_data["target_date"]),
        is_active=True,
        progress=0.0,
    )
    db_session.add(plan)

    # Create tasks
    for i in range(5):
        task = Task(
            id=uuid4(),
            user_id=test_user.id,
            plan_id=plan.id,
            title=f"{sample_task_data['title']} {i+1}",
            type=sample_task_data["type"],
            description=sample_task_data["description"],
            estimated_minutes=sample_task_data["estimated_minutes"],
            difficulty=sample_task_data["difficulty"],
            status=TaskStatus.PENDING,
            order=i,
        )
        db_session.add(task)

    await db_session.flush()
    await db_session.refresh(plan)
    return plan


# =============================================================================
# Test Helpers
# =============================================================================

@pytest.fixture
def test_assertions():
    """Custom assertion helpers for E2E tests"""
    class Assertions:
        @staticmethod
        def assert_message_flow(messages: list, expected_count: int):
            """Assert message flow is complete"""
            assert len(messages) == expected_count, f"Expected {expected_count} messages, got {len(messages)}"

        @staticmethod
        def assert_plan_created(plan: Plan, expected_attributes: dict):
            """Assert plan was created correctly"""
            for key, value in expected_attributes.items():
                assert getattr(plan, key) == value, f"Plan {key} mismatch: {getattr(plan, key)} != {value}"

        @staticmethod
        def assert_task_progress(tasks: list, expected_completed: int):
            """Assert task progress is correct"""
            completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
            assert completed == expected_completed, f"Expected {expected_completed} completed tasks, got {completed}"

        @staticmethod
        def assert_websocket_connected(client):
            """Assert WebSocket is connected"""
            assert client.connected, "WebSocket client should be connected"

        @staticmethod
        def assert_response_contains(response: dict, expected_fields: list):
            """Assert response contains expected fields"""
            for field in expected_fields:
                assert field in response, f"Response missing field: {field}"

    return Assertions()


@pytest_asyncio.fixture
async def test_scenario_runner():
    """Helper to run complex test scenarios"""
    class ScenarioRunner:
        def __init__(self):
            self.steps = []
            self.context = {}

        def add_step(self, name: str, fn):
            """Add a step to the scenario"""
            self.steps.append((name, fn))
            return self

        async def run(self):
            """Run all steps in sequence"""
            results = []
            for name, fn in self.steps:
                try:
                    result = await fn(**self.context)
                    results.append((name, "PASS", result))
                except Exception as e:
                    results.append((name, "FAIL", str(e)))
                    raise
            return results

        def set_context(self, key: str, value: Any):
            """Set context value for next steps"""
            self.context[key] = value

    return ScenarioRunner()


# =============================================================================
# Integration Markers
# =============================================================================

def pytest_configure(config):
    """Configure custom pytest markers"""
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "websocket: mark test as WebSocket test"
    )


@pytest.fixture
def skip_integration():
    """Skip integration tests if flag not set"""
    return not os.getenv("SPARKLE_INTEGRATION", "").lower() in {"1", "true", "yes"}
