# 深度审计：通知/推送系统完整链路

> 日期：2026-04-22 02:45
> 范围：`push_service.py` 推送策略 → `push_sender_service.py` FCM 发送 → `jpush_sender_service.py` 极光推送 → `push_router_service.py` 路由 → `push_feedback_service.py` 反馈闭环 → `push_policy_compiler.py` 策略编译 → `nudge_service.py` 触发 → `notification_center_service.py` 通知中心 → `calendar.py` 日历提醒 → Flutter 通知中心 → DB schema（6 张核心表）

## 审计发现

### P0 — 阻断性问题（2 项）

#### P0-1: 主动推送策略从未被调度执行，5 个策略引擎全部为死代码
- **位置**: `backend/app/services/push_service.py:30-123` (process_all_users) + `backend/app/celery_schedule.py` (仅清理任务)
- **问题**: `PushService` 实现了 5 个主动推送策略（Memory/Sprint/Inactivity/Curiosity/EmptyCapsule），但 `process_all_users()` 从未被 Celery beat 或任何定时任务调用
  ```python
  # push_service.py:30 — 入口存在但无调度
  async def process_all_users(self) -> list[dict]:
      """处理所有用户的推送需求"""
      # Memory策略: 检查知识节点掌握度低于阈值的用户
      # Sprint策略: 检查任务截止日期临近的用户
      # Inactivity策略: 检查24h+未活跃的用户
      # Curiosity策略: 按概率触发好奇心推送
      # EmptyCapsule策略: 检查空认知胶囊用户
  
  # celery_schedule.py — 仅注册了清理任务:
  sender.add_periodic_task(86400.0, cleanup_outbox_events.s())
  sender.add_periodic_task(86400.0, cleanup_galaxy_outbox.s())
  # ❌ 无: sender.add_periodic_task(3600.0, process_all_pushes.s())
  ```
- **影响**: 5 个精心设计的推送策略（含个性化引擎集成、频率上限、静默时段）在运行时完全不会触发。用户不会收到任何主动推送（学习提醒、截止日期通知、好奇心激发等）。仅事件驱动的 nudge 可工作
- **修复**: 在 `celery_schedule.py` 中注册推送处理任务（建议每小时执行），添加到 Celery beat 调度

#### P0-2: 日历提醒调度完全未实现，reminder_minutes 字段为死数据
- **位置**: `backend/app/api/v1/calendar.py:147` + `schema.sql` (reminder_minutes 列)
- **问题**: `calendar_events` 表有 `reminder_minutes jsonb` 字段，用户可在 UI 设置提醒时间（如提前 15/30/60 分钟），但**无任何调度逻辑**
  ```python
  # calendar.py:147 — 仅有 TODO 注释
  # TRACKED(TD-006): 调度提醒通知
  # 没有后续代码，提醒永远不会被发送
  ```
  ```sql
  -- schema.sql — 字段存在但无用
  reminder_minutes jsonb DEFAULT '[]'::jsonb NOT NULL,  -- 存储但从未消费
  ```
- **对比**: 日历事件确实通过 Event Bus 发布（CalendarEventCreated/Updated/Deleted），但仅被 profile_event_consumer 用于**缓存失效**（:41-43），不触发通知
- **影响**: 用户设置日历提醒后永远不会收到通知，功能名存实亡
- **修复**: (1) 创建 Celery 任务，每 5 分钟扫描即将到期的 reminder (2) 匹配当前时间 + reminder_minutes → 发送推送

---

### P1 — 重要问题（5 项）

#### P1-1: 推送发送失败无重试机制，瞬态故障导致通知永久丢失
- **位置**: `backend/app/services/push_sender_service.py:246-259` + `nudge_service.py:89-90`
  ```python
  # nudge_service.py:89-90 — 失败仅日志
  except Exception as e:
      logger.error(f"Failed to send push notification for nudge: {e}")
  # 无: retry, DLQ, exponential backoff
  ```
- **影响**: 网络超时、FCM/JPush 限流等瞬态故障导致通知永久丢失
- **修复**: 添加 Celery 重试任务 + 指数退避（max_retries=3）

