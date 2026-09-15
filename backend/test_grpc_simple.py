"""
简单的 gRPC 测试客户端
使用 DEMO_MODE 测试流式通信
"""
import asyncio
import grpc
import os
import uuid
from loguru import logger
from sqlalchemy import text

from app.gen.agent.v1 import agent_service_pb2, agent_service_pb2_grpc
from app.core.security import create_access_token
from app.config import settings
from app.db.session import AsyncSessionLocal


async def _resolve_test_user_id() -> str:
    env_user_id = os.getenv("TEST_USER_ID")
    if env_user_id:
        return env_user_id

    async with AsyncSessionLocal() as db:
        result = await db.execute(text("SELECT id::text FROM users WHERE is_active = true LIMIT 1"))
        row = result.first()
        if row and row[0]:
            return str(row[0])

    raise RuntimeError("No active user found. Set TEST_USER_ID in environment.")


async def test_demo_mode():
    """
    测试 DEMO_MODE 下的流式对话
    """
    logger.info("🧪 Testing gRPC StreamChat with REAL_USER...")
    
    real_user_id = await _resolve_test_user_id()
    session_id = str(uuid.uuid4())

    async with grpc.aio.insecure_channel('localhost:50051') as channel:
        stub = agent_service_pb2_grpc.AgentServiceStub(channel)

        # 使用非常简单的请求，确保能走到最后的 record_decision
        request = agent_service_pb2.ChatRequest(
            user_id=real_user_id,
            session_id=session_id,
            message="你好，请介绍一下你自己", 
            user_profile=agent_service_pb2.UserProfile(
                nickname="测试同学",
                timezone="Asia/Shanghai",
                language="zh-CN"
            ),
            request_id="fresh_req_v5"
        )

        token = create_access_token({"sub": real_user_id})
        
        # Use configured internal key for service-to-service authentication.
        internal_key = os.getenv("INTERNAL_API_KEY") or settings.INTERNAL_API_KEY
        if not internal_key:
            logger.error("❌ INTERNAL_API_KEY is not configured")
            return False
        
        metadata = (
            ("authorization", f"Bearer {token}"),
            ("user-id", real_user_id),
            ("x-trace-id", "demo_trace_001"),
            ("x-internal-api-key", internal_key), # Add internal key
        )

        try:
            logger.info(f"📤 Sending request: {request.message}")
            print("\n" + "=" * 70)
            print("🤖 AI Response:")
            print("=" * 70)

            response_count = 0
            full_text = ""

            async for response in stub.StreamChat(request, metadata=metadata):
                response_count += 1

                if response.HasField("delta"):
                    # 打印流式文本
                    print(response.delta, end="", flush=True)
                    full_text += response.delta

                elif response.HasField("status_update"):
                    status = response.status_update
                    state_name = agent_service_pb2.AgentStatus.State.Name(status.state)
                    logger.info(f"\n📍 [{state_name}] {status.details}")

                elif response.HasField("full_text"):
                    logger.info(f"\n✅ Completed! Total length: {len(response.full_text)} chars")

                elif response.HasField("error"):
                    error = response.error
                    logger.error(f"\n❌ Error: [{error.code}] {error.message}")
                    return False

            print("\n" + "=" * 70)
            logger.success(f"✅ Test completed successfully!")
            logger.info(f"📊 Statistics:")
            logger.info(f"   - Response chunks: {response_count}")
            logger.info(f"   - Total characters: {len(full_text)}")

            return True

        except grpc.RpcError as e:
            logger.error(f"❌ gRPC error: {e.code()} - {e.details()}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}", exc_info=True)
            return False


if __name__ == '__main__':
    success = asyncio.run(test_demo_mode())
    exit(0 if success else 1)
