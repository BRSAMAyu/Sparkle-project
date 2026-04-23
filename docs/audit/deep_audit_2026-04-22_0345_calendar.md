# 深度审计：Calendar Event（日历事件）完整链路

> 日期：2026-04-22 03:45
> 范围：Flutter 日历 CRUD + 本地通知提醒 → Go Gateway proxy 路由 → Python calendar.py API CRUD → EventBus 发布/消费 → SmartScheduleService 智能排程 → ContextManager 日历注入 → InsightSignalRegistry 密度信号 → UserInsightCompiler 统计 → DB schema（calendar_events 表）

## 审计发现

### P0 — 阻断性问题（2 项）

#### P0-1: 服务端日历提醒完全未实现，reminder_minutes 为死数据（与 Round 15 P0-2 同源）
- **位置**: `backend/app/api/v1/calendar.py:146` + `backend/app/services/notification_push_service.py` + `backend/app/celery_schedule.py`
- **问题**: `calendar_events` 表有 `reminder_minutes jsonb` 字段（默认 `[]`），用户可在 Flutter UI 设置提醒时间（如 [0, 15, 60]），Python API 正确写入 DB，但**无任何后端调度逻辑**消费此字段：
  ```python
  # calendar.py:146 — 仅有 TODO 注释
  # TRACKED(TD-006): 调度提醒通知
  # 没有后续代码，后端永远不会发送提醒
  ```
  ```python
  # celery_schedule.py — 仅注册清理任务，无 reminder 调度
  sender.add_periodic_task(86400.0, cleanup_outbox_events.s())
  sender.add_periodic_task(86400.0, cleanup_galaxy_outbox.s())
  # ❌ 无: scan_calendar_reminders 任务
  ```
  ```python
  # notification_push_service.py — 无 calendar reminder 方法
  # ❌ 无: async def send_calendar_reminder(...)
  ```
- **缓解**: Flutter 客户端**确实实现了本地通知提醒**（`calendar_repository.dart:368-395`），通过 `flutter_local_notifications` 插件在设备端调度：
  ```dart
  // calendar_repository.dart:368-395 — 客户端本地提醒
  Future<void> _scheduleReminders(CalendarEventModel event) async {
    for (var i = 0; i < event.reminderMinutes.length; i++) {
      final minutes = event.reminderMinutes[i];
      final reminderTime = event.startTime.subtract(Duration(minutes: minutes));
      await _notificationService.scheduleNotification(
        id: baseId + i,
        title: '日程提醒: ${event.title}',
        scheduledDate: reminderTime,
      );
    }
  }
  ```
- **影响**: 本地通知在 App 进程存活时有效。但：(1) 用户在其他设备登录时不会收到提醒 (2) App 被系统杀死后本地通知可能丢失（取决于平台策略）(3) 服务端无法追踪提醒是否已发送/已读 (4) 无法基于日历提醒触发自适应重规划或推送策略
- **修复**: (1) 创建 Celery 任务，每 5 分钟扫描 `start_time BETWEEN now() AND now() + interval '1 day'` 的事件 (2) 匹配 `reminder_minutes` 数组中即将到期的条目 (3) 通过 PushRouterService 发送 FCM/JPush (4) 标记已发送避免重复

#### P0-2: 日历事件仅被缓存失效消费，全系统无下游联动
- **位置**: `backend/app/services/profile_event_consumer.py:39-50` (订阅) + `:189-197` (处理)
- **问题**: 日历事件发布 3 种事件（`calendar.event.created/updated/deleted`），唯一的消费者 `ProfileEventConsumer` 将其归入 `INSIGHT_SIGNAL_EVENTS` 集合，触发 `_invalidate_profile_context_cache()` — 仅做 Redis 缓存失效：
  ```python
  # profile_event_consumer.py:39-43 — 订阅
  INSIGHT_SIGNAL_EVENTS = {
      "achievement.unlocked",
      "calendar.event.created",    # ← 日历事件
      "calendar.event.updated",    # ← 日历事件
      "calendar.event.deleted",    # ← 日历事件
      ...
  }
  # → 处理路径: _handle_insight_signal_family_updated()
  # → 仅调用: _invalidate_profile_context_cache(user_id)
  ```
