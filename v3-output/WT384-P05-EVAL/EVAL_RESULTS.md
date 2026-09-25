# P-05 Proactive Longitudinal Evaluation — Results

- git SHA: `322988ce` ｜ 运行：2026-09-25 10:50 UTC ｜ seed=20260925 ｜ 每组 24 persona（{'stalled': 8, 'deadline': 8, 'completion': 8}）× 14 模拟天

## 口径声明（如实）

- 样本：每组同一份 seeded persona 总体（24 = stalled/deadline/completion 各 8），两组唯一差异是主动面开/关。
- 生成/抑制/投递/行动/授权全部经真实服务（comeback 任务直调 + ActionCommand/Permission/FeedbackService）；
  模拟时钟以 backdate 换算（活动痕迹/计划窗口/建议时间/cooldown 尾每 tick 重写为真实时间戳）。
- persona 决策（accept/dismiss/mute/silent）与内在自发重启是 **seeded 显式模型**（参数全量在 events_timeline.json）；
  量化结论 = 该模型 + 真实主动面行为的联合结果，不是真人 RCT——量级读法见 REPORT。

## 两组对照（恢复轴 × 负担轴）

| 指标 | proactive | baseline | Δ |
|---|---|---|---|
| restart 率（停滞→重启） | 0.875 | 0.5417 | 0.3333 |
| 重启中位天数 | 2 | 7 | - |
| deadline 达成率 | 0.4167 | 0.0 | 0.4167 |
| 期末账本进度均值 | 0.7726 | 0.4115 | 0.3611 |
| 建议投放量 | 112 | 0 | - |
| 人均建议（最坏 persona） | 4.667（14） | 0（0） | - |
| 每重启 persona 打扰次数 | 5.333 | 0.0 | - |
| disposition（accept/silent/dismiss/mute） | {'accept': 51, 'silent': 22, 'dismiss': 30, 'mute': 9} | {} | - |

## 主动面正确性计数（违例 >0 即红）

- post_mute_deliveries: **0**
- next_day_redeliveries_after_accept: **0**
- sub_threshold_deliveries: **0**
- post_auto_revoke_auto_steps: **0**
- executed_steps_by_mode: **{'confirmation': 92, 'auto': 10}**
- post_ledger_complete_deliveries: **0**
- deliveries_while_plan_expired: **4**

## 跳过原因分布（真源抑制的证据）

- not_eligible: 165
- suggestion_suppressed:cooldown: 30
- suggestion_suppressed:muted: 59

