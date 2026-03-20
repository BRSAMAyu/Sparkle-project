from app.agents.graph.nodes.review_nodes import _should_skip_review


def test_should_skip_review_for_simple_standard_chat():
    state = {
        "messages": [
            {"role": "user", "content": "番茄钟学习法是什么？"},
            {"role": "assistant", "content": "番茄钟学习法是 25 分钟专注加 5 分钟休息的循环方法。"},
        ],
        "context_data": {
            "chat_mode": "standard",
            "workflow_type": "standard_chat",
        },
    }

    assert _should_skip_review(state) is True


def test_should_not_skip_review_for_study_plan_with_tools():
    state = {
        "messages": [
            {"role": "user", "content": "帮我做一个 7 天学习计划。"},
            {"role": "assistant", "content": "这里是一份详细的 7 天学习拆解计划，包含任务、时间块与里程碑。"},
        ],
        "context_data": {
            "chat_mode": "study_plan",
            "workflow_type": "task_decomposition",
            "tool_calls": [{"name": "get_plan_state"}],
        },
    }

    assert _should_skip_review(state) is False


def test_should_not_skip_review_for_explicit_expert_response():
    state = {
        "messages": [
            {"role": "user", "content": "请用两个专家讨论后给我答案。"},
            {"role": "assistant", "content": "这是综合两位专家观点后的最终答案。"},
        ],
        "context_data": {
            "chat_mode": 'team::{"agents":["deep_analyst","time_tutor"]}',
            "selected_experts": ["deep_analyst", "time_tutor"],
        },
    }

    assert _should_skip_review(state) is False


def test_should_skip_review_for_deep_analysis_without_tools():
    state = {
        "messages": [
            {"role": "user", "content": "请深度分析一下栈和队列的区别。"},
            {"role": "assistant", "content": "这是一个较长的深度分析回答。"},
        ],
        "context_data": {
            "chat_mode": "deep_analysis",
            "workflow_type": "progressive_exploration",
            "tool_calls": [],
        },
    }

    assert _should_skip_review(state) is True


def test_should_skip_review_for_short_tool_intermediate_response():
    state = {
        "messages": [
            {"role": "user", "content": "帮我看看计划。"},
            {"role": "assistant", "content": "我先帮你查一下当前计划状态。"},
        ],
        "context_data": {
            "chat_mode": "study_plan",
            "tool_calls": [{"name": "get_plan_state"}],
        },
    }

    assert _should_skip_review(state) is True
