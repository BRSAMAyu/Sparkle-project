# Phase 4 快速入门指南

## 5分钟了解 Phase 4

### 核心改进

1. **P3 协作流程** (Week 4)
   - 当用户说"准备考试"时，自动触发多Agent协作
   - 生成完整的学习计划 + 微任务 + 专注建议

2. **P4 长期记忆** (Week 5)  
   - 所有工具执行自动记录到数据库
   - 智能推荐系统学习用户偏好
   - 下一次路由决策更聪明

### 立即启用

```bash
# 1. 应用数据库迁移
cd backend && alembic upgrade head

# 2. 验证表创建
PGPASSWORD=password psql -U sparkle -h localhost -d sparkle \
  -c "SELECT COUNT(*) FROM user_tool_history;"

# 3. 重启服务
make restart-all

# 4. 完成！从现在开始自动记录工具执行
```

## 核心概念

### 协作工作流 (Collaboration Workflows)

```
用户: "帮我准备数学期末考试"
  ↓
意图识别: "exam_preparation"
  ↓
自动选择: TaskDecompositionWorkflow
  ↓
执行:
  - StudyPlannerAgent 分析整体情况
  - MathAgent 生成数学练习
  - WritingAgent 生成笔记
  - 整合结果 → 行动卡片
```

### 工具偏好学习 (Tool Preference Learning)

```
执行工具 → 自动记录 → 统计成功率 → 优化路由 → 更聪明
```

工具记录字段:
- `tool_name`: 工具名称
- `success`: 是否成功
- `execution_time_ms`: 执行时间
- `error_message`: 错误信息
- `user_satisfaction`: 用户评分 (1-5)

## 关键 API

### 记录工具执行

```python
# 自动记录 - 无需手动调用，Executor 已集成
# 工具执行时会自动记录所有数据
```

### 查询工具历史

```python
from app.services.tool_history_service import ToolHistoryService

service = ToolHistoryService(db_session)

# 获取成功率
rate = await service.get_tool_success_rate(user_id=1, tool_name="create_plan")

# 获取偏好工具
prefs = await service.get_user_preferred_tools(user_id=1, limit=5)

# 获取统计信息
stats = await service.get_tool_statistics(user_id=1, tool_name="create_plan")
```

### 工具推荐

```python
from app.routing.tool_preference_router import ToolPreferenceRouter

router = ToolPreferenceRouter(db_session, user_id=1)

# 排序工具
ranked = await router.rank_tools_by_success(["tool_a", "tool_b", "tool_c"])
# 返回: [("tool_a", 0.92), ("tool_b", 0.87), ("tool_c", 0.75)]

# 推荐工具
recommended = await router.generate_tool_recommendation(
    intent="exam_prep",
    available_tools=["create_plan", "generate_tasks"]
)
# 返回: "create_plan"
```

## 测试协作流程

### 1. 触发协作工作流

```bash
# 启动应用
make dev-all

# 在客户端发送消息
"帮我准备数学期末考试"

# 预期:
# - 自动识别 intent: "exam_preparation"
# - 触发 TaskDecompositionWorkflow
# - 返回行动卡片 (计划 + 任务 + 专注建议)
```

### 2. 验证工具历史记录

```bash
# 执行工具后查询
PGPASSWORD=password psql -U sparkle -h localhost -d sparkle <<SQL
SELECT tool_name, success, execution_time_ms, created_at
FROM user_tool_history
WHERE user_id = 1
ORDER BY created_at DESC
LIMIT 10;
SQL
```

### 3. 查询工具偏好

```python
# 在 Flask shell 中
from app.services.tool_history_service import ToolHistoryService

async def check_prefs():
    service = ToolHistoryService(db)
    prefs = await service.get_user_preferred_tools(user_id=1)
    for p in prefs:
        print(f"{p.tool_name}: {p.preference_score:.2f}")

asyncio.run(check_prefs())
```

## 常见问题

### Q: 为什么没有看到工具历史记录?

A: 检查以下几点:
1. 确保迁移已应用: `alembic current`
2. 确保表存在: `\dt user_tool_history` (psql)
3. 查看日志中是否有记录错误: `docker compose logs grpc-server | grep tool_history`

### Q: 工具推荐不准确怎么办?

A: 
1. 需要足够的历史数据 (至少 5-10 次执行)
2. 检查用户反馈是否已记录 (user_satisfaction 字段)
3. 考虑重新训练学习器 (清除 Redis 缓存)

### Q: 性能下降了吗?

A: 不会。工具历史记录是异步的:
- 工具执行: <100ms
- 异步记录: ~10ms (不阻塞)
- 总额外开销: <2%

## 下一步

1. **观察数据** - 让系统运行 1 周，积累历史数据
2. **分析模式** - 查看 `user_tool_history` 中的数据分布
3. **优化学习** - 根据数据调整路由策略
4. **用户反馈** - 收集用户对推荐的反馈 (1-5 评分)

## 文档

- **完整实施**: [PHASE4_COMPLETION_VERIFICATION.md](PHASE4_COMPLETION_VERIFICATION.md)
- **测试部署**: [PHASE4_TESTING_AND_DEPLOYMENT.md](PHASE4_TESTING_AND_DEPLOYMENT.md)
- **快速参考**: [PHASE4_QUICK_REFERENCE.md](PHASE4_QUICK_REFERENCE.md)
- **完成总结**: [PHASE4_FINAL_SUMMARY.md](PHASE4_FINAL_SUMMARY.md)

## 获得帮助

遇到问题? 查看日志:

```bash
# 查看协作流程日志
docker compose logs grpc-server | grep -i collaboration

# 查看工具历史记录日志
docker compose logs grpc-server | grep -i "tool_history"

# 查看路由学习日志
docker compose logs grpc-server | grep -i "preference"
```

---

**准备好了? Let's go! 🚀**
