# Sparkle 测试质量升级 — 完整任务书

> **目标**: 让每一行测试都真正验证生产行为，而不是为覆盖率数字服务。测试必须能捕获真实 bug。
> **衡量标准**: 如果一个 P0 bug（如 kwargs NameError、重复代码块）能通过所有现有测试，说明测试体系本身有问题。

---

## 0. 前置：你必须了解的项目结构

```
backend/
├── app/                    # 生产代码
│   ├── orchestration/      # 核心编排（orchestrator, dual_core_router, spine）
│   ├── services/           # 30+ 服务
│   ├── signals/            # Signal Spine（spine_orchestrator 4400+ 行）
│   ├── core/               # event_bus, config, kill_switch
│   └── state_aggregator/   # Aurora 状态聚合
├── tests/
│   ├── unit/               # 单元测试（主要在这里）
│   ├── integration/        # 集成测试
│   ├── contract/           # 契约测试
│   ├── workflow/           # 工作流测试
│   └── conftest.py         # 全局 fixtures
├── scripts/                # 21 个验收脚本
└── alembic/                # 52 个数据库迁移

backend/gateway/            # Go Gateway
├── internal/
│   ├── handler/            # HTTP/WS handlers
│   ├── agent/client.go     # gRPC client（17 RPC 方法）
│   ├── middleware/          # 16 中间件
│   └── db/                 # sqlc 生成代码
└── tests/                  # Go 测试

mobile/                     # Flutter
├── lib/features/           # 24 个功能模块
├── test/                   # Flutter 测试
└── integration_test/       # 集成测试
```

---

## 1. 核心原则

### 1.1 测试必须能捕获真实 bug

以下 bug 曾通过全部测试。你的首要任务是确保类似 bug 不再漏过：

- **B-001** (`achievement_engine.py:451`): `_get_relevant_achievements(event_type: str)` 调用了 `kwargs.get()` 但签名没有 `**kwargs` → NameError
- **B-002** (`spine_orchestrator.py:206-475`): 5 处完全相同的代码块（双写 Redis、双调方法、指标虚高 2x）
- **B-003** (`event_bus.py:795 vs 1584`): 同名类 `DocumentCitationFeedbackEvent` 定义两次，字段不同
- **B-004** (`memory_service.py:382`): `update_goal` 缺少 `SELECT FOR UPDATE`，并发覆盖
- **B-005** (`cognitive_service.py:38`): 模块级 Set 只增不减，用户永久被排除

**对每个 bug，写一个回归测试，证明修复前测试会失败。**

### 1.2 Mock 最小化

当前状态：3,235 处 mock/patch。很多测试 mock 了所有依赖后测试什么都不验证。

**规则**:
- 数据库操作：用真实 SQLite/PostgreSQL（`conftest.py` 已有 `async_session` fixture）
- Redis 操作：用真实 Redis（`conftest.py` 应有 redis fixture，没有就创建）
- LLM 调用：可以 mock（成本原因），但必须验证 mock 返回值的结构匹配真实 LLM 响应格式
- 服务间调用：优先用真实实例，仅 mock 外部 HTTP/gRPC

### 1.3 断言必须有意义

**无效断言**（禁止）:
```python
assert result is not None  # 只验证没崩溃
mock_service.process.assert_called_once()  # 只验证调用了，不验证结果
```

**有效断言**（要求）:
```python
assert result.strategy_key == "study_session_defense"
assert len(result.execution_constraints) > 0
assert result.confidence >= 0.0 and result.confidence <= 1.0
# 验证状态机的状态转移
assert fsm.current_state == "GENERATING"
assert "kwargs" in inspect.signature(engine._get_relevant_achievements).parameters
```

---

## 2. 具体任务（按优先级排序）

### Phase 1: 回归测试 — Bug 血的教训（最高优先级）

为以下 5 个已修复 bug 各写一个回归测试，确保不会再犯：

#### T1.1 achievement_engine kwargs 回归测试
**文件**: `backend/tests/unit/test_achievement_engine_regression.py`（新建）

```python
async def test_hidden_trigger_requires_kwargs():
    """B-001 回归: HIDDEN_TRIGGER 事件必须接受 **kwargs"""
    sig = inspect.signature(AchievementEngine._get_relevant_achievements)
    assert "kwargs" in sig.parameters

async def test_hidden_trigger_no_name_error(mock_db, engine):
    """B-001 回归: 传入 HIDDEN_TRIGGER + kwargs 不应 NameError"""
    engine._get_all_achievements = AsyncMock(return_value=[
        Achievement(trigger_code="HIDDEN_TRIGGER", ...)
    ])
    # 不应抛出 NameError
    result = await engine._get_relevant_achievements(
        AchievementEvent.HIDDEN_TRIGGER,
        hidden_trigger_code="EASTER_EGG"
    )
    assert len(result) >= 1

async def test_process_event_passes_kwargs_through():
    """验证 process_event 将 kwargs 传递到 _get_relevant_achievements"""
    # 用 spy 验证调用链
```

