# adaptive_replanner -> 计划执行实施方案

> 日期: 2026-04-02  
> 适用对象: 后端研发、产品、架构、测试  
> 关联文档:  
> - `docs/product/SPARKLE_PRODUCT_CONSENSUS_2026-04-02.md`  
> - `docs/product/SPARKLE_INTERVENTION_LANGUAGE_SYSTEM_2026-04-02.md`  
> 状态: 第一版技术实施方案

---

## 1. 这份方案解决什么问题

当前 `AdaptiveReplanner` 已经能够:

- 根据计划健康度判断是否调整或重规划
- 记录 `adaptive_adjustments`
- 记录 adaptation record
- 在严重情况下触发 `plan_review_service.trigger_replanning`
- 将高置信行为模式映射成计划约束

但是它现在最关键的缺口是:

`增量调整写进了 PlanState，却没有真正改写用户正在执行的计划内容。`

也就是说:

- 系统“知道”该把时长变长一点
- 系统“知道”该把难度降一点
- 系统“知道”该插入前置知识复习
- 但用户实际看到的任务列表、时长、顺序和接下来要做什么，往往没有同步变化

这导致系统当前状态是:

`会诊断、会记录、会说要调整，但不会真正把调整落成用户可执行的新路径。`

本方案的目标就是接上这条断点。

---

## 2. 当前代码现状

### 2.1 已有能力

`backend/app/orchestration/adaptive_replanner.py` 当前已经具备以下基础能力:

1. `_handle_report()`  
   根据 `PlanHealthReport.recommended_action` 在增量调整和全量重规划之间分流。

2. `_apply_incremental_adjustment()`  
   计算出 `adaptive_adjustments`，写入 `PlanState.facts`，并记录 adaptation。

3. `_trigger_full_replan()`  
   在严重情况下通过 `plan_review_service.trigger_replanning()` 触发重规划。

4. `_apply_cognitive_pattern_adjustments()`  
   将高置信行为模式映射为计划约束，写入 `PlanState.constraints`。

5. `PlanProgressService.evaluate_progress()`  
   已经能产出 `warning / critical`、`adjust / replan` 级别判断。

### 2.2 关键断裂

问题集中在 `_apply_incremental_adjustment()`:

- 它把 `time_multiplier` / `difficulty_shift` 等写进了 `PlanState.facts`
- 但没有消费这些 adjustments 去改当前 plan 下的实际任务
- 因此用户侧“计划实体”和“状态层事实”发生分离

当前行为更像:

`系统做了状态注释`

而不是:

`系统真的重写了路径`

### 2.3 现有全量重规划链路

`_trigger_full_replan()` 已经走通到:

- 记录 feedback_log
- 更新 adaptive_meta
- 调用 `plan_review_service.trigger_replanning()`
- 生成 pending action 给 orchestrator

说明“全量重规划入口”是存在的。

因此此次实施不需要重造一条新的重规划链，而要做的是:

1. 让“增量调整”真正改写计划实体
2. 明确什么情况仍走“全量重规划”
3. 保证用户侧能感知到“计划已经被温和改写”

---

## 3. 实施目标

本阶段不追求“万能智能重规划”，只追求一条稳定主链路:

`PlanHealthReport -> adaptive adjustments -> plan task patch -> user-visible next steps`

成功标准:

1. 用户计划健康度触发 `adjust` 时，系统能对现有任务做可验证的增量改写
2. 用户不需要重新创建整套计划，也能看到接下来几步确实变了
3. 改写结果有审计记录、可回滚、可解释
4. 改写交付采用低防御语言，而不是“你的计划有问题”

---

## 4. 实施边界

### 4.1 这阶段要做的

1. 只处理“当前计划的短窗口任务”
2. 只处理最稳定的几类调整
3. 只改未来任务，不改已完成任务
4. 只改用户接下来 1-3 天内的计划段

### 4.2 这阶段不做的

1. 不做全计划重新生成引擎
2. 不做多计划联动优化
3. 不做历史任务 retroactive 改写
4. 不做完全自动的激进结构改造
5. 不把所有认知模式一次性映射进任务层

这是刻意收缩范围，确保 90 天内能跑通一条闭环，而不是把系统做得更复杂。

---

## 5. 第一阶段要支持的四类增量调整

第一阶段建议只把下面四类 adjustments 真正落到计划任务上。

