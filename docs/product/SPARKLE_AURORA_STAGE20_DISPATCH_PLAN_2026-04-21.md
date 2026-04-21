# SPARKLE Aurora Stage 20 Dispatch Plan (2026-04-21)

> **Workstream Bundle**: `WS-SJ-*` + `WS-CR-*` + `WS-RH-*`（Sufficiency Judge + Conflict Resolver + Route History）
> **Phase Mapping**: Roadmap v2.0 原 Stage 19B 内容下移到 Stage 20
> **战略定位**: 让系统第一次显式承认"自己知道多少 / 知道得对不对 / 之前的决策结果如何"。

## §0 Stage 20 元信息

### 0.1 7-Phase Growth Ring 映射

| Phase | Stage 20 解锁 | 不做 |
| --- | --- | --- |
| Clarify | Sufficiency Judge 让"我不够确定"可以被显式问出来 | 不做主动追问的 prompt 工程优化 |
| Reflect | Route History 把过去的决策与结果配对 | 不做反思的 LLM 评估 |
| Reinforce | Conflict Resolver 把矛盾事实公开化 | 不做用户层面的"事实校验"对话 |
| Adapt | 为 Stage 22 Bayesian wire-on 提供可信底料 | 本期不接通 Bayesian |

### 0.2 Aurora 三层架构定位

- Sufficiency Judge / Conflict Resolver 属 **L3 Aurora 决策层**
- Route History 属 **L3 决策审计基础设施**
- 三者对 Aggregator + Working Memory 都是 **read-only consumers**
- Sufficiency / Conflict 写入审计侧表，不改 Aurora 决策日志主表 schema

### 0.3 Rule 审计清单

- Rule G / H / K / Y / Z / AB / AC：照旧
- **Rule AD**：Sufficiency Judge 治理
- **Rule AE**：Conflict Resolver 治理
- Route History 复用既有 L3 决策审计约束

### 0.4 Path A / B / C

| Path | 触发条件 | 范围 |
| --- | --- | --- |
| **A** | Stage 19 final-accept + LLM 抽取 precision ≥ 0.85 | 全 7 WS |
| **B1** | task/context 分离精度 < 0.80 | Sufficiency logging-only |
| **B2** | Conflict Resolver 替换路径退化 | 回滚替换，保留影子模式 |
| **C** | Route History 写入退化 > 20% | 停库写，转 Redis buffer |

### 0.5 Codex 自答四题

1. Sufficiency Judge 必须是纯规则，不得 LLM 化。
2. Conflict Resolver 任一覆盖都必须留下审计记录。
3. Route History 本期只写；除按 `decision_id` 回填 outcome 外，不允许在线读取。
4. Router 只能基于 `task_sufficiency` 分支；`context_sufficiency` 只能进入 prompt caveat。

## §1 Stage 20 总目标

1. 建立 Sufficiency Judge：分 `task_sufficiency` 与 `context_sufficiency`
2. 建立 Conflict Resolver：冻结优先级链 + 审计
3. 建立 Route History：采集 routing decision 与 outcome 对

## §2 Gate S20-0 入场基线

1. Stage 12 baseline `144`
2. Rule V `8`
3. Rule K + Z + AB + AC `0 violation`
4. Stage 13-19 carry-forward sweep 通过
5. Stage 19 LLM 抽取 precision ≥ `0.85`
6. 顺手清 Stage 17 carry-forward：Rule Z HMAC 升级路径注释 + closeout reconfirm

## §3 Workstreams

| WS | 目的 |
| --- | --- |
| `WS-SCQ-RULES` | Rule AD + AE 联合定义、CI 守卫、Stage 17 carry-forward 清理 |
| `WS-SJ-CORE` | Sufficiency Judge 核心评分器 |
| `WS-CR-CORE` | Conflict Resolver 核心 + 审计 |
| `WS-SCQ-AGGREGATOR-INTEGRATE` | Aggregator `v1.2` sufficiency 字段 |
| `WS-SJ-ROUTER-CONSUME` | Router 只消费 `task_sufficiency`，`context` 仅 caveat |
| `WS-RH-CORE` | Route History 决策采集与 outcome 回填 |
| `WS-SCQ-MOBILE-DECL` | 画像 front door 暴露未决冲突 |

## §4 Rule AD + Rule AE 正式表述

> **Rule AD**: Sufficiency Judge 是确定性规则评分器，输出必须拆成 `task_sufficiency` 与 `context_sufficiency` 两路；Router 仅可基于 `task_sufficiency` 做分支，`context_sufficiency` 只能进 prompt caveat。评分公式 frozen，输入仅限 Aggregator + Working Memory + 当前 turn 解析结果，输出必须带 `missing_dimensions`。

> **Rule AE**: Conflict Resolver 是确定性优先级裁决器，优先级链 frozen 为 `explicit_correction > inferred_extraction(rule-based) > inferred_extraction(LLM) > working_memory`。任一覆盖必须留下 `conflict_resolution_record`，被覆盖记录软撤销保留审计，禁止跨用户仲裁。

## §5 Gate S20-FINAL

1. Gate S20-0 全绿
2. Rule AD + AE 文档 + guard `0 violation`
3. Sufficiency 分离精度 ≥ `0.80`
4. Conflict Resolver 替换后 Stage 16 inferred-write 测试 `100%` 通过
5. Route History 写入 < `5ms`
6. Aggregator 加 sufficiency 字段后 Router migrate 等价性 KL 增量 ≤ `0.03`
7. Stage 20 backend sweep ≥ `22 passed`
8. Stage 20 mobile sweep ≥ `5 passed`
9. grep 守卫通过
10. Stage 17 carry-forward 两笔补齐

## §6 延后到 Stage 21+

1. Skill 系统（Stage 21）
2. Bayesian wire-on（Stage 22）
3. Accountability Policy Compiler 完整版（Stage 23）
4. Route History 在线读取消费

## §7 Stage 21 入场义务

- Rule AD / AE 正式落地
- Skill 共享治理改号为 **Rule AF**
- Stage 21 Skill 选择必须基于 Aggregator + Conflict Resolver 输出，而不是平行事实视图

## §8 自动化执行模式

- `scripts/stage20/run_stage20.sh`
- `scripts/stage20/ws_*.sh` × 7
- `scripts/stage20/gate_final.sh`
- `docs/product/stage20_progress.md`

## §9 关键设计决策锁定

1. Sufficiency Judge 永禁 LLM 化
2. Sufficiency 输出必须 task/context 双路分离
3. Conflict Resolver 优先级链 frozen 不可改
4. 覆盖必审计，严禁静默
5. Route History 本期只写不读，允许按 `decision_id` 单条回填 outcome
6. Push 永禁消费 Sufficiency / Conflict / Route History

## §10 执行令

1. 落盘 Stage 20 dispatch、Rule AD/AE、follow-up 模板、`scripts/stage20/`
2. 更新 Stage 21+ 命名表（Skill Rule = AF）
3. 顺手清 Stage 17 carry-forward：Rule Z HMAC 升级路径 + handoff reconfirm
4. 通过 Gate S20-FINAL 后产出 `SPARKLE_AURORA_STAGE20_HANDOFF_2026-04-21.md`
