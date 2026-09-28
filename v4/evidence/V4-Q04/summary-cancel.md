# V4-Q04 run summary — tag=cancel raw=raw-cancel.jsonl
generated: 2026-09-28T23:43:12.853402+00:00

## L0（分母 n=2；失败/取消/超时不剔除，分位基于实际到达样本并单独列分母）
outcome: {'cancelled': 2}
| 时刻 | n_reached | P50(s) | P90(s) | P99(s) | max(s) |
|---|---|---|---|---|---|
| t_ack_s | 2 | 1.144 | 1.919 | 2.093 | 2.112 |
| t_first_delta_s | 1 | 28.548 | 28.548 | 28.548 | 28.548 |
| t_first_useful_s | 0 | - | - | - | - |
| t_complete_s | 0 | - | - | - | - |
| t_first_stage_s | 1 | 6.579 | 6.579 | 6.579 | 6.579 |
| t_first_fulltext_s | 0 | - | - | - | - |
delivered=0  non_delivered=2
cost: db_attributed=0行/0tok/$0.000000 | stream_frame_only=0行/0tok/$0.000000 | fully_unmetered_delivered=0行 | 合计(三源)≈$0.000000

## L1（分母 n=2；失败/取消/超时不剔除，分位基于实际到达样本并单独列分母）
outcome: {'cancelled': 2}
| 时刻 | n_reached | P50(s) | P90(s) | P99(s) | max(s) |
|---|---|---|---|---|---|
| t_ack_s | 2 | 0.557 | 1.001 | 1.101 | 1.112 |
| t_first_delta_s | 1 | 14.651 | 14.651 | 14.651 | 14.651 |
| t_first_useful_s | 0 | - | - | - | - |
| t_complete_s | 0 | - | - | - | - |
| t_first_stage_s | 1 | 2.376 | 2.376 | 2.376 | 2.376 |
| t_first_fulltext_s | 0 | - | - | - | - |
delivered=0  non_delivered=2
cost: db_attributed=0行/0tok/$0.000000 | stream_frame_only=0行/0tok/$0.000000 | fully_unmetered_delivered=0行 | 合计(三源)≈$0.000000

## L2（分母 n=2；失败/取消/超时不剔除，分位基于实际到达样本并单独列分母）
outcome: {'cancelled': 2}
| 时刻 | n_reached | P50(s) | P90(s) | P99(s) | max(s) |
|---|---|---|---|---|---|
| t_ack_s | 2 | 0.236 | 0.409 | 0.448 | 0.452 |
| t_first_delta_s | 1 | 20.391 | 20.391 | 20.391 | 20.391 |
| t_first_useful_s | 1 | 20.391 | 20.391 | 20.391 | 20.391 |
| t_complete_s | 0 | - | - | - | - |
| t_first_stage_s | 1 | 1.041 | 1.041 | 1.041 | 1.041 |
| t_first_fulltext_s | 0 | - | - | - | - |
delivered=0  non_delivered=2
cost: db_attributed=1行/0tok/$0.000000 | stream_frame_only=0行/0tok/$0.000000 | fully_unmetered_delivered=0行 | 合计(三源)≈$0.000000

## L3（分母 n=2；失败/取消/超时不剔除，分位基于实际到达样本并单独列分母）
outcome: {'cancelled': 2}
| 时刻 | n_reached | P50(s) | P90(s) | P99(s) | max(s) |
|---|---|---|---|---|---|
| t_ack_s | 2 | 0.566 | 1.004 | 1.103 | 1.114 |
| t_first_delta_s | 1 | 25.318 | 25.318 | 25.318 | 25.318 |
| t_first_useful_s | 1 | 25.318 | 25.318 | 25.318 | 25.318 |
| t_complete_s | 0 | - | - | - | - |
| t_first_stage_s | 1 | 1.309 | 1.309 | 1.309 | 1.309 |
| t_first_fulltext_s | 0 | - | - | - | - |
delivered=0  non_delivered=2
cost: db_attributed=0行/0tok/$0.000000 | stream_frame_only=0行/0tok/$0.000000 | fully_unmetered_delivered=0行 | 合计(三源)≈$0.000000

## 成本三源口径
- db_attributed：token_usage 行（引擎账，I10 单一核价权威；模型/tier 归因完整）
- stream_frame_only：DB 行丢失（共享队列竞争消费者致死信后未恢复/丢失），
  以流内 usage 帧（引擎回执 cost_micro_usd，同源权威）计量；模型归因缺失如实标注
- fully_unmetered：无 usage 帧且无 DB 行——计费完整性红项（见下）

## 计费完整性红项（验收 2：no_generation 带 token/漏辅助计费必须报红）
- 无（本 run 观测面内未发现 no_generation 带 token / 未归因 / usage 帧缺失）

注：隐藏辅助调用（Layer3 意图分类/sufficiency/HyDE/router embedding）不在 token_usage
计量范围——本表口径为「主生成计量成本」；辅助调用无计量即属漏计费面，
以 token_usage 行数与 attempt 数的差异另报（见 run_manifest.attempt_reconciliation）。