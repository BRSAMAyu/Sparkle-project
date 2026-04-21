# SPARKLE Aurora Stage 21 Dispatch Plan (2026-04-21)

> **Workstream Bundle**: `WS-SK-*`（Skill System MVP）
> **Phase Mapping**: Roadmap v2.0 原 Stage 20 内容下移到 Stage 21
> **战略定位**: 让“用户与 AI 共同沉淀的可复用问题处理模式”第一次成为系统一等公民。

## §0 Stage 21 元信息

### 0.1 7-Phase Growth Ring 映射

| Phase | Stage 21 解锁 | 不做 |
| --- | --- | --- |
| Plan | Skill 在规划阶段作为 prompt context 影响策略选择 | 不让 Skill 替代 Plan |
| Execute | Skill 作为 prompt context 影响响应风格与工具偏好 | 不让 Skill 直接产出 routing branch |
| Reflect | 用户可把“刚才那种处理方式”沉淀为 Skill | 不做自动反思评分 |
| Reinforce | Skill 使用计数器开始累积 | 不做 Skill 效果学习 |

### 0.2 Aurora 三层架构定位

- Skill 元数据（`id / name / usage_count / active`）属 **L1 派生层**，可进 Aggregator
- Skill 内容（`pattern_template / activation_conditions / examples`）属 **独立 L1 子系统 `skill_store`**，严禁进入 Aggregator
- Cross-user 共享走 **独立 `skill_share` 子系统**，与个人 `skill_store` 物理隔离
- Skill 只能在 prompt 渲染阶段以 **read-only context** 注入；严禁进入 Router 决策分支

### 0.3 Rule 审计清单

- Rule G / H / K / Y / Z / AB / AC / AD / AE：照旧
- **Rule AF**：Cross-user Skill 共享治理
- Rule U：Skill 任一条目必须 widget-level 可点编辑 / 删除 / 分享
- Rule V：新增 Stage 21 契约覆盖 schema、隔离、审核链、激活条件、三级 kill
- Rule W：Skill 效果学习延后到 Stage 22 Bayesian wire-on

### 0.4 Path A / B / C

| Path | 触发条件 | 范围 |
| --- | --- | --- |
| **A** | Stage 20 final-accept + Conflict Resolver 替换稳定 | 全 7 WS |
| **B1** | Skill 共享审核流水线 PII 漏检率 `> 1%` | 保留个人 Skill Store / Extract / Selection；Sharing 延后 |
| **B2** | Skill Selection 接入后响应分布 KL `> 0.10` | Store / Extract 继续；Selection logging-only |
| **C** | Skill 内容进入 Aggregator 或 Skill 参与 Router 分支 | 立即停并回滚违规切面 |

### 0.5 Codex 自答四题

1. Skill 不能是“AI 自动学到的隐藏行为”，必须来自显式沉淀。
2. Skill 内容不能进入 Aggregator，只能元数据进 Aggregator。
3. Cross-user 共享不能绕过审核队列。
4. Shared Skill 必须支持作者侧一键撤回新 fork 能力。

## §1 Stage 21 总目标

1. 建立 frozen Skill schema v1 与个人 Skill Store
2. 建立仅依赖显式信号的 Skill 抽取与草稿确认流
3. 建立 Skill Selection：Aggregator 暴露元数据，Router 只做 prompt context 注入
4. 建立 opt-in per skill 的 Cross-user 分享 / fork / 撤回基础设施

## §2 Gate S21-0 入场基线

1. Stage 12 baseline `144`
2. Rule V `8`
3. Rule K + Z + AB + AC + AD + AE `0 violation`
4. Stage 13-20 carry-forward sweep 全绿
5. Stage 20 Conflict Resolver 稳定性证明完成
6. Roadmap v2.0 命名表已更新：Rule AF 锁定为 Skill sharing governance

## §3 Workstreams

