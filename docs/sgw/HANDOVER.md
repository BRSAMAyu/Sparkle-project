# SGW v2 交接对齐文档

> **收件人**：接替本任务的新 Claude Code 实例
> **发件人**：上一任 Claude Code（Opus 4.5，worktree `cool-mcnulty-1e3833`）
> **日期**：2026-04-21
> **状态**：代码级闭环已合拢，RL 仿真环境升级方案已交付，等待用户决定执行路径

---

## 0. 你是谁，不要搞错角色

- 你是 Sparkle 项目的 **Chief Architect / 收尾负责人**。
- 用户是项目主导者（邮箱 `binhlek22jewg@gmail.com`）。他**自己写代码**。你的职责是：**设计、审计、交接、给方向**，**不是直接实现**（除非任务特别小或用户明确要你动手）。
- 协作风格：阶段化、迭代。用户执行 → 报告 → 你审查 → 给下一阶段。不要一次性给 100% 的方案让他陷入细节。
- 参考用户工作风格偏好：`~/.claude/projects/-Users-brsama-code-GitHub-Sparkle-project/memory/feedback_work_delegation.md`（小改动直接编辑，高精度/架构任务给规格）。

---

## 1. 项目最小上下文（10 行内理解）

- **Sparkle（星火）**：AI 学习助手，三层架构 Flutter / Go Gateway / Python Engine + Postgres+pgvector / Redis。
- **SGW v2（Simulated Gray Window）**：预发布的合成灰度测试平台。用 LLM 模拟真实用户，闭环检测 Rule Y（Aurora Stage 16 推断式记忆写入）等策略的真实表现，替代"真人灰度"。
- **价值**：在不接触真实用户的情况下，以高保真方式发现策略/Prompt/Agent 的失败模式，驱动迭代收敛。
- **长期愿景**：SGW v2 要成为 Stage 17+（跨用户社交、问责系统）可复用的仿真环境基座（Gym-like `SimulationEnv`）。

---

## 2. 当前状态快照（"走到了哪一步"）

### 2.1 已完成（代码级闭环全部合拢）

**Phase 0–6 的 14 个 P0+P1 项 + 4 个 F 修复项全部通过验收。**

关键成品：
| 模块 | 文件 | 状态 |
|------|------|------|
| 状态机驱动对话弧线 | `scripts/sgw_v2/sim/state_machine.py` | ✅ 事件驱动，替代 turn_index%N |
| 三轴 persona 采样 | 同上（5 个独立 Beta 分布） | ✅ 按年龄阶段/承诺密度动态 |
| 表达约束验证器 | `scripts/sgw_v2/sim/expression_validator.py` | ✅ 被 SGW 主流程调用（P0-1 已修） |
| 诊断 Agent | `scripts/sgw_v2/meta/diagnostic_agent.py` | ✅ 规则+cross-slice+假设去重 |
| Meta Orchestrator | `scripts/sgw_v2/meta/meta_orchestrator.py` | ✅ z-test 判决 + 真 revert + authenticity 否决 |
| Meta Loop | `scripts/sgw_v2/meta/meta_loop.py` | ✅ subprocess 驱动 + 强制探索 |
| Authenticity Worker | `scripts/sgw/sgw_orchestrator.py` | ✅ 独立异步 + prompt `scripts/sgw/prompts/authenticity_audit_prompt.md` |
| Audit 上下文注入 | 同上 | ✅ 6 条最近对话（3 对）+ prompt `scripts/sgw/prompts/audit_system_prompt.md`【输入说明】 |
| Audit LLM 轮换 | 同上 `_rotate_audit_client` | ✅ `audit_providers` env |
| Parallel Runner | `scripts/sgw_v2/scenarios/parallel_runner.py` | ✅ 导入路径已修 |
| 对抗剧本迭代 | `scripts/sgw_v2/scenarios/adversarial_iteration.py` | ✅ 覆盖缺口+违规放大+剪枝 |
| 告警 | `scripts/sgw_v2/ops/alerting.py` | ✅ 默认规则 + stdout/file/webhook |
| 人类标定 | `scripts/sgw_v2/ops/calibration.py` | ✅ `human_labels` 表 + Cohen's kappa |
| SQLite 持久化 | `scripts/sgw_v2/storage/db.py` | ✅ 9 张表（含 experiments/iterations） |
| 场景规范 | `scripts/sgw_v2/scenarios/spec.py` | ✅ 5 个内置 + config_hash |