#### T1.2 spine_orchestrator 去重回归测试
**文件**: `backend/tests/unit/test_spine_dedup_regression.py`（新建）

```python
async def test_state_register_upsert_called_once():
    """B-002 回归: state_register.upsert_from_signal 每个信号只调一次"""
    spine = ...  # 真实实例
    spine.state_register.upsert_from_signal = AsyncMock()
    await spine.on_task_completed(...)
    assert spine.state_register.upsert_from_signal.call_count == 1

async def test_metrics_receipt_shown_called_once():
    """B-002 回归: record_receipt_shown 不应重复调用"""
    spine.metrics.record_receipt_shown = AsyncMock()
    # ... 触发有 receipt 的场景
    assert spine.metrics.record_receipt_shown.call_count == 1

async def test_aurora_control_signal_written_once():
    """B-002 回归: AuroraControlSignal 只写入一次"""
    # 检查 Redis SET 调用次数

async def test_no_duplicate_store_directive_by_id():
    """B-002 回归: 每个 _store_*_directive 方法中 store_directive_by_id 只调一次"""
    for method_name in [
        "_store_notification_directive",
        "_store_retrieval_directive",
        "_store_plan_directive",
        "_store_model_write_directive",
        "_store_ux_directive",
    ]:
        # 验证每个方法体中 store_directive_by_id 只出现一次
```

#### T1.3 event_bus 重复类定义回归测试
**文件**: `backend/tests/unit/test_event_bus_regression.py`

```python
def test_no_duplicate_event_class_names():
    """B-003 回归: event_bus.py 中不应有同名类定义"""
    # 用 AST 解析，检查所有 class 定义名唯一
    import ast
    with open("backend/app/core/event_bus.py") as f:
        tree = ast.parse(f.read())
    class_names = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    assert len(class_names) == len(set(class_names)), f"重复类名: {[n for n in class_names if class_names.count(n) > 1]}"
```

#### T1.4 memory_service 竞态回归测试
**文件**: `backend/tests/unit/test_memory_service_regression.py`

```python
async def test_update_goal_uses_row_lock():
    """B-004 回归: update_goal 必须使用 SELECT FOR UPDATE"""
    # 并发调用 update_goal，验证不会丢失更新
    async def concurrent_update(field, value):
        async with AsyncSessionLocal() as session:
            svc = MemoryService(session)
            await svc.update_goal(user_id, goal_id, **{field: value})

    await asyncio.gather(
        concurrent_update("title", "Title A"),
        concurrent_update("description", "Desc B"),
    )
    # 两个更新都应生效
    goal = await svc.get_goal(user_id, goal_id)
    assert goal.title == "Title A"
    assert goal.description == "Desc B"
```

#### T1.5 cognitive_service 无界集合回归测试
**文件**: `backend/tests/unit/test_cognitive_service_regression.py`

```python
async def test_disabled_users_has_ttl_eviction():
    """B-005 回归: 被禁用用户应在 TTL 后自动恢复"""
    from app.services.cognitive_service import _VECTOR_RUNTIME_DISABLED_USERS
    # 添加用户
    _VECTOR_RUNTIME_DISABLED_USERS["test_user"] = datetime.now() - timedelta(hours=2)
    # 调用检查函数，应自动清理过期条目
    result = _is_vector_runtime_enabled_for_user("test_user")
    assert result is True  # TTL 过期，应重新启用
    assert "test_user" not in _VECTOR_RUNTIME_DISABLED_USERS

async def test_disabled_users_has_size_cap():
    """B-005 回归: 超过 10000 条时自动淘汰"""
    # 填充 10001 条
    for i in range(10001):
        _VECTOR_RUNTIME_DISABLED_USERS[f"u_{i}"] = datetime.now()
    assert len(_VECTOR_RUNTIME_DISABLED_USERS) <= 10000
```

---

### Phase 2: Spine 端到端集成测试

当前 spine 测试全部是 mock 的。需要真实 Redis 的集成测试。

#### T2.1 Spine 全链路集成测试
**文件**: `backend/tests/integration/test_spine_e2e.py`（新建）

