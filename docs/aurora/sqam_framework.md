# Aurora SQAM Framework

Aurora 的 CL 质量轨以 4 个统一维度约束 PersDyn、JITAI、Predictive、SRL、Idiographic Lite。

## 四维定义

| 维度 | 含义 | 典型失败形态 | Stage 32 对策 |
| --- | --- | --- | --- |
| `ID1` | Input Drift | 非有限值、未归一化输入、结构回退 | AST/结构 guard + 单元测试 |
| `ST1` | Stability | 置信度无上限、EMA/状态更新发散 | 上限封顶、`math.isfinite` 守护 |
| `DP1` | Privacy | 事件导出泄漏 PII、自由格式 ID、跨用户聚合未防护 | 脱敏、格式校验、DP 工具 |
| `SM1` | Safety Margin | 单因子触发、情绪维度过度驱动、强制重置过猛 | mood guard、risk handoff、confidence cap |

## 组件矩阵

| 组件 | ID1 | ST1 | DP1 | SM1 |
| --- | --- | --- | --- | --- |
| PersDyn | 观测值统一 clamp 到 `[0,1]` | EMA 仅消费有限值 | 事件总线不导出 attractor internals | `mood_valence` 不得单因子分支 |
| JITAI | `z_score/confidence` 必须 finite | 沿用 Stage 27 kill switch | 对外事件仅导出 `user_id_hash` | 与 Predictive 风险级别联动 |
| Predictive | analytics 必须稳定暴露 CTR | confidence ceiling `<=0.95` | realtime LLM 输入先脱敏 | 高风险时压制 mood-only JITAI |
| SRL | transition 证据 ID 结构合法 | force reset cap `0.8` | `evidence_id` 格式校验 | justification 必填并审计 |
| Idiographic Lite | 45d/40d 窗口阈值稳定 | confidence cap `0.80` | disclaimer + user-scoped recompute | 情绪关联退居次位 |

## Runner

- CI 入口：`scripts/run_all_rule_guards.sh --rule AR`
- Stage runner：`scripts/stage32/run_sqam_suite.sh`
- Runtime alerts：`monitoring/sqam_alerts.yml`
- Dashboard：`monitoring/grafana-dashboards/aurora_sqam_dashboard.json`
