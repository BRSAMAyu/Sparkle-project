"""
翻译 API
Translation API - 使用统一翻译工具进行多语言翻译

支持分片翻译、领域术语、缓存和信号评估
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db
from app.tools.translation_tool import TranslateTextParams, TranslateTextTool, _normalize_language_code

router = APIRouter()

# ============ Schemas ============

class TranslateRequest(BaseModel):
    """翻译请求 - 支持Flutter和通用客户端"""
    text: str = Field(..., description="需要翻译的文本", max_length=5000)
    # 支持两种参数命名风格
    source_lang: str | None = Field(default="auto", description="源语言代码 (如: en, zh, auto)")
    source_language: str | None = Field(default=None, description="源语言 (兼容字段)")
    target_lang: str | None = Field(default="zh-CN", description="目标语言代码 (如: en, zh-CN)")
    target_language: str | None = Field(default=None, description="目标语言 (兼容字段)")
    # 高级参数
    domain: str = Field(default="general", description="领域: cs, math, business, general")
    style: str = Field(default="natural", description="风格: concise, literal, natural")
    glossary_id: str | None = Field(default=None, description="术语表ID")
    # 信号参数
    fingerprint: str | None = Field(default=None, description="内容指纹用于去重")
    context_before: str | None = Field(default=None, description="选择前的上下文")
    context_after: str | None = Field(default=None, description="选择后的上下文")
    page_no: int | None = Field(default=None, description="页码")
    source_file_id: str | None = Field(default=None, description="源文件ID")

    model_config = ConfigDict(extra="allow")

    def get_normalized_params(self) -> dict[str, Any]:
        """获取标准化后的参数"""
        # 如果 source_lang 是默认值 "auto" 且提供了 source_language，则使用 source_language
        source = self.source_lang
        if source == "auto" and self.source_language:
            source = self.source_language

        # 如果 target_lang 是默认值 "zh-CN" 且提供了 target_language，则使用 target_language
        target = self.target_lang
        if target == "zh-CN" and self.target_language:
            target = self.target_language

        return {
            "source_lang": source or "auto",
            "target_lang": target or "zh-CN",
        }


class TranslationSegmentData(BaseModel):
    """翻译片段数据"""
    id: str
    translation: str
    notes: list[str] = []


class TranslationRecommendation(BaseModel):
    """翻译推荐数据"""
    should_create_card: bool = False
    reason: str | None = None
    daily_quota_remaining: int = 0


class TranslateResponse(BaseModel):
    """翻译响应 - 匹配Flutter期望格式"""
    success: bool
    translation: str | None = None
    segments: list[TranslationSegmentData] = []
    recommendation: TranslationRecommendation | None = None
    meta: dict[str, Any] = {}

# ============ Endpoints ============

@router.post("/translate", response_model=TranslateResponse, summary="文本翻译")
async def translate_text(
    request: TranslateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    使用统一翻译工具进行文本翻译

    - **text**: 需要翻译的文本（最多5000字符）
    - **source_lang/source_language**: 源语言代码（如: en, zh, auto）
    - **target_lang/target_language**: 目标语言代码（如: en, zh-CN）
    - **domain**: 领域术语 (cs, math, business, general)
    - **style**: 翻译风格 (concise, literal, natural)
    - **glossary_id**: 术语表ID (如: cs_terms_v1)
    - **fingerprint**: 内容指纹用于信号追踪

    示例：
    - 英译中：source_lang="en", target_lang="zh-CN"
    - 中译英：source_lang="zh-CN", target_lang="en"
    - 计算机领域：domain="cs", glossary_id="cs_terms_v1"
    """
    try:
        # 标准化语言参数
        normalized = request.get_normalized_params()
        source_lang = _normalize_language_code(normalized["source_lang"])
        target_lang = _normalize_language_code(normalized["target_lang"])

        # 创建翻译工具实例
        tool = TranslateTextTool()

        # 创建参数 - 使用 Pydantic 模型正确实例化
        params = TranslateTextParams(
            text=request.text,
            source_lang=source_lang,
            target_lang=target_lang,
            domain=request.domain,
            style=request.style,
            glossary_id=request.glossary_id,
            fingerprint=request.fingerprint,
        )

        # 执行翻译（需要 db 用于信号评估）
        result = await tool.execute(
            params=params,
            user_id=user_id,
            db_session=db,
        )

        if result.success:
            # 构建响应元数据
            meta = {
                "source_lang": result.data.get("source_lang", source_lang),
                "target_lang": result.data.get("target_lang", target_lang),
                "provider": result.data.get("provider", "unknown"),
                "cache_hit": result.data.get("cache_hit", False),
                "latency_ms": result.data.get("latency_ms", 0),
                "domain": request.domain,
                "style": request.style,
            }

            # 构建片段列表
            segments_data = result.data.get("segments", [])
            segments = [
                TranslationSegmentData(
                    id=seg.get("id", ""),
                    translation=seg.get("translation", ""),
                    notes=seg.get("notes", []),
                )
                for seg in segments_data
            ]

            # 构建推荐数据
            recommendation = None
            recommendation_data = result.data.get("recommendation")
            if recommendation_data:
                recommendation = TranslationRecommendation(
                    should_create_card=recommendation_data.get("should_create_card", False),
                    reason=recommendation_data.get("reason"),
                    daily_quota_remaining=recommendation_data.get("daily_quota_remaining", 0),
                )

            return TranslateResponse(
                success=True,
                translation=result.data.get("translation", ""),
                segments=segments,
                recommendation=recommendation,
                meta=meta,
            )
        else:
            return TranslateResponse(
                success=False,
                segments=[],
                meta={
                    "error": result.error_message or "Translation failed",
                },
            )

    except Exception as e:
        from loguru import logger as log
        log.warning("Translation endpoint error: {} — {}", type(e).__name__, e)
        raise HTTPException(
            status_code=500,
            detail=f"Translation service unavailable: {type(e).__name__}",
        )


@router.get("/languages", summary="支持的语言列表")
async def get_supported_languages():
    """
    获取支持的语言列表
    """
    return {
        "languages": [
            {"code": "auto", "name": "自动检测"},
            {"code": "zh", "name": "中文"},
            {"code": "zh-CN", "name": "中文（简体）"},
            {"code": "en", "name": "English"},
            {"code": "ja", "name": "日本語"},
            {"code": "ko", "name": "한국어"},
            {"code": "fr", "name": "Français"},
            {"code": "de", "name": "Deutsch"},
            {"code": "es", "name": "Español"},
            {"code": "ru", "name": "Русский"},
            {"code": "pt", "name": "Português"},
            {"code": "it", "name": "Italiano"},
            {"code": "nl", "name": "Nederlands"},
            {"code": "ar", "name": "العربية"},
        ]
    }


@router.get("/glossaries", summary="获取可用的术语表")
async def get_glossaries():
    """
    获取可用的术语表列表
    """
    return {
        "glossaries": [
            {
                "id": "cs_terms_v1",
                "name": "计算机术语",
                "description": "Common computer science terminology",
                "domain": "cs",
                "terms_count": 11,
            },
            # 未来可以添加更多术语表
        ]
    }
