"""
MiniMax M3 异步分析通道单测（mock 传输，零真实请求）。

覆盖面：
1. 请求形态：URL = {base}/text/chatcompletion_v2、Bearer 鉴权、payload 字段
2. 并发钳制：max_concurrency=8 时 8 个并发全部放行，峰值 in-flight == 8
3. 快速拒绝：第 9 个并发请求立即 MinimaxLaneBusyError，不排队等待
4. 错误处理：HTTP 5xx / 空 choices / 空 content → MinimaxLaneError
5. 消费点（错题分析）：_run_llm_analysis 优先走 MiniMax 车道，
   车道 busy 时降级主 LLM 通道，双车道全挂时走规则兜底
"""

import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.error_book_service import ErrorBookService
from app.services.llm.minimax_provider import (
    MinimaxLaneBusyError,
    MinimaxLaneError,
    MinimaxProvider,
)


def _ok_body(content: str = '{"ok": true}') -> dict:
    return {
        "choices": [
            {
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"total_tokens": 42},
    }


def _make_provider(handler, *, max_concurrency: int = 8) -> MinimaxProvider:
    return MinimaxProvider(
        api_key="test-key",
        base_url="https://mock.minimaxi.test/v1",
        model="MiniMax-M3",
        max_concurrency=max_concurrency,
        transport=httpx.MockTransport(handler),
    )


def _error_book_service() -> ErrorBookService:
    db_mock = MagicMock(spec=AsyncSession)
    return ErrorBookService(db_mock)


# ---------------------------------------------------------------------------
# 1. 请求形态
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_request_shape_and_content_parsing():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("Authorization")
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, json=_ok_body('{"error_type": "concept_confusion"}'))

    provider = _make_provider(handler)
    result = await provider.analyze(
        messages=[
            {"role": "system", "content": "You are an expert tutor."},
            {"role": "user", "content": "分析这道错题"},
        ],
        max_tokens=700,
        response_format={"type": "json_object"},
    )

    assert result == '{"error_type": "concept_confusion"}'
    # OpenAI 兼容端点：{base}/text/chatcompletion_v2
    assert captured["url"] == "https://mock.minimaxi.test/v1/text/chatcompletion_v2"
    assert captured["auth"] == "Bearer test-key"
    payload = captured["payload"]
    assert payload["model"] == "MiniMax-M3"
    assert payload["messages"][0]["content"] == "You are an expert tutor."
    # 安全模式开启时 user 内容会被 <USER_INPUT> 包裹，但原文必须保留
    assert "分析这道错题" in payload["messages"][1]["content"]
    assert payload["max_tokens"] == 700
    assert payload["response_format"] == {"type": "json_object"}
    assert payload.get("stream") is not True  # 异步分析非流式


@pytest.mark.asyncio
async def test_reasoning_content_field_is_ignored_content_wins():
    """M3 是推理模型：reasoning_content 单独返回，lane 只取最终 content。"""

    def handler(request: httpx.Request) -> httpx.Response:
        body = _ok_body('{"final": true}')
        body["choices"][0]["message"]["reasoning_content"] = "让我想想……"
        return httpx.Response(200, json=body)

    provider = _make_provider(handler)
    result = await provider.analyze(messages=[{"role": "user", "content": "q"}])
    assert result == '{"final": true}'


# ---------------------------------------------------------------------------
# 2. 并发钳制到 8
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_concurrency_clamped_to_max():
    peak_in_flight = 0
    in_flight = 0
    started = asyncio.Event()
    release = asyncio.Event()
    completed = 0

    async def _slow(_request: httpx.Request) -> httpx.Response:
        nonlocal peak_in_flight, in_flight, completed
        in_flight += 1
        peak_in_flight = max(peak_in_flight, in_flight)
        if in_flight >= 8:
            started.set()
        try:
            await release.wait()
        finally:
            in_flight -= 1
            completed += 1
        return httpx.Response(200, json=_ok_body())

    provider = _make_provider(_slow, max_concurrency=8)

    tasks = [asyncio.create_task(provider.analyze(messages=[{"role": "user", "content": f"q{i}"}])) for i in range(8)]
    # 8 个请求应全部在途（钳制上限 == 8），而不是拒绝
    await asyncio.wait_for(started.wait(), timeout=2.0)
    assert peak_in_flight == 8
    assert provider.stats()["active"] == 8

    release.set()
    results = await asyncio.gather(*tasks)
    assert len(results) == 8
    assert all(r == '{"ok": true}' for r in results)
    assert peak_in_flight == 8  # 全程从未超过 8
    assert provider.stats()["active"] == 0
    assert provider.stats()["rejected_busy"] == 0