### 5.1 时长放大

来源:

- `adaptive_adjustments.time_multiplier`
- `task_duration_multiplier`
- `ai_duration_multiplier`

任务层改写:

- 更新未来任务 `estimated_minutes`
- 对超长任务触发拆分建议

用户感知变化:

- 接下来任务时间更真实
- 单次任务不再过度乐观

### 5.2 难度下调

来源:

- `difficulty_shift`
- `difficulty_shift_delta`

任务层改写:

- 将未来高难任务替换为更低负荷版本
- 或将一个任务拆成更小步

用户感知变化:

- 接下来几步不再那么“上来就硬”

### 5.3 插入前置知识复习

来源:

- `insert_prerequisite_review`
- `weak_knowledge_node_ids`

任务层改写:

- 在相关任务前插入一个短前置复习任务
- 将主任务状态延后半步，而不是直接保留原顺序

用户感知变化:

- 系统不只是说“你基础不足”，而是直接在路径里补上缺口

### 5.4 收缩并发和可见范围

来源:

- `max_concurrent_tasks`
- `hide_distant_phases`
- `require_min_completion_unit`

任务层改写:

- 压缩当前窗口内同时暴露给用户的任务数量
- 只保留最关键的 1-3 项
- 远期任务只保留骨架，不继续堆到用户面前

用户感知变化:

- 计划不再“压着人”
- 焦虑感降低

---

## 6. 技术实现方案

### 6.1 新增核心服务

建议新增:

`backend/app/services/plan_adjustment_applier.py`

职责:

1. 读取 `PlanState.facts.adaptive_adjustments`
2. 读取 `PlanState.constraints`
3. 查询当前计划的未来任务
4. 生成可执行的任务层 patch
5. 应用 patch 到任务实体
6. 记录 adjustment result 和审计信息

建议输出结构:

```python
@dataclass
class PlanAdjustmentResult:
    applied: bool
    plan_id: UUID
    user_id: UUID
    patch_summary: dict[str, Any]
    affected_task_ids: list[UUID]
    user_facing_summary: str
    rollback_snapshot_id: str | None
```

### 6.2 在哪里接入

当前最佳接入点:

- `AdaptiveReplanner._apply_incremental_adjustment()`

当前逻辑:

1. 计算 adjustments
2. 写入 `PlanState.facts`
3. 记录 feedback_log
4. 发 adaptation update

目标逻辑:

1. 计算 adjustments
2. 写入 `PlanState.facts`
3. 调用 `PlanAdjustmentApplier.apply_incremental_changes(...)`
4. 将任务层 patch 结果写入 `PlanState.facts.adaptive_meta`
5. 记录 feedback_log
6. 发 adaptation update
7. 可选: 生成一个面向用户的轻提示 system update

### 6.3 为什么不直接在 Planner 重跑

因为当前阶段目标是:

`先让局部调整真实生效`

不是:

`每次都重新跑全套 Planner`

增量调整和全量重规划应该共存:

- `adjust` -> 任务层 patch
- `replan` -> 走 `plan_review_service.trigger_replanning()`

---

## 7. 任务层 patch 规则

### 7.1 目标任务选择范围

默认只处理:

- 当前计划中未完成任务
- 截止时间在未来 3 天内，或前 N 个 upcoming tasks

不处理:

- 已完成任务
- 已放弃任务
- 历史任务

### 7.2 patch 顺序

建议按以下优先级依次应用:

1. `insert_prerequisite_review`
2. `difficulty_shift`
3. `time_multiplier`
4. `max_concurrent_tasks / hide_distant_phases`

原因:

- 先决定“该不该插前置”
- 再决定“原任务要不要降负荷”
- 再决定“需要多少时间”
- 最后决定“用户眼前显示多少”

### 7.3 patch 结果形式

建议任务层允许三种改动:

1. 更新任务字段
- `estimated_minutes`
- `priority`
- `due_date`
- `metadata.adaptive_origin`

2. 插入新任务
- 如 `prerequisite_review`
- 如 `micro_start_task`

3. 调整显示窗口
- 通过计划页/任务页读取 `active_window_task_ids` 或 `hidden_future_task_ids`

---

## 8. 数据记录与回滚

### 8.1 为什么必须保留回滚

当前 `adaptive_replanner` 已经有 snapshot/rollback 机制。  
这非常重要，应该继续沿用，而不是重写。

