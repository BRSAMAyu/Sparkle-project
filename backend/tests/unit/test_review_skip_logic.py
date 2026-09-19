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


def test_should_not_skip_review_for_final_study_plan_response_without_pending_tools():
    # wave5 对齐：现行语义是"所有生成内容都经过审查"（standard_workflow
    # generation→generation_review 边的注释），只有 standard 简短寒暄/工具
    # 进度提示跳过。study_plan 最终答复是实质性用户可见内容，仍需审查——
    # 5416b1d3 已修复审查超时（12s→45s）与 reflection 断链，42956c11 将
    # 审查系统错误从用户流抑制（fail-closed 保留），"也审查"的噪声代价已被
    # 消化。旧断言（无工具即跳过）在本仓库历史上从未实现过。
    state = {
        "messages": [
            {"role": "user", "content": "帮我做一个 7 天学习计划。"},
            {"role": "assistant", "content": "下面是结合你当前计划和任务整理出的 7 天执行拆解。"},
        ],
        "context_data": {
            "chat_mode": "study_plan",
            "workflow_type": "task_decomposition",
            "tool_calls": [],
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


def test_should_not_skip_review_for_deep_analysis_without_tools():
    # wave5 对齐：deep_analysis（无工具、无专家）在生产图里走
    # generation→generation_review（_should_disable_tools_for_deep_analysis
    # 只是关闭工具暴露，不绕过审查）。42956c11 在 deep_analysis 上做了三次
    # 实弹验证（幻觉 0/3），表明现行"深度分析也审查"是有意保留的质量闸门；
    # 审查超时不再向用户推错误文案（review_error 抑制），延迟与噪声代价
    # 已可控。若未来产品决定以延迟优先（审查 12-67s），应在 review_nodes
    # 增加 skip 分支并回翻本断言——见 testdebt-wave5.md 记录。
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

    assert _should_skip_review(state) is False


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