#### P1-2: 通知表无清理任务，notifications/push_histories 无限增长
- **位置**: `backend/app/celery_schedule.py` + `schema.sql` (notifications, push_histories, notification_interactions 表)
- **问题**: 仅 outbox_events 和 galaxy_outbox 有清理任务；notifications 和 push_histories 表无定期清理，仅依赖 `deleted_at` 软删除但无归档任务
- **修复**: 添加每日清理任务，归档 >90 天的通知和 >180 天的推送历史

#### P1-3: Flutter 通知无本地持久化，离线无法查看
- **位置**: `mobile/lib/features/notification_center/presentation/providers/notification_center_provider.dart`
- **问题**: 通知仅存在于内存（Riverpod state），无 SQLite/Isar/Hive 缓存
- **影响**: 网络断开或 App 重启后，用户无法查看任何历史通知
- **修复**: 使用 Hive 缓存最近 100 条通知到本地

#### P1-4: 专注模式完成不触发通知，focus.session.completed 事件仅失效缓存
- **位置**: `backend/app/services/focus_service.py:142-149` (事件发布) + `profile_event_consumer.py:154-163` (仅缓存失效)
- **问题**: `focus.session.completed` 事件发布后，唯一消费者（ProfileEventConsumer）仅做缓存失效，不创建祝贺通知或成就进度更新
- **修复**: 添加 FocusEventConsumer，专注完成后发送鼓励通知 + 触发 AchievementEngine 检查

#### P1-5: SystemUpdateService 仅 Redis 存储，Redis 故障时通知丢失
- **位置**: `backend/app/services/system_update_service.py:23-37`
  ```python
  # 仅写 Redis list，无 DB fallback
  await self.redis.lpush(f"system_updates:{user_id}", json.dumps(update))
  await self.redis.ltrim(f"system_updates:{user_id}", 0, self.MAX_ITEMS - 1)  # 200 条上限
  await self.redis.expire(f"system_updates:{user_id}", self.TTL_SECONDS)  # 7 天 TTL
  ```
- **修复**: 添加 DB 写入作为持久化备份，Redis 作为热数据层

---

### P2 — 改进建议（3 项）

#### P2-1: Flutter 通知操作按钮硬编码中文，未国际化
- **位置**: `mobile/lib/core/services/notification_service.dart:414-426`
  ```dart
  // 硬编码中文文本
  actions: [TextInputAction(⬅ "⚡ 开始"), TextInputAction("💤 稍后"), TextInputAction("🔕 勿扰")]
  ```
- **修复**: 使用 `context.l10n` 国际化字符串

#### P2-2: Device ID 使用 hashCode 生成，存在碰撞风险
- **位置**: `mobile/lib/core/services/push_token_manager.dart:54`
- **修复**: 使用 UUID v5 或 SHA-256 替代 hashCode

#### P2-3: 日历数据仅通过 context_manager 注入 prompts，未进入 ContextPack
- **位置**: `backend/app/core/context_pack.py` (无 calendar 段) vs `context_manager.py:285-290` (有 _get_calendar_context)
- **问题**: 日历上下文通过 context_manager → prompts.py 渲染（✅ 可工作），但未通过 ContextPack 标准化路径
- **修复**: 将日历上下文迁移到 ContextPackBuilder

---

### 合规项（5 项）

1. **双通道推送** ✅ — FCM（国际）+ JPush（中国）智能路由，PushRouterService 按区域/设备自动选择
2. **无效 Token 清理** ✅ — push_sender_service 检测 UNREGISTERED/INVALID_ARGUMENT 错误码并标记 token 为 inactive
3. **频率控制** ✅ — PushPolicyCompiler 实现 daily_cap=2 + 静默时段 + 个性化策略
4. **反馈闭环** ✅ — PushFeedbackService 追踪 opened/clicked/dismissed/ignored 操作，推断偏好更新（receptivity, curiosity_frequency）
5. **推送策略个性化** ✅ — 5 个策略基于 pressure_tolerance, curiosity_frequency, memory_urgency_threshold 等维度个性化

---

## 数据流图

