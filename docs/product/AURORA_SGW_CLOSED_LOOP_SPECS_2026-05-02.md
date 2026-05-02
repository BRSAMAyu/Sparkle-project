# Aurora 自适应闭环 — 完整实现规格书

**日期**: 2026-05-02
**核心思路**: 复用已有 SGW 脚手架（ScaffoldingFSM + CapabilityTracker + BehavioralOutcome），把 Dual-Core Router 接入因果链，不新建平行系统。

---

## 现状：两个独立运行的闭环

```
闭环 A: SGW 脚手架（已完整运行）
  trigger → IntentGenerator → intervention → BehavioralOutcome → apply_feedback → CapabilityTracker → support_level 调整
  数据库: scaffolding_states + passive_signals + behavioral_outcomes + intervention_requests

闭环 B: Dual-Core Router（单向运行）
  UserStateV1 → DualCoreRouter → routing_mode → cognitive_adjustments → LLM prompt → 用户响应 → ???
  数据库: 无 outcome 记录，路由决策和用户结果之间没有因果链
```

**目标**: 把闭环 B 的输出接入闭环 A 的因果链，形成统一闭环。

---

## 完整闭环设计

```
                    ┌─────────────────────────────────────────────┐
                    │              统一因果链                       │
                    │                                             │
用户消息 → orchestrator → routing_engine → DualCoreRouter        │
                    │                    ↓                        │
                    │           routing_decision                  │
                    │                    ↓                        │
                    │     PassiveSignal(signal_type=              │
                    │       "routing_decision")  ←── 写入点 ①    │
                    │                    ↓                        │
                    │           cognitive_adjustments             │
                    │                    ↓                        │
                    │           LLM prompt + 响应                 │
                    │                    ↓                        │
                    │           用户行为（完成任务/校正/流失）       │
                    │                    ↓                        │
                    │     BehavioralOutcome(outcome_type=         │
                    │       "routing_effectiveness")  ←── 写入点② │
                    │                    ↓                        │
                    │  ScaffoldingFSM.apply_feedback()             │
                    │                    ↓                        │
                    │  CapabilityTracker.update(success=...)       │
                    │                    ↓                        │
                    │  capability_level / support_level 变化       │
                    │                    ↓                        │
                    │  context_builder 读取 scaffolding_snapshot  │
                    │                    ↓                        │
                    │  routing_engine 注入 DualCoreRoutingInput   │
                    │       ←── 回路 ③，影响下一次路由决策          │
                    └─────────────────────────────────────────────┘
```

---

## 写入点 ①: 路由决策写入 PassiveSignal

### 当前状态
路由决策在 `routing_engine.py` 的 `build_routing_input()` 中完成，结果存入 `DualCoreRoutingInput` dataclass，但没有任何持久化。

### 修改位置
`backend/app/orchestration/routing_engine.py` — `build_routing_input()` 方法内部

### 实现

在 `build_routing_input()` 返回后，orchestrator 调用一个新的异步方法记录路由决策：

```python
# 新文件: backend/app/services/routing_outcome_recorder.py

class RoutingOutcomeRecorder:
    """记录路由决策到 SGW 的 PassiveSignal 表，建立因果链起点。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_routing_decision(
        self,
        *,
        user_id: UUID,
        session_id: str,
        request_id: str,
        routing_mode: str,          # execution_first / cognitive_first / balanced
        triggered_signals: dict[str, float],  # {"emotional_block": 0.8, "procrastination": 0.6}
        cognitive_adjustments_count: int,
        routing_input_summary: dict[str, Any],  # DualCoreRoutingInput 的关键字段快照
    ) -> None:
        # 复用 PassiveSignal 表 — signal_type 标记为 "routing_decision"
        signal = PassiveSignal(
            user_id=user_id,
            signal_type="routing_decision",
            context={
                "session_id": session_id,
                "request_id": request_id,
                "routing_mode": routing_mode,
                "triggered_signals": triggered_signals,
                "cognitive_adjustments_count": cognitive_adjustments_count,
                "routing_input_summary": routing_input_summary,
                # 冗余关键字段，便于 SQL 查询
                "dominant_signal": max(triggered_signals, key=triggered_signals.get) if triggered_signals else None,
                "max_signal_score": max(triggered_signals.values()) if triggered_signals else 0.0,
            },
        )
        self.db.add(signal)
        await self.db.flush()
```

