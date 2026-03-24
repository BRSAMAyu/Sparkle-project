from __future__ import annotations
"""
LLM Fallback Utilities - 统一的LLM降级工具

提供安全的LLM调用包装器，包含：
- 自动重试和降级
- 默认值返回
- 超时保护
- 错误日志记录

使用方式:
    from app.services.llm_fallback_utils import safe_llm_call, safe_llm_json_call

    # 简单调用
    result = await safe_llm_call(messages, fallback="默认响应")

    # JSON调用
    data = await safe_llm_json_call(messages, fallback={"key": "default"})
"""

import asyncio
import json
import re
from typing import Any

from loguru import logger

from app.services.llm_service import llm_service


class LLMFallbackError(Exception):
    """LLM降级后仍失败的异常"""
    pass


def _extract_json_payload(raw: str) -> str | None:
    """Extract a likely JSON payload from plain text or fenced markdown."""
    cleaned = (raw or "").strip().lstrip("\ufeff")
    if not cleaned:
        return None

    fenced_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
    if fenced_match:
        cleaned = fenced_match.group(1).strip()

    for start, end in (("[", "]"), ("{", "}")):
        start_idx = cleaned.find(start)
        end_idx = cleaned.rfind(end)
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            return cleaned[start_idx : end_idx + 1].strip()

    return cleaned or None


async def safe_llm_call(
    messages: list[dict[str, str]],
    fallback: str = "",
    timeout: float = 30.0,
    retry_count: int = 1,
    **kwargs
) -> str:
    """
    安全的LLM调用，带降级保护

    Args:
        messages: LLM消息列表
        fallback: 失败时返回的默认值
        timeout: 超时时间（秒）
        retry_count: 重试次数
        **kwargs: 传递给llm_service.chat的额外参数

    Returns:
        LLM响应或fallback值

    Example:
        result = await safe_llm_call(
            [{"role": "user", "content": "Hello"}],
            fallback="抱歉，服务暂时不可用"
        )
    """
    last_error = None

    for attempt in range(retry_count + 1):
        try:
            # 使用asyncio.wait_for添加超时保护
            result = await asyncio.wait_for(
                llm_service.chat(messages, **kwargs),
                timeout=timeout
            )
            return result
        except asyncio.TimeoutError:
            last_error = f"LLM call timed out after {timeout}s"
            logger.warning(f"[LLMFallback] Timeout (attempt {attempt + 1}/{retry_count + 1})")
        except Exception as e:
            last_error = str(e)
            logger.warning(
                f"[LLMFallback] Call failed (attempt {attempt + 1}/{retry_count + 1}): {e}"
            )

        # 如果不是最后一次尝试，等待后重试
        if attempt < retry_count:
            await asyncio.sleep(0.5 * (attempt + 1))

    # 所有尝试都失败，返回fallback
    logger.error(f"[LLMFallback] All attempts failed, using fallback. Last error: {last_error}")
    return fallback


async def safe_llm_json_call(
    messages: list[dict[str, str]],
    fallback: dict[str, Any] | list[Any] | None = None,
    timeout: float = 30.0,
    retry_count: int = 1,
    **kwargs
) -> dict[str, Any] | list[Any] | None:
    """
    安全的LLM JSON调用，带降级保护

    Args:
        messages: LLM消息列表
        fallback: 失败时返回的默认值
        timeout: 超时时间（秒）
        retry_count: 重试次数
        **kwargs: 传递给llm_service.chat的额外参数

    Returns:
        解析后的JSON或fallback值

    Example:
        data = await safe_llm_json_call(
            [{"role": "user", "content": "Return JSON"}],
            fallback={"status": "error"}
        )
    """
    response = await safe_llm_call(
        messages,
        fallback="",  # 空字符串作为中间fallback
        timeout=timeout,
        retry_count=retry_count,
        **kwargs
    )

    if not response:
        return fallback

    json_payload = _extract_json_payload(response)
    if not json_payload:
        return fallback

    # 尝试解析JSON
    try:
        return json.loads(json_payload)
    except json.JSONDecodeError:
        logger.warning(f"[LLMFallback] Failed to parse JSON from response: {response[:100]}...")
        return fallback


async def safe_llm_chat(
    prompt: str,
    system_prompt: str | None = None,
    fallback: str = "",
    timeout: float = 30.0,
    **kwargs
) -> str:
    """
    简化的安全LLM聊天接口

    Args:
        prompt: 用户提示
        system_prompt: 系统提示（可选）
        fallback: 失败时的默认响应
        timeout: 超时时间
        **kwargs: 额外参数

    Returns:
        LLM响应或fallback
    """
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    return await safe_llm_call(messages, fallback=fallback, timeout=timeout, **kwargs)


