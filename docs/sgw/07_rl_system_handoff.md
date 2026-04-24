# SGW v2 RL System Handoff — Phase II 入场凭证

> Version: 1.2 | Date: 2026-04-24 | Status: FROZEN（四个核心缺陷已修复并测试验证）
> 承接：`docs/sgw/HANDOVER.md` §3 阶段 0–8、`docs/sgw/04_mdp_formalization.md`、`docs/sgw/05_rollout_gates.md`、`docs/product/SPARKLE_AURORA_PHASE_I_EXIT_GATE_2026-04-22.md`、`docs/product/SPARKLE_AURORA_PHASE_II_RL_OPTIMIZATION_KICKOFF_2026-04-22.md`
> 目的：作为 Phase II 真跑的唯一入场凭证，锁定 CLI 契约、门槛指标、回滚红线、失败模式回流口径。Phase II 实际执行前必须把本文件收到 `FROZEN`。

---

## 1. Phase II 定位

Phase II 的唯一主题：**用 SGW v2 的 RL 模式持续调优已打通的 Stage 22–40 回路，而不是继续扩张新功能面。**

- Phase I Exit Gate 已签字（2026-04-22，建议 YES，ready with exception）。SGW dogfood 判定 `CONDITIONAL` 的唯一原因 = 后端栈未起真跑；其余治理全绿。
- 数据利用基线由 Stage 22 `WS-BR-PROMPT-VERIFY` 审计锁定到 ~82% 覆盖率。Phase II **不做打通**，只做**精调 + 观测多轮真实对话下的行为偏差**。
- 唯一允许新增的产出：policy snapshot、arm stats、holdout/diversity/exploration 指标、RL overfitting 观测面，以及 dashboard KPI 三件套。

## 2. 指标与通过线

| 层级 | 指标 | 口径 | Phase II 首轮通过线 |
|---|---|---|---|
| 顶线 KPI | `soft_violation_rate` | `population_stats`，RunDB 聚合 | 基线 0.08 → **≤ 0.05** |
| 顶线 KPI | `authenticity_mean` | Authenticity Worker z-test 均值 | 基线 0.78 → **≥ 0.83** |
| 顶线 KPI | `session_completion_rate` | Session FSM 终止态统计 | 基线 0.72 → **≥ 0.80** |
| 成功定义 | Total reward (Σ r_t) | `reward.compute_reward()` 累加 | 20 iter 内 **≥ Phase I 基线 × 1.15** |
| 反过拟合 | `holdout_reward` / `in_sample_reward` | `overfitting.HoldoutGuard` | **≥ 0.85**（否则判定过拟合并回退） |
| 反过拟合 | `diversity_bonus` | `overfitting.DiversityMetrics` | `unique_persona_axes/40 × unique_behavior_classes/7 ≥ 0.40` |

Phase II 首轮 = `default` recipe × 20 iteration × `rl_mode=rl`。未达通过线不阻断 Phase II 延续，但必须在 dashboard 上打红并进入 §6 诊断循环。

## 3. CLI 契约（LOCKED）

Phase I Exit Gate `f6798938` 已补完三旗，入口在 `scripts/sgw_v2/meta/meta_loop.py:335-351`。以下为真跑标准用法：

```bash
python -m scripts.sgw_v2.meta.meta_loop \
  --db-path                 artifacts/sgw/sgw_runs.db \
  --persona-library         scripts/sgw/persona_library.json \
  --adversarial-playbook    scripts/sgw/adversarial_playbook.json \
  --max-iterations          20 \
  --exploration-every-n     5 \
  --convergence-window      5 \
  --seed                    42 \
  --rl-mode                 rl        # off | shadow | rl
  --rl-recipe               default   # default | compliance_focus | authenticity_focus | fast_iteration | stress_test
  --dashboard                          # 每轮 stdout 打一行 dashboard 摘要
```

**三模式语义（`meta_loop.py:50` + §5 rollout gate）**：
- `off`：纯走基线配置，不调参，不记录 policy 决策。用于基线复跑与对照组。
- `shadow`：策略照常推演并写 `iterations` 表，但**不**落地到 SGW 实际配置；用于 Stage 2 Shadow Run。
- `rl`：策略决策直接落地为下一轮 SGW 配置，进入完整 RL 循环；用于 Stage 3/4 Canary/Full Rollout。

