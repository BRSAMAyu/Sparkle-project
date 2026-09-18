"""中文 commitment/考试类记忆抽取回归（R28 验收断点）。

验收现场：用户说"我下周三有数据结构期中考试，帮我记住这个。"助手回复"已记住"，
但 episodic 表只有电影偏好条目入库。根因：
1. `_looks_like_commitment` 的 future_markers 全是"我会/我要…"意图式，事件式
   承诺句（考试/交作业/上课）全部漏判为 self，due_at 永不解析；
2. `parse_commitment_due_at` 不支持"下周三/这周五/周X/星期X"中文星期表达，
   一旦判为 commitment 又因 due_at None 整条放弃；
3. LLM 路 prompt 无中文示例、无当前时钟，qwen 返回的 commitment 候选缺 due_at。

本文件锁定规则路修复：候选必须产出、subject_type=commitment、due_at 正确且 naive UTC。
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.services import commitment_parser as commitment_parser_module
from app.services import memory_inferred_write_lane as lane_module
from app.services.memory_inferred_write_lane import MemoryInferredWriteLaneService

# 固定时钟：2026-09-21 是周一（UTC），让"下周三/这周五"的期望值可精确断言。
FROZEN_NOW = datetime(2026, 9, 21, 12, 0, 0)


@pytest.fixture(autouse=True)
def _freeze_clock(monkeypatch):
    monkeypatch.setattr(commitment_parser_module, "_utcnow", lambda: FROZEN_NOW)
    monkeypatch.setattr(lane_module, "_utcnow", lambda: FROZEN_NOW)


def _extract(user_message: str):
    service = MemoryInferredWriteLaneService(db=None)
    return service.extract_candidate(
        user_id=uuid4(),
        user_message=user_message,
        assistant_message="好的，已经帮你记住了。",
        evidence_token=f"turn_{uuid4().hex}",
    )


class TestParseCommitmentDueAtChineseWeekday:
    def test_next_wednesday(self):
        due = commitment_parser_module.parse_commitment_due_at("下周三有数据结构期中考试")
        assert due == datetime(2026, 9, 30, 18, 0, 0)

    def test_this_friday_deadline(self):
        due = commitment_parser_module.parse_commitment_due_at("这周五要交实验报告")
        assert due == datetime(2026, 9, 25, 18, 0, 0)

    def test_bare_weekday_rolls_forward(self):
        # 周一 12:00 说"周三"→ 本周三；说"周一"→ 即当天；说"上周已过的周一"场景由 (t-w)%7 顺延。
        assert commitment_parser_module.parse_commitment_due_at("周三下午组会") == datetime(2026, 9, 23, 15, 0, 0)
        assert commitment_parser_module.parse_commitment_due_at("周一要交周报") == datetime(2026, 9, 21, 18, 0, 0)

    def test_week_after_next(self):
        due = commitment_parser_module.parse_commitment_due_at("下下周一有操作系统考试")
        assert due == datetime(2026, 10, 5, 18, 0, 0)

    def test_weekday_without_time_expression_still_none(self):
        assert commitment_parser_module.parse_commitment_due_at("我会继续认真学习。") is None


class TestRuleLaneChineseCommitmentCandidates:
    @pytest.mark.parametrize(
        ("user_message", "expected_due"),
        [
            # 验收原始句（带显式口令 + 全角标点）。
            ("我下周三有数据结构期中考试，帮我记住这个。", datetime(2026, 9, 30, 18, 0, 0)),
            ("这周五要交实验报告", datetime(2026, 9, 25, 18, 0, 0)),
            ("明天上午有英语课", datetime(2026, 9, 22, 9, 0, 0)),
            ("下周四有一场高数小测", datetime(2026, 10, 1, 18, 0, 0)),
            ("我下周一要考概率论", datetime(2026, 9, 28, 18, 0, 0)),
        ],
    )
    def test_candidate_produced_with_commitment_and_due_at(self, user_message, expected_due):
        candidate = _extract(user_message)
        assert candidate is not None, f"中文承诺句未产出候选: {user_message}"
        assert candidate.subject_type == "commitment"
        assert candidate.due_at == expected_due
        # 项目规范：occurred_at/due_at 必须是 naive UTC。
        assert candidate.due_at.tzinfo is None
        assert candidate.occurred_at.tzinfo is None
        assert candidate.confidence >= 0.9

    def test_real_acceptance_sentence_strips_command_phrase(self):
        candidate = _extract("我下周三有数据结构期中考试，帮我记住这个。")
        assert candidate is not None
        assert candidate.candidate_text == "我下周三有数据结构期中考试"

    def test_occurred_at_aligns_with_weekday_event_day(self):
        # "下周三" occurred_at 必须落在下周三当天，而不是"下周"兜底的周一。
        candidate = _extract("下周三有数据结构期中考试")
        assert candidate is not None
        assert candidate.occurred_at == datetime(2026, 9, 30, 18, 0, 0)

    def test_command_phrase_prefixed_fact_routes_commitment(self):
        # 无"我"、带口令前缀的事件句：口令剥离后仍要以 commitment 入库。
        candidate = _extract("帮我记住这个，下周三有数据结构期中考试")
        assert candidate is not None
        assert candidate.subject_type == "commitment"
        assert candidate.due_at == datetime(2026, 9, 30, 18, 0, 0)

    def test_explicit_command_fallback_routes_commitment_fact(self):
        # "考试"不在学习词表 → 候选句选择器放弃 → 走显式口令 fallback；
        # fallback 产出的事实带可解析时间锚时同样升级为 commitment。
        candidate = _extract("帮我记住，下周三有考试")
        assert candidate is not None
        assert candidate.subject_type == "commitment"
        assert candidate.due_at == datetime(2026, 9, 30, 18, 0, 0)

    def test_question_without_time_anchor_stays_non_commitment(self):
        # 提问句不得被误判为 commitment（否则 due_at None 整条丢弃）。
        candidate = _extract("根据你的记忆，我之前提到过什么考试？")
        assert candidate is None or candidate.subject_type != "commitment"


class TestCommitmentDueAtNaiveUtc:
    def test_parser_returns_naive_utc(self):
        due = commitment_parser_module.parse_commitment_due_at("下周三有考试")
        assert due is not None
        assert due.tzinfo is None
        # naive 值必须可与现代 UTC now 直接比较（无 offset 混淆）。
        assert due > datetime.now(UTC).replace(tzinfo=None) - timedelta(days=1)