class LLMFallbackWrapper:
    """
    LLM降级包装器类

    为特定服务提供可复用的降级逻辑

    Example:
        wrapper = LLMFallbackWrapper(
            service_name="VocabularyService",
            default_fallback="服务暂时不可用"
        )
        result = await wrapper.call(messages)
    """

    def __init__(
        self,
        service_name: str,
        default_fallback: str = "",
        default_json_fallback: dict[str, Any] | None = None,
        timeout: float = 30.0,
        retry_count: int = 1
    ):
        self.service_name = service_name
        self.default_fallback = default_fallback
        self.default_json_fallback = default_json_fallback or {}
        self.timeout = timeout
        self.retry_count = retry_count

    async def call(
        self,
        messages: list[dict[str, str]],
        fallback: str | None = None,
        **kwargs
    ) -> str:
        """安全调用LLM"""
        return await safe_llm_call(
            messages,
            fallback=fallback or self.default_fallback,
            timeout=self.timeout,
            retry_count=self.retry_count,
            **kwargs
        )

    async def json_call(
        self,
        messages: list[dict[str, str]],
        fallback: dict[str, Any] | None = None,
        **kwargs
    ) -> dict[str, Any] | None:
        """安全调用LLM并返回JSON"""
        return await safe_llm_json_call(
            messages,
            fallback=fallback or self.default_json_fallback,
            timeout=self.timeout,
            retry_count=self.retry_count,
            **kwargs
        )

    async def chat(
        self,
        prompt: str,
        system_prompt: str | None = None,
        fallback: str | None = None,
        **kwargs
    ) -> str:
        """简化的聊天接口"""
        return await safe_llm_chat(
            prompt,
            system_prompt=system_prompt,
            fallback=fallback or self.default_fallback,
            timeout=self.timeout,
            **kwargs
        )


# 预定义的服务包装器实例
vocabulary_llm = LLMFallbackWrapper(
    service_name="VocabularyService",
    default_fallback="词典服务暂时不可用",
    default_json_fallback={"word": "", "definitions": [], "examples": []}
)

analysis_llm = LLMFallbackWrapper(
    service_name="AnalysisService",
    default_fallback="分析服务暂时不可用",
    default_json_fallback={"analysis": None, "confidence": 0.0}
)

omnibar_llm = LLMFallbackWrapper(
    service_name="OmniBarService",
    default_fallback="",
    default_json_fallback={"type": "CHAT"}  # 默认回退到聊天模式
)

summarization_llm = LLMFallbackWrapper(
    service_name="SummarizationService",
    default_fallback="",
    default_json_fallback={"summary": ""}
)

stt_llm = LLMFallbackWrapper(
    service_name="STTService",
    default_fallback="",  # STT增强失败返回原文
    timeout=10.0  # STT增强需要更快的响应
)

# 新增服务包装器
preferences_llm = LLMFallbackWrapper(
    service_name="PreferencesService",
    default_fallback="[预览生成失败，请稍后重试]",
    timeout=15.0  # 偏好预览可以稍长
)

agent_llm = LLMFallbackWrapper(
    service_name="SpecialistAgent",
    default_fallback="抱歉，当前无法处理您的请求，请稍后重试。",
    timeout=45.0  # 专家智能体需要更长响应时间
)

cognitive_llm = LLMFallbackWrapper(
    service_name="CognitiveService",
    default_fallback="",
    default_json_fallback={
        "root_cause": "分析暂时不可用",
        "pattern_name": "Unknown Pattern",
        "confidence_score": 0.0
    },
    timeout=30.0
)

sufficiency_llm = LLMFallbackWrapper(
    service_name="SufficiencyChecker",
    default_fallback="",
    default_json_fallback={"specific": True},  # 默认认为足够具体
    timeout=10.0  # 充分性检查需要快速
)

router_llm = LLMFallbackWrapper(
    service_name="RequestRouter",
    default_fallback="chat",  # 降级到默认聊天
    timeout=5.0  # 路由需要非常快
)

# 新增服务包装器
focus_llm = LLMFallbackWrapper(
    service_name="FocusService",
    default_fallback="继续专注，你做得很好！",
    default_json_fallback={"subtasks": []},  # 任务拆解降级
    timeout=15.0
)

search_llm = LLMFallbackWrapper(
    service_name="SearchAgent",
    default_fallback="搜索结果摘要暂时不可用。",
    timeout=10.0
)

plan_llm = LLMFallbackWrapper(
    service_name="PlanTools",
    default_fallback="",
    default_json_fallback=[],  # 计划生成降级返回空列表
    timeout=30.0
)

hyde_llm = LLMFallbackWrapper(
    service_name="HyDE",
    default_fallback="",  # HyDE 失败时返回空，使用原始查询
    timeout=1.5  # HyDE 需要非常快，有严格延迟预算
)
