"""Round2 系统审查修复：reflection 上下文继承 + 审查"未通过"噪声根因。

已实证缺陷（round2 验收，引擎日志 /tmp/wt1_deep_eval_grpc4.log）：
1. 审查模型 qwen3.8-flash 实测延迟 12.6-13.7s，而 REVIEWER_LLM_TIMEOUT_SECONDS
   默认 12s → TimeoutError → fail-closed（decision=failed, score=0.00, 恰好
   1 个 critical "审查过程出错"）→ 回复尾部恒带 "[内容审查: 未通过] 发现
   1 个严重问题需要处理" 并触发无效重写。
2. reflection_node 调 reflector.reflect 时不携带主生成 system_prompt（检索
   材料 / 跨会话记忆 / 用户画像全部丢失）→ 重写回复"失明"并替换主回复交付。

修复契约：
- generation_node 持久化最终组装的 system_prompt → review_context 携带 →
  reflection_node 传入 reflect context → ReflectionAgent._execute_fix 注入
  system 消息。
- 审查超时放宽到 30s；_parse_review_result 对"总分达标却贴非 safety
  critical"的严重度通胀做校准（safety 类 critical 保留）。
"""

from __future__ import annotations

from typing import Any

import pytest

from app.agents.reflection_agent import (
    ReflectionAgent,
    ReflectionOutcome,
    ReflectionResult,
    ReflectionStrategy,
)
from app.agents.reviewer_agent import ReviewerAgent
from app.config import settings

# ============================================
# 测试替身
# ============================================


class CapturingGenerator:
    """签名与裸 LLMService.chat 一致；捕获 messages 供断言。"""

    def __init__(self, response: str = "修正后的内容") -> None:
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
        self.calls.append({"messages": messages, "temperature": temperature})
        return self.response


class FakeReviewerLLM:
    """可编程 chat_json，模拟审查模型输出。"""

    def __init__(self, payload: dict[str, Any] | None = None) -> None:
        self.default_model = "review-model"
        self.model_key = "review_model_key"
        self.provider_name = "dashscope"
        self.payload = payload
        self.messages: list[dict[str, str]] | None = None

    async def chat_json(self, messages, temperature=0.2):
        self.messages = messages
        return self.payload


def _normal_reply_review_payload() -> dict[str, Any]:
    """模拟严格审查 LLM 对一条正常学习回复的输出：总分 0.82，
    仍带 1 个非 safety critical（严重度通胀）+ 2 个 warning。"""
    return {
        "overall_score": 0.82,
        "decision": "needs_refinement",
        "metrics": [
            {"metric": "accuracy", "score": 0.85, "weight": 1.5, "threshold": 0.8},
            {"metric": "completeness", "score": 0.78, "weight": 1.2, "threshold": 0.7},
        ],
        "issues": [
            {
                "category": "completeness",
                "severity": "critical",
                "location": "第2段",
                "description": "未展开说明易错点",
                "affected_content": "",
                "suggested_fix": "补充易错点",
                "confidence": 0.7,
            },
            {
                "category": "clarity",
                "severity": "warning",
                "location": "第1段",
                "description": "开头略绕",
                "affected_content": "",
                "suggested_fix": "直接给结论",
                "confidence": 0.6,
            },
            {
                "category": "helpfulness",
                "severity": "warning",
                "location": "结尾",
                "description": "缺少下一步建议",
                "affected_content": "",
                "suggested_fix": "补一个行动项",
                "confidence": 0.6,
            },
        ],
        "improvement_suggestions": ["补充易错点"],
        "requires_reflection": True,
        "timestamp": "2026-09-18T00:00:00",
    }


GENERATION_SYSTEM_PROMPT = (
    "你是 Sparkle 星火……\n\n"
    "## Retrieved Documents（用户上传资料原文——回答相关问题必须优先引用，禁止声称未看到）\n"
    "【材料原文】贝叶斯证据融合模块把多路检索置信度按先验加权……doc_chunks:165 token\n\n"
    "【近期相关记忆】用户此前提到：数据结构期中考试定在下周三，最怕二叉树旋转题。"
)


def _review_result_dict() -> dict[str, Any]:
    return {
        "review_id": "rev-1",
        "target_type": "response",
        "target_id": "resp-1",
        "decision": "failed",
        "overall_score": 0.4,
        "metrics": [],
        "issues": [
            {
                "category": "accuracy",
                "severity": "critical",
                "location": "body",
                "description": "结论与材料不一致",
                "affected_content": "",
                "suggested_fix": "对齐材料",
                "confidence": 0.9,
            }
        ],
        "improvement_suggestions": [],
        "requires_reflection": True,
        "reviewer_model": "stub",
        "review_timestamp": "2026-09-18T00:00:00",
        "review_profile_id": "default_response",
        "workflow_context": {"workflow_type": "", "chat_mode": "standard"},
    }


class _MinimalReviewResult:
    """_execute_fix 所需的最小审查结果视图。"""

    target_type = "response"
    issues: list[Any] = []
    improvement_suggestions: list[str] = []
    critical_issues: list[Any] = []


# ============================================
# A. reflection 上下文继承
# ============================================


