# Sparkle x OpenClaw 集成 — 实施快速参考

> **详细规格**: 见 `SPARKLE_OPENCLAW_IMPLEMENTATION_SPEC_v1.0.md`
> **日期**: 2026-03-27

---

## 一、实施顺序总览

```
Phase 0 (2-3天)
├── 1. settings.py — 添加配置项
├── 2. models/execution_intent.py — 新建数据模型
├── 3. models/execution_record.py — 新建数据模型
├── 4. models/task.py — 添加一个字段
├── 5. models/__init__.py — 注册新模型
├── 6. core/execution_router.py — 新建路由器
├── 7. core/execution_trust.py — 新建信任引擎
├── 8. core/event_types.py — 添加4个事件类
└── 9. alembic migration — 执行迁移

Phase 1 (3-5天)
├── 1. adapters/openclaw/ — 新建适配器包
├── 2. services/execution_service.py — 新建执行服务
├── 3. api/v1/executions.py — 新建API端点
├── 4. api/v1/router.py — 注册路由
└── 5. Mobile — Flutter模型 + UI组件
```

---

## 二、关键安全约束

### 2.1 三级信任引擎（强制）

```
RAW       → 只存 ExecutionRecord，不写入任何其他地方
VALIDATED → 可更新 Task 状态、写入 PlanExecutionRecord
TRUSTED   → 可写入行为信号、更新用户画像
```

### 2.2 零侵入原则

```
✅ 新文件
✅ 现有文件只添加（新字段有默认值、新导入、新路由注册）
✅ Feature flag 全局开关（OPENCLAW_ENABLED，默认 False）
❌ 现有模块不能导入新模块（除了 models/__init__.py）
❌ 修改现有测试
❌ NOT NULL 约束加到现有表
```

### 2.3 数据流不变式

```
OpenClaw 结果 → ResultParser → TrustEngine.evaluate() → ExecutionRecord (必须)
                                           │
                                           ├─ RAW → 停止
                                           ├─ VALIDATED → Task + PlanExecutionRecord
                                           └─ TRUSTED → 行为信号 + 画像
```

---

## 三、文件清单

### Phase 0 — 新建文件

| 文件 | 说明 |
|------|------|
| `backend/app/models/execution_intent.py` | 执行意图模型 |
| `backend/app/models/execution_record.py` | 执行记录模型 |
| `backend/app/core/execution_router.py` | 执行路由决策 |
| `backend/app/core/execution_trust.py` | 信任评估引擎 |
| `backend/alembic/versions/oc001_*.py` | 数据库迁移 |

### Phase 0 — 修改文件（仅添加）

| 文件 | 改动 |
|------|------|
| `backend/app/models/task.py` | +1 nullable 字段 `execution_mode` |
| `backend/app/models/__init__.py` | +导入 +__all__ 条目 |
| `backend/app/core/event_types.py` | +4 事件类 |
| `backend/app/config/settings.py` | +7 配置项（全部有默认值） |

### Phase 1 — 新建文件

| 文件 | 说明 |
|------|------|
| `backend/app/adapters/__init__.py` | 包初始化（空） |
| `backend/app/adapters/openclaw/__init__.py` | 包导出 |
| `backend/app/adapters/openclaw/config.py` | 配置类 |
| `backend/app/adapters/openclaw/client.py` | HTTP 客户端 |
| `backend/app/adapters/openclaw/intent_translator.py` | 意图翻译 |
| `backend/app/adapters/openclaw/result_parser.py` | 结果解析 |
| `backend/app/services/execution_service.py` | 执行服务 |
| `backend/app/api/v1/executions.py` | REST API |

### Phase 1 — 修改文件

| 文件 | 改动 |
|------|------|
| `backend/app/api/v1/router.py` | +1 导入 +1 路由注册 |
| `mobile/lib/core/network/api_endpoints.dart` | +7 端点字符串 |
| `mobile/lib/features/task/data/models/execution_intent_model.dart` | 新文件 |

---

## 四、配置项

