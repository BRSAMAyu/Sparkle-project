# SPARKLE Aurora Stage 22 Dispatch Plan (2026-04-21)

> **Workstream Bundle**: `WS-BR-*`（Baseline Repair）
> **战略定位**：在 Stage 23 Bayesian wire-on 之前，把“数据收集 → AI 可见 → AI 利用 → 闭环”主干从泄漏态修到可审计、可接线、可验证的基线。
> **执行模式**：Fast-Dev 启动；本阶段先以真实代码审计和 gate 自动化拉出基线，再推进各 WS 实装。

## §0 Stage 22 元信息

### 0.1 七阶段成长环映射

| Phase | Stage 22 解锁 | 不做 |
| --- | --- | --- |
| Sense | 成就 / 日历 / 错题信号到达 AI prompt | 不新增信号源 |
| Clarify | 不变 | — |
| Plan | `error_replan_bridge` 触发扩展至 `>= 6` 种 | 不新增规划算法 |
| Execute | 不变 | — |
| Reflect | OutcomeVerifier 常驻化、cohort 补全 | 不改验证算法 |
| Reinforce | 种子采纳 → outcome → 回流 | 不新增奖励机制 |
| Adapt | 为 Stage 23 Bayesian 准备输入基线 | 不启动学习策略 |

### 0.2 Aurora 三层定位

- `L0`：无改动（事件 / 原始证据层）
- `L1`：成就 / 日历 / 种子元数据读通道补齐，进 Aggregator `v1.4`（向后兼容）
- `L2`：`error_replan_bridge` 触发器扩展；OutcomeVerifier Celery 常驻化
- `L3`：写审计照旧
- `User Correction`：种子验证闭环中保留用户显式撤回路径

### 0.3 Rule 审计清单

- Stage 22 **不新增 Rule**
- 沿用 Rule `G / H / K / Y / Z / AB / AC / AD / AE / AF`
- Aggregator schema `v1.3 → v1.4` 升级必过 Rule AB guard
- OutcomeVerifier Celery 化仍须遵守 Rule K 写道白名单，不得绕过 `L0/L1/L2`

### 0.4 Path A / B / C

| Path | 触发条件 | 范围 |
| --- | --- | --- |
| `A` | Stage 21 final-accept 达成 + GLM1 / observer 双绿 | 全 6 WS |
| `B1` | Achievement / Calendar 读通道 A/B 等价性 `KL > 0.03` | 该 WS 回滚，其余继续 |
| `B2` | OutcomeVerifier Celery 化后延迟 `p95 > 3s` | 回退 in-process，WS-BR-LOOP-CLOSURE 保留触发器扩展 |
| `C` | Aggregator `v1.4` 引入 Router 分支条件（违反 Rule AB） | 立即停并回滚 `v1.4` |

### 0.5 Codex 自答 4 题

1. `WS-BR-PROMPT-VERIFY` 只做验证，不做 `prompts.py` 修复；如发现真实漏渲染字段，升级为架构提案。
2. `error_replan_bridge` 触发器必须纯规则，LLM 只可做错因归类，不可做触发判定。
3. Achievement / Calendar 只读单向进入 AI，上行反写被明确禁止。
4. OutcomeVerifier Celery worker 的 DB 写入必须继续走 Rule K 白名单。

## §1 总目标

一句话：把“AI 可见”从局部打通提升到可审计的 Stage 23 可接线基线，并把 Growth Loop 的闭环证据从 2 个亮绿节点推进到 6 个。

Stage 22 本期只做 6 件事：

1. 验证 prompt 渲染覆盖率并固化遥测口径
2. 激活 `error → replan → outcome` 闭环
3. 打通 `achievement → AI` 画像（只读）
4. 打通 `calendar → AI` 上下文（只读）
5. 修 `InterventionStrategyLearner` 队列 / cohort 路径
6. 打通 `seed adoption → action → outcome → quality score` 验证回流

禁止事项：

- 禁止在 Stage 22 新增学习 / 预测 / 推荐能力
- 禁止重构 orchestrator FSM
- 禁止破坏 Aggregator read-only invariant
- 禁止引入新 Rule
- 禁止在 Achievement / Calendar 反向写入 AI 推断
- 禁止在 `error_replan_bridge` 触发器路径内调 LLM

## §2 Gate S22-0 入场基线

1. Stage 21 final-accept 已出（GLM1 / observer 双绿）
2. Stage 12 baseline `144` 测试全绿
3. Rule `K / Z / AB / AC / AD / AE / AF` 七重 guard `0 violation`
4. Stage 20-21 carry-forward sweep 全绿
5. Aggregator `v1.3 → v1.4` 升级前先补契约测试，旧 consumer 反序列化 `v1.4` 不崩
6. Stage 22 开工前先产出 [stage22_precheck.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/stage22_precheck.md)

## §3 六个 Workstream

### `WS-BR-PROMPT-VERIFY` — prompt 渲染覆盖率验证 + 遥测基线

目标：

1. 扫描 `context_manager.py` / `plan_context.py` / `prompts.py` 等链路，列出 normalize 进 context dict 的字段
2. 审计 `_mark_rendered()` 和 model-facing 渲染点，计算覆盖率
3. 固化 [stage22_prompt_coverage_baseline.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/stage22_prompt_coverage_baseline.md)
4. 严禁修改 `prompts.py` 渲染逻辑；真实漏渲染字段升级到独立提案

验收：

- 覆盖率 `>= 70%`：green
- 覆盖率 `60%-70%`：Path B 候选
- 覆盖率 `< 60%`：暂停并升级架构

### `WS-BR-LOOP-CLOSURE` — error → replan 闭环激活

目标：

