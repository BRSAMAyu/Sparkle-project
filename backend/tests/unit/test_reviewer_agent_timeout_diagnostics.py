"""PROD-LOG #4 契约测试：ReviewerAgent 超时与空消息异常必须可诊断.

背景（v3-output/PROD-LOG/REPORT.md ②-4）：
- ``asyncio.wait_for`` 抛出的 ``asyncio.TimeoutError`` 的 ``str()`` 为空串，
  通用 ``except Exception as e: logger.error(f"... {e}")`` 落出
  ``[ReviewerAgent] Review failed: ``（空尾巴），6 条 ERROR 全部不可诊断。
- 契约：① 超时单独分级记录——哪个 review、等了多久、阈值、模型；② ``str()``
  为空的异常兜底用异常类名（不再有空尾巴）；③ R6-P0-3 fail-closed 语义不变
  （超时/异常 -> FAILED + requires_reflection，见 test_reviewer_agent_phase62）。
"""

from __future__ import annotations

import asyncio

import pytest
from loguru import logger

from app.agents.reviewer_agent import ReviewerAgent


class _SleepyReviewerLLM:
    """慢响应 LLM：用于触发 wait_for 超时。"""

    default_model = "review-model"
    model_key = "review_model_key"
    provider_name = "dashscope"

    async def chat_json(self, messages, temperature=0.2):
        await asyncio.sleep(0.05)
        return {"decision": "passed", "overall_score": 0.9, "issues": []}


class _EmptyErrorReviewerLLM:
    """抛出 str() 为空串异常的 LLM：复现原缺陷的空尾巴场景。"""

    default_model = "review-model"
    model_key = "review_model_key"
    provider_name = "dashscope"

    async def chat_json(self, messages, temperature=0.2):
        raise ValueError()  # str(ValueError()) == ""


@pytest.fixture
def loguru_records():
    records: list = []
    sink_id = logger.add(lambda msg: records.append(msg.record), level="DEBUG")
    yield records
    logger.remove(sink_id)


def _error_records(records: list) -> list:
    return [r for r in records if r["level"].name == "ERROR"]


@pytest.mark.asyncio
async def test_timeout_log_carries_context_and_fails_closed(
    monkeypatch: pytest.MonkeyPatch, loguru_records: list
):
    """超时 ERROR 必须带：哪个 review、等了多久、阈值、模型；fail-closed 不回退."""
    monkeypatch.setattr("app.agents.reviewer_agent.settings.REVIEWER_LLM_TIMEOUT_SECONDS", 0.01)
    reviewer = ReviewerAgent(reviewer_llm=_SleepyReviewerLLM())

    result = await reviewer.review_llm_response(user_query="讲讲梯度下降", llm_response="梯度下降是…")

    # fail-closed 语义保持（R6-P0-3）
    assert result.decision == "failed"
    assert result.review_error is True
    assert result.requires_reflection is True

    errors = _error_records(loguru_records)
    assert errors, "超时必须留下 ERROR 级日志"
    msg = errors[-1]["message"]
    assert msg.startswith("[ReviewerAgent] Response review review_"), msg
    assert "timed out after" in msg  # 实际等待时长
    assert "threshold=" in msg  # 超时阈值
    assert "reviewer_model=" in msg  # 所用模型
    # 问题单描述可诊断（且兼容既有 '审查过程出错' 契约）
    assert "审查过程出错" in result.issues[0].description
    assert "reviewer LLM 超时" in result.issues[0].description


@pytest.mark.asyncio
async def test_timeout_wrapper_message_includes_operation_and_threshold(
    monkeypatch: pytest.MonkeyPatch,
):
    """_chat_json_with_timeout 抛出的 TimeoutError 自带操作名/等待时长/阈值."""
    monkeypatch.setattr("app.agents.reviewer_agent.settings.REVIEWER_LLM_TIMEOUT_SECONDS", 0.01)
    reviewer = ReviewerAgent(reviewer_llm=_SleepyReviewerLLM())

    with pytest.raises(asyncio.TimeoutError) as exc_info:
        await reviewer._chat_json_with_timeout(
            messages=[{"role": "user", "content": "x"}],
            temperature=0.2,
            operation="response review review_fixedid",
        )

    detail = str(exc_info.value)
    assert detail, "TimeoutError 的 str() 不得为空串（原缺陷根因）"
    assert "response review review_fixedid" in detail  # 哪个 review
    assert "waited" in detail  # 等了多久
    assert "threshold" in detail  # 阈值


@pytest.mark.asyncio
async def test_empty_exception_message_falls_back_to_class_name(
    monkeypatch: pytest.MonkeyPatch, loguru_records: list
):
    """str() 为空的异常：日志与问题单描述兜底异常类名，不再出现空尾巴."""
    reviewer = ReviewerAgent(reviewer_llm=_EmptyErrorReviewerLLM())

    result = await reviewer.review_llm_response(user_query="q", llm_response="r")

    assert result.decision == "failed"
    assert result.review_error is True
    assert result.requires_reflection is True

    errors = _error_records(loguru_records)
    assert errors, "异常必须留下 ERROR 级日志"
    msg = errors[-1]["message"]
    assert msg.endswith("Review failed: ValueError"), f"空消息未兜底: {msg!r}"
    assert "ValueError" in result.issues[0].description


@pytest.mark.asyncio
async def test_plan_review_timeout_log_carries_context(
    monkeypatch: pytest.MonkeyPatch, loguru_records: list
):
    """plan review 路径同样钉：超时上下文 + fail-closed."""
    monkeypatch.setattr("app.agents.reviewer_agent.settings.REVIEWER_LLM_TIMEOUT_SECONDS", 0.01)
    reviewer = ReviewerAgent(reviewer_llm=_SleepyReviewerLLM())

    result = await reviewer.review_plan(plan={}, user_query="帮我定复习计划")

    assert result.decision == "failed"
    assert result.review_error is True
    assert result.requires_reflection is True

    errors = _error_records(loguru_records)
    assert errors, "超时必须留下 ERROR 级日志"
    msg = errors[-1]["message"]
    assert msg.startswith("[ReviewerAgent] Plan review plan_review_"), msg
    assert "timed out after" in msg
    assert "threshold=" in msg
    assert "计划审查出错" in result.issues[0].description
