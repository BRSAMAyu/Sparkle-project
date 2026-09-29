# V4-Q04 run summary — tag=pilot_a raw=raw-pilot_a.jsonl
generated: 2026-09-28T19:51:22.435186+00:00

## L0（分母 n=2；失败/取消/超时不剔除，分位基于实际到达样本并单独列分母）
outcome: {'delivered': 2}
| 时刻 | n_reached | P50(s) | P90(s) | P99(s) | max(s) |
|---|---|---|---|---|---|
| t_ack_s | 2 | 0.001 | 0.001 | 0.001 | 0.001 |
| t_first_delta_s | 2 | 1.022 | 1.203 | 1.244 | 1.249 |
| t_first_useful_s | 2 | 1.022 | 1.203 | 1.244 | 1.249 |
| t_complete_s | 2 | 1.518 | 1.750 | 1.802 | 1.808 |
| t_first_stage_s | 2 | 0.043 | 0.053 | 0.055 | 0.056 |
| t_first_fulltext_s | 2 | 1.513 | 1.745 | 1.797 | 1.803 |
delivered=2  non_delivered=0
tokens_total(db)=0 bench_priced_cost=$0.0000

## L1（分母 n=2；失败/取消/超时不剔除，分位基于实际到达样本并单独列分母）
outcome: {'delivered': 2}
| 时刻 | n_reached | P50(s) | P90(s) | P99(s) | max(s) |
|---|---|---|---|---|---|
| t_ack_s | 2 | 0.001 | 0.001 | 0.001 | 0.001 |
| t_first_delta_s | 2 | 0.934 | 0.968 | 0.976 | 0.977 |
| t_first_useful_s | 2 | 1.120 | 1.194 | 1.211 | 1.213 |
| t_complete_s | 2 | 1.490 | 1.643 | 1.678 | 1.682 |
| t_first_stage_s | 2 | 0.023 | 0.028 | 0.029 | 0.029 |
| t_first_fulltext_s | 2 | 1.484 | 1.639 | 1.674 | 1.678 |
delivered=2  non_delivered=0
tokens_total(db)=1100 bench_priced_cost=$0.0000

## 计费完整性红项（验收 2：no_generation 带 token/漏辅助计费必须报红）
- RED: L0/L0-r1-01: billing_persistence_loss usage_frame_tokens=1359 but no token_usage row req=wtq04-pilot_a-l0-r1-01-3217c7
- RED: L0/L0-r1-02: billing_persistence_loss usage_frame_tokens=1030 but no token_usage row req=wtq04-pilot_a-l0-r1-02-0d3415
- RED: L1/L1-r1-02: billing_persistence_loss usage_frame_tokens=1366 but no token_usage row req=wtq04-pilot_a-l1-r1-02-02444c

注：隐藏辅助调用（Layer3 意图分类/sufficiency/HyDE/router embedding）不在 token_usage
计量范围——本表口径为「主生成计量成本」；辅助调用无计量即属漏计费面，
以 token_usage 行数与 attempt 数的差异另报（见 run_manifest.attempt_reconciliation）。