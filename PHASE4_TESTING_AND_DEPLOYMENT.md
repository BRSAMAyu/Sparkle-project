# Phase 4 测试与部署指南

## 目录

1. [数据库迁移](#数据库迁移)
2. [单元测试](#单元测试)
3. [集成测试](#集成测试)
4. [端到端测试](#端到端测试)
5. [性能测试](#性能测试)
6. [生产部署清单](#生产部署清单)

---

## 数据库迁移

### 步骤 1: 应用迁移

```bash
cd /Users/a/code/sparkle-flutter/backend

# 查看当前状态
alembic current

# 查看待应用的迁移
alembic heads

# 应用最新迁移
alembic upgrade head
```

**预期输出**:
```
...
2025-01-15 10:00:00,123 INFO [alembic.runtime.migration] Running upgrade p1_add_post_visibility -> p2_add_user_tool_history
...
Running upgrade p2_add_user_tool_history
```

### 步骤 2: 验证表创建

```bash
# 连接到数据库
PGPASSWORD=password psql -U sparkle -h localhost -d sparkle -c "
  \dt user_tool_history
  \di user_tool_history*
"
```

**预期输出**:
```
                    List of relations
 Schema |          Name          | Type  |  Owner
--------+------------------------+-------+----------
 public | user_tool_history      | table | sparkle
(1 row)

                       List of indexes
 Schema |                  Name                  | Type  | Table
--------+----------------------------------------+-------+------------------
 public | user_tool_history_pkey                 | index | user_tool_history
 public | ix_user_tool_history_user_id           | index | user_tool_history
 public | ix_user_tool_history_tool_name         | index | user_tool_history
 public | ix_user_tool_history_success           | index | user_tool_history
 public | idx_user_tool_history_metrics          | index | user_tool_history
```

---

## 单元测试

### 测试 1: ToolHistoryService

文件: `backend/app/services/test_tool_history_service.py`

```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.models.tool_history import UserToolHistory
from app.services.tool_history_service import ToolHistoryService

@pytest.fixture
async def db_session():
    """创建测试数据库会话"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        yield session

@pytest.mark.asyncio
async def test_record_tool_execution(db_session):
    """测试工具执行记录"""
    service = ToolHistoryService(db_session)

    # 记录工具执行
    record = await service.record_tool_execution(
        user_id=1,
        tool_name="create_plan",
        success=True,
        execution_time_ms=150,
        tool_category="plan"
    )

    assert record.user_id == 1
    assert record.tool_name == "create_plan"
    assert record.success == True
    assert record.execution_time_ms == 150

@pytest.mark.asyncio
async def test_get_tool_success_rate(db_session):
    """测试成功率计算"""
    service = ToolHistoryService(db_session)

    # 记录 10 次执行，8 次成功
    for i in range(8):
        await service.record_tool_execution(1, "test_tool", True)
    for i in range(2):
        await service.record_tool_execution(1, "test_tool", False)

    success_rate = await service.get_tool_success_rate(1, "test_tool")
    assert success_rate == 80.0

@pytest.mark.asyncio
async def test_get_user_preferred_tools(db_session):
    """测试偏好工具获取"""
    service = ToolHistoryService(db_session)

    # 记录不同工具的执行
    for i in range(10):
        await service.record_tool_execution(1, "create_plan", True)
    for i in range(5):
        await service.record_tool_execution(1, "generate_tasks", True)

    preferences = await service.get_user_preferred_tools(1, limit=5)

    assert len(preferences) > 0
    assert preferences[0].tool_name in ["create_plan", "generate_tasks"]
```

**运行测试**:
```bash
cd backend
pytest app/services/test_tool_history_service.py -v
```

### 测试 2: ToolPreferenceRouter

文件: `backend/app/routing/test_tool_preference_router.py`

```python
@pytest.mark.asyncio
async def test_get_preferred_tools(db_session):
    """测试偏好工具列表"""
    router = ToolPreferenceRouter(db_session, user_id=1)

    # 记录历史
    service = ToolHistoryService(db_session)
    await service.record_tool_execution(1, "create_plan", True)
    await service.record_tool_execution(1, "create_plan", True)

    # 获取偏好
    preferred = await router.get_preferred_tools(limit=5)
    assert "create_plan" in preferred

@pytest.mark.asyncio
async def test_estimate_tool_success_probability(db_session):
    """测试成功概率估计"""
    router = ToolPreferenceRouter(db_session, user_id=1)
    service = ToolHistoryService(db_session)

    # 记录 10 次执行，9 次成功
    for i in range(9):
        await service.record_tool_execution(1, "create_plan", True)
    await service.record_tool_execution(1, "create_plan", False)

    prob = await router.estimate_tool_success_probability("create_plan")
    assert 0.85 < prob <= 1.0  # 应该接近 0.9

@pytest.mark.asyncio
async def test_rank_tools_by_success(db_session):
    """测试工具排序"""
    router = ToolPreferenceRouter(db_session, user_id=1)
    service = ToolHistoryService(db_session)

    # tool1: 90% 成功率
    for i in range(9):
        await service.record_tool_execution(1, "tool1", True)
    await service.record_tool_execution(1, "tool1", False)

    # tool2: 70% 成功率
    for i in range(7):
        await service.record_tool_execution(1, "tool2", True)
    for i in range(3):
        await service.record_tool_execution(1, "tool2", False)

    ranked = await router.rank_tools_by_success(["tool1", "tool2"])
    assert ranked[0][0] == "tool1"  # tool1 应该排在前面
```

### 测试 3: Executor 历史记录

文件: `backend/app/orchestration/test_executor_history.py`

```python
@pytest.mark.asyncio
async def test_execute_tool_records_history(db_session, mocker):
    """测试工具执行自动记录历史"""
    executor = ToolExecutor()

    # Mock 一个工具
    mock_tool = mocker.Mock()
    mock_tool.parameters_schema = lambda **kw: kw
    mock_tool.execute = mocker.AsyncMock(
        return_value=ToolResult(
            success=True,
            tool_name="test_tool",
            data={"result": "ok"}
        )
    )

    # Mock tool_registry
    mocker.patch.object(
        tool_registry, 'get_tool',
        return_value=mock_tool
    )

    # 执行工具
    result = await executor.execute_tool_call(
        tool_name="test_tool",
        arguments={"param": "value"},
        user_id="1",
        db_session=db_session
    )

    # 验证执行成功
    assert result.success == True

    # 验证历史记录
    service = ToolHistoryService(db_session)
    stats = await service.get_tool_statistics(1, "test_tool")
    assert stats.usage_count >= 1
```

---

## 集成测试

### 测试场景 1: 协作流程端到端

**场景**: 用户说"准备数学考试" → 触发协作流程

```python
@pytest.mark.asyncio
async def test_collaboration_workflow_e2e():
    """端到端协作工作流测试"""
    # 构建测试状态
    state = WorkflowState(
        messages=[{
            "role": "user",
            "content": "帮我准备数学期末考试"
        }],
        context_data={
            "user_id": 1,
            "user_context": {"name": "测试用户"},
            "db_session": db_session,
        }
    )

    # 执行协作节点
    from app.agents.standard_workflow import collaboration_node
    result_state = await collaboration_node(state)

    # 验证协作被触发
    assert result_state.next_step in ["collaboration_post_process", "tool_planning"]

    if "collaboration_result" in result_state.context_data:
        collab_result = result_state.context_data["collaboration_result"]
        assert collab_result.workflow_type == "task_decomposition"
        assert len(collab_result.participants) > 1
        print(f"✅ Collaboration triggered with {len(collab_result.participants)} agents")

@pytest.mark.asyncio
async def test_collaboration_action_cards():
    """验证协作结果包含行动卡片"""
    # ... (setup)

    result_state = await collaboration_node(state)

    if "collaboration_result" in result_state.context_data:
        result = result_state.context_data["collaboration_result"]

        # 验证有 action cards
        has_action_cards = False
        if hasattr(result, 'outputs'):
            for output in result.outputs:
                if hasattr(output, 'tool_results'):
                    for tr in output.tool_results:
                        if hasattr(tr, 'widget_type'):
                            has_action_cards = True

        assert has_action_cards, "协作结果应包含 action cards"
        print("✅ Action cards validation passed")
```

### 测试场景 2: 路由学习闭环

**场景**: 工具执行 → 记录 → 优化路由决策

```python
@pytest.mark.asyncio
async def test_router_learning_loop():
    """测试路由器学习闭环"""

    # 第1次: 记录工具执行历史
    service = ToolHistoryService(db_session)
    for i in range(10):
        await service.record_tool_execution(
            user_id=1,
            tool_name="tool_a",
            success=(i < 8),  # 80% 成功率
            execution_time_ms=100 + i*10
        )

    # 第2次: 构建路由状态并执行
    state = WorkflowState(
        messages=[{"role": "user", "content": "test"}],
        context_data={
            "user_id": 1,
            "db_session": db_session,
            "current_node": "orchestrator"
        }
    )

    from app.routing.router_node import RouterNode
    router = RouterNode(
        routes=["generation", "tool_a"],
        redis_client=None,
        user_id=1
    )

    result_state = await router(state)

    # 验证路由决策
    assert "router_decision" in result_state.context_data
    assert "tool_preferences" in result_state.context_data

    preferences = result_state.context_data.get("tool_preferences", {})
    if "tool_a" in preferences:
        assert preferences["tool_a"]["success_rate"] == 80.0
        print("✅ Router learning loop validated")
```

---

## 端到端测试

### 测试场景: 完整用户对话

```bash
# 启动服务
make dev-all

# 使用测试客户端
cd mobile && flutter test integration_test/e2e_agent_test.dart
```

**测试脚本** (`mobile/test/integration/agent_phase4_test.dart`):

```dart
void main() {
  group('Phase 4 Agent E2E Tests', () {

    testWidgets('Collaboration workflow triggers on exam prep intent',
      (WidgetTester tester) async {
      // 启动应用
      await tester.pumpWidget(const MyApp());

      // 输入消息
      await tester.enterText(
        find.byType(TextField),
        "帮我准备数学期末考试"
      );
      await tester.tap(find.byIcon(Icons.send));
      await tester.pumpAndSettle();

      // 验证协作流程被触发
      expect(find.byType(AgentStatusIndicator), findsOneWidget);
      expect(
        find.text(contains("多Agent协作")),
        findsOneWidget
      );

      // 等待行动卡片出现
      await tester.pumpAndSettle(Duration(seconds: 3));
      expect(find.byType(ActionCard), findsWidgets);

      print("✅ Collaboration workflow test passed");
    });

    testWidgets('Tool history is recorded and used for routing',
      (WidgetTester tester) async {
      // ... (setup)

      // 执行多个工具调用
      for (int i = 0; i < 5; i++) {
        await tester.enterText(find.byType(TextField), "创建任务");
        await tester.tap(find.byIcon(Icons.send));
        await tester.pumpAndSettle();
      }

      // 验证历史被记录
      // (通过后端API验证)
      final response = await http.get(
        Uri.parse('http://localhost:8080/api/user/tool-history?limit=10')
      );

      expect(response.statusCode, 200);
      final histories = jsonDecode(response.body);
      expect(histories.length, greaterThanOrEqualTo(5));

      print("✅ Tool history recording test passed");
    });
  });
}
```

---

## 性能测试

### 测试 1: 工具历史查询性能

```python
import time

async def test_tool_history_query_performance(db_session):
    """测试工具历史查询性能"""
    service = ToolHistoryService(db_session)

    # 准备测试数据: 10,000 条记录
    print("Inserting 10,000 records...")
    for user_id in range(1, 101):
        for tool_idx in range(100):
            await service.record_tool_execution(
                user_id=user_id,
                tool_name=f"tool_{tool_idx % 10}",
                success=random.random() > 0.2,
                execution_time_ms=random.randint(50, 500)
            )

    # 测试查询性能
    queries = [
        ("get_tool_success_rate", lambda: service.get_tool_success_rate(1, "tool_0")),
        ("get_user_preferred_tools", lambda: service.get_user_preferred_tools(1)),
        ("get_tool_statistics", lambda: service.get_tool_statistics(1, "tool_0")),
    ]

    for query_name, query_func in queries:
        start = time.time()
        result = await query_func()
        elapsed = (time.time() - start) * 1000  # ms

        assert elapsed < 100, f"{query_name} too slow: {elapsed:.2f}ms"
        print(f"✅ {query_name}: {elapsed:.2f}ms")
```

### 测试 2: 路由决策性能

```python
async def test_routing_performance(db_session):
    """测试路由决策性能"""
    from app.routing.router_node import RouterNode

    router = RouterNode(
        routes=["generation", "tool_execution"],
        redis_client=None,
        user_id=1
    )

    state = WorkflowState(
        messages=[{"role": "user", "content": "test query"}],
        context_data={"db_session": db_session, "user_id": 1}
    )

    start = time.time()
    result_state = await router(state)
    elapsed = (time.time() - start) * 1000  # ms

    assert elapsed < 500, f"Routing too slow: {elapsed:.2f}ms"
    print(f"✅ Routing decision: {elapsed:.2f}ms")
```

---

## 生产部署清单

### 部署前检查

```bash
# 1. 代码审查
git diff main..HEAD --stat  # 确认所有更改

# 2. 运行所有测试
cd backend && pytest --cov=app --cov-report=html  # 覆盖率 >80%
cd backend/gateway && go test ./...
cd mobile && flutter test

# 3. 检查日志
grep -r "TODO\|FIXME\|HACK" backend/app --include="*.py"

# 4. 数据库检查
# 确认迁移脚本正确
alembic show p2_add_user_tool_history
```

### 部署步骤

```bash
# 1. 备份数据库
pg_dump sparkle > sparkle_backup_2025_01_15.sql

# 2. 应用数据库迁移 (生产环境)
cd backend
SPARKLE_ENV=production alembic upgrade head

# 3. 部署应用
git checkout main
git pull origin main
git merge release/phase4

# 4. 重启服务
make restart-all

# 5. 验证服务
curl http://localhost:8080/health
curl http://localhost:50051/api/health  # gRPC health check
```

### 监控和告警

```yaml
# prometheus 告警规则
groups:
  - name: Phase4
    rules:
      - alert: ToolHistoryRecordingFailure
        expr: |
          rate(tool_history_record_errors[5m]) > 0.1
        for: 5m
        annotations:
          summary: "Tool history recording failures detected"

      - alert: RoutingPerformanceDegraded
        expr: |
          histogram_quantile(0.95, routing_decision_duration_ms) > 500
        for: 10m
        annotations:
          summary: "Router performance degraded"
```

### 灾难恢复

```bash
# 如果需要回滚
alembic downgrade p1_add_post_visibility

# 还原数据库
psql sparkle < sparkle_backup_2025_01_15.sql

# 重启服务
make restart-all
```

---

## 验收标准

所有以下测试必须通过才能认为 Phase 4 完成:

- [ ] 数据库迁移成功
- [ ] ToolHistoryService 单元测试 >90%
- [ ] ToolPreferenceRouter 单元测试 >90%
- [ ] Executor 历史记录集成测试通过
- [ ] 协作流程端到端测试通过
- [ ] 路由学习闭环测试通过
- [ ] 完整用户对话集成测试通过
- [ ] 工具历史查询性能 <100ms
- [ ] 路由决策性能 <500ms
- [ ] 生产部署检查清单全部通过

---

**部署日期**: 2025-01-15
**预计停机时间**: 5-10 分钟 (仅数据库迁移期间)
**回滚时间**: <5 分钟

**准备就绪! 可以开始生产部署。**
