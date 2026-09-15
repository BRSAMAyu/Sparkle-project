import pytest

from app.orchestration.task_guide_enricher import TaskGuideEnricher


def _guide_json() -> dict:
    return {
        "objective": "Day 1：极限与连续代表题",
        "output_action": "不看答案先做 3 道代表题，并写下每道题的判断依据或错因。",
        "success_criteria": "至少完成 3 道代表题，其中至少 2 道能独立判断。",
        "method_steps": [
            "先闭卷写出题目的已知条件和判断依据。",
            "独立完成 3 道代表题，不先看答案。",
            "对照解析补错因并重做 1 道同型题。",
        ],
        "key_points": ["极限与连续", "代表题判断依据"],
        "minimum_output": "闭卷复述或小测",
    }


def test_enrich_sync_adds_non_empty_guide_fields() -> None:
    enricher = TaskGuideEnricher()

    result = enricher.enrich_sync(
        guide_json=_guide_json(),
        task_kind="retrieval_drill",
        subject="高等数学",
        focus="极限与连续",
    )

    assert 3 <= len(result["if_stuck"]) <= 5
    assert 2 <= len(result["prerequisite_check"]) <= 3
    assert "极限与连续" in result["focus_cue"]
    assert result["why_now"].endswith("。")
    assert result["objective"] == "Day 1：极限与连续代表题"
    assert len(result["steps"]) == 4
    assert all(step["name"] and step["duration_min"] > 0 for step in result["steps"])
    assert len(result["done_criteria"]) >= 2
    assert len(result["mini_quiz"]["items"]) == 3
    assert len(result["fallback_if_stuck"]) >= 2
    assert any(trigger["code"] == "accuracy_below_0.5" for trigger in result["aurora_triggers"])


@pytest.mark.asyncio
async def test_enrich_falls_back_when_llm_fails() -> None:
    class FailingTaskGuideEnricher(TaskGuideEnricher):
        async def _llm_enrich(self, **kwargs) -> dict:
            raise RuntimeError("llm unavailable")

    result = await FailingTaskGuideEnricher().enrich(
        guide_json=_guide_json(),
        task_kind="retrieval_drill",
        subject="高等数学",
        focus="极限与连续",
        bottlenecks=[{"description": "基础公式记不牢"}],
        use_llm=True,
    )

    assert result["if_stuck"] == TaskGuideEnricher.RULE_BASED_IF_STUCK["retrieval_drill"]
    assert result["prerequisite_check"]
    assert "极限与连续" in result["focus_cue"]
    assert result["why_now"]


@pytest.mark.asyncio
async def test_enrich_handles_empty_bottlenecks_without_llm() -> None:
    result = await TaskGuideEnricher().enrich(
        guide_json=_guide_json(),
        task_kind="concept_review",
        subject="高等数学",
        focus="导数定义",
        bottlenecks=None,
        use_llm=False,
    )

    assert result["if_stuck"] == TaskGuideEnricher.RULE_BASED_IF_STUCK["concept_review"]
    assert result["prerequisite_check"]
    assert "导数定义" in result["focus_cue"]
    assert result["why_now"]
