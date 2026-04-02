"""
Sparkle Backend - FastAPI Application Entry Point
"""
import asyncio
import os
import sys
from contextlib import asynccontextmanager, suppress

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.middleware import IdempotencyMiddleware, RequestContextMiddleware
from app.api.v1.health import set_start_time
from app.api.v1.router import api_router
from app.config import settings
from app.core.cache import cache_service
from app.core.redis_search_client import redis_search_client
from app.core.exceptions import SparkleException
from app.core.idempotency import get_idempotency_store
from app.core.pending_actions import pending_actions_store
from app.core.rate_limiting import setup_rate_limiting
from app.core.websocket import manager
from app.db.extensions import ensure_database_extensions
from app.db.init_db import init_db
from app.db.session import AsyncSessionLocal
from app.orchestration.summarization_worker import create_summarization_worker
from app.services.achievement_event_consumer import AchievementEventConsumer
from app.services.billing_worker import BillingWorker
from app.services.capsule_event_consumer import CapsuleEventConsumer
from app.services.execution_event_consumer import ExecutionEventConsumer
from app.services.galaxy_execution_consumer import GalaxyExecutionConsumer
from app.services.galaxy_event_consumer import GalaxyEventConsumer
from app.services.job_service import JobService
from app.services.preference_event_consumer import PreferenceEventConsumer
from app.services.profile_event_consumer import ProfileEventConsumer
from app.services.cognitive_event_consumer import CognitiveEventConsumer
from app.services.nudge_event_consumer import NudgeEventConsumer
from app.services.scheduler_service import scheduler_service
from app.services.subject_service import SubjectService
from app.services.task_event_consumer import TaskEventConsumer
from app.services.user_service import UserService
from app.workers.expansion_worker import start_expansion_worker, stop_expansion_worker
from app.workers.graph_sync_worker import start_sync_worker, stop_sync_worker

