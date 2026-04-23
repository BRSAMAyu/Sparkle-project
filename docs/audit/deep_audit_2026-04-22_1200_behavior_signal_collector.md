# 深度审计 #58 — BehaviorSignalCollector 行为信号聚合器完整链路

> **日期**: 2026-04-22 12:00
> **模块**: BehaviorSignalCollector — EventBus 消费 → 冷却去重 → 认知片段生成 → 模式分析 → 自适应重规划 → 推断偏好更新
> **范围**: `behavior_signal_collector.py`（416 行）+ `task_event_consumer.py`（5 处调用）+ `cognitive_service.py`（create_fragment + analyze_behavior）+ `adaptive_replanner.py`（on_behavior_pattern_detected）+ `profile_write_service.py`（update_inferred_preference）
> **审计员**: GLM-5.1 executor (Session continuation)

---

## 审计范围

BehaviorSignalCollector 是 Sparkle "Sense → Clarify → Adapt" 链路的核心桥梁。它将低级事件（任务完成/放弃/反馈、计划重规划、行为模式更新）聚合为认知片段，驱动自适应重规划和用户画像更新。

### 文件清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `services/behavior_signal_collector.py` | 416 | 行为信号聚合核心 |
| `services/task_event_consumer.py` | ~160 | EventBus 消费者，创建 BSC 实例 |
| `services/cognitive_service.py` | ~3000+ | 认知片段 CRUD + analyze_behavior |
| `orchestration/adaptive_replanner.py` | ~800+ | 自适应重规划触发 |
| `services/profile_write_service.py` | ~400+ | 推断偏好写入 |

**总计**: 5 核心文件，~4800+ 行交互链路

---

## 数据流图

```
EventBus (Redis Streams)
  │
  ├── task.completed ──────────────┐
  ├── task.abandoned ──────────────┤
  ├── task.feedback_submitted ─────┤  TaskEventConsumer
  ├── plan.replanned ──────────────┤  (per-event AsyncSessionLocal)
  ├── behavior.pattern.updated ────┘
      │
      ▼
  BehaviorSignalCollector(db, redis)
      │
      ├── [冷却检查] Redis cooldown key (24h TTL)
      │   └── behavior:auto:cooldown:{user_id}:{signal_key}
      │       └── ⚠️ Redis 不可用时冷却失效，无降级保护 (P0-2)
      │
      ├── [片段生成] CognitiveService.create_fragment()
      │   ├── source_event_id 幂等 ✅ (重复事件返回已有片段)
      │   ├── ⚠️ 5 种片段内容全部硬编码中文 (P1-3)
      │   └── ⚠️ event dict 无校验，UUID(str()) 静默吞错 (P0-1)
      │
      ├── [行为分析] CognitiveService.analyze_behavior()
      │   ├── RAG + LLM 模式识别 ✅
      │   ├── ⚠️ 放弃事件触发双分析 (abandon + too_difficult) (P1-1)
      │   └── ⚠️ 分析失败不阻塞但无重试 (P2-2)
      │
      ├── [重规划触发] AdaptiveReplanner.on_behavior_pattern_detected()
      │   ├── ⚠️ _maybe_emit_pattern_adjustment 无冷却保护 (P0-3)
      │   ├── ⚠️ 每次反馈事件对最多 3 个活跃计划调用 (P0-3)
      │   └── pattern_name=None → 重规划无模式上下文 (P1-4)
      │
      └── [推断偏好] ProfileWriteService.update_inferred_preference()
          ├── 每 5 次信号触发一次 ✅ (INFERRED_AGGREGATION_STEP)
          ├── ⚠️ diff 写入但无审计追踪 (P2-3)
          └── ⚠️ median() 对空列表不报错但返回统计噪音 (P2-4)
```

---

## 审计发现

### P0 — 严重缺陷

#### P0-1: event dict 零校验 — UUID(str()) 静默吞错，攻击者可注入任意 user_id
**文件**: `behavior_signal_collector.py:50-52, 62-63, 90-91, 96-98, 104-106`
**严重性**: P0 — 数据完整性风险

```python
# :50-52 — handle_task_feedback_event
async def handle_task_feedback_event(self, event: dict) -> None:
    user_id = UUID(str(event["user_id"]))  # ← KeyError 如果 user_id 不存在
    task_id = UUID(str(event["task_id"]))   # ← 无格式校验

# :62-63 — handle_task_abandoned_event
user_id = UUID(str(event["user_id"]))
task_id = UUID(str(event["task_id"]))  # ← 同上
```

**问题**:
1. `event["user_id"]` — 如果 key 不存在抛 KeyError，整个 handler 崩溃
2. `UUID(str(...))` — `str()` 不做格式校验。`str("not-a-uuid")` → `"not-a-uuid"` → `UUID("not-a-uuid")` → ValueError 崩溃
3. `event.get("category")` vs `event["user_id"]` — 混合使用 `.get()` 和 `[]`，行为不一致

