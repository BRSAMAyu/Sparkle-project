# 深度审计 #64 — Profile Event Consumer 画像事件消费与缓存失效链路

> **日期**: 2026-04-25 07:30
> **模块**: ProfileEventConsumer — EventBus 消费 → 偏好/知识/认知/专注/错题事件 → 缓存失效 + 系统更新 + 信号处理
> **范围**: `profile_event_consumer.py`（206 行）+ `main.py`（启动注册）+ 下游信号处理器
> **总计**: 1 核心文件（206 行）+ 2 关联处理器 + 1 启动点
> **审计员**: Chris (Session 7 复核+新审模式)

---

## 审计范围

ProfileEventConsumer 是画像域缓存一致性的核心消费者。它订阅 Redis Streams 的 `sparkle_events`，处理 6 种事件类型，确保 ProfileContextService、ContextManager、Personalization Engine 的缓存与 DB 保持同步。

### 文件清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `services/profile_event_consumer.py` | 206 | 事件消费 + 缓存失效 + 系统更新推送 |
| `main.py:135-139` | 5 | lifespan 启动 + task 管理 |
| `services/focus_signal_processor.py` | ~100 | 专注会话信号处理（下游） |
| `services/error_book_signal_processor.py` | ~80 | 错题信号处理（下游） |

---

## 数据流图

```
Redis Stream: sparkle_events
    │
    ├── profile.preference.updated ──→ _invalidate_context_cache ✅
    │                                 _invalidate_profile_context_cache ✅
    │                                 invalidate_personalization_cache ✅
    │                                 SystemUpdateService.enqueue (if ai_inferred) ✅
    │
    ├── profile.preference.deleted ──→ _invalidate_context_cache ✅
    │                                 _invalidate_profile_context_cache ✅
    │                                 invalidate_personalization_cache ✅
    │
    ├── knowledge_node_updated ─────→ _invalidate_profile_context_cache ✅
    │   node_mastery_updated ────────→ _invalidate_profile_context_cache ✅
    │
    ├── behavior.pattern.updated ───→ _invalidate_profile_context_cache ✅
    │
    ├── focus.session.completed ────→ FocusSignalProcessor.process_focus_event
    │
    └── error_created / error.created → ErrorBookSignalProcessor + AutoFragmentCollector
```

---

## 审计发现

### P0 — 严重缺陷

#### P0-1: `start()` 方法中 `subscribe` 使用一次性 consumer_name — 重启后无法恢复未处理消息
**文件**: `profile_event_consumer.py:44`
**严重性**: P0 — 消费者组中残留消息在重启后无法被新消费者接管

```python
consumer_name=f"profile-{_utcnow().timestamp()}",
```

`_utcnow().timestamp()` 每次启动生成不同的 consumer_name。这意味着：
1. 上次运行中 pending（XACK 未完成）的消息仍然绑定到旧 consumer_name
2. 新启动的消费者看不到这些 pending 消息
3. 如果 `subscribe` 内部使用 `XREADGROUP` 而非 `XPENDING` + `XCLAIM`，这些消息会永久滞留

**影响**: 偏好更新事件在消费者重启期间丢失 → 缓存不一致 → AI 使用陈旧偏好。

**修复方向**: 使用固定 consumer_name（如 `profile-consumer-1`），或在 `subscribe` 的实现中添加 XPENDING/XCLAIM 逻辑。

#### P0-2: `_handle_focus_session_completed` 和 `_handle_error_created` 不清除 ProfileContext 缓存 — 认知/专注变更后 AI 不知道
**文件**: `profile_event_consumer.py:130-163`
**严重性**: P0 — 专注会话和错题事件不触发 ProfileContext 缓存失效

```python
# :130-139 — focus session completed handler
async def _handle_focus_session_completed(self, event: dict) -> None:
    # ... creates FocusSignalProcessor, processes event
    # ❌ NO call to _invalidate_profile_context_cache(user_id)

# :141-163 — error created handler
async def _handle_error_created(self, event: dict) -> None:
    # ... creates ErrorBookSignalProcessor + AutoFragmentCollector
    # ❌ NO call to _invalidate_profile_context_cache(user_id)
```

对比 `_handle_knowledge_updated` (:117) 和 `_handle_behavior_pattern_updated` (:126)，两者都调用了 `_invalidate_profile_context_cache`。但 focus 和 error 事件不调用。

**影响**:
- 用户完成专注会话 → ProfileContext 的 `cognitive_summary` 可能已变化 → AI 在 5 分钟内不知道
- 用户创建错题 → AutoFragmentCollector 可能添加认知片段 → AI 在 5 分钟内不知道

**修复方向**: 在两个 handler 中添加 `await self._invalidate_profile_context_cache(user_id)`。

---

### P1 — 重要问题

#### P1-1: `_invalidate_context_cache` 在 `redis.delete(*keys)` 时如果 keys 列表为空会报错
**文件**: `profile_event_consumer.py:173`
**严重性**: P1

