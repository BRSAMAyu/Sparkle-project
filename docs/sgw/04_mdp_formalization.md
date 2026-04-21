# SGW v2 MDP Formalization

> Version: 1.0 | Date: 2026-04-21 | Status: FROZEN
> 定义 SGW v2 作为 MDP (Markov Decision Process) 的六个要素和四条护栏。
> 所有后续 Phase 的代码必须遵守本文档中的定义。

---

## 1. MDP 六要素定义

### 1.1 State s_t（系统状态）

系统在时刻 t 的完整可观测状态。由三个子空间组成：

```
s_t = (run_context, population_stats, failure_signal)
```

| 子空间 | 维度 | 类型 | 说明 |
|--------|------|------|------|
| **run_context** | | | 当前 run 的元信息 |
| ├ scenario_id | str | 场景标识 (e.g. "stage_16_rule_y") |
| ├ config_hash | str | 当前配置的 SHA-256 |
| ├ iteration_number | int | 当前迭代序号 (0-indexed) |
| ├ turns_completed | int | 已完成 turn 数 |
| └ sessions_completed | int | 已完成 session 数 |
| **population_stats** | | | 当前 run 的聚合指标 |
| ├ soft_violation_rate | float ∈ [0,1] | 软违规率 |
| ├ hard_violations | int | 硬违规数 |
| ├ authenticity_mean | float ∈ [0,1] | 真实性评分均值 |
| ├ authenticity_failure_rate | float ∈ [0,1] | 真实性审计失败率 |
| ├ session_completion_rate | float ∈ [0,1] | session 完成率 |
| └ avg_turns_per_session | float | 平均每 session turn 数 |
| **failure_signal** | | | 最新诊断结果 |
| ├ active_hypotheses | list[str] | 活跃假设 ID 列表 |
| ├ critical_alerts | int | 未消除的 critical 告警数 |
| └ last_outcome | str | 上次迭代结果 (improved_sig/nonsig, regressed_sig/nonsig, neutral) |

**状态空间特性**：
- 连续维度：soft_violation_rate, authenticity_mean, authenticity_failure_rate, session_completion_rate, avg_turns_per_session (5 维连续)
- 离散维度：hard_violations, turns_completed, sessions_completed, iteration_number, critical_alerts (5 维离散计数)
- 类别维度：scenario_id, config_hash, last_outcome, active_hypotheses (4 维类别)

### 1.2 Action a_t（策略动作）

策略可以在一次迭代中执行的动作。定义为对可调参数的增量调整：

```python
Action = dict[str, float]  # {parameter_name: delta_value}
```

| 参数 | 类型 | 调整范围 | 步长约束 |
|------|------|---------|---------|
| `soft_violation_threshold` | float | [0.80, 0.95] | ±0.05 |
| `audit_sample_rate` | float | [0.10, 0.50] | ±0.05 |
| `authenticity_sample_rate` | float | [0.10, 0.50] | ±0.10 |
| `turn_target` | int | [8, 20] | ±2 |
| `claude_timeout_seconds` | int | [30, 120] | ±15 |
| `claude_failure_backoff_seconds` | int | [10, 120] | ±10 |
| `expression_validation_retries` | int | [0, 5] | ±1 |
| `max_history_pairs` | int | [2, 10] | ±2 |
| `session_turn_slice` | int | [1, 3] | ±1 |

**不可自动调整的参数**（需要人类审批）：
- `websocket_url`, `api_base_url` — 基础设施端点
- `llm_provider`, `api_model` — 模型选择
- `random_seed` — 可复现性种子
- `wall_clock_hours`, `min_sessions`, `min_turns` — 运行级参数
- `soft_violation_rate_limit` — 验收门限（变更需人类确认）
- `authenticity_threshold` — 验收门限

**动作约束**：
- 单次迭代最多调整 3 个参数（避免无法归因的复合变更）
- 每个参数单次只能向一个方向调整（不能同时加减）
- 连续 3 次迭代不得对同一参数施加同方向调整（防止单调漂移）

### 1.3 Reward r_t（奖励信号）

奖励函数是 SGW RL 的核心。定义为多维加权和：

```
r_t = w_soft * Δ(-soft_violation_rate)
    + w_auth * Δ(authenticity_mean)
    + w_hard * (-hard_violations_delta * 10)
    + w_session * Δ(session_completion_rate)
    + w_diversity * diversity_bonus
```

| 权重 | 符号 | 默认值 | 说明 |
|------|------|--------|------|
| `w_soft` | w₁ | 0.30 | 软违规率改善的权重 |
| `w_auth` | w₂ | 0.35 | 真实性评分改善的权重 |
| `w_hard` | w₃ | 0.20 | 硬违规惩罚的权重 |
| `w_session` | w₄ | 0.10 | session 完成率权重 |
| `w_diversity` | w₅ | 0.05 | 多样性奖励权重 |