**上游保护**: `TaskEventConsumer` 在创建 BSC 前已做了 `UUID(event["user_id"])` 校验（task_event_consumer.py:76-77），但这是偶然保护，BSC 自身无防御。

**修复**: BSC 每个入口添加 `try/except (KeyError, ValueError)` 或使用 Pydantic event model 校验。

---

#### P0-2: `_signal_on_cooldown` Redis 不可用时返回 False — 所有冷却失效，24h 信号重复发送
**文件**: `behavior_signal_collector.py:274-278`
**严重性**: P0 — 信号洪水

```python
async def _signal_on_cooldown(self, user_id: UUID, signal_key: str) -> bool:
    if not self.redis:
        return False  # ← Redis 不可用 → 冷却失效 → 每个事件都触发
    raw = await self.redis.get(self._cooldown_key(user_id, signal_key))
    return bool(raw)
```

**问题**: 如果 Redis 暂时不可用（网络抖动、Redis 重启），`self.redis` 为 None 或 `get()` 抛异常（未 catch），则冷却检查完全失效。同一个信号会在 24h 内被重复触发：
- `too_difficult_streak`: 3 次反馈 × N 个事件 = N 个认知片段
- `overrun_streak`: 每次任务完成都触发 overrun 检查 + 模式调整
- `plan_modifications`: 每次计划修改都检查 + 发信号
- `inactive_with_active_plan`: 每个事件都触发不活跃检查

**影响**: Redis 故障期间，行为信号洪水会：
1. 大量创建认知片段（DB 写入压力）
2. 大量调用 `cognitive_service.analyze_behavior()`（LLM 调用成本）
3. 大量调用 `AdaptiveReplanner.on_behavior_pattern_detected()`（计划重规划）

**修复**: (1) Redis get 异常 catch + 保守返回 True（fail-closed） (2) 添加内存级 LRU 冷却缓存作为降级

---

#### P0-3: `_maybe_emit_pattern_adjustment` 无冷却保护 — 每次反馈事件触发最多 3 次重规划
**文件**: `behavior_signal_collector.py:264-272`
**严重性**: P0 — 重规划风暴

```python
async def _maybe_emit_pattern_adjustment(self, user_id: UUID) -> None:
    # ← 无冷却检查！无信号标记！
    states = await self.plan_state_service.get_active_plan_states(user_id, limit=3)
    for state in states:
        replanner = AdaptiveReplanner(self.db, self.redis)
        await replanner.on_behavior_pattern_detected(
            user_id=user_id,
            plan_id=state.plan_id,
            pattern_name=None,  # ← 无模式名称
        )
```

**问题**:
1. **无冷却**: 其他所有 `_maybe_emit_*` 方法都有 `_signal_on_cooldown` 检查，唯独此方法没有
2. **无信号标记**: 调用后不 `_mark_signal_emitted`
3. **每次反馈触发**: `handle_task_feedback_event` → `_maybe_emit_pattern_adjustment`，每次用户反馈任务都触发
4. **最多 3 个计划**: 对每个活跃计划独立调用 `on_behavior_pattern_detected`
5. **pattern_name=None**: 重规划器收到空模式名称，无法区分触因

**计算**: 用户反馈 1 次任务 → 3 次活跃计划 × `on_behavior_pattern_detected()`。如果 AdaptiveReplanner 内部有 LLM 调用，这是 3 次额外的 LLM 调用。

**对比**: `handle_behavior_pattern_event` 对同一调用路径有 `confidence < 0.7` 过滤，而 `_maybe_emit_pattern_adjustment` 无任何前置条件。

**修复**: 添加冷却检查 + 信号标记，至少 24h 内对同一用户只触发一次模式调整。

---

### P1 — 重要问题

#### P1-1: `handle_task_abandoned_event` 可触发双分析 — 同一事件产生 2 次 analyze_behavior 调用
**文件**: `behavior_signal_collector.py:61-88`

```python
async def handle_task_abandoned_event(self, event: dict) -> None:
    # ... 创建认知片段 ...
    await self.cognitive_service.analyze_behavior(user_id, fragment.id)  # ← 第 1 次
    # ... 标记信号 ...

async def handle_task_feedback_event(self, event: dict) -> None:
    if category == TaskFeedbackCategory.TOO_DIFFICULT.value:
        await self._maybe_emit_too_difficult_streak(user_id)  # ← 可能触发第 2 次
    await self._maybe_emit_pattern_adjustment(user_id)  # ← 第 3 次（重规划）

# _maybe_emit_too_difficult_streak:
await self.cognitive_service.analyze_behavior(user_id, fragment.id)  # ← 独立分析
```

