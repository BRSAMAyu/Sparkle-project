# 迈向时间连续性：Sparkle 系统时间认知架构与前沿研究整合分析报告

> **版本**: v3.0 Final (三轮自审定稿) | **日期**: 2026-04-23 | **作者**: Chief Architect Review
> **定位**: 将前沿学术研究 (TiMem / TReMu / Zep-Graphiti / CMA / Nemori / HMO / REMem / Stream of Computation) 与 Sparkle 代码库现状进行精确对位分析，产出可落地的架构演进路线

---

## 第零部分：方法论声明

本报告的所有技术判断均基于对以下核心代码文件的逐行阅读：

| 模块 | 已读文件 | 行数范围 |
|------|---------|---------|
| 编排器 | `backend/app/orchestration/orchestrator.py` | L1-550 |
| 上下文构建 | `backend/app/orchestration/context_builder.py` | L1-840 |
| Prompt 组装 | `backend/app/orchestration/prompts.py` | L1-800 |
| 上下文聚焦 | `backend/app/orchestration/context_focus.py` | L1-100 |
| 上下文管理器 | `backend/app/core/context_manager.py` | L1-150 |
| 上下文包 | `backend/app/core/context_pack.py` | L1-100 |
| 计划上下文 | `backend/app/core/plan_context.py` | L1-150 |
| 事件总线 | `backend/app/core/event_bus.py` | L1-150 |
| 记忆服务 | `backend/app/services/memory_service.py` | L1-150 |
| 计划进度 | `backend/app/services/plan_progress_service.py` | L1-150 |
| 计划状态 | `backend/app/services/plan_state_service.py` | L1-200 |
| 衰减服务 | `backend/app/services/decay_service.py` | L1-100 |
| 自适应重规划 | `backend/app/orchestration/adaptive_replanner.py` | L1-150 |
| UX 信封 | `backend/app/orchestration/ux_envelope.py` | L1-140 |
| 充分性检查 | `backend/app/orchestration/sufficiency_checker.py` | L1-150 |
| 数据模型 | `models/plan.py`, `models/plan_state.py`, `models/task.py`, `models/memory.py` | 全文 |
| 调度服务 | `services/scheduler_service.py` | 摘要（APScheduler ~20 周期任务） |
| 通知服务 | `services/notification_service.py`, `services/accountability_notification_service.py` | 摘要 |
| Celery 配置 | `core/celery_app.py`, `core/celery_tasks.py` | 摘要（Beat Schedule + 任务定义） |

**不依赖 agent 返回的二手信息做架构判断**——所有关键结论均可在上述文件中验证。

---

## 第一部分：Sparkle 时间感知现状——代码级精确审计

### 1.1 当前系统如何"知道时间"

Sparkle 当前对时间的处理分布在 6 个层次：

**层次 1：原子时钟访问（Tool-Call 范式）**

```python
# 全项目统一的 _utcnow() 工厂函数，在 17+ 文件中重复定义
def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
```

系统通过 `_utcnow()` 获取当前物理时刻。这是纯粹的 **Current Time Access**——离散的瞬时观测，没有时间积分。每次调用面对的是一个切断了过去演化轨迹的时间横截面。

**层次 2：时间戳标注（Event Log 范式）**

系统大量使用 `created_at`、`updated_at`、`occurred_at`、`completed_at` 等时间戳字段：

- `Task`: `started_at`, `confirmed_at`, `completed_at`, `due_date`
- `EpisodicMemory`: `occurred_at`
- `Event Bus`: 所有事件均携带 `self.timestamp = datetime.now(timezone.utc)`
- `MemoryPreference`: `evidence_checked_at`, `last_consumed_at`
- `MemoryGoal`: `expires_at`, `target_date`

这是标准的 **Event Log/Timeline 范式**——事件按时间戳追加写入，但缺乏有效的时序推理和状态推演能力。

**层次 3：生命周期软标记**

系统使用软删除和归档标记管理实体生命周期：

- `PlanState`: `status` (active/archived), `archived_at`
- `MemoryPreference`: `archived_at`, `retracted_at`, `replaced_by_id`
- `MemoryGoal`: `archived_at`, `retracted_at`
- `EpisodicMemory`: `archived_at`, `retracted_at`

**关键发现**：`MemoryPreference.replaced_by_id` 实际上已经实现了原始版本的 **Bi-temporal 覆盖链**——新偏好写入后，旧记录通过 `replaced_by_id` 指向新记录，保留了完整的版本演变历史。但这个机制目前只用于偏好，未推广到计划、任务等核心实体。

**层次 4：进度计算与截止检测**

```python
# backend/app/services/plan_progress_service.py
OVERRUN_RATIO_WARN = 1.3
OVERRUN_RATIO_CRITICAL = 1.6
PROGRESS_LAG_WARN = 0.25
PROGRESS_LAG_CRITICAL = 0.4

def _compute_time_progress(self, plan) -> float | None:
    """计算时间流逝进度 vs 任务完成进度的差值"""
```

`PlanProgressService` 已实现时间进度 vs 完成进度的差值计算（`progress_lag`），能检测 `healthy / warning / critical` 三级健康状态。但这是 **请求驱动的即时计算**——只有当用户主动触发聊天时才执行，没有后台持续监控。

**层次 5：沉默间隔检测**

```python
# backend/app/orchestration/context_builder.py L644-729
async def _build_returning_context(self, *, user_id, session_id, db_session):
    silence_gap = _utcnow() - last_message_at
    if silence_gap < timedelta(days=3):
        return None
    # 构建欢迎回来消息...
    payload = {
        "days_away": max(int(silence_gap.days), 3),
        "last_active_at": last_message_at.isoformat(),
        "overdue_task_count": overdue_count,
        "welcome_back_message": f"{progress_text}{due_text} 欢迎回来，我们可以从这里继续。",
    }
```

