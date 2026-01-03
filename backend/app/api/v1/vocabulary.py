"""
生词本与词典 API
Vocabulary & Dictionary API
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.vocabulary_service import vocabulary_service
from app.config import settings
from app.utils.helpers import read_upload_file

router = APIRouter()

# ============ Schemas ============

class WordBookAdd(BaseModel):
    word: str
    definition: str
    phonetic: Optional[str] = None
    context_sentence: Optional[str] = None
    task_id: Optional[UUID] = None

class ReviewRecord(BaseModel):
    word_id: UUID
    success: bool

class DictionaryImport(BaseModel):
    source: str = "custom"
    format: str = "json"

# ============ Endpoints ============

@router.get("/lookup", summary="词典查询")
async def lookup_word(
    word: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    entry = await vocabulary_service.lookup(db, word)
    if not entry:
        # If not in local dict, maybe use LLM to provide a temporary definition?
        # For now, 404
        raise HTTPException(status_code=404, detail="Word not found in dictionary")
    return entry

@router.post("/wordbook", summary="添加到生词本")
async def add_to_wordbook(
    data: WordBookAdd,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    word_entry = await vocabulary_service.add_to_wordbook(
        db, current_user.id, **data.model_dump()
    )
    return word_entry

@router.get("/wordbook/review", summary="获取复习列表")
async def get_review_list(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await vocabulary_service.get_review_list(db, current_user.id)

@router.post("/wordbook/review", summary="记录复习结果")
async def record_review(
    data: ReviewRecord,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await vocabulary_service.record_review(db, data.word_id, data.success)
    return {"success": True}

@router.post("/import", summary="导入词典数据")
async def import_dictionary(
    format: str = Form("json"),
    source: str = Form("custom"),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Only admins should probably do this, but for this app we allow the user for their private setup
    if format not in {"json", "csv"}:
        raise HTTPException(status_code=400, detail="Unsupported dictionary format")

    if format == "json":
        allowed_extensions = {".json"}
        allowed_types = {"application/json", "text/json"}
    else:
        allowed_extensions = {".csv"}
        allowed_types = {"text/csv", "application/csv", "application/vnd.ms-excel"}

    content = await read_upload_file(
        file,
        max_size=settings.MAX_UPLOAD_SIZE,
        allowed_extensions=allowed_extensions,
        allowed_content_types=allowed_types,
    )
    try:
        text_content = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Invalid file encoding")
    count = await vocabulary_service.import_dictionary(
        db, text_content, format=format, source=source
    )
    return {"imported": count}

# ============ LLM Integration ============

@router.get("/llm/associate", summary="词汇联想")
async def associate_word(word: str):
    words = await vocabulary_service.get_word_associations(word)
    return {"associations": words}

@router.get("/llm/sentence", summary="例句生成")
async def generate_sentence(word: str, context: Optional[str] = None):
    sentence = await vocabulary_service.generate_example_sentence(word, context)
    return {"sentence": sentence}

@router.get("/llm/polish", summary="释义润色")
async def polish_definition(word: str, definition: str):
    polished = await vocabulary_service.polish_definition(word, definition)
    return {"polished": polished}