**不可绕过约束**：
- `--rl-mode` 必须显式传入；省略默认 `rl`，但 CI 守卫要求 Phase II 所有脚本都显式声明。
- `--rl-recipe` 可选，但 `authenticity_focus` / `stress_test` recipe 在 Phase II 首轮需要架构师额外签字。
- `--dashboard` 在生产真跑时必须开启，用于向 SRE 暴露 KPI 三件套。

## 4. MDP 六要素与四条护栏（引用锁）

全部事实来源锁定在 `docs/sgw/04_mdp_formalization.md`，本文件不复述；Phase II 实现禁止改动任一锁定值。

- State：`(run_context, population_stats, failure_signal)`，14 维（5 连续 + 5 离散 + 4 类别）。
- Action：`dict[str, float]` 单次调整 ≤ 3 参数；保护参数列表见 04 §1.2。
- Reward：默认权重 `w_soft=0.30, w_auth=0.35, w_hard=0.20, w_session=0.10, w_diversity=0.05`；一票否决 hard violation → r_t=−1.0，authenticity 显著回退 → r_t=−0.8；归一化 `tanh(r_t / 0.3)`。
- Transition：subprocess 驱动 `sgw_orchestrator.py`，单次 state transition 8–18 小时。
- Policy：`PolicyRouter`（`rl/policy.py:454`）三段递进 Rule → Thompson Sampling Bandit → LinUCB，切换条件见 04 §1.5。
- Episode：max 20 iter，连续 5 neutral/improved_sig 收敛，连续 2 regressed_sig 强制中止。
- 四条护栏：config_hash 新颖性、连续同方向 ≤ 3、幅度 ≤ 参数范围 15%、每 10 iter 强制 1 次随机探索。

## 5. Rollout 门（引用锁 + Phase II 首轮具体化）

四阶段契约锁定在 `docs/sgw/05_rollout_gates.md` 与 `rl/rollout.RolloutGate`（`scripts/sgw_v2/rl/rollout.py:36`）。Phase II 首轮的具体通过条件：

| Stage | 入口 | 通过条件 | 失败动作 |
|---|---|---|---|
| 1. Offline Validation | `rl/spec.py::validate_action` + guardrail × 4 | 0 violation | 拒绝 action，重新采样 |
| 2. Shadow Run | `--rl-mode shadow` × 1 完整 run（≤ 18h） | outcome ∈ {improved_sig, improved_nonsig, neutral} 且 hard_violations=0 | `_revert_config(iteration_id)` + 回到 Stage 1 |
| 3. Canary Run | `--rl-mode rl` × 10% session 与 control 组 A/B，持续 ≥ 1h | `canary.soft_violation_rate ≤ 1.2 × control`、`canary.authenticity_mean ≥ 0.95 × control`、hard=0 | Emergency Rollback + Alert |
| 4. Full Rollout | `--rl-mode rl` × 100% session × 24h 监控 | hard=0、`soft_rate ≤ 1.5 × shadow`、`auth ≥ 0.9 × shadow` | 立即回滚 |

**紧急回滚三路径**：`MetaOrchestrator._revert_config(iteration_id)`、CLI `python -m scripts.sgw_v2.meta.cli rollback --iteration-id <id>`、`config_hash` 不一致自动告警。

## 6. 失败模式回流到三专家循环

Phase II 的独特责任：**RL 迭代暴露的每一个系统行为缺陷都必须回流到 `.claude/workflow/` 三专家循环，而不是内部消化。**

回流契约：

1. **诊断 Agent 产出**：`scripts/sgw_v2/meta/diagnostic_agent.py::diagnose()` 每轮产出 `active_hypotheses` 列表，存 `experiments` 表。
2. **自动 issue 化**：凡命中以下条件之一，由 `ops/alerting.py` 自动在 `.claude/workflow/issues/` 生成 ISSUE 草案（ID 格式 `ISSUE-YYYYMMDD-NNN`，并追加到 `.claude/workflow/state.json` stats）：
   - `critical_alerts > 0`
   - 同一 hypothesis 连续 3 iter 未消除
   - `authenticity z-test` 显著回退（veto 触发）
   - Shadow/Canary 任一门 FAIL