### 调用位置
在 `orchestrator.py` 的 `process_stream()` 中，路由决策完成后（routing_engine.build_routing_input 返回后），异步调用：

```python
# orchestrator.py — process_stream 中，路由完成后
routing_input = await self.routing_engine.build_routing_input(...)
routing_decision = self.router.route(routing_input)

# 新增：记录路由决策到 SGW
recorder = RoutingOutcomeRecorder(self.db)
await recorder.record_routing_decision(
    user_id=user_uuid,
    session_id=session_id,
    request_id=request_id,
    routing_mode=routing_decision.mode,
    triggered_signals=routing_decision.signal_scores,  # 需要 router 暴露
    cognitive_adjustments_count=len(routing_decision.cognitive_adjustments),
    routing_input_summary={
        "emotion_hint": str(routing_input.emotion_hint),
        "engagement_streak": routing_input.engagement_state.streak if routing_input.engagement_state else None,
        "recent_corrections_count": len(routing_input.recent_corrections),
        "scaffolding_capability_level": routing_input.scaffolding_snapshot.get("capability_level") if routing_input.scaffolding_snapshot else None,
    },
)
```

### 需要额外暴露的数据
`DualCoreDecision` 需要暴露 `signal_scores: dict[str, float]`，记录每个信号的得分。当前 router 返回的 decision 中有 mode 和 adjustments，但没有原始 signal scores。

修改 `backend/app/orchestration/dual_core_router.py`：
- 在 `DualCoreDecision` dataclass 中添加 `signal_scores: dict[str, float]`
- 在 `_score_all_signals()` 方法中返回完整评分，在 `route()` 方法中赋值给 decision

---

## 写入点 ②: 路由结果写入 BehavioralOutcome

### 当前状态
`BehavioralOutcome` 表已存在，通过 `BehavioralOutcomeTracker.record()` 写入。当前只记录 intervention 的结果（用户是否接受干预），不记录路由决策的下游效果。

### 实现

创建一个 Celery task，在路由决策后 48 小时回填 outcome：