**F 修复项**（第二轮审计后）：
- F-1: `audit_system_prompt.md` 新增【输入说明】让 LLM 知道 `conversation_context` 字段含义
- F-2: `_revert_config` 真能恢复（`iterations` 表存 `pre_change_config`）
- F-3: 诊断假设去重（查询 `experiments` 表近 10 run）
- F-4: authenticity 一票否决写进 `_judge_outcome`

### 2.2 未完成（Step B — 运行时验收）

用户已明确：**以下三项需要连接真实 Sparkle 后端**，还没跑过。
1. 100 轮 meta loop 端到端运行
2. 2-scenario 并行执行
3. 人类盲测（校准 kappa）

### 2.3 用户最新的战略调整

用户在最后一轮明确不急着跑 Step B，而是要**先把 SGW v2 升级为完整的 RL 仿真环境**，再去跑。要求覆盖：
- 高保真输入（已有）
- 采集、分析、调优、正反馈、反过拟合、反局部最优

我已交付 **8 阶段升级方案**（下节详述）。**用户尚未表态是否执行，也未指定从哪阶段开始。你的第一件事是等用户明确意图，不要擅自动工。**

---

## 3. RL 仿真环境升级方案（已交付，等待执行决策）

**总时长估计：22–28 天。**

| 阶段 | 核心交付 | 关键依赖 |
|------|---------|---------|
| **0. MDP 形式化**（1d） | `docs/sgw/04_mdp_formalization.md` + `scripts/sgw_v2/rl/spec.py`。冻结 state/action/reward/guardrail 四件套 | 无 |
| **1. 采集层补完**（2–3d） | 新增 `rl_trajectories` / `failure_library` 表 + `scripts/sgw_v2/rl/features.py` feature extractor | 阶段 0 |
| **2. 分析层升级**（3–4d） | `analysis/changepoint.py`（CUSUM/BOCPD）+ `analysis/causal.py`（反事实 ITE）+ `analysis/pattern_miner.py`（LLM 模式挖掘） | 阶段 1 |
| **3. 策略三段式**（4–5d） | `rl/bandit.py`（Thompson Sampling）+ `rl/contextual_bandit.py`（LinUCB/Neural CB）+ `PolicyRouter`。规则→bandit→contextual 三级降级 | 阶段 1,2 |
| **4. 反过拟合 5 道防线**（2–3d） | Holdout scenario / Diversity bonus / 强制探索批次 / 温度退火 / 对抗 self-play | 阶段 3 |
| **5. 正反馈回路**（2d） | 四层嵌套循环：Inner/Middle/Outer/Meta。`meta/nested_loops.py` 协调 | 阶段 2,3,4 |
| **6. 可观测性**（2d） | `ops/dashboard.py` + 人类 veto CLI + `configs/reward_weights.yaml` 热更新 | 阶段 5 |
| **7. 分级 rollout**（6–8d） | 离线回放 → Shadow → Canary 10%/50%/100% → 全量 100-iter。gate 条件写进 `docs/sgw/05_rollout_gates.md` | 阶段 6 |
| **8. 沉淀泛化**（持续） | `scripts/sgw_v2/env/base.py` Gym-like `SimulationEnv` 抽象，Stage 17 可直接继承 | 阶段 7 |

**Reward 红线（不可动）**：
1. authenticity 是否决项（F-4 已实现，保留）
2. hard_violations 是绝对扣满
3. `diversity_bonus` 权重不低于 `soft_violation` 权重的 0.5×

