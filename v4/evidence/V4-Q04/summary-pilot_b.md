# V4-Q04 run summary — tag=pilot_b raw=raw-pilot_b.jsonl
generated: 2026-09-28T23:45:27.474059+00:00

## L2（分母 n=1；失败/取消/超时不剔除，分位基于实际到达样本并单独列分母）
outcome: {'delivered': 1}
| 时刻 | n_reached | P50(s) | P90(s) | P99(s) | max(s) |
|---|---|---|---|---|---|
| t_ack_s | 1 | 0.001 | 0.001 | 0.001 | 0.001 |
| t_first_delta_s | 1 | 0.874 | 0.874 | 0.874 | 0.874 |
| t_first_useful_s | 1 | 1.057 | 1.057 | 1.057 | 1.057 |
| t_complete_s | 1 | 22.256 | 22.256 | 22.256 | 22.256 |
| t_first_stage_s | 1 | 0.021 | 0.021 | 0.021 | 0.021 |
| t_first_fulltext_s | 1 | 22.253 | 22.253 | 22.253 | 22.253 |
delivered=1  non_delivered=0
cost: db_attributed=1行/1971tok/$0.000197 | stream_frame_only=0行/0tok/$0.000000 | fully_unmetered_delivered=0行 | 合计(三源)≈$0.000197

## L3（分母 n=1；失败/取消/超时不剔除，分位基于实际到达样本并单独列分母）
outcome: {'delivered': 1}
| 时刻 | n_reached | P50(s) | P90(s) | P99(s) | max(s) |
|---|---|---|---|---|---|
| t_ack_s | 1 | 0.002 | 0.002 | 0.002 | 0.002 |
| t_first_delta_s | 1 | 7.652 | 7.652 | 7.652 | 7.652 |
| t_first_useful_s | 1 | 7.652 | 7.652 | 7.652 | 7.652 |
| t_complete_s | 1 | 25.981 | 25.981 | 25.981 | 25.981 |
| t_first_stage_s | 1 | 0.041 | 0.041 | 0.041 | 0.041 |
| t_first_fulltext_s | 1 | 25.974 | 25.974 | 25.974 | 25.974 |
delivered=1  non_delivered=0
cost: db_attributed=1行/2784tok/$0.000278 | stream_frame_only=0行/0tok/$0.000000 | fully_unmetered_delivered=0行 | 合计(三源)≈$0.000278

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