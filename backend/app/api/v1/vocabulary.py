"""
生词本与词典 API
Vocabulary & Dictionary API
"""
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config.settings import settings
from app.db.session import get_db
from app.models.user import User
from app.services.mdx_dictionary_service import create_mdx_service
from app.services.vocabulary_service import vocabulary_service
from app.utils.helpers import read_upload_file

router = APIRouter()

# 全局 MDX 服务实例
_mdx_service = None


def get_mdx_service():
    """获取或初始化 MDX 词典服务"""
    global _mdx_service
    if _mdx_service is None:
        mdx_path = getattr(settings, 'MDX_DICTIONARY_PATH', None)
        mdd_path = getattr(settings, 'MDD_RESOURCES_PATH', None)
        if mdx_path:
            try:
                _mdx_service = create_mdx_service(mdx_path, mdd_path)
            except Exception as e:
                from app.utils.logger import get_logger
                logger = get_logger()
                logger.warning(f"MDX service init failed: {e}")
    return _mdx_service


# ============ Schemas ============

class WordBookAdd(BaseModel):
    """添加生词到生词本"""
    word: str = Field(..., min_length=1, max_length=100)
    definition: str = Field(..., min_length=1)
    phonetic: str | None = Field(None, max_length=100)
    context_sentence: str | None = Field(None, max_length=1000)
    task_id: UUID | None = None
    importance: int = Field(3, ge=1, le=5, description="1-5 星，5 星为最需要复习的词汇")
    part_of_speech: str | None = Field(None, max_length=50)
    source_translation_id: str | None = Field(None, max_length=100)


class ReviewRecord(BaseModel):
    """记录复习结果"""
    word_id: UUID
    remembered: bool = Field(..., description="是否记住")


class UpdateImportance(BaseModel):
    """更新重要度"""
    importance: int = Field(..., ge=1, le=5, description="1-5 星")


class DictionaryImport(BaseModel):
    """导入词典数据"""
    source: str = "custom"
    format: str = "json"


class WordBookResponse(BaseModel):
    """生词本条目响应"""
    id: UUID
    word: str
    phonetic: str | None
    definition: str
    importance: int
    consecutive_correct: int
    correct_review_count: int
    review_count: int
    next_review_at: datetime
    last_review_at: datetime | None
    accuracy_rate: float
    part_of_speech: str | None = None
    source_translation_id: str | None = None
    context_sentence: str | None = None

    class Config:
        from_attributes = True


class VocabularyStats(BaseModel):
    """词汇统计"""
    total_words: int
    due_for_review: int
    accuracy_rate: float
    by_importance: dict[str, int]


# ============ Endpoints ============

@router.get("/lookup", summary="词典查询")
async def lookup_word(
    word: str = Query(..., min_length=1, max_length=100),
    db: AsyncSession = Depends(get_db)
):
    """
    查询单词释义

    首先查询本地数据库，如果未找到则回退到 MDX 词典（如果配置）。
    """
    # 1. 先查本地数据库
    entry = await vocabulary_service.lookup(db, word)
    if entry:
        return {
            "word": entry.word,
            "phonetic": entry.phonetic,
            "pos": entry.pos,
            "definitions": entry.definitions,
            "examples": entry.examples,
            "source": entry.source
        }

    # 2. 回退到 MDX 词典
    mdx = get_mdx_service()
    if mdx:
        mdx_result = mdx.lookup(word)
        if mdx_result:
            return mdx_result

    return await vocabulary_service.synthesize_lookup(word)


