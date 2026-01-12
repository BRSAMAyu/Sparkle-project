from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Form
from app.services.document_service import document_service
from app.core.cache import cache_service
import shutil
import os
import uuid
import json
from loguru import logger

router = APIRouter()

TEMP_DIR = "/tmp/sparkle_uploads"
os.makedirs(TEMP_DIR, exist_ok=True)

async def _process_document_task(task_id: str, file_path: str, options: dict):
    """Background task wrapper"""
    try:
        await document_service.clean_and_summarize(file_path, task_id, options)
    except Exception as e:
        logger.error(f"Background task {task_id} failed: {e}")
    finally:
        # Cleanup file after processing
        if os.path.exists(file_path):
            os.remove(file_path)

@router.post("/clean", summary="Async Upload and Clean Document")
async def clean_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    options: str = Form("{}", description="JSON string of options (e.g. {'enable_ocr': true})")
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
        
        # 2. Save temp file
        file_ext = os.path.splitext(file.filename)[1]
        temp_filename = f"{task_id}{file_ext}" # Use task_id in filename to avoid collision
        temp_path = os.path.join(TEMP_DIR, temp_filename)
        
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 3. Initialize Task Status in Redis
        await cache_service.set(f"task:{task_id}", {
            "status": "queued",
            "percent": 0,
            "message": "Waiting for worker..."
        }, ttl=3600)

        # 4. Dispatch Background Task
        background_tasks.add_task(_process_document_task, task_id, temp_path, opts)
            
        return {"task_id": task_id, "status": "queued"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/clean/{task_id}", summary="Check Cleaning Task Status")
async def check_task_status(task_id: str):
    """
    Poll this endpoint to get progress (percent, message) and final result.
    """
    data = await cache_service.get(f"task:{task_id}")
    if not data:
        raise HTTPException(status_code=404, detail="Task not found or expired")
    
    return data