```python
@pytest.fixture
async def real_redis():
    """连接真实 Redis（docker compose 中的 redis）"""
    import redis.asyncio as aioredis
    client = aioredis.from_url("redis://localhost:6379/0")
    yield client
    # 清理测试数据
    keys = await client.keys("spine:test:*")
    if keys:
        await client.delete(*keys)

@pytest.fixture
async def real_db():
    """真实 PostgreSQL session"""
    async with AsyncSessionLocal() as session:
        yield session

async def test_task_completed_generates_directive_end_to_end(real_redis, real_db):
    """完整信号链: task.completed → signal → policy → directive → Redis"""
    spine = SpineOrchestrator(redis_client=real_redis, db=real_db, ...)
    trace = await spine.on_task_completed(
        user_id="test_user_001",
        task_id="task_001",
        plan_id="plan_001",
        completed_at=datetime.now(UTC),
        actual_duration_min=45,
    )

    # 验证完整链路
    assert trace.trace_id is not None
    assert len(trace.signal_ids) > 0

    # 验证 Redis 中确实写入了 directive
    directive_raw = await real_redis.get("spine:directive:active:test_user_001")
    assert directive_raw is not None

    # 验证 state register 有记录
    state_keys = await real_redis.smembers("spine:state_index:test_user_001")
    assert len(state_keys) > 0

async def test_duplicate_signal_idempotent(real_redis, real_db):
    """相同事件不应产生重复 directive"""
    spine = SpineOrchestrator(...)
    trace1 = await spine.on_task_completed(user_id="u1", task_id="t1", ...)
    trace2 = await spine.on_task_completed(user_id="u1", task_id="t1", ...)

    # 验证 Redis 中只有一份 directive
    keys = await real_redis.keys("spine:directive:*:u1:*")
    directive_keys = [k for k in keys if "active" not in k]
    # 每种类型最多一个
    ...

async def test_receipt_user_action_flows_back(real_redis, real_db):
    """Receipt 用户操作 → outcome 记录 → 关系模型更新"""
    # 1. 触发 task.completed 产生 receipt
    # 2. 模拟用户 dismiss
    # 3. 验证 outcome 被记录
    # 4. 验证 relationship trust 被更新
```

#### T2.2 Event Bus 集成测试
**文件**: `backend/tests/integration/test_event_bus_e2e.py`

```python
async def test_retry_requeue_preserves_payload(real_redis):
    """重试 requeue 后消息体完整"""
    bus = EventBus(redis=real_redis)
    await bus.publish("test_stream", TestEvent(data="original"))
    # 模拟消费失败
    # 验证 requeue 后消息体一致

async def test_stale_and_new_both_processed(real_redis):
    """stale 和 new 消息都应被处理"""
    # 发布 3 条消息
    # 模拟消费者 crash（不 ack）
    # 重启消费者
    # 验证 3 条 stale + 新消息都被处理
```

---

### Phase 3: Go Gateway 测试升级

当前 Go 覆盖率阈值 4%，极低。

#### T3.1 新 RPC 方法测试
**文件**: `backend/gateway/internal/agent/client_test.go`（扩展）

```go
func TestRetrieveMemory(t *testing.T) {
    // 验证 RetrieveMemory 正确传递 metadata (user_id, auth)
    // 验证错误处理（gRPC unavailable）
    // 验证重连后重试
}

func TestGetUserProfile(t *testing.T) { ... }
func TestSubmitContentReviewFeedback(t *testing.T) { ... }
func TestSubmitReviewOverride(t *testing.T) { ... }
func TestSubmitReviewAppeal(t *testing.T) { ... }
func TestGetAppealStatus(t *testing.T) { ... }
func TestSubmitReviewFeedback(t *testing.T) { ... }
func TestRequestRegeneration(t *testing.T) { ... }
func TestGetFeedbackStatistics(t *testing.T) { ... }
func TestGetArbitrationQueue(t *testing.T) { ... }
func TestAssignArbitrationCase(t *testing.T) { ... }
func TestSubmitArbitrationDecision(t *testing.T) { ... }
func TestGetArbitrationQueueStats(t *testing.T) { ... }
```

每个测试必须验证：
1. 正确的 gRPC 请求构造
2. `injectMetadata` 被调用（认证上下文）
3. 连接失败时的重连逻辑
4. 响应正确解析

#### T3.2 中间件安全测试
**文件**: `backend/gateway/internal/middleware/auth_test.go`（扩展）

```go
func TestAuthMiddleware_RejectsExpiredToken(t *testing.T) { ... }
func TestAuthMiddleware_RejectsTamperedPayload(t *testing.T) { ... }
func TestAuthMiddleware_FailClosed_WhenRedisDown(t *testing.T) { ... }
func TestAuthMiddleware_BlacklistedToken_Rejected(t *testing.T) { ... }
func TestRateLimitMiddleware_BurstExceeded(t *testing.T) { ... }
func TestCORSMiddleware_RejectsUnknownOrigin(t *testing.T) { ... }
func TestSecurityHeaders_AllPresent(t *testing.T) {
    // 验证 CSP, HSTS, X-Frame-Options, Permissions-Policy 全部存在
}
```