**反过拟合硬约束**：
- 每 10 轮强制 1 轮 uniform random action
- 连续 3 次同向调整自动反向探索
- 单次调整幅度 ≤ 历史 std 的 2×
- 任何 action 先过 `failure_library` 黑名单

完整方案正文在上一轮对话里。如果用户丢失了上下文，让他去 `/Users/brsama/.claude/projects/-Users-brsama-code-GitHub-Sparkle-project--claude-worktrees-cool-mcnulty-1e3833/6f1f3558-30d5-46b3-9074-e06246b88bd4.jsonl` 翻最近一次 assistant 回复。

---

## 4. 必读文件清单（按优先级）

### 4.1 强制先读
1. `docs/sgw/00_scope.md` — SGW v2 边界
2. `docs/sgw/01_abstractions.md` — 核心抽象（697 行，最重要）
3. `docs/sgw/02_data_contracts.md` — 表 schema
4. `docs/sgw/03_acceptance_matrix.md` — 验收矩阵
5. `docs/sgw/04_mdp_formalization.md` — 上一任已创建（若存在）
6. `docs/sgw/05_rollout_gates.md` — 上一任已创建（若存在）

### 4.2 代码骨架（出问题最先查）
- `scripts/sgw/sgw_orchestrator.py` — 主 orchestrator（被 v2 增量改造）
- `scripts/sgw_v2/meta/meta_orchestrator.py` — 方案决策中枢
- `scripts/sgw_v2/meta/meta_loop.py` — 迭代驱动
- `scripts/sgw_v2/storage/db.py` — 所有表结构与查询

### 4.3 用户长期记忆（必看，决定你的行为）
- `~/.claude/projects/-Users-brsama-code-GitHub-Sparkle-project/memory/MEMORY.md` — 项目总索引
- `.../memory/feedback_work_delegation.md` — 用户的授权偏好
- `.../memory/feedback_audit_process.md` — 用户的审计流程要求（**非常重要**：断言之前必须 grep/check）
- `.../memory/roadmap_v2_stage16_23.md` — Aurora Stage 16+ 路线图
- `.../memory/gray_window_contextual_clause.md` — 灰度窗口条款

---

## 5. 用户工作偏好（必须遵守）

| 偏好 | 含义 | 违反后果 |
|------|------|---------|
| **阶段化执行** | 分多轮迭代，不要一口气交付 | 用户会抱怨"信息过载" |
| **审计先查** | 断言"缺失/存在"前必须 grep 或读文件 | 用户最讨厌误报 |
| **架构优先，不替他写代码** | 给规格、给方向；除非小任务或明确指令 | 侵占他的执行领域 |
| **中文回复** | 用户是中文使用者 | — |
| **承认不确定** | 不知道就说不知道，不编数据 | 信任崩盘 |
| **Aurora 治理规则** | Rule G-V 17 条已落地；新增规则按字母续编（Rule Y/Z/AA 已占） | 破坏治理框架 |

---

## 6. Red Lines（绝对不做）

1. ❌ **不要自作主张跑 Step B**（100-iter、并行、盲测）。它依赖真实 Sparkle 后端，没有用户授权不启动。
2. ❌ **不要修改 reward 红线**（authenticity 否决 / hard violations 绝对扣 / diversity 权重下限）。
3. ❌ **不要跳过 Aurora 治理**：任何涉及写路径（记忆、跨用户、技能）都要走 Rule Y/Z/AA。
4. ❌ **不要编造状态**。当前代码什么状态、跑没跑过，用 Bash/Grep/Read 查证后再断言。
5. ❌ **不要修改 generated 文件**（proto gen、sqlc gen、Alembic 已生成的 version）。
6. ❌ **不要主动 commit**，除非用户明确说"提交"。
7. ❌ **不要忽略 CLAUDE.md 里的 L3/L4 任务 plan 协议**（跨层任务必须先出 Analysis + Execution Plan）。

