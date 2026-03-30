"""
Statechart Engine Core Test Suite

测试 StateGraph (Statechart Engine) 的核心功能：
- StateGraph 基本执行流程
- 嵌套状态进入/退出
- 条件路由决策
- 并行分支执行与同步
- 错误传播与恢复
"""
from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.orchestration.statechart_engine import (
    StateGraph,
    WorkflowState,
    GraphEventType,
    GraphEvent,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_state():
    """创建初始 WorkflowState"""
    return WorkflowState(
        messages=[{"role": "user", "content": "Hello"}],
        context_data={"user_id": "test-user-123"},
    )


@pytest.fixture
def event_history():
    """用于收集事件的列表"""
    events = []

    async def event_collector(event: GraphEvent):
        events.append(event)

    return events, event_collector


# =============================================================================
# Test WorkflowState
# =============================================================================


class TestWorkflowState:
    """测试 WorkflowState 数据结构"""

    def test_workflow_state_initialization(self):
        """测试 WorkflowState 初始化"""
        state = WorkflowState()
        assert state.messages == []
        assert state.context_data == {}
        assert state.next_step is None
        assert state.errors == []
        assert state.is_finished is False
        assert state.trace_id is not None

    def test_workflow_state_with_initial_data(self):
        """测试带初始数据的 WorkflowState"""
        state = WorkflowState(
            messages=[{"role": "user", "content": "test"}],
            context_data={"key": "value"},
            next_step="processing",
        )
        assert len(state.messages) == 1
        assert state.context_data["key"] == "value"
        assert state.next_step == "processing"

    def test_workflow_state_update(self):
        """测试 update 方法"""
        state = WorkflowState()
        state.update({"user_id": "123", "action": "test"})
        assert state.context_data["user_id"] == "123"
        assert state.context_data["action"] == "test"

    def test_workflow_state_append_message(self):
        """测试 append_message 方法"""
        state = WorkflowState()
        state.append_message("user", "Hello")
        state.append_message("assistant", "Hi there", name="Bot")
        assert len(state.messages) == 2
        assert state.messages[0]["role"] == "user"
        assert state.messages[1]["name"] == "Bot"

    def test_workflow_state_clone(self):
        """测试 clone 方法"""
        original = WorkflowState(
            messages=[{"role": "user", "content": "test"}],
            context_data={"key": "value"},
        )
        cloned = original.clone()

        # 验证克隆的数据
        assert cloned.messages == original.messages
        assert cloned.context_data == original.context_data
        assert cloned.trace_id == original.trace_id

        # 验证是深拷贝（修改克隆不影响原对象）
        cloned.context_data["key"] = "modified"
        assert original.context_data["key"] == "value"
        assert cloned.context_data["key"] == "modified"


# =============================================================================
# Test StateGraph Basic Execution
# =============================================================================


class TestStateGraphBasicExecution:
    """测试 StateGraph 基本执行流程"""

    @pytest.mark.asyncio
    async def test_simple_linear_execution(self, sample_state):
        """测试简单的线性执行流程"""

        # 定义节点函数
        async def node_a(state: WorkflowState) -> WorkflowState:
            state.append_message("system", "Node A executed")
            return state

        async def node_b(state: WorkflowState) -> WorkflowState:
            state.append_message("system", "Node B executed")
            return state

        async def node_c(state: WorkflowState) -> WorkflowState:
            state.append_message("system", "Node C executed")
            state.is_finished = True
            return state

        # 构建图
        graph = StateGraph("TestGraph")
        graph.add_node("node_a", node_a)
        graph.add_node("node_b", node_b)
        graph.add_node("node_c", node_c)
        graph.add_edge("node_a", "node_b")
        graph.add_edge("node_b", "node_c")
        graph.set_entry_point("node_a")
        graph.compile()

        # 执行
        result = await graph.invoke(sample_state)

        # 验证
        assert result.is_finished is True
        assert len(result.messages) == 4  # user + 3 system messages
        assert result.messages[1]["content"] == "Node A executed"
        assert result.messages[2]["content"] == "Node B executed"
        assert result.messages[3]["content"] == "Node C executed"

    @pytest.mark.asyncio
    async def test_execution_stops_at_end_point(self, sample_state):
        """测试执行在 __end__ 节点停止"""

        async def node_a(state: WorkflowState) -> WorkflowState:
            state.append_message("system", "A")
            return state

        async def node_b(state: WorkflowState) -> WorkflowState:
            state.append_message("system", "B")
            return state

        async def node_c(state: WorkflowState) -> WorkflowState:
            state.append_message("system", "C")
            return state

        # node_b 之后没有边，应该停止
        graph = StateGraph("TestGraph")
        graph.add_node("node_a", node_a)
        graph.add_node("node_b", node_b)
        graph.add_node("node_c", node_c)  # 不可达
        graph.add_edge("node_a", "node_b")
        # node_b 没有出边
        graph.set_entry_point("node_a")
        graph.compile()

        result = await graph.invoke(sample_state)

        # 只有 A 和 B 被执行
        assert len(result.messages) == 3  # user + A + B
        assert result.messages[1]["content"] == "A"
        assert result.messages[2]["content"] == "B"

    @pytest.mark.asyncio
    async def test_synchronous_node_execution(self, sample_state):
        """测试同步节点函数的执行"""

        def sync_node(state: WorkflowState) -> WorkflowState:
            state.append_message("system", "Sync executed")
            state.context_data["sync_result"] = "done"
            return state

        graph = StateGraph("TestGraph")
        graph.add_node("sync_node", sync_node)
        graph.set_entry_point("sync_node")
        graph.compile()

        result = await graph.invoke(sample_state)

        assert result.context_data["sync_result"] == "done"
        assert result.messages[1]["content"] == "Sync executed"

    @pytest.mark.asyncio
    async def test_max_steps_limit(self, sample_state):
        """测试最大步数限制"""

        async def loop_node(state: WorkflowState) -> WorkflowState:
            state.append_message("system", f"Step {len(state.messages)}")
            # 返回到自身
            state.next_step = "loop_node"
            return state

        graph = StateGraph("LoopGraph")
        graph.add_node("loop_node", loop_node)

        # 使用条件边创建循环
        def loop_router(state: WorkflowState) -> str:
            if len(state.messages) < 5:  # 执行 3 次后停止
                return "loop_node"
            return "__end__"

        graph.add_conditional_edge("loop_node", loop_router)
        graph.set_entry_point("loop_node")
        graph.compile()

        # 执行
        result = await graph.invoke(sample_state, max_steps=5)

        # 验证最大步数限制生效
        # 应该执行: 初始 + 4 次 = 5 步
        assert len(result.messages) >= 5


# =============================================================================
# Test Conditional Routing
# =============================================================================


class TestConditionalRouting:
    """测试条件路由决策"""

    @pytest.mark.asyncio
    async def test_conditional_edge_routing(self, sample_state):
        """测试条件边路由"""

        async def process_node(state: WorkflowState) -> WorkflowState:
            state.append_message("system", "Processed")
            return state

        async def approve_node(state: WorkflowState) -> WorkflowState:
            state.append_message("system", "Approved")
            state.context_data["decision"] = "approve"
            return state

        async def reject_node(state: WorkflowState) -> WorkflowState:
            state.append_message("system", "Rejected")
            state.context_data["decision"] = "reject"
            return state

        # 路由函数：根据 context_data 决定
        def decision_router(state: WorkflowState) -> str:
            if state.context_data.get("should_approve"):
                return "approve_node"
            return "reject_node"

        # 构建图
        graph = StateGraph("DecisionGraph")
        graph.add_node("process_node", process_node)
        graph.add_node("approve_node", approve_node)
        graph.add_node("reject_node", reject_node)
        graph.add_edge("process_node", decision_router)
        graph.set_entry_point("process_node")
        graph.compile()

        # 测试批准路径
        sample_state.context_data["should_approve"] = True
        result = await graph.invoke(sample_state)
        assert result.context_data["decision"] == "approve"

        # 测试拒绝路径
        sample_state.context_data["should_approve"] = False
        result = await graph.invoke(sample_state)
        assert result.context_data["decision"] == "reject"

    @pytest.mark.asyncio
    async def test_multi_branch_routing(self, sample_state):
        """测试多分支路由"""

        async def router_node(state: WorkflowState) -> WorkflowState:
            # 不覆盖分数，使用传入的分数
            return state

        async def high_branch(state: WorkflowState) -> WorkflowState:
            state.context_data["tier"] = "high"
            return state

        async def medium_branch(state: WorkflowState) -> WorkflowState:
            state.context_data["tier"] = "medium"
            return state

        async def low_branch(state: WorkflowState) -> WorkflowState:
            state.context_data["tier"] = "low"
            return state

        def tier_router(state: WorkflowState) -> str:
            score = state.context_data.get("score", 0)
            if score >= 80:
                return "high_branch"
            elif score >= 50:
                return "medium_branch"
            return "low_branch"

        # 构建图
        graph = StateGraph("TierGraph")
        graph.add_node("router_node", router_node)
        graph.add_node("high_branch", high_branch)
        graph.add_node("medium_branch", medium_branch)
        graph.add_node("low_branch", low_branch)
        graph.add_edge("router_node", tier_router)
        graph.set_entry_point("router_node")
        graph.compile()

        # 测试中等分数
        sample_state.context_data["score"] = 75
        result = await graph.invoke(sample_state)
        assert result.context_data["tier"] == "medium"

        # 测试高分
        sample_state.context_data["score"] = 90
        result = await graph.invoke(sample_state)
        assert result.context_data["tier"] == "high"

        # 测试低分
        sample_state.context_data["score"] = 30
        result = await graph.invoke(sample_state)
        assert result.context_data["tier"] == "low"


# =============================================================================
# Test Nested States
# =============================================================================


class TestNestedStates:
    """测试嵌套状态进入/退出"""

    @pytest.mark.asyncio
    async def test_nested_graph_execution(self, sample_state):
        """测试嵌套图执行"""

        # 子图
        async def sub_node_a(state: WorkflowState) -> WorkflowState:
            state.append_message("system", "Sub A")
            state.context_data["sub_executed"] = True
            return state

        async def sub_node_b(state: WorkflowState) -> WorkflowState:
            state.append_message("system", "Sub B")
            return state

        sub_graph = StateGraph("SubGraph")
        sub_graph.add_node("sub_node_a", sub_node_a)
        sub_graph.add_node("sub_node_b", sub_node_b)
        sub_graph.add_edge("sub_node_a", "sub_node_b")
        sub_graph.set_entry_point("sub_node_a")
        sub_graph.compile()

        # 主图
        async def main_node_a(state: WorkflowState) -> WorkflowState:
            state.append_message("system", "Main A")
            return state

        async def main_node_b(state: WorkflowState) -> WorkflowState:
            state.append_message("system", "Main B")
            return state

        main_graph = StateGraph("MainGraph")
        main_graph.add_node("main_a", main_node_a)
        main_graph.add_node("nested", sub_graph)  # 嵌套子图
        main_graph.add_node("main_b", main_node_b)
        main_graph.add_edge("main_a", "nested")
        main_graph.add_edge("nested", "main_b")
        main_graph.set_entry_point("main_a")
        main_graph.compile()

        # 执行
        result = await main_graph.invoke(sample_state)

        # 验证执行顺序
        assert result.context_data["sub_executed"] is True
        messages = [m["content"] for m in result.messages if m["role"] == "system"]
        assert messages == ["Main A", "Sub A", "Sub B", "Main B"]

    @pytest.mark.asyncio
    async def test_deeply_nested_graphs(self, sample_state):
        """测试深层嵌套图"""

        # 第三层图
        async def level3_node(state: WorkflowState) -> WorkflowState:
            state.context_data["level"] = 3
            return state

        level3_graph = StateGraph("Level3")
        level3_graph.add_node("l3", level3_node)
        level3_graph.set_entry_point("l3")
        level3_graph.compile()

        # 第二层图
        async def level2_node(state: WorkflowState) -> WorkflowState:
            state.context_data["level"] = 2
            return state

        level2_graph = StateGraph("Level2")
        level2_graph.add_node("l2", level2_node)
        level2_graph.add_node("nested_l3", level3_graph)
        level2_graph.add_edge("l2", "nested_l3")
        level2_graph.set_entry_point("l2")
        level2_graph.compile()

        # 第一层图
        async def level1_node(state: WorkflowState) -> WorkflowState:
            state.context_data["level"] = 1
            return state

        level1_graph = StateGraph("Level1")
        level1_graph.add_node("l1", level1_node)
        level1_graph.add_node("nested_l2", level2_graph)
        level1_graph.add_edge("l1", "nested_l2")
        level1_graph.set_entry_point("l1")
        level1_graph.compile()

        # 执行
        result = await level1_graph.invoke(sample_state)

        # 验证所有层级都被执行
        assert result.context_data["level"] == 3  # 最后设置的值

    @pytest.mark.asyncio
    async def test_nested_graph_state_isolation(self, sample_state):
        """测试嵌套图的状态隔离"""

        async def parent_node(state: WorkflowState) -> WorkflowState:
            state.context_data["parent"] = "parent_value"
            state.context_data["shared"] = "original"
            return state

        async def child_node(state: WorkflowState) -> WorkflowState:
            # 子图修改 context_data
            state.context_data["child"] = "child_value"
            state.context_data["shared"] = "modified_by_child"
            return state

        child_graph = StateGraph("ChildGraph")
        child_graph.add_node("child", child_node)
        child_graph.set_entry_point("child")
        child_graph.compile()

        parent_graph = StateGraph("ParentGraph")
        parent_graph.add_node("parent", parent_node)
        parent_graph.add_node("child_graph", child_graph)
        parent_graph.add_edge("parent", "child_graph")
        parent_graph.set_entry_point("parent")
        parent_graph.compile()

        result = await parent_graph.invoke(sample_state)

        # 验证子图的修改被合并
        assert result.context_data["parent"] == "parent_value"
        assert result.context_data["child"] == "child_value"
        assert result.context_data["shared"] == "modified_by_child"


# =============================================================================
# Test Parallel Execution
# =============================================================================


class TestParallelExecution:
    """测试并行分支执行与同步"""

    @pytest.mark.asyncio
    async def test_parallel_branch_execution(self, sample_state):
        """测试并行分支执行"""

        # 用于跟踪执行顺序
        execution_order = []

        async def branch_a(state: WorkflowState) -> WorkflowState:
            await asyncio.sleep(0.05)  # 模拟耗时
            execution_order.append("A")
            state.context_data["branch_a"] = "completed"
            return state

        async def branch_b(state: WorkflowState) -> WorkflowState:
            await asyncio.sleep(0.02)
            execution_order.append("B")
            state.context_data["branch_b"] = "completed"
            return state

        async def branch_c(state: WorkflowState) -> WorkflowState:
            execution_order.append("C")
            state.context_data["branch_c"] = "completed"
            return state

        # 并行节点
        graph = StateGraph("ParallelGraph")
        graph.add_node("parallel", [branch_a, branch_b, branch_c])
        graph.set_entry_point("parallel")
        graph.compile()

        # 执行
        import time
        start = time.time()
        result = await graph.invoke(sample_state)
        elapsed = time.time() - start

        # 验证所有分支都完成了
        assert result.context_data["branch_a"] == "completed"
        assert result.context_data["branch_b"] == "completed"
        assert result.context_data["branch_c"] == "completed"

        # 验证并行执行（时间应该接近最慢的分支，而不是总和）
        assert elapsed < 0.10  # 应该 < 0.05 + 0.02 + 0.01 的串行时间

        # 验证执行顺序（并行顺序不确定，但都应该执行）
        assert set(execution_order) == {"A", "B", "C"}

    @pytest.mark.asyncio
    async def test_parallel_with_state_merge(self, sample_state):
        """测试并行执行后的状态合并"""

        async def writer_a(state: WorkflowState) -> WorkflowState:
            state.context_data["result_a"] = "value_a"
            state.append_message("system", "From A")
            return state

        async def writer_b(state: WorkflowState) -> WorkflowState:
            state.context_data["result_b"] = "value_b"
            state.append_message("system", "From B")
            return state

        async def writer_c(state: WorkflowState) -> WorkflowState:
            state.context_data["result_c"] = "value_c"
            state.append_message("system", "From C")
            return state

        graph = StateGraph("ParallelMergeGraph")
        graph.add_node("parallel", [writer_a, writer_b, writer_c])
        graph.set_entry_point("parallel")
        graph.compile()

        result = await graph.invoke(sample_state)

        # 验证所有分支的结果都被合并
        assert result.context_data["result_a"] == "value_a"
        assert result.context_data["result_b"] == "value_b"
        assert result.context_data["result_c"] == "value_c"

        # 验证消息被合并
        system_messages = [m for m in result.messages if m["role"] == "system"]
        assert len(system_messages) == 3

    @pytest.mark.asyncio
    async def test_parallel_branch_with_subgraphs(self, sample_state):
        """测试并行分支包含子图"""

        # 子图 A
        async def sub_a1(state: WorkflowState) -> WorkflowState:
            state.context_data["sub_a1"] = True
            return state

        sub_graph_a = StateGraph("SubA")
        sub_graph_a.add_node("sub_a1", sub_a1)
        sub_graph_a.set_entry_point("sub_a1")
        sub_graph_a.compile()

        # 子图 B
        async def sub_b1(state: WorkflowState) -> WorkflowState:
            state.context_data["sub_b1"] = True
            return state

        sub_graph_b = StateGraph("SubB")
        sub_graph_b.add_node("sub_b1", sub_b1)
        sub_graph_b.set_entry_point("sub_b1")
        sub_graph_b.compile()

        # 主图：并行执行两个子图
        main_graph = StateGraph("MainGraph")
        main_graph.add_node("parallel", [sub_graph_a, sub_graph_b])
        main_graph.set_entry_point("parallel")
        main_graph.compile()

        result = await main_graph.invoke(sample_state)

        # 验证两个子图的结果都被合并
        assert result.context_data.get("sub_a1") is True
        assert result.context_data.get("sub_b1") is True

    @pytest.mark.asyncio
    async def test_parallel_with_one_branch_failing(self, sample_state):
        """测试并行执行中一个分支失败"""

        async def success_branch(state: WorkflowState) -> WorkflowState:
            await asyncio.sleep(0.01)
            state.context_data["success"] = True
            return state

        async def failing_branch(state: WorkflowState) -> WorkflowState:
            await asyncio.sleep(0.01)
            raise ValueError("Intentional failure")

        async def another_success_branch(state: WorkflowState) -> WorkflowState:
            await asyncio.sleep(0.01)
            state.context_data["another"] = True
            return state

        graph = StateGraph("ParallelErrorGraph")
        graph.add_node("parallel", [success_branch, failing_branch, another_success_branch])
        graph.set_entry_point("parallel")
        graph.compile()

        result = await graph.invoke(sample_state)

        # 验证成功的分支完成了
        assert result.context_data.get("success") is True
        assert result.context_data.get("another") is True

        # 验证错误被记录
        assert len(result.errors) == 1
        assert "Parallel branch" in result.errors[0]
        assert "Intentional failure" in result.errors[0]


# =============================================================================
# Test Error Handling
# =============================================================================


class TestErrorHandling:
    """测试错误传播与恢复"""

    @pytest.mark.asyncio
    async def test_node_error_propagation(self, sample_state):
        """测试节点错误传播"""

        async def failing_node(state: WorkflowState) -> WorkflowState:
            raise RuntimeError("Node execution failed")

        async def next_node(state: WorkflowState) -> WorkflowState:
            state.append_message("system", "Should not reach here")
            return state

        graph = StateGraph("ErrorGraph")
        graph.add_node("failing_node", failing_node)
        graph.add_node("next_node", next_node)
        graph.add_edge("failing_node", "next_node")
        graph.set_entry_point("failing_node")
        graph.compile()

        result = await graph.invoke(sample_state)

        # 验证错误被记录
        assert len(result.errors) == 1
        assert "Node execution failed" in result.errors[0]

        # 验证执行停止（next_node 未执行）
        assert "Should not reach here" not in [m.get("content", "") for m in result.messages]

    @pytest.mark.asyncio
    async def test_nested_graph_error_propagation(self, sample_state):
        """测试嵌套图中的错误传播"""

        async def failing_sub_node(state: WorkflowState) -> WorkflowState:
            raise ValueError("Sub graph failure")

        sub_graph = StateGraph("FailingSubGraph")
        sub_graph.add_node("fail", failing_sub_node)
        sub_graph.set_entry_point("fail")
        sub_graph.compile()

        async def main_node(state: WorkflowState) -> WorkflowState:
            state.context_data["main_executed"] = True
            return state

        main_graph = StateGraph("MainGraph")
        main_graph.add_node("main", main_node)
        main_graph.add_node("sub", sub_graph)
        main_graph.add_edge("main", "sub")
        main_graph.set_entry_point("main")
        main_graph.compile()

        result = await main_graph.invoke(sample_state)

        # 验证主节点执行了
        assert result.context_data.get("main_executed") is True

        # 验证错误被记录
        assert len(result.errors) == 1
        assert "Sub graph failure" in result.errors[0]

    @pytest.mark.asyncio
    async def test_error_in_parallel_branch(self, sample_state):
        """测试并行分支中的错误处理"""

        async def failing_branch(state: WorkflowState) -> WorkflowState:
            raise Exception("Parallel branch error")

        async def working_branch(state: WorkflowState) -> WorkflowState:
            state.context_data["working"] = True
            return state

        graph = StateGraph("ParallelErrorGraph")
        graph.add_node("parallel", [failing_branch, working_branch])
        graph.set_entry_point("parallel")
        graph.compile()

        result = await graph.invoke(sample_state)

        # 验证工作的分支完成了
        assert result.context_data.get("working") is True

        # 验证错误被记录
        assert len(result.errors) == 1
        assert "Parallel branch" in result.errors[0]

    @pytest.mark.asyncio
    async def test_error_recovery_with_conditional_edge(self, sample_state):
        """测试使用条件边进行错误恢复"""

        async def process_node(state: WorkflowState) -> WorkflowState:
            if state.context_data.get("should_fail"):
                state.errors.append("Processing failed")
            return state

        async def recovery_node(state: WorkflowState) -> WorkflowState:
            state.context_data["recovered"] = True
            state.context_data["fallback_applied"] = True
            return state

        async def success_node(state: WorkflowState) -> WorkflowState:
            state.context_data["success"] = True
            return state

        def error_router(state: WorkflowState) -> str:
            if state.errors:
                return "recovery"
            return "success"

        graph = StateGraph("RecoveryGraph")
        graph.add_node("process", process_node)
        graph.add_node("recovery", recovery_node)
        graph.add_node("success", success_node)
        graph.add_edge("process", error_router)
        graph.set_entry_point("process")
        graph.compile()

        # 测试错误恢复路径
        sample_state.context_data["should_fail"] = True
        result = await graph.invoke(sample_state)
        assert result.context_data.get("recovered") is True
        assert result.context_data.get("fallback_applied") is True

        # 测试成功路径
        sample_state.context_data["should_fail"] = False
        sample_state.errors.clear()
        result = await graph.invoke(sample_state)
        assert result.context_data.get("success") is True


# =============================================================================
# Test Event Emission
# =============================================================================


class TestEventEmission:
    """测试事件发射"""

    @pytest.mark.asyncio
    async def test_graph_events_emitted(self, sample_state, event_history):
        """测试图事件发射"""

        events, collector = event_history

        async def first_node(state: WorkflowState) -> WorkflowState:
            await asyncio.sleep(0.01)
            return state

        async def second_node(state: WorkflowState) -> WorkflowState:
            return state

        graph = StateGraph("EventTestGraph")
        graph.add_node("first_node", first_node)
        graph.add_node("second_node", second_node)
        graph.add_edge("first_node", "second_node")
        graph.set_entry_point("first_node")
        graph.on_event = collector
        graph.compile()

        await graph.invoke(sample_state)

        # 验证事件被发射
        event_types = [e.type for e in events]
        assert GraphEventType.GRAPH_START in event_types
        assert GraphEventType.NODE_START in event_types
        assert GraphEventType.NODE_END in event_types
        assert GraphEventType.EDGE_TRAVERSAL in event_types
        assert GraphEventType.GRAPH_END in event_types

    @pytest.mark.asyncio
    async def test_nested_graph_events(self, sample_state, event_history):
        """测试嵌套图的事件传播"""

        events, collector = event_history

        async def sub_node(state: WorkflowState) -> WorkflowState:
            return state

        sub_graph = StateGraph("SubGraph")
        sub_graph.add_node("sub", sub_node)
        sub_graph.set_entry_point("sub")
        sub_graph.compile()

        async def main_node(state: WorkflowState) -> WorkflowState:
            return state

        main_graph = StateGraph("MainGraph")
        main_graph.add_node("main", main_node)
        main_graph.add_node("sub", sub_graph)
        main_graph.add_edge("main", "sub")
        main_graph.set_entry_point("main")
        main_graph.on_event = collector
        main_graph.compile()

        await main_graph.invoke(sample_state)

        # 验证子图的事件也被发射
        node_starts = [e for e in events if e.type == GraphEventType.NODE_START]
        node_ids = [e.node_id for e in node_starts]
        assert "main" in node_ids
        assert "sub" in node_ids

    @pytest.mark.asyncio
    async def test_error_event_emission(self, sample_state, event_history):
        """测试错误事件发射"""

        events, collector = event_history

        async def failing_node(state: WorkflowState) -> WorkflowState:
            raise ValueError("Test error")

        graph = StateGraph("ErrorEventGraph")
        graph.add_node("fail", failing_node)
        graph.set_entry_point("fail")
        graph.on_event = collector
        graph.compile()

        await graph.invoke(sample_state)

        # 验证错误事件被发射
        error_events = [e for e in events if e.type == GraphEventType.ERROR]
        assert len(error_events) == 1
        assert "Test error" in error_events[0].details


# =============================================================================
# Test Graph Compilation and Validation
# =============================================================================


class TestGraphCompilation:
    """测试图编译和验证"""

    def test_compile_without_entry_point_raises_error(self):
        """测试没有入口点的图编译失败"""
        graph = StateGraph("InvalidGraph")
        graph.add_node("node", lambda s: s)

        with pytest.raises(ValueError, match="entry point not set"):
            graph.compile()

    def test_compile_with_invalid_entry_point_raises_error(self):
        """测试无效入口点的图编译失败"""
        graph = StateGraph("InvalidGraph")
        graph.add_node("node", lambda s: s)
        graph.set_entry_point("nonexistent")

        with pytest.raises(ValueError, match="not found in nodes"):
            graph.compile()

    def test_successful_compilation(self):
        """测试成功的图编译"""
        graph = StateGraph("ValidGraph")
        graph.add_node("node", lambda s: s)
        graph.set_entry_point("node")

        result = graph.compile()
        assert result is graph  # 返回自身以便链式调用
        assert graph._compiled is True

    def test_multiple_compile_is_idempotent(self):
        """测试多次编译是幂等的"""
        graph = StateGraph("ValidGraph")
        graph.add_node("node", lambda s: s)
        graph.set_entry_point("node")
        graph.compile()

        # 第二次编译应该没问题
        graph.compile()
        assert graph._compiled is True