```python
# 新文件: backend/app/services/routing_outcome_evaluator.py

class RoutingOutcomeEvaluator:
    """48h 后评估路由决策的效果，写入 BehavioralOutcome。"""

    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis

    async def evaluate_pending(self, max_age_hours: int = 48) -> int:
        """
        扫描 PassiveSignal(signal_type="routing_decision")
        中尚未有对应 BehavioralOutcome 的记录，评估效果。
        """
        # 1. 找到未评估的路由决策信号
        signals = await self._find_unevaluated_routing_signals(max_age_hours)
        evaluated = 0

        for signal in signals:
            user_id = signal.user_id
            ctx = signal.context or {}
            session_id = ctx.get("session_id", "")
            routing_mode = ctx.get("routing_mode", "")

            # 2. 评估这个路由决策的效果
            outcome = await self._evaluate_routing_effect(
                user_id=user_id,
                session_id=session_id,
                routing_mode=routing_mode,
                signal_created_at=signal.timestamp,
                window_hours=max_age_hours,
            )

            # 3. 写入 BehavioralOutcome
            if outcome is not None:
                tracker = BehavioralOutcomeTracker(self.db)
                await tracker.record(
                    user_id=user_id,
                    intervention_id=signal.id,  # 复用 signal ID 作为 intervention_id
                    outcome_type=f"routing_{routing_mode}",
                    time_to_outcome=int((datetime.now(UTC) - signal.timestamp.replace(tzinfo=UTC)).total_seconds()),
                    success=outcome["success"],
                    context={
                        "routing_mode": routing_mode,
                        "dominant_signal": ctx.get("dominant_signal"),
                        "max_signal_score": ctx.get("max_signal_score"),
                        "task_completion_rate": outcome.get("task_completion_rate"),
                        "corrections_count": outcome.get("corrections_count"),
                        "session_continued": outcome.get("session_continued"),
                    },
                )
                evaluated += 1

        return evaluated

    async def _evaluate_routing_effect(
        self,
        *,
        user_id: UUID,
        session_id: str,
        routing_mode: str,
        signal_created_at: datetime,
        window_hours: int,
    ) -> dict[str, Any] | None:
        """评估路由决策在 window_hours 内的用户行为指标。"""

        window_start = signal_created_at
        window_end = signal_created_at + timedelta(hours=window_hours)

        # 指标 1: 任务完成率（48h 内完成 vs 放弃的任务比例）
        task_completion_rate = await self._get_task_completion_rate(
            user_id, window_start, window_end,
        )

        # 指标 2: 校正次数（48h 内用户校正 Aurora 的次数）
        corrections_count = await self._get_corrections_count(
            user_id, window_start, window_end,
        )

        # 指标 3: 会话延续（48h 内是否回来继续对话）
        session_continued = await self._check_session_continuation(
            user_id, session_id, signal_created_at,
        )

        # 综合判断成功/失败
        success = self._judge_success(
            routing_mode=routing_mode,
            task_completion_rate=task_completion_rate,
            corrections_count=corrections_count,
            session_continued=session_continued,
        )

        return {
            "success": success,
            "task_completion_rate": task_completion_rate,
            "corrections_count": corrections_count,
            "session_continued": session_continued,
        }

    def _judge_success(
        self,
        *,
        routing_mode: str,
        task_completion_rate: float,
        corrections_count: int,
        session_continued: bool,
    ) -> bool:
        """
        判断路由决策是否成功。

        规则：
        - cognitive_first: 用户在 48h 内校正 < 2 次 → 成功（认知干预没有过度）
        - cognitive_first: 任务完成率 > 0.5 → 成功（认知干预后继续执行了）
        - execution_first: 任务完成率 > 0.6 → 成功（执行推进有效）
        - balanced: 任务完成率 > 0.5 且校正 < 2 次 → 成功
        - 任何模式：session_continued=True 且 corrections < 3 → 成功
        """
        if routing_mode == "cognitive_first":
            return corrections_count < 2 and (task_completion_rate > 0.3 or session_continued)
        if routing_mode == "execution_first":
            return task_completion_rate > 0.5 or (session_continued and corrections_count < 2)
        # balanced
        return task_completion_rate > 0.4 or session_continued
```

### Celery task 注册

```python
# 在 backend/app/core/celery_tasks.py 中添加

@celery_app.task(bind=True, max_retries=2, name="app.core.celery_tasks.evaluate_routing_outcomes")
def evaluate_routing_outcomes(self):
    """每日评估 48h 前的路由决策效果。"""
    async def _run():
        async with async_session() as session:
            evaluator = RoutingOutcomeEvaluator(session)
            count = await evaluator.evaluate_pending(max_age_hours=48)
            logger.info(f"Evaluated {count} routing outcomes")
    asyncio.run(_run())
```

### Celery beat 调度

```python
# 在 backend/app/core/celery_app.py 的 beat schedule 中添加
"evaluate-routing-outcomes": {
    "task": "app.core.celery_tasks.evaluate_routing_outcomes",
    "schedule": crontab(hour=4, minute=0),  # 每天凌晨 4 点，在 memory_decay 之后
},
```

---

## 回路 ③: ScaffoldingFSM → CapabilityTracker → Router

### 当前状态
`context_builder.py:152-184` 已经把 scaffolding_snapshot 注入到 user_context_payload 中：

```python
scaffolding_fsm_snapshot = {
    "capability_level": ...,       # CapabilityTracker 的能力水平
    "support_level": ...,         # 自适应后的支持级别
    "current_zone": ...,          # frustration / flow / boredom
    "consecutive_successes": ...,
    "consecutive_failures": ...,
}
```

这个数据已经通过 `cognitive_context["scaffolding_fsm_snapshot"]` 传给了 routing_engine。

但 routing_engine 当前**没有读取** scaffolding_snapshot 来影响路由决策。

### 修改位置
`backend/app/orchestration/routing_engine.py` — `_extract_*` 系列方法 + `build_routing_input()`

### 实现

**Step 1: 提取 scaffolding 数据**

