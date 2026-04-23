# 深度审计：Task Service 生命周期链路

> 日期：2026-04-22 03:15
> 范围：Flutter 任务 CRUD/执行 → Go Gateway 路由 → Python task_service 状态机 → 事件发布（task.started/completed/abandoned）→ Plan 联动 → 成就触发 → Galaxy spark → DB schema（8 张核心表）

## 审计发现

### P0 — 阻断性问题（2 项）

#### P0-1: 成就 TASK_COMPLETED 双重处理 — 个人任务成就被 API 端点和事件消费者各触发一次
- **位置**: `backend/app/api/v1/tasks.py:726-733` (API 直接调用) + `backend/app/services/achievement_event_consumer.py:68-80` (事件消费)
- **问题**: `complete_task()` API 端点在调用 `TaskService.complete()` 后（发布 `task.completed` 事件），又直接调用了 `AchievementEngine`：
  ```python
  # tasks.py:726-733 — 第一重：API 层直接调用
  achievement_engine = AchievementEngine(db)
  unlocked = await achievement_engine.process_event(
      user_id=str(current_user.id),
      event_type=AchievementEvent.TASK_COMPLETED,
      task_id=str(task.id),
      actual_minutes=actual_minutes,
      estimated_minutes=task.estimated_minutes,
      difficulty=task.difficulty,
  )
  
  # achievement_event_consumer.py:68-80 — 第二重：事件消费者
  async def _handle_task_completed(self, event: dict):
      if str(event.get("source") or "personal") == "group":
          return  # 跳过 group 任务，但 personal 任务继续处理
      await engine.process_event(
          user_id=str(event["user_id"]),
          event_type=AchievementEvent.TASK_COMPLETED,
          task_id=str(event.get("task_id") or ""),
          actual_minutes=int(float(event.get("actual_minutes") or 0)),
          ...
      )
  ```
- **影响**: 每次个人任务完成后，`TASK_COMPLETED` 成就事件被处理两次。累计任务完成数成就会被双倍计算。用户提前解锁本不该获得的成就。注意：group 任务因事件消费者 line 69 的 `source == "group"` 守卫而不受此影响
- **修复**: 移除 `tasks.py` 中的直接成就调用（lines 720-744），仅保留事件驱动路径。或参照 Focus Mode P0-1 统一修复

#### P0-2: TaskService.complete() 服务层无状态守卫，允许非法状态转换
- **位置**: `backend/app/services/task_service.py:304-401` (complete 方法)
- **问题**: `complete()` 方法直接设置 `db_obj.status = TaskStatus.COMPLETED`，不检查当前状态：
  ```python
  # task_service.py:308 — 无状态检查
  db_obj.status = TaskStatus.COMPLETED
  db_obj.completed_at = _utcnow()
  db_obj.actual_minutes = actual_minutes
  ```
- **对比**: API 端点 `tasks.py:652-660` 有守卫：
  ```python
  if task.status == TaskStatus.COMPLETED:
      return {"success": True, "message": "Task already completed", ...}
  ```
  但服务层自身不做校验。任何内部调用方（admin API、批量任务、未来代码路径）若直接调用 `TaskService.complete()` 而不先检查状态，将导致：
  - ABANDONED → COMPLETED：已放弃任务被完成，违反状态机约束
  - COMPLETED → COMPLETED：重复完成，导致 Plan 进度、Galaxy spark、事件发布全部重复触发
- **影响**: 状态机约束仅在 API 层执行，服务层可被绕过。与 Round 16 Focus Mode P0-2 同构问题
- **修复**: 在 `TaskService.complete()` 开头添加状态检查：
  ```python
  if db_obj.status in (TaskStatus.COMPLETED, TaskStatus.ABANDONED):
      raise ValueError(f"Cannot complete task in {db_obj.status} state")
  ```

---

### P1 — 重要问题（5 项）