3. **切片归属**：issue front matter 必须填 `slice` 字段（引用 `.claude/workflow/coverage_matrix.md` 中的切片编号）。RL 参数调整本身不是 issue；issue 指向的是被 RL 暴露的业务/工程缺陷。
4. **优先级映射**：hard violation → **P0**；authenticity 显著回退 → **P1**；soft violation 累积偏差 → **P2**；diversity 坍缩 → **P3**。
5. **Fixer 处理完毕后**：issue closed 时必须反向 ping `meta_orchestrator.py::_revert_config` 解除相关 arm 的 β penalty，让策略重新评估该区域。

**反向禁令**：三专家循环的 fixer **禁止**直接改动 `reward_weights.yaml`、MDP 保护参数、Guardrail 常量；这三类修改必须走架构师签字。

## 7. Memory Write NON-LIVE 的显式边界

Phase I Exit Gate 结论：**Memory Write 保持非 live**（`SPARKLE_MEMORY_INFERRED_WRITE_ENABLED=False`）。

Phase II 期间该决定继续生效，解除条件三选三（不可减项）：

1. `docs/audit/deep_audit_2026-04-22_0130_memory_service.md` 中的两个 P0（写入禁用 + 读路径字段丢失）都被新的 FIXED 条目关闭，并通过 Rule Y 四要素验证。
2. 单独产出 `stage39_memory_write_readiness_report.md` 并附 architect 签字。
3. SGW v2 在 `--rl-mode shadow` 下跑 ≥ 5 iter、authenticity 不低于基线、hard violations=0。

**在解除之前，Phase II RL 策略不得观测、不得写入 Memory Write Lane 的 `inferred_extraction` 字段**；相关 hypothesis 若命中该路径必须降级为 shadow-only 诊断。

## 8. Stage 22–40 回路在 RL 下的观测口径

以下八条回路是 Phase II RL 的主要"被调优对象"。每条都明确 state 观测通道与禁改点。

| 回路 | 被调优的参数边界 | State 观测通道 | 禁改点 |
|---|---|---|---|
| error → replan（Stage 22/34） | `error_replan_bridge` 触发 cohort 权重 | `failure_signal.active_hypotheses` | `TRIGGERING_ERROR_TYPES ≥ 6` 不得被削减 |
| achievement → AI 画像（Stage 22） | prompt 注入长度 budget | `population_stats.authenticity_mean` | 单向只读，禁止 AI 反写成就 |
| calendar → 上下文（Stage 22/40） | 读授权开启时的注入密度 | prompt 覆盖率遥测 | 禁止 AI 写日历 |
| seed → outcome（Stage 22） | 7d 采纳窗口长度、质量分衰减 | `session_completion_rate` | 用户显式撤回路径不得被策略跳过 |
| Social → Router（Stage 33） | Router 分支读取条件（Rule Z 约束） | routing_decision_log | 跨用户隐私边界禁止放宽 |
| SRL Phase → Router+Prompt（Stage 33） | Phase 判定阈值 | routing_decision_log | `SRLPhaseTracker` 与 `ScaffoldingFSM` 不得合并 |
| Working Memory → Prompt（Stage 33） | WM TTL、session 边界 | WM hit ratio | Redis-only、session-scoped 不得放宽为持久化 |
| Metacognition Hint → Router Shadow（Stage 35） | shadow path 采样率 | routing_decision_log shadow slot | 不得升级为 live 分支（需独立 Stage） |

## 9. 运行前置条件（真跑前 checklist）

架构师签字本文件后，Phase II 首轮真跑前必须：

```
[ ] docker compose up -d sparkle_db redis minio
[ ] make env-check && make local-signoff-preflight
[ ] make grpc-server                    # :50051
[ ] make gateway-dev                    # :8080
[ ] curl localhost:8080/api/v1/health   # 200
[ ] cd backend && python scripts/seed_demo_user_enhanced.py
[ ] make smoke
[ ] python -m scripts.sgw_v2.meta.meta_loop --rl-mode off ...   # 跑一次基线确认链路通
[ ] python -m scripts.sgw_v2.meta.meta_loop --rl-mode shadow ... --max-iterations 3
[ ] 架构师审 shadow 输出 → 签字允许 Stage 3
[ ] python -m scripts.sgw_v2.meta.meta_loop --rl-mode rl ...    # 首轮 20 iter
```

