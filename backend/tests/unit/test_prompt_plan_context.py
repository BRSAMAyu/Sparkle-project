from app.orchestration.prompts import _format_plan_context


def test_format_plan_context_skips_irrelevant_plan_context():
    plan_context = {
        "plan_title": "长期计划验收-更新",
        "goal": "完成长期计划链路验收",
        "task_summaries": [{"title": "更新计划任务"}],
    }

    rendered = _format_plan_context(plan_context, query_text="请用三条简洁要点告诉我番茄钟学习法是什么。")

    assert rendered == ""


def test_format_plan_context_keeps_relevant_plan_context():
    plan_context = {
        "plan_title": "Python 测验冲刺",
        "goal": "7 天准备 Python 测验",
        "task_summaries": [{"title": "完成 Python 基础语法复习"}],
    }

    rendered = _format_plan_context(plan_context, query_text="请结合我现在的计划和任务，给我一个 Python 学习任务拆解。")

    assert "Python 测验冲刺" in rendered
    assert "仅在当前问题与这些计划/任务信息直接相关时" in rendered