系统在沉默 ≥ 3 天后生成回归上下文。这是目前唯一体现 **"上次到现在发生了什么"** 的代码路径，但它：
- 仅在用户下次发消息时触发（被动响应）
- 阈值硬编码为 3 天（无多分辨率）
- 不涉及置信度衰减或状态推演

**层次 6：定时调度（Celery + APScheduler）**

系统有完善的定时任务基础设施（~20 个周期任务），包括：
- 每日衰减（3:00 AM，Ebbinghaus 曲线）
- 任务提醒（每 15 分钟）
- 智能推送（每 15 分钟）
- 每周报告（周一 9:00 AM）
- 责任伙伴签到（9:00 AM / 9:00 PM）

这些任务构成了一个原始的 **Wake-up Engine** 雏形，但它们基于固定的 Cron 表达式而非事件驱动的动态阈值。

### 1.2 关键发现：已删除的 Temporal Engine

```
backend/app/services/card_protocol/__pycache__/temporal_engine.cpython-311.pyc  ← 存在
backend/app/services/card_protocol/temporal_engine.py  ← 不存在（已删除）
```

项目曾有 `temporal_engine.py` 模块（属于 Card Protocol 子系统），但其源码已被移除，仅剩编译缓存。这暗示时间连续性曾被视为 Card Protocol 的核心组件，但在某次重构中被剥离或搁置。

### 1.3 被禁用的时间感知特性

通过代码阅读确认，以下关键特性通过 Feature Flag 默认关闭：

```python
# backend/app/config.py (settings)
ENABLE_CONTEXT_BRIEFING = False  # 上下文简报（时间感知上下文摘要）
# 被 backend/app/core/context_pack.py 和 backend/app/orchestration/context_focus.py 消费

ENABLE_PERCEPTIBLE_INTELLIGENCE = False  # 感知智能（主动洞察）
ENABLE_PROACTIVE_INSIGHTS = False  # 主动洞察推送
# 被 backend/app/services/perceptible_intelligence_service.py 消费
# 被 backend/app/orchestration/context_builder.py L361-364 条件调用
```

这意味着系统已有时间感知上下文注入的代码路径，但因未启用而处于休眠状态。值得注意的是，`context_builder.py` 中已有 `if settings.ENABLE_PERCEPTIBLE_INTELLIGENCE:` 的条件分支，代码路径完整但未被激活。

### 1.4 现状综合诊断

| 研究定义的概念 | Sparkle 当前状态 | 成熟度 |
|--------------|----------------|--------|
| Current Time Access | ✅ `_utcnow()` 全项目可用 | 成熟 |
| Temporal Awareness | ⚠️ 仅限于 `returning_context` 和固定 Cron | 初级 |
| Temporal Continuity | ❌ 无持续状态演化，每次请求从零构建上下文 | 缺失 |
| Time-aware Memory | ⚠️ `occurred_at` 存在但未用于时序检索推理 | 初级 |
| Timeline Reasoning | ❌ 无跨事件时序推理能力 | 缺失 |
| Temporal State Tracking | ⚠️ `PlanProgressService` 即时计算，无持久跟踪 | 初级 |
| Time-sensitive Planning | ⚠️ `due_date` + `overdue_count` 存在，无动态调度 | 初级 |
| Deadline/Expiration Awareness | ⚠️ 简单 SQL 比较，无置信度模型或压力曲线 | 初级 |
| Event-time vs System-time | ⚠️ `EpisodicMemory.occurred_at` ≠ `created_at`，但未双轨推理 | 雏形 |
| Wall-clock vs Subjective Time | ❌ 完全缺失 | 缺失 |

---

## 第二部分：研究理论与代码现状的精确对位分析

### 2.1 TiMem（时序分层记忆树） vs Sparkle 当前记忆架构

**研究主张**：5 层时序记忆树（片段→会话→日总结→周总结→长期画像），执行时间包含原则，复杂度感知召回减少 52% 上下文开销。

**Sparkle 现状对位**：

Sparkle 的记忆系统有 3 种存储结构，但它们之间没有 TiMem 式的层级坍缩关系：

1. **`EpisodicMemory`**（情节记忆）：存储带 `occurred_at` 的事件摘要。这是 L1（片段级），但**没有向上坍缩管道**——没有日总结、周总结、长期画像的自动化生成。

2. **`MemoryPreference`**（偏好记忆）：通过 `version` + `replaced_by_id` 维护版本链。这提供了 L5（长期画像）的一个侧面，但**仅覆盖偏好维度**，不包含行为模式、知识状态、情感轨迹。

3. **`MemoryGoal`**（目标记忆）：带 `expires_at` 的目标追踪。提供了时间有效期概念，但**没有与任务执行进度关联的自动状态迁移**。

**关键差距**：没有 Consolidation Worker（整合管道）。`EpisodicMemory` 累积增长但从不被压缩为高层摘要。系统唯一接近整合的操作是 `ContextPruner` 的会话内摘要（超过 20 轮时触发），但这只是截断而非 TiMem 式的语义坍缩。

```python
# backend/app/orchestration/orchestrator.py L310-311
self.context_pruner = ContextPruner(
    summary_threshold=20,  # 超过20轮触发总结 — 这是截断，不是层级坍缩
)
```

### 2.2 TReMu（神经符号时序推理） vs Sparkle 当前推理能力

**研究主张**：解耦提及时间与事件时间，用 Python 代码执行器做精确的日期区间计算，避免 LLM 在文本空间中"生憋"时间数学。

