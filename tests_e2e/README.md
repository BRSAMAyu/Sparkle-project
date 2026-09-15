# 端到端测试 (End-to-End Tests)

完整的跨层测试套件,覆盖Flutter → Go Gateway → Python Engine → Database的完整流程。

## 测试架构

```
┌─────────────────────────────────────────────────────┐
│  E2E Test Framework                                 │
│  ├── Fixtures (测试数据准备)                         │
│  ├── Helpers (测试辅助工具)                          │
│  ├── Scenarios (测试场景)                            │
│  └── Assertions (验证工具)                           │
└─────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────┐
│  Flutter (Client Layer)                             │
│  ├── Mock WebSocket Client                          │
│  └── Test State Providers                           │
└─────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────┐
│  Go Gateway (Coordination Layer)                    │
│  ├── Test HTTP Server                               │
│  ├── Mock gRPC Client                               │
│  └── In-Memory Redis                                │
└─────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────┐
│  Python Engine (Intelligence Layer)                 │
│  ├── Mock LLM Service                               │
│  ├── Test Orchestrator                              │
│  └── In-Memory Database                             │
└─────────────────────────────────────────────────────┘
```

## 测试覆盖范围

### 1. 核心流程 E2E (Critical Path)

#### 1.1 聊天系统完整流程
- ✅ 用户发送消息 → WebSocket连接建立
- ✅ Gateway路由验证
- ✅ gRPC调用Python Orchestrator
- ✅ LLM流式响应
- ✅ 响应实时推送到Flutter
- ✅ UI状态更新

#### 1.2 学习计划创建与执行
- ✅ 用户请求创建计划
- ✅ 意图识别与信息收集
- ✅ LLM生成计划任务
- ✅ 任务卡片展示
- ✅ 用户完成任务
- ✅ 进度更新
- ✅ 动态调整反馈

#### 1.3 知识星图系统
- ✅ 知识节点创建
- ✅ 关系建立
- ✅ 可视化渲染
- ✅ 交互操作(拖拽、缩放)

### 2. 跨层集成测试

#### 2.1 用户画像与认知棱镜
- 事件收集 → 画像生成 → 可视化展示

#### 2.2 离线同步机制
- 离线操作 → 队列 → 在线同步 → 冲突解决

#### 2.3 实时通知系统
- 事件触发 → 通知生成 → 跨平台推送

### 3. 边缘场景

#### 3.1 错误处理
- 网络断开重连
- 服务不可用降级
- 超时处理
- 并发冲突

#### 3.2 性能测试
- 大量消息吞吐
- 长连接稳定性
- 内存泄漏检测

## 运行测试

### Python E2E测试
```bash
# 运行所有E2E测试
cd backend
pytest tests_e2e/ -v

# 运行特定场景
pytest tests_e2e/test_chat_e2e.py -v
pytest tests_e2e/test_plan_lifecycle_e2e.py -v

# 带覆盖率报告
pytest tests_e2e/ --cov=app --cov-report=html
```

### Go集成测试
```bash
cd backend/gateway
go test ./internal/handler/... -v -tags=integration
```

### Flutter集成测试
```bash
cd mobile
flutter test integration_test/ --dart-define=SPARKLE_INTEGRATION=true
```

## 测试前置条件

### 环境变量
```bash
# .env.test
SPARKLE_INTEGRATION=true
DATABASE_URL=postgresql://sparkle:test@localhost:5432/sparkle_test
REDIS_URL=redis://localhost:6379/1
LLM_API_KEY=fake_key_for_testing
LLM_BASE_URL=http://localhost:8888/mocking
```

### 服务启动
```bash
# 启动测试依赖
make dev-all

# 或使用Docker Compose
docker compose -f docker-compose.test.yml up -d
```

## 测试数据管理

### Fixtures
测试数据位于 `tests_e2e/fixtures/`:
- `users.json` - 测试用户数据
- `plans.json` - 测试计划数据
- `tasks.json` - 测试任务数据
- `knowledge_nodes.json` - 知识节点数据

### 数据清理
每个测试后自动清理,避免状态污染:
```python
@pytest.fixture(autouse=True)
async def cleanup_test_data(db_session):
    yield
    # 清理测试数据
    await db_session.execute(delete(TestData))
    await db_session.commit()
```

## Mock策略

### LLM服务Mock
```python
@pytest.fixture
async def mock_llm_service():
    async def mock_chat_stream(messages):
        yield ChatChunk(content="Mocked response")
    return mock_chat_stream
```

### Redis Mock
```python
@pytest.fixture
async def mock_redis():
    return FakeRedis()
```

## 持续集成

### GitHub Actions
```yaml
name: E2E Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Start services
        run: make dev-all
      - name: Run Python E2E
        run: cd backend && pytest tests_e2e/
      - name: Run Go integration
        run: cd backend/gateway && go test ./...
      - name: Run Flutter integration
        run: cd mobile && flutter test integration_test/
```

## 贡献指南

添加新的E2E测试:

1. 在对应目录创建测试文件: `tests_e2e/test_feature_e2e.py`
2. 使用现有fixtures和helpers
3. 遵循AAA模式(Arrange-Act-Assert)
4. 添加清晰的文档字符串
5. 确保测试独立运行
6. 清理测试数据

## 故障排查

### 常见问题

**问题**: 测试超时
**解决**: 增加timeout配置或mock慢速依赖

**问题**: 数据库连接失败
**解决**: 检查PostgreSQL是否运行,连接字符串是否正确

**问题**: 测试间相互影响
**解决**: 确保每个测试使用独立的测试数据,或添加清理逻辑