**Δ (delta) 定义**：
- `Δ(metric) = metric_after - metric_before`
- 对于"越小越好"的指标（soft_violation_rate），取负号使其改善为正奖励
- `hard_violations_delta` 为正时表示恶化，乘以 10 放大惩罚

**diversity_bonus 定义**：
```
diversity_bonus = min(1.0, unique_persona_axes / 40)
                * min(1.0, unique_behavior_classes / 7)
```
确保策略不会坍缩到只测试少数 persona/behavior 组合。

**一票否决**：
- `hard_violations_delta > 0` → r_t = -1.0（无论其他维度如何）
- `authenticity z-test significant regression` → r_t = -0.8
- 与 `_judge_outcome` 中的一票否决逻辑一致

**奖励归一化**：
- r_t ∈ [-1.0, 1.0]
- 使用 sigmoid-like 的归一化确保极端值不会主导
- `r_normalized = tanh(r_t / reward_scale)`，reward_scale = 0.3

### 1.4 Transition P(s_{t+1} | s_t, a_t)（状态转移）

SGW 的状态转移不是确定性的——同一 action 在不同的 LLM 行为下产生不同的 next state。

**转移模型**：
1. **Action 执行**：将参数变更应用到配置，生成新的 config_hash
2. **Run 执行**：用新配置运行一个完整的 SGW run（subprocess）
3. **观测收集**：从 SQLite 读取 run 结果，构建 s_{t+1}

**转移特性**：
- 非马尔可夫性：LLM 的 temperature 导致非确定性
- 延迟观测：一个完整的 state transition 需要 8-18 小时（一次完整 run）
- 部分可观测：审计采样率 < 100%，真实指标是估计值

**工程实现**：
- 通过 `meta_loop.py` 的 subprocess 机制实现转移
- 通过 `RunDB.run_summary()` 读取观测
- 通过 `config_hash` 保证 action 的确定性应用

### 1.5 Policy π(a_t | s_t)（策略）

策略选择下一个参数调整。三阶段递进：

**Stage 1: Rule-based π_rule**
- 确定性规则：`_ADJUSTMENT_RULES` 中定义的参数调整映射
- 基于诊断假设的规则触发
- 无探索，完全利用已知知识

**Stage 2: Bandit π_bandit (Thompson Sampling)**
- 每个 (parameter, direction) 组合 = 一个 arm
- Beta(α, β) 后验，每次迭代后更新
- α 初始值 = 规则的推荐次数 + 1
- β 初始值 = 规则的失败次数 + 1
- 自然探索：不确定性高的 arm 有更高的采样概率

**Stage 3: Contextual Bandit π_context (LinUCB)**
- State s_t 作为 context vector
- 每个 arm 独立的线性模型：r_t = θ_arm^T * φ(s_t) + ε
- UCB 项提供探索：a_t = argmax(θ_arm^T * φ(s_t) + α * √(φ(s_t)^T * A_arm^{-1} * φ(s_t)))
- 适用于区分"什么状态下用什么参数调整"

**策略切换条件**：
- Rule → Bandit：完成 ≥ 20 次迭代，rule-based 成功率 < 60%
- Bandit → Contextual：完成 ≥ 50 次迭代，≥ 3 个 state cluster 被识别

### 1.6 Episode（回合定义）

一个 Episode = 一组连续迭代直到终止条件满足。

**终止条件**（满足任一即结束）：
1. **Convergence**：连续 N 次迭代 outcome = "neutral" 或 "improved_sig"（N = convergence_window, 默认 5）
2. **Budget exhausted**：迭代次数达到 max_iterations（默认 20）
3. **Critical regression**：连续 2 次 "regressed_sig"（策略严重失效，需要人类介入）
4. **Hard violation**：任何一次 run 产生 hard violation（立即终止，需要人工审查）

**Episode 度量**：
- Total reward: Σ r_t
- Final metrics vs initial metrics
- Iterations used
- Exploration vs exploitation ratio

---

## 2. 四条护栏（Guardrails）

### Guardrail 1: config_hash 碰撞检查

**规则**：新配置的 config_hash 不得与最近 10 次迭代中的任何配置重复。

**理由**：防止策略陷入"改了又改回来"的循环。

**实现**：
```python
def check_config_novelty(new_config: dict, recent_hashes: list[str]) -> bool:
    new_hash = compute_config_hash(new_config)
    return new_hash not in recent_hashes
```

**违反时**：拒绝该 action，从策略中采样下一个 action。

### Guardrail 2: 连续同方向触发

**规则**：同一参数不得在连续 3 次迭代中被同方向调整。

**理由**：防止单调漂移。如果 3 次同方向调整仍不能改善指标，说明该参数不是正确的调节点。

**实现**：
```python
def check_direction_history(
    parameter: str,
    direction: float,  # +1 or -1
    history: list[dict],
    window: int = 3,
) -> bool:
    recent = [h for h in history[-window:] if parameter in h.get("changes", {})]
    if len(recent) >= window:
        directions = [sign(h["changes"][parameter]) for h in recent]
        return not all(d == direction for d in directions)
    return True  # OK
```