- **缺失的下游集成**:
  - ❌ 无 AchievementEngine 联动：日历事件完成/到期不触发任何成就（对比：Task 完成触发 TASK_COMPLETED）
  - ❌ 无 MemoryService 联动：日历事件不创建情景记忆（对比：Focus 会话写入 Episodic Memory）
  - ❌ 无 CognitiveService 联动：日历密度/模式不更新认知画像
  - ❌ 无 AdaptiveReplanner 联动：日历到期事件不触发计划重评估
  - ❌ 无 BehaviorSignalCollector 联动：日历创建/删除行为不进入行为分析
- **已工作的集成**: ContextManager 日历注入（today + 7 天事件 → prompt 渲染）✅, SmartScheduleService 智能排程 ✅, InsightSignalRegistry 密度/窗口信号 ✅, UserInsightCompiler 统计 ✅
- **影响**: 日历是 Sparkle 24 个路由模块之一，但仅作为"数据存储+上下文注入"使用。用户创建的日历事件（如考试、截止日期）不驱动任何主动行为，丧失了"即将到期 → AI 主动提醒/调整计划"的关键价值
- **修复**: (1) 添加 CalendarEventConsumer，订阅 calendar.event.* (2) 日历到期 → 检查关联 task_id/plan_id → 触发 AdaptiveReplanner (3) 日历完成 → AchievementEngine 检查 (4) 日历创建 → EpisodicMemory 写入

---

### P1 — 重要问题（5 项）

#### P1-1: 批量操作不发布 EventBus 事件，下游完全无感知
- **位置**: `backend/app/api/v1/calendar.py:298-387` (batch_operations)
- **问题**: 单条 CRUD（create/update/delete）均发布 EventBus 事件，但批量操作端点 `POST /calendar/batch` 在创建/更新/删除事件后**不发布任何事件**：
  ```python
  # calendar.py:311-379 — 循环处理但无事件发布
  for op in request.operations:
      if op.action == "create":
          db.add(event)
          await db.flush()
          # ❌ 无: event_bus.publish("calendar.event.created", ...)
      elif op.action == "delete":
          event.soft_delete()
          # ❌ 无: event_bus.publish("calendar.event.deleted", ...)
  await db.commit()
  # 批量操作后无事件 → ProfileEventConsumer 不知道日历变更
  ```
- **影响**: 通过批量操作创建的日历事件不会触发缓存失效，ContextManager 可能返回过时的日历数据。如果 AI 生成了多个日历事件（如从计划拆解），这些事件不会反映到后续对话上下文中
- **修复**: 在 batch 操作完成后，为每个成功的操作发布对应事件

#### P1-2: recurrence_rule 存储为字符串但无解析/展开逻辑，后端无法识别重复事件
- **位置**: `backend/app/models/calendar_event.py:55` + `backend/app/api/v1/calendar.py`
- **问题**: `recurrence_rule` 字段（String(512)）存储 RRULE 格式字符串，但后端无任何解析或展开逻辑：
  ```python
  # calendar_event.py:55 — 存储但不解析
  recurrence_rule = Column(String(512), nullable=True)
  
  # calendar.py — 仅存储和返回原始值，无 RRULE → 日期展开
  # 查询时仅查 calendar_events 表中的单条记录
  # ❌ 无: 展开 "FREQ=WEEKLY;BYDAY=MO,WE,FR" → 生成实际日期实例
  ```
- **对比**: Flutter 客户端 `calendar_repository.dart:372-378` 对 recurrence_rule 做了简化的字符串匹配（`daily`/`weekly`/`monthly`）用于本地通知调度，但这与 RRULE 标准不兼容
- **影响**: (1) SmartScheduleService 查询时仅看到原始事件，看不到展开后的重复实例 (2) ContextManager 注入的日历上下文缺少重复事件 (3) 前端需要自行展开重复规则
- **修复**: 添加 `rrule` 库依赖，在查询时展开 recurrence_rule → 生成虚拟事件实例