```
触发源
  │
  ├── [事件驱动] ✅ 工作正常
  │   ├── BehaviorPatternService → nudge.triggered 事件
  │   ├── NudgeService.handle_nudge_triggered()
  │   │   ├── 创建 Notification 记录 ✅
  │   │   └── push_sender_service.send_push() ⚠️ 无重试 (P1-1)
  │   └── → FCM / JPush → 用户设备 ✅
  │
  ├── [主动策略] ❌ 完全不工作 (P0-1)
  │   ├── push_service.process_all_users()
  │   │   ├── MemoryStrategy → 低掌握度节点提醒
  │   │   ├── SprintStrategy → 截止日期提醒
  │   │   ├── InactivityStrategy → 不活跃用户唤醒
  │   │   ├── CuriosityStrategy → 好奇心激发
  │   │   └── EmptyCapsuleStrategy → 空认知胶囊提醒
  │   ├── push_policy_compiler.compile() → 频率控制 ✅
  │   └── ❌ 从未被 Celery beat 调度执行
  │
  ├── [日历提醒] ❌ 完全不工作 (P0-2)
  │   ├── calendar_events.reminder_minutes = [15, 30, 60]
  │   ├── # TRACKED(TD-006): 调度提醒通知 (TODO)
  │   ├── CalendarEventCreated 事件 → profile_event_consumer
  │   └── ❌ 仅做缓存失效，不发送通知
  │
  ├── [专注完成] ⚠️ 通知链断裂 (P1-4)
  │   ├── focus.session.completed → EventBus ✅
  │   └── ❌ 无消费者发送完成通知
  │
  ↓ 推送发送层
  │
  ├── PushRouterService → 区域/设备路由
  │   ├── CN → JPush → 极光推送服务器
  │   └── INTL → FCM → Firebase Cloud Messaging
  │
  ├── 无效 Token 清理 ✅ (UNREGISTERED → 标记 inactive)
  ├── 频率控制 ✅ (daily_cap=2, 静默时段)
  └── ⚠️ 无重试机制 (P1-1)
  │
  ↓ 设备接收
  │
  ├── Flutter UnifiedPushService → FCM/JPush SDK
  │   ├── 前台: showSmartPush() → 本地通知
  │   ├── 后台: 系统托盘通知
  │   └── 点击: _onNotificationResponse() → 深链导航
  │
  ├── NotificationCenterProvider
  │   ├── loadNotifications() → API 获取 ✅
  │   ├── handleNewNotification() → WebSocket 实时更新 ✅
  │   └── ⚠️ 无本地持久化 (P1-3)
  │
  └── PushFeedbackService → 推断偏好更新 ✅
      ├── opened/clicked → 正向信号
      └── dismissed/ignored → 负向信号 → 调整推送策略
```

---

## 建议修复方案

| 优先级 | 问题 | 修复方案 | 工作量 |
|--------|------|---------|--------|
| P0-1 | 主动推送策略未调度 | celery_schedule.py 注册 hourly 任务 | 低（~10 行 Python） |
| P0-2 | 日历提醒未实现 | 创建 Celery 任务扫描 reminder_minutes | 中（~60 行 Python） |
| P1-1 | 推送失败无重试 | Celery retry + exponential backoff | 低（~20 行 Python） |
| P1-2 | 通知表无清理 | 添加每日清理归档任务 | 低（~30 行 Python） |
| P1-3 | Flutter 无本地缓存 | Hive 缓存最近 100 条 | 中（~60 行 Dart） |
| P1-4 | 专注完成无通知 | 添加 FocusEventConsumer | 低（~20 行 Python） |
| P1-5 | SystemUpdate 仅 Redis | 添加 DB 持久化备份 | 低（~20 行 Python） |

---

## 复核笔记