#### P1-1: 任务完成响应返回硬编码 mock 火焰/统计数据，误导用户
- **位置**: `backend/app/api/v1/tasks.py:765-773`
  ```python
  # tasks.py:765-773 — 注释明确标注 Mock
  "flame_update": {
      "level_before": 3,       # ← 固定值
      "level_after": 3,        # ← 固定值
      "brightness_change": 5 + feedback.get("flame_bonus", 0)
  },
  "stats_update": {
      "today_completed": 5,    # ← 固定值
      "streak_days": 7         # ← 固定值
  },
  ```
- **影响**: 用户每次完成任务后看到的火焰等级始终为 3、今日完成数始终为 5、连续天数始终为 7。对比 FocusService 返回真实火焰数据（flame_earned, leveled_up, new_level），任务完成的反馈完全不可信
- **修复**: 从 User 模型和统计服务获取真实数据替代 mock 值

#### P1-2: 批量任务确认存在 N+1 查询，每个任务触发独立 start + refresh
- **位置**: `backend/app/services/task_service.py:563-577`
  ```python
  # task_service.py:565-576 — 循环内逐个操作
  for task in tasks:
      started_task = await TaskService.start(db, task)  # ← N 次 DB 操作
      started_task.confirmed_at = current_time
      db.add(started_task)
      confirmed_tasks.append(started_task)
  
  await db.commit()
  for task in confirmed_tasks:
      await db.refresh(task)  # ← N 次 DB 查询
  ```
- **影响**: AI 生成 5 个任务后确认 = 10+ 次 DB 操作（5 次 start + 5 次 refresh）。如果 AI 生成 10+ 任务，延迟显著
- **修复**: 使用批量 UPDATE 语句替代循环，一次性更新所有 PENDING → IN_PROGRESS

#### P1-3: 任务标签 JSONB 使用 `@>` 过滤但无 GIN 索引，大数据集时退化为顺序扫描
- **位置**: `backend/app/models/task.py:137-143` (索引定义) + `backend/app/api/v1/tasks.py:160-169` (查询)
  ```python
  # tasks.py:160-169 — JSONB contains 查询
  for tag in tags:
      tag_conditions.append(Task.tags.op('@>')(f'["{tag}"]'))
  ```
  ```python
  # task.py:137-143 — 定义的索引（无 GIN）
  Index("idx_tasks_user_id", Task.user_id),
  Index("idx_tasks_plan_id", Task.plan_id),
  Index("idx_tasks_status", Task.status),
  # ❌ 无: Index("idx_tasks_tags_gin", Task.tags, postgresql_using="gin")
  ```
- **影响**: 当用户任务数增长到数百条时，按标签过滤变慢。`@>` 无 GIN 索引时做全表 JSONB 逐行解析
- **修复**: `CREATE INDEX idx_tasks_tags_gin ON tasks USING gin (tags);`

#### P1-4: Galaxy spark 同步调用 + 事件消费者可能双重处理
- **位置**: `backend/app/services/task_service.py:346-360` (直接 spark) + `backend/app/services/galaxy_event_consumer.py` (事件消费 task.completed)
  ```python
  # task_service.py:352-358 — 服务层直接 spark
  await galaxy_service.spark_node(
      user_id=db_obj.user_id,
      node_id=db_obj.knowledge_node_id,
      study_minutes=study_minutes,
      task_id=db_obj.id,
      trigger_expansion=True,
  )
  ```
- **问题**: 服务层直接调用 `spark_node()` 增加掌握度，同时 `GalaxyEventConsumer` 也消费 `task.completed` 事件（Round 11 确认），可能导致知识节点掌握度双倍增长
- **修复**: 移除服务层直接 spark 调用，统一走事件驱动路径

#### P1-5: 幂等键仅作透传，未实际用于去重
- **位置**: `backend/app/api/v1/tasks.py:628,659`
  ```python
  # tasks.py:628 — 接受幂等键
  x_idempotency_key: str | None = Header(None, alias="X-Idempotency-Key")
  
  # tasks.py:659 — 仅作为 response 字段返回
  "retry_token": x_idempotency_key or "generated-token",
  ```