# ---------------------------------------------------------------------------
# 3. 第 9 个快速拒绝（不排队）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ninth_call_fast_rejects_without_queueing():
    started = asyncio.Event()
    release = asyncio.Event()
    in_flight = 0

    async def _slow(_request: httpx.Request) -> httpx.Response:
        nonlocal in_flight
        in_flight += 1
        if in_flight >= 8:
            started.set()
        await release.wait()
        in_flight -= 1
        return httpx.Response(200, json=_ok_body())

    provider = _make_provider(_slow, max_concurrency=8)

    busy_tasks = [
        asyncio.create_task(provider.analyze(messages=[{"role": "user", "content": f"q{i}"}])) for i in range(8)
    ]
    await asyncio.wait_for(started.wait(), timeout=2.0)

    # 第 9 个：立即拒绝，不允许排队（耗时远小于任何排队等待）
    reject_start = time.perf_counter()
    with pytest.raises(MinimaxLaneBusyError):
        await provider.analyze(messages=[{"role": "user", "content": "overflow"}])
    elapsed = time.perf_counter() - reject_start
    assert elapsed < 0.5  # 快速拒绝，无排队

    stats = provider.stats()
    assert stats["rejected_busy"] == 1
    assert stats["active"] == 8  # 原 8 个不受影响

    release.set()
    await asyncio.gather(*busy_tasks)

    # 车道释放后新请求可再次进入
    def _ok(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_ok_body("recovered"))

    provider._transport = httpx.MockTransport(_ok)
    assert await provider.analyze(messages=[{"role": "user", "content": "next"}]) == "recovered"


@pytest.mark.asyncio
async def test_busy_rejection_does_not_leak_slot():
    """快速拒绝路径不得占用/泄漏槽位：单槽被占时拒绝，释放后立即可用。"""

    started = asyncio.Event()
    release = asyncio.Event()

    async def _slow(_request: httpx.Request) -> httpx.Response:
        started.set()
        await release.wait()
        return httpx.Response(200, json=_ok_body())

    def _ok(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_ok_body("after release"))

    provider = _make_provider(_slow, max_concurrency=1)
    holder = asyncio.create_task(provider.analyze(messages=[{"role": "user", "content": "hold"}]))
    await asyncio.wait_for(started.wait(), timeout=2.0)

    with pytest.raises(MinimaxLaneBusyError):
        await provider.analyze(messages=[{"role": "user", "content": "reject me"}])

    provider._transport = httpx.MockTransport(_ok)
    release.set()
    assert await holder == '{"ok": true}'

    # 拒绝路径未泄漏槽位：车道空闲后新请求立即通过
    assert await provider.analyze(messages=[{"role": "user", "content": "b"}]) == "after release"
    assert provider.stats()["active"] == 0


# ---------------------------------------------------------------------------
# 4. 错误处理
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_http_500_raises_lane_error():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    provider = _make_provider(handler)
    with pytest.raises(MinimaxLaneError):
        await provider.analyze(messages=[{"role": "user", "content": "q"}])
    assert provider.stats()["active"] == 0  # 出错也必须释放槽位


@pytest.mark.asyncio
async def test_rate_limit_429_raises_lane_error():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": "rate limited"})

    provider = _make_provider(handler)
    with pytest.raises(MinimaxLaneError):
        await provider.analyze(messages=[{"role": "user", "content": "q"}])


@pytest.mark.asyncio
async def test_empty_choices_raises_lane_error():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})

    provider = _make_provider(handler)
    with pytest.raises(MinimaxLaneError):
        await provider.analyze(messages=[{"role": "user", "content": "q"}])