**违反时**：跳过该参数，选择次优参数。

### Guardrail 3: 幅度限制（Amplitude Clamp）

**规则**：单次参数调整幅度不超过该参数最大范围的 15%。

**理由**：避免过大的跳跃导致不可预测的行为。

**参数幅度表**：

| 参数 | 最大范围 | 15% 限制 |
|------|---------|---------|
| soft_violation_threshold | 0.15 (0.80-0.95) | ±0.0225 ≈ ±0.02 |
| audit_sample_rate | 0.40 (0.10-0.50) | ±0.06 ≈ ±0.05 |
| authenticity_sample_rate | 0.40 (0.10-0.50) | ±0.06 ≈ ±0.05 |
| turn_target | 12 (8-20) | ±1.8 ≈ ±2 |
| claude_timeout_seconds | 90 (30-120) | ±13.5 ≈ ±13 |
| expression_validation_retries | 5 (0-5) | ±0.75 ≈ ±1 |

**实现**：
```python
AMPLITUDE_LIMITS = {
    "soft_violation_threshold": (0.80, 0.95, 0.0225),
    "audit_sample_rate": (0.10, 0.50, 0.06),
    ...
}

def clamp_amplitude(param: str, current: float, proposed: float) -> float:
    lo, hi, max_step = AMPLITUDE_LIMITS[param]
    delta = proposed - current
    delta = max(-max_step, min(max_step, delta))
    return max(lo, min(hi, current + delta))
```

### Guardrail 4: 强制随机探索

**规则**：每 10 次迭代，强制插入 1 次随机探索（从可调参数中随机选 1-2 个，随机方向，随机幅度）。

**理由**：避免策略完全利用已知模式而错过未知的最优区域。

**实现**：
```python
def should_explore(iteration_number: int, explore_every: int = 10) -> bool:
    return iteration_number > 0 and iteration_number % explore_every == 0
```

**探索动作**：
- 从 9 个可调参数中随机选择 1-2 个
- 方向从 {-1, +1} 中均匀随机
- 幅度在该参数步长约束范围内均匀随机
- 不触发 Guardrail 2（强制探索豁免方向检查）

---

## 3. 可调参数完整清单

| # | 参数名 | 类型 | 范围 | 默认值 | 步长 | Bandit arm? |
|---|--------|------|------|--------|------|-------------|
| 1 | soft_violation_threshold | float | [0.80, 0.95] | 0.85 | ±0.05 | yes |
| 2 | audit_sample_rate | float | [0.10, 0.50] | 0.25 | ±0.05 | yes |
| 3 | authenticity_sample_rate | float | [0.10, 0.50] | 0.20 | ±0.10 | yes |
| 4 | turn_target | int | [8, 20] | 12 | ±2 | yes |
| 5 | claude_timeout_seconds | int | [30, 120] | 45 | ±15 | yes |
| 6 | claude_failure_backoff_seconds | int | [10, 120] | 30 | ±10 | yes |
| 7 | expression_validation_retries | int | [0, 5] | 2 | ±1 | yes |
| 8 | max_history_pairs | int | [2, 10] | 6 | ±2 | yes |
| 9 | session_turn_slice | int | [1, 3] | 1 | ±1 | yes |

Bandit arms = 9 parameters × 2 directions = 18 arms。

---

## 4. 与现有代码的映射

| MDP 概念 | 现有实现 | Phase 代码位置 |
|----------|---------|---------------|
| State s_t | `RunDB.run_summary()` | `rl/features.py` — StateVector |
| Action a_t | `ExperimentPlanner._ADJUSTMENT_RULES` | `rl/spec.py` — ActionSpec |
| Reward r_t | `MetaOrchestrator._judge_outcome()` | `rl/reward.py` |
| Transition P | `meta_loop.py` subprocess | 现有，无需改动 |
| Policy π_rule | `ExperimentPlanner.plan()` | `rl/policy.py` |
| Episode | `meta_loop.py run_meta_loop()` | 现有，增强终止条件 |
| Guardrail 1 | config_hash in runs table | `rl/guardrails.py` |
| Guardrail 2 | 需新增 | `rl/guardrails.py` |
| Guardrail 3 | 部分在 ExperimentPlanner | `rl/guardrails.py` |
| Guardrail 4 | `_inject_random_exploration` | 现有，规范化 |

---

## 5. 验证标准

Phase 0 完成需满足：

1. **文档完整性**：State/Action/Reward/Transition/Policy/Episode 六要素全部定义
2. **代码对应**：`spec.py` 中每个 MDP 要素有对应的 Python 类型
3. **护栏可执行**：4 条护栏有独立的函数实现和单元测试
4. **参数表完整**：所有可调参数、范围、步长、默认值列出
5. **与现有代码无冲突**：不破坏 meta_orchestrator.py, experiment_planner.py 的接口
