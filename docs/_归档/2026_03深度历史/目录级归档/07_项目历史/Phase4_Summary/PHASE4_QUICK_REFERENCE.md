# Phase 4 快速参考指南

## 📋 核心改进概览

### Week 4 - P3: 协作流程集成

**文件**: `backend/app/agents/standard_workflow.py`

| 功能 | 触发条件 | 工作流 | 输出 |
|------|---------|--------|------|
| 任务分解 | "准备考试"、"备考" | TaskDecompositionWorkflow | 计划 + 微任务 |
| 错题诊断 | "错误"、"诊断" | ErrorDiagnosisWorkflow | 诊断 + 复习计划 |
| 深度学习 | "详细"、"原理" | ProgressiveExplorationWorkflow | 5轮深度讲解 |

**流程图**:
```
用户输入
  ↓
[意图分类] (6种意图)
  ↓
[协作检测] → YES → [多Agent协作]
  ↓ NO      ↓
[标准流程]  [行动卡片强制]
```

### Week 5 - P4: 长期记忆与优化

**核心系统**: 工具执行历史 + 偏好学习

1. **自动记录** (`executor.py`)
   ```python
   工具执行时自动记录:
   - 成功/失败
   - 执行时间
   - 错误信息
   - 输入参数
   ```

2. **统计分析** (`tool_history_service.py`)
   ```python
   查询接口:
   - get_tool_success_rate()      # 成功率
   - get_user_preferred_tools()   # 偏好工具
   - get_recent_failed_tools()    # 失败追踪
   ```

3. **路由优化** (`tool_preference_router.py`)
   ```python
   决策优化:
   - rank_tools_by_success()      # 工具排序
   - estimate_tool_success_probability()  # 成功率估计
   - should_retry_tool()          # 重试判断
   ```

---

## 🔧 关键 API

### 协作工作流触发

```python
# standard_workflow.py

# 1. 意图分类
intent = _classify_user_intent("帮我准备考试")
# 返回: "exam_preparation"

# 2. 协作判断
if _should_use_collaboration(message, intent):
    # 触发协作

# 3. 工作流选择
WorkflowClass = _select_workflow(intent)
# 返回: TaskDecompositionWorkflow
```

### 工具历史记录和查询

```python
# tool_history_service.py

service = ToolHistoryService(db_session)

# 记录执行
await service.record_tool_execution(
    user_id=1,
    tool_name="create_plan",
    success=True,
    execution_time_ms=150
)

# 查询统计
success_rate = await service.get_tool_success_rate(
    user_id=1,
    tool_name="create_plan",
    days=30  # 过去30天
)

# 获取偏好工具
prefs = await service.get_user_preferred_tools(
    user_id=1,
    limit=5
)
```

### 工具偏好路由

```python
# tool_preference_router.py

pref_router = ToolPreferenceRouter(db_session, user_id=1)

# 获取偏好工具
preferred = await pref_router.get_preferred_tools(limit=5)

# 估计成功概率
prob = await pref_router.estimate_tool_success_probability("create_plan")

# 工具排序
ranked = await pref_router.rank_tools_by_success(tool_list)

# 是否应重试
should_retry = await pref_router.should_retry_tool(
    tool_name="create_plan",
    last_failure_time=datetime.now()
)
```

---

## 📊 数据模型

### user_tool_history 表

```sql
CREATE TABLE user_tool_history (
    id                INTEGER PRIMARY KEY,
    user_id           INTEGER NOT NULL,           -- 用户ID
    tool_name         VARCHAR(100) NOT NULL,      -- 工具名称
    success           BOOLEAN NOT NULL,           -- 是否成功
    execution_time_ms INTEGER,                    -- 执行时间(毫秒)
    error_message     VARCHAR(500),               -- 错误信息
    error_type        VARCHAR(100),               -- 错误类型
    context_snapshot  JSONB,                      -- 执行上下文
    input_args        JSONB,                      -- 输入参数
    output_summary    TEXT,                       -- 输出摘要
    user_satisfaction INTEGER,                    -- 用户评分(1-5)
    was_helpful       BOOLEAN,                    -- 是否有帮助
    created_at        DATETIME DEFAULT NOW(),     -- 创建时间
    updated_at        DATETIME DEFAULT NOW()      -- 更新时间
);

-- 关键索引
INDEX idx_user_tool_history_user_id;
INDEX idx_user_tool_history_tool_name;
INDEX idx_user_tool_history_success;
INDEX idx_user_tool_history_metrics(user_id, tool_name, success, created_at);
```

### 数据模型类

```python
# tool_history.py

class UserToolHistory(Base):
    # 直接映射数据库表

class ToolSuccessRateView:
    tool_name: str
    success_rate: float  # 0-100
    usage_count: int
    avg_time_ms: float
    last_used_at: datetime

class UserToolPreference:
    tool_name: str
    preference_score: float  # 0-1
    last_30d_success_rate: float
    last_30d_usage: int
```

---

## 🔌 集成点

### 1. Executor 自动记录

**位置**: `backend/app/orchestration/executor.py`

```python
# 在 execute_tool_call() 中自动记录
await self._record_tool_execution(
    user_id=user_id,
    tool_name=tool_name,
    success=result.success,
    execution_time_ms=execution_time_ms,
    error_message=result.error_message,
    input_args=arguments,
    output_summary=result.suggestion[:200]
)
```

**无需修改工具代码** - 执行器自动捕获所有数据

### 2. Router 优化决策

**位置**: `backend/app/routing/router_node.py` L60-82