> **复核日期**: 2026-04-25 05:00
> **复核轮次**: 第七次唤醒 (Round #53 并行复核)
> **复核方式**: 代码验证

### 复核结果: 0/10 已修

| 原始编号 | 描述 | 状态 | 备注 |
|----------|------|------|------|
| P0-1 | 主动推送策略从未被调度执行 | ❌ 未修 | `celery_schedule.py` 仍仅注册 2 个清理任务（outbox + galaxy），无推送调度。`PushService.process_all_users()` 完整存在于 `push_service.py:30` 但无任何 Celery beat 或 worker 调用入口。5 个策略仍为死代码。`backend/app/workers/` 下无 push worker |
| P0-2 | 日历提醒调度完全未实现 | ❌ 未修 | `calendar.py:146` 仍为 `# TRACKED(TD-006): 调度提醒通知` 注释。`reminder_minutes` jsonb 字段在 schema.sql 中存在但从未被消费。CalendarEventCreated 事件仅触发 EventBus 发布，唯一消费者做缓存失效，不发送通知 |
| P1-1 | 推送发送失败无重试机制 | ❌ 未修 | `nudge_service.py:89-90` 仍为 bare `except Exception as e: logger.error(...)`，无 retry/DLQ/exponential backoff。`push_sender_service.py` 的 `_send_fcm_multicast` 和 `_send_fcm_single` 均无重试逻辑 |
| P1-2 | 通知表无清理任务 | ❌ 未修 | `cleanup_worker.py` 仅含 3 个任务：`cleanup_outbox_events`、`cleanup_galaxy_outbox`、`process_inbox_decay`。`notifications`、`push_histories`、`notification_interactions` 表无任何清理或归档逻辑 |
| P1-3 | Flutter 通知无本地持久化 | ❌ 未修 | `notification_center_provider.dart` 全量内存 Riverpod state，无 Hive/Isar/sqflite 缓存。`notification_center_repository.dart` 仅 API 调用 + demo mode fallback，无本地持久层 |
| P1-4 | 专注模式完成不触发通知 | ⚠️ 部分缓解 | 现有两条事件消费链：(1) `ProfileEventConsumer._handle_focus_session_completed` → `FocusSignalProcessor.process_focus_event` → 更新推断偏好；(2) `AchievementEventConsumer._handle_focus_session_completed` → AchievementEngine 检查。但**两条路径均不创建用户可见通知**。原始发现核心"完成通知"仍未修 |
| P1-5 | SystemUpdateService 仅 Redis 存储 | ❌ 未修 | `system_update_service.py` 仍为纯 Redis lpush/ltrim/expire（200 条上限，7 天 TTL），无 DB 写入 |
| P2-1 | 通知操作按钮硬编码中文 | ❌ 未修 | `notification_service.dart:338-352` 仍为硬编码 `'⚡ 开始'`、`'💤 稍后'`、`'🔕 勿扰'`，未使用 `context.l10n` |
| P2-2 | Device ID hashCode 碰撞风险 | ❌ 未修 | `push_token_manager.dart:54` 仍为 `deviceId = 'sparkle_${identifier.hashCode.toRadixString(16)}'`，32-bit hashCode |
| P2-3 | 日历数据未进入 ContextPack | ❌ 未修（加重） | 原报告称 `context_manager.py:285-290` 有 `_get_calendar_context`，但当前代码中 `context_manager.py` 和 `context_pack.py` **均无任何 calendar 引用**。日历上下文注入路径不仅未迁移，连旧路径也已消失。日历数据目前完全不进入 AI prompt |

### 复核附加发现

1. **P1-4 消费链重复处理风险**: `focus_service.py:107-129` 在 `log_session` 中已直接调用 `AchievementEngine.process_event`，而 `AchievementEventConsumer._handle_focus_session_completed:79` 再次处理同一事件。`focus.session.completed` EventBus 事件触发二次成就检查，可能导致重复计数或重复解锁。

2. **P2-3 加重说明**: Data Utilization Analysis (2026-04-06) 记录的"Calendar (CRUD-only)"定性在当前代码中进一步加重——日历不仅 CRUD-only，连 context_manager 中的旧注入路径也被移除，日历数据对 AI 系统完全不可见。

### 跨轮次因果链更新

| 本轮复核 | 关联 | 说明 |
|----------|------|------|
| P0-2 (日历提醒死代码) | ↔ Round #14 P1-4 (push_token 明文) | 同属 notification/push 子系统基础设施缺失 |
| P2-3 (日历上下文消失) | → Data Utilization Analysis (2026-04-06) | 日历从"CRUD-only"恶化为"完全不可见"，AI prompt 零日历上下文 |
| P1-1 (无重试) | ↔ Round #51 P1-2 (CSP connect-src 宽松) | 推送失败不可恢复 + 潜在数据外泄通道的组合风险 |
| P1-4 (专注完成无通知) | ↔ Stage 22 Baseline Repair | growth loop 中 "Reinforce" 阶段断裂，应在 Stage 22+ 优先修复 |
