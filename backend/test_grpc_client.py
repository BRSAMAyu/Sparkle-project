"""
测试 gRPC 客户端
验证端到端流式通信
"""
import asyncio
import grpc
from loguru import logger

from app.gen.agent.v1 import agent_service_pb2, agent_service_pb2_grpc


async def test_stream_chat():
    """
    测试流式聊天功能
    """
    logger.info("Starting gRPC StreamChat test...")

    # 连接到 gRPC 服务器
    async with grpc.aio.insecure_channel('localhost:50051') as channel:
        stub = agent_service_pb2_grpc.AgentServiceStub(channel)

        # 构建请求
        request = agent_service_pb2.ChatRequest(
            user_id="test_user_123",
            session_id="test_session_456",
            message="你好，请介绍一下你自己",
            user_profile=agent_service_pb2.UserProfile(
                nickname="测试同学",
                timezone="Asia/Shanghai",
                language="zh-CN",
                is_pro=False
            ),
            config=agent_service_pb2.ChatConfig(
                model="",
                temperature=0.7,
                max_tokens=500,
                tools_enabled=False
            ),
            request_id="test_req_001"
        )

        # 添加 metadata
        metadata = (
            ("user-id", "test_user_123"),
            ("x-trace-id", "test_trace_001"),
        )

        try:
            logger.info("Sending StreamChat request...")
            logger.info(f"Request: user_id={request.user_id}, message={request.message}")

            response_count = 0
            full_response = ""

            # 接收流式响应
            async for response in stub.StreamChat(request, metadata=metadata):
                response_count += 1

                # 处理不同类型的响应
                if response.HasField("delta"):
                    print(response.delta, end="", flush=True)
                    full_response += response.delta

                elif response.HasField("status_update"):
                    status = response.status_update
                    state_name = agent_service_pb2.AgentStatus.State.Name(status.state)
                    logger.info(f"\n📍 Status: {state_name} - {status.details}")

                elif response.HasField("full_text"):
                    logger.info(f"\n✅ Full response received: {len(response.full_text)} chars")

                elif response.HasField("error"):
                    error = response.error
                    logger.error(f"\n❌ Error: [{error.code}] {error.message}")

                elif response.HasField("usage"):
                    usage = response.usage
                    logger.info(f"\n📊 Usage: {usage.total_tokens} tokens")

            print("\n")  # 换行
            logger.success(f"✅ StreamChat completed! Received {response_count} chunks")
            logger.info(f"📝 Full response length: {len(full_response)} chars")

            return True

        except grpc.RpcError as e:
            logger.error(f"❌ gRPC error: {e.code()} - {e.details()}")
            return False
        except Exception as e:
            logger.opt(exception=True).error(f"❌ Unexpected error: {e}")
            return False


async def test_retrieve_memory():
    """
    测试记忆检索功能
    """
    logger.info("\nStarting gRPC RetrieveMemory test...")

    async with grpc.aio.insecure_channel('localhost:50051') as channel:
        stub = agent_service_pb2_grpc.AgentServiceStub(channel)

        request = agent_service_pb2.MemoryQuery(
            user_id="test_user_123",
            query_text="高等数学 极限",
            limit=5,
            min_score=0.7,
            hybrid_alpha=0.8
        )

        try:
            logger.info("Sending RetrieveMemory request...")
            response = await stub.RetrieveMemory(request)

            logger.info(f"✅ Found {response.total_found} memory items")
            for idx, item in enumerate(response.items, 1):
                logger.info(f"  {idx}. Score: {item.score:.3f} - {item.content[:50]}...")

            return True

        except grpc.RpcError as e:
            logger.error(f"❌ gRPC error: {e.code()} - {e.details()}")
            return False


async def main():
    """
    运行所有测试
    """
    logger.info("=" * 70)
    logger.info("🧪 Sparkle AI Agent gRPC Client Test Suite")
    logger.info("=" * 70)

    # 测试 StreamChat
    test1_success = await test_stream_chat()

    # 等待一下
    await asyncio.sleep(1)

    # 测试 RetrieveMemory
    test2_success = await test_retrieve_memory()

    # 总结
    logger.info("\n" + "=" * 70)
    logger.info("📊 Test Results:")
    logger.info(f"  StreamChat:      {'✅ PASS' if test1_success else '❌ FAIL'}")
    logger.info(f"  RetrieveMemory:  {'✅ PASS' if test2_success else '❌ FAIL'}")
    logger.info("=" * 70)

    if test1_success and test2_success:
        logger.success("🎉 All tests passed!")
        return 0
    else:
        logger.error("❌ Some tests failed")
        return 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    exit(exit_code)
