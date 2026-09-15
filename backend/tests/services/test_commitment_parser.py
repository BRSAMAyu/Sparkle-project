from datetime import datetime

from app.services.commitment_parser import parse_commitment_due_at


REFERENCE = datetime(2026, 4, 20, 10, 0, 0)


def test_parse_commitment_due_at_tomorrow():
    due_at = parse_commitment_due_at("我明天要把提纲补完。", reference_time=REFERENCE)
    assert due_at == datetime(2026, 4, 21, 9, 0, 0)


def test_parse_commitment_due_at_this_week():
    due_at = parse_commitment_due_at("这周我要把错题本整理完。", reference_time=REFERENCE)
    assert due_at == datetime(2026, 4, 26, 18, 0, 0)


def test_parse_commitment_due_at_month_end():
    due_at = parse_commitment_due_at("月底前我要交完申请。", reference_time=REFERENCE)
    assert due_at == datetime(2026, 4, 30, 18, 0, 0)


def test_parse_commitment_due_at_absolute_month_day():
    due_at = parse_commitment_due_at("我计划 5月3日 前完成复盘。", reference_time=REFERENCE)
    assert due_at == datetime(2026, 5, 3, 18, 0, 0)


def test_parse_commitment_due_at_requires_supported_time_anchor():
    assert parse_commitment_due_at("我会继续认真学习。", reference_time=REFERENCE) is None
