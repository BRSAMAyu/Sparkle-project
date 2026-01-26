"""
WebSocket 测试客户端
测试 Go Gateway → Python gRPC → LLM 的完整链路
"""
import asyncio
import json
import os
import time
from jose import jwt as jose_jwt
from pathlib import Path
import websockets
from loguru import logger


def _load_jwt_secret() -> str:
    env_secret = os.getenv("JWT_SECRET")
    if env_secret:
        return env_secret
    for path in (Path(__file__).resolve().parents[1] / ".env", Path(__file__).resolve().parent / "gateway" / ".env"):
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.startswith("JWT_SECRET="):
                    return line.split("=", 1)[1].strip()
    return "dev-secret-key"


JWT_SECRET = _load_jwt_secret()


def _create_jwt(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": int(time.time()) + 3600,
        "type": "access",  # Required by validateJWT in gateway
    }
    return jose_jwt.encode(payload, JWT_SECRET, algorithm="HS256")

DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"


async def test_websocket_chat():
    """
    测试 WebSocket 流式对话
    """
    user_id = DEFAULT_USER_ID
    token = _create_jwt(user_id)
    uri = f"ws://localhost:8080/ws/chat?user_id={user_id}&token={token}"

    headers = {"Authorization": f"Bearer {token}"}
    logger.info(f"🔌 Connecting to WebSocket: {uri}")

    try:
        async with websockets.connect(uri, additional_headers=headers) as websocket:
            logger.success("✅ WebSocket connected!")

            # 发送测试消息
            test_message = {
                "message": "帮我制定高数复习计划",  # DEMO_MODE 关键词
                "session_id": "test_session_001",
                "nickname": "测试同学"
            }

            logger.info(f"📤 Sending message: {test_message['message']}")
            await websocket.send(json.dumps(test_message))

            # 接收流式响应
            logger.info("\n" + "=" * 70)
            logger.info("🤖 AI Response Stream:")
            logger.info("=" * 70)

            response_count = 0
            full_text = ""

            while True:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    response_count += 1

                    data = json.loads(response)
                    response_type = data.get("type")

                    if response_type == "delta":
                        # 流式文本
                        delta = data.get("delta", "")
                        print(delta, end="", flush=True)
                        full_text += delta

                    elif response_type == "status_update":
                        # 状态更新
                        status = data.get("status", {})
                        state = status.get("state", "UNKNOWN")
                        details = status.get("details", "")
                        logger.info(f"\n📍 [{state}] {details}")

                    elif response_type == "full_text":
                        # 完整文本
                        full_text = data.get("full_text", "")
                        logger.info(f"\n✅ Received full_text: {len(full_text)} chars")

                    elif response_type == "error":
                        # 错误
                        error = data.get("error", {})
                        logger.error(f"\n❌ Error: {error}")
                        break

                    elif response_type == "usage":
                        # Token 使用统计
                        usage = data.get("usage", {})
                        logger.info(f"\n📊 Usage: {usage}")

                    # 检查是否结束
                    if data.get("finish_reason") and data.get("finish_reason") != "NULL":
                        logger.info(f"\n🏁 Finish reason: {data['finish_reason']}")
                        break

                except asyncio.TimeoutError:
                    logger.warning("\n⏱️  Response timeout - stream may have ended")
                    break
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("\n🔌 Connection closed by server")
                    break

            print("\n" + "=" * 70)
            logger.success("✅ Test completed successfully!")
            logger.info(f"📊 Statistics:")
            logger.info(f"   - Response chunks: {response_count}")
            logger.info(f"   - Total characters: {len(full_text)}")

            return True

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False


async def test_multiple_messages():
    """
    测试多轮对话
    """
    user_id = DEFAULT_USER_ID
    token = _create_jwt(user_id)
    uri = f"ws://localhost:8080/ws/chat?user_id={user_id}&token={token}"

    headers = {"Authorization": f"Bearer {token}"}
    logger.info(f"🔌 Testing multiple messages...")

    async with websockets.connect(uri, additional_headers=headers) as websocket:
        messages = [
            "帮我制定高数复习计划",
            "什么是微积分？",
            "推荐一本好书"
        ]

        for i, msg in enumerate(messages, 1):
            logger.info(f"\n📤 Message {i}/{len(messages)}: {msg}")

            await websocket.send(json.dumps({
                "message": msg,
                "session_id": "multi_test_session",
                "nickname": "测试同学"
            }))

            # 接收这条消息的所有响应
            while True:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(response)

                    if data.get("type") == "delta":
                        print(data.get("delta", ""), end="", flush=True)

                    if data.get("finish_reason") and data.get("finish_reason") != "NULL":
                        print()  # 换行
                        break

                except asyncio.TimeoutError:
                    break

        logger.success("\n✅ Multiple messages test completed!")


async def main():
    """
    运行所有测试
    """
    logger.info("🧪 Starting WebSocket Integration Tests\n")

    # 测试1: 单条消息
    logger.info("=" * 70)
    logger.info("Test 1: Single Message Stream")
    logger.info("=" * 70)
    success1 = await test_websocket_chat()

    await asyncio.sleep(1)

    # 测试2: 多轮对话
    logger.info("\n" + "=" * 70)
    logger.info("Test 2: Multiple Messages")
    logger.info("=" * 70)
    try:
        await test_multiple_messages()
        success2 = True
    except Exception as e:
        logger.error(f"Multiple messages test failed: {e}")
        success2 = False

    # 汇总结果
    logger.info("\n" + "=" * 70)
    logger.info("🎯 Test Summary:")
    logger.info("=" * 70)
    logger.info(f"  Single Message: {'✅ PASS' if success1 else '❌ FAIL'}")
    logger.info(f"  Multiple Messages: {'✅ PASS' if success2 else '❌ FAIL'}")
    logger.info("=" * 70)

    return success1 and success2


if __name__ == '__main__':
    success = asyncio.run(main())
    exit(0 if success else 1)
