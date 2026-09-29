# V4-Q04 run summary — tag=fastlane raw=raw-fastlane.jsonl
generated: 2026-09-28T23:42:03.596069+00:00

## L0（分母 n=104；失败/取消/超时不剔除，分位基于实际到达样本并单独列分母）
outcome: {'delivered': 104}
| 时刻 | n_reached | P50(s) | P90(s) | P99(s) | max(s) |
|---|---|---|---|---|---|
| t_ack_s | 104 | 0.004 | 0.925 | 1.660 | 1.788 |
| t_first_delta_s | 104 | 2.366 | 6.013 | 10.088 | 13.940 |
| t_first_useful_s | 101 | 2.441 | 6.143 | 10.113 | 13.940 |
| t_complete_s | 104 | 6.215 | 24.397 | 42.522 | 43.765 |
| t_first_stage_s | 104 | 0.083 | 1.150 | 1.809 | 1.898 |
| t_first_fulltext_s | 104 | 6.197 | 24.386 | 42.516 | 43.758 |
delivered=104  non_delivered=0
cost: db_attributed=91行/103336tok/$0.010334 | stream_frame_only=0行/0tok/$0.000000 | fully_unmetered_delivered=13行 | 合计(三源)≈$0.010334

## 成本三源口径
- db_attributed：token_usage 行（引擎账，I10 单一核价权威；模型/tier 归因完整）
- stream_frame_only：DB 行丢失（共享队列竞争消费者致死信后未恢复/丢失），
  以流内 usage 帧（引擎回执 cost_micro_usd，同源权威）计量；模型归因缺失如实标注
- fully_unmetered：无 usage 帧且无 DB 行——计费完整性红项（见下）

## 计费完整性红项（验收 2：no_generation 带 token/漏辅助计费必须报红）
- RED: L0/L0-r1-02: fully_unmetered_delivered 无usage帧且无token_usage行 req=wtq04-fastlane-l0-r1-02-633e41
- RED: L0/L0-r1-06: fully_unmetered_delivered 无usage帧且无token_usage行 req=wtq04-fastlane-l0-r1-06-e87212
- RED: L0/L0-r1-16: fully_unmetered_delivered 无usage帧且无token_usage行 req=wtq04-fastlane-l0-r1-16-d37dab
- RED: L0/L0-r2-01: fully_unmetered_delivered 无usage帧且无token_usage行 req=wtq04-fastlane-l0-r2-01-563eed
- RED: L0/L0-r2-04: fully_unmetered_delivered 无usage帧且无token_usage行 req=wtq04-fastlane-l0-r2-04-bbc988
- RED: L0/L0-r3-01: fully_unmetered_delivered 无usage帧且无token_usage行 req=wtq04-fastlane-l0-r3-01-ba361f
- RED: L0/L0-r3-02: fully_unmetered_delivered 无usage帧且无token_usage行 req=wtq04-fastlane-l0-r3-02-e8b994
- RED: L0/L0-r3-04: fully_unmetered_delivered 无usage帧且无token_usage行 req=wtq04-fastlane-l0-r3-04-09af4b
- RED: L0/L0-r3-06: fully_unmetered_delivered 无usage帧且无token_usage行 req=wtq04-fastlane-l0-r3-06-88a5f0
- RED: L0/L0-r4-01: fully_unmetered_delivered 无usage帧且无token_usage行 req=wtq04-fastlane-l0-r4-01-f1be63
- RED: L0/L0-r4-06: fully_unmetered_delivered 无usage帧且无token_usage行 req=wtq04-fastlane-l0-r4-06-69151f
- RED: L0/L0-r4-14: fully_unmetered_delivered 无usage帧且无token_usage行 req=wtq04-fastlane-l0-r4-14-34ed21
- RED: L0/L0-r4-16: fully_unmetered_delivered 无usage帧且无token_usage行 req=wtq04-fastlane-l0-r4-16-42c480

注：隐藏辅助调用（Layer3 意图分类/sufficiency/HyDE/router embedding）不在 token_usage
计量范围——本表口径为「主生成计量成本」；辅助调用无计量即属漏计费面，
以 token_usage 行数与 attempt 数的差异另报（见 run_manifest.attempt_reconciliation）。

---

## 一审勘误注记（wtQ04R1 PASS_WITH_CHALLENGES；本文件为采集时点快照，原始行未改动）

本文件 generated=23:42:03 的 join 晚于本卡自身恢复批（23:42:02，58 行/120ms 突发）读及面 1 秒——TOCTOU 竞态。一审终态复验订正：本表 13 行「fully_unmetered_delivered」**全部已落库**，标签恰为 I09 承诺的 no_generation_model/0tok（deterministic 面 26/26 达标）；「快路 early-return 疑绕过 cleanup」根因假设撤回（C-1）。权威口径以 run_manifest.json / diff_or_evidence_only.md 勘误值为准。