**场景**: 如果用户放弃任务 + 反馈太难 → task.abandoned 事件触发 analyze_behavior，然后 task.feedback_submitted 事件再触发 too_difficult_streak → analyze_behavior。两个事件可以短时间内连续到达。

**影响**: LLM 分析成本翻倍，且两次分析可能产生冲突的模式结论。

**修复**: 使用 `source_event_id` 幂等保护（已存在于 create_fragment 但不保护 analyze_behavior 调用）。

---

#### P1-2: 每个事件创建独立 AsyncSessionLocal — DB 连接池压力
**文件**: `task_event_consumer.py:79-80, 129-130, 138-139, 146-147, 154-155`

```python
async def _handle_task_completed(self, event: dict):
    async with AsyncSessionLocal() as db:
        collector = BehaviorSignalCollector(db, cache_service.redis)
        # ... handler 内部又创建多个 service 实例：
        # CognitiveService(db), PlanStateService(db, redis), ProfileWriteService(db, redis)
```

**问题**: 每个事件创建独立 DB session。BehaviorSignalCollector 构造函数又创建 3 个子 service 实例，每个持有同一个 db session。单个事件的处理链路可能执行 5-10 次 DB 查询（fragment 创建、plan_state 查询、task 查询、feedback 查询、preference 更新），全部在同一个 session 中。

**影响**: 高事件吞吐时，DB 连接池可能耗尽。每个事件至少 1 个连接，高峰时 5 个并发事件 = 5 个连接 + 子查询。

**修复**: 考虑批量处理或连接池监控。

---

#### P1-3: 全部 5 种认知片段内容硬编码中文 — i18n 零支持
**文件**: `behavior_signal_collector.py:65, 73, 140-141, 179-180, 209-211, 249-250`

```python
# :65 — 放弃事件
content=f"用户放弃了任务《{title}》，已执行 {time_spent or 0} 分钟。"

# :140-141 — 太难连续
content=f"用户连续3次反馈任务太难：{', '.join(titles)}"

# :179-180 — 超时连续
content=f"最近{len(rows)}次任务实际用时都超过预估50%以上：{', '.join(titles)}"

# :209-211 — 计划频繁修改
content=f"用户在24小时内修改了计划 {plan_id} 共 {count} 次。"

# :249-250 — 不活跃
content="用户有活跃计划但连续3天未完成任何任务。"
```

**影响**: 所有行为信号片段对 LLM 的输入都是中文。如果用户语言为英文，认知片段与用户对话语言不匹配，可能影响 LLM 分析质量。

**修复**: 使用 i18n key + 用户语言偏好渲染片段内容。

---

#### P1-4: `on_behavior_pattern_detected` 调用 pattern_name=None — 重规划缺乏上下文
**文件**: `behavior_signal_collector.py:268-272`

```python
await replanner.on_behavior_pattern_detected(
    user_id=user_id,
    plan_id=state.plan_id,
    pattern_name=None,  # ← 无模式名称
)
```

对比 `handle_behavior_pattern_event`:
```python
# :115-119 — 正确传递 pattern_name
await replanner.on_behavior_pattern_detected(
    user_id=user_id,
    plan_id=state.plan_id,
    pattern_name=str(event.get("pattern_name") or ""),  # ← 有上下文
)
```

**影响**: AdaptiveReplanner 收到 None 作为 pattern_name 时，无法判断重规划的具体触发原因（是执行阻力？情绪问题？低估难度？），降低了重规划的针对性。

**修复**: 根据 `_maybe_emit_too_difficult_streak` 和其他检测方法的信号类型传入对应的 pattern_name。

---

#### P1-5: `_build_task_inferred_updates` median() 对小样本不稳定
**文件**: `behavior_signal_collector.py:374`

```python
if ratios:
    updates["task_difficulty_accuracy"] = round(float(median(ratios)), 3)
```

**问题**: `median()` 对 1-2 个样本极度不稳定。如果用户只有 1 个完成的任务，ratio 就是 median。2 个任务时 median 取平均值。3 个任务时才开始有统计意义。

**修复**: 添加最小样本量要求（如 `if len(ratios) < 3: return`）。

---

### P2 — 改进建议

#### P2-1: `_track_plan_modification` Redis-only，无 DB 持久化 — 计划修改计数在 Redis TTL 后丢失
**文件**: `behavior_signal_collector.py:194-223`

`_track_plan_modification` 使用 Redis ZSet 跟踪 24h 内的计划修改次数，但 ZSet 有 TTL（24h）。如果 Redis 在 TTL 期间重启，计数器归零，信号无法触发。

**修复**: 可接受风险——24h 窗口内的短暂丢失影响有限。

---

#### P2-2: analyze_behavior 调用失败静默忽略 — 无重试、无指标
**文件**: `behavior_signal_collector.py:86, 153, 191, 222, 261`