```python
# routing_engine.py — 新增方法

@staticmethod
def _extract_scaffolding_context(user_context_payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(user_context_payload, dict):
        return {}
    # 从 cognitive_context 或顶层读取
    scaffolding = user_context_payload.get("scaffolding_fsm_snapshot")
    if not isinstance(scaffolding, dict):
        cognitive = user_context_payload.get("cognitive_context")
        if isinstance(cognitive, dict):
            scaffolding = cognitive.get("scaffolding_fsm_snapshot")
    return scaffolding if isinstance(scaffolding, dict) else {}
```

**Step 2: 注入 DualCoreRoutingInput**

在 `DualCoreRoutingInput` dataclass 中添加字段（如果还没有）：

```python
@dataclass
class DualCoreRoutingInput:
    # ... 现有字段 ...
    scaffolding_capability_level: float | None = None
    scaffolding_zone: str | None = None          # frustration / flow / boredom
    scaffolding_support_level: float | None = None
```

在 `build_routing_input()` 中赋值：

```python
scaffolding = self._extract_scaffolding_context(user_context_payload)
routing_input.scaffolding_capability_level = float(scaffolding.get("capability_level") or 0)
routing_input.scaffolding_zone = str(scaffolding.get("current_zone") or "flow")
routing_input.scaffolding_support_level = float(scaffolding.get("support_level") or 3)
```

**Step 3: Router 消费 scaffolding 数据**

在 `dual_core_router.py` 的 `_apply_cognitive_adjustments()` 中添加逻辑：

```python
# 基于 scaffolding zone 的路由调整
zone = routing_input.scaffolding_zone or "flow"
capability = routing_input.scaffolding_capability_level or 0.5

if zone == "frustration":
    # 用户处于挫败区：优先考虑认知支持，即使没有强烈信号
    cognitive_adjustments.append("用户近期多次尝试未果，本轮优先降低认知负荷，给出最简单可行的下一步。")
    recommend_strategy("intervention_intensity", "low")
    recommend_strategy("explanation_style", "minimal")

elif zone == "boredom":
    # 用户处于无聊区：可以给更有挑战性的任务
    if goal_clarity_score > 0.6:
        cognitive_adjustments.append("用户近期连续成功，本轮可尝试更有挑战性的内容或更大步幅。")
        recommend_strategy("difficulty_level", 3)

# 基于 capability_level 的微调
if capability < 0.35:
    # 能力评估很低：强制 cognitive_first（覆盖其他信号）
    cognitive_adjustments.append("用户能力评估极低，系统需要先处理认知障碍再推进执行。")
```

---

## 完整因果链数据流图

```
用户发送消息
    │
    ├── orchestrator.process_stream()
    │       │
    │       ├── context_builder.build()
    │       │       │
    │       │       ├── _build_stage39_scaffolding_snapshot()  ← 读取 ScaffoldingFSM 状态
    │       │       │       │
    │       │       │       └── scaffolding_snapshot 写入 user_context_payload
    │       │               (capability_level, support_level, zone)
    │       │
    │       ├── routing_engine.build_routing_input()
    │       │       │
    │       │       ├── _extract_scaffolding_context()  ← 读取 scaffolding_snapshot
    │       │       │       │
    │       │       │       └── 注入 DualCoreRoutingInput
    │       │               (scaffolding_capability_level, scaffolding_zone)
    │       │
    │       └── return DualCoreRoutingInput
    │
    ├── dual_core_router.route(routing_input)
    │       │
    │       ├── 基于 9+ 信号维度 + scaffolding zone → routing_mode
    │       ├── signal_scores 写入 DualCoreDecision
    │       └── cognitive_adjustments + execution_constraints
    │
    ├── routing_outcome_recorder.record_routing_decision()  ← 写入点 ①
    │       │
    │       └── PassiveSignal(signal_type="routing_decision", context={routing_mode, signal_scores, ...})
    │
    ├── LLM 生成响应 → 流式返回给用户
    │
    └── 用户行为（完成任务/校正/流失）

            │
            │  48 小时后
            │
    ┌───────┴───────────────────────────────────────────┐
    │  Celery task: evaluate_routing_outcomes            │
    │       │                                            │
    │       ├── 扫描 PassiveSignal(routing_decision)     │
    │       ├── 查询 48h 内的用户行为指标                  │
    │       │       ├── task_completion_rate              │
    │       │       ├── corrections_count                │
    │       │       └── session_continued                │
    │       ├── 判断 success/failure                     │
    │       └── BehavioralOutcomeTracker.record()  ← 写入点 ② │
    │               │                                    │
    │               ├── BehavioralOutcome 写入           │
    │               └── plan_outcome_service.record_outcome() │
    │                       │                            │
    │                       └── profile_ledger 合成学习   │
    │                               │                    │
    └───────────────────────────────┼────────────────────┘
                                    │
            ┌───────────────────────┘
            │
    ┌───────┴───────────────────────────────────────────┐
    │  下次用户消息到达                                   │
    │       │                                            │
    │       ├── ScaffoldingFSM.get_state()               │
    │       │       └── capability_level 已根据          │
    │       │           BehavioralOutcome 更新            │
    │       │                                            │
    │       ├── context_builder 读取更新后的 snapshot     │
    │       │                                            │
    │       ├── routing_engine 注入新的 capability_level │
    │       │                                            │
    │       └── dual_core_router 基于新的 zone/capability │
    │           做出不同的路由决策  ← 回路 ③              │
    └────────────────────────────────────────────────────┘
```