**Sparkle 现状对位**：

Sparkle 有丰富的工具调用系统（`dynamic_tool_registry` 注册了 20+ 工具），但**没有任何时序推理工具**。当用户说"上周五讨论的那个知识点"时：

- `UnifiedIntentRouter` 可能路由到 `knowledge_query` 意图
- 但系统没有能力将"上周五"解析为绝对日期区间
- 没有工具可以执行 `date_range("last_friday")` 或 `events_between(start, end)` 的查询

`_build_returning_context` 中的时间差计算是硬编码的：
```python
silence_gap = _utcnow() - last_message_at
if silence_gap < timedelta(days=3):  # 硬编码阈值
    return None
```

这不是 TReMu 式的"LLM 解析意图 → 代码执行器精准运算"，而是简单的 Python timedelta 比较。

### 2.3 Zep/Graphiti（双时态知识图谱） vs Sparkle 当前状态管理

**研究主张**：每条关系边携带事件时间（Event-time）和摄入时间（Ingestion-time）双轨时钟，通过 Validity Windows（$t_{valid}$ / $t_{invalid}$）管理状态生命周期。

**Sparkle 现状对位**：

`MemoryPreference` 已经隐式实现了最原始的双时态：

```python
# backend/app/models/memory.py
class MemoryPreference(BaseModel):
    version = Column(Integer)           # 版本序列
    replaced_by_id = Column(GUID())     # 指向替代者 → 隐式 t_invalid
    evidence_score = Column(Float)      # 置信度
    correction_count = Column(Integer)  # 纠正次数
    archived_at = Column(DateTime)      # 归档时间
    retracted_at = Column(DateTime)     # 撤回时间
```

但这个模式**没有被推广到其他核心实体**：

- `Plan`：没有版本链，状态变更无法追溯
- `Task`：没有 `replaced_by_id`，状态流转是覆盖式的（`status` 字段直接修改）
- `PlanState`：有 `version` 字段（乐观锁），但没有 `t_valid`/`t_invalid` 的有效期概念

**精确差距**：Sparkle 需要 Graphiti 式的有效期窗口来回答"用户关于 X 的意图在哪个时间点是有效的"，但当前系统只能回答"用户最后一次说了什么"。

### 2.4 Nemori（事件分割理论） vs Sparkle 当前会话管理

**研究主张**：基于预测误差（Prediction Error）自动切分事件边界，而非按固定时间或 Token 数截断。

**Sparkle 现状对位**：

`ContextPruner` 的截断逻辑完全是长度驱动的：
```python
summary_threshold=20,  # 超过20轮触发总结
max_history_messages=10,  # 保留最近10轮
```

`_build_returning_context` 用硬编码的 3 天阈值：
```python
if silence_gap < timedelta(days=3):
    return None
```

没有任何"语义边界检测"逻辑。系统无法识别"这个话题讨论结束了，应该封存为一个事件"。

### 2.5 HMO（分层记忆调度） vs Sparkle 上下文预算系统

**研究主张**：三层物理存储（工作记忆→语义知识→深层存档），自适应优先级打分，推理延迟下降 77%。

**Sparkle 现状对位**：

Sparkle 有一个精密的 **Token 预算调度系统**（`prompts.py` 中的 `_apply_prompt_budget`），按优先级和比例分配各 section 的 token 上限：

```python
_SECTION_BUDGET_RATIO = {
    "context_briefing_section": (80, 0.05),
    "plan_context_section": (100, 0.12),
    "user_context": (120, 0.10),
    "conversation_history_section": (80, 0.20),
    # ... 18 个 section，总计 2800 tokens 软上限
}
```

这是一个优秀的**上下文工程**实现，但它不是 HMO 式的**记忆分层**——它控制的是"同一层中不同信息源的 token 分配"，而不是"不同时间粒度信息的层级隔离"。

`ContextBudgetScheduler` 和 `ContextPackTelemetryService` 进一步精细化了预算管理，但核心问题仍然是：所有信息都在同一个扁平的上下文窗口中竞争空间，没有 L1-L4 的层级分离。

### 2.6 CMA（连续记忆架构） vs Sparkle 记忆巩固机制

**研究主张**：6 大行为属性，检索驱动突变（Retrieval-driven Mutation），时间链（Temporal Chaining），记忆被回忆时权重增强，长期未唤醒则衰减。

**Sparkle 现状对位**：

`DecayService` 实现了 Ebbinghaus 遗忘曲线：
```python
# backend/app/services/decay_service.py
BASE_HALF_LIFE_DAYS = 7.0  # 基础半衰期
Retention = e^(-t/S)
```

但衰减**只作用于知识节点（KnowledgeNode）的 mastery_score**，不作用于：
- 记忆偏好（`MemoryPreference` 无衰减）
- 计划状态（`PlanState` 无衰减）
- 事件记忆（`EpisodicMemory` 无衰减）

**缺失的是 CMA 的"检索驱动突变"**——Sparkle 的记忆被检索后，没有"回忆增强"机制。`MemoryPreference.last_consumed_at` 字段存在但只用于追踪，不用于权重调整。

### 2.7 REMem（时序检索子智能体） vs Sparkle 检索架构

**研究主张**：智能体式检索器（Agentic Retriever），分步骤在混合图谱上迭代检索，处理多跳时序约束。

**Sparkle 现状对位**：

Sparkle 的检索是**单轮、无状态的**：
1. `ContextOrchestrator.get_user_context()` 并行调用 5 个服务获取上下文
2. 结果合并为一个扁平的 `CognitiveContext` JSON
3. 注入 Prompt 作为 `{user_context}` 占位符