## 10. 产物与落盘路径

| 产物 | 路径 | 责任人 |
|---|---|---|
| RunDB | `artifacts/sgw/sgw_runs.db` | meta_loop |
| rl_trajectories | RunDB `rl_trajectories` 表 | PolicyRouter |
| iterations | RunDB `iterations` 表（含 `pre_change_config`，支持 F-2 真 revert） | meta_orchestrator |
| dashboard | stdout + `artifacts/sgw/dashboard_<ts>.jsonl` | `--dashboard` |
| policy snapshot | `artifacts/sgw/policy/<run_id>.json` | Phase II 首轮补 |
| arm stats | RunDB `bandit_arms` 表 | ThompsonSamplingBandit |
| holdout | `artifacts/sgw/holdout/<run_id>.json` | HoldoutGuard |

policy snapshot 与 arm stats 的结构化导出是 Phase II Backlog 第 3 项，本文件锁定路径，实现由 Codex 在首周补齐。

## 11. Freeze 条件

本文件从 `DRAFT` 升级为 `FROZEN` 需要：

1. 架构师（Opus 4.7）审读并签字
2. 用户（BRSAMA）口头/文本确认"可以作为 Phase II 入场凭证"
3. §9 checklist 首项 `docker compose up -d` 至 `make smoke` 全绿
4. Git commit with message `docs(sgw): freeze RL system handoff v1.0`

在 FROZEN 之前，`--rl-mode rl` 不得在真跑环境触发；只允许 `off` / `shadow` 两模式作为诊断用途。

---

## 修订记录

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.0 DRAFT | 2026-04-24 | 架构师初稿，基于实证落盘 |
| 1.1 FROZEN | 2026-04-24 | 三个核心缺陷修复 + 测试验证后升至 FROZEN |
| 1.2 FROZEN | 2026-04-24 | 补修 meta_loop 迭代评估时序缺陷，避免 run 与自身比较 |

### v1.2 修复内容（已验证，31/31 tests pass）

| 缺陷 | 根因 | 修复位置 |
|---|---|---|
| DB 路径断层（RL 循环完全失效） | orchestrator 写 `checkpoint_path.parent/sgw_runs.db`，meta_loop 读 `--db-path`，两个不同文件 → `db.latest_run_id()` 永远 None | `sgw_orchestrator.py`: 加 `--db-path` CLI arg + `OrchestratorConfig.db_path`；`meta_loop.py`: `_run_sgw_subprocess` 传 `--db-path shared_db_path` |
| RL 动态参数不传（调优零效果） | `_run_sgw_subprocess` 只传 5 个 CLI arg，`soft_violation_threshold` 等 8 个可调参数被忽略 | `meta_loop.py`: 加 `_ENV_MAP` + `subprocess_env` 注入完整 env vars |
| `cli rollback` 子命令缺失 | cli.py 只有 diagnose/plan/iterate/history | `cli.py`: 加 `rollback --iteration-id` 子命令 |
| policy snapshot 未落盘 | Phase II Backlog #3 | `environment.py`: 加 `PolicyZoo.save_config_snapshot()`；`meta_loop.py`: significant improvement 时自动保存 |
| subprocess timeout 硬编码 1h | full run 8–18h 会被提前 kill | `meta_loop.py`: `timeout = wall_clock_hours * 3600 + 600` |
| iteration 自比较（RL adopt/rollback 永远失真） | `meta_loop` 在创建 iteration 后立刻用同一个 `latest_run_id` 调 `evaluate_iteration()`，结果变成“run 对自己” | `meta_loop.py`: 先评估上一轮 `pending iteration`，再为下一轮创建新计划；`meta_orchestrator.py`: 加 `get_latest_pending_iteration()` / `set_iteration_outcome()`；`test_rl_scaffolding.py`: 加两条回归测试 |

**对齐锚点**：`SGW_V2_RL_PHASE_II_HANDOFF`
**下一步**：§9 checklist → 首轮 `--rl-mode off` 基线复跑
