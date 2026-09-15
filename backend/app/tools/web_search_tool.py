"""
智谱联网搜索工具 (Web Search Tool)
使用 Zhipu GLM 官方搜索 API
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import httpx
from pydantic import BaseModel, Field

from app.config import settings

from .base import BaseTool, ToolCategory, ToolResult

_MAX_SEARCH_RESULT_LENGTH = 2000
_PROMPT_INJECTION_PATTERN = re.compile(
    r"(ignore\s+(previous|above|all)\s+instructions|system\s*prompt|you\s+are\s+a|"
    r"pretend\s+you\s+are|<\|.*?\||\[/?(INST|SYS|im_start|im_end)\])",
    re.IGNORECASE,
)

# ============ Schema ============

class WebSearchProParams(BaseModel):
    """智联网搜索参数 (使用 search_pro 高阶引擎)"""
    query: str = Field(..., description="搜索关键词，建议不超过 70 个字符以获得最佳效果", max_length=70)
    count: int = Field(default=10, description="返回结果数量 1-50", ge=1, le=50)
    recency_filter: str | None = Field(
        default="noLimit",
        description="时间范围: oneDay/oneWeek/oneMonth/oneYear/noLimit"
    )
    domain_filter: str | None = Field(None, description="限定搜索域名 (如: www.example.com)")
    content_size: str = Field(default="medium", description="内容长度: medium(摘要)/high(详细)")


# ============ Tool ============

class WebSearchProTool(BaseTool):
    """智谱联网搜索 - 使用 search_pro 高阶搜索引擎"""
    name = "web_search_pro"
    description = """
    使用智谱 search_pro 高阶搜索引擎进行联网搜索，获取最新信息。
    当用户询问时事新闻、最新数据、实时信息时使用此工具。
    建议搜索 query 不超过 70 个字符以获得最佳效果。
    """
    category = ToolCategory.QUERY
    parameters_schema = WebSearchProParams
    timeout_seconds = 30.0  # External API call, should complete quickly
    requires_confirmation = False

    API_URL = "https://open.bigmodel.cn/api/paas/v4/web_search"

    async def execute(
        self,
        params: WebSearchProParams,
        user_id: str,
        db_session: Any,
        tool_call_id: str | None = None
    ) -> ToolResult:
        if not settings.ZHIPU_API_KEY:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message="ZHIPU_API_KEY not configured",
                suggestion="请在环境变量中配置 ZHIPU_API_KEY"
            )

        headers = {
            "Authorization": f"Bearer {settings.ZHIPU_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "search_query": params.query,
            "search_engine": "search_pro",
            "search_intent": True,
            "count": params.count,
            "search_recency_filter": params.recency_filter,
            "content_size": params.content_size
        }

        if params.domain_filter:
            payload["search_domain_filter"] = params.domain_filter

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(self.API_URL, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()

            # 解析搜索结果 (sanitized)
            results = []
            if "search_result" in data:
                for item in data["search_result"]:
                    content = item.get("content", "")
                    if len(content) > _MAX_SEARCH_RESULT_LENGTH:
                        content = content[:_MAX_SEARCH_RESULT_LENGTH] + "..."
                    content = _PROMPT_INJECTION_PATTERN.sub("[filtered]", content)
                    title = _PROMPT_INJECTION_PATTERN.sub("[filtered]", item.get("title", ""))
                    results.append({
                        "title": title,
                        "content": content,
                        "link": item.get("link", ""),
                        "media": item.get("media", ""),
                        "refer": item.get("refer", ""),
                        "publish_date": item.get("publish_date", "")
                    })

            return ToolResult(
                success=True,
                tool_name=self.name,
                data={
                    "query": params.query,
                    "result_count": len(results),
                    "results": results,
                    "search_intent": data.get("search_intent", []),
                    "timestamp": datetime.now().isoformat()
                },
                widget_type="web_search_results",
                widget_data={
                    "query": params.query,
                    "results": results
                }
            )

        except httpx.HTTPStatusError as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=f"API 请求失败: {e.response.status_code}",
                suggestion=f"响应内容: {e.response.text[:200]}"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=f"搜索失败: {str(e)}",
                suggestion="请检查网络连接和 API 密钥配置"
            )
