"""
Agent Stats Integration Test

测试Agent统计系统的完整流程：
1. 记录Agent执行
2. 查询统计数据
3. 验证数据准确性
"""
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.models.agent_stats import AgentExecutionStats, Base
from app.services.agent_stats_service import AgentStatsService


async def test_agent_stats_integration():
    """完整集成测试"""

    # 创建内存数据库用于测试
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        service = AgentStatsService(session)

        print("🧪 开始Agent统计系统集成测试\n")

        # 测试数据
        test_user_id = 1
        test_session_id = "test_session_123"
        test_request_id = "req_456"

        # 1. 测试记录Agent执行
        print("1️⃣ 测试记录Agent执行...")

        test_cases = [
            {
                "agent_type": "knowledge",
                "tool_name": "knowledge_search",
                "operation": "检索知识库",
                "duration": 450,
                "status": "success"
            },
            {
                "agent_type": "math",
                "tool_name": "calculate_math",
                "operation": "计算公式",
                "duration": 320,
                "status": "success"
            },
            {
                "agent_type": "code",
                "tool_name": "run_code",
                "operation": "执行Python代码",
                "duration": 680,
                "status": "success"
            },
            {
                "agent_type": "data_analysis",
                "tool_name": "analyze_data",
                "operation": "分析数据集",
                "duration": 890,
                "status": "success"
            },
            {
                "agent_type": "translation",
                "tool_name": "translate_text",
                "operation": "翻译文本",
                "duration": 230,
                "status": "success"
            },
            {
                "agent_type": "knowledge",
                "tool_name": "knowledge_search",
                "operation": "检索知识库",
                "duration": 520,
                "status": "failed"
            },
        ]

        for i, case in enumerate(test_cases):
            start_time = datetime.utcnow() - timedelta(seconds=case['duration'] / 1000)
            end_time = start_time + timedelta(milliseconds=case['duration'])

            await service.record_agent_execution(
                user_id=test_user_id,
                session_id=test_session_id,
                request_id=f"{test_request_id}_{i}",
                agent_type=case['agent_type'],
                started_at=start_time,
                completed_at=end_time,
                status=case['status'],
                tool_name=case['tool_name'],
                operation=case['operation']
            )
            print(f"   ✅ 记录: {case['agent_type']} - {case['operation']} ({case['duration']}ms)")

        # 2. 测试获取用户统计概览
        print("\n2️⃣ 测试获取用户统计概览...")
        overview = await service.get_user_stats(test_user_id, days=30)

        print(f"   📊 总体统计:")
        print(f"      - 总执行次数: {overview['overall']['total_executions']}")
        print(f"      - 平均耗时: {overview['overall']['avg_duration_ms']}ms")
        print(f"      - 总会话数: {overview['overall']['total_sessions']}")

        print(f"   📈 按Agent统计:")
        for agent in overview['by_agent']:
            print(f"      - {agent['agent_type']}: {agent['count']}次, "
                  f"平均{agent['avg_duration_ms']}ms, "
                  f"成功率{agent['success_rate']:.1f}%")

        # 3. 测试获取Top Agent
        print("\n3️⃣ 测试获取Top Agent...")
        top_agents = await service.get_most_used_agents(test_user_id, limit=3)

        for i, agent in enumerate(top_agents, 1):
            print(f"   🏆 Top {i}: {agent['agent_name']} - {agent['usage_count']}次")

        # 4. 测试获取性能指标
        print("\n4️⃣ 测试获取性能指标...")
        metrics = await service.get_performance_metrics(
            user_id=test_user_id,
            days=30
        )

        print(f"   ⚡ 性能指标:")
        print(f"      - 总执行: {metrics['total_executions']}次")
        print(f"      - 平均耗时: {metrics['avg_duration_ms']}ms")
        print(f"      - 中位数: {metrics['median_duration_ms']}ms")
        print(f"      - P95: {metrics['p95_duration_ms']}ms")
        print(f"      - 成功率: {metrics['success_rate']:.1f}%")

        # 5. 验证数据准确性
        print("\n5️⃣ 验证数据准确性...")

        # 验证总执行次数
        expected_count = len(test_cases)
        actual_count = overview['overall']['total_executions']
        assert actual_count == expected_count, f"期望{expected_count}次，实际{actual_count}次"
        print(f"   ✅ 执行次数验证通过: {actual_count}次")

        # 验证Agent类型数量
        expected_agent_types = len(set(c['agent_type'] for c in test_cases))
        actual_agent_types = len(overview['by_agent'])
        assert actual_agent_types == expected_agent_types, f"期望{expected_agent_types}种Agent，实际{actual_agent_types}种"
        print(f"   ✅ Agent类型数量验证通过: {actual_agent_types}种")

        # 验证成功率计算
        success_count = sum(1 for c in test_cases if c['status'] == 'success')
        expected_success_rate = (success_count / len(test_cases)) * 100
        actual_success_rate = metrics['success_rate']
        assert abs(actual_success_rate - expected_success_rate) < 0.1, f"成功率计算错误"
        print(f"   ✅ 成功率计算验证通过: {actual_success_rate:.1f}%")

        print("\n🎉 所有测试通过！Agent统计系统运行正常。")

        # 打印汇总信息
        print("\n📊 测试数据汇总:")
        print(f"   - 测试用户ID: {test_user_id}")
        print(f"   - 测试会话数: {overview['overall']['total_sessions']}")
        print(f"   - 总执行次数: {overview['overall']['total_executions']}")
        print(f"   - 涉及Agent数: {len(overview['by_agent'])}")
        print(f"   - 平均耗时: {overview['overall']['avg_duration_ms']}ms")

        return True


async def test_agent_type_mapping():
    """测试Agent类型映射"""
    print("\n🧪 测试Agent类型映射...")

    from app.orchestration.orchestrator import get_agent_type_for_tool
    from app.gen.agent.v1 import agent_service_pb2

    test_cases = [
        ('knowledge_search', agent_service_pb2.KNOWLEDGE),
        ('calculate_math', agent_service_pb2.MATH),
        ('run_code', agent_service_pb2.CODE),
        ('analyze_data', agent_service_pb2.DATA_ANALYSIS),
        ('translate_text', agent_service_pb2.TRANSLATION),
        ('generate_image', agent_service_pb2.IMAGE),
        ('process_audio', agent_service_pb2.AUDIO),
        ('write_content', agent_service_pb2.WRITING),
        ('solve_logic', agent_service_pb2.REASONING),
        ('create_task', agent_service_pb2.ORCHESTRATOR),
    ]

    for tool_name, expected in test_cases:
        actual = get_agent_type_for_tool(tool_name)
        assert actual == expected, f"工具{tool_name}映射错误"
        print(f"   ✅ {tool_name} -> {agent_service_pb2.AgentType.Name(actual)}")

    print("   🎉 Agent类型映射测试通过！")
    return True


async def main():
    """运行所有测试"""
    try:
        await test_agent_type_mapping()
        await test_agent_stats_integration()
        print("\n" + "="*60)
        print("✅ 所有集成测试通过！")
        print("="*60)
        return True
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
