"""
Sparkle Backend - FastAPI Application Entry Point
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator
from app.core.rate_limiting import setup_rate_limiting
from app.config import settings
from app.db.session import get_db, AsyncSessionLocal
from app.db.init_db import init_db
from app.services.job_service import JobService
from app.services.subject_service import SubjectService
from app.services.scheduler_service import scheduler_service
from app.core.cache import cache_service
from app.core.access_control import verify_token
from app.core.idempotency import get_idempotency_store
from app.api.middleware import IdempotencyMiddleware
from loguru import logger
from app.api.v1.router import api_router
from app.workers.expansion_worker import start_expansion_worker, stop_expansion_worker
from app.api.v1.health import set_start_time
from starlette.middleware.base import BaseHTTPMiddleware

from fastapi.responses import JSONResponse
from app.core.exceptions import SparkleException

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    
    # ==================== 启动时 ====================
    logger.info("Starting Sparkle API Server...")
    set_start_time()  # 记录启动时间
    
    # Ensure upload directory exists
    if not os.path.exists(settings.UPLOAD_DIR):
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    # Initialize Cache (Redis)
    await cache_service.init_redis()
    
    async with AsyncSessionLocal() as db:
        try:
            # 🆕 0. 初始化数据库数据
            await init_db(db)

            # 🆕 1. 恢复中断的 Job
            job_service = JobService()
            await job_service.startup_recovery(db)
            
            # 🆕 2. 加载学科缓存
            subject_service = SubjectService()
            await subject_service.load_cache(db)

            # 🆕 3. 启动定时任务调度器
            scheduler_service.start()

            # 🆕 4. 启动知识拓展后台任务
            await start_expansion_worker()
        except Exception as e:
            logger.error(f"Startup tasks failed: {e}")
            # 可以在这里决定是否终止启动

    logger.info("Sparkle API Server started successfully")
    
    yield
    
    # ==================== 关闭时 ====================
    logger.info("Shutting down Sparkle API Server...")

    # 停止知识拓展后台任务
    await stop_expansion_worker()
    
    # Close Cache
    await cache_service.close()

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

setup_rate_limiting(app)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self' *; frame-ancestors 'none'; object-src 'none'; img-src 'self' data: *;"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🆕 幂等性中间件
idempotency_store = get_idempotency_store(settings.IDEMPOTENCY_STORE if hasattr(settings, "IDEMPOTENCY_STORE") else "memory")
app.add_middleware(IdempotencyMiddleware, store=idempotency_store)


@app.on_event("startup")
async def startup_event():
    """Startup event to instrument and expose metrics"""
    Instrumentator().instrument(app).expose(app)


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


# Include API routers
app.include_router(api_router, prefix="/api/v1")

# Mount static files for uploads
# Make sure the directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

@app.exception_handler(SparkleException)
async def sparkle_exception_handler(request: Request, exc: SparkleException):
    """自定义异常处理器"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_code": exc.__class__.__name__,
            "message": exc.message,
            "detail": exc.detail
        },
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """全局未捕获异常处理器"""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error_code": "InternalServerError",
            "message": "An unexpected error occurred",
            "detail": str(exc) if settings.DEBUG else None
        },
    )