@pytest.mark.asyncio
async def test_execute_fix_injects_generation_system_prompt():
    """重写 LLM 调用的 system 消息必须包含主生成 system_prompt 中的
    检索材料段与跨会话记忆段（否则重写"失明"）。"""
    generator = CapturingGenerator()
    agent = ReflectionAgent(generator_llm=generator, reviewer=None)

    fixed_content, reasoning = await agent._execute_fix(
        user_query="根据我上传的资料讲讲贝叶斯证据融合",
        current_content="有问题的内容",
        review_result=_MinimalReviewResult(),
        strategy=ReflectionStrategy.DIRECT_FIX,
        context={"generation_system_prompt": GENERATION_SYSTEM_PROMPT},
        review_profile_id="default_response",
        workflow_context=None,
    )

    assert fixed_content == "修正后的内容"
    assert "修正失败" not in reasoning
    assert len(generator.calls) == 1
    messages = generator.calls[0]["messages"]
    assert messages[0]["role"] == "system"
    assert messages[-1]["role"] == "user"
    system_content = messages[0]["content"]
    # 检索材料段继承
    assert "Retrieved Documents" in system_content
    assert "贝叶斯证据融合" in system_content
    # 跨会话记忆段继承
    assert "近期相关记忆" in system_content
    assert "数据结构期中考试" in system_content
    # 反修指示存在
    assert "禁止声称" in system_content


@pytest.mark.asyncio
async def test_execute_fix_without_generation_prompt_keeps_base_system():
    """无继承上下文时保持原有单段 system，不注入空段。"""
    generator = CapturingGenerator()
    agent = ReflectionAgent(generator_llm=generator, reviewer=None)

    await agent._execute_fix(
        user_query="q",
        current_content="c",
        review_result=_MinimalReviewResult(),
        strategy=ReflectionStrategy.DIRECT_FIX,
        context={},
        review_profile_id="default_response",
        workflow_context=None,
    )

    system_content = generator.calls[0]["messages"][0]["content"]
    assert "内容优化专家" in system_content
    assert "原始生成上下文" not in system_content


@pytest.mark.asyncio
async def test_reflection_node_threads_generation_system_prompt(monkeypatch):
    """reflection_node 必须把 review_context.generation_system_prompt 传给
    reflector.reflect 的 context（节点级接线测试）。"""
    import app.agents.graph.nodes.review_nodes as review_nodes

    captured: dict[str, Any] = {}

    class StubReflector:
        generator = CapturingGenerator()

        async def reflect(self, **kwargs):
            captured.update(kwargs)
            return ReflectionResult(
                reflection_id="reflection_stub",
                target_id="rev-1",
                total_rounds=1,
                final_outcome=ReflectionOutcome.FIXED,
                initial_score=0.4,
                final_score=0.9,
                score_delta=0.5,
                rounds=[],
                success=True,
                final_content="依据材料重写的回复",
                reasoning="stub",
                review_profile_id="default_response",
                best_review_result={"review_id": "rev-2"},
            )

    def _stub_get_reflection_agent(**kwargs):
        captured["reflector"] = kwargs.get("reviewer")
        return StubReflector()

    monkeypatch.setattr(review_nodes, "get_reflection_agent", _stub_get_reflection_agent)
    monkeypatch.setattr(
        review_nodes,
        "_get_reviewer",
        lambda *a, **k: object(),
    )

    state: dict[str, Any] = {
        "user_id": "u-1",
        "session_id": "s-1",
        "messages": [{"role": "user", "content": "根据资料讲讲贝叶斯证据融合"}],
        "context_data": {},
        "review_context": {
            "reflection_round": 0,
            "result": _review_result_dict(),
            "original_content": "有问题的原始回复",
            "review_profile_id": "default_response",
            "workflow_context": {"workflow_type": "", "chat_mode": "standard", "target_type": "response"},
            "generation_system_prompt": GENERATION_SYSTEM_PROMPT,
        },
    }

    result = await review_nodes.reflection_node(state)

    assert captured["context"]["generation_system_prompt"] == GENERATION_SYSTEM_PROMPT
    assert result["context_data"]["fixed_response"] == "依据材料重写的回复"
    assert result["review_context"]["status"].value == "passed"