- **影响**: 虽然有状态守卫（line 652 检查 COMPLETED）防止大部分重复，但幂等键本身未被用于存储/查询去重。如果并发请求同时通过状态检查（race condition），理论上可双重完成
- **修复**: 将幂等键存入 Redis（SETNX），在状态检查前先验证幂等键唯一性

---

### P2 — 改进建议（3 项）

#### P2-1: Flutter 执行状态/信任等级标签硬编码中文，未走国际化
- **位置**: `mobile/lib/features/task/data/models/execution_intent_model.dart` + `next_action.dart`
  - ExecutionMode labels: "人工执行", "AI执行", "混合模式"
  - ExecutionTrustLevel labels: "原始结果", "已校验", "可信"
  - NextActionType displayNames: "快速回顾", "轻度扩展", "练习巩固", "休息", "继续计划"
- **修复**: 迁移到 l10n YAML

#### P2-2: 任务无依赖/DAG 支持，仅平面排序
- **位置**: `backend/app/models/task.py` — 仅有 `order_index` 字段，无 `depends_on`/`blocked_by`
- **影响**: 无法表达"完成任务 B 前必须先完成任务 A"的约束
- **修复**: 添加 `depends_on uuid[]` 字段 + DAG 验证逻辑

#### P2-3: TaskRepository 错误消息硬编码中文
- **位置**: `mobile/lib/features/task/data/repositories/task_repository.dart` — 集中式 `_handleDioError()` 方法
- **修复**: 使用 `context.l10n` 替代硬编码字符串

---

### 合规项（5 项）

1. **API 层状态守卫** ✅ — `tasks.py:652-660` 检查 COMPLETED 状态并短路返回，防止 API 层面的重复完成
2. **完整的事件驱动架构** ✅ — 发布 3 种事件（task.started/completed/abandoned），4+ 个消费者（TaskEventConsumer, AchievementEventConsumer, GalaxyEventConsumer, ProfileEventConsumer）
3. **Plan 双层同步** ✅ — TaskService.complete() 同时调用 PlanService.update_progress() + TaskStateSyncService.on_task_completed() 确保计划进度准确
4. **任务模型前后端对齐** ✅ — Flutter TaskType/TaskStatus 枚举与 Python 完全一致（PENDING/IN_PROGRESS/COMPLETED/ABANDONED）
5. **子任务级联删除** ✅ — `subtasks_parent_task_id_fkey → tasks(id) ON DELETE CASCADE`

---

## 数据流图

