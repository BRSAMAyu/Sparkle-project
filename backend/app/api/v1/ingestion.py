import asyncio
import json
import os
import tempfile
import uuid

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from loguru import logger

from app.config import settings
from app.core.cache import cache_service
from app.services.document_service import document_service

router = APIRouter()

# 使用环境变量配置临时目录，避免硬编码
TEMP_DIR = os.path.join(
    os.getenv("SPARKLE_UPLOAD_TEMP_DIR", tempfile.gettempdir()),
    "sparkle_uploads"
)
os.makedirs(TEMP_DIR, exist_ok=True)

# 清洗后内容的最大大小（10MB）
MAX_CLEANED_SIZE = 10 * 1024 * 1024  # 10MB in bytes
DOCUMENT_CLEANING_CONCURRENCY = max(1, int(os.getenv("SPARKLE_DOCUMENT_CLEAN_CONCURRENCY", "3")))
_DOCUMENT_CLEANING_SEMAPHORE = asyncio.Semaphore(DOCUMENT_CLEANING_CONCURRENCY)

def check_disk_space(required_bytes: int) -> bool:
    """
    检查临时目录是否有足够的磁盘空间
    """
    try:
        stat = os.statvfs(TEMP_DIR)
        free_space = stat.f_bavail * stat.f_frsize
        if free_space < required_bytes:
            logger.error(
                f"Insufficient disk space: {free_space} bytes available, "
                f"{required_bytes} bytes required"
            )
            return False
        return True
    except Exception as e:
        logger.warning(f"Failed to check disk space: {e}")
        # 如果无法检查，假设有足够空间（向后兼容）
        return True

async def _process_document_task(task_id: str, file_path: str, options: dict):
    """Background task wrapper with proper error handling"""
    try:
        async with _DOCUMENT_CLEANING_SEMAPHORE:
            await document_service.clean_and_summarize(file_path, task_id, options)
    except Exception as e:
        logger.error(f"Background task {task_id} failed: {e}", exc_info=True)
        # 更新任务状态为失败，通知用户
        try:
            await cache_service.set(f"task:{task_id}", {
                "status": "failed",
                "percent": 100,
                "message": f"Processing failed: {str(e)}",
                "error": str(e)
            }, ttl=3600)
        except Exception as cache_err:
            logger.error(f"Failed to update task status: {cache_err}")
    finally:
        # Cleanup file after processing
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"Cleaned up temp file: {file_path}")
        except Exception as cleanup_err:
            logger.warning(f"Failed to cleanup temp file {file_path}: {cleanup_err}")

@router.post("/clean", summary="Async Upload and Clean Document")
async def clean_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    options: str = Form("{}", description="JSON options (e.g. {'enable_ocr': true, 'ocr_engine': 'zhipu' | 'local'})")
):
    """
    Starts an asynchronous document cleaning task.
    Returns a `task_id` immediately. Use `GET /clean/{task_id}` to check progress.
    """
    try:
        # Parse options
        try:
            opts = json.loads(options)
        except json.JSONDecodeError:
            opts = {}

        # 1. Generate Task ID
        task_id = str(uuid.uuid4())

        # 2. 检查磁盘空间（假设需要文件大小的3倍空间用于处理）
        file_size = 0
        file_content = await file.read()
        file_size = len(file_content)
        if file_size > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum upload size is {settings.MAX_UPLOAD_SIZE} bytes."
            )
        required_space = file_size * 3  # 原始文件 + 临时文件 + 处理结果

        if not check_disk_space(required_space):
            raise HTTPException(
                status_code=507,
                detail="Insufficient disk space on server. Please try again later."
            )

        # 3. Save temp file
        file_ext = os.path.splitext(file.filename)[1]
        temp_filename = f"{task_id}{file_ext}" # Use task_id in filename to avoid collision
        temp_path = os.path.join(TEMP_DIR, temp_filename)

        with open(temp_path, "wb") as buffer:
            buffer.write(file_content)

        # 4. Initialize Task Status in Redis
        await cache_service.set(f"task:{task_id}", {
            "status": "queued",
            "percent": 0,
            "message": "Waiting for worker..."
        }, ttl=3600)

        # 5. Dispatch Background Task
        background_tasks.add_task(_process_document_task, task_id, temp_path, opts)

        return {"task_id": task_id, "status": "queued"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to initiate document cleaning: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process upload: {str(e)}")

@router.get("/clean/{task_id}", summary="Check Cleaning Task Status")
async def check_task_status(task_id: str):
    """
    Poll this endpoint to get progress (percent, message) and final result.
    """
    data = await cache_service.get(f"task:{task_id}")
    if not data:
        raise HTTPException(status_code=404, detail="Task not found or expired")

    return data
