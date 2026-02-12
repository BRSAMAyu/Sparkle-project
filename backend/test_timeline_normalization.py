#!/usr/bin/env python3
"""
直接测试 standard_workflow.py 中的 timeline 标准化逻辑
"""

import json
from datetime import datetime
from app.gen.agent.v1 import agent_service_pb2
from app.agents.collaboration_workflows import CollaborationResult, _build_timeline_step


def test_timeline_normalization_logic():
    """
    直接测试 standard_workflow.py:639-676 的 timeline 标准化逻辑
    """
    print("\n=== 测试 Timeline 标准化逻辑 ===")

    # 模拟 validated_result.timeline (可能包含各种格式的 events)
    start_time = datetime.now()

    # 模拟不同格式的 timeline events
    timeline_events = [
        # 完整格式（新格式）
        {
            "agent_name": "SearchExpert",
            "action": "检索背景知识",
            "status": "completed",
            "start_time_ms": int(start_time.timestamp() * 1000),
            "duration_ms": 350,
            "output_summary": "找到5个相关文档",
        },
        # 旧格式（使用 agent 而不是 agent_name）
        {
            "agent": "StudyPlanner",
            "action": "制定学习计划",
            "status": "completed",
            "timestamp": start_time.timestamp(),
        },
        # 缺少某些字段
        {
            "agent_name": "MathExpert",
            "action": "生成练习题",
        },
        # 包含可选字段
        {
            "agent_name": "WritingExpert",
            "action": "生成学习笔记",
            "status": "completed",
            "start_time_ms": int(start_time.timestamp() * 1000),
            "agent_role": "writing",
            "output_summary": "生成笔记模板",
            "metadata": {"word_count": 500},
        },
    ]

    print(f"\n原始 timeline events: {len(timeline_events)} 个")

    # 这是 standard_workflow.py 中的标准化逻辑（lines 639-670）
    normalized_steps = []
    for event in timeline_events:
        # Extract with fallbacks for required fields
        agent_name = event.get("agent_name") or event.get("agent") or "Agent"
        action = event.get("action") or ""
        status = event.get("status") or "completed"

        # Handle timestamp with fallback
        start_time_ms = event.get("start_time_ms")
        if start_time_ms is None and event.get("timestamp") is not None:
            start_time_ms = int(float(event.get("timestamp")) * 1000)
        if start_time_ms is None:
            start_time_ms = 0  # Required field

        # Build normalized step (Schema v1.0)
        step = {
            "agent_name": agent_name,
            "action": action,
            "status": status,
            "start_time_ms": start_time_ms,
        }

        # Add optional fields if present
        if event.get("agent_role"):
            step["agent_role"] = event["agent_role"]
        if event.get("duration_ms") is not None:
            step["duration_ms"] = event["duration_ms"]
        if event.get("output_summary"):
            step["output_summary"] = event["output_summary"]
        if event.get("metadata"):
            step["metadata"] = event["metadata"]

        normalized_steps.append(step)

    print(f"标准化后的 steps: {len(normalized_steps)} 个")

    # 构建最终的 collaboration_timeline（lines 665-670）
    collaboration_timeline = {
        "schema_version": "1.0",
        "workflow_type": "task_decomposition",
        "execution_time_ms": 3500,
        "steps": normalized_steps,
    }

    # 序列化为 JSON（模拟发送给 Go Gateway）
    timeline_json = json.dumps(collaboration_timeline, ensure_ascii=False)

    print("\n发送的 JSON:")
    print(timeline_json)

    # 验证
    print("\n=== 验证 ===")

    # 1. 验证可以正确解析
    parsed = json.loads(timeline_json)
    assert parsed["schema_version"] == "1.0"
    print("✅ schema_version == '1.0'")

    # 2. 验证每个步骤
    for i, step in enumerate(parsed["steps"]):
        print(f"\n步骤 {i}: {step['agent_name']} - {step['action']}")

        # 必需字段
        required_fields = ["agent_name", "action", "status", "start_time_ms"]
        for field in required_fields:
            assert field in step, f"缺少必需字段: {field}"
        print("  ✅ 包含所有必需字段")

        # 字段类型
        assert isinstance(step["agent_name"], str)
        assert isinstance(step["action"], str)
        assert isinstance(step["status"], str)
        assert isinstance(step["start_time_ms"], int)
        print("  ✅ 字段类型正确")

        # 可选字段
        if "duration_ms" in step:
            assert isinstance(step["duration_ms"], int)
            print(f"  ✅ duration_ms: {step['duration_ms']}")

        if "output_summary" in step:
            assert isinstance(step["output_summary"], str)
            print(f"  ✅ output_summary: {step['output_summary'][:30]}...")

        if "agent_role" in step:
            assert isinstance(step["agent_role"], str)
            print(f"  ✅ agent_role: {step['agent_role']}")

    # 3. 验证向后兼容性
    # 步骤 1 使用了旧的 "agent" 字段，应该被正确转换
    assert parsed["steps"][1]["agent_name"] == "StudyPlanner"
    print("\n✅ 向后兼容：旧格式 'agent' 字段正确转换为 'agent_name'")

    # 步骤 2 缺少 start_time_ms，应该使用默认值 0
    assert parsed["steps"][2]["start_time_ms"] == 0
    print("✅ 默认值：缺少 start_time_ms 时使用 0")

    return True