#### P1-3: calendar.py API 层直接使用 db.get() 无所有权校验优化，批量操作 N+1 查询
- **位置**: `backend/app/api/v1/calendar.py:218,235,271,334,354,399`
- **问题**: 每个端点都使用 `db.get(CalendarEvent, event_id)` 后手动检查 `event.user_id != current_user.id`，批量操作中循环调用：
  ```python
  # calendar.py:334-355 — 批量中逐个获取
  for op in request.operations:
      event = await db.get(CalendarEvent, op.event_id)  # ← N 次 DB 查询
      if not event or event.user_id != current_user.id or event.deleted_at:
          raise ValueError("Event not found")
  ```
- **影响**: 批量创建 10 个事件 = 10 次 `db.get()`。应使用批量查询 + IN 子句
- **修复**: 提取 `_get_user_event()` 辅助方法，批量操作使用 `WHERE id IN (...) AND user_id = ?`

#### P1-4: 日历事件创建/更新无 start_time < end_time 校验
- **位置**: `backend/app/schemas/calendar_event.py:27` + `backend/app/api/v1/calendar.py:111-127`
- **问题**: Pydantic schema 和 API 端点均不校验时间合法性：
  ```python
  # calendar_event.py schema — 无时间约束
  start_time: datetime  # 无 validator
  end_time: datetime    # 无 validator
  ```
  用户可提交 `start_time: 2026-04-22T10:00, end_time: 2026-04-21T10:00`（结束时间早于开始时间），后端直接写入 DB
- **修复**: 添加 Pydantic `@model_validator` 检查 `end_time > start_time`

#### P1-5: restore 端点不发布 EventBus 事件，缓存失效缺失
- **位置**: `backend/app/api/v1/calendar.py:390-412`
- **问题**: 软删除后恢复事件不发布 `calendar.event.updated` 或 `calendar.event.restored` 事件：
  ```python
  # calendar.py:406-408 — 恢复后无事件发布
  event.restore()
  db.add(event)
  await db.commit()
  # ❌ 无: event_bus.publish(...)
  ```
- **影响**: 恢复的事件不会触发缓存失效，ContextManager 和 InsightSignalRegistry 不知道日历变更
- **修复**: 恢复后发布 `calendar.event.updated` 事件

---

### P2 — 改进建议（3 项）

#### P2-1: Flutter 日历提醒标题/正文硬编码中文，未走国际化
- **位置**: `mobile/lib/features/calendar/data/repositories/calendar_repository.dart:388-389`
  ```dart
  title: '日程提醒: ${event.title}',      // ← 硬编码
  body: minutes == 0 ? '现在开始' : '还有 $minutes 分钟开始',  // ← 硬编码
  ```
- **修复**: 迁移到 l10n YAML

#### P2-2: CalendarEventDetail schema 不返回 duration_minutes 属性
- **位置**: `backend/app/models/calendar_event.py:77-83` (模型有 property) vs `backend/app/schemas/calendar_event.py:103` (schema 无字段)
- **影响**: 模型定义了 `duration_minutes` 计算属性，但 API 响应中不包含此字段
- **修复**: 在 CalendarEventDetail schema 中添加 `duration_minutes: int | None = None`

#### P2-3: 日历统计摘要查询未缓存，每次 GET /summary 执行 4 条 COUNT 查询
- **位置**: `backend/app/api/v1/calendar.py:151-206`
- **问题**: 统计摘要端点执行 4 条独立的 COUNT 查询（total/today/upcoming/recurring），无 Redis 缓存
- **修复**: 添加短期 Redis 缓存（TTL 60s），日历事件变更时失效

---

### 合规项（5 项）

1. **CRUD 完整性** ✅ — 创建/读取/更新/删除/批量操作/恢复全部实现，遵循 RESTful 规范，使用 BaseModel 软删除模式
2. **Go Gateway proxy 路由** ✅ — 使用项目标准 `proxyWithHeaders` 模式（9 条路由），与其他 23 个模块架构一致
3. **ContextManager 日历注入** ✅ — `context_manager.py:466-527` 查询 today + 7 天事件，提取 upcoming_deadlines、time_blocks_today、workload_density、exam_urgency，渲染到 prompt（`prompts.py:2674-2709`）
4. **SmartScheduleService 智能排程** ✅ — 考虑已有事件密度、认知模式、用户偏好，推荐最优时间槽
5. **InsightSignalRegistry 信号注册** ✅ — calendar_density、calendar_recurring_windows、calendar_weekend_count、calendar_morning_ratio 4 个信号已注册