因为一旦自动调整真正改到任务层，就必须允许:

- 连续负反馈后恢复上一版本
- 产品和运营能复盘“改了什么”
- 用户未来可以看到“为什么这周计划变了”

### 8.2 任务层回滚建议

除了现有 `PlanState.facts.adaptive_meta.adjustment_snapshots` 外，建议新增:

- `facts.adaptive_meta.task_patch_snapshots`

每次 patch 记录:

```json
{
  "snapshot_id": "...",
  "trigger": "task_feedback",
  "affected_task_ids": ["..."],
  "before": {...},
  "after": {...},
  "created_at": "..."
}
```

### 8.3 回滚触发条件

延续现有逻辑:

- 连续负反馈
- 用户显式拒绝
- 干预后完成率继续恶化

但第一阶段只要求支持:

- 连续负反馈 -> 回滚上一 snapshot

---

## 9. 用户可感知交付方式

这是技术方案里必须显式写进去的部分。

系统改了计划，不代表用户就会接受。  
所以“计划改写”必须通过低防御方式交付。

### 9.1 不该如何提示

不要用:

- “已自动修正你的计划”
- “原计划不合理，已重调”
- “你的节奏落后，已调整”

这些话会把系统放在裁判位置。

### 9.2 应该如何提示

建议用 system update 或 card 交付，语言遵循干预规范:

- “我把接下来几步收紧了一点，让这条路更好走。”
- “接下来不会一下压给你那么多，我先帮你保留最关键的三步。”
- “我插入了一个很短的前置复习，不是因为你不行，而是这个结点补一下，后面会顺很多。”

### 9.3 CTA 建议

- `看一下新安排`
- `只调整今天`
- `保持原计划`

这里必须给用户保留控制权，避免“系统替我决定了”的感觉。

---

## 10. 实施步骤

### Phase 1: 打通最小闭环

目标:

- 新建 `PlanAdjustmentApplier`
- 在 `_apply_incremental_adjustment()` 中调用
- 支持四类基础 patch
- 支持用户可见的轻提示

验收:

- `adjust` 不再只写状态，而会改接下来 1-3 天的计划

### Phase 2: 引入行为与知识补丁

目标:

- 支持 `insert_prerequisite_review`
- 支持 `require_min_completion_unit`
- 支持 upcoming window 收缩

验收:

- 用户真的看到“更轻”和“更顺”的路径变化

### Phase 3: 接回验证与回滚

目标:

- 将 patch 后的后续任务表现纳入验证
- 接通 rollback snapshot 与失败调整标记

验收:

- 系统知道“这次改法是不是有效”

---

## 11. 测试策略

### 11.1 单元测试

覆盖:

- 不同 `PlanHealthReport` 输入对应的 adjustments
- 四类 patch 的任务层改写是否正确
- snapshot 是否写入
- rollback 是否可恢复

### 11.2 集成测试

建议新增场景:

1. 用户连续任务超时 -> 系统延长未来任务时长
2. 用户多次反馈 too_difficult -> 系统压缩难度和任务窗口
3. 用户知识盲区模式被识别 -> 系统插入前置复习任务
4. 连续负反馈 -> 自动回滚到上一 snapshot

### 11.3 产品验收测试

人工必须验收:

1. 计划页是否真的变化
2. 用户是否看得懂改动
3. 文案是否不会引发强防御
4. 改动是否“更能走”，而不是“更复杂”

---

## 12. 成功标准

这项工作的成功，不是“代码写完”，而是以下四件事同时成立:

1. `AdaptiveReplanner` 的增量调整真正落到计划实体上
2. 用户能在计划页看到接下来几步被改写
3. 交付语言不会引发明显防御
4. 系统能记录这次改动，后续可验证是否有效

只满足前两项，只能算“技术接通”。  
四项都满足，才算“主链路成立”。

---

## 13. 一句话结论

这项工作的本质不是“让 replanner 更聪明”，而是:

`让系统第一次真正把“我知道你现在该换一种走法”变成用户眼前真实可走的新路径。`

这一步接通后，Sparkle 才从“会诊断的系统”迈向“会纠偏的系统”。

---

**文档状态**: 第一版实施方案  
**建议下一步**: 基于本方案直接拆分后端任务，先实现 Phase 1 的最小闭环