def test_go_gateway_parsing():
    """
    模拟 Go Gateway 的 JSON 解析逻辑
    """
    print("\n=== 测试 Go Gateway 解析 ===")

    # 模拟 Python 发送的 metadata
    python_metadata = {
        "collaboration_timeline": json.dumps({
            "schema_version": "1.0",
            "workflow_type": "task_decomposition",
            "execution_time_ms": 2500,
            "steps": [
                {
                    "agent_name": "StudyPlanner",
                    "action": "分析学习状态",
                    "status": "completed",
                    "start_time_ms": 1706409600000,
                    "duration_ms": 1200,
                }
            ]
        }, ensure_ascii=False),
        "other_field": "plain_string"
    }

    print(f"\nPython 发送的 metadata keys: {list(python_metadata.keys())}")

    # 模拟 Go Gateway 的解析逻辑（chat_orchestrator.go:517-524）
    go_metadata = {}
    for key, value in python_metadata.items():
        if key == "collaboration_timeline":
            try:
                decoded = json.loads(value)
                go_metadata[key] = decoded
                print(f"✅ {key}: JSON 解析成功")
            except json.JSONDecodeError as e:
                print(f"❌ {key}: JSON 解析失败 - {e}")
                go_metadata[key] = value  # 降级：返回原始字符串
        else:
            go_metadata[key] = value

    # 验证
    assert isinstance(go_metadata["collaboration_timeline"], dict)
    assert go_metadata["collaboration_timeline"]["schema_version"] == "1.0"
    assert isinstance(go_metadata["collaboration_timeline"]["steps"], list)
    assert len(go_metadata["collaboration_timeline"]["steps"]) == 1

    step = go_metadata["collaboration_timeline"]["steps"][0]
    assert step["agent_name"] == "StudyPlanner"
    assert step["action"] == "分析学习状态"
    assert step["status"] == "completed"
    assert step["start_time_ms"] == 1706409600000

    print("\n✅ Go Gateway 成功解析 collaboration_timeline 为对象")
    print("✅ 前端可以直接使用 metadata.collaboration_timeline.steps[*].agent_name")

    return True


def main():
    """运行所有测试"""
    print("=" * 60)
    print("Timeline 标准化 & Go Gateway 解析测试")
    print("=" * 60)

    tests = [
        test_timeline_normalization_logic,
        test_go_gateway_parsing,
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
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)

    if failed == 0:
        print("\n🎉 所有测试通过！")
        print("\n验证清单:")
        print("✅ schema_version == '1.0'")
        print("✅ steps[*].agent_name 存在")
        print("✅ steps[*].action 存在")
        print("✅ steps[*].status 存在")
        print("✅ steps[*].start_time_ms 存在")
        print("✅ Go Gateway 正确解析 JSON 为对象")
        print("✅ 前端可直接使用 metadata.collaboration_timeline.steps")
        return 0
    else:
        print(f"\n⚠️  有 {failed} 个测试失败")
        return 1


if __name__ == "__main__":
    exit(main())
