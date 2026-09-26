"""V3-FIX-287（wt569）：demo_mode 短路「总括性」——无 user 角色消息形状不再落穿真实 provider。

缺陷（台账 287，wt567 猎缺轴 3 实证）：`_check_demo_match`（llm_service.py）的
实际判据是「demo_mode ∧ messages 存在非空 user 角色内容」——messages 无 user
角色行（工具续写类形状 [system, tool]）或最后一条 user 内容为空白时返回 None，
chat/reason 落穿 budget 与 provider 判空走真实调用（stream 的
``demo_mode and not provider`` 兜底只覆盖无 provider 面）；随后
persistence_layer._persist_assistant_message 与 REST save_chat_message 按落库
时刻的全局 demo_mode 把真实产出标 origin=DEMO，memory_inferred_write_lane
读同判据整轮跳过——真实模型产出被误标并静默退出记忆推断（内容损失）。

修法（候选 a，侵入最小）：`_check_demo_match` 在 user_content 为空时也返回
通用演示回复，恢复 V3-FIX-258 两条读侧判据依赖的不变式「demo_mode 置位 ⇒
一切回复均为 provider 调用前的脚本短路」。origin 落库判据与 lane 跳过判据
零改动即恢复语义正确，无需生成侧逐响应回传（候选 b）的跨层接线。

可证伪判据（本文件钉死）：settings.DEMO_MODE=true + stub provider
（has_api_key=True），messages=[system, tool]（无 user 角色）调
chat/reason/stream_chat——provider 不得收到真实调用，产出必须是演示脚本文案；
非 demo 轮正控照常到达 provider（修复不得过拦真实轮）；既有 user 关键词
命中行为不回归。
"""

from __future__ import annotations

from typing import Any

import pytest

from app.config import settings
from app.services.llm_service import DEMO_MOCK_RESPONSES, LLMService


class _StubProvider:
    """has_api_key=True 的 stub provider：记录收到的真实调用（判据要求面）。"""

    def __init__(self) -> None:
        self.has_api_key = True
        self.calls: list[dict[str, Any]] = []

    async def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        self.calls.append({"messages": messages, **kwargs})
        return "REAL_PROVIDER_REPLY"


# 工具续写类形状：无 user 角色行（台账判据的触发形状）。
_TOOL_CONTINUATION_MESSAGES: list[dict[str, str]] = [
    {"role": "system", "content": "你是学习助手。"},
    {"role": "tool", "content": "工具返回的学习状态数据。"},
]


def _build_service(monkeypatch: pytest.MonkeyPatch, *, demo_mode: bool) -> tuple[LLMService, _StubProvider]:
    """按台账触发前提构建：settings.DEMO_MODE=demo_mode + stub provider
    (has_api_key=True)。settings 经 __init__（llm_service :364）生效后替换
    provider 为 stub，等价「demo 置位且 api key 有效」的部署面。"""
    monkeypatch.setattr(settings, "DEMO_MODE", demo_mode, raising=False)
    service = LLMService(enable_dynamic_routing=False)
    # 测试环境无 API key 时 _init_legacy 会强制 demo_mode=True（:458-460 自动
    # 激活），与 settings.DEMO_MODE 无关——正控面按 test_llm_service_security
    # 先例显式钉回目标值，等价「有 key 且 DEMO_MODE=false」部署面。
    service.demo_mode = demo_mode
    stub = _StubProvider()
    service._provider = stub  # noqa: SLF001 — 测试装配桩
    service._provider_error = None
    service._extra_body = None
    service._current_selection = None
    service.chat_model = "test-model"
    service.reason_model = "test-model"
    return service, stub


class TestDemoShortCircuitTotality:
    async def test_chat_no_user_role_short_circuits(self, monkeypatch):
        """红→绿：chat() 在 [system, tool] 形状下必须演示脚本短路，不得落穿
        真实 provider（修前实录：stub 收到真实调用）。"""
        service, stub = _build_service(monkeypatch, demo_mode=True)

        result = await service.chat(_TOOL_CONTINUATION_MESSAGES)

        assert "演示模式" in result, "必须返回演示脚本文案（短路前提命中）"
        assert result == LLMService._generic_demo_response()
        assert stub.calls == [], "provider 不得收到真实调用（此前落穿点）"

    async def test_reason_no_user_role_short_circuits(self, monkeypatch):
        """红→绿：reason() 同形状不得落穿（台账 :1068-1075 落穿点）。"""
        service, stub = _build_service(monkeypatch, demo_mode=True)

        result = await service.reason(_TOOL_CONTINUATION_MESSAGES)

        assert "演示模式" in result
        assert result == LLMService._generic_demo_response()
        assert stub.calls == []

    async def test_stream_chat_no_user_role_short_circuits(self, monkeypatch):
        """stream 路径不回归：有 provider 时（`demo_mode and not provider` 兜底
        覆盖不到的面）同形状也必须演示脚本短路。"""
        service, stub = _build_service(monkeypatch, demo_mode=True)

        chunks = [chunk async for chunk in service.stream_chat(_TOOL_CONTINUATION_MESSAGES)]

        full = "".join(chunks)
        assert "演示模式" in full
        assert full == LLMService._generic_demo_response()
        assert stub.calls == []

    async def test_chat_blank_user_content_also_short_circuits(self, monkeypatch):
        """边界：最后一条 user 内容 strip 后为空，与无 user 角色同判据短路。"""
        service, stub = _build_service(monkeypatch, demo_mode=True)
        messages = [
            {"role": "system", "content": "你是学习助手。"},
            {"role": "user", "content": "   "},
        ]

        result = await service.chat(messages)

        assert result == LLMService._generic_demo_response()
        assert stub.calls == []

    async def test_demo_keyword_match_unregressed(self, monkeypatch):
        """回归守卫：user 关键词命中的既有演示行为不变（不得被通用兜底吞掉）。"""
        service, stub = _build_service(monkeypatch, demo_mode=True)
        key, scripted = next(iter(DEMO_MOCK_RESPONSES.items()))

        result = await service.chat([{"role": "user", "content": key}])

        assert result == scripted
        assert stub.calls == []


class TestNonDemoControl:
    async def test_non_demo_no_user_role_reaches_provider(self, monkeypatch):
        """正控（修前后恒绿）：非 demo 轮的同形状请求必须照常到达 provider——
        修复不得过拦真实轮（否则构成新的内容损失方向）。"""
        service, stub = _build_service(monkeypatch, demo_mode=False)
        monkeypatch.setattr(
            service, "_build_provider_for_selection", lambda selection: ("stub", stub, {})
        )

        result = await service.chat(_TOOL_CONTINUATION_MESSAGES)

        assert result == "REAL_PROVIDER_REPLY"
        assert len(stub.calls) == 1, "非 demo 轮必须真实到达 provider 恰好一次"