```
Flutter 任务操作 (创建/执行/完成/放弃)
  │
  ├── [创建] POST /tasks → Go proxy → Python tasks.py → TaskService.create()
  │   ├── 创建 Task DB 记录 ✅
  │   ├── 可选: 生成 AI Guide (LLM 调用) ✅
  │   ├── 创建日历事件 (due_date) ✅
  │   ├── 调度本地通知 ✅
  │   └── TaskStateSyncService.on_task_created() ✅
  │
  ├── [启动] POST /tasks/:id/start → TaskService.start()
  │   ├── PENDING → IN_PROGRESS ✅
  │   ├── 设置 started_at ✅
  │   └── 发布 task.started 事件 ✅
  │       └── SRL PhaseTracker → FORETHOUGHT ✅
  │
  ├── [完成] POST /tasks/:id/complete → TaskService.complete()
  │   ├── ⚠️ 无状态守卫 (P0-2)
  │   ├── → COMPLETED + completed_at ✅
  │   ├── PlanService.update_progress() ✅
  │   ├── TaskStateSyncService.on_task_completed() ✅
  │   ├── PlanStateService.append_task_summary() ✅
  │   ├── GalaxyService.spark_node() ⚠️ 可能与消费者双重 (P1-4)
  │   ├── 发布 task.completed 事件 ✅
  │   │   ├── TaskEventConsumer
  │   │   │   ├── BehaviorSignalCollector ✅
  │   │   │   ├── MetacognitionService.refresh_snapshot() ✅
  │   │   │   ├── CommunitySignalBridge.handle_group_task_completed() ✅
  │   │   │   ├── AutoFragmentCollector ✅
  │   │   │   └── AdaptiveReplanner.on_task_completed() ✅
  │   │   ├── AchievementEventConsumer
  │   │   │   └── ⚠️ AchievementEngine.process_event(TASK_COMPLETED) (P0-1 第二重)
  │   │   └── GalaxyEventConsumer ⚠️ 可能双重 spark (P1-4)
  │   ├── API 层直接调用:
  │   │   ├── ⚠️ AchievementEngine.process_event(TASK_COMPLETED) (P0-1 第一重)
  │   │   ├── ContractService.update_daily_progress() ✅ (仅此一处)
  │   │   └── NextStepService.suggest_next_actions() ✅
  │   └── 返回: ⚠️ 硬编码 mock 火焰/统计数据 (P1-1)
  │
  ├── [放弃] POST /tasks/:id/abandon → TaskService.abandon()
  │   ├── → ABANDONED + reason ✅
  │   └── 发布 task.abandoned 事件 ✅
  │       └── BehaviorSignalCollector.handle_task_abandoned_event() ✅
  │
  └── [批量确认] POST /tasks/confirm → TaskService.confirm_tasks_by_tool_result()
      └── ⚠️ N+1 查询 (P1-2)
          ├── N × TaskService.start()
          └── N × db.refresh()
  
  ↓ 跨系统消费汇总
  
  AchievementEngine ← ⚠️ 双重处理 (P0-1)
  AdaptiveReplanner ← task.completed 事件 ✅
  GalaxyService ← ⚠️ 可能双重 spark (P1-4)
  BehaviorSignalCollector ← 所有任务事件 ✅
  MetacognitionService ← task.completed ✅
  CommunitySignalBridge ← source=group ✅
  SRLPhaseTracker ← task.started/completed ✅
  PlanStateService ← 同步+异步双层 ✅
```

---

## 建议修复方案

| 优先级 | 问题 | 修复方案 | 工作量 |
|--------|------|---------|--------|
| P0-1 | 成就 TASK_COMPLETED 双重处理 | 移除 tasks.py 直接调用，仅保留事件路径 | 低（删除 ~25 行 Python） |
| P0-2 | 服务层无状态守卫 | complete() 开头添加状态校验 | 低（~5 行 Python） |
| P1-1 | 硬编码 mock 火焰/统计 | 从 User + 统计服务获取真实值 | 中（~40 行 Python） |
| P1-2 | 批量确认 N+1 查询 | 批量 UPDATE + 单次 refresh | 中（~30 行 Python） |
| P1-3 | 标签 JSONB 无 GIN 索引 | 添加 GIN 索引 | 低（1 条 DDL） |
| P1-4 | Galaxy spark 可能双重 | 移除服务层直接 spark，统一走事件 | 低（删除 ~10 行 Python） |
| P1-5 | 幂等键未实际使用 | Redis SETNX 去重 | 中（~20 行 Python） |

---

## 复核笔记

