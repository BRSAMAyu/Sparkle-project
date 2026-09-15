#!/usr/bin/env python3
"""
验证 standard_workflow.py 中的 collaboration_timeline 输出

测试目标：
1. collaboration_node 发送的 metadata 包含正确的 timeline 结构
2. schema_version == "1.0"
3. steps 包含所有必需字段
"""

import json
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.orchestration.statechart_engine import WorkflowState
from app.agents.collaboration_workflows import (
    TaskDecompositionWorkflow,
    CollaborationResult,
    _build_timeline_step
)


async def test_standard_workflow_collaboration_timeline():
    """测试 standard_workflow.py 中的 collaboration_timeline 输出"""
    print("\n=== 测试 standard_workflow.py collaboration_timeline ===")

    # 导入 collaboration_node (需要模拟依赖)
    from app.agents.standard_workflow import collaboration_node

    # 创建模拟的 CollaborationResult
    start_time = datetime.now()
    timeline = [
        _build_timeline_step("SearchExpert", "检索背景知识", start_time, output_summary="找到5个相关文档"),
        _build_timeline_step("StudyPlanner", "制定学习计划", start_time, output_summary="识别3个薄弱点"),
        _build_timeline_step("MathExpert", "生成练习题", start_time, output_summary="生成10道练习题"),
    ]

    mock_result = CollaborationResult(
        workflow_type="task_decomposition",
        participants=["SearchExpert", "StudyPlanner", "MathExpert"],
        outputs=[],
        final_response="完整的学习计划已生成...",
        reasoning="任务分解协作完成",
        metadata={"execution_time": 3.5},
        timeline=timeline,
        confidence=0.90
    )

    # 创建模拟的 stream_callback
    received_metadata = {}

    async def mock_stream_callback(response):
        """捕获发送的 metadata"""
        if hasattr(response, 'metadata') and response.metadata:
            received_metadata.update(response.metadata)

    # 创建 WorkflowState
    state = WorkflowState()
    state.messages = [{"role": "user", "content": "帮我准备期末考试"}]
    state.context_data = {
        "user_id": "test_user",
        "detected_intent": "task_decomposition",
        "stream_callback": mock_stream_callback,
    }

    # 模拟 workflow 执行
    with patch('app.agents.standard_workflow._select_workflow') as mock_select:
        with patch('app.agents.standard_workflow.EnhancedAgentContext') as mock_context:
            mock_select.return_value = TaskDecompositionWorkflow
            mock_context.return_value = Mock()

            # Mock workflow.execute
            with patch.object(TaskDecompositionWorkflow, 'execute', new=AsyncMock(return_value=mock_result)):
                # Mock _ensure_action_cards
                with patch('app.agents.standard_workflow._ensure_action_cards', new=AsyncMock(return_value=mock_result)):
                    # 执行 node
                    result_state = await collaboration_node(state)

    # 验证收到的 metadata
    assert "collaboration_timeline" in received_metadata, "缺少 collaboration_timeline"
    print("✅ collaboration_timeline 存在于发送的 metadata")

    # 解析 JSON
    timeline_json = received_metadata["collaboration_timeline"]
    timeline_data = json.loads(timeline_json)

    print(f"\n收到的 collaboration_timeline:")
    print(json.dumps(timeline_data, ensure_ascii=False, indent=2))

    # 验证 schema
    assert timeline_data["schema_version"] == "1.0"
    print("✅ schema_version == '1.0'")

    assert timeline_data["workflow_type"] == "task_decomposition"
    print("✅ workflow_type 正确")

    assert "steps" in timeline_data
    assert len(timeline_data["steps"]) == 3
    print(f"✅ 包含 {len(timeline_data['steps'])} 个步骤")

    # 验证每个 step 的必需字段
    for i, step in enumerate(timeline_data["steps"]):
        print(f"\n步骤 {i}: {step['agent_name']} - {step['action']}")

        required_fields = ["agent_name", "action", "status", "start_time_ms"]
        missing = [f for f in required_fields if f not in step]

        if missing:
            print(f"  ❌ 缺少字段: {missing}")
            assert False, f"步骤 {i} 缺少字段: {missing}"

        # 验证字段类型
        assert isinstance(step["agent_name"], str), "agent_name 必须是字符串"
        assert isinstance(step["action"], str), "action 必须是字符串"
        assert isinstance(step["status"], str), "status 必须是字符串"
        assert isinstance(step["start_time_ms"], int), "start_time_ms 必须是整数"

        print(f"  ✅ agent_name: {step['agent_name']}")
        print(f"  ✅ action: {step['action']}")
        print(f"  ✅ status: {step['status']}")
        print(f"  ✅ start_time_ms: {step['start_time_ms']}")

        # 可选字段
        if "duration_ms" in step:
            assert isinstance(step["duration_ms"], int)
            print(f"  ✅ duration_ms: {step['duration_ms']}")

        if "output_summary" in step:
            assert isinstance(step["output_summary"], str)
            print(f"  ✅ output_summary: {step['output_summary'][:50]}...")

    return True


async def main():
    """运行测试"""
    print("=" * 60)
    print("Standard Workflow Collaboration Timeline 验证")
    print("=" * 60)

    try:
        await test_standard_workflow_collaboration_timeline()
        print("\n" + "=" * 60)
        print("🎉 测试通过！standard_workflow.py 输出正确！")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ 测试错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