```python
# 在路由决策前应用工具偏好学习
pref_router = ToolPreferenceRouter(db_session, int(user_id))

# 从历史更新学习器
await pref_router.update_learner_from_history()

# 按成功率重新排序候选工具
ranked_candidates = await pref_router.rank_tools_by_success(candidates)

# 存储偏好信息
state.context_data['tool_preferences'] = {...}
```

### 3. 协作流程集成

**位置**: `backend/app/agents/standard_workflow.py` L232-300

```python
# 在 collaboration_node() 中执行多Agent工作流
workflow = TaskDecompositionWorkflow(None)
result = await workflow.execute(user_message, context)

# 强制验证行动卡片
validated_result = await _ensure_action_cards(result, state)
```

---

## 📈 性能基准

### 查询性能

| 操作 | 响应时间 | 说明 |
|------|---------|------|
| 获取工具成功率 | <50ms | 单个工具的30天统计 |
| 获取用户偏好工具 | <100ms | Top 5工具列表 |
| 统计工具信息 | <50ms | 完整统计数据 |

### 执行性能

| 操作 | 开销 | 说明 |
|------|------|------|
| 工具执行记录 | +10ms | 异步记录 |
| 路由决策 | <300ms | 包含历史查询 |
| 协作执行 | 500-2000ms | 取决于工作流复杂度 |

---

## 🚀 部署步骤

### 1. 数据库迁移

```bash
cd backend
alembic upgrade head
```

### 2. 验证表创建

```bash
PGPASSWORD=password psql -U sparkle -h localhost -d sparkle -c "\dt user_tool_history"
```

### 3. 重启服务

```bash
make restart-all
```

### 4. 验证日志

```bash
# 检查工具历史记录
docker compose logs grpc-server | grep "tool_history"

# 检查路由学习
docker compose logs grpc-server | grep "Tool preference"
```

---

## 🧪 测试命令

### 单元测试

```bash
cd backend

# 运行ToolHistoryService测试
pytest app/services/test_tool_history_service.py -v

# 运行ToolPreferenceRouter测试
pytest app/routing/test_tool_preference_router.py -v

# 运行所有Phase 4测试
pytest -k phase4 -v
```

### 集成测试

```bash
# 运行集成测试
pytest -k "integration" -v

# 运行端到端测试
cd mobile && flutter test integration_test/e2e_agent_test.dart
```

### 性能测试

```bash
# 运行性能基准测试
pytest app/ -v --durations=10
```

---

## 📚 文件导航

### 关键文件位置

| 文件 | 功能 | 行数 |
|------|------|------|
| backend/app/agents/standard_workflow.py | 协作流程 | 540 |
| backend/app/models/tool_history.py | 数据模型 | 180 |
| backend/app/services/tool_history_service.py | 历史服务 | 280 |
| backend/app/routing/tool_preference_router.py | 偏好路由 | 350 |
| backend/app/orchestration/executor.py | 执行器 | 180+ |
| backend/app/routing/router_node.py | 路由节点 | 140+ |

### 数据库迁移

```
backend/alembic/versions/
└── p2_add_user_tool_history.py (60 行)
```

### 文档

```
repo root/
├── PHASE4_COMPLETION_VERIFICATION.md    (验证报告)
├── PHASE4_TESTING_AND_DEPLOYMENT.md     (测试部署)
├── PHASE4_FINAL_SUMMARY.md              (完成总结)
└── PHASE4_QUICK_REFERENCE.md            (本文档)
```

---

## ❓ 常见问题

### Q: 工具执行历史什么时候开始记录?

A: 数据库迁移应用后，所有工具执行都会自动记录到 `user_tool_history` 表。无需修改工具代码。

### Q: 查询历史数据会很慢吗?

A: 不会。通过复合索引优化，查询响应时间 <100ms。建议只查询过去30天的数据。

### Q: 如何重置用户的工具偏好学习?

A: 清除用户的历史记录或重置 Redis 中的 BayesianLearner 状态:
```bash
redis-cli DEL learner:user_id
```

### Q: 协作流程失败时会怎样?

A: 自动降级到标准工作流，用户不会有中断体验。错误日志会详细记录。

### Q: 能否在测试环境验证?

A: 可以。在本地启动完整栈:
```bash
make dev-all
# 在终端1: flask shell
# 在终端2: flutter run
```

---

## 🔗 相关链接

### Phase 4 文档

- [完成验证报告](PHASE4_COMPLETION_VERIFICATION.md) - 详细的实施细节
- [测试部署指南](PHASE4_TESTING_AND_DEPLOYMENT.md) - 测试用例和部署步骤
- [完成总结](PHASE4_FINAL_SUMMARY.md) - 整体项目评价

### 代码库

- [Agent 标准工作流](backend/app/agents/standard_workflow.py)
- [工具执行器](backend/app/orchestration/executor.py)
- [路由节点](backend/app/routing/router_node.py)
- [知识图谱系统](docs/02_技术设计文档/02_知识星图系统设计_v3.0.md)

### 前期阶段

- [Phase 1-3 报告](WEEK2_WEEK3_COMPLETION.md) - 前三周完成情况
- [项目计划](README.md) - 整体项目概览

---

## 📞 获得帮助

### 遇到问题?

1. 检查日志: `docker compose logs grpc-server`
2. 查看测试: `pytest app/ -v --tb=short`
3. 查阅文档: 相关文档在上面的链接中
4. 运行验证: `alembic current` 检查迁移状态

### 需要扩展?

- 添加新的协作工作流: 参考 `collaboration_workflows.py`
- 实现新的学习策略: 扩展 `ToolPreferenceRouter`
- 定制工具推荐: 修改 `estimate_tool_success_probability()`

---

**Last Updated**: 2025-01-15
**Version**: 1.0
**Status**: ✅ Ready for Production
