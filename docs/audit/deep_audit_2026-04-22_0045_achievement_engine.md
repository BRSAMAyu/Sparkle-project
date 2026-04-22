# 深度审计：Achievement Engine 事件处理与奖励发放链路

> 日期：2026-04-22 00:45
> 范围：AchievementEventConsumer 消费 → AchievementEngine 条件评估 → 解锁判定 → Photon/Title/Skin 奖励发放 → Streak 更新 → DB 持久化

## 审计发现

### P0 — 阻断性问题（3 项）

#### P0-1: 成就解锁与奖励发放非原子操作，Photon 可永久丢失
- **位置**: `backend/app/services/achievement_engine.py:778-852` (解锁) + `:1038-1112` (奖励)
- **问题**: 解锁操作（`UserAchievement.unlocked_at = now` + `flush`）与 Photon 发放在同一事务内但无回滚保护
  ```python
  # :829 — 解锁已写入 flush
  await self.db.flush()

  # :832 — 奖励发放，可能失败
  await self._grant_rewards(user_id, locked_achievement)

  # :1074-1091 — Photon 发放失败时，成就已标记解锁
  try:
      await photon_service.grant_photons(...)
  except Exception as e:
      # 仅排队重试，不回滚解锁状态
      self._enqueue_after_commit(lambda: self._schedule_photon_reward_retry(...))
  ```
- **影响**: 成就已显示为"已解锁"但 Photon 奖励永久丢失；重试耗尽后无恢复机制（:1023-1036）
- **修复**: (1) 奖励发放失败时回滚解锁状态（或使用 SAVEPOINT）(2) 添加补偿表记录待发奖励

#### P0-2: 进度更新无行锁保护，并发事件可覆盖进度
- **位置**: `backend/app/services/achievement_engine.py:739-776`
- **问题**: `_update_progress()` 无 `with_for_update()` 锁，多个事件同时更新同一成就进度
  ```python
  # :739-776 — 无锁更新
  async def _update_progress(self, user_id, achievement_id, progress, ...):
      # 直接 SET progress = min(progress, 1.0)，无行锁
      user_achievement.progress = min(progress, 1.0)
      await self.db.flush()
  ```
- **对比**: 解锁操作使用了 `with_for_update()`（:789, :799），但进度更新没有
- **影响**: 并发事件（如连续完成多个任务）可能导致进度倒退或丢失
- **修复**: `_update_progress` 添加 `with_for_update()` 行锁

#### P0-3: 缓存计数器非原子递增，并发事件导致计数丢失
- **位置**: `backend/app/services/achievement_engine.py:540-546, 552-558`
- **问题**: NIGHT_OWL_STUDY 和 EARLY_BIRD 使用 get→计算→set 模式
  ```python
  # :540-546
  count = max(await cache_service.get(cache_key) or 0, current) + 1
  await cache_service.set(cache_key, count, ttl=86400 * 30)
  ```
- **影响**: 两个事件同时读取 count=5 → 都计算 6 → 都写入 6 → 实际应为 7；并发下计数持续偏低
- **修复**: 使用 Redis `INCR` 原子递增

---

### P1 — 重要问题（5 项）

#### P1-1: ErrorCreated 事件不触发成就评估，错题成就链断裂
- **位置**: `backend/app/services/achievement_event_consumer.py:53-66`
- **问题**: AchievementEventConsumer 仅处理 6 种事件（task.completed, galaxy.node.updated, focus.session.completed 等），不处理 ErrorCreated
- **影响**: 错题相关成就（如"从错误中学习"类成就）无法被触发；用户无法通过错题获取成就
- **修复**: 添加 `_handle_error_created` handler → 映射到新的 trigger_code

#### P1-2: Contract 完成/失败不发布事件，成就与契约断裂
- **位置**: `backend/app/services/achievement_engine.py:2088-2118`
- **问题**: Contract 完成在内存中处理，不发布 `CONTRACT_COMPLETED`/`CONTRACT_FAILED` 事件到 Event Bus
- **影响**: ContractEvent 定义了（:78-79）但从未被 AchievementEventConsumer 消费；契约成就链路断裂
- **修复**: Contract 完成时发布事件到 Event Bus

#### P1-3: Streak 统计并发更新无锁，数据可损坏
- **位置**: `backend/app/services/achievement_engine.py:1258-1361`
  ```python
  # :1267 — 无锁递增
  stats.current_streak += 1
  ```
- **问题**: 与 P0-2 类似，streak 更新无行锁保护
- **影响**: 连续签到天数可能被并发事件覆盖为错误值
- **修复**: 使用 SQL `UPDATE ... SET current_streak = current_streak + 1` 或添加行锁

#### P1-4: N+1 查询在先决条件检查和统计聚合中
- **位置**: `achievement_engine.py:413-415` (先决条件) + `:1799-1804` (统计)
  ```python
  # :413-415 — 每个先决条件一次查询
  for prereq_id in achievement.prerequisites:
      if not await self._is_unlocked(user_id, prereq_id):  # N+1

  # :1799-1804 — 每个解锁成就一次查询
  for ua in unlocked:
      achievement = await self._get_achievement(ua.achievement_id)  # N+1
  ```
- **影响**: 用户有 10 个先决条件 + 50 个解锁成就时，单次评估产生 60 次 DB 查询
- **修复**: 批量查询使用 `IN` 子句；虽有缓存（300s TTL）但首次仍全量查询

