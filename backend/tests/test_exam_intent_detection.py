import pytest

from app.agents.standard_workflow import _classify_user_intent, detect_exam_urgency


@pytest.mark.parametrize(
    "text,expected",
    [
        ("我明天考数学", 1),
        ("我后天考试", 2),
        ("还有3天期末考试", 3),
        ("下周有测验", 7),
        ("tomorrow exam", 1),
    ],
)
def test_detect_exam_urgency(text, expected):
    assert detect_exam_urgency(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "我后天考试",
        "准备期末复习",
        "考研冲刺计划",
    ],
)
def test_classify_exam_intent(text):
    assert _classify_user_intent(text) == "exam_preparation"


def test_detect_exam_urgency_returns_none_when_no_exam():
    assert detect_exam_urgency("我今天想听音乐") is None