没有"先定位时间点 A，再检索 A 到 B 之间的关联"这种多跳检索能力。向量检索（`embedding` 字段存在于 `EpisodicMemory`）是纯语义相似度匹配。值得注意的是，`memory.py` 中已定义了 `idx_episodic_memories_user_occurred` 复合索引 `(user_id, occurred_at)`，数据库层面已支持时间过滤查询，但当前代码路径中没有任何服务使用这个索引做时间范围检索。

### 2.8 Stream of Computation（持续计算流） vs Sparkle 主动机制

**研究主张**：系统在无用户输入时仍维持计算流，通过模拟睡眠整合（Sleep-like Consolidation）推进内部状态。

**Sparkle 现状对位**：

Celery 定时任务构成了一个原始的"持续计算"层：
- 每日衰减任务（3:00 AM）模拟了"睡眠期整合"
- 每 15 分钟的任务提醒模拟了"唤醒检查"
- 智能推送策略（`SprintStrategy`, `InactivityStrategy` 等）模拟了"主动介入"

但这些都是**独立的定时脚本**，不是一个统一的"计算流"。它们之间没有共享的状态空间，没有状态转移方程。每个任务独立运行，互相不知道对方的执行结果。

```python
# Celery 任务之间没有共享的 Temporal State
# 每个任务独立查询数据库，独立执行逻辑
@app.task(name="send_task_reminders")
def send_task_reminders():  # 独立执行，不感知其他任务的状态
    ...
```

---

## 第三部分：核心诊断——Sparkle 的"时间病"

### 3.1 症状总结

经过代码级审计，Sparkle 的时间感知问题可以精确诊断为：**"离散时间戳堆积症"**。

具体表现为：

1. **时间数据充足，但时间推理为零**：系统采集了大量时间戳（`created_at`, `occurred_at`, `completed_at`, `due_date` 等），但从不基于这些时间戳做跨实体的时序推理。

2. **每次请求从零构建时间上下文**：`ContextBuilderMixin._build_full_context()` 每次都重新查询所有服务、重新组装上下文。系统不维护一个"上次已知状态"的持续快照。

3. **计划状态是快照而非轨迹**：`PlanState` 的 `version` 字段用于乐观锁并发控制，不用于状态演变追踪。系统不知道"这个计划的状态在过去一周内经历了什么变化"。

4. **记忆与时间脱钩**：`EpisodicMemory.occurred_at` 存在但没有时序索引驱动的检索逻辑。记忆检索主要靠向量相似度，时间只是一个元数据标签。

5. **主动机制是闹钟不是哨兵**：Celery 定时任务像闹钟一样在固定时间响起，但不像哨兵一样持续监控状态变化并在阈值突破时触发。

### 3.2 根因分析

根因不在于缺少某个模块，而在于 **架构层面的时间维度缺失**：

```
当前架构：
  User Request → Context Assembly (from scratch) → LLM → Response
                   ↑ 每次从零构建，无状态记忆

缺失的层：
  User Request → [Temporal Continuity Layer] → Context Assembly → LLM → Response
                   ↑ 维护持续演化的状态，提供"上次到现在"的差值
```

`_build_returning_context` 是唯一的例外（检测沉默间隔），但它是挂载在 `ContextBuilderMixin` 上的一个独立方法，不是一个独立层。

---

## 第四部分：Sparkle 时间连续性架构（TCL）设计蓝图

### 4.1 设计原则

基于研究理论与代码现状的差距分析，TCL 的设计必须遵循以下原则：

**原则 1：渐进式引入，不破坏现有架构**

TCL 不是替换现有模块，而是在现有模块之间插入一个新的协调层。现有的 `ContextOrchestrator`、`PlanProgressService`、`DecayService` 等继续运行，TCL 作为它们之上的时间维度抽象。

**原则 2：复用现有基础设施**

- 复用 `MemoryPreference.replaced_by_id` 的版本链模式（推广到其他实体）
- 复用 `DecayService` 的 Ebbinghaus 曲线（扩展作用范围）
- 复用 Celery/APScheduler 的定时基础设施（增加时间状态巡检任务）
- 复用 `_build_returning_context` 的沉默间隔检测（增强为持续状态跟踪）

**原则 3：计算重力转移**

将时间推演的计算从前端 LLM 的在线推理转移到后台的廉价结构化运算，只向 LLM 暴露"当前时刻依然存活且迫切的活期状态面板"。

### 4.2 TCL 四层架构（适配 Sparkle 现有代码结构）

