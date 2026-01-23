from typing import Any, Optional
from uuid import UUID
from openai import AsyncOpenAI

from .base import BaseTool, ToolCategory, ToolResult
from .schemas import SuggestFocusSessionParams, TranslateParams
from app.models.task import Task
from app.services.llm_service import llm_service
from app.config import settings
from loguru import logger


class SuggestFocusSessionTool(BaseTool):
    """专注会话建议"""
    name = "suggest_focus_session"
    description = """生成一个可立即开始的专注冲刺卡片，可绑定到某个任务。"""
    category = ToolCategory.FOCUS
    parameters_schema = SuggestFocusSessionParams
    requires_confirmation = False

    async def execute(
        self,
        params: SuggestFocusSessionParams,
        user_id: str,
        db_session: Any,
        tool_call_id: Optional[str] = None
    ) -> ToolResult:
        try:
            task_data = None
            title = params.task_title or "专注冲刺"

            if params.task_id:
                task = await db_session.get(Task, UUID(params.task_id))
                if not task or str(task.user_id) != user_id:
                    return ToolResult(
                        success=False,
                        tool_name=self.name,
                        error_message="未找到对应任务",
                        suggestion="请确认任务是否存在或创建新的专注任务"
                    )

                title = task.title
                task_data = {
                    "id": str(task.id),
                    "title": task.title,
                    "type": task.type.value,
                    "status": task.status.value,
                    "estimated_minutes": task.estimated_minutes,
                    "priority": task.priority,
                    "difficulty": task.difficulty,
                    "energy_cost": task.energy_cost,
                    "tags": task.tags or [],
                    "created_at": task.created_at.isoformat(),
                    "updated_at": task.updated_at.isoformat(),
                }

            return ToolResult(
                success=True,
                tool_name=self.name,
                data={"duration_minutes": params.duration_minutes},
                widget_type="focus_card",
                widget_data={
                    "title": title,
                    "duration_minutes": params.duration_minutes,
                    "reason": "建议立即开始一段专注冲刺",
                    "task": task_data,
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=str(e),
                suggestion="请稍后再试或直接进入专注模式"
            )


class HunyuanTranslateTool(BaseTool):
    """翻译工具 - 使用混元模型"""
    name = "translate"
    description = """翻译文本到指定语言。支持多语言互译。
    当用户请求翻译时使用，例如：
    - "把这段英文翻译成中文"
    - "翻译成日语"
    - "中译英"
    """
    category = ToolCategory.QUERY
    parameters_schema = TranslateParams
    requires_confirmation = False

    async def execute(
        self,
        params: TranslateParams,
        user_id: str,
        db_session: Any,
        tool_call_id: Any = None
    ) -> ToolResult:
        try:
            # 构建翻译提示词
            if params.source_language == "auto":
                lang_instruction = f"翻译成{params.target_language}"
            else:
                lang_instruction = f"从{params.source_language}翻译成{params.target_language}"

            prompt = f"""请将以下文本{lang_instruction}。只输出翻译结果，不要添加任何解释或额外内容。

{params.text}"""

            # 使用混元模型进行翻译 - 直接调用API
            try:
                # Create OpenAI-compatible client for Hunyuan
                hunyuan_client = AsyncOpenAI(
                    api_key=settings.HUNYUAN_API_KEY,
                    base_url=settings.HUNYUAN_BASE_URL
                )

                response = await hunyuan_client.chat.completions.create(
                    model=settings.HUNYUAN_TRANSLATE_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3
                )

                translation = response.choices[0].message.content.strip()
            except Exception as api_error:
                logger.error(f"Hunyuan API error: {api_error}")
                # Fallback to the existing LLM service
                translation = await llm_service.chat(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3
                )

            return ToolResult(
                success=True,
                tool_name=self.name,
                data={
                    "original_text": params.text,
                    "translated_text": translation.strip(),
                    "source_language": params.source_language,
                    "target_language": params.target_language
                },
                widget_type="translation_result",
                widget_data={
                    "original": params.text,
                    "translation": translation.strip(),
                    "target_lang": params.target_language
                }
            )
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=str(e),
                suggestion="请检查文本内容或稍后重试"
            )
