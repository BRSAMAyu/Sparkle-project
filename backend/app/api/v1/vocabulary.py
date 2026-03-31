"""
生词本与词典 API
Vocabulary & Dictionary API
"""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config.settings import settings
from app.services.dictionary_package_service import dictionary_package_service
from app.db.session import get_db
from app.models.user import User
from app.services.mdx_dictionary_service import create_mdx_service
from app.services.vocabulary_service import vocabulary_service
from app.utils.helpers import read_upload_file

router = APIRouter()

# 全局 MDX 服务实例
_mdx_service = None


def _external_base_url(request: Request) -> str:
    """Build a client-reachable base URL behind the gateway/proxy."""
    if settings.DICTIONARY_PACKAGE_BASE_URL:
        return settings.DICTIONARY_PACKAGE_BASE_URL.rstrip("/")

    gateway_base = getattr(settings, "GATEWAY_INTERNAL_URL", "") or ""
    if gateway_base.startswith(("http://", "https://")):
        return gateway_base.rstrip("/")

    forwarded_proto = request.headers.get("x-forwarded-proto")
    forwarded_host = request.headers.get("x-forwarded-host")
    forwarded_prefix = request.headers.get("x-forwarded-prefix", "").rstrip("/")

    scheme = forwarded_proto or request.url.scheme
    host = forwarded_host or request.headers.get("host") or request.url.netloc

    if host:
        return f"{scheme}://{host}{forwarded_prefix}".rstrip("/")

    return str(request.base_url).rstrip("/")


def get_mdx_service():
    """获取或初始化 MDX 词典服务"""
    global _mdx_service
    if _mdx_service is None:
        if not settings.MDX_DICTIONARY_ENABLED:
            return None
        mdx_path = getattr(settings, 'MDX_DICTIONARY_PATH', None)
        if not mdx_path:
            candidates: list[Path] = []
            package_dir = getattr(settings, "DICTIONARY_PACKAGE_DIR", None)
            if package_dir:
                candidates.append(Path(package_dir).resolve().parent / "oaldpe.mdx")
            current_path = Path(__file__).resolve()
            for parent_index in (3, 4):
                if len(current_path.parents) > parent_index:
                    candidates.append(current_path.parents[parent_index] / "data" / "dictionaries" / "oaldpe.mdx")
            for candidate in candidates:
                if candidate.exists():
                    mdx_path = str(candidate)
                    break
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

    model_config = ConfigDict(from_attributes=True)


class VocabularyStats(BaseModel):
    """词汇统计"""
    total_words: int
    due_for_review: int
    accuracy_rate: float
    by_importance: dict[str, int]


class DictionaryPackageInfo(BaseModel):
    id: str
    name: str
    version: str
    description: str
    package_scope: str
    source: str
    format: str
    entry_count: int
    size_bytes: int | None = None
    sha256: str | None = None
    generated_at: str | None = None
    download_available: bool
    download_url: str


# ============ Endpoints ============

@router.get("/lookup", summary="词典查询")
async def lookup_word(
    word: str = Query(..., min_length=1, max_length=100),
    db: AsyncSession = Depends(get_db)
):
    """
    查询单词释义

    优先查询 Oxford MDX 词典；若未命中，再查本地数据库，最后回退到 LLM 合成释义。
    """
    normalized_word = word.strip().lower()

    # 1. 优先查 MDX 词典（Oxford 数据）
    mdx = get_mdx_service()
    if mdx:
        mdx_result = mdx.lookup(normalized_word)
        if mdx_result:
            return mdx_result

    packaged_fallback = dictionary_package_service.lookup_fallback_entry(normalized_word)
    if packaged_fallback:
        return packaged_fallback

    # 2. 再查数据库镜像/导入词典
    entry = await vocabulary_service.lookup(db, normalized_word)
    if entry:
        return {
            "word": entry.word,
            "phonetic": entry.phonetic,
            "pos": entry.pos,
            "definitions": entry.definitions,
            "examples": entry.examples,
            "source": entry.source,
        }

    # 3. 最后回退到 LLM
    return await vocabulary_service.synthesize_lookup(normalized_word)


@router.get("/dictionary/packages", summary="获取离线词典包", response_model=list[DictionaryPackageInfo])
async def list_dictionary_packages(request: Request):
    download_path_template = request.app.url_path_for(
        "download_dictionary_package",
        package_id="__PACKAGE_ID__",
    )
    external_base = _external_base_url(request)
    packages = []
    for package in dictionary_package_service.list_packages():
        download_path = str(download_path_template).replace("__PACKAGE_ID__", package["id"])
        packages.append(
            DictionaryPackageInfo(
                **package,
                download_url=f"{external_base}{download_path}",
            )
        )
    return packages


@router.get(
    "/dictionary/packages/{package_id}/download",
    summary="下载离线词典包",
    name="download_dictionary_package",
)
async def download_dictionary_package(package_id: str):
    try:
        package_path = dictionary_package_service.ensure_package(package_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Dictionary package unavailable: {exc}")

    return FileResponse(
        path=package_path,
        media_type="application/gzip",
        filename=package_path.name,
    )


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
    limit: int = Query(
        vocabulary_service.DEFAULT_REVIEW_BATCH_SIZE,
        ge=1,
        le=200,
        description="Maximum number of due words to return",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取需要复习的单词列表"""
    words = await vocabulary_service.get_review_list(db, current_user.id, limit=limit)

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