@pytest.mark.asyncio
async def test_reflection_node_reads_review_context_from_context_data(monkeypatch):
    """真实图形态：自研 WorkflowState 把节点返回值合并进 context_data，
    review_context / user_id / session_id 都只能从 context_data 拿到
    （修复前 reflection 恒以 "No review context" 空转，从未执行）。"""
    import app.agents.graph.nodes.review_nodes as review_nodes

    captured: dict[str, Any] = {}

    class StubReflector:
        generator = None

        async def reflect(self, **kwargs):
            captured.update(kwargs)
            return ReflectionResult(
                reflection_id="reflection_stub",
                target_id="rev-1",
                total_rounds=1,
                final_outcome=ReflectionOutcome.FIXED,
                initial_score=0.4,
                final_score=0.9,
                score_delta=0.5,
                rounds=[],
                success=True,
                final_content="重写完成",
                reasoning="stub",
                review_profile_id="default_response",
                best_review_result={"review_id": "rev-2"},
            )

    monkeypatch.setattr(review_nodes, "get_reflection_agent", lambda **kw: StubReflector())
    monkeypatch.setattr(review_nodes, "_get_reviewer", lambda *a, **k: object())

    state: dict[str, Any] = {
        "messages": [{"role": "user", "content": "根据资料讲讲贝叶斯证据融合"}],
        "context_data": {
            "user_id": "u-real",
            "session_id": "s-real",
            "review_context": {
                "reflection_round": 0,
                "result": _review_result_dict(),
                "original_content": "有问题的原始回复",
                "review_profile_id": "default_response",
                "workflow_context": {"workflow_type": "", "chat_mode": "standard", "target_type": "response"},
                "generation_system_prompt": GENERATION_SYSTEM_PROMPT,
            },
        },
    }

    result = await review_nodes.reflection_node(state)

    # 不再空转：reflect 被真实调用且拿到继承上下文与身份
    assert captured["user_id"] == "u-real"
    assert captured["context"]["session_id"] == "s-real"
    assert captured["context"]["generation_system_prompt"] == GENERATION_SYSTEM_PROMPT
    assert result["context_data"]["fixed_response"] == "重写完成"


# ============================================
# B. 审查"未通过"噪声根因
# ============================================


@pytest.mark.asyncio
async def test_normal_reply_with_inflated_critical_passes_review():
    """正常学习回复（总分 0.82、1 个非 safety critical + 2 个 warning）
    必须判定通过：审查通过则根本不进 reflection。"""
    reviewer = ReviewerAgent(reviewer_llm=FakeReviewerLLM(_normal_reply_review_payload()))
    result = await _run_review(reviewer)

    assert result.passed is True
    assert result.decision == "passed"
    assert len(result.critical_issues) == 0
    # 被降级的问题保留为 warning，不丢失信息
    assert len(result.warning_issues) == 3


@pytest.mark.asyncio
async def test_safety_critical_is_never_demoted_by_high_score():
    """safety 类 critical 即使总分高也不降级，绝不因高分放行安全问题。"""
    payload = _normal_reply_review_payload()
    payload["overall_score"] = 0.85
    payload["issues"][0] = {
        "category": "safety",
        "severity": "critical",
        "location": "第1段",
        "description": "包含危险建议",
        "affected_content": "",
        "suggested_fix": "删除",
        "confidence": 0.9,
    }
    reviewer = ReviewerAgent(reviewer_llm=FakeReviewerLLM(payload))
    result = await _run_review(reviewer)

    assert result.passed is False
    assert result.decision == "needs_refinement"
    assert len(result.critical_issues) == 1


@pytest.mark.asyncio
async def test_genuinely_bad_reply_still_fails_and_requires_reflection():
    """低分（0.45）且带 critical 的回复仍判 failed，反思通道不受校准影响。"""
    payload = _normal_reply_review_payload()
    payload["overall_score"] = 0.45
    reviewer = ReviewerAgent(reviewer_llm=FakeReviewerLLM(payload))
    result = await _run_review(reviewer)

    assert result.passed is False
    assert result.decision == "failed"
    assert len(result.critical_issues) == 1


def test_reviewer_default_timeout_covers_measured_review_latency():
    """默认审查超时必须覆盖审查模型实测延迟（12.6-13.7s），否则每轮
    TimeoutError → fail-closed（score=0.00 + 1 个 critical）即验收噪声。"""
    assert settings.REVIEWER_LLM_TIMEOUT_SECONDS >= 30
    assert ReviewerAgent(reviewer_llm=FakeReviewerLLM({})).llm_timeout_seconds >= 30


@pytest.mark.asyncio
async def test_non_dict_reviewer_payload_fails_closed_with_clear_reason():
    """chat_json 解析失败返回 None 时显式 fail-closed，错误信息可读。"""
    reviewer = ReviewerAgent(reviewer_llm=FakeReviewerLLM(None))

    async def _none_chat_json(messages, temperature=0.2):
        return None  # chat_json JSON 解析失败的真实返回形态

    reviewer.llm.chat_json = _none_chat_json  # type: ignore[method-assign]
    result = await reviewer.review_llm_response(
        user_query="帮我总结这份资料的重点",
        llm_response="这份资料围绕贝叶斯证据融合展开……",
        context={"conversation_history": []},
        review_profile_id="default_response",
        workflow_context={"workflow_type": "", "chat_mode": "standard", "target_type": "response"},
    )

    assert result.passed is False
    assert result.decision == "failed"
    assert result.requires_reflection is True
    assert any("reviewer payload is not a dict" in i.description for i in result.issues)


async def _run_review(reviewer: ReviewerAgent):
    return await reviewer.review_llm_response(
        user_query="帮我总结这份资料的重点",
        llm_response="这份资料围绕贝叶斯证据融合展开，先讲了先验，再讲了加权……",
        context={"conversation_history": []},
        review_profile_id="default_response",
        workflow_context={"workflow_type": "", "chat_mode": "standard", "target_type": "response"},
    )
