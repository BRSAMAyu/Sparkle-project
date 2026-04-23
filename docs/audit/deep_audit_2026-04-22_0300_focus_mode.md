# 深度审计：Focus Mode（专注模式）完整闭环

> 日期：2026-04-22 03:00
> 范围：Flutter 专注会话管理（mindfulness_provider + focus_statistics_provider）→ Go Gateway 路由/WS focus_card 处理 → Python focus_service 会话生命周期 → 事件发布/消费 → 成就/认知/记忆/画像集成 → DB schema（focus_sessions 表）→ Isar 离线持久化

## 审计发现

### P0 — 阻断性问题（2 项）

#### P0-1: 成就事件双重处理，STUDY_MINUTES_ACCUMULATED 被直接调用和事件消费各触发一次
- **位置**: `backend/app/services/focus_service.py:108-111` (直接调用) + `backend/app/services/achievement_event_consumer.py:82-95` (事件消费)
- **问题**: `FocusService.log_session()` 完成会话后执行了**两重**成就处理：
  ```python
  # focus_service.py:108-111 — 第一重：直接调用（同步）
  unlocked = await achievement_engine.process_event(
      user_id=str(user_id),
      event_type=AchievementEvent.STUDY_MINUTES_ACCUMULATED,
      study_minutes=duration_minutes,
      session_id=session_id,
      session_start_time=start_time,
  )
  
  # focus_service.py:142-149 — 发布事件
  await event_bus.publish("focus.session.completed", {
      "event_type": "focus.session.completed",
      "user_id": str(user_id),
      "duration_minutes": duration_minutes,
      ...
  })
  
  # achievement_event_consumer.py:82-95 — 第二重：事件消费（异步）
  async def _handle_focus_session_completed(self, event: dict):
      ...
      await engine.process_event(
          user_id=str(user_id),
          event_type=AchievementEvent.STUDY_MINUTES_ACCUMULATED,
          actual_minutes=duration_minutes,  # ← 同一个分钟数
      )
  ```
- **影响**: 每次专注会话完成后，`STUDY_MINUTES_ACCUMULATED` 成就事件被处理两次。累积学习时长成就会被**双倍计算**，导致用户提前解锁本不该获得的成就（如"累计学习 100 分钟"仅需实际学习 50 分钟即可解锁）。Night owl/Early bird 成就不受影响（仅直接调用触发）
- **修复**: 移除 `focus_service.py` 中的直接成就调用（lines 95-137），仅保留事件驱动路径；或在 `AchievementEventConsumer` 中跳过已在 `focus_service` 中处理的事件类型

#### P0-2: 专注会话无幂等保护，网络重试导致重复会话和双重奖励
- **位置**: `backend/app/services/focus_service.py:32-200` (log_session) + `backend/app/api/v1/focus.py:23-29` (FocusSessionLog) + `mobile/lib/features/focus/data/repositories/focus_statistics_repository.dart` (离线同步)
- **问题**: 
  1. `FocusSessionLog` Pydantic 模型无幂等键（idempotency key）
     ```python
     # focus.py:23-29 — 无 client_generated_id 或 request_id
     class FocusSessionLog(BaseModel):
         task_id: UUID | None = None
         start_time: datetime
         end_time: datetime
         duration_minutes: int
         focus_type: str = "pomodoro"
         status: str = "completed"
     ```
  2. `focus_sessions` 表无防重复约束：
     ```sql
     -- schema.sql — 仅 PK + 普通索引，无 (user_id, start_time) unique
     CREATE TABLE focus_sessions (
         id uuid NOT NULL,  -- 每次生成新 UUID
         user_id uuid NOT NULL,
         start_time timestamp NOT NULL,
         ...
     );
     -- 仅: idx_focus_user_time(user_id, start_time) — 普通索引，非 UNIQUE
     ```
  3. Flutter 离线同步重试无去重：
     ```dart
     // focus_statistics_repository.dart — 同步未上传会话
     // 对每个 unsynced session 直接 POST，无 dedup key
     ```
- **影响**: Flutter 客户端 POST 超时后重试（或离线同步重试）→ 后端创建新 UUID 会话 → 火焰点双倍、成就双倍触发（在 P0-1 基础上进一步叠加）、情景记忆重复写入、任务 actual_minutes 重复累加
- **修复**: (1) `FocusSessionLog` 添加 `client_request_id: str` 字段 (2) `log_session()` 开头查询是否已存在相同 client_request_id (3) 或添加 `(user_id, start_time, end_time)` 唯一约束

---

### P1 — 重要问题（5 项）