@pytest.mark.asyncio
async def test_empty_content_raises_lane_error():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_ok_body(""))

    provider = _make_provider(handler)
    with pytest.raises(MinimaxLaneError):
        await provider.analyze(messages=[{"role": "user", "content": "q"}])


@pytest.mark.asyncio
async def test_lane_error_releases_slot_for_next_caller():
    calls = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(500, json={"error": "boom"})
        return httpx.Response(200, json=_ok_body("fine"))

    provider = _make_provider(handler, max_concurrency=2)
    with pytest.raises(MinimaxLaneError):
        await provider.analyze(messages=[{"role": "user", "content": "fail"}])
    # 槽位已释放，后续请求正常
    assert await provider.analyze(messages=[{"role": "user", "content": "ok"}]) == "fine"
    assert provider.stats()["active"] == 0


# ---------------------------------------------------------------------------
# 5. 配置
# ---------------------------------------------------------------------------


def test_settings_expose_minimax_lane_config():
    assert settings.MINIMAX_MAX_CONCURRENCY == 8
    assert settings.MINIMAX_BASE_URL == "https://api.minimaxi.com/v1"
    assert settings.MINIMAX_CHAT_MODEL == "MiniMax-M3"


def test_provider_from_settings_uses_lane_defaults():
    provider = MinimaxProvider.from_settings()
    assert provider.model == settings.MINIMAX_CHAT_MODEL
    assert provider.max_concurrency == settings.MINIMAX_MAX_CONCURRENCY


# ---------------------------------------------------------------------------
# 6. 消费点：错题 analyze 后台任务
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_error_book_analysis_prefers_minimax_lane():
    """B 线 2026-09-22（BATCH_LLM_PROVIDER 开关）：本用例验证 minimax 档契约，
    快照钉 BATCH_LLM_PROVIDER=minimax；glm 回滚位契约见
    test_batch_llm_provider_switch.py::TestErrorBookDirectLaneGating。"""
    service = _error_book_service()
    with (
        patch.object(settings, "BATCH_LLM_PROVIDER", "minimax"),
        patch("app.services.error_book_service.minimax_provider") as mock_lane,
        patch("app.services.error_book_service.llm_client") as mock_llm,
    ):
        mock_lane.analyze = AsyncMock(return_value='{"error_type": "concept_confusion"}')
        result = await service._run_llm_analysis("math", "1+1=?", "3", "2", [])
    assert result["error_type"] == "concept_confusion"
    mock_lane.analyze.assert_awaited_once()
    mock_llm.chat_completion.assert_not_called()  # 车道可用时不烧主通道


@pytest.mark.asyncio
async def test_error_book_analysis_falls_back_to_primary_lane_on_busy():
    service = _error_book_service()
    with (
        patch.object(settings, "BATCH_LLM_PROVIDER", "minimax"),
        patch("app.services.error_book_service.minimax_provider") as mock_lane,
        patch("app.services.error_book_service.llm_client") as mock_llm,
    ):
        mock_lane.analyze = AsyncMock(side_effect=MinimaxLaneBusyError("lane full"))
        mock_llm.chat_completion = AsyncMock(return_value='{"error_type": "calculation_error"}')
        result = await service._run_llm_analysis("math", "1+1=?", "3", "2", [])
    assert result["error_type"] == "calculation_error"
    mock_llm.chat_completion.assert_awaited_once()


@pytest.mark.asyncio
async def test_error_book_analysis_rule_fallback_when_both_lanes_fail():
    service = _error_book_service()
    with (
        patch.object(settings, "BATCH_LLM_PROVIDER", "minimax"),
        patch("app.services.error_book_service.minimax_provider") as mock_lane,
        patch("app.services.error_book_service.llm_client") as mock_llm,
    ):
        mock_lane.analyze = AsyncMock(side_effect=MinimaxLaneError("down"))
        mock_llm.chat_completion = AsyncMock(side_effect=RuntimeError("primary down"))
        result = await service._run_llm_analysis("math", "1+1=?", "3", "2", [])
    # 双车道全挂 → 规则兜底，绝不抛出
    assert "error_type" in result