| WS | 目的 |
| --- | --- |
| `WS-SK-RULE-AF` | Rule AF 定义 + CI 守卫 |
| `WS-SK-SCHEMA` | Skill schema v1 + `user_skills` store |
| `WS-SK-EXTRACT` | 仅显式信号触发的 Skill 草稿抽取 |
| `WS-SK-SELECTION` | Aggregator `v1.3` + Router prompt-only Skill 注入 |
| `WS-SK-SHARE` | Cross-user 共享流水线 + fork / 撤回 |
| `WS-SK-MOBILE` | “我的方式” 管理 UI + draft / share / catalog / fork |
| `WS-SK-KILL` | Store / Selection / Share 三级 kill 独立开关 |

## §4 Rule AF 正式表述

> **Rule AF**: 任一 Cross-user Skill 共享必须 opt-in per skill、必经 `PII scanner + prompt injection detector + moderation queue` 三步流水线、作者匿名化、采用为 fork 复制，并且不留 `author_user_id` 反向引用或任何 telemetry 回链。Shared Skill 内容禁止包含 `person_mention` 或 `inferred_extraction` 具体值，永禁进入 Aggregator 任一字段，永禁作为 LLM 抽取器 few-shot 输入。

CI 入口：

1. `scripts/check_rule_af_skill_share_isolation.py`
2. `scripts/check_rule_af_skill_pii_pipeline.py`

## §5 Gate S21-FINAL

1. Gate S21-0 全绿
2. Rule AF 文档 + 两条 guard `0 violation`
3. Skill schema v1 frozen + 契约测试 green
4. 个人 Skill Store CRUD + Alembic migration apply / rollback 通过
5. Skill 抽取草稿生成正确率 `>= 0.85`
6. Skill Selection A/B KL `<= 0.10`
7. Sharing 流水线 PII 漏检 `<= 1%` 且 injection 漏检 `0`
8. Aggregator 加 `active_skills_summary` 后 Router migrate 等价性 KL 增量 `<= 0.03`
9. Stage 21 targeted backend sweep `>= 24 passed`
10. Stage 21 targeted mobile sweep `>= 8 passed`
11. grep 守卫通过：
   - `Skill.pattern_template` 在 `state_aggregator/` 下 `0 hit`
   - `activation_match_score` 在 Router 决策分支 `0 hit`
   - `skill_share/` import `skill_store/` 内部模块 `0 hit`
   - adopted Skill 路径上 `author_user_id` `0 hit`

## §6 延后到 Stage 22+

1. Bayesian wire-on（Stage 22）
2. Skill 效果学习
3. LLM 自动 Skill 生成
4. Shared Skill 实时订阅 / 市场化目录
5. Shared Skill 社交特征（关注 / 排行 / 评论 / 推荐）

## §7 Stage 22 入场义务

- Stage 22 Bayesian 必须消费 `Route History + Skill usage_count + Sufficiency Judge`
- Stage 22 必须重做 Stage 14 SQAM 四维测量
- Stage 23 Accountability 规则号预留为 **Rule AG**

## §8 自动化执行模式

- `scripts/stage21/run_stage21.sh`
- `scripts/stage21/ws_sk_*.sh` × 7
- `scripts/stage21/gate_final.sh`
- `docs/product/stage21_progress.md`

## §9 关键设计决策锁定

1. Skill 抽取仅显式信号触发，永禁 LLM 主动抽取
2. Skill 内容永禁进入 Aggregator；只元数据进
3. Skill Selection 永禁进入 Router 决策分支；只进 prompt context
4. Cross-user 共享永禁保留 `author_user_id` 反向引用
5. Cross-user 共享永禁任何社交特征
6. Skill 内容永禁包含 `person_mention` 或 `inferred_extraction` 具体值
7. 单用户 Skill 上限 `50`；最多 top `3` 注入 prompt
8. 共享流水线三步缺一不可：PII scanner + injection detector + moderation queue
9. Adopted Skill 即解耦，严禁 telemetry 回链原作者

## §10 执行令

1. 落盘 Stage 21 dispatch、Rule AF、frozen prompts、`scripts/stage21/`
2. 更新 Roadmap v2.0 Stage 22 / 23 命名表
3. 实现 Stage 21 全 7 WS
4. 通过 Gate S21-FINAL 后产出 `SPARKLE_AURORA_STAGE21_HANDOFF_2026-04-21.md`
5. Stage 22 dispatch 由架构师下一轮发起，Codex 不自造