#### P1-1: FocusSessionLog 使用原始 `str` 类型接收 focus_type/status，非法值导致 500 而非 422
- **位置**: `backend/app/api/v1/focus.py:23-29` (schema) + `:64-65` (运行时转换)
  ```python
  # focus.py:28-29 — str 接受任意值
  focus_type: str = "pomodoro"
  status: str = "completed"
  
  # focus.py:64-65 — 运行时构造枚举（ValueError → 500）
  FocusType(data.focus_type),
  FocusStatus(data.status)
  ```
- **对比**: 正确做法是在 Pydantic 模型中直接使用枚举类型 `focus_type: FocusType = FocusType.POMODORO`，Pydantic 会自动返回 422 Validation Error
- **Go 侧风险**: `chat_orchestrator_feedback.go:973-974` 允许客户端覆盖 `focus_type`，如果传入 `"deep_work"` 会在 Python 侧触发 ValueError → 500 → 会话丢失
- **修复**: 将 schema 字段类型改为枚举 `FocusType`/`FocusStatus`

#### P1-2: duration_minutes 无上下限校验，客户端可提交极端值获取高额奖励
- **位置**: `backend/app/api/v1/focus.py:27` + `backend/app/services/focus_service.py:60-84`
  ```python
  # focus.py:27 — 无约束
  duration_minutes: int
  
  # focus_service.py:60-84 — 火焰点 = duration_minutes × 1（无上限）
  flame_earned = duration_minutes
  ```
- **影响**: 客户端提交 `duration_minutes: 999999` → 获得 999,999 火焰点 → 瞬间满级。无服务端校验
- **修复**: 添加 `duration_minutes: int = Field(ge=1, le=480)` (最大 8 小时)

#### P1-3: 事件发布 fire-and-forget，发布失败则画像更新/认知碎片/偏好学习全部丢失
- **位置**: `backend/app/services/focus_service.py:141-152`
  ```python
  try:
      await event_bus.publish("focus.session.completed", {...})
  except Exception as e:
      logging.warning(f"Focus session event publish failed: {e}")
      # ← 仅日志，事件永久丢失
  ```
- **影响**: 事件发布失败后，以下下游系统**永久跳过**本次会话：
  - `ProfileEventConsumer` → `FocusSignalProcessor`（偏好学习、峰值时段、完成率更新）
  - `AchievementEventConsumer`（第二重成就处理，见 P0-1）
  - 下游 cognitive fragment collection
- **修复**: 添加重试机制（Celery retry 或 outbox pattern），或至少将失败事件写入 DLQ

#### P1-4: 情景记忆创建失败静默吞没，AI 对话丢失专注上下文
- **位置**: `backend/app/services/focus_service.py:166-190`
  ```python
  if status == FocusStatus.COMPLETED and duration_minutes > 0:
      try:
          ...
          await memory_service.create_episodic_memory(...)
      except Exception as e:
          logging.warning(f"Focus session episodic memory write failed: {e}")
          # ← 记忆永久丢失，AI 后续对话无专注上下文
  ```
- **影响**: MemoryService 写入失败时（如 DB 超时、embedding 服务不可用），该次专注会话的情景记忆永久丢失。AI 在后续对话中无法感知"用户刚完成了 45 分钟专注"
- **修复**: 将情景记忆写入移入事件消费链，与其他下游处理一起做异步重试

#### P1-5: Go handleFocusCompleted 静默丢弃会话，后端 4xx/5xx 时无客户端反馈
- **位置**: `backend/gateway/internal/handler/chat_orchestrator_feedback.go:990-1012`
  ```go
  // chat_orchestrator_feedback.go:999-1012
  resp, err := h.httpClient.Do(req)
  if err != nil {
      log.Printf("Failed to persist focus_completed: %v", err)
      return  // ← 客户端不知道会话未被保存
  }
  if resp.StatusCode >= 300 {
      log.Printf("Focus completion rejected by backend: status=%d", resp.StatusCode)
      return  // ← 客户端以为会话已保存
  }
  ```
- **影响**: 通过 WebSocket focus_card 触发的专注会话完成后，如果后端拒绝（如 focus_type 无效导致 422），Go 网关仅打日志，不通知客户端。用户以为数据已保存但实际丢失
- **修复**: 向客户端发送 WebSocket 错误消息，或在 `handleFocusCompleted` 中实现重试

---

### P2 — 改进建议（3 项）