```python
# backend/app/config/settings.py 新增

OPENCLAW_ENABLED: bool = False                    # 主开关（默认关闭）
OPENCLAW_GATEWAY_URL: str = ""                    # 如 "http://127.0.0.1:18789"
OPENCLAW_AUTH_TOKEN: str = ""                     # Bearer token
OPENCLAW_DEFAULT_AGENT_ID: str = ""               # 默认 agent
OPENCLAW_DEFAULT_TIMEOUT_SECONDS: int = 300       # 5分钟
OPENCLAW_MAX_CONCURRENT_RUNS: int = 3             # 每用户并发
OPENCLAW_TRUST_AUTO_PROMOTE_MIN_HISTORY: int = 5  # 自动信任阈值
```

---

## 五、API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/executions/health` | 检查集成状态 |
| POST | `/executions/tasks/{id}/classify` | 分类任务（不执行） |
| POST | `/executions/tasks/{id}/handoff` | 委派给 AI |
| GET | `/executions/{id}` | 获取执行状态 |
| GET | `/executions/tasks/{id}/intents` | 列出任务执行记录 |
| POST | `/executions/{id}/cancel` | 取消执行 |
| POST | `/executions/{id}/handback` | 取回自己做 |

---

## 六、验证清单

### Phase 0 完成标志

```bash
# 1. 迁移成功
cd backend && alembic upgrade head

# 2. 回滚可用
alembic downgrade -1

# 3. 现有测试通过
pytest

# 4. 新模型可用
python -c "from app.models import ExecutionIntent, ExecutionRecord; print('OK')"

# 5. 路由器默认返回 HUMAN
python -c "
from app.core.execution_router import ExecutionRouter
r = ExecutionRouter(openclaw_enabled=False)
d = r.classify(task_type='learning', goal='test')
assert d.execution_mode.value == 'human'
print('OK')
"

# 6. 信任引擎拦截敏感内容
python -c "
from app.core.execution_trust import ExecutionTrustEngine
e = ExecutionTrustEngine()
result = e.evaluate(
    raw_result={'output': 'password=secret123'},
    success_criteria={},
    result_contract={},
)
assert result.trust_level == 'raw'
assert 'sensitive_content' in str(result.blocked_fields)
print('OK')
"
```

### Phase 1 完成标志

```bash
# 1. 分类端点工作
curl -X GET http://localhost:8000/api/v1/executions/health
# {"openclaw_enabled": false, "gateway_url": null}

# 2. Feature flag 关闭时返回 503
curl -X POST http://localhost:8000/api/v1/executions/tasks/{id}/handoff
# 503 Service Unavailable

# 3. 开启后完整流程
# (需要 OpenClaw 实例运行)
```

---

## 七、常见问题

### Q: 如何验证不会影响现有系统？

```bash
# 1. 确保 OPENCLAW_ENABLED=False（默认）
# 2. 运行完整测试套件
cd backend && pytest

# 3. 启动服务，正常使用移动端
# 4. 检查日志无 OpenClaw 相关错误
```

### Q: 如何回滚迁移？

```bash
cd backend
alembic downgrade -1  # 回退一个版本
# 或
alembic downgrade oc001a2b3c4d5  # 回退到特定版本
```

### Q: 如何测试 OpenClaw 连接？

```bash
# 1. 确保 OpenClaw gateway 运行
curl http://127.0.0.1:18789/v1/models

# 2. 设置配置
export OPENCLAW_ENABLED=true
export OPENCLAW_GATEWAY_URL=http://127.0.0.1:18789
export OPENCLAW_AUTH_TOKEN=your_token

# 3. 调用健康检查
curl http://localhost:8000/api/v1/executions/health
```

### Q: 数据污染如何处理？

1. **RAW 级数据**：只存在于 `execution_records` 表，可安全删除
2. **误写入 Task 状态**：需要手动回滚 Task 状态
3. **误写入画像**：需要从 `cognitive_fragments` / `behavior_patterns` 中清理

---

## 八、下一步

1. **阅读详细规格**: `SPARKLE_OPENCLAW_IMPLEMENTATION_SPEC_v1.0.md`
2. **按 Phase 0 文件清单顺序实施**
3. **每完成一个文件，运行测试验证**
4. **Phase 0 完成后汇报，进行验收**
5. **Phase 1-3 依次推进**