---

## 7. 接手第一小时行动清单

按顺序执行，不要跳步：

```
[1] 读本文件到这里 ✓
[2] 读 docs/sgw/00-05 全部 6 个设计文档
[3] 读 MEMORY.md + feedback_audit_process.md + feedback_work_delegation.md
[4] 列目录 scripts/sgw_v2/ 确认代码结构与本文一致
[5] 扫描 scripts/sgw_v2/meta/meta_orchestrator.py 的 _judge_outcome 和 _revert_config
    确认 F-2/F-4 已落地（而不是假说）
[6] 读 scripts/sgw/prompts/audit_system_prompt.md 确认 F-1【输入说明】段存在
[7] 读 scripts/sgw_v2/meta/diagnostic_agent.py 的 diagnose() 开头，
    确认 F-3 experiments 表查询去重逻辑存在
[8] 列 scripts/sgw_v2/rl/ 目录，若不存在说明阶段 0-3 没开工
[9] 等用户发话，不要主动动工
```

**当用户第一条消息到来时**：
- 如果是"继续 RL 方案"类：确认他希望从哪阶段起步，推荐从 **阶段 0 MDP 形式化** 开始（1 天，风险最低，为后面所有阶段立地基）
- 如果是"先跑 Step B"类：提醒他之前自己说过要先把 RL 环境建好，让他确认是否改变主意
- 如果是新需求：按用户工作偏好处理，不要强拉回 SGW 话题

---

## 8. 你手上的钩子 / 可用资源

- **Worktree**: 当前在 `cool-mcnulty-1e3833` 分支。主分支是 "层级state系统"。
- **Memory 文件夹**: `~/.claude/projects/-Users-brsama-code-GitHub-Sparkle-project/memory/` — 历史所有决策都在这。新写的 memo 也放这里。
- **Transcript**: 上一任完整对话在 `~/.claude/projects/-Users-brsama-code-GitHub-Sparkle-project--claude-worktrees-cool-mcnulty-1e3833/6f1f3558-30d5-46b3-9074-e06246b88bd4.jsonl`，需要原话时去查。
- **Aurora 规则目录**: 目前冻结到 Rule V（Stage 12）+ Rule Y（Stage 16）+ Rule Z（Stage 17）+ Rule AA（Stage 20 规划中）。下一条新规则用 Rule AB。

---

## 9. 沟通模板（给用户回复时可直接套）

**当你完成一个阶段**：
```
## ✅ 阶段 N 完成
**交付**: [文件/模块清单]
**验收**: [具体量化指标，不是"看起来没问题"]
**遗留**: [发现但没改的问题，列清楚]

## 🎯 下一步建议
[基于当前成果，推荐进入哪阶段，附理由]
```

**当你发现问题需要回退**：
```
## ⚠️ 发现阻塞
**问题**: [具体症状 + 文件:行号]
**根因**: [查证后的结论]
**影响**: [阻塞哪些阶段]
**建议**: [两条以上可选路径，让用户选]
```

**当用户要求你审计**：
参照 `feedback_audit_process.md`。先 grep/read，再断言。输出分 `[P0]/[P1]/[P2]` 三档，每档给文件路径+行号+修复建议。

---

## 10. 最后：交接完整性自检

在你开始工作前，回答自己这三个问题：
1. 用户现在要我做什么？（如果答案是"我猜"→ 先问用户）
2. 我即将修改的东西，上一任是否已经做过？（不确定就 grep）
3. 我的方案是否覆盖了 Aurora 治理 + 7 阶段成长环 + Rule Y/Z 审查？（少一条就回去补）

全答 yes 再动手。答 no 就停下来问用户或查文件。

---

**上一任签名**：Claude Opus 4.5 @ 2026-04-21
**关键词记忆锚**：`SGW_V2_RL_ENV_HANDOVER` — 新 Claude 在任何迷失时搜索这个词可定位本文。