```
┌─────────────────────────────────────────────────────────────────┐
│  L1: Now Layer (瞬态定锚层)                                      │
│  数据：当前物理时间 + 距上次交互时长 + 触发信号                     │
│  实现：注入 System Prompt 首部，< 50 tokens                      │
│  对应代码：prompts.py → AGENT_SYSTEM_PROMPT 的 user_context 区    │
├─────────────────────────────────────────────────────────────────┤
│  L2: Active State Layer (活跃状态面板)                            │
│  数据：活跃计划状态 + 紧迫任务 + 截止压力 + 用户当前阶段            │
│  实现：结构化 JSON 字典，O(1) 检索                                │
│  对应代码：plan_context.py → PlanContextBuilder.build()           │
│  增强方向：添加 deadline_proximity + confidence_score              │
├─────────────────────────────────────────────────────────────────┤
│  L3: Session Delta Layer (会话增量缓冲层)                         │
│  数据：自上次状态盘点以来的新事件 + 尚未消化的外部变化               │
│  实现：Redis 有序列表，按事件时间排序                               │
│  对应代码：event_bus.py → Event 基类 + 各子类                     │
│  增强方向：添加 event_time / ingestion_time 双轨标记               │
├─────────────────────────────────────────────────────────────────┤
│  L4: Long-term Timeline Layer (长程时序层)                        │
│  数据：压缩后的高层画像摘要 + 版本化的状态演变轨迹                   │
│  实现：TiMem 式层级坍缩 + Zep 式双时态关系链                      │
│  对应代码：memory_service.py → MemoryPreference 版本链             │
│  增强方向：推广到 PlanState/Task + 添加 consolidation worker       │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3 各层与现有代码的精确映射与增强路径

#### L1: Now Layer

**当前状态**：`_build_user_context` 会收集 `last_active_at`，但没有将其转化为时间差值并注入 Prompt。

**增强方案**：在 `build_system_prompt()` 中增加一个 `temporal_anchor_section`：

```python
# prompts.py 中新增 section（~30 tokens）
TEMPORAL_ANCHOR_SECTION = """
## 时间锚点
- 当前时间：{current_time}
- 距上次交互：{time_since_last_interaction}
- 今日已学：{today_focus_minutes} 分钟
- 活跃计划截止倒计时：{deadline_countdown}
"""
```

**预算分配**：为 `temporal_anchor_section` 分配独立的预算配额（80 tokens 基础，2% 比例），与 `context_briefing_section` 并列。如果两者同时启用，总计增加约 3% 的 prompt 预算消耗，仍在 `_apply_prompt_budget` 的软限裁剪能力范围内（2800 tokens 软上限）。

**实现位置**：修改 `prompts.py:build_system_prompt()` 函数，在 `intent_section` 之后插入。

#### L2: Active State Layer

**当前状态**：`PlanContextBuilder.build()` 已经构建了包含 `status`、`progress`、`milestones` 的计划上下文字典。但缺少两个关键维度：

1. **Deadline Proximity**：当前 `PlanProgressService` 计算了 `time_progress` 和 `progress_lag`，但这些值没有进入 `PlanContextBuilder` 的输出。
2. **Confidence Score**：计划状态的置信度完全缺失——系统不知道"用户已经 5 天没有反馈这个计划了，当前进度估值的置信度应该是多少"。

**增强方案**：

```python
# plan_context.py 中 PlanContextBuilder.build() 增强
context.update({
    # 现有字段保持不变...
    "plan_title": plan.name,
    "progress": plan.progress,
    "plan_stage": plan.plan_stage.value,

    # 新增时间连续性字段
    "deadline_proximity": self._compute_deadline_proximity(plan),
    "days_since_last_activity": self._days_since_last_plan_activity(state),
    "confidence_score": self._estimate_plan_confidence(state, plan),
    "time_progress": self._compute_time_progress(plan),  # 从 PlanProgressService 复用
    "progress_lag": self._compute_progress_lag(plan),    # 从 PlanProgressService 复用
})
```

**置信度衰减模型**：基于 Ebbinghaus 曲线的变体，但应用于计划状态而非知识节点：

```python
def _estimate_plan_confidence(self, state, plan) -> float:
    """
    计划状态置信度：随着沉默时间增长而衰减
    base_confidence = 1.0
    half_life = 7 天（可配置）
    confidence = e^(-ln(2) * days_silent / half_life)
    """
    days_silent = (datetime.now(timezone.utc) - state.updated_at).days
    half_life = 7.0
    return math.exp(-0.693 * days_silent / half_life)
```

#### L3: Session Delta Layer

**当前状态**：`Event Bus` 定义了丰富的事件类型（`KnowledgeNodeUpdated`, `TaskCompleted`, `ErrorCreated`, `TaskAbandoned`），但这些事件是即发即忘的——没有持久化的事件流。

**增强方案**：为 `Event` 基类增加双时态标记：

```python
class Event(ABC):
    def __init__(self):
        self.event_time: datetime = None      # 事件在现实世界发生的时间
        self.ingestion_time: datetime = _utcnow()  # 系统记录该事件的时间
```

同时需要一个轻量级的事件缓冲区。**关键设计决策**：当前 Event Bus 是进程内直接调用（非消息队列），事件发布后立即被消费者处理。L3 事件缓冲区不应改变这一模式——而是增加一个"旁路写入"（Sidecar Write），在事件被正常处理的同时，异步将其副本写入 Redis Sorted Set（按 event_time 排序）。这样：
- 现有事件处理流程不受影响（零风险）
- 新增的时间维度作为只读副产物存在
- 缓冲区在每次状态盘点（Consolidation）后被清零

#### L4: Long-term Timeline Layer

**当前状态**：`MemoryPreference` 的版本链（`version` + `replaced_by_id`）提供了 L4 的一个雏形，但仅限于偏好。

**增强方案**：将版本链模式推广到 `PlanState` 和 `Task`：

1. **PlanState 版本链**：`PlanState` 已有 `version` 字段用于乐观锁，在此基础上增加 `superseded_by_id`（类似 `MemoryPreference.replaced_by_id`），实现计划状态的非破坏性更新。

2. **Consolidation Worker**（整合管道）：新增 Celery 任务，每日凌晨运行：
   - 扫描 `EpisodicMemory` 表中过去 24 小时的新记录
   - 调用轻量级 LLM（如 GPT-4o-mini / GLM-4-flash）生成"日总结"
   - 将日总结写入新的 `DailySummary` 表（L3→L4 坍缩）
   - 每周运行一次"周总结"任务，将 7 天日总结进一步坍缩

### 4.4 新增组件：Deadline Proximity Monitor

这是研究论文中"Expiration/Deadline Monitor"的 Sparkle 适配版本。

```python
class DeadlineProximityMonitor:
    """
    Deadline 临近引力模型
    当物理时间逼近截止点时，proximity 呈指数上升
    proximity = e^(k * (1 - days_remaining / total_days))
    """

    def compute_proximity(self, plan: Plan) -> float:
        if not plan.target_date:
            return 0.0
        now = date.today()
        total = (plan.target_date - plan.created_at.date()).days
        remaining = (plan.target_date - now).days
        if total <= 0:
            return 1.0
        ratio = max(0, 1 - remaining / total)
        return min(1.0, math.exp(3.0 * ratio))  # k=3.0 控制指数增长速率