---

## 涉及文件汇总

| 文件 | 修改类型 | 内容 |
|------|----------|------|
| `backend/app/services/routing_outcome_recorder.py` | **新建** | 路由决策 → PassiveSignal 写入 |
| `backend/app/services/routing_outcome_evaluator.py` | **新建** | 48h 回填 → BehavioralOutcome |
| `backend/app/orchestration/dual_core_router.py` | 修改 | DualCoreDecision 添加 signal_scores；消费 scaffolding zone |
| `backend/app/orchestration/routing_engine.py` | 修改 | _extract_scaffolding_context + 注入 DualCoreRoutingInput |
| `backend/app/orchestration/orchestrator.py` | 修改 | 路由完成后调用 RoutingOutcomeRecorder |
| `backend/app/core/celery_tasks.py` | 修改 | 添加 evaluate_routing_outcomes task |
| `backend/app/core/celery_app.py` | 修改 | beat schedule 添加每日 04:00 调度 |

---

## 实现顺序

```
Step 1: DualCoreDecision 暴露 signal_scores
    - 修改 dual_core_router.py
    - 验证：单元测试确认 signal_scores 字段存在

Step 2: RoutingOutcomeRecorder（写入点 ①）
    - 新建文件
    - 在 orchestrator.py 中调用
    - 验证：路由决策后 PassiveSignal 表有记录

Step 3: routing_engine 注入 scaffolding 数据
    - 修改 routing_engine.py
    - 验证：DualCoreRoutingInput 包含 scaffolding 字段

Step 4: Router 消费 scaffolding zone（回路 ③）
    - 修改 dual_core_router.py
    - 验证：frustration zone 用户路由到 cognitive_first

Step 5: RoutingOutcomeEvaluator（写入点 ②）
    - 新建文件
    - Celery task + beat 注册
    - 验证：48h 后 BehavioralOutcome 表有路由效果记录

Step 6: 端到端验证
    - 创建 acceptance script
    - 模拟：路由决策 → 48h → outcome 评估 → capability_level 变化 → 下次路由不同
```

---

## 安全护栏

1. **写入点 ① 是异步的** — 路由决策记录失败不应阻塞正常对话流程。用 try/except 包裹，失败只 log warning。

2. **写入点 ② 是 Celery 异步的** — 48h 回填不影响在线服务。

3. **_judge_success 规则保守** — 宁可多给 cognitive support 也不要在用户需要帮助时撤掉。cognitive_first 的成功门槛比 execution_first 低。

4. **Governance rule guard** — 新增的 scaffolding zone 路由逻辑需要通过现有 53 条规则检查，不能违反 kill switch 约束。

5. **能力回退保护** — 如果 BehavioralOutcome 评估连续 3 次 failure，capability_level 不会无限制降低（CapabilityTracker 的 EMA 有自然下限）。
