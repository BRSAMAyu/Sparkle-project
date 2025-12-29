"""
Sparkle AI Agent - gRPC Server
Python 后端 gRPC 服务入口
负责 AI 推理、RAG 检索、长期记忆管理
"""
import asyncio
import signal
from concurrent import futures
from loguru import logger
import grpc
from grpc_reflection.v1alpha import reflection
from opentelemetry.instrumentation.grpc import GrpcAioInstrumentorServer

from app.gen.agent.v1 import agent_service_pb2, agent_service_pb2_grpc
from app.services.agent_grpc_service import AgentServiceImpl
from app.core.cache import cache_service
from app.db.session import AsyncSessionLocal
from app.orchestration.orchestrator import ChatOrchestrator
from app.config import settings


# 配置日志
logger.add(
    "logs/grpc_server_{time}.log",
    rotation="1 day",
    retention="7 days",
    level="INFO"
)


class GracefulShutdown:
    """优雅关闭处理器"""

    def __init__(self, server: grpc.aio.Server):
        self.server = server
        self.is_shutting_down = False

    async def shutdown(self, sig=None):
        if self.is_shutting_down:
            return

        self.is_shutting_down = True

        if sig:
            logger.info(f"Received signal {sig.name}, initiating graceful shutdown...")
        else:
            logger.info("Initiating graceful shutdown...")

        logger.info("Stopping gRPC server...")
        await self.server.stop(grace=5.0)  # 5 秒优雅关闭
        await cache_service.close()
        logger.info("gRPC server stopped successfully")


async def serve():
    """
    启动 gRPC 服务器
    """
    # 创建服务器
    server = grpc.aio.server(
        futures.ThreadPoolExecutor(max_workers=10),
        options=[
            ('grpc.max_send_message_length', 50 * 1024 * 1024),  # 50MB
            ('grpc.max_receive_message_length', 50 * 1024 * 1024),  # 50MB
            ('grpc.keepalive_time_ms', 10000),
            ('grpc.keepalive_timeout_ms', 5000),
            ('grpc.keepalive_permit_without_calls', True),
            ('grpc.http2.max_pings_without_data', 0),
        ]
    )

    # Initialize Redis (required for orchestrator)
    await cache_service.init_redis()
    if not cache_service.redis:
        raise RuntimeError("Redis client initialization failed")
    try:
        await cache_service.redis.ping()
    except Exception as e:
        logger.error(f"Redis unavailable: {e}")
        raise

    orchestrator = ChatOrchestrator(redis_client=cache_service.redis)

    # 注册 AgentService
    agent_service_pb2_grpc.add_AgentServiceServicer_to_server(
        AgentServiceImpl(orchestrator=orchestrator, db_session_factory=AsyncSessionLocal), server
    )

    if settings.DEBUG or settings.GRPC_ENABLE_REFLECTION:
        # 启用 gRPC 反射（用于调试，生产环境可关闭）
        SERVICE_NAMES = (
            agent_service_pb2.DESCRIPTOR.services_by_name['AgentService'].full_name,
            reflection.SERVICE_NAME,
        )
        reflection.enable_server_reflection(SERVICE_NAMES, server)

    # 监听端口
    listen_addr = f'[::]:{getattr(settings, "GRPC_PORT", 50051)}'
    use_tls = settings.GRPC_REQUIRE_TLS or (
        settings.GRPC_TLS_CERT_PATH and settings.GRPC_TLS_KEY_PATH
    )
    if use_tls:
        with open(settings.GRPC_TLS_CERT_PATH, "rb") as cert_file:
            cert_chain = cert_file.read()
        with open(settings.GRPC_TLS_KEY_PATH, "rb") as key_file:
            private_key = key_file.read()
        credentials = grpc.ssl_server_credentials(((private_key, cert_chain),))
        server.add_secure_port(listen_addr, credentials)
    else:
        server.add_insecure_port(listen_addr)

    logger.info("=" * 60)
    logger.info("🚀 Sparkle AI Agent gRPC Server Starting...")
    logger.info(f"📡 Listening on: {listen_addr} ({'TLS' if use_tls else 'PLAINTEXT'})")
    logger.info(f"🔧 Environment: {'DEMO' if getattr(settings, 'DEMO_MODE', False) else 'PRODUCTION'}")
    logger.info(f"🤖 LLM Model: {settings.LLM_MODEL_NAME}")
    logger.info(f"🔗 LLM Provider: {settings.LLM_API_BASE_URL}")
    logger.info("=" * 60)

    # 启动服务器
    # Auto-instrument gRPC Server
    grpc_server_instrumentor = GrpcAioInstrumentorServer()
    grpc_server_instrumentor.instrument()

    await server.start()
    logger.success("✅ gRPC server started successfully!")

    # 设置优雅关闭
    shutdown_handler = GracefulShutdown(server)

    # 注册信号处理
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(
            sig,
            lambda s=sig: asyncio.create_task(shutdown_handler.shutdown(s))
        )

    try:
        # 等待服务器被停止
        await server.wait_for_termination()
    except KeyboardInterrupt:
        await shutdown_handler.shutdown()


def main():
    """主入口"""
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    main()