所有 `analyze_behavior` 调用都无 try/except。如果 cognitive_service 内部抛异常（LLM 超时、RAG 失败），整个 handler 崩溃，被 TaskEventConsumer 的外层 try/except 捕获并仅记录日志。

**修复**: 在每个 analyze_behavior 调用外添加 try/except + Prometheus counter。

---

#### P2-3: `_build_task_inferred_updates` 查询最近 14 天所有完成任务 — 大量任务用户查询慢
**文件**: `behavior_signal_collector.py:316-330`

14 天窗口内对活跃用户可能有 50-100 个任务，加上 feedback 查询（:343-351），单次推断更新执行 2 次 DB 查询 + Python 端统计计算。

**修复**: 考虑使用 SQL 聚合（AVG, MEDIAN）代替全量加载。

---

## 合规项（5 项）

| 检查项 | 状态 | 备注 |
|--------|------|------|
| 幂等保护（source_event_id） | ✅ | create_fragment 有 source_event_id 去重 |
| 冷却机制（24h TTL） | ⚠️ | 5 个信号中 4 个有冷却，`_maybe_emit_pattern_adjustment` 例外 (P0-3) |
| EventBus 消费集成 | ✅ | TaskEventConsumer 正确订阅 5 种事件 |
| DB Session 生命周期 | ✅ | TaskEventConsumer 使用 AsyncSessionLocal context manager |
| 推断偏好写入保护 | ✅ | ProfileWriteService.update_inferred_preference 有 diff 检查（:382-385） |

---

## 统计

| 级别 | 数量 |
|------|------|
| P0 | 3 |
| P1 | 5 |
| P2 | 3 |
| **总计** | **11** |

---

## 修复优先级建议

| 优先级 | 问题 | 修复方案 | 工作量 |
|--------|------|---------|--------|
| P0-3 | pattern_adjustment 无冷却 | 添加冷却检查 + 信号标记 | 低（~10 行） |
| P0-2 | Redis 冷却失效 → 信号洪水 | Redis get 异常 catch + fail-closed | 低（~5 行） |
| P0-1 | event dict 零校验 | 入口添加 Key/ValueError catch | 低（~10 行） |
| P1-1 | 双分析 | analyze_behavior 添加冷却或去重 | 中 |
| P1-4 | pattern_name=None | 传入具体模式名称 | 低（~5 行） |
| P1-5 | 小样本 median 不稳定 | 添加最小样本量 | 低（~3 行） |
| P1-3 | 硬编码中文 | i18n key 替换 | 中 |
| P1-2 | 独立 session 连接压力 | 连接池监控 | 低 |

---

## 跨轮次因果链

| 本轮发现 | 关联轮次 | 关联模式 |
|----------|---------|---------|
| P0-2 (Redis fail-open) | Round #3 P0-5 (EventBus lock fail-open) | Redis 不可用时系统 fail-open 而非 fail-closed |
| P1-3 (硬编码中文) | Rounds #48→#128 (i18n 九连) | 系统性硬编码中文反模式 |
| P0-1 (零校验) | Round #47 P1-2 (FileIds 未验证) | 事件输入零校验 — 防御纵深缺失 |
| P0-3 (无冷却重规划) | Round #20 P0-2 (认知模式不触发 FSM 更新) | 自适应闭环的触发/抑制机制不完整 |

---

## Chris (Session 5) 复核 — 2026-04-23

> 逐项验证 P0 发现对主项目当前代码 (`/Users/brsama/code/GitHub/Sparkle-project/`)。

### P0 验证

| 原始发现 | 文件 | 行号 | 当前状态 | 结论 |
|----------|------|------|---------|------|
| P0-1 event dict 零校验 | `behavior_signal_collector.py` | :50-52, :62-63 `UUID(str(event["user_id"]))` | 代码未变, 无 try/except 包裹 | **CONFIRMED** |
| P0-2 Redis 冷却 fail-open | `behavior_signal_collector.py` | :274-278 `_signal_on_cooldown` | `except Exception: return False` 仍存在 | **CONFIRMED** |
| P0-3 pattern_adjustment 无冷却 | `behavior_signal_collector.py` | :264-272 `_maybe_emit_pattern_adjustment` | 无冷却检查, `pattern_name=None` 仍存在 | **CONFIRMED** |

### P1 抽样验证

| 发现 | 结论 |
|------|------|
| P1-4 pattern_name=None | **CONFIRMED** — `:271` 仍然传入 `pattern_name=None` |

### 总结

报告质量高，行号精确，3个P0全部确认仍存在。代码自审计以来无变化。`behavior_signal_collector.py` 属于可修复范围——P0-3(添加冷却)、P0-2(fail-closed)、P0-1(入口校验) 均为 ~5-10 行低风险修复。