1. `TRIGGERING_ERROR_TYPES` 从 2 种扩到 `>= 6` 种，且全部纯规则
2. 同一 `plan + trigger_type` 增加 `24h` 冷静期
3. OutcomeVerifier 常驻 Celery worker / beat
4. `cohort_profile` 补齐 `goal_type + knowledge_level`

验收：

- `scripts/check_error_replan_trigger_purity.py` 通过
- OutcomeVerifier Celery 化后 `p95 < 3s`
- cohort fallback 契约测试 green

### `WS-BR-ACHIEVEMENT-WIRE` — 成就 → AI 画像（只读单向）

目标：

1. `achievement_context_provider` 提供 `recent_unlocks / in_progress_achievements / total_achievement_score`
2. `prompts.py` 新增 `_format_achievement_context_line()`
3. Aggregator `v1.4` 增 `achievement_summary`
4. `achievement_summary` 在 Router 分支条件命中数必须为 `0`

### `WS-BR-CALENDAR-WIRE` — 日历 → AI 上下文（扩展读字段）

目标：

1. 日历上下文扩展 `upcoming_deadlines / time_blocks_today / workload_density / exam_urgency`
2. 仅在用户日历读授权开启时注入
3. 禁止 AI 写日历

### `WS-BR-INTERVENTION-Q` — 干预学习队列修复

目标：

1. 复现并修复 `error_replan_bridge → InterventionStrategyLearner` 队列到达缺口
2. 修复 OutcomeVerifier 在 bridge 路径的 cohort 字段补齐
3. bridge 路径事件失败后重试 `3` 次，再进入 `dead_letter`

### `WS-BR-SEED-VERIFY` — 种子验证闭环

目标：

1. 采纳事件补 `adoption_id`
2. `<= 7d` 用户行动与 `adoption_id` 关联
3. OutcomeVerifier 复用 Celery worker 消费 seed outcome
4. 回流更新既有 `seed_quality_score`
5. UI 保留“此种子不适合我”的显式撤回路径

## §4 Gate S22-FINAL 验收门

1. Gate S22-0 全绿
2. 6 WS 全 green，或显式触发 Path `B1/B2`
3. 数据利用评分 `>= 7.0/10`
4. Growth Loop 8 环节亮绿 `>= 6`
5. Stage 22 targeted backend sweep `>= 20 passed`
6. Stage 22 targeted mobile sweep `>= 4 passed`
7. grep 守卫通过：
   - `achievement_summary` 在 Router 分支 `0`
   - `calendar_context` 在 Router 分支 `0`
   - `error_replan_bridge` 触发路径 `openai|anthropic|llm import` `0`
   - Achievement engine 被 AI `tool_call` 写入 `0`
8. CL baseline regression 首次纳入 gate
9. [stage22_precheck.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/stage22_precheck.md) 落盘
10. [stage22_prompt_coverage_baseline.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/stage22_prompt_coverage_baseline.md) 落盘

## §5 已知延后到 Stage 23+

1. Growth Loop 完整 `8/8` 亮绿
2. Memory Scene 聚类
3. Foresight 引擎
4. Traits 弱先验
5. SRL 三阶段完整化
6. Metacognition 三维偏差
7. Idiographic 关联发现

## §6 Stage 23 入场义务

1. Stage 23 source-state 必须消费 Stage 22 补齐后的 `achievement + calendar + cohort_profile + seed outcome`
2. Stage 23 必须重做 Stage 14 `SS-AUDIT` 全套 4 维 SQAM（Rule W）
3. Stage 23 不得自建平行历史采集层，所有输入从 `routing_decision_log + outcome_records + user_skills.usage_count` 三源读
4. Stage 23 执行期间需持续监控 Stage 22 六通道稳定性
5. [stage22_precheck.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/stage22_precheck.md) 里的 Stage `25 / 27 / 29` 定性结论直接继承到后续 dispatch

## §7 自动化执行模式

```
scripts/stage22/run_stage22.sh
scripts/stage22/ws_br_prompt_verify.sh
scripts/stage22/ws_br_loop_closure.sh
scripts/stage22/ws_br_achievement_wire.sh
scripts/stage22/ws_br_calendar_wire.sh
scripts/stage22/ws_br_intervention_q.sh
scripts/stage22/ws_br_seed_verify.sh
scripts/stage22/gate_final.sh
docs/product/stage22_progress.md
```

失败策略：

- prompt 覆盖率 `< 60%`：暂停升级架构
- OutcomeVerifier Celery `p95 > 3s`：自动 Path `B2` 回退
- Achievement / Calendar Router `KL > 0.03`：自动 Path `B1` 回滚该 WS
- Aggregator `v1.4` 命中 Router 分支：立即 Path `C`

## §8 关键设计锁定

1. `WS-BR-PROMPT-VERIFY` 只审计不修 prompt
2. `error_replan_bridge` 触发器纯规则、禁 LLM
3. Achievement / Calendar 只读单向
4. Celery worker DB 写入走 Rule K 白名单
5. Aggregator `v1.4` 字段禁入 Router 分支
6. 种子撤回必须保留用户显式路径
7. Stage 22 禁新增 Rule
8. Stage 22 禁重构 orchestrator 状态转移

## §9 Codex 执行令

1. 落盘本 dispatch plan
2. 落盘 `scripts/stage22/` 全套脚本
3. Roadmap v2.1 Amendment 与主路线图 `§6.5` 同步到本 dispatch / fast-dev lock
4. 完成以上后立即执行 `bash scripts/stage22/run_stage22.sh`
5. Gate S22-FINAL 通过后产出 `SPARKLE_AURORA_STAGE22_HANDOFF_2026-04-21.md`
6. Stage 23 dispatch 由架构师下一轮发出，Codex 不自造 Stage 23 implementation beyond the locked table