---

## 数据流图

```
Flutter 日历操作 (创建/编辑/删除/查看)
  │
  ├── [创建] POST /calendar → Go proxy → Python calendar.py
  │   ├── 创建 CalendarEvent DB 记录 ✅
  │   ├── reminder_minutes 写入 DB ✅
  │   ├── EventBus: calendar.event.created ✅
  │   │   └── ProfileEventConsumer → 缓存失效 ✅
  │   │       ❌ 无下游联动 (P0-2)
  │   ├── # TRACKED(TD-006): 调度提醒通知 ❌ (P0-1)
  │   └── Flutter: _scheduleReminders() → 本地通知 ✅ (仅客户端)
  │
  ├── [更新] PUT /calendar/:id → calendar.py
  │   ├── 更新 DB 记录 ✅
  │   ├── EventBus: calendar.event.updated ✅
  │   │   └── ProfileEventConsumer → 缓存失效 ✅
  │   ├── Flutter: _cancelReminders() + _scheduleReminders() ✅
  │   └── ❌ 无 start_time < end_time 校验 (P1-4)
  │
  ├── [删除] DELETE /calendar/:id → calendar.py
  │   ├── 软删除 (deleted_at) ✅ / 硬删除 ✅
  │   ├── EventBus: calendar.event.deleted ✅
  │   │   └── ProfileEventConsumer → 缓存失效 ✅
  │   └── Flutter: _cancelReminders() ✅
  │
  ├── [恢复] POST /calendar/:id/restore
  │   ├── restore() + commit ✅
  │   └── ❌ 无 EventBus 事件发布 (P1-5)
  │
  ├── [批量] POST /calendar/batch
  │   ├── 循环处理 create/update/delete ✅
  │   ├── ❌ 无 EventBus 事件发布 (P1-1)
  │   └── ⚠️ N+1 db.get() 查询 (P1-3)
  │
  ├── [智能排程] POST /calendar/suggest-time
  │   └── SmartScheduleService.suggest_time_slots() ✅
  │       ├── 查询已有事件密度 ✅
  │       ├── 考虑认知模式 ✅
  │       └── 推荐最优时间槽 ✅
  │
  └── [统计] GET /calendar/summary
      └── 4 条 COUNT 查询 ⚠️ 无缓存 (P2-3)

  ↓ 跨系统消费汇总

  ContextManager ← 日历上下文 (today + 7d) ✅
  Prompts ← _format_calendar_context_lines() ✅
  SmartScheduleService ← 已有事件查询 ✅
  InsightSignalRegistry ← 4 个日历信号 ✅
  UserInsightCompiler ← 日历统计 ✅
  ProfileEventConsumer ← 仅缓存失效 ⚠️ (P0-2)

  AchievementEngine ← ❌ 无日历事件
  MemoryService ← ❌ 无日历情景记忆
  CognitiveService ← ❌ 无日历认知联动
  AdaptiveReplanner ← ❌ 无日历到期触发
  BehaviorSignalCollector ← ❌ 无日历行为分析
```

---

## 建议修复方案

| 优先级 | 问题 | 修复方案 | 工作量 |
|--------|------|---------|--------|
| P0-1 | 服务端提醒未实现 | Celery 任务扫描 reminder_minutes + 推送 | 中（~60 行 Python） |
| P0-2 | 日历事件无下游联动 | 添加 CalendarEventConsumer + 多系统联动 | 高（~100 行 Python） |
| P1-1 | 批量操作无事件发布 | 循环中为每个操作发布事件 | 低（~20 行 Python） |
| P1-2 | RRULE 无解析展开 | 添加 rrule 库 + 展开逻辑 | 中（~80 行 Python） |
| P1-3 | N+1 查询 | 提取辅助方法 + 批量查询 | 低（~30 行 Python） |
| P1-4 | 无时间合法性校验 | Pydantic model_validator | 低（~10 行 Python） |
| P1-5 | restore 无事件 | 添加 event_bus.publish | 低（~5 行 Python） |

---

## 复核笔记