@router.post("/wordbook", summary="添加到生词本", response_model=WordBookResponse)
async def add_to_wordbook(
    data: WordBookAdd,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """添加单词到用户的生词本"""
    word_entry = await vocabulary_service.add_to_wordbook(
        db,
        current_user.id,
        word=data.word,
        definition=data.definition,
        phonetic=data.phonetic,
        context_sentence=data.context_sentence,
        task_id=data.task_id,
        importance=data.importance,
        part_of_speech=data.part_of_speech,
        source_translation_id=data.source_translation_id,
    )

    # 计算准确率
    accuracy_rate = (
        word_entry.correct_review_count / word_entry.review_count
        if word_entry.review_count > 0
        else 0.0
    )

    return WordBookResponse(
        id=word_entry.id,
        word=word_entry.word,
        phonetic=word_entry.phonetic,
        definition=word_entry.definition,
        importance=word_entry.importance,
        consecutive_correct=word_entry.consecutive_correct,
        correct_review_count=word_entry.correct_review_count,
        review_count=word_entry.review_count,
        next_review_at=word_entry.next_review_at,
        last_review_at=word_entry.last_review_at,
        accuracy_rate=accuracy_rate,
        part_of_speech=word_entry.part_of_speech,
        source_translation_id=word_entry.source_translation_id,
        context_sentence=word_entry.context_sentence,
    )


@router.get("/wordbook", summary="获取生词本列表", response_model=list[WordBookResponse])
async def get_wordbook(
    search: str | None = Query(None, max_length=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取当前用户的完整生词本列表。"""
    words = await vocabulary_service.get_wordbook(db, current_user.id, search=search)

    result = []
    for word_entry in words:
        accuracy_rate = (
            word_entry.correct_review_count / word_entry.review_count
            if word_entry.review_count > 0
            else 0.0
        )
        result.append(WordBookResponse(
            id=word_entry.id,
            word=word_entry.word,
            phonetic=word_entry.phonetic,
            definition=word_entry.definition,
            importance=word_entry.importance,
            consecutive_correct=word_entry.consecutive_correct,
            correct_review_count=word_entry.correct_review_count,
            review_count=word_entry.review_count,
            next_review_at=word_entry.next_review_at,
            last_review_at=word_entry.last_review_at,
            accuracy_rate=accuracy_rate,
            part_of_speech=word_entry.part_of_speech,
            source_translation_id=word_entry.source_translation_id,
            context_sentence=word_entry.context_sentence,
        ))

    return result


@router.get("/wordbook/review", summary="获取复习列表", response_model=list[WordBookResponse])
async def get_review_list(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取需要复习的单词列表"""
    words = await vocabulary_service.get_review_list(db, current_user.id)

    result = []
    for word_entry in words:
        accuracy_rate = (
            word_entry.correct_review_count / word_entry.review_count
            if word_entry.review_count > 0
            else 0.0
        )
        result.append(WordBookResponse(
            id=word_entry.id,
            word=word_entry.word,
            phonetic=word_entry.phonetic,
            definition=word_entry.definition,
            importance=word_entry.importance,
            consecutive_correct=word_entry.consecutive_correct,
            correct_review_count=word_entry.correct_review_count,
            review_count=word_entry.review_count,
            next_review_at=word_entry.next_review_at,
            last_review_at=word_entry.last_review_at,
            accuracy_rate=accuracy_rate,
            part_of_speech=word_entry.part_of_speech,
            source_translation_id=word_entry.source_translation_id,
            context_sentence=word_entry.context_sentence,
        ))

    return result


@router.post("/wordbook/review", summary="记录复习结果", response_model=WordBookResponse)
async def record_review(
    data: ReviewRecord,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """记录单词复习结果"""
    word_entry = await vocabulary_service.record_review(
        db, data.word_id, data.remembered
    )

    if not word_entry:
        raise HTTPException(status_code=404, detail="Word not found")

    accuracy_rate = (
        word_entry.correct_review_count / word_entry.review_count
        if word_entry.review_count > 0
        else 0.0
    )

    return WordBookResponse(
        id=word_entry.id,
        word=word_entry.word,
        phonetic=word_entry.phonetic,
        definition=word_entry.definition,
        importance=word_entry.importance,
        consecutive_correct=word_entry.consecutive_correct,
        correct_review_count=word_entry.correct_review_count,
        review_count=word_entry.review_count,
        next_review_at=word_entry.next_review_at,
        last_review_at=word_entry.last_review_at,
        accuracy_rate=accuracy_rate,
        part_of_speech=word_entry.part_of_speech,
        source_translation_id=word_entry.source_translation_id,
        context_sentence=word_entry.context_sentence,
    )


@router.delete("/wordbook/{word_id}", summary="删除生词本条目")
async def delete_wordbook_entry(
    word_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除当前用户的某个生词本条目。"""
    deleted = await vocabulary_service.delete_wordbook_entry(
        db,
        current_user.id,
        word_id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Word not found")
    return {"deleted": True}


@router.patch("/wordbook/{word_id}/importance", summary="更新单词重要度", response_model=WordBookResponse)
async def update_importance(
    word_id: UUID,
    data: UpdateImportance,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新单词的重要度评级"""
    word_entry = await vocabulary_service.update_importance(
        db, word_id, data.importance
    )

    if not word_entry:
        raise HTTPException(status_code=404, detail="Word not found")

    accuracy_rate = (
        word_entry.correct_review_count / word_entry.review_count
        if word_entry.review_count > 0
        else 0.0
    )

    return WordBookResponse(
        id=word_entry.id,
        word=word_entry.word,
        phonetic=word_entry.phonetic,
        definition=word_entry.definition,
        importance=word_entry.importance,
        consecutive_correct=word_entry.consecutive_correct,
        correct_review_count=word_entry.correct_review_count,
        review_count=word_entry.review_count,
        next_review_at=word_entry.next_review_at,
        last_review_at=word_entry.last_review_at,
        accuracy_rate=accuracy_rate,
        part_of_speech=word_entry.part_of_speech,
        source_translation_id=word_entry.source_translation_id,
        context_sentence=word_entry.context_sentence,
    )


@router.get("/wordbook/stats", summary="获取词汇统计", response_model=VocabularyStats)
async def get_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取用户的词汇学习统计"""
    return await vocabulary_service.get_statistics(db, current_user.id)


@router.post("/import", summary="导入词典数据")
async def import_dictionary(
    format: str = Form("json"),
    source: str = Form("custom"),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    导入词典数据

    支持的格式:
    - JSON: [{"word": "...", "definitions": [...], "phonetic": "...", "pos": "..."}]
    - CSV: word,phonetic,pos,definitions,examples
    """
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
async def associate_word(word: str = Query(..., min_length=1, max_length=100)):
    """通过 LLM 获取相关词汇（同义词、反义词等）"""
    words = await vocabulary_service.get_word_associations(word)
    return {"associations": words}


@router.get("/llm/sentence", summary="例句生成")
async def generate_sentence(
    word: str = Query(..., min_length=1, max_length=100),
    context: str | None = Query(None, max_length=500)
):
    """通过 LLM 生成单词例句"""
    sentence = await vocabulary_service.generate_example_sentence(word, context)
    return {"sentence": sentence}


@router.get("/llm/polish", summary="释义润色")
async def polish_definition(
    word: str = Query(..., min_length=1, max_length=100),
    definition: str = Query(..., min_length=1, max_length=1000)
):
    """通过 LLM 润色单词释义"""
    polished = await vocabulary_service.polish_definition(word, definition)
    return {"polished": polished}
