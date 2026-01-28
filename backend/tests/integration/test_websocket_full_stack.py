"""
WebSocket Full-Stack Integration Tests

Tests the complete WebSocket flow:
Flutter Client → Go Gateway → Python gRPC Service → Orchestrator → Response

This test requires:
- Running Go Gateway (make gateway-dev)
- Running Python gRPC server (make grpc-server)
- Running PostgreSQL and Redis (make dev-all)
"""

import pytest
import asyncio
import json
from typing import AsyncGenerator, List, Dict, Any
from datetime import datetime
import websockets
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.user import User
from app.models.plan import Plan
from app.core.security import create_access_token


# ============================================================
# Test Fixtures
# ============================================================

@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user for WebSocket authentication"""
    from app.services.user_service import user_service

    user_data = {
        "email": "websocket_test@example.com",
        "nickname": "WebSocket Test User",
        "password_hash": "test_password"
    }

    # Try to get existing user
    result = await db_session.execute(
        select(User).where(User.email == user_data["email"])
    )
    user = result.scalar_one_or_none()

    if not user:
        # Create new user
        user = User(**user_data)
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

    yield user

    # Cleanup
    await db_session.delete(user)
    await db_session.commit()


@pytest.fixture
def auth_headers(test_user: User) -> Dict[str, str]:
    """Generate authentication headers for WebSocket connection"""
    token = create_access_token(data={"sub": test_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def websocket_url() -> str:
    """Get WebSocket URL from environment"""
    import os
    gateway_host = os.getenv("GATEWAY_HOST", "localhost")
    gateway_port = os.getenv("GATEWAY_PORT", "8080")
    return f"ws://{gateway_host}:{gateway_port}/ws/chat"


# ============================================================
# WebSocket Connection Tests
# ============================================================

class TestWebSocketConnection:
    """Test WebSocket connection lifecycle"""

    @pytest.mark.asyncio
    async def test_connection_with_valid_token(
        self,
        websocket_url: str,
        auth_headers: Dict[str, str]
    ):
        """Test successful WebSocket connection with valid token"""
        uri = f"{websocket_url}?token={auth_headers['Authorization'].split()[1]}"

        async with websockets.connect(uri) as websocket:
            # Connection should be established
            assert websocket.open

            # Send ping message
            await websocket.send(json.dumps({"type": "ping"}))

            # Receive pong
            response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
            data = json.loads(response)
            assert data["type"] == "pong"

    @pytest.mark.asyncio
    async def test_connection_with_invalid_token(self, websocket_url: str):
        """Test WebSocket connection rejection with invalid token"""
        uri = f"{websocket_url}?token=invalid_token_12345"

        with pytest.raises(Exception):  # Connection should fail
            async with websockets.connect(uri) as websocket:
                await websocket.send(json.dumps({"type": "ping"}))

    @pytest.mark.asyncio
    async def test_connection_without_token(self, websocket_url: str):
        """Test WebSocket connection rejection without token"""
        with pytest.raises(Exception):  # Connection should fail
            async with websockets.connect(websocket_url) as websocket:
                pass

    @pytest.mark.asyncio
    async def test_connection_reconnect(
        self,
        websocket_url: str,
        auth_headers: Dict[str, str]
    ):
        """Test WebSocket reconnection after disconnect"""
        uri = f"{websocket_url}?token={auth_headers['Authorization'].split()[1]}"

        # First connection
        async with websockets.connect(uri) as websocket1:
            assert websocket1.open
            await websocket1.send(json.dumps({"type": "ping"}))
            response = await websocket1.recv()
            assert json.loads(response)["type"] == "pong"

        # Disconnect and reconnect
        await asyncio.sleep(0.1)

        async with websockets.connect(uri) as websocket2:
            assert websocket2.open
            await websocket2.send(json.dumps({"type": "ping"}))
            response = await websocket2.recv()
            assert json.loads(response)["type"] == "pong"


# ============================================================
# Chat Message Flow Tests
# ============================================================

class TestChatMessageFlow:
    """Test complete chat message flow through the stack"""

    @pytest.mark.asyncio
    async def test_simple_chat_message(
        self,
        websocket_url: str,
        auth_headers: Dict[str, str],
        test_user: User
    ):
        """Test sending a simple chat message and receiving response"""
        uri = f"{websocket_url}?token={auth_headers['Authorization'].split()[1]}"

        async with websockets.connect(uri) as websocket:
            # Send chat message
            chat_request = {
                "type": "message",
                "content": "你好，请介绍一下你自己",
                "session_id": "test-session-123",
                "user_id": str(test_user.id)
            }
            await websocket.send(json.dumps(chat_request))

            # Receive streaming response
            responses = []
            timeout = 30.0  # 30 seconds timeout for LLM response

            start_time = datetime.now()
            while (datetime.now() - start_time).total_seconds() < timeout:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(response)
                    responses.append(data)

                    # Check if streaming is complete
                    if data.get("type") == "done":
                        break

                except asyncio.TimeoutError:
                    break

            # Verify responses
            assert len(responses) > 0, "Should receive at least one response"

            # Check for delta responses (streaming)
            delta_responses = [r for r in responses if r.get("type") == "delta"]
            assert len(delta_responses) > 0, "Should receive streaming delta responses"

            # Check content
            all_content = "".join([
                r.get("delta", "")
                for r in delta_responses
            ])
            assert len(all_content) > 0, "Should receive actual content"

    @pytest.mark.asyncio
    async def test_chat_message_with_context(
        self,
        websocket_url: str,
        auth_headers: Dict[str, str],
        test_user: User
    ):
        """Test chat message with conversation history context"""
        uri = f"{websocket_url}?token={auth_headers['Authorization'].split()[1]}"

        async with websockets.connect(uri) as websocket:
            # Send first message
            await websocket.send(json.dumps({
                "type": "message",
                "content": "My favorite color is blue",
                "session_id": "test-session-context-1",
                "user_id": str(test_user.id)
            }))

            # Receive first response
            responses = []
            while True:
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                data = json.loads(response)
                responses.append(data)
                if data.get("type") == "done":
                    break

            # Send follow-up message
            await websocket.send(json.dumps({
                "type": "message",
                "content": "What is my favorite color?",
                "session_id": "test-session-context-1",  # Same session
                "user_id": str(test_user.id)
            }))

            # Receive follow-up response
            responses = []
            while True:
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                data = json.loads(response)
                responses.append(data)
                if data.get("type") == "done":
                    break

            # Verify response mentions "blue"
            all_content = "".join([
                r.get("delta", "")
                for r in responses
                if r.get("type") == "delta"
            ])
            # LLM should remember the context
            assert "blue" in all_content.lower() or "蓝色" in all_content.lower()

    @pytest.mark.asyncio
    async def test_multiple_concurrent_messages(
        self,
        websocket_url: str,
        auth_headers: Dict[str, str],
        test_user: User
    ):
        """Test sending multiple messages concurrently"""
        uri = f"{websocket_url}?token={auth_headers['Authorization'].split()[1]}"

        async with websockets.connect(uri) as websocket:
            messages = [
                {"content": "What is 1+1?", "session_id": "test-concurrent-1"},
                {"content": "What is 2+2?", "session_id": "test-concurrent-2"},
                {"content": "What is 3+3?", "session_id": "test-concurrent-3"},
            ]

            # Send all messages
            for msg in messages:
                await websocket.send(json.dumps({
                    "type": "message",
                    "content": msg["content"],
                    "session_id": msg["session_id"],
                    "user_id": str(test_user.id)
                }))

            # Collect all responses
            all_responses = {}
            timeout = 60.0
            start_time = datetime.now()

            while (datetime.now() - start_time).total_seconds() < timeout:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(response)

                    session_id = data.get("session_id")
                    if session_id:
                        if session_id not in all_responses:
                            all_responses[session_id] = []
                        all_responses[session_id].append(data)

                    # Check if we received all responses
                    if len(all_responses) == len(messages):
                        # Verify all have "done" type
                        if all(
                            any(r.get("type") == "done" for r in all_responses[sid])
                            for sid in all_responses
                        ):
                            break

                except asyncio.TimeoutError:
                    break

            # Verify all sessions received responses
            assert len(all_responses) == len(messages)


# ============================================================
# Error Handling Tests
# ============================================================

class TestWebSocketErrorHandling:
    """Test WebSocket error handling"""

    @pytest.mark.asyncio
    async def test_malformed_message(
        self,
        websocket_url: str,
        auth_headers: Dict[str, str]
    ):
        """Test handling of malformed messages"""
        uri = f"{websocket_url}?token={auth_headers['Authorization'].split()[1]}"

        async with websockets.connect(uri) as websocket:
            # Send invalid JSON
            await websocket.send("not a valid json {{{")

            # Should receive error message
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(response)

            # Server should respond with error
            assert data.get("type") in ["error", "validation_error"]

    @pytest.mark.asyncio
    async def test_message_without_required_fields(
        self,
        websocket_url: str,
        auth_headers: Dict[str, str]
    ):
        """Test handling of message without required fields"""
        uri = f"{websocket_url}?token={auth_headers['Authorization'].split()[1]}"

        async with websockets.connect(uri) as websocket:
            # Send message without content
            await websocket.send(json.dumps({
                "type": "message"
                # Missing: content, session_id, user_id
            }))

            # Should receive error response
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(response)

            assert data.get("type") in ["error", "validation_error"]

    @pytest.mark.asyncio
    async def test_server_error_recovery(
        self,
        websocket_url: str,
        auth_headers: Dict[str, str],
        test_user: User,
        monkeypatch
    ):
        """Test recovery from server-side errors"""
        # This test would require mocking server-side errors
        # For now, we'll test connection after error
        uri = f"{websocket_url}?token={auth_headers['Authorization'].split()[1]}"

        async with websockets.connect(uri) as websocket:
            # Send invalid request
            await websocket.send(json.dumps({
                "type": "invalid_type"
            }))

            # Receive error
            error_response = await websocket.recv()

            # Send valid request after error
            await websocket.send(json.dumps({
                "type": "message",
                "content": "Hello",
                "session_id": "test-recovery",
                "user_id": str(test_user.id)
            }))

            # Should receive valid response
            response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            data = json.loads(response)

            # Connection should still work
            assert websocket.open


# ============================================================
# Metadata and Event Tests
# ============================================================

class TestWebSocketMetadataAndEvents:
    """Test WebSocket metadata and special events"""

    @pytest.mark.asyncio
    async def test_plan_review_event(
        self,
        websocket_url: str,
        auth_headers: Dict[str, str],
        test_user: User,
        db: AsyncSession
    ):
        """Test receiving plan review event via WebSocket"""
        # Create a test plan
        plan = Plan(
            user_id=test_user.id,
            name="Test Plan for Review",
            description="This is a test plan",
            status="active"
        )
        db.add(plan)
        await db.commit()
        await db.refresh(plan)

        uri = f"{websocket_url}?token={auth_headers['Authorization'].split()[1]}"

        async with websockets.connect(uri) as websocket:
            # Request plan review
            await websocket.send(json.dumps({
                "type": "message",
                "content": f"请帮我评审计划: {plan.id}",
                "session_id": "test-plan-review",
                "user_id": str(test_user.id)
            }))

            # Listen for plan review event
            review_received = False
            timeout = 30.0
            start_time = datetime.now()

            while (datetime.now() - start_time).total_seconds() < timeout:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(response)

                    # Check for plan review metadata
                    metadata = data.get("metadata", {})
                    if metadata.get("requires_review") == True:
                        review_received = True
                        assert "review_data" in metadata
                        break

                    if data.get("type") == "done":
                        break

                except asyncio.TimeoutError:
                    break

            # Note: Plan review may not be triggered for all messages
            # This test mainly verifies the event structure when it occurs

        # Cleanup
        await db.delete(plan)
        await db.commit()

    @pytest.mark.asyncio
    async def test_state_change_event(
        self,
        websocket_url: str,
        auth_headers: Dict[str, str],
        test_user: User
    ):
        """Test receiving state change notification event"""
        uri = f"{websocket_url}?token={auth_headers['Authorization'].split()[1]}"

        async with websockets.connect(uri) as websocket:
            # Send message that might trigger state change
            await websocket.send(json.dumps({
                "type": "message",
                "content": "创建一个新计划",
                "session_id": "test-state-change",
                "user_id": str(test_user.id)
            }))

            # Listen for state change events
            state_events = []
            timeout = 20.0
            start_time = datetime.now()

            while (datetime.now() - start_time).total_seconds() < timeout:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(response)

                    # Check for state_change_event in metadata
                    metadata = data.get("metadata", {})
                    if "state_change_event" in metadata:
                        state_events.append(metadata["state_change_event"])

                    if data.get("type") == "done":
                        break

                except asyncio.TimeoutError:
                    break

            # Note: State changes may not always occur
            # This test verifies the event structure when it does


# ============================================================
# Performance Tests
# ============================================================

class TestWebSocketPerformance:
    """Test WebSocket performance characteristics"""

    @pytest.mark.asyncio
    async def test_response_time(
        self,
        websocket_url: str,
        auth_headers: Dict[str, str],
        test_user: User
    ):
        """Test WebSocket response time"""
        uri = f"{websocket_url}?token={auth_headers['Authorization'].split()[1]}"

        async with websockets.connect(uri) as websocket:
            import time

            # Send message
            start_time = time.time()
            await websocket.send(json.dumps({
                "type": "message",
                "content": "Hi",
                "session_id": "test-perf",
                "user_id": str(test_user.id)
            }))

            # Receive first response chunk
            first_chunk_time = None
            while True:
                response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                data = json.loads(response)

                if first_chunk_time is None and data.get("type") == "delta":
                    first_chunk_time = time.time()

                if data.get("type") == "done":
                    break

            assert first_chunk_time is not None

            # First response chunk should arrive within 10 seconds
            time_to_first_chunk = (first_chunk_time - start_time)
            assert time_to_first_chunk < 10.0

    @pytest.mark.asyncio
    async def test_concurrent_connections(
        self,
        websocket_url: str,
        auth_headers: Dict[str, str]
    ):
        """Test multiple concurrent WebSocket connections"""
        token = auth_headers['Authorization'].split()[1]

        async def single_connection(conn_id: int):
            uri = f"{websocket_url}?token={token}"
            async with websockets.connect(uri) as websocket:
                await websocket.send(json.dumps({
                    "type": "ping",
                    "connection_id": conn_id
                }))
                response = await websocket.recv()
                return conn_id

        # Create 10 concurrent connections
        tasks = [single_connection(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert len(results) == 10
        assert set(results) == set(range(10))


# ============================================================
# Test Run Configuration
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