# Configure Loguru
logger.remove()
logger.add(
    sys.stderr,
    level=settings.LOG_LEVEL,
    serialize=not settings.DEBUG, # JSON format in production
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理

    P1 Fix: All startup/shutdown logic is now unified in lifespan context manager.
    Removed deprecated @app.on_event("startup") to prevent race conditions.
    """

    # ==================== 启动时 ====================
    logger.info("Starting Sparkle API Server...")
    set_start_time()  # 记录启动时间

    # 版本兼容性检查 (passlib/bcrypt)
    try:
        import bcrypt
        import passlib
        logger.info(f"Auth deps: passlib={passlib.__version__}, bcrypt={bcrypt.__version__}")
        # 验证兼容性: passlib 1.7.4 与 bcrypt 5.0+ 不兼容
        if passlib.__version__.startswith("1.7."):
            try:
                bcrypt_ver = tuple(map(int, bcrypt.__version__.split(".")[:2]))
                if bcrypt_ver >= (5, 0):
                    logger.warning(f"⚠️  passlib {passlib.__version__} may be incompatible with bcrypt {bcrypt.__version__}. Consider downgrading to bcrypt<5.0.0")
            except Exception:
                pass
    except ImportError:
        logger.warning("passlib or bcrypt not installed")

    # Ensure upload directory exists
    if not os.path.exists(settings.UPLOAD_DIR):
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    # Initialize Cache (Redis)
    await cache_service.init_redis()
    pending_actions_store.set_redis(cache_service.redis)
    # Initialize WebSocket Redis
    await manager.init_redis()
    if cache_service.redis:
        try:
            await redis_search_client.ensure_index()
        except Exception as e:
            logger.warning(f"Failed to ensure Redis search index at startup (non-fatal): {e}")

    event_bus = None
    preference_consumer_task = None
    if cache_service.redis:
        user_service = UserService(None, cache_service.redis)
        consumer = PreferenceEventConsumer(cache_service.redis, user_service)
        preference_consumer_task = asyncio.create_task(consumer.start())
        app.state.preference_consumer_task = preference_consumer_task

    # Start Galaxy event consumer
    galaxy_consumer_task = None
    if cache_service.redis:
        from app.core.event_bus import event_bus
        galaxy_consumer = GalaxyEventConsumer(event_bus=event_bus)
        galaxy_consumer_task = asyncio.create_task(galaxy_consumer.start())
        app.state.galaxy_consumer_task = galaxy_consumer_task

    # Start Task event consumer
    task_consumer_task = None
    if cache_service.redis:
        task_consumer = TaskEventConsumer(event_bus=event_bus)
        task_consumer_task = asyncio.create_task(task_consumer.start())
        app.state.task_consumer_task = task_consumer_task

    achievement_consumer_task = None
    if cache_service.redis:
        achievement_consumer = AchievementEventConsumer(event_bus=event_bus)
        achievement_consumer_task = asyncio.create_task(achievement_consumer.start())
        app.state.achievement_consumer_task = achievement_consumer_task

    execution_consumer_task = None
    if cache_service.redis:
        execution_consumer = ExecutionEventConsumer(event_bus=event_bus)
        execution_consumer_task = asyncio.create_task(execution_consumer.start())
        app.state.execution_consumer_task = execution_consumer_task

    galaxy_execution_consumer_task = None
    if cache_service.redis:
        galaxy_execution_consumer = GalaxyExecutionConsumer(event_bus=event_bus)
        galaxy_execution_consumer_task = asyncio.create_task(galaxy_execution_consumer.start())
        app.state.galaxy_execution_consumer_task = galaxy_execution_consumer_task

    profile_consumer_task = None
    if cache_service.redis:
        profile_consumer = ProfileEventConsumer(event_bus=event_bus, redis_client=cache_service.redis)
        profile_consumer_task = asyncio.create_task(profile_consumer.start())
        app.state.profile_consumer_task = profile_consumer_task

    if cache_service.redis:
        cognitive_consumer = CognitiveEventConsumer(event_bus=event_bus, redis_client=cache_service.redis)
        cognitive_consumer_task = asyncio.create_task(cognitive_consumer.start())
        app.state.cognitive_consumer_task = cognitive_consumer_task

    if cache_service.redis:
        capsule_consumer = CapsuleEventConsumer(event_bus=event_bus)
        capsule_consumer_task = asyncio.create_task(capsule_consumer.start())
        app.state.capsule_consumer_task = capsule_consumer_task

    if cache_service.redis and event_bus is not None:
        nudge_consumer = NudgeEventConsumer(event_bus=event_bus)
        nudge_consumer_task = asyncio.create_task(nudge_consumer.start())
        app.state.nudge_consumer_task = nudge_consumer_task

    summarization_worker_task = None
    summarization_worker = None
    if cache_service.redis and settings.ENABLE_SUMMARIZATION_WORKER:
        try:
            summarization_worker = create_summarization_worker(
                cache_service.redis,
                worker_id="main-app-worker",
            )
            summarization_worker_task = asyncio.create_task(summarization_worker.start())
            app.state.summarization_worker = summarization_worker
            app.state.summarization_worker_task = summarization_worker_task
            logger.info("SummarizationWorker started")
        except Exception as e:
            logger.error(f"Failed to start SummarizationWorker: {e}")

    billing_worker_task = None
    billing_worker = None
    if cache_service.redis:
        try:
            billing_worker = BillingWorker()
            billing_worker_task = asyncio.create_task(billing_worker.start())
            app.state.billing_worker = billing_worker
            app.state.billing_worker_task = billing_worker_task
            logger.info("BillingWorker started")
        except Exception as e:
            logger.error(f"Failed to start BillingWorker: {e}")

    # Start Galaxy Services (Phase 4)
    if cache_service.redis and event_bus is not None:
        from app.services.galaxy.streaming_service import init_galaxy_streaming_service
        try:
            galaxy_streaming_service = await init_galaxy_streaming_service(manager, event_bus)
            # Store the service in app state for potential access
            app.state.galaxy_streaming_service = galaxy_streaming_service
            logger.info("GalaxyStreamingService initialized")
        except Exception as e:
            logger.error(f"Failed to initialize GalaxyStreamingService: {e}")

    async with AsyncSessionLocal() as db:
        try:
            try:
                extension_status = await ensure_database_extensions(db, ("vector", "age"))
                logger.info(
                    "Database extensions ensured: vector={}, age={}",
                    extension_status.get("vector", False),
                    extension_status.get("age", False),
                )
            except Exception as e:
                await db.rollback()
                logger.warning(f"Failed to ensure database extensions at startup (non-fatal): {e}")

            # 0. 初始化数据库数据
            await init_db(db)

            # 0.5 确保全局成就和皮肤定义存在 (所有用户共享)
            try:
                from app.services.guest_seed_service import (
                    _ensure_achievements,
                    _ensure_galaxy_skins,
                    ensure_global_galaxy_baseline,
                )
                from app.data.seed_content_initial import initialize_seed_libraries
                await _ensure_achievements(db)
                await _ensure_galaxy_skins(db)
                await ensure_global_galaxy_baseline(db)
                await initialize_seed_libraries(db)
                await db.commit()
                logger.info("Global achievements, galaxy skins, galaxy baseline, and official seed libraries ensured")
            except Exception as e:
                await db.rollback()
                logger.warning(f"Failed to ensure startup reference data (non-fatal): {e}")

            # 1. 恢复中断的 Job
            job_service = JobService()
            await job_service.startup_recovery(db)

            # 2. 加载学科缓存
            subject_service = SubjectService()
            await subject_service.ensure_default_subjects(db)
            await subject_service.load_cache(db)
            await db.commit()

            # 3. 启动定时任务调度器
            scheduler_service.start()

            # 4. 启动知识拓展后台任务
            await start_expansion_worker()

            # 5. 启动图同步 Worker (AGE)
            if start_sync_worker:
                await start_sync_worker()
        except Exception as e:
            logger.error(f"Startup tasks failed: {e}")
            # 可以在这里决定是否终止启动

    logger.info("Sparkle API Server started successfully")

    yield

    # ==================== 关闭时 ====================
    logger.info("Shutting down Sparkle API Server...")

    # 停止图同步 Worker
    if stop_sync_worker:
        await stop_sync_worker()

    # 停止知识拓展后台任务
    await stop_expansion_worker()

    # Stop preference event consumer
    preference_consumer_task = getattr(app.state, "preference_consumer_task", None)
    if preference_consumer_task:
        preference_consumer_task.cancel()
        with suppress(asyncio.CancelledError):
            await preference_consumer_task

    # Stop galaxy event consumer
    galaxy_consumer_task = getattr(app.state, "galaxy_consumer_task", None)
    if galaxy_consumer_task:
        galaxy_consumer_task.cancel()
        with suppress(asyncio.CancelledError):
            await galaxy_consumer_task

    # Stop task event consumer
    task_consumer_task = getattr(app.state, "task_consumer_task", None)
    if task_consumer_task:
        task_consumer_task.cancel()
        with suppress(asyncio.CancelledError):
            await task_consumer_task

    achievement_consumer_task = getattr(app.state, "achievement_consumer_task", None)
    if achievement_consumer_task:
        achievement_consumer_task.cancel()
        with suppress(asyncio.CancelledError):
            await achievement_consumer_task

    execution_consumer_task = getattr(app.state, "execution_consumer_task", None)
    if execution_consumer_task:
        execution_consumer_task.cancel()
        with suppress(asyncio.CancelledError):
            await execution_consumer_task

    galaxy_execution_consumer_task = getattr(app.state, "galaxy_execution_consumer_task", None)
    if galaxy_execution_consumer_task:
        galaxy_execution_consumer_task.cancel()
        with suppress(asyncio.CancelledError):
            await galaxy_execution_consumer_task

    profile_consumer_task = getattr(app.state, "profile_consumer_task", None)
    if profile_consumer_task:
        profile_consumer_task.cancel()
        with suppress(asyncio.CancelledError):
            await profile_consumer_task

    cognitive_consumer_task = getattr(app.state, "cognitive_consumer_task", None)
    if cognitive_consumer_task:
        cognitive_consumer_task.cancel()
        with suppress(asyncio.CancelledError):
            await cognitive_consumer_task

    nudge_consumer_task = getattr(app.state, "nudge_consumer_task", None)
    if nudge_consumer_task:
        nudge_consumer_task.cancel()
        with suppress(asyncio.CancelledError):
            await nudge_consumer_task

    # Stop summarization worker
    summarization_worker = getattr(app.state, "summarization_worker", None)
    summarization_worker_task = getattr(app.state, "summarization_worker_task", None)
    if summarization_worker:
        await summarization_worker.stop()
    if summarization_worker_task:
        summarization_worker_task.cancel()
        with suppress(asyncio.CancelledError):
            await summarization_worker_task

    billing_worker = getattr(app.state, "billing_worker", None)
    billing_worker_task = getattr(app.state, "billing_worker_task", None)
    if billing_worker:
        billing_worker.stop()
    if billing_worker_task:
        billing_worker_task.cancel()
        with suppress(asyncio.CancelledError):
            await billing_worker_task

    # Stop Galaxy Streaming Service
    galaxy_streaming_service = getattr(app.state, "galaxy_streaming_service", None)
    if galaxy_streaming_service:
        galaxy_streaming_service.stop()
        logger.info("GalaxyStreamingService stopped")

    # Close Cache
    await cache_service.close()
    # Close WebSocket Redis
    await manager.close_redis()

    logger.info("Sparkle API Server stopped")

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Sparkle AI Learning Assistant API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Auto-instrument FastAPI
FastAPIInstrumentor.instrument_app(app)
# Auto-instrument SQLAlchemy
SQLAlchemyInstrumentor().instrument()
# Auto-instrument Requests (for LLM API calls)
RequestsInstrumentor().instrument()
# Auto-instrument Redis
RedisInstrumentor().instrument()

setup_rate_limiting(app)

# P1: Initialize Prometheus Instrumentator within app creation
# Moved from deprecated @app.on_event("startup") to ensure proper lifecycle order
_instrumentator = Instrumentator().instrument(app)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        if settings.DEBUG:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-src 'none'; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "form-action 'self';"
            )
        else:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self'; "
                "img-src 'self' data:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-src 'none'; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "form-action 'self';"
            )
        return response

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestContextMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🆕 幂等性中间件
idempotency_store = get_idempotency_store(settings.IDEMPOTENCY_STORE if hasattr(settings, "IDEMPOTENCY_STORE") else "redis")
app.add_middleware(IdempotencyMiddleware, store=idempotency_store)


@app.get("/")
async def root():
    """Root endpoint - health check"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """
    简单健康检查端点

    完整的健康检查请访问 /api/v1/health
    """
    return {
        "status": "healthy",
        "detail": "For detailed health info, use /api/v1/health"
    }


@app.get("/live")
async def liveness_probe():
    """Kubernetes liveness probe alias."""
    return {"status": "alive"}


@app.get("/ready")
async def readiness_probe():
    """Kubernetes readiness probe alias."""
    return {"status": "ready"}


# Include API routers
app.include_router(api_router, prefix="/api/v1")
if settings.ENABLE_AGENT_GRAPH_V2:
    try:
        from importlib import import_module
        agent_graph_router = import_module("app.api.v2.agent_graph").router
        app.include_router(agent_graph_router, prefix="/api/v2/agent", tags=["Agent V2"])
    except Exception as exc:
        logger.warning(f"Agent Graph V2 disabled (import failed): {exc}")
        placeholder_router = APIRouter()

        @placeholder_router.get("/status")
        async def agent_graph_v2_unavailable():
            raise HTTPException(
                status_code=501,
                detail="Agent Graph V2 dependencies not installed (langgraph/langchain)."
            )

        app.include_router(placeholder_router, prefix="/api/v2/agent", tags=["Agent V2"])
else:
    logger.info("Agent Graph V2 disabled (ENABLE_AGENT_GRAPH_V2=false)")


# Mount static files for uploads
# Make sure the directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理 Pydantic 验证错误"""
    encoded_errors = jsonable_encoder(exc.errors(), custom_encoder={ValueError: lambda value: str(value)})
    logger.error(f"Validation error for {request.method} {request.url}: {encoded_errors}")
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "error_code": "ValidationError",
            "message": "请求数据格式不正确",
            "detail": encoded_errors,
        },
    )

@app.exception_handler(SparkleException)
async def sparkle_exception_handler(request: Request, exc: SparkleException):
    """自定义异常处理器"""
    request_id = getattr(request.state, "request_id", None)
    trace_id = getattr(request.state, "trace_id", None)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_code": exc.__class__.__name__,
            "message": exc.message,
            "detail": exc.detail,
            "request_id": request_id,
            "trace_id": trace_id,
        },
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """全局未捕获异常处理器"""
    logger.exception(f"Unhandled exception: {exc}")
    request_id = getattr(request.state, "request_id", None)
    trace_id = getattr(request.state, "trace_id", None)
    content = {
        "success": False,
        "error_code": "InternalServerError",
        "message": "An unexpected error occurred",
        "request_id": request_id,
        "trace_id": trace_id,
    }
    if settings.DEBUG:
        content["detail"] = str(exc)
    return JSONResponse(
        status_code=500,
        content=content,
    )