#### P1-5: user_streak_stats/user_streak_days/spark_contracts 缺失外键约束
- **位置**: `backend/gateway/internal/db/schema.sql:4438, 4419, 3581`
- **问题**: 这三张表的 `user_id` 列无 `REFERENCES users(id)` 外键约束
- **影响**: 删除用户后孤立记录残留；数据完整性无法在 DB 层保障
- **修复**: 添加 FK 约束 + 迁移脚本

---

### P2 — 改进建议（4 项）

#### P2-1: 6 种事件类型定义但从不触发任何成就
- **位置**: `achievement_engine.py:83,85,80,91,90,81`
- **问题**: `SPRINT_STARTED`, `SPRINT_ABANDONED`, `MUTUAL_STUDY`, `PROGRESS_MILESTONE`, `ACHIEVEMENT_COMBO`, `HIDDEN_TRIGGER` 定义了但 `_get_relevant_achievements()` 无匹配 trigger_code
- **修复**: 实现对应 trigger_code 映射或移除死定义

#### P2-2: user_achievements_unlocked_at 重复索引
- **位置**: `schema.sql:7834` + `:10669`
- **问题**: 同一字段有两个相同索引（idx_ 和 ix_ 前缀不同）
- **修复**: 移除重复索引

#### P2-3: 缺失复合索引（equipped skin/title 查询）
- **位置**: `user_galaxy_skins` 和 `user_titles` 表
- **问题**: 查询"当前装备的皮肤/称号"需要 `(user_id, is_equipped)` 索引
- **修复**: 添加复合索引

#### P2-4: study_buddies 表无 SQLAlchemy 模型
- **位置**: `schema.sql:3653` 有表定义，Python 无对应模型
- **问题**: Go 侧可通过 sqlc 操作该表，Python 侧无 ORM 映射
- **修复**: 添加 SQLAlchemy 模型（如需 Python 侧访问）

---

### 合规项（4 项）

1. **行级锁保护解锁** ✅ — `_unlock_achievement` 使用 `with_for_update()` 防止重复解锁（:789, :799）
2. **Photon 去重** ✅ — `PhotonService.grant_photons` 检查 existing transaction 防止重复发放
3. **重试机制** ✅ — Photon 奖励有 Celery 重试 + 本地 3 次降级重试（:899-1036）
4. **Schema 对齐** ✅ — Go schema.sql 与 Python SQLAlchemy 模型字段一一对应

---

## 数据流图

```
Event Bus (sparkle_events)
  │
  ├── task.completed ───────────────┐
  ├── galaxy.node.updated ──────────┤
  ├── focus.session.completed ──────┤
  ├── community.group_task_completed┤
  ├── execution.result_ingested ────┤
  ├── achievement.unlocked ─────────┤
  │                                 ↓
  │        AchievementEventConsumer (6 handlers)
  │                                 │
  │        转换为 AchievementEvent → engine.process_event()
  │                                 │
  ↓                                 ↓
AchievementEngine.process_event()
  │
  ├── _get_relevant_achievements() → 按 trigger_code 匹配
  │   ⚠️ ErrorCreated 无匹配 (P1-1)
  │   ⚠️ CONTRACT_COMPLETED/FIELD 无匹配 (P1-2)
  │
  ├── _check_prerequisites() → N+1 查询 ⚠️ (P1-4)
  ├── _is_unlocked() → 跳过已解锁
  │
  ├── _calculate_progress()
  │   ├── STREAK_DAYS → _get_or_create_streak_stats() ⚠️ 无锁 (P1-3)
  │   ├── NIGHT_OWL → cache get→set ⚠️ 非原子 (P0-3)
  │   ├── TASKS_TOTAL → DB COUNT
  │   └── ...
  │
  ├── _update_progress() ⚠️ 无行锁 (P0-2)
  │
  └── progress >= 1.0 → _unlock_achievement()
      ├── with_for_update() 行锁 ✅
      ├── 检查已解锁 → 跳过
      ├── 设置 unlocked_at, progress=1.0
      ├── flush() ← 事务未提交
      ├── _grant_rewards()
      │   ├── photon_service.grant_photons() ⚠️ 失败不回滚 (P0-1)
      │   ├── title unlock → 无错误处理
      │   └── galaxy skin unlock → 无错误处理
      ├── 更新 first_unlocker, total_unlocked
      ├── flush()
      └── after_commit → _finalize_unlock_side_effects()
          ├── 缓存清理
          └── 广播解锁信号
```

---

## 建议修复方案

| 优先级 | 问题 | 修复方案 | 工作量 |
|--------|------|---------|--------|
| P0-1 | 解锁+奖励非原子 | 奖励失败回滚或 SAVEPOINT + 补偿表 | 中（~80 行 Python） |
| P0-2 | 进度更新无行锁 | `_update_progress` 添加 `with_for_update()` | 低（~5 行 Python） |
| P0-3 | 缓存计数器非原子 | 使用 Redis INCR 替代 get→set | 低（~10 行 Python） |
| P1-1 | ErrorCreated 不触发成就 | 添加 handler + trigger_code 映射 | 低（~20 行 Python） |
| P1-2 | Contract 事件不发布 | Contract 完成时发布到 Event Bus | 低（~15 行 Python） |
| P1-3 | Streak 更新无锁 | SQL 原子递增或行锁 | 低（~10 行 Python） |
| P1-4 | N+1 查询 | 批量 IN 查询 + 预热缓存 | 中（~40 行 Python） |
| P1-5 | 缺失 FK 约束 | 迁移脚本添加 FK | 低（迁移文件） |
