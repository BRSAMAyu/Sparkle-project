"""
MiniMax M3 异步分析通道（async analysis lane）。

定位（与主聊天路由严格分离）：
- 主聊天（用户直面、实时流式）走 qwen/dashscope 等主力通道，**永不**路由到本车道；
- 本车道只承接后台/离线、非用户直面的分析类任务（错题分析、离线摘要、批量质检等），
  跑在 MiniMax token plan 免费档（MiniMax-M3）上，换Token成本为零；
- 端点为 OpenAI 兼容 chat completions：``{base}/text/chatcompletion_v2``。

并发语义（DIST-SEMAPHORE 口径校正，依据 v3-output/MINIMAX-QUOTA）：
- MiniMax 官方按**账户**（主+子账号共享）限 RPM/TPM——免费 20 RPM / 1M TPM，
  充值 200 RPM / 10M TPM，**无文档化并发数**；
- 全局 semaphore 钳制（``MINIMAX_MAX_CONCURRENCY``，默认 8）是进程内自保护阀，
  非官方配额口径；跨进程 RPM 预算收敛见 ``MINIMAX_RPM_BUDGET``（llm_concurrency
  acquire 路径前置，本直连 lane 不经过该路径）；
- **快速拒绝、不排队**：车道满时调用方立即收到 :class:`MinimaxLaneBusyError`，
  而不是排队等待——异步任务应由消费方决定「现在降级」还是「下个周期重试」，
  排队只会把免费车道的拥堵传染给调用方的事件循环。

降级契约：消费方应捕获 ``MinimaxLaneBusyError`` / ``MinimaxLaneError`` 并回落到
主 LLM 通道（如 ``llm_client``）或规则兜底；本模块只负责车道本身。
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
from loguru import logger

from app.config import settings
from app.core.llm_secure_io import sanitize_llm_output, secure_messages

# 兼容端点路径：MiniMax 与 OpenAI 请求/响应形态兼容，但路径不同（非 /chat/completions）
CHAT_COMPLETIONS_PATH = "/text/chatcompletion_v2"


class MinimaxLaneBusyError(Exception):
    """车道并发已满（达到 MINIMAX_MAX_CONCURRENCY），快速拒绝、未排队。"""


class MinimaxLaneError(Exception):
    """车道请求失败（HTTP 5xx/429、超时、响应形态异常等）。"""


class MinimaxProvider:
    """
    MiniMax 异步分析车道客户端。

    通过 ``transport`` 注入 httpx Transport 以便单测 mock；
    生产代码直接使用模块级单例 :data:`minimax_provider`。
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        max_concurrency: int,
        transport: httpx.AsyncBaseTransport | None = None,
        output_sanitized: bool = True,
    ):
        self.api_key = api_key
        self.base_url = (base_url or "").rstrip("/")
        self.model = model
        self.max_concurrency = max(1, int(max_concurrency))
        self._transport = transport
        self._output_sanitized = output_sanitized

        # 并发钳制状态（跨 loop 安全：惰性绑定当前 running loop，
        # 重建时机参考 LLMConcurrencyManager._ensure_loop_state）
        self._semaphore: asyncio.Semaphore | None = None
        self._bound_loop: asyncio.AbstractEventLoop | None = None

        # 轻量运行统计（供观测/测试）
        self._active = 0
        self._total_requests = 0
        self._total_successes = 0
        self._total_errors = 0
        self._rejected_busy = 0

    @classmethod
    def from_settings(cls) -> MinimaxProvider:
        """从全局 settings 构建车道客户端。"""
        return cls(
            api_key=settings.MINIMAX_API_KEY,
            base_url=settings.MINIMAX_BASE_URL,
            model=settings.MINIMAX_CHAT_MODEL,
            max_concurrency=settings.MINIMAX_MAX_CONCURRENCY,
        )

    # ------------------------------------------------------------------
    # 并发钳制：全局 semaphore + 快速拒绝
    # ------------------------------------------------------------------

    def _get_semaphore(self) -> asyncio.Semaphore:
        loop = asyncio.get_running_loop()
        if self._semaphore is None or self._bound_loop is not loop:
            self._semaphore = asyncio.Semaphore(self.max_concurrency)
            self._bound_loop = loop
            self._active = 0
        return self._semaphore

    async def _acquire_nowait(self) -> asyncio.Semaphore:
        """
        原子地「有槽则占、无槽则拒」。

        ``locked()`` 检查与 ``acquire()`` 之间没有任何让位点（事件循环单线程
        协作式调度），因此不会与其它协程竞争：locked() 为 False 时 acquire()
        必然同步完成（信号量计数 > 0 且无等待者，acquire 不挂起）。
        """
        semaphore = self._get_semaphore()
        if semaphore.locked():
            self._rejected_busy += 1
            raise MinimaxLaneBusyError(
                f"MiniMax async lane is full (max_concurrency={self.max_concurrency}); " "fast-reject, not queueing"
            )
        await semaphore.acquire()
        return semaphore

    # ------------------------------------------------------------------
    # 分析请求
    # ------------------------------------------------------------------

    async def analyze(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.3,
        max_tokens: int | None = None,
        response_format: dict[str, str] | None = None,
        timeout_seconds: float = 45.0,
        user_id: str | None = None,
        wrap_user_messages: bool = False,
    ) -> str:
        """
        在异步分析车道上执行一次 chat completion，返回最终 content。

        Note:
            ``wrap_user_messages`` 默认关闭 ``<USER_INPUT>`` 注入防御信封
            （PII/密钥脱敏在两种模式下均生效）。实测 M3 对带信封的个别 prompt
            会返回空 content（去掉信封后同一 prompt 正常），而本车道消费者是
            内部服务拼装的分析 prompt，注入面远小于用户直面聊天，故默认不包信封。

        Raises:
            MinimaxLaneBusyError: 车道满，立即拒绝（调用方应降级或稍后重试）。
            MinimaxLaneError: 请求/响应失败（消费方应降级）。
        """
        semaphore = await self._acquire_nowait()
        self._active += 1
        self._total_requests += 1
        try:
            content = await self._request(
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
                timeout_seconds=timeout_seconds,
                user_id=user_id,
                wrap_user_messages=wrap_user_messages,
            )
            self._total_successes += 1
            return content
        except (MinimaxLaneBusyError, MinimaxLaneError):
            self._total_errors += 1
            raise
        except Exception as exc:
            self._total_errors += 1
            logger.error(f"[MinimaxLane] Unexpected error: {exc}")
            raise MinimaxLaneError(f"MiniMax async lane request failed: {exc}") from exc
        finally:
            self._active -= 1
            semaphore.release()

    async def _request(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float,
        max_tokens: int | None,
        response_format: dict[str, str] | None,
        timeout_seconds: float,
        user_id: str | None,
        wrap_user_messages: bool,
    ) -> str:
        # SEC-1 对齐：入参脱敏（两种模式下 PII/密钥脱敏均生效）/ 出参消毒
        safe_messages = secure_messages(
            messages,
            user_id=user_id,
            wrap_user_messages=wrap_user_messages,
        )

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": safe_messages,
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if response_format:
            payload["response_format"] = response_format

        url = f"{self.base_url}{CHAT_COMPLETIONS_PATH}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=timeout_seconds, transport=self._transport) as client:
                response = await client.post(url, headers=headers, json=payload)
        except httpx.TimeoutException as exc:
            raise MinimaxLaneError(f"MiniMax async lane timeout after {timeout_seconds}s") from exc
        except httpx.HTTPError as exc:
            raise MinimaxLaneError(f"MiniMax async lane transport error: {exc}") from exc

        if response.status_code >= 400:
            raise MinimaxLaneError(f"MiniMax async lane HTTP {response.status_code}: {response.text[:200]}")

        try:
            data = response.json()
            choices = data["choices"]
            message = choices[0]["message"]
        except Exception as exc:
            raise MinimaxLaneError(f"MiniMax async lane unexpected response shape: {data!r:.200}") from exc

        content = message.get("content")
        if not content:
            # M3 为推理模型：思维链在 reasoning_content，content 为空视为失败。
            # 常见诱因：max_tokens 被思维链耗尽（finish_reason=length）或
            # <USER_INPUT> 信封触发怪癖 —— 消费方应降级回主通道。
            finish_reason = choices[0].get("finish_reason")
            has_reasoning = bool(message.get("reasoning_content"))
            raise MinimaxLaneError(
                "MiniMax async lane returned empty content "
                f"(finish_reason={finish_reason}, has_reasoning_content={has_reasoning})"
            )

        if self._output_sanitized:
            return sanitize_llm_output(str(content), context={"type": "minimax_lane.analyze"})
        return str(content)

    # ------------------------------------------------------------------

    def stats(self) -> dict[str, int]:
        """车道运行统计（并发观测用）。"""
        return {
            "max_concurrency": self.max_concurrency,
            "active": self._active,
            "total_requests": self._total_requests,
            "total_successes": self._total_successes,
            "total_errors": self._total_errors,
            "rejected_busy": self._rejected_busy,
        }


# 模块级单例：全局唯一车道，并发钳制因此是全局的
minimax_provider = MinimaxProvider.from_settings()