> **复核日期**: 2026-04-25
> **复核轮次**: 第十二次唤醒 (Round #58 并行复核)
> **复核方式**: 代码验证

### 复核结果: 0/10 已修

| 原始编号 | 描述 | 状态 | 备注 |
|----------|------|------|------|
| P0-1 | 成就 TASK_COMPLETED 双重处理 | ❌ 未修 | `tasks.py:634-657` 仍直接调用 `AchievementEngine.process_event(TASK_COMPLETED)`；`achievement_event_consumer.py:57-69` 仍消费 `task.completed` 事件并调用同一方法。双重处理完整保留。行号从原始 726-733 变为 634-657（代码重构导致偏移），逻辑未变 |
| P0-2 | 服务层无状态守卫 | ❌ 未修 | `task_service.py:268` 仍直接 `db_obj.status = TaskStatus.COMPLETED`，无前置状态检查。API 层 `tasks.py:565-567` 的 COMPLETED 短路守卫仍在，但服务层自身不防护 |
| P1-1 | 硬编码 mock 火焰/统计 | ❌ 未修 | `tasks.py:678-686` 仍返回固定值 `level_before: 3, level_after: 3, today_completed: 5, streak_days: 7`，代码注释 `# Mock update data for MVP` 保留 |
| P1-2 | 批量确认 N+1 查询 | ❌ 未修 | `task_service.py:511-522` 仍循环调用 `TaskService.start()` + `db.refresh()`，结构未变 |
| P1-3 | 标签 JSONB 无 GIN 索引 | ❌ 未修 | `task.py:138-143` 索引定义仍为 user_id/plan_id/status/created_at/due_date/order_index，无 GIN 索引。`tasks.py:137` 仍使用 `@>` 操作符无 GIN 支持 |
| P1-4 | Galaxy spark 可能双重 | ⚠️ 需修正描述 | `task_service.py:305-319` 仍直接调用 `galaxy_service.spark_node()`。但 `GalaxyEventConsumer._handle_task_completed` (line 212-222) 实际调用的是 `GraphEvolutionService.handle_task_completed()`，后者执行 `record_engagement` + `adjust_neighbor_relation_strengths` + `tag_node_signal`，**不调用 spark_node**。原始审计"双重 spark"描述不准确——实际问题是架构违规：spark 仍在服务层同步调用而非事件驱动路径，但 GalaxyEventConsumer 不会重复 spark。修正为"架构违反：spark 同步调用未走事件路径" |
| P1-5 | 幂等键未实际使用 | ❌ 未修 | `tasks.py:541` 仍接受 `X-Idempotency-Key` header；`tasks.py:572` 仍仅用作 `retry_token` 返回值。未做 Redis SETNX 去重 |
| P2-1 | Flutter 标签硬编码中文 | ❌ 未修 | `execution_intent_model.dart:200-240` statusLabel/trustLabel 仍全硬编码中文（"待准备"/"原始结果"/等）。`next_action.dart:120-148` displayName/description 仍全硬编码中文（"快速回顾"/"拓展学习"/等） |
| P2-2 | 无依赖/DAG 支持 | ❌ 未修 | `task.py` 仍仅有 `order_index` 字段，无 `depends_on`/`blocked_by` |
| P2-3 | TaskRepository 错误消息硬编码中文 | ❌ 未修 | `task_repository.dart:25-52` `_handleDioError` 仍全硬编码中文（"网络超时"/"网络连接失败"/"服务器返回错误"/等） |

### 复核附加发现

| 编号 | 描述 | 状态 | 备注 |
|------|------|------|------|
| AF-1 | P1-4 描述需修正 | ⚠️ | 原始审计称 GalaxyEventConsumer 会"双重 spark"。经代码验证，GalaxyEventConsumer 调用的是 `GraphEvolutionService.handle_task_completed()`（图结构强化），非 `spark_node()`。实际问题是 spark 仍在服务层同步调用（架构违反事件驱动原则），但不会双重 spark。建议将 P1-4 从"双重 spark"修正为"spark 架构违反：同步调用未走事件路径" |
| AF-2 | `_handle_task_completed` 签名偏移 | ℹ️ | `achievement_event_consumer.py:57` 方法签名与原始审计一致，但无实质变化。行号偏移 <5 行 |
| AF-3 | `complete()` 中 galaxy spark 仍在服务层 | ⚠️ | `task_service.py:305-319` 的 `spark_node` 调用位置未变。与事件驱动架构原则矛盾——理想方案应将 spark 移到事件消费者中，但当前双路径不会导致功能 bug |

### 跨轮次因果链更新

- **Round #17 → Round #58**: 本轮 Task Service 生命周期链路 10 项发现中，**0 项已修**，全部保留至后续轮次。
- **P1-4 修正**: 原始审计称 GalaxyEventConsumer 会导致双重 spark，经代码验证不成立。GalaxyEventConsumer 调用 `GraphEvolutionService.handle_task_completed()`（图结构强化），与 `spark_node()` 是不同操作。但仍存在架构问题：spark 同步调用未走事件路径。
- **无新增 P0**: 本阶段未发现新的阻断性问题。
- **未修复项保持原优先级**: P0-1（双重成就）和 P0-2（无状态守卫）仍为最高优先级修复项。
