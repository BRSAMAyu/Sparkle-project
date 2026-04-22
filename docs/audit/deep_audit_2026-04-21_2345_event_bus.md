# 深度审计：Redis Event Bus 完整链路

> 日期：2026-04-21 23:45
> 范围：EventBus 发布路径 → Stream 消费 → DLQ → 跨系统桥接（Community/Galaxy/Achievement）→ 幂等性 → 告警

## 审计发现

### P0 — 阻断性问题（6 项）

#### P0-1: EventBus 主 Stream XADD 无 maxlen 参数，内存无限增长
- **位置**: `backend/app/core/event_bus.py:896`
- **问题**: `EVENT_BUS_STREAM_MAXLEN=50000` 配置存在但仅用于 retry/DLQ stream，主 stream 的 XADD 未设置 MAXLEN
  ```python
  # event_bus.py:896 — 主发布路径
  result = await self.redis.xadd(self.stream_name, fields_dict)
  # 对比 retry stream (有 maxlen):
  # event_bus.py:retry 路径
  await self.redis.xadd(self.retry_stream_name, fields_dict, maxlen=self.maxlen)
  ```
- **影响**: 高频事件（TaskCompleted, ErrorCreated 等）在 24h 内可积累数百万条，Redis 内存溢出触发 OOM
- **修复**: 主 stream XADD 添加 `maxlen=self.maxlen`（约 ~50000 条，近似裁剪可接受）

#### P0-2: EventBus 发布失败静默丢弃，无持久化无重试
- **位置**: `backend/app/core/event_bus.py:900-902`
- **问题**: `xadd` 异常时仅打 WARNING 日志并返回 None，事件永久丢失
  ```python
  except Exception as e:
      logger.warning(f"Failed to publish event: {e}")
      return None  # 事件丢失，无 fallback
  ```
- **影响**: 成就解锁、任务完成、知识节点更新等关键业务事件在 Redis 抖动时丢失，用户无感知
- **修复**: (1) 本地 outbox 表持久化未发送事件 (2) 后台任务补偿重发 (3) 关键事件发布失败应 raise 而非静默

#### P0-3: Consumer 崩溃后 Pending Entries 无自动回收
- **位置**: `backend/app/core/event_bus.py` 消费者逻辑
- **问题**: 无 XAUTOCLAIM 机制。消费者崩溃后，pending entries 永久停留在 XPENDING 列表中
- **影响**: 长期运行后 pending 积压，新消息消费延迟增加；崩溃消费者的消息永远不会被重新处理
- **修复**: 添加 XAUTOCLAIM 定时任务（idle > 60s 的 pending entries 自动转移给活跃消费者）

#### P0-4: CommunitySignalBridge 多写操作无事务保护
- **位置**: `backend/app/services/community_signal_bridge.py`
- **问题**: 处理 group_activity 事件时涉及多次 Redis/DB 写操作，任一步骤失败导致数据不一致
  - 写入个人上下文缓存
  - 更新社群活跃度指标
  - 触发认知服务更新
  - 以上操作不在同一事务中
- **影响**: 部分写入成功、部分失败，用户看到不一致的社群状态
- **修复**: 使用 Redis Pipeline 或 Lua 脚本保证原子性；DB 操作使用事务块

#### P0-5: GalaxyEventConsumer 多表写入异常静默吞没
- **位置**: `backend/app/services/galaxy_event_consumer.py`
- **问题**: 处理 ErrorCreated 事件时涉及 knowledge_node + error_book + cognitive_fragment 三表写入，外层 `except Exception` 静默捕获
  ```python
  try:
      # 写入 1: knowledge_node
      # 写入 2: error_book entry
      # 写入 3: cognitive_fragment
  except Exception as e:
      logger.error(f"Failed to handle error created: {e}")
      # 部分写入成功但不回滚，数据不一致
  ```
- **影响**: 错题记录可能存在 knowledge_node 但无 error_book entry，或反之
- **修复**: 包裹在 DB 事务中；失败时写入 DLQ 并记录 correlation_id

#### P0-6: EventBus 幂等性检查 get→lock 非原子操作（竞态条件）
- **位置**: `backend/app/core/event_bus.py` 幂等性保护逻辑
- **问题**: 先 GET 检查是否已处理，再 SET 加锁，两步非原子
  ```
  时序: Consumer A: GET(idempotency_key) → None
        Consumer B: GET(idempotency_key) → None  (此时 A 尚未 SET)
        Consumer A: SET(idempotency_key, "processing")
        Consumer B: SET(idempotency_key, "processing")  → 两个 consumer 同时处理
  ```
- **影响**: 高并发下同一事件被两个消费者重复处理，导致重复成就解锁、重复积分发放
- **修复**: 使用 `SET key value NX EX ttl` 原子操作替代 GET→SET 两步

---

### P1 — 重要问题（5 项）

#### P1-1: EventBus 无 payload 大小限制
- **位置**: `backend/app/core/event_bus.py:860-905`
- **问题**: 事件 payload 未做大小校验，理论上单条事件可达数 MB（如含完整对话历史）
- **影响**: 大 payload 压入 Redis Stream 导致内存压力和消费延迟
- **修复**: 添加 `MAX_EVENT_PAYLOAD_SIZE = 64KB` 检查，超限时截断或拆分

#### P1-2: 无事件类型注册表（27 种事件类型为硬编码字符串）
- **位置**: `backend/app/core/event_bus.py` 事件类定义
- **问题**: 27 种事件类型散布在多个文件中，无中央注册表，无法枚举所有事件类型
- **影响**: 新增事件类型时无法验证 schema 合规性；无法生成事件依赖图
- **修复**: 创建 `EventTypeRegistry`，要求所有事件类型注册并附带 schema 定义

