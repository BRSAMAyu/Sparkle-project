#!/usr/bin/env python3
"""
快速验证 collaboration_timeline schema v1.0

测试目标：
1. metadata.collaboration_timeline.schema_version == "1.0"
2. steps[*] 包含必需字段: agent_name, action, status, start_time_ms
"""

import json
from app.agents.collaboration_workflows import (
    TaskDecompositionWorkflow,
    ProgressiveExplorationWorkflow,
    ErrorDiagnosisWorkflow,
    CollaborationResult,
    _build_timeline_step
)
from app.agents.enhanced_agents import EnhancedAgentContext
from app.agents.enhanced_orchestrator import EnhancedOrchestratorAgent
from datetime import datetime


def test_build_timeline_step_schema():
    """测试 _build_timeline_step 生成符合 v1.0 schema 的步骤"""
    print("\n=== 测试 _build_timeline_step ===")

    start_time = datetime.now()
    step = _build_timeline_step(
        agent_name="TestAgent",
        action="测试动作",
        start_time=start_time,
        status="completed",
        output_summary="测试输出"
    )

    print(f"生成的 step: {json.dumps(step, ensure_ascii=False, indent=2)}")

    # 验证必需字段
    required_fields = ["agent_name", "action", "status", "start_time_ms"]
    for field in required_fields:
        assert field in step, f"缺少必需字段: {field}"
        print(f"✅ 字段 {field} 存在")

    # 验证字段类型
    assert isinstance(step["agent_name"], str)
    assert isinstance(step["action"], str)
    assert isinstance(step["status"], str)
    assert isinstance(step["start_time_ms"], int)
    print("✅ 字段类型正确")

    # 验证可选字段
    assert "duration_ms" in step
    assert isinstance(step["duration_ms"], int)
    assert step["duration_ms"] >= 0
    print("✅ duration_ms 存在且为非负整数")

    return True


def test_collaboration_result_timeline():
    """测试 CollaborationResult.timeline 结构"""
    print("\n=== 测试 CollaborationResult.timeline ===")

    start_time = datetime.now()
    timeline = [
        _build_timeline_step("Agent1", "动作1", start_time, status="completed"),
        _build_timeline_step("Agent2", "动作2", start_time, status="running"),
    ]

    result = CollaborationResult(
        workflow_type="test_workflow",
        participants=["Agent1", "Agent2"],
        outputs=[],
        final_response="测试响应",
        reasoning="测试推理",
        metadata={},
        timeline=timeline,
        confidence=0.9
    )

    print(f"Timeline 包含 {len(result.timeline)} 个步骤")

    # 验证每个步骤的 schema
    for i, step in enumerate(result.timeline):
        print(f"\n步骤 {i}: {step['agent_name']} - {step['action']}")
        required_fields = ["agent_name", "action", "status", "start_time_ms"]
        for field in required_fields:
            assert field in step, f"步骤 {i} 缺少字段: {field}"
        print(f"  ✅ 包含所有必需字段")

    return True


def test_enhanced_orchestrator_response_format():
    """测试 EnhancedOrchestrator 输出的 collaboration_timeline 格式"""
    print("\n=== 测试 EnhancedOrchestrator._format_collaboration_response ===")

    orchestrator = EnhancedOrchestratorAgent()

    # 创建模拟的 CollaborationResult
    start_time = datetime.now()
    timeline = [
        _build_timeline_step("StudyPlanner", "分析学习状态", start_time),
        _build_timeline_step("MathExpert", "生成练习题", start_time),
    ]

    mock_result = CollaborationResult(
        workflow_type="task_decomposition",
        participants=["StudyPlanner", "MathExpert"],
        outputs=[],
        final_response="完整的学习计划...",
        reasoning="任务分解协作完成",
        metadata={"execution_time": 2.5},
        timeline=timeline,
        confidence=0.88
    )

    # 格式化响应
    response = orchestrator._format_collaboration_response(mock_result)

    print(f"Response metadata keys: {list(response.metadata.keys())}")

    # 验证 collaboration_timeline 存在
    assert "collaboration_timeline" in response.metadata
    print("✅ collaboration_timeline 存在于 metadata")

    # 解析 JSON 字符串
    timeline_json = response.metadata["collaboration_timeline"]
    timeline_data = json.loads(timeline_json)

    print(f"\nParsed collaboration_timeline:")
    print(json.dumps(timeline_data, ensure_ascii=False, indent=2))

    # 验证 schema_version
    assert "schema_version" in timeline_data
    assert timeline_data["schema_version"] == "1.0"
    print("✅ schema_version == '1.0'")

    # 验证顶层字段
    assert "workflow_type" in timeline_data
    assert "execution_time_ms" in timeline_data
    assert "steps" in timeline_data
    print("✅ 包含顶层字段: workflow_type, execution_time_ms, steps")

    # 验证每个 step
    for i, step in enumerate(timeline_data["steps"]):
        print(f"\n步骤 {i}:")
        print(f"  agent_name: {step['agent_name']}")
        print(f"  action: {step['action']}")
        print(f"  status: {step['status']}")
        print(f"  start_time_ms: {step['start_time_ms']}")

        required_fields = ["agent_name", "action", "status", "start_time_ms"]
        for field in required_fields:
            assert field in step, f"步骤 {i} 缺少字段: {field}"
        print(f"  ✅ 包含所有必需字段")

    return True


def test_timeline_monotonic_timestamps():
    """测试时间戳单调递增"""
    print("\n=== 测试时间戳单调递增 ===")

    start_time = datetime.now()
    step1 = _build_timeline_step("Agent1", "First", start_time)

    # 稍后执行第二个步骤
    import time
    time.sleep(0.01)
    step2 = _build_timeline_step("Agent2", "Second", start_time)

    print(f"Step 1 start_time_ms: {step1['start_time_ms']}")
    print(f"Step 2 start_time_ms: {step2['start_time_ms']}")

    # start_time_ms 应该是绝对时间戳，所以后续步骤应该更大
    assert step2['start_time_ms'] >= step1['start_time_ms']
    print("✅ 时间戳单调递增")

    return True


def main():
    """运行所有测试"""
    print("=" * 60)
    print("Collaboration Timeline Schema v1.0 验证")
    print("=" * 60)

    tests = [
        test_build_timeline_step_schema,
        test_collaboration_result_timeline,
        test_enhanced_orchestrator_response_format,
        test_timeline_monotonic_timestamps,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"\n❌ 测试失败: {test.__name__}")
            print(f"   错误: {e}")
            failed += 1
        except Exception as e:
            print(f"\n❌ 测试错误: {test.__name__}")
            print(f"   错误: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)

    if failed == 0:
        print("\n🎉 所有测试通过！Schema v1.0 验证成功！")
        return 0
    else:
        print(f"\n⚠️  有 {failed} 个测试失败")
        return 1


if __name__ == "__main__":
    exit(main())