---

### Phase 4: CI 质量门升级

#### T4.1 覆盖率阈值调整
**文件**: `.github/workflows/ci.yml`

```yaml
# 从
COVERAGE_THRESHOLD_GO: '4'
COVERAGE_THRESHOLD_PYTHON: '25'
COVERAGE_THRESHOLD_FLUTTER: '8'

# 调整为（分阶段，不要一步到位）
# 第一步（本次）:
COVERAGE_THRESHOLD_GO: '15'
COVERAGE_THRESHOLD_PYTHON: '40'
COVERAGE_THRESHOLD_FLUTTER: '20'
```

#### T4.2 启用 CI 失败阻断
**文件**: `.github/workflows/ci.yml`

将所有 `fail_ci_if_error: false` 改为 `fail_ci_if_error: true`。

#### T4.3 添加重复代码检测
**文件**: `.pre-commit-config.yaml` 或 CI step

```yaml
- name: Detect duplicate code blocks
  run: |
    python scripts/check_duplicate_code_blocks.py backend/app/signals/spine_orchestrator.py
```

创建 `scripts/check_duplicate_code_blocks.py`：
- 扫描 Python 文件中连续 ≥3 行的重复代码块
- 对 `_store_*` 系列方法验证无重复调用
- 在 CI 中作为阻塞门

---

### Phase 5: Flutter 测试升级

#### T5.1 WebSocket 服务测试
**文件**: `mobile/test/services/community_websocket_service_test.dart`

```dart
test('disconnectGroup cancels subscription', () async {
  final service = CommunityWebSocketService(...);
  await service.connectToGroup('group-1', token: 'test-token');
  expect(service._groupSubscription, isNotNull);
  await service.disconnectGroup();
  // 验证 subscription 已取消
  // 验证 channel 已关闭
});

test('reconnect does not leak old subscriptions', () async {
  // 连接 → 断开 → 再连接
  // 验证只有一份活跃 subscription
});

test('message deduplication works correctly', () async {
  // 发送重复消息
  // 验证 handler 只被调用一次
});
```

---

## 3. 验证标准

完成以下所有项才算通过：

### 3.1 回归测试覆盖
- [ ] 5 个已知 bug 各有回归测试
- [ ] 每个回归测试在 bug 代码上会失败，在修复代码上会通过
- [ ] `pytest tests/unit/test_*_regression.py` 全部通过

### 3.2 集成测试
- [ ] Spine 全链路测试使用真实 Redis
- [ ] Event bus 测试使用真实 Redis Streams
- [ ] `pytest tests/integration/ -v` 全部通过

### 3.3 Go 测试
- [ ] 17 个 RPC 方法各有至少 1 个测试
- [ ] 安全中间件有针对性测试
- [ ] `cd backend/gateway && go test ./...` 全部通过
- [ ] Go 覆盖率 ≥ 15%

### 3.4 CI 门控
- [ ] 覆盖率阈值已提升
- [ ] `fail_ci_if_error: true` 已启用
- [ ] 重复代码检测已加入 CI
- [ ] CI 完整运行通过

### 3.5 Flutter 测试
- [ ] WebSocket 订阅管理有测试
- [ ] `flutter test` 全部通过

---

## 4. 禁止事项

- ❌ 不要为了提高覆盖率数字而写无意义测试
- ❌ 不要 mock 被测系统本身（mock 外部依赖，不 mock 被测代码）
- ❌ 不要跳过失败的测试（不用 `@pytest.skip` 或 `try/except pass` 掩盖）
- ❌ 不要修改生产代码来适配测试（除非是修复 bug）
- ❌ 不要降低任何已有的测试断言严格度

## 5. 执行顺序

```
Phase 1 (回归测试) → Phase 2 (Spine 集成) → Phase 3 (Go 测试) → Phase 4 (CI 门) → Phase 5 (Flutter)
```

Phase 1 是硬性前置——没有回归测试，后续工作没有意义。

## 6. 完成标志

当你完成所有 Phase 后，运行以下命令并全部通过：

```bash
# Python 回归测试
cd backend && pytest tests/unit/test_*_regression.py -v

# Python 集成测试（需要 Redis + PostgreSQL）
cd backend && pytest tests/integration/ -v

# Go 测试
cd backend/gateway && go test ./... -race -coverprofile=coverage.out
go tool cover -func=coverage.out | tail -1  # 验证 ≥ 15%

# Flutter 测试
cd mobile && flutter test

# CI 模拟
bash scripts/check_duplicate_code_blocks.py backend/app/signals/spine_orchestrator.py
```

全部绿色 = 任务完成。