#### P1-3: DLQ 无告警机制
- **位置**: DLQ 消费逻辑
- **问题**: 事件进入 DLQ 后仅日志记录，虽有 Prometheus counter 但无主动告警规则
- **影响**: 业务事件静默失败，运维团队无感知，直到用户投诉
- **修复**: (1) 添加 `SparkleDLQDepthHigh` Prometheus 告警规则 (2) DLQ 深度 >10 时触发 Alertmanager 通知

#### P1-4: Consumer 数量固定为 1，吞吐量瓶颈
- **位置**: EventBus consumer group 配置
- **问题**: 每个 consumer group 仅 1 个消费者实例
- **影响**: 高频事件（TaskCompleted, ProfilePreferenceUpdated）消费延迟
- **修复**: 支持动态 consumer 数量；高频事件类型使用独立 consumer group

#### P1-5: CommunitySignalBridge handle_resource_shared 缺幂等保护
- **位置**: `backend/app/services/community_signal_bridge.py`
- **问题**: 资源分享事件处理无 idempotency key，重复消费会重复发放 mastery bonus
- **修复**: 添加 `resource_shared:{resource_id}:{user_id}` 幂等键

---

### P2 — 改进建议（3 项）

#### P2-1: GalaxyEventConsumer _handle_error_created 缺 error_id 去重
- **位置**: `backend/app/services/galaxy_event_consumer.py`
- **问题**: 重复的 ErrorCreated 事件会创建重复的 knowledge_node
- **修复**: 先查询 error_id 是否已有对应 node 再创建

#### P2-2: AchievementEngine 奖励发放失败后成就已解锁
- **位置**: `backend/app/services/achievement_engine.py`
- **问题**: 成就解锁和 photon 奖励发放非原子；奖励失败后成就仍显示已解锁
- **修复**: 事务包裹，或添加补偿机制确保最终一致

#### P2-3: Idempotency TTL 24h 可能不足
- **位置**: EventBus idempotency 配置
- **问题**: 消费者宕机超过 24h 后恢复，幂等键已过期，可能重复处理
- **修复**: TTL 延长至 72h 或与 XAUTOCLAIM idle 阈值对齐

---

### 合规项（4 项）

1. **EventBus 幂等性框架存在** ✅ — 有 idempotency key 机制，虽非原子但框架完整
2. **重试机制完备** ✅ — max 3 次重试 + 指数退避 + DLQ 转移
3. **Prometheus 指标覆盖** ✅ — `sparkle_event_published_total`, `sparkle_event_consumed_total`, `sparkle_event_dlq_total` 等
4. **Retry/DLQ Stream 有 maxlen** ✅ — 防止 retry 和 DLQ stream 无限增长

---

## 数据流图

```
Publisher (任意 Service)
  │  event_bus.publish(Event(data))
  ↓
EventBus._publish()
  │  XADD main_stream [fields]  ⚠️ 无 maxlen
  │  失败 → 返回 None ⚠️ 事件丢失
  ↓
Redis Stream (main_stream)
  │  ⚠️ 无限增长 (无 maxlen)
  │  消费者组: community_cg, galaxy_cg, achievement_cg, ...
  ↓
Consumer (各 EventConsumer)
  │  XREADGROUP → 获取消息
  │  幂等检查: GET key → SET key ⚠️ 非原子
  │  处理事件
  │   ├── 成功 → XACK
  │   └── 失败 → 重试 (max 3) → DLQ
  ↓
Cross-System Bridges
  ├── CommunitySignalBridge  ⚠️ 多写无事务
  ├── GalaxyEventConsumer    ⚠️ 异常静默吞没
  └── AchievementEventConsumer  ⚠️ 奖励非原子
  ↓
DLQ Stream
  │  maxlen=50000 ✅
  │  ⚠️ 无告警
  ↓
监控
  Prometheus counters ✅
  无 DLQ 告警规则 ⚠️
```

---

## 建议修复方案

| 优先级 | 问题 | 修复方案 | 工作量 |
|--------|------|---------|--------|
| P0-1 | 主 Stream 无 maxlen | XADD 添加 maxlen 参数 | 低（~5 行 Python） |
| P0-2 | 发布失败静默丢弃 | Outbox 表 + 补偿重发 + 关键事件 raise | 中（~100 行 Python） |
| P0-3 | Pending 无自动回收 | XAUTOCLAIM 定时任务 | 中（~60 行 Python） |
| P0-4 | Bridge 多写无事务 | Redis Pipeline / DB 事务 | 中（每桥 ~40 行） |
| P0-5 | Galaxy 多表写异常 | DB 事务 + DLQ + correlation_id | 中（~50 行 Python） |
| P0-6 | 幂等 get→lock 竞态 | SET NX EX 原子操作 | 低（~10 行 Python） |
| P1-1 | 无 payload 大小限制 | 添加 64KB 检查 | 低（~10 行） |
| P1-2 | 无事件类型注册表 | EventTypeRegistry + schema | 中（~80 行 Python） |
| P1-3 | DLQ 无告警 | Prometheus alert rule | 低（~10 行 YAML） |
| P1-4 | Consumer 数=1 | 动态 consumer + 独立 group | 中（~50 行） |
| P1-5 | 资源分享缺幂等 | 添加 idempotency key | 低（~10 行） |
