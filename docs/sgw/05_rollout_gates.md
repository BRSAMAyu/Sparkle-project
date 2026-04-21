# SGW v2 Rollout Gates

> Version: 1.0 | Date: 2026-04-21 | Status: FROZEN
> Defines the four-stage rollout process for RL policy changes to production.

---

## 1. Rollout Stages

### Stage 1: Offline Validation

**触发**：策略产生一个 Action（参数变更）

**验证内容**：
1. `validate_action()` — 参数范围、数量 ≤ 3、非保护参数
2. Guardrail 1 — config_hash 新颖性
3. Guardrail 2 — 方向历史检查
4. Guardrail 3 — 幅度限制（15% max range）

**通过条件**：所有检查无 violation

**代码位置**：`rl/spec.py::validate_action()` + `rl/spec.py::check_*()`

### Stage 2: Shadow Run

**触发**：Offline Validation 通过后

**运行方式**：
- 使用新配置运行一个完整 SGW run（8-18h）
- 不替换当前生产配置
- 结果写入独立的 run_id，标记 `shadow = true`

**评估内容**：
1. `_judge_outcome(before, after)` — 统计显著性
2. `compute_reward(before, after)` — 奖励信号
3. 无 hard violation
4. authenticity 无显著回退

**通过条件**：outcome ∈ {improved_sig, improved_nonsig, neutral}

### Stage 3: Canary Run

**触发**：Shadow Run 通过后

**运行方式**：
- 在 10% 的 session 上使用新配置
- 90% 使用当前配置
- 同时运行，比较实时指标

**评估内容**：
1. A/B 比较：canary 组 vs control 组
2. 无 hard violation
3. soft_violation_rate 不超过 control 组的 1.2 倍
4. authenticity_mean 不低于 control 组的 0.95 倍

**通过条件**：所有 A/B 指标达标，持续至少 1 小时

### Stage 4: Full Rollout

**触发**：Canary Run 通过后

**运行方式**：
- 100% 使用新配置
- 持续监控 24 小时
- 设置回滚触发条件

**回滚触发**：
- hard_violations > 0 → 立即回滚
- soft_violation_rate > shadow_run_rate * 1.5 → 立即回滚
- authenticity_mean < shadow_run_mean * 0.9 → 立即回滚

---

## 2. Emergency Rollback

任何阶段都可以通过以下方式触发紧急回滚：
1. `MetaOrchestrator._revert_config(iteration_id)` — 恢复到迭代前配置
2. 手动 CLI：`python -m scripts.sgw_v2.meta.cli rollback --iteration-id <id>`
3. `config_hash` 不匹配时自动告警

---

## 3. Human Approval Gates

以下变更需要人类审批，即使通过了所有自动 gate：

| 变更类型 | 审批级别 |
|----------|---------|
| 首次使用新 PolicyStage | 架构师确认 |
| 连续 3 次 regressed_sig | 架构师审查 |
| Holdout overfitting 检测 | 需要重新校准 |
| `PROTECTED_PARAMETERS` 中的参数 | 产品负责人确认 |
| Episode 未收敛就终止 | 需要诊断报告 |

---

## 4. Gate 实现映射

| Gate | 代码位置 |
|------|---------|
| Offline Validation | `rl/spec.py::validate_action()` |
| Guardrail 1-4 | `rl/spec.py::check_*()` + `should_explore()` |
| Shadow Run | `meta/meta_loop.py::_run_sgw_subprocess()` |
| Outcome Judge | `meta/meta_orchestrator.py::_judge_outcome()` |
| Reward Computation | `rl/reward.py::compute_reward()` |
| Rollback | `meta/meta_orchestrator.py::_revert_config()` |
| Canary Logic | `rl/rollout.py::RolloutGate` (Phase 7 新增) |

---

## 5. 数据流

```
Action from Policy
    │
    ├─→ Offline Validation (sync, <1s)
    │     FAIL → reject, log, try next action
    │     PASS ↓
    │
    ├─→ Shadow Run (async, 8-18h)
    │     FAIL → reject, diagnose, update policy
    │     PASS ↓
    │
    ├─→ Canary Run (async, 1-4h, 10% traffic)
    │     FAIL → reject, revert to current config
    │     PASS ↓
    │
    └─→ Full Rollout (async, 24h monitoring)
          FAIL → rollback to pre-change config
          PASS → new config becomes current
```