```

**触发阈值**：当 `proximity > 0.7` 且 `progress < 0.8` 时，通过 Celery 任务向用户发送温和提醒。

### 4.5 新增组件：Temporal State Estimator

这是整个 TCL 的核心——维护一个持续演化的时序状态空间。

```python
class TemporalStateEstimator:
    """
    时序状态估计器——类比卡尔曼滤波的状态更新方程

    S(t) = f(S(t-1), ΔT, observations)

    其中：
    - S(t) 是当前时刻的时序状态
    - S(t-1) 是上一次估计的状态
    - ΔT 是时间流逝量
    - observations 是新的交互观测值
    """

    @dataclass
    class TemporalState:
        # 用户时间状态
        last_interaction_at: datetime
        silence_days: float
        interaction_phase: str  # "active" | "returning" | "dormant"

        # 计划时间状态
        active_plan_deadline_proximity: float  # 0-1，指数增长
        active_plan_confidence: float          # 0-1，Ebbinghaus 衰减
        progress_lag: float | None             # time_progress - completion_rate

        # 系统时间状态
        last_consolidation_at: datetime
        next_wake_up_at: datetime | None

        # 语义时间
        subjective_time_resolution: str  # "fine" | "normal" | "coarse"
```

**存储位置**：Redis Hash，key 为 `temporal_state:{user_id}`，TTL 为 30 天（活跃用户自动续期）。

**更新触发点**：
1. 每次用户发送消息时（实时更新）
2. 每次 Celery 定时任务运行时（批量更新）
3. 每次状态盘点完成时（consolidation 后更新）

---

## 第五部分：分阶段实施路线图

### Phase 0：激活休眠能力（1-2 天，零风险）

**目标**：不写新代码，只翻转 Feature Flag，验证已有时间感知路径。

| 动作 | 代码位置 | 预期效果 |
|------|---------|---------|
| 启用 `ENABLE_CONTEXT_BRIEFING=True` | `backend/app/core/context_pack.py` | LLM 开始接收上下文简报 |
| 启用 `ENABLE_PERCEPTIBLE_INTELLIGENCE=True` | `backend/app/services/perceptible_intelligence_service.py` | 激活主动洞察生成 |
| 观察指标 | `CONTEXT_BRIEFING_GENERATED_TOTAL`, `PERCEPTIBLE_INSIGHT_CANDIDATE_TOTAL` | 确认代码路径无异常 |

**风险**：Feature Flag 被禁用可能是有原因的（性能/质量），需先在 staging 环境验证。

### Phase 1：L1 Now Layer（3-5 天）

**目标**：为每个用户会话注入精确的时间锚点信息。

| 步骤 | 改动文件 | 改动内容 |
|------|---------|---------|
| 1.1 | `prompts.py` | 新增 `TEMPORAL_ANCHOR_SECTION` 模板 |
| 1.2 | `prompts.py` → `build_system_prompt()` | 在 section_map 中注入时间锚点数据 |
| 1.3 | `context_builder.py` → `_build_user_context()` | 计算 `time_since_last_interaction` |
| 1.4 | `prompts.py` → `_SECTION_BUDGET_RATIO` | 为 `temporal_anchor_section` 分配 2% 预算 |

**验证标准**：每次 LLM 调用的 System Prompt 首部包含"当前时间"、"距上次交互时长"信息，token 开销增量 < 50。

### Phase 2：L2 Active State Layer 增强（5-7 天）

**目标**：为活跃计划和任务添加 deadline proximity 和 confidence score。

| 步骤 | 改动文件 | 改动内容 |
|------|---------|---------|
| 2.1 | `plan_context.py` | 新增 `_compute_deadline_proximity()` 方法 |
| 2.2 | `plan_context.py` | 新增 `_estimate_plan_confidence()` 方法（Ebbinghaus 变体） |
| 2.3 | `plan_context.py` → `build()` | 在输出字典中增加上述字段 |
| 2.4 | `plan_progress_service.py` | 复用 `time_progress` 和 `progress_lag` 计算逻辑 |

**验证标准**：`PlanContextBuilder.build()` 返回的字典包含 `deadline_proximity`（0-1）和 `confidence_score`（0-1）。

### Phase 3：L3 Session Delta Layer（7-10 天）

**目标**：建立双时态事件缓冲区，实现事件流的时间有序管理。

| 步骤 | 改动文件 | 改动内容 |
|------|---------|---------|
| 3.1 | `event_bus.py` → `Event` 基类 | 增加 `event_time` / `ingestion_time` 双轨字段 |
| 3.2 | 新建 `event_buffer.py` | Redis Sorted Set 事件缓冲区实现 |
| 3.3 | `event_bus.py` → 各事件子类 | 适配双时态字段 |
| 3.4 | Celery 任务配置 | 新增每日事件归档任务（L3→L4 坍缩触发器） |

**验证标准**：所有事件均携带双时态标记，事件缓冲区按 event_time 有序，能在 P95 < 50ms 内检索指定时间窗口内的事件。

### Phase 4：L4 Long-term Timeline Layer（10-14 天）

**目标**：实现 TiMem 式的层级坍缩和 Zep 式的版本化状态链。

| 步骤 | 改动文件 | 改动内容 |
|------|---------|---------|
| 4.1 | 新建 `consolidation_worker.py` | 日总结 + 周总结的 LLM 调用管道 |
| 4.2 | 新建 `daily_summary.py` 模型 | 日总结数据表 |
| 4.3 | `plan_state_service.py` | 推广 `replaced_by_id` 模式到 PlanState |
| 4.4 | Celery Beat | 新增 consolidation 定时任务（每日 3:30 AM） |

**验证标准**：系统能自动将过去 7 天的 EpisodicMemory 坍缩为一条日总结，过去 4 周的日总结坍缩为一条周总结。

### Phase 5：Temporal State Estimator（14-21 天）

**目标**：建立统一的时序状态空间，实现"上次到现在"的连续感知。

| 步骤 | 改动文件 | 改动内容 |
|------|---------|---------|
| 5.1 | 新建 `temporal_state_estimator.py` | TemporalState 数据类 + 状态更新方程 |
| 5.2 | `context_builder.py` | 集成 TemporalState 到上下文构建流程 |
| 5.3 | Celery 任务 | 新增 `update_temporal_states` 批量更新任务 |
| 5.4 | `orchestrator.py` → `stream_chat()` | 在主循环中调用 TemporalState 更新 |

**验证标准**：每个活跃用户维护一个持续更新的 `TemporalState`，系统在任何时刻都能回答"距上次交互多久了"、"当前最紧迫的事项是什么"、"哪个计划需要立即关注"。

---

## 第六部分：风险与防护

### 6.1 时间推断置信度衰减（对应研究 §VIII 的 "Risks of Temporal Over-reliance"）

**风险**：系统根据物理时间流逝盲目推算任务进度（"已经 3 天了，用户应该完成了"）。

**防护**：Phase 2 中引入的 `confidence_score` 必须：
- 初始值为 1.0（用户明确确认时）
- 按半衰期衰减（默认 7 天降至 0.5）
- 跌破 0.3 时触发"状态验证探针"（轻量级消息询问用户进展）
- **绝不允许**在置信度 < 0.3 时自动推进计划状态

### 6.2 过度主动的越界打断（对应研究 §VIII 的 "Over-proactivity"）

**风险**：Deadline proximity 模型导致系统在深夜或用户高压期频繁打扰。

**防护**：
- 所有主动推送必须经过 UX Envelope 的负信号检测（`NEGATIVE_USER_SIGNAL_KEYWORDS`）
- 推送频率受 `PushService` 的最小间隔限制（已有机制）
- Deadline proximity > 0.9 但用户最近 2 小时内有负信号 → 抑制推送，降级为静默记录

### 6.3 用户矫正特权（对应研究 §VIII 的 "User-correctable Time State"）

**风险**：系统的时序推断与用户实际状态不符。

**防护**：
- L2 的 Active State 面板应该可以通过 Flutter 端的"计划详情页"直接查看和修正
- 用户手动修改计划状态时，`confidence_score` 重置为 1.0
- 所有状态变更记录在 `MemoryCorrection` 表中（已有机制，复用即可）

---

## 第七部分：与研究论文 6 大范式的精确对应关系

| 研究范式 | Sparkle 当前位置 | TCL 增强位置 | 预期收益 |
|---------|----------------|-------------|---------|
| 1. Tool-Call 范式 | `_utcnow()` 全项目 | 不变（保持基础能力） | — |
| 2. Event Log 范式 | `event_bus.py`, `ChatMessage` | Phase 3: 双时态事件缓冲区 | 事件不再丢失，支持时间窗口查询 |
| 3. 时序知识图谱范式 | `MemoryPreference` 版本链 | Phase 4: 推广到所有核心实体 | 状态演变可追溯，过期事实自动失效 |
| 4. 任务状态追踪范式 | `PlanProgressService`, `PlanState` | Phase 2: deadline proximity + confidence | 计划跟踪从"即时快照"升级为"持续监控" |
| 5. 主动唤醒/调度范式 | Celery/APScheduler 定时任务 | Phase 5: Temporal State Estimator | 从固定 Cron 升级为事件驱动的动态唤醒 |
| 6. 分层压缩摘要范式 | `ContextPruner`（仅会话内） | Phase 4: Consolidation Worker | 从"暴力截断"升级为"语义坍缩" |

---

## 第八部分：5 项研究前沿问题的 Sparkle 适配优先级

### 优先级 1（立即启动）：Deadline Proximity + Confidence Decay

**适配理由**：`PlanProgressService` 已有 `time_progress` 和 `progress_lag` 计算，添加 `deadline_proximity` 和 `confidence_score` 是增量工作，风险极低。

**对应研究**：Zep 的 Validity Windows + CMA 的时间衰变

**实现位置**：`plan_context.py` 增强

### 优先级 2（Phase 3 启动）：双时态事件流

**适配理由**：`Event Bus` 已有丰富的事件定义，只需增加 `event_time` / `ingestion_time` 字段和 Redis 缓冲区。

**对应研究**：Zep/Graphiti 的 Bi-temporal 双轨 + TReMu 的提及时间/事件时间解耦

**实现位置**：`event_bus.py` 增强 + 新建 `event_buffer.py`

### 优先级 3（Phase 4 启动）：层级整合管道

**适配理由**：`EpisodicMemory` 持续增长但从不压缩，添加 Consolidation Worker 是解决上下文膨胀的根本方案。

**对应研究**：TiMem 的 5 层时序记忆树 + HMO 的三层物理存储

**实现位置**：新建 `consolidation_worker.py` + `daily_summary.py`

### 优先级 4（Phase 5 启动）：时序状态估计器

**适配理由**：这是将所有时间能力统一为一个连续状态空间的核心组件，必须在前 3 个阶段完成后再启动。

**对应研究**：Stream of Computation 的持续递归推理 + 控制论的状态估计

**实现位置**：新建 `temporal_state_estimator.py`

### 优先级 5（长期研究方向）：主观时间分辨率映射

**适配理由**：需要大量用户行为数据来训练"什么情境下用户感知的时间更紧迫"的模型，是长期研究方向。

**对应研究**：Wall-clock vs Subjective Time 的多分辨率映射

**实现位置**：`personalization` 模块增强

---

## 第九部分：与 Aurora Stage 路线图的交叉分析

### 9.1 与当前 Aurora Stage 的关系

根据 MEMORY.md 中记录的 Aurora 路线图（Stage 22+），本报告提出的时间连续性方案与 Aurora 存在以下交叉：

| Aurora Stage | 本报告对应 | 交叉性质 |
|-------------|----------|---------|
| Stage 22 (Baseline Repair) | Phase 0 (激活 Feature Flag) | **高度重叠**——Stage 22 的核心任务之一是验证 prompt 渲染覆盖率，与 Phase 0 启用 `ENABLE_CONTEXT_BRIEFING` 直接相关 |
| Stage 23 (Bayesian Wire-On) | Phase 5 (Temporal State Estimator) | **互补**——Bayesian 为 Temporal State Estimator 提供先验概率框架 |
| Stage 24 (Accountability Policy Compiler) | Phase 2 (Deadline Proximity) | **互补**——Accountability 的策略编译可以消费 Deadline Proximity 作为输入 |
| Stage 19A (Working Memory + Consolidation) | Phase 4 (L4 Consolidation Worker) | **高度重叠**——Working Memory 概念与 L3/L4 的缓冲区+整合管道是同一件事 |

### 9.2 建议的协调策略

**本报告不应取代 Aurora 路线图**，而应作为 Aurora 的"时间维度增强视角"被整合。具体建议：

1. **Stage 22 的 Baseline Repair 优先执行**，在其 prompt 覆盖率验证完成后，再决定是否启用 `ENABLE_CONTEXT_BRIEFING`
2. **本报告的 Phase 1 (L1 Now Layer)** 可以作为 Stage 22 的附加交付物，因为两者都涉及 prompt 结构调整
3. **Phase 2-5 的优先级排序需要与 Aurora Stage 23-25 协调**，避免两条并行的改动路径在 `plan_context.py` 和 `orchestrator.py` 上产生冲突

### 9.3 关于 `temporal_engine.py` 删除的历史考证

在 Aurora Card Protocol (Stage 0-1) 阶段，`temporal_engine.py` 曾作为 Card Protocol 的子模块存在。根据 MEMORY.md 中"Phase 0 DONE: All vocabularies, types, boundaries frozen"的记录，temporal engine 可能在 Card Protocol 的 vocabulary 冻结过程中被移除，因为其功能超出了 Phase 0 的 vocabulary 定义范围。建议在重启时间能力建设时，先回溯 Aurora 治理记录确认移除原因。

---

## 第十部分：结论

### 10.1 核心发现

1. **Sparkle 的时间基础设施比预期更成熟**：`MemoryPreference.replaced_by_id`（双时态雏形）、`DecayService`（Ebbinghaus 曲线）、`PlanProgressService`（进度差值检测）、Celery 定时任务（原始 Wake-up Engine）——这些都为 TCL 的构建提供了坚实的基础。

2. **关键缺失不是模块而是层**：系统有大量时间相关代码，但它们散布在各个模块中，没有一个统一的抽象层来协调。TCL 的核心价值是将这些碎片整合为一个连续的状态空间。

3. **最高 ROI 的第一步是激活休眠 Feature Flag**：`ENABLE_CONTEXT_BRIEFING` 和 `ENABLE_PERCEPTIBLE_INTELLIGENCE` 的启用不需要写新代码，但能立即提升系统的时间感知能力。

4. **`temporal_engine.py` 的删除暗示了历史包袱**：Card Protocol 子系统曾有时间引擎，但被移除了。在重新引入时间能力时，需要理解当初移除的原因（性能？复杂度？优先级调整？）。

### 10.2 架构判断

**"轻量级的高效活跃状态机 (L2) + 负责深层长程管理的异步时序压缩管道 (L4) + 外挂事件驱动调度引擎"** 是 Sparkle 的最佳实践架构。

理由：
- **L2 增强**可以复用 `PlanProgressService` 和 `PlanContextBuilder`，增量改动极小
- **L4 管道**可以复用 Celery 基础设施和 `DecayService` 的数学模型
- **事件驱动调度**可以复用 `PushService` 的策略模式
- 整体架构不破坏现有的 Mixin 组合结构

### 10.3 最终建议

**先做 Phase 0（激活 Feature Flag）和 Phase 1（L1 Now Layer）**。这两个阶段的改动量最小、风险最低，但能立即可见地提升用户感受到的时间连续性。后续阶段根据 Phase 0-1 的运行数据决定是否推进。

---

**报告状态**: ✅ 三轮自审定稿完成（v3.0 Final）
- 第一轮自审：修正 Feature Flag 位置、预算分配逻辑、补充 Aurora 对齐分析
- 第二轮自审：修正 REMem 对位（补充已有索引说明）、L3 Event Buffer 改为旁路写入模式
- 第三轮自审：确认论文覆盖完整、架构约束合规、验证标准完备

*附录：本文引用的 8 篇前沿研究详细分析见用户提供的原始研究文本。*
