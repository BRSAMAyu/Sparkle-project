"""
Sparkle Backend - FastAPI Application Entry Point
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.db.init_db import init_db
from app.services.job_service import JobService
from app.services.subject_service import SubjectService
from app.services.scheduler_service import scheduler_service
from app.core.idempotency import get_idempotency_store
from app.api.middleware import IdempotencyMiddleware
from app.api.v1.router import api_router
from app.api.v1.health import set_start_time

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    
    # ==================== 启动时 ====================
    logger.info("Starting Sparkle API Server...")
    set_start_time()  # 记录启动时间
    
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
        except Exception as e:
            logger.error(f"Startup tasks failed: {e}")
            # 可以在这里决定是否终止启动
    
    logger.info("Sparkle API Server started successfully")
    
    yield
    
    # ==================== 关闭时 ====================
    logger.info("Shutting down Sparkle API Server...")
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

