from __future__ import annotations

import json

import pytest

from app.orchestration.bottleneck_analyzer import BottleneckAnalyzer


class _FakeLLM:
    def __init__(self, payload=None, exc: Exception | None = None) -> None:
        self.payload = payload
        self.exc = exc
        self.calls = []

    async def chat_json(self, *args, **kwargs):
        self.calls.append({"args": args, "kwargs": kwargs})
        if self.exc:
            raise self.exc
        return self.payload


def _base_kwargs(**overrides):
    payload = {
        "subject": "热学",
        "knowledge_baseline": "学过一遍但概念混乱",
        "time_constraint_days": 7,
        "daily_available_hours": 2.0,
        "galaxy_weak_nodes": [
            {"name": "热力学第一定律", "mastery_score": 25, "node_type": "concept"},
            {"name": "理想气体状态方程", "mastery_score": 40, "node_type": "concept"},
        ],
        "available_materials": ["课件", "真题"],
        "blocked_days": ["周三晚"],
        "open_tensions": ["考试范围还没完全确认"],
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_llm_path_parses_valid_json(monkeypatch):
    fake_llm = _FakeLLM(
        json.dumps(
            {
                "bottlenecks": [
                    {
                        "description": "热力学第一定律的能量守恒关系掌握不稳，容易影响综合题建模。",
                        "severity": "high",
                        "specific_risk": "遇到过程分析题时会把做功和吸热方向混掉。",
                        "affected_concepts": ["热力学第一定律"],
                        "recommendation": "先闭卷写出符号约定，再做 3 道过程判断题。",
                    },
                    {
                        "description": "理想气体状态方程和图像题之间的转换还不稳定。",
                        "severity": "medium",
                        "specific_risk": "图像题会消耗过多时间，压缩后续检查。",
                        "affected_concepts": ["理想气体状态方程"],
                        "recommendation": "把 PV 图和公式对应关系整理成一张表。",
                    },
                ],
                "confidence": 0.88,
            },
            ensure_ascii=False,
        )
    )

    async def _get_llm(*args, **kwargs):
        return fake_llm

    monkeypatch.setattr("app.orchestration.bottleneck_analyzer.get_configured_llm_service", _get_llm)

    result = await BottleneckAnalyzer().analyze(**_base_kwargs())

    assert result.analysis_method == "llm"
    assert result.confidence == pytest.approx(0.88)
    assert len(result.bottlenecks) == 2
    assert result.bottlenecks[0].id == "b1"
    assert result.bottlenecks[0].severity == "high"
    assert "热力学第一定律" in result.bottlenecks[0].description
    assert fake_llm.calls[0]["kwargs"]["temperature"] == 0.2


@pytest.mark.asyncio
async def test_llm_failure_returns_rule_fallback(monkeypatch):
    fake_llm = _FakeLLM(exc=RuntimeError("llm down"))

    async def _get_llm(*args, **kwargs):
        return fake_llm

    monkeypatch.setattr("app.orchestration.bottleneck_analyzer.get_configured_llm_service", _get_llm)

    result = await BottleneckAnalyzer().analyze(**_base_kwargs())

    assert result.analysis_method == "rule_fallback"
    assert len(result.bottlenecks) >= 2
    assert result.bottlenecks[0].severity == "high"


@pytest.mark.asyncio
async def test_weak_nodes_are_grounded_in_bottleneck_description(monkeypatch):
    fake_llm = _FakeLLM(
        {
            "bottlenecks": [
                {
                    "description": "核心概念之间的因果链条还没有成型。",
                    "severity": "high",
                    "specific_risk": "综合题会缺少第一步判断。",
                    "affected_concepts": [],
                    "recommendation": "先做一轮闭卷复述。",
                },
                {
                    "description": "题目验证不足。",
                    "severity": "medium",
                    "specific_risk": "后期才发现错题类型会来不及补。",
                    "affected_concepts": [],
                    "recommendation": "每天做一次小测。",
                },
            ],
            "confidence": 0.7,
        }
    )

    async def _get_llm(*args, **kwargs):
        return fake_llm

    monkeypatch.setattr("app.orchestration.bottleneck_analyzer.get_configured_llm_service", _get_llm)

    result = await BottleneckAnalyzer().analyze(**_base_kwargs())

    assert result.analysis_method == "llm"
    assert any("热力学第一定律" in item.description for item in result.bottlenecks)


@pytest.mark.asyncio
async def test_no_weak_nodes_still_returns_at_least_two_bottlenecks(monkeypatch):
    fake_llm = _FakeLLM(
        {
            "bottlenecks": [
                {
                    "description": "复习时间被压缩，章节覆盖需要先分层。",
                    "severity": "high",
                    "specific_risk": "后半程可能没有时间做模拟。",
                    "affected_concepts": ["热学"],
                    "recommendation": "先切出高频保底内容。",
                }
            ],
            "confidence": 0.66,
        }
    )

    async def _get_llm(*args, **kwargs):
        return fake_llm

    monkeypatch.setattr("app.orchestration.bottleneck_analyzer.get_configured_llm_service", _get_llm)

    result = await BottleneckAnalyzer().analyze(**_base_kwargs(galaxy_weak_nodes=[]))

    assert result.analysis_method == "llm"
    assert len(result.bottlenecks) >= 2


@pytest.mark.asyncio
async def test_empty_galaxy_weak_nodes_does_not_crash(monkeypatch):
    fake_llm = _FakeLLM(exc=RuntimeError("force fallback"))

    async def _get_llm(*args, **kwargs):
        return fake_llm

    monkeypatch.setattr("app.orchestration.bottleneck_analyzer.get_configured_llm_service", _get_llm)

    result = await BottleneckAnalyzer().analyze(**_base_kwargs(galaxy_weak_nodes=[]))

    assert result.analysis_method == "rule_fallback"
    assert len(result.bottlenecks) >= 2