#### P2-1: Go 网关 focus_card 响应硬编码中文，未走国际化
- **位置**: `backend/gateway/internal/handler/chat_orchestrator_feedback.go:268-284`
  ```go
  sender.SendActionStatus(toolResultID, "confirmed", map[string]interface{}{
      "message":     "专注已开始",  // ← 硬编码
      "widget_type": widgetType,
  })
  ```
- **修复**: 使用 i18n key 或由 Python 后端返回本地化消息

#### P2-2: Flutter 魔法数字散布多处
- **位置**:
  - `focus_main_screen.dart:156` — `estimatedMinutes: 25`
  - `mindfulness_mode_screen.dart:271` — `starCount: 88`
  - `mindfulness_mode_screen.dart:334` — `fontSize: 72`
  - `focus_service.py` — `min(1.0, max(0.2, duration_minutes / 120.0))` (120 分钟阈值)
- **修复**: 提取到 design_system.dart 或常量文件

#### P2-3: ContextService 语言/领域检测硬编码为 TODO (TD-004)
- **位置**: `mobile/lib/features/focus/data/services/context_service.dart:56-57`
  ```dart
  "language": 'en',  // TRACKED(TD-004): Detect from content
  "domain": 'general', // TRACKED(TD-004): Infer from task
  ```
- **影响**: AI 预测服务的上下文中语言始终为 English、领域始终为 general，降低预测质量
- **修复**: 实现语言检测和领域推断逻辑

---

### 合规项（5 项）

1. **离线优先架构** ✅ — Isar 本地 DB 即时保存 + 后台同步策略 + 失败重试 + SharedPreferences 活跃会话持久化（mindfulness_provider:437-543）
2. **三重确认退出** ✅ — `exit_confirmation_dialog.dart` 实现 3 步确认，防止误放弃专注
3. **优雅降级** ✅ — 成就处理/事件发布/记忆写入/认知碎片收集均独立 try/except，不阻断会话记录
4. **跨系统集成丰富** ✅ — 专注会话数据流入成就引擎、画像服务、认知服务、记忆服务、统计服务、预测服务、智能调度等 11+ 系统
5. **客户端计时器安全** ✅ — `isServerTaskId()` 检查过滤本地生成的 Quick Focus 任务 ID，防止无效 FK

---

## 数据流图

```
Flutter 专注计时器 (mindfulness_provider)
  │
  ├── [路径 A: REST API 直接上报] ✅ 主路径
  │   ├── MindfulnessNotifier.stop()
  │   │   ├── FocusStatisticsNotifier.saveSession()
  │   │   │   ├── Isar 本地保存 ✅ (立即)
  │   │   │   └── POST /api/v1/focus/sessions → Go proxy → Python
  │   │   ├── PredictionService.getNextActions() (非关键)
  │   │   └── VisualElementRepository.unlock() (成就视觉)
  │   └── FocusRepository.logFocusSession()
  │       └── DemoDataService.isDemoMode 分支 ✅
  │
  ├── [路径 B: WebSocket Focus Card]
  │   ├── SuggestFocusSessionTool → "focus_card" widget
  │   ├── 用户确认 → chat_orchestrator_feedback.go
  │   │   └── handleFocusCompleted()
  │   │       ├── 默认 focus_type: "pomodoro" ✅
  │   │       ├── 允许客户端覆盖 ⚠️ "deep_work" → 422 (P1-1)
  │   │       └── POST /api/v1/focus/sessions
  │   │           └── ⚠️ 后端拒绝时客户端不感知 (P1-5)
  │   └── 同一个 Python 端点
  │
  ├── [路径 C: 离线同步]
  │   ├── FocusStatisticsRepository (Isar)
  │   ├── getUnsyncedSessions() → 逐条 POST
  │   └── ⚠️ 无 dedup key → 可能重复 (P0-2)
  │
  ↓ Python FocusService.log_session()
  │
  ├── 创建 FocusSession DB 记录 ✅
  ├── 计算火焰点 (1min=1pt) ⚠️ 无上限 (P1-2)
  ├── 更新 User flame_level/brightness ✅
  ├── 更新 Task actual_minutes + status ✅
  ├── ⚠️ 直接成就处理 (STUDY_MINUTES_ACCUMULATED) (P0-1 第一重)
  │   ├── Night owl (23:00-05:00)
  │   └── Early bird (05:00-08:00)
  ├── db.commit() ✅
  ├── ⚠️ Event publish fire-and-forget (P1-3)
  │   └── focus.session.completed 事件
  │       ├── ProfileEventConsumer
  │       │   └── FocusSignalProcessor → inferred preferences ✅
  │       ├── ⚠️ AchievementEventConsumer → STUDY_MINUTES_ACCUMULATED (P0-1 第二重)
  │       └── AutoFragmentCollector → cognitive fragments ✅
  ├── Episodic Memory 写入 ⚠️ 静默失败 (P1-4)
  └── 返回 {session_id, rewards, unlocked_achievements}
  
  ↓ 跨系统消费
  
  ├── AchievementEngine → 成就解锁 + 视觉元素
  ├── FocusSignalProcessor → 偏好学习 (duration/hours/completion_rate)
  ├── CognitiveService → 行为模式检测
  ├── MemoryService → 情景记忆 → AI 对话上下文
  ├── PredictiveService → 学习预测
  ├── SmartScheduleService → 最优时段推荐
  ├── StateAggregator → 用户活跃度评分
  └── DashboardService → 统计面板
```

