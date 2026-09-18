"""R2 N2 (P1→P2)：reflection_agent 以不存在的 ``chat(system_prompt=, user_message=)`` 签名调用裸服务。

R2 报告 §3 N2：``agents/reflection_agent.py:566/:706`` 的该签名在全仓任何实现上都不存在
（裸 LLMService.chat 是 messages-first），必 TypeError：:706 被 try 吞掉（修正恒失败），
:566 无局部防护。修复契约：构造 messages 列表按裸服务真实签名调用。

本测试注入 bare-signature 假生成器做真实参数绑定（多余 kwarg 会 TypeError）。
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from app.agents.reflection_agent import ReflectionAgent, ReflectionStrategy
from app.agents.reviewer_agent import Issue, ReviewResult


class BareSignatureGenerator:
    """签名与裸 LLMService.chat 一致；system_prompt=/user_message= 传入会直接 TypeError。"""

    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float | None = None,
        *,
        task_type: Any = None,
        **kwargs: Any,
    ) -> str:
        self.calls.append({"messages": messages, "temperature": temperature, "kwargs": kwargs})
        return self.response


_TRIGGER_JSON = json.dumps(
    {
        "summary": "连续两轮停在计划确认",
        "confidence": 0.8,
        "reasoning": "route history 显示重复超时",
        "evidence": ["step stalled"],
    },
    ensure_ascii=False,
)


def _make_agent(response: str) -> tuple[ReflectionAgent, BareSignatureGenerator]:
    generator = BareSignatureGenerator(response)
    agent = ReflectionAgent(generator_llm=generator, reviewer=None)
    return agent, generator


def _review_result() -> ReviewResult:
    return ReviewResult(
        review_id="rev-1",
        target_type="response",
        target_id="resp-1",
        decision="failed",
        overall_score=0.4,
        metrics=[],
        issues=[
            Issue(
                category="accuracy",
                severity="critical",
                location="body",
                description="结论与用户目标不一致",
                affected_content="原内容片段",
                suggested_fix="改写结论",
                confidence=0.9,
            )
        ],
        improvement_suggestions=["对齐目标"],
        requires_reflection=True,
        reviewer_model="stub",
        review_timestamp="2026-09-18T00:00:00Z",
    )


@pytest.mark.asyncio
async def test_reflect_trigger_binds_real_chat_signature():
    agent, generator = _make_agent(_TRIGGER_JSON)
    result = await agent._reflect_trigger(
        user_id="u1",
        trigger_category="stall",
        trigger_payload={"step": "confirm"},
        context={},
    )
    assert result.summary == "连续两轮停在计划确认"
    assert len(generator.calls) == 1
    call = generator.calls[0]
    # 调用必须是 messages-first（system 提示并入 messages），而非 system_prompt=/user_message=
    assert isinstance(call["messages"], list)
    assert call["messages"][0]["role"] == "system"
    assert call["messages"][-1]["role"] == "user"


@pytest.mark.asyncio
async def test_execute_fix_binds_real_chat_signature():
    agent, generator = _make_agent("修正后的内容")
    fixed_content, reasoning = await agent._execute_fix(
        user_query="帮我做周计划",
        current_content="有问题的内容",
        review_result=_review_result(),
        strategy=ReflectionStrategy.DIRECT_FIX,
        context={},
        review_profile_id="default_response",
        workflow_context=None,
    )
    assert fixed_content == "修正后的内容"
    assert "修正失败" not in reasoning
    assert len(generator.calls) == 1
    call = generator.calls[0]
    assert isinstance(call["messages"], list)
    assert call["messages"][0]["role"] == "system"
    assert call["messages"][-1]["role"] == "user"