```python
await self.redis.delete(*keys)  # keys 是 2 元素列表，但模式脆弱
```

当前 `keys` 固定是 2 元素列表，所以 `delete(*keys)` 不会为空。但如果未来维护者修改 `keys` 列表为动态生成且为空时，`redis.delete()` 无参数会抛异常。建议添加 `if keys:` 保护。

#### P1-2: `_normalize_user_id` 不验证 UUID 格式 — 后续 `UUID(user_id)` 可能抛 ValueError
**文件**: `profile_event_consumer.py:186-189, 137, 148`
**严重性**: P1

```python
@staticmethod
def _normalize_user_id(value: Any) -> str:
    if value is None:
        return ""
    return str(value)  # ← 不验证是否是有效 UUID
```

在 `:137` 和 `:148`，返回值被直接传给 `UUID(user_id)`。如果事件中的 `user_id` 是非 UUID 字符串（如 `"anonymous"` 或空字符串以外的垃圾值），`UUID(user_id)` 抛 `ValueError`。虽然有外层 try/except 捕获，但会导致整个事件静默丢弃。

#### P1-3: `_handle_error_created` 中 `linked_node_ids` 未验证类型 — 直接传递给 auto_collector
**文件**: `profile_event_consumer.py:160`
**严重性**: P1

```python
linked_node_ids=event.get("linked_node_ids") or [],
```

`linked_node_ids` 可能是任意类型（字符串、字典、None）。直接传递给 `AutoFragmentCollector.collect_from_error_pattern`，如果该方法不验证输入类型，可能导致下游错误。

---

### P2 — 改进建议

#### P2-1: `start()` 中 subscribe 失败后 `break` — 仅重试一次
**文件**: `profile_event_consumer.py:46-50`

```python
try:
    await self.event_bus.subscribe(...)
    break  # 成功后退出重试循环
except Exception as exc:
    logger.error(f"ProfileEventConsumer error: {exc}")
    await asyncio.sleep(1)  # 1秒后重试
```

如果 subscribe 连续失败（如 Redis 不可用），会无限循环每秒重试。无指数退避、无最大重试次数、无 DLQ。

#### P2-2: `_running` flag 被设置但无 `stop()` 方法
**文件**: `profile_event_consumer.py:34`

`_running = True` 在 `start()` 中设置，但无对应 `stop()` 方法设置 `_running = False`。`main.py` 中也没有调用 `profile_consumer.stop()`（如果存在）的 shutdown 钩子。

#### P2-3: `_handle_preference_updated` 中系统更新消息有硬编码中文
**文件**: `profile_event_consumer.py:80-81`

```python
description = "系统根据你的行为更新了偏好"
title="你的画像偏好已更新",
```

与系统其他模块的 i18n 问题一致。

---

## 合规项

| 检查项 | 状态 | 备注 |
|--------|------|------|
| 缓存失效覆盖完整性 | PARTIAL | 4/6 事件类型有 ProfileContext 失效, focus+error 缺失 (P0-2) |
| ContextManager 缓存失效 | PASS | preference 事件同时清除 `user:context` + `user:context:snapshot` |
| Personalization 缓存失效 | PASS | preference 事件调用 `invalidate_personalization_cache` |
| 错误容忍 | PASS | 所有 handler 有 try/except 保护 |
| Redis 失败保护 | PASS | `_invalidate_*` 方法有 try/except + warning 日志 |
| EventBus 消费者组 | PARTIAL | consumer_name 不可预测 (P0-1) |

---

## 统计

| 级别 | 数量 |
|------|------|
| P0 | 2 |
| P1 | 3 |
| P2 | 3 |
| **总计** | **8** |

---

## 修复优先级建议

| 优先级 | 问题 | 修复方案 | 工作量 |
|--------|------|---------|--------|
| P0-2 | focus/error 不清缓存 | 添加 2 行 `_invalidate_profile_context_cache` | 低（~2 行） |
| P0-1 | consumer_name 不固定 | 改为固定名 `profile-consumer-{N}` | 低（~1 行） |
| P1-2 | user_id 不验证 UUID | 添加 UUID 验证 | 低（~5 行） |
| P2-1 | subscribe 无指数退避 | 添加退避策略 | 中 |

---

## 跨轮次因果链

| 本轮发现 | 关联轮次 | 关联模式 |
|----------|---------|---------|
| P0-1 (consumer_name 不固定) | Round #3 (EventBus 无 XAUTOCLAIM) | 消费者组消息恢复机制不完整 |
| P0-2 (focus/error 不清缓存) | Round #61 P0-1 (ProfileContext 缓存不清除→FALSE) | #61 P0-1 被判 FALSE 因为 4 种事件有缓存清除, 但现在发现实际是 6 种事件中只有 4 种覆盖 |
| P1-2 (UUID 不验证) | Round #58 P0-1 (event dict 零校验) | 事件 payload 入口校验缺失的系统性问题 |