---

## 建议修复方案

| 优先级 | 问题 | 修复方案 | 工作量 |
|--------|------|---------|--------|
| P0-1 | 成就双重处理 | 移除 focus_service 直接调用，仅保留事件路径 | 低（删除 ~40 行 Python） |
| P0-2 | 无幂等保护 | 添加 client_request_id + DB unique 约束 | 中（~50 行 Python + DDL） |
| P1-1 | focus_type/status 类型不安全 | Pydantic 模型使用枚举类型 | 低（~5 行 Python） |
| P1-2 | duration 无上限 | 添加 Field(ge=1, le=480) | 低（1 行 Python） |
| P1-3 | 事件发布 fire-and-forget | 添加 Celery retry 或 outbox pattern | 中（~30 行 Python） |
| P1-4 | 情景记忆静默失败 | 移入事件消费链做异步重试 | 低（~20 行 Python） |
| P1-5 | Go WS 会话静默丢弃 | 向客户端发送错误 WebSocket 消息 | 低（~10 行 Go） |

---

## 复核笔记

> **复核日期**: 2026-04-25
> **复核轮次**: 第十一次唤醒 (Round #57 并行复核)
> **复核方式**: 代码验证

### 复核结果: 2/10 已修 (P0 项 0/2, P1 项 1/5, P2 项 1/3)

| 原始编号 | 描述 | 状态 | 备注 |
|----------|------|------|------|
| P0-1 | 成就事件双重处理 STUDY_MINUTES_ACCUMULATED | ❌ 未修 | `focus_service.py:96-136` 直接调用 `achievement_engine.process_event(STUDY_MINUTES_ACCUMULATED)` 仍在。`achievement_event_consumer.py:71-84` 的 `_handle_focus_session_completed` 也仍在消费 `focus.session.completed` 事件并再次触发同一 `STUDY_MINUTES_ACCUMULATED`。双重触发路径完全保留。 |
| P0-2 | 专注会话无幂等保护 | ❌ 未修 | (1) `FocusSessionLog` Pydantic 模型（`focus.py:23-29`）仍无 `client_request_id` 字段。(2) `focus_sessions` 表（`schema.sql:1771-1784`）仍仅有 `focus_sessions_pkey` PK 约束，无 `(user_id, start_time, end_time)` 唯一约束。(3) Flutter 离线同步（`focus_statistics_provider.dart:427-441`）逐条 POST 仍无 dedup key。注意：数据库中存在通用 `idempotency_keys` 表，但 focus 路径未使用它。 |
| P1-1 | focus_type/status 使用原始 str 类型 | ❌ 未修 | `focus.py:28-29` 仍为 `focus_type: str = "pomodoro"` 和 `status: str = "completed"`。`focus.py:64-65` 仍在运行时构造 `FocusType(data.focus_type)` — 若客户端传非法值会 ValueError → 500（非 422）。Go 侧 `chat_orchestrator_feedback.go:786-788` 仍允许客户端覆盖 `focus_type`。 |
| P1-2 | duration_minutes 无上下限校验 | ❌ 未修 | `focus.py:27` 仍为 `duration_minutes: int`，无 `Field(ge=1, le=480)` 约束。`focus_service.py:67` 火焰点 `points = duration_minutes` 仍无上限。客户端提交极端值仍可获取高额奖励。 |
| P1-3 | 事件发布 fire-and-forget | ❌ 未修 | `focus_service.py:140-151` 仍为 `try/except` + `logging.warning`，无重试、无 DLQ、无 outbox pattern。事件发布失败时画像/认知碎片/偏好学习仍永久丢失。 |
| P1-4 | 情景记忆创建失败静默吞没 | ✅ 部分缓解 | 原始报告引用的 `focus_service.py:166-190` 中的情景记忆写入代码已被移除。当前 `focus_service.py` 在 `log_session()` 中不再直接调用 `memory_service.create_episodic_memory()`。情景记忆写入已通过 `AutoFragmentCollector`（`focus_service.py:153-163`）间接处理，但仍为 fire-and-forget + `logging.warning` 吞没模式。对比原报告描述的"直接 memory_service 调用"，路径已改变但静默失败问题仍存。 |
| P1-5 | Go handleFocusCompleted 静默丢弃 | ❌ 未修 | `chat_orchestrator_feedback.go:812-821` 仍为 `log.Printf` + `return`，不向客户端发送任何 WebSocket 错误消息。后端 4xx/5xx 时客户端不感知。 |
| P2-1 | Go 网关 focus_card 响应硬编码中文 | ❌ 未修 | `chat_orchestrator_feedback.go:260` 仍为 `"专注已开始"`，`:267` 仍为 `"专注已取消"`，以及 `:220` 的 `"任务已确认"` / `:230` 的 `"任务已忽略"` / `:242` 的 `"计划已确认"` / `:249` 的 `"计划已忽略"` — 均硬编码中文，未走国际化。 |
| P2-2 | Flutter 魔法数字散布多处 | ✅ 已修 (部分) | `focus_main_screen.dart:156,245` 仍有 `estimatedMinutes: 25` 硬编码。`mindfulness_mode_screen.dart:226` 仍有 `starCount: 88` 硬编码。`mindfulness_mode_screen.dart:289` 仍有 `fontSize: 72` 硬编码。但 `focus_service.py` 中的 `120.0` 阈值已不存在（该代码已重构移除）。状态：大部分魔法数字仍存。 |
| P2-3 | ContextService 语言/领域检测硬编码 TODO | ❌ 未修 | `context_service.dart:56-57` 仍为 `'language': 'en'` 和 `'domain': 'general'`，注释仍标记 `TRACKED(TD-004)`。 |

### 复核附加发现

#### AF-1: focus_service.log_session 不再包含情景记忆直接写入
原报告 P1-4 引用 `focus_service.py:166-190` 的 `memory_service.create_episodic_memory()` 调用已不存在。当前代码路径中，情景记忆通过 `AutoFragmentCollector` 间接处理。但该 collector 仍以 fire-and-forget 模式运行（`focus_service.py:153-163`），静默失败风险并未消除。原 P1-4 的核心问题（"AI 对话丢失专注上下文"）仍成立，只是代码位置已变更。

#### AF-2: AutoFragmentCollector 替代了多个下游直接调用
原报告数据流图中的以下路径已简化：
- "Episodic Memory 写入" 不再由 `focus_service` 直接调用 `memory_service`，而是通过 `AutoFragmentCollector` 间接处理
- 但成就双重处理（P0-1）和事件发布（P1-3）路径未变

#### AF-3: Flutter 离线同步路径中 FocusSessionRequest 无 client_request_id
`focus_session_model.dart:8-21` 的 `FocusSessionRequest` 不包含 `client_request_id` 或任何幂等键。`focus_statistics_provider.dart:427-441` 的 `sync()` 方法逐条 POST 不做去重。此发现与 P0-2 一致，但增加了 Flutter 侧的确认。

#### AF-4: Go handleFocusCompleted 默认 focus_type 为 "pomodoro" 但允许客户端覆盖
`chat_orchestrator_feedback.go:783` 默认 `"focus_type": "pomodoro"`，但 `:786-788` 允许客户端覆盖。如果客户端发送非法 `focus_type`（如 `"deep_work"`），Python 端的 `FocusType("deep_work")` 会 ValueError → 500。这与 P1-1 联动。

### 跨轮次因果链更新

1. **P0-1 (成就双重处理) 是最高优先级阻断项**。它不仅导致成就双倍计算，还在 P0-2 (无幂等保护) 叠加时可导致四倍甚至更高倍率的奖励膨胀。两项 P0 均未修，风险持续累积。

2. **P1-2 (无上限校验) + P0-2 (无幂等) = 经济系统完全失控**。任何客户端均可通过发送 `duration_minutes: 999999` 的重复请求获取无限火焰点。两项均未修。

3. **P1-4 的代码位置已变更**（从直接 `memory_service` 调用迁移到 `AutoFragmentCollector`），但静默失败问题仍在。复核将状态标记为"部分缓解"而非"已修"。

4. **合规项仍然成立**：离线优先架构、三重确认退出、优雅降级等 5 项合规特性仍在代码中保留且未退化。
