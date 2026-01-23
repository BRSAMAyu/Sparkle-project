"""
翻译 API
Translation API - 使用混元模型进行多语言翻译
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import get_current_user_id
from app.tools.focus_tools import HunyuanTranslateTool
from app.tools.schemas import TranslateParams

router = APIRouter()

# ============ Schemas ============

class TranslateRequest(BaseModel):
    """翻译请求"""
    text: str = Field(..., description="需要翻译的文本", max_length=5000)
    target_language: str = Field(..., description="目标语言", examples=["中文", "English", "日本語"])
    source_language: str = Field(default="auto", description="源语言，默认为自动检测")

class TranslateResponse(BaseModel):
    """翻译响应"""
    success: bool
    original_text: str
    translated_text: Optional[str] = None
    source_language: str
    target_language: str
    error_message: Optional[str] = None

# ============ Endpoints ============

@router.post("/translate", response_model=TranslateResponse, summary="文本翻译")
async def translate_text(
    request: TranslateRequest,
    user_id: str = Depends(get_current_user_id),
):
    """
    使用混元 MT 模型进行文本翻译

    - **text**: 需要翻译的文本（最多5000字符）
    - **target_language**: 目标语言（如：中文、English、日本語）
    - **source_language**: 源语言，默认为自动检测

    示例：
    - 中译英：source_language="auto", target_language="English"
    - 英译中：source_language="auto", target_language="中文"
    """
    try:
        # 创建翻译工具实例
        tool = HunyuanTranslateTool()

        # 创建参数
        params = TranslateParams(
            text=request.text,
            target_language=request.target_language,
            source_language=request.source_language,
        )

        # 执行翻译（不需要 db_session，翻译工具不使用数据库）
        result = await tool.execute(
            params=params,
            user_id=user_id,
            db_session=None,
        )

        if result.success:
            return TranslateResponse(
                success=True,
                original_text=result.data.get("original_text", request.text),
                translated_text=result.data.get("translated_text"),
                source_language=result.data.get("source_language", request.source_language),
                target_language=result.data.get("target_language", request.target_language),
            )
        else:
            return TranslateResponse(
                success=False,
                original_text=request.text,
                source_language=request.source_language,
                target_language=request.target_language,
                error_message=result.error_message,
            )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"翻译服务错误: {str(e)}",
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
            {"code": "en", "name": "English"},
            {"code": "ja", "name": "日本語"},
            {"code": "ko", "name": "한국어"},
            {"code": "fr", "name": "Français"},
            {"code": "de", "name": "Deutsch"},
            {"code": "es", "name": "Español"},
            {"code": "ru", "name": "Русский"},
        ]
    }
