"""
测试 WebSocket 响应中是否包含 session_id
"""
import asyncio
import json
import websockets
from jose import jwt
import time

JWT_SECRET = "dev-secret-key"

def create_jwt(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": int(time.time()) + 3600,
        "type": "access",
        "iss": "sparkle-gateway",
        "aud": "sparkle-app",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

async def test_session_id():
    user_id = "00000000-0000-0000-0000-000000000001"
    token = create_jwt(user_id)
    uri = f"ws://localhost:8080/ws/chat?token={token}"

    try:
        async with websockets.connect(uri, ping_interval=None, ping_timeout=None) as websocket:
            # 发送测试消息
            test_message = {
                "type": "message",
                "message": "测试session_id",
                "session_id": "test-session-123",
                "user_id": user_id
            }

            print(f"📤 发送消息: session_id={test_message['session_id']}")
            await websocket.send(json.dumps(test_message))

            # 接收响应
            print("\n📥 收到的响应:")
            response_count = 0
            session_ids_found = []

            while response_count < 5:  # 只接收前5条消息
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=60.0)
                    data = json.loads(response)
                    response_count += 1

                    # 检查 session_id
                    session_id = data.get("session_id")
                    msg_type = data.get("type")
                    print(f"\n响应 #{response_count}:")
                    print(f"  type: {msg_type}")
                    print(f"  session_id: {session_id}")

                    if session_id:
                        session_ids_found.append(session_id)

                    if msg_type == "done":
                        break

                except asyncio.TimeoutError:
                    print("⏱️  超时")
                    break

            print(f"\n📊 总结:")
            print(f"  收到响应数: {response_count}")
            print(f"  包含session_id的响应数: {len(session_ids_found)}")
            print(f"  session_ids: {session_ids_found}")

            return len(session_ids_found) > 0

    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_session_id())
    exit(0 if success else 1)