> **复核日期**: 2026-04-25 05:15
> **复核轮次**: 第八次唤醒 (Round #54 并行复核)
> **复核方式**: 代码验证

### 复核结果: 2/10 已修 (P1-4 部分修)

| 原始编号 | 描述 | 状态 | 备注 |
|----------|------|------|------|
| P0-1 | 服务端日历提醒完全未实现 | ❌ 未修 | `celery_schedule.py` 仍仅 2 个 periodic task。`calendar.py:146` 仍为 `# TRACKED(TD-006)`。Flutter 客户端本地通知 `_scheduleReminders()` 仍是唯一提醒路径 |
| P0-2 | 日历事件无下游联动 | ❌ 未修 | `ProfileEventConsumer` 已完全移除 `calendar.event.*` 订阅。不存在 `CalendarEventConsumer`。AchievementEngine、MemoryService、CognitiveService 均无 calendar 引用。**审计声称的 InsightSignalRegistry 4 个信号在当前代码中不存在** |
| P1-1 | 批量操作不发布 EventBus 事件 | ❌ 未修 | `calendar.py:311-381` batch_operations 仍循环中无 event_bus.publish |
| P1-2 | recurrence_rule 无解析/展开 | ❌ 未修 | `calendar_event.py:55` 仍为 String(512) 直接存储，Flutter 仍做简化字符串匹配 |
| P1-3 | 批量操作 N+1 查询 | ❌ 未修 | `calendar.py:334,354` 仍循环调用 db.get，未用 IN 子句 |
| P1-4 | 无 start_time < end_time 校验 | ✅ 部分修 | `CalendarEventCreate` 新增 `@field_validator("end_time")` 检查。但 **`CalendarEventUpdate` 仍无交叉字段校验**，更新操作可设置 end_time 早于 start_time |
| P1-5 | restore 不发布 EventBus 事件 | ❌ 未修 | `calendar.py:406-412` 仍无 event_bus.publish。额外发现:**Go Gateway `proxy_routes.go` 缺少 POST /:id/restore 路由**，该端点对 Gateway 不可达 |
| P2-1 | Flutter 日历提醒硬编码中文 | ❌ 未修 | `calendar_repository.dart:387-388` 仍为硬编码中文 |
| P2-2 | CalendarEventDetail 缺 duration_minutes | ✅ 已修 | `calendar_event.py:110` schema 已包含 `duration_minutes: int` 和 `is_recurring: bool` |
| P2-3 | 统计摘要未缓存 | ❌ 未修 | `calendar.py:151-206` summary 仍 4 条独立 COUNT 查询，无 Redis 缓存 |

### 复核附加发现

**AD-1 (P0 级): ContextManager 日历注入已完全消失 — 加剧**
审计合规项 3 声称 `context_manager.py:466-527` 查询 today+7d 事件并注入 prompt。当前验证:
- `context_manager.py` (411 行): **零** calendar 引用
- `prompts.py` (1876 行): **零** calendar 引用
- `context_pack.py` (33K): **零** calendar 引用
日历数据对 AI **完全不可见**。Round #15 P2-3 中已标记的恶化持续。

**AD-2 (P0 级): ProfileEventConsumer 已移除 calendar.event.* 订阅**
当前 `profile_event_consumer.py` 仅处理 6 种事件类型，无日历事件。日历事件现在零消费者，连缓存失效都无。

**AD-3 (P1 级): Go Gateway 缺 restore 代理路由**
`proxy_routes.go:160-171` 注册了 9 条 calendar 路由但缺少 `POST /:id/restore`。Python 端点存在但不可达。

**AD-4: 审计合规项 3/5 声称有误**
- 合规项 3（ContextManager 日历注入）: 当前不存在
- 合规项 5（InsightSignalRegistry 4 个信号）: 当前不存在

### 跨轮次因果链更新

| 本轮复核 | 关联 | 说明 |
|----------|------|------|
| P0-1 (日历提醒未实现) | Round #15 P0-2 (TD-006) | 同源问题，至今未修 |
| AD-1 (注入消失) | Round #15 P2-3 | 恶化持续: 日历从"CRUD-only"退化为"CRUD-only 且 AI 不可见" |
| AD-2 (订阅移除) | 本轮新发现 | 日历事件现在零消费者 |
| P0-2 (无下游联动) | Data Utilization Analysis | 日历仍是集成度最低的模块 |
