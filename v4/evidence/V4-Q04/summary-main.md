# V4-Q04 run summary — tag=main raw=raw-main.jsonl
generated: 2026-09-28T23:43:12.789195+00:00

## L0（分母 n=104；失败/取消/超时不剔除，分位基于实际到达样本并单独列分母）
outcome: {'delivered': 104}
| 时刻 | n_reached | P50(s) | P90(s) | P99(s) | max(s) |
|---|---|---|---|---|---|
| t_ack_s | 104 | 0.013 | 0.587 | 4.598 | 4.767 |
| t_first_delta_s | 104 | 3.584 | 9.354 | 11.849 | 15.392 |
| t_first_useful_s | 101 | 3.756 | 9.451 | 11.850 | 15.569 |
| t_complete_s | 104 | 10.284 | 32.971 | 45.928 | 49.240 |
| t_first_stage_s | 104 | 0.151 | 1.367 | 4.956 | 5.535 |
| t_first_fulltext_s | 104 | 10.271 | 32.966 | 45.920 | 49.232 |
delivered=104  non_delivered=0
cost: db_attributed=53行/70398tok/$0.007044 | stream_frame_only=51行/70114tok/$0.007012 | fully_unmetered_delivered=0行 | 合计(三源)≈$0.014056

## L1（分母 n=104；失败/取消/超时不剔除，分位基于实际到达样本并单独列分母）
outcome: {'delivered': 104}
| 时刻 | n_reached | P50(s) | P90(s) | P99(s) | max(s) |
|---|---|---|---|---|---|
| t_ack_s | 104 | 0.001 | 0.323 | 1.394 | 1.811 |
| t_first_delta_s | 97 | 2.072 | 4.988 | 9.167 | 9.620 |
| t_first_useful_s | 104 | 2.450 | 5.551 | 9.718 | 9.756 |
| t_complete_s | 104 | 19.822 | 30.896 | 39.667 | 40.504 |
| t_first_stage_s | 104 | 0.045 | 0.434 | 2.255 | 5.058 |
| t_first_fulltext_s | 104 | 19.816 | 30.872 | 39.662 | 40.500 |
delivered=104  non_delivered=0
cost: db_attributed=43行/190964tok/$0.019094 | stream_frame_only=56行/222394tok/$0.022240 | fully_unmetered_delivered=5行 | 合计(三源)≈$0.041334

## L2（分母 n=104；失败/取消/超时不剔除，分位基于实际到达样本并单独列分母）
outcome: {'delivered': 104}
| 时刻 | n_reached | P50(s) | P90(s) | P99(s) | max(s) |
|---|---|---|---|---|---|
| t_ack_s | 104 | 0.028 | 0.382 | 5.017 | 5.553 |
| t_first_delta_s | 84 | 3.967 | 19.258 | 112.562 | 117.140 |
| t_first_useful_s | 104 | 4.272 | 12.081 | 111.523 | 117.140 |
| t_complete_s | 104 | 29.878 | 56.179 | 112.405 | 117.659 |
| t_first_stage_s | 104 | 0.111 | 0.518 | 5.085 | 5.633 |
| t_first_fulltext_s | 104 | 29.872 | 56.172 | 112.397 | 117.657 |
delivered=104  non_delivered=0
cost: db_attributed=73行/228664tok/$0.022797 | stream_frame_only=26行/91472tok/$0.009148 | fully_unmetered_delivered=5行 | 合计(三源)≈$0.031945

## L3（分母 n=104；失败/取消/超时不剔除，分位基于实际到达样本并单独列分母）
outcome: {'delivered': 104}
| 时刻 | n_reached | P50(s) | P90(s) | P99(s) | max(s) |
|---|---|---|---|---|---|
| t_ack_s | 104 | 0.112 | 0.770 | 1.784 | 2.995 |
| t_first_delta_s | 96 | 6.414 | 11.600 | 17.017 | 17.028 |
| t_first_useful_s | 104 | 6.422 | 11.651 | 17.250 | 17.796 |
| t_complete_s | 104 | 38.714 | 57.760 | 65.365 | 69.823 |
| t_first_stage_s | 104 | 0.282 | 0.982 | 3.302 | 3.872 |
| t_first_fulltext_s | 104 | 38.702 | 57.753 | 65.364 | 69.733 |
delivered=104  non_delivered=0
cost: db_attributed=81行/532510tok/$0.053250 | stream_frame_only=19行/161220tok/$0.016125 | fully_unmetered_delivered=4行 | 合计(三源)≈$0.069375

## 成本三源口径
- db_attributed：token_usage 行（引擎账，I10 单一核价权威；模型/tier 归因完整）
- stream_frame_only：DB 行丢失（共享队列竞争消费者致死信后未恢复/丢失），
  以流内 usage 帧（引擎回执 cost_micro_usd，同源权威）计量；模型归因缺失如实标注
- fully_unmetered：无 usage 帧且无 DB 行——计费完整性红项（见下）

## 计费完整性红项（验收 2：no_generation 带 token/漏辅助计费必须报红）
- RED: L0/L0-r1-03: billing_persistence_loss tokens=1512 receipt_usd=0.000151 but no token_usage row req=wtq04-main-l0-r1-03-8eca2a
- RED: L0/L0-r1-04: billing_persistence_loss tokens=1408 receipt_usd=0.000141 but no token_usage row req=wtq04-main-l0-r1-04-2a72a9
- RED: L0/L0-r1-07: billing_persistence_loss tokens=1379 receipt_usd=0.000138 but no token_usage row req=wtq04-main-l0-r1-07-6d3b0b
- RED: L0/L0-r1-09: billing_persistence_loss tokens=1070 receipt_usd=0.000107 but no token_usage row req=wtq04-main-l0-r1-09-4e5a0a
- RED: L0/L0-r1-12: billing_persistence_loss tokens=1342 receipt_usd=0.000134 but no token_usage row req=wtq04-main-l0-r1-12-3cbff7
- RED: L0/L0-r1-14: billing_persistence_loss tokens=1536 receipt_usd=0.000154 but no token_usage row req=wtq04-main-l0-r1-14-4f3bc1
- RED: L0/L0-r1-15: billing_persistence_loss tokens=1560 receipt_usd=0.000156 but no token_usage row req=wtq04-main-l0-r1-15-425be1
- RED: L0/L0-r1-20: billing_persistence_loss tokens=1489 receipt_usd=0.000149 but no token_usage row req=wtq04-main-l0-r1-20-284c21
- RED: L0/L0-r1-21: billing_persistence_loss tokens=1948 receipt_usd=0.000195 but no token_usage row req=wtq04-main-l0-r1-21-1a01f5
- RED: L0/L0-r1-23: billing_persistence_loss tokens=1345 receipt_usd=0.000135 but no token_usage row req=wtq04-main-l0-r1-23-6dc296
- RED: L0/L0-r1-25: billing_persistence_loss tokens=1453 receipt_usd=0.000145 but no token_usage row req=wtq04-main-l0-r1-25-8b3784
- RED: L0/L0-r2-01: billing_persistence_loss tokens=1443 receipt_usd=0.000144 but no token_usage row req=wtq04-main-l0-r2-01-773a81
- RED: L0/L0-r2-02: billing_persistence_loss tokens=1373 receipt_usd=0.000137 but no token_usage row req=wtq04-main-l0-r2-02-193de4
- RED: L0/L0-r2-04: billing_persistence_loss tokens=1389 receipt_usd=0.000139 but no token_usage row req=wtq04-main-l0-r2-04-6cdf2c
- RED: L0/L0-r2-05: billing_persistence_loss tokens=1416 receipt_usd=0.000142 but no token_usage row req=wtq04-main-l0-r2-05-da753f
- RED: L0/L0-r2-07: billing_persistence_loss tokens=1187 receipt_usd=0.000119 but no token_usage row req=wtq04-main-l0-r2-07-ce63b6
- RED: L0/L0-r2-10: billing_persistence_loss tokens=1216 receipt_usd=0.000122 but no token_usage row req=wtq04-main-l0-r2-10-e055b0
- RED: L0/L0-r2-12: billing_persistence_loss tokens=1188 receipt_usd=0.000119 but no token_usage row req=wtq04-main-l0-r2-12-d55ee2
- RED: L0/L0-r2-19: billing_persistence_loss tokens=1234 receipt_usd=0.000123 but no token_usage row req=wtq04-main-l0-r2-19-8ec757
- RED: L0/L0-r2-23: billing_persistence_loss tokens=1433 receipt_usd=0.000143 but no token_usage row req=wtq04-main-l0-r2-23-959a5a
- RED: L0/L0-r2-24: billing_persistence_loss tokens=1408 receipt_usd=0.000141 but no token_usage row req=wtq04-main-l0-r2-24-fc4eb1
- RED: L0/L0-r2-25: billing_persistence_loss tokens=1618 receipt_usd=0.000162 but no token_usage row req=wtq04-main-l0-r2-25-26c157
- RED: L0/L0-r2-26: billing_persistence_loss tokens=1102 receipt_usd=0.000110 but no token_usage row req=wtq04-main-l0-r2-26-7dfeae
- RED: L0/L0-r3-01: billing_persistence_loss tokens=1474 receipt_usd=0.000147 but no token_usage row req=wtq04-main-l0-r3-01-6a0a72
- RED: L0/L0-r3-02: billing_persistence_loss tokens=1466 receipt_usd=0.000147 but no token_usage row req=wtq04-main-l0-r3-02-5100bc
- RED: L0/L0-r3-05: billing_persistence_loss tokens=1318 receipt_usd=0.000132 but no token_usage row req=wtq04-main-l0-r3-05-bb8aca
- RED: L0/L0-r3-08: billing_persistence_loss tokens=1046 receipt_usd=0.000105 but no token_usage row req=wtq04-main-l0-r3-08-acc645
- RED: L0/L0-r3-10: billing_persistence_loss tokens=1647 receipt_usd=0.000165 but no token_usage row req=wtq04-main-l0-r3-10-3f6f6c
- RED: L0/L0-r3-14: billing_persistence_loss tokens=1295 receipt_usd=0.000130 but no token_usage row req=wtq04-main-l0-r3-14-b044f9
- RED: L0/L0-r3-16: billing_persistence_loss tokens=1162 receipt_usd=0.000116 but no token_usage row req=wtq04-main-l0-r3-16-63ed5c
- RED: L0/L0-r3-17: billing_persistence_loss tokens=1492 receipt_usd=0.000149 but no token_usage row req=wtq04-main-l0-r3-17-1d18ec
- RED: L0/L0-r3-19: billing_persistence_loss tokens=1130 receipt_usd=0.000113 but no token_usage row req=wtq04-main-l0-r3-19-49ce2e
- RED: L0/L0-r3-20: billing_persistence_loss tokens=1305 receipt_usd=0.000131 but no token_usage row req=wtq04-main-l0-r3-20-71e703
- RED: L0/L0-r3-21: billing_persistence_loss tokens=1104 receipt_usd=0.000110 but no token_usage row req=wtq04-main-l0-r3-21-15ed54
- RED: L0/L0-r3-23: billing_persistence_loss tokens=1238 receipt_usd=0.000124 but no token_usage row req=wtq04-main-l0-r3-23-448246
- RED: L0/L0-r3-25: billing_persistence_loss tokens=1301 receipt_usd=0.000130 but no token_usage row req=wtq04-main-l0-r3-25-ebf739
- RED: L0/L0-r4-01: billing_persistence_loss tokens=1414 receipt_usd=0.000141 but no token_usage row req=wtq04-main-l0-r4-01-cf61dc
- RED: L0/L0-r4-04: billing_persistence_loss tokens=1404 receipt_usd=0.000140 but no token_usage row req=wtq04-main-l0-r4-04-8a876b
- RED: L0/L0-r4-07: billing_persistence_loss tokens=1371 receipt_usd=0.000137 but no token_usage row req=wtq04-main-l0-r4-07-fb2759
- RED: L0/L0-r4-09: billing_persistence_loss tokens=1155 receipt_usd=0.000116 but no token_usage row req=wtq04-main-l0-r4-09-d9d083
- RED: L0/L0-r4-10: billing_persistence_loss tokens=1399 receipt_usd=0.000140 but no token_usage row req=wtq04-main-l0-r4-10-25cda7
- RED: L0/L0-r4-11: billing_persistence_loss tokens=1613 receipt_usd=0.000161 but no token_usage row req=wtq04-main-l0-r4-11-6e2aad
- RED: L0/L0-r4-13: billing_persistence_loss tokens=1423 receipt_usd=0.000142 but no token_usage row req=wtq04-main-l0-r4-13-6586b5
- RED: L0/L0-r4-14: billing_persistence_loss tokens=1673 receipt_usd=0.000167 but no token_usage row req=wtq04-main-l0-r4-14-f25520
- RED: L0/L0-r4-16: billing_persistence_loss tokens=1378 receipt_usd=0.000138 but no token_usage row req=wtq04-main-l0-r4-16-e44401
- RED: L0/L0-r4-17: billing_persistence_loss tokens=1533 receipt_usd=0.000153 but no token_usage row req=wtq04-main-l0-r4-17-ab0b1c
- RED: L0/L0-r4-18: billing_persistence_loss tokens=1260 receipt_usd=0.000126 but no token_usage row req=wtq04-main-l0-r4-18-5418f1
- RED: L0/L0-r4-20: billing_persistence_loss tokens=1445 receipt_usd=0.000145 but no token_usage row req=wtq04-main-l0-r4-20-e3ac0d
- RED: L0/L0-r4-22: billing_persistence_loss tokens=1423 receipt_usd=0.000142 but no token_usage row req=wtq04-main-l0-r4-22-519e81
- RED: L0/L0-r4-23: billing_persistence_loss tokens=1224 receipt_usd=0.000122 but no token_usage row req=wtq04-main-l0-r4-23-af4b7e
- RED: L0/L0-r4-26: billing_persistence_loss tokens=1372 receipt_usd=0.000137 but no token_usage row req=wtq04-main-l0-r4-26-30e7f9
- RED: L1/L1-r1-01: billing_persistence_loss tokens=1404 receipt_usd=0.000140 but no token_usage row req=wtq04-main-l1-r1-01-88b1d8
- RED: L1/L1-r1-02: billing_persistence_loss tokens=1408 receipt_usd=0.000141 but no token_usage row req=wtq04-main-l1-r1-02-b57dea
- RED: L1/L1-r1-03: billing_persistence_loss tokens=1214 receipt_usd=0.000121 but no token_usage row req=wtq04-main-l1-r1-03-10ff1c
- RED: L1/L1-r1-04: billing_persistence_loss tokens=1599 receipt_usd=0.000160 but no token_usage row req=wtq04-main-l1-r1-04-8c8888
- RED: L1/L1-r1-05: billing_persistence_loss tokens=1573 receipt_usd=0.000157 but no token_usage row req=wtq04-main-l1-r1-05-79fd0d
- RED: L1/L1-r1-06: billing_persistence_loss tokens=1738 receipt_usd=0.000174 but no token_usage row req=wtq04-main-l1-r1-06-d66ec6
- RED: L1/L1-r1-07: billing_persistence_loss tokens=1810 receipt_usd=0.000181 but no token_usage row req=wtq04-main-l1-r1-07-9499c6
- RED: L1/L1-r1-09: billing_persistence_loss tokens=1966 receipt_usd=0.000197 but no token_usage row req=wtq04-main-l1-r1-09-26a7a8
- RED: L1/L1-r1-12: billing_persistence_loss tokens=1929 receipt_usd=0.000193 but no token_usage row req=wtq04-main-l1-r1-12-278466
- RED: L1/L1-r1-14: billing_persistence_loss tokens=13431 receipt_usd=0.001343 but no token_usage row req=wtq04-main-l1-r1-14-967f14
- RED: L1/L1-r1-15: billing_persistence_loss tokens=1950 receipt_usd=0.000195 but no token_usage row req=wtq04-main-l1-r1-15-8d3099
- RED: L1/L1-r1-17: fully_unmetered_delivered 无usage帧且无token_usage行 req=wtq04-main-l1-r1-17-b586cc
- RED: L1/L1-r1-19: billing_persistence_loss tokens=1690 receipt_usd=0.000169 but no token_usage row req=wtq04-main-l1-r1-19-f2ab11
- RED: L1/L1-r1-20: billing_persistence_loss tokens=13707 receipt_usd=0.001371 but no token_usage row req=wtq04-main-l1-r1-20-0df795
- RED: L1/L1-r1-23: billing_persistence_loss tokens=2055 receipt_usd=0.000206 but no token_usage row req=wtq04-main-l1-r1-23-b17829
- RED: L1/L1-r1-24: billing_persistence_loss tokens=1626 receipt_usd=0.000163 but no token_usage row req=wtq04-main-l1-r1-24-1b204c
- RED: L1/L1-r2-03: fully_unmetered_delivered 无usage帧且无token_usage行 req=wtq04-main-l1-r2-03-567984
- RED: L1/L1-r2-04: billing_persistence_loss tokens=1523 receipt_usd=0.000152 but no token_usage row req=wtq04-main-l1-r2-04-3839d6
- RED: L1/L1-r2-05: billing_persistence_loss tokens=2018 receipt_usd=0.000202 but no token_usage row req=wtq04-main-l1-r2-05-2b3b51
- RED: L1/L1-r2-07: billing_persistence_loss tokens=1013 receipt_usd=0.000101 but no token_usage row req=wtq04-main-l1-r2-07-f3c67c
- RED: L1/L1-r2-08: billing_persistence_loss tokens=1563 receipt_usd=0.000156 but no token_usage row req=wtq04-main-l1-r2-08-0ac760
- RED: L1/L1-r2-10: billing_persistence_loss tokens=1661 receipt_usd=0.000166 but no token_usage row req=wtq04-main-l1-r2-10-1b07f9
- RED: L1/L1-r2-11: billing_persistence_loss tokens=13908 receipt_usd=0.001391 but no token_usage row req=wtq04-main-l1-r2-11-776c60
- RED: L1/L1-r2-16: billing_persistence_loss tokens=1813 receipt_usd=0.000181 but no token_usage row req=wtq04-main-l1-r2-16-555a4f
- RED: L1/L1-r2-18: billing_persistence_loss tokens=1982 receipt_usd=0.000198 but no token_usage row req=wtq04-main-l1-r2-18-d518fd
- RED: L1/L1-r2-19: billing_persistence_loss tokens=1540 receipt_usd=0.000154 but no token_usage row req=wtq04-main-l1-r2-19-884313
- RED: L1/L1-r2-21: billing_persistence_loss tokens=14165 receipt_usd=0.001417 but no token_usage row req=wtq04-main-l1-r2-21-a057f8
- RED: L1/L1-r2-22: billing_persistence_loss tokens=13613 receipt_usd=0.001361 but no token_usage row req=wtq04-main-l1-r2-22-391679
- RED: L1/L1-r2-23: billing_persistence_loss tokens=2380 receipt_usd=0.000238 but no token_usage row req=wtq04-main-l1-r2-23-9d9b0a
- RED: L1/L1-r2-25: billing_persistence_loss tokens=2732 receipt_usd=0.000273 but no token_usage row req=wtq04-main-l1-r2-25-db41a7
- RED: L1/L1-r3-01: billing_persistence_loss tokens=2049 receipt_usd=0.000205 but no token_usage row req=wtq04-main-l1-r3-01-4e7156
- RED: L1/L1-r3-03: fully_unmetered_delivered 无usage帧且无token_usage行 req=wtq04-main-l1-r3-03-336bd1
- RED: L1/L1-r3-04: billing_persistence_loss tokens=1259 receipt_usd=0.000126 but no token_usage row req=wtq04-main-l1-r3-04-670d13
- RED: L1/L1-r3-06: billing_persistence_loss tokens=2003 receipt_usd=0.000200 but no token_usage row req=wtq04-main-l1-r3-06-6668e8
- RED: L1/L1-r3-07: billing_persistence_loss tokens=1822 receipt_usd=0.000182 but no token_usage row req=wtq04-main-l1-r3-07-140581
- RED: L1/L1-r3-08: billing_persistence_loss tokens=1697 receipt_usd=0.000170 but no token_usage row req=wtq04-main-l1-r3-08-72c699
- RED: L1/L1-r3-10: billing_persistence_loss tokens=2258 receipt_usd=0.000226 but no token_usage row req=wtq04-main-l1-r3-10-3caabf
- RED: L1/L1-r3-11: billing_persistence_loss tokens=13408 receipt_usd=0.001341 but no token_usage row req=wtq04-main-l1-r3-11-536383
- RED: L1/L1-r3-12: billing_persistence_loss tokens=1562 receipt_usd=0.000156 but no token_usage row req=wtq04-main-l1-r3-12-9fe3b7
- RED: L1/L1-r3-15: billing_persistence_loss tokens=1750 receipt_usd=0.000175 but no token_usage row req=wtq04-main-l1-r3-15-87b3fc
- RED: L1/L1-r3-17: fully_unmetered_delivered 无usage帧且无token_usage行 req=wtq04-main-l1-r3-17-142988
- RED: L1/L1-r3-21: billing_persistence_loss tokens=1631 receipt_usd=0.000163 but no token_usage row req=wtq04-main-l1-r3-21-0499b6
- RED: L1/L1-r3-22: billing_persistence_loss tokens=13866 receipt_usd=0.001387 but no token_usage row req=wtq04-main-l1-r3-22-07c7fd
- RED: L1/L1-r3-23: billing_persistence_loss tokens=14089 receipt_usd=0.001409 but no token_usage row req=wtq04-main-l1-r3-23-67d55f
- RED: L1/L1-r3-24: billing_persistence_loss tokens=13728 receipt_usd=0.001373 but no token_usage row req=wtq04-main-l1-r3-24-db9e55
- RED: L1/L1-r3-25: billing_persistence_loss tokens=2714 receipt_usd=0.000271 but no token_usage row req=wtq04-main-l1-r3-25-085a7d
- RED: L1/L1-r3-26: billing_persistence_loss tokens=13962 receipt_usd=0.001396 but no token_usage row req=wtq04-main-l1-r3-26-b66ea9
- RED: L1/L1-r4-01: billing_persistence_loss tokens=1715 receipt_usd=0.000172 but no token_usage row req=wtq04-main-l1-r4-01-37dde8
- RED: L1/L1-r4-03: fully_unmetered_delivered 无usage帧且无token_usage行 req=wtq04-main-l1-r4-03-7696a8
- RED: L1/L1-r4-05: billing_persistence_loss tokens=1832 receipt_usd=0.000183 but no token_usage row req=wtq04-main-l1-r4-05-3ab24a
- RED: L1/L1-r4-06: billing_persistence_loss tokens=4288 receipt_usd=0.000429 but no token_usage row req=wtq04-main-l1-r4-06-841c83
- RED: L1/L1-r4-07: billing_persistence_loss tokens=1013 receipt_usd=0.000101 but no token_usage row req=wtq04-main-l1-r4-07-995f2d
- RED: L1/L1-r4-08: billing_persistence_loss tokens=1511 receipt_usd=0.000151 but no token_usage row req=wtq04-main-l1-r4-08-81dd05
- RED: L1/L1-r4-09: billing_persistence_loss tokens=1322 receipt_usd=0.000132 but no token_usage row req=wtq04-main-l1-r4-09-76fee3
- RED: L1/L1-r4-10: billing_persistence_loss tokens=1776 receipt_usd=0.000178 but no token_usage row req=wtq04-main-l1-r4-10-3eb0f1
- RED: L1/L1-r4-12: billing_persistence_loss tokens=2101 receipt_usd=0.000210 but no token_usage row req=wtq04-main-l1-r4-12-0a7bc9
- RED: L1/L1-r4-15: billing_persistence_loss tokens=1896 receipt_usd=0.000190 but no token_usage row req=wtq04-main-l1-r4-15-3136ec
- RED: L1/L1-r4-18: billing_persistence_loss tokens=2080 receipt_usd=0.000208 but no token_usage row req=wtq04-main-l1-r4-18-e3ba31
- RED: L1/L1-r4-19: billing_persistence_loss tokens=1710 receipt_usd=0.000171 but no token_usage row req=wtq04-main-l1-r4-19-f357d6
- RED: L1/L1-r4-20: billing_persistence_loss tokens=2169 receipt_usd=0.000217 but no token_usage row req=wtq04-main-l1-r4-20-82afb7
- RED: L1/L1-r4-21: billing_persistence_loss tokens=2172 receipt_usd=0.000217 but no token_usage row req=wtq04-main-l1-r4-21-8c23fe
- RED: L2/L2-r1-04: billing_persistence_loss tokens=2489 receipt_usd=0.000249 but no token_usage row req=wtq04-main-l2-r1-04-c593e1
- RED: L2/L2-r1-06: billing_persistence_loss tokens=1604 receipt_usd=0.000160 but no token_usage row req=wtq04-main-l2-r1-06-72f29a
- RED: L2/L2-r1-08: no_generation_estimated_with_tokens(I10检出桶) tokens=277 req=wtq04-main-l2-r1-08-e6b31f
- RED: L2/L2-r1-08: usage_frame_missing_but_db_tokens req=wtq04-main-l2-r1-08-e6b31f
- RED: L2/L2-r1-12: billing_persistence_loss tokens=14382 receipt_usd=0.001438 but no token_usage row req=wtq04-main-l2-r1-12-214b73
- RED: L2/L2-r1-22: billing_persistence_loss tokens=2110 receipt_usd=0.000211 but no token_usage row req=wtq04-main-l2-r1-22-95b94c
- RED: L2/L2-r1-26: billing_persistence_loss tokens=2409 receipt_usd=0.000241 but no token_usage row req=wtq04-main-l2-r1-26-5e0536
- RED: L2/L2-r2-03: billing_persistence_loss tokens=3091 receipt_usd=0.000309 but no token_usage row req=wtq04-main-l2-r2-03-28504c
- RED: L2/L2-r2-08: fully_unmetered_delivered 无usage帧且无token_usage行 req=wtq04-main-l2-r2-08-a4c62b
- RED: L2/L2-r2-11: fully_unmetered_delivered 无usage帧且无token_usage行 req=wtq04-main-l2-r2-11-e39b1b
- RED: L2/L2-r2-13: billing_persistence_loss tokens=2637 receipt_usd=0.000264 but no token_usage row req=wtq04-main-l2-r2-13-ea1762
- RED: L2/L2-r2-14: billing_persistence_loss tokens=2734 receipt_usd=0.000273 but no token_usage row req=wtq04-main-l2-r2-14-25374d
- RED: L2/L2-r2-19: billing_persistence_loss tokens=1800 receipt_usd=0.000180 but no token_usage row req=wtq04-main-l2-r2-19-9aa649
- RED: L2/L2-r2-22: billing_persistence_loss tokens=2952 receipt_usd=0.000295 but no token_usage row req=wtq04-main-l2-r2-22-169eaf
- RED: L2/L2-r2-24: billing_persistence_loss tokens=2839 receipt_usd=0.000284 but no token_usage row req=wtq04-main-l2-r2-24-64c325
- RED: L2/L2-r3-05: billing_persistence_loss tokens=3208 receipt_usd=0.000321 but no token_usage row req=wtq04-main-l2-r3-05-f119ce
- RED: L2/L2-r3-08: no_generation_estimated_with_tokens(I10检出桶) tokens=216 req=wtq04-main-l2-r3-08-fd86c1
- RED: L2/L2-r3-08: usage_frame_missing_but_db_tokens req=wtq04-main-l2-r3-08-fd86c1
- RED: L2/L2-r3-13: billing_persistence_loss tokens=2398 receipt_usd=0.000240 but no token_usage row req=wtq04-main-l2-r3-13-a96775
- RED: L2/L2-r3-17: billing_persistence_loss tokens=3194 receipt_usd=0.000319 but no token_usage row req=wtq04-main-l2-r3-17-009c85
- RED: L2/L2-r3-20: fully_unmetered_delivered 无usage帧且无token_usage行 req=wtq04-main-l2-r3-20-009c3b
- RED: L2/L2-r3-21: billing_persistence_loss tokens=2354 receipt_usd=0.000235 but no token_usage row req=wtq04-main-l2-r3-21-6ba513
- RED: L2/L2-r3-25: fully_unmetered_delivered 无usage帧且无token_usage行 req=wtq04-main-l2-r3-25-323d2c
- RED: L2/L2-r4-03: billing_persistence_loss tokens=3393 receipt_usd=0.000339 but no token_usage row req=wtq04-main-l2-r4-03-3e6e63
- RED: L2/L2-r4-05: billing_persistence_loss tokens=2095 receipt_usd=0.000210 but no token_usage row req=wtq04-main-l2-r4-05-69449f
- RED: L2/L2-r4-08: no_generation_estimated_with_tokens(I10检出桶) tokens=216 req=wtq04-main-l2-r4-08-356189
- RED: L2/L2-r4-08: usage_frame_missing_but_db_tokens req=wtq04-main-l2-r4-08-356189
- RED: L2/L2-r4-09: fully_unmetered_delivered 无usage帧且无token_usage行 req=wtq04-main-l2-r4-09-40f0f3
- RED: L2/L2-r4-12: billing_persistence_loss tokens=13822 receipt_usd=0.001382 but no token_usage row req=wtq04-main-l2-r4-12-c7b3ff
- RED: L2/L2-r4-13: billing_persistence_loss tokens=2450 receipt_usd=0.000245 but no token_usage row req=wtq04-main-l2-r4-13-b85893
- RED: L2/L2-r4-14: billing_persistence_loss tokens=2377 receipt_usd=0.000238 but no token_usage row req=wtq04-main-l2-r4-14-a10328
- RED: L2/L2-r4-15: billing_persistence_loss tokens=2315 receipt_usd=0.000232 but no token_usage row req=wtq04-main-l2-r4-15-133d5f
- RED: L2/L2-r4-17: billing_persistence_loss tokens=3837 receipt_usd=0.000384 but no token_usage row req=wtq04-main-l2-r4-17-57e065
- RED: L2/L2-r4-18: billing_persistence_loss tokens=2070 receipt_usd=0.000207 but no token_usage row req=wtq04-main-l2-r4-18-357c0e
- RED: L2/L2-r4-23: billing_persistence_loss tokens=3857 receipt_usd=0.000386 but no token_usage row req=wtq04-main-l2-r4-23-c7a9f2
- RED: L2/L2-r4-24: billing_persistence_loss tokens=2656 receipt_usd=0.000266 but no token_usage row req=wtq04-main-l2-r4-24-d25a41
- RED: L2/L2-r4-26: billing_persistence_loss tokens=2399 receipt_usd=0.000240 but no token_usage row req=wtq04-main-l2-r4-26-21cda4
- RED: L3/L3-r1-01: billing_persistence_loss tokens=15105 receipt_usd=0.001511 but no token_usage row req=wtq04-main-l3-r1-01-43d644
- RED: L3/L3-r1-02: billing_persistence_loss tokens=15115 receipt_usd=0.001512 but no token_usage row req=wtq04-main-l3-r1-02-b9a752
- RED: L3/L3-r1-03: billing_persistence_loss tokens=3718 receipt_usd=0.000372 but no token_usage row req=wtq04-main-l3-r1-03-f5c92c
- RED: L3/L3-r1-07: billing_persistence_loss tokens=14947 receipt_usd=0.001495 but no token_usage row req=wtq04-main-l3-r1-07-8b6372
- RED: L3/L3-r1-10: billing_persistence_loss tokens=14110 receipt_usd=0.001411 but no token_usage row req=wtq04-main-l3-r1-10-8165db
- RED: L3/L3-r1-11: billing_persistence_loss tokens=3239 receipt_usd=0.000324 but no token_usage row req=wtq04-main-l3-r1-11-5e6da7
- RED: L3/L3-r1-12: billing_persistence_loss tokens=13998 receipt_usd=0.001400 but no token_usage row req=wtq04-main-l3-r1-12-d7e6c4
- RED: L3/L3-r1-14: billing_persistence_loss tokens=3042 receipt_usd=0.000304 but no token_usage row req=wtq04-main-l3-r1-14-b74756
- RED: L3/L3-r1-16: billing_persistence_loss tokens=13880 receipt_usd=0.001388 but no token_usage row req=wtq04-main-l3-r1-16-b71e2d
- RED: L3/L3-r1-19: billing_persistence_loss tokens=1544 receipt_usd=0.000154 but no token_usage row req=wtq04-main-l3-r1-19-52543d
- RED: L3/L3-r1-20: billing_persistence_loss tokens=3457 receipt_usd=0.000346 but no token_usage row req=wtq04-main-l3-r1-20-a42cd0
- RED: L3/L3-r2-04: fully_unmetered_delivered 无usage帧且无token_usage行 req=wtq04-main-l3-r2-04-de4274
- RED: L3/L3-r2-05: billing_persistence_loss tokens=2007 receipt_usd=0.000201 but no token_usage row req=wtq04-main-l3-r2-05-bf2704
- RED: L3/L3-r2-06: billing_persistence_loss tokens=15501 receipt_usd=0.001550 but no token_usage row req=wtq04-main-l3-r2-06-821672
- RED: L3/L3-r2-08: billing_persistence_loss tokens=4629 receipt_usd=0.000463 but no token_usage row req=wtq04-main-l3-r2-08-fe113a
- RED: L3/L3-r2-09: fully_unmetered_delivered 无usage帧且无token_usage行 req=wtq04-main-l3-r2-09-874ba4
- RED: L3/L3-r2-10: billing_persistence_loss tokens=1635 receipt_usd=0.000164 but no token_usage row req=wtq04-main-l3-r2-10-df6553
- RED: L3/L3-r2-15: billing_persistence_loss tokens=3895 receipt_usd=0.000390 but no token_usage row req=wtq04-main-l3-r2-15-3b100c
- RED: L3/L3-r2-16: billing_persistence_loss tokens=14067 receipt_usd=0.001407 but no token_usage row req=wtq04-main-l3-r2-16-7e6c8c
- RED: L3/L3-r2-17: billing_persistence_loss tokens=3118 receipt_usd=0.000312 but no token_usage row req=wtq04-main-l3-r2-17-298a0b
- RED: L3/L3-r2-18: billing_persistence_loss tokens=14213 receipt_usd=0.001421 but no token_usage row req=wtq04-main-l3-r2-18-2257e6
- RED: L3/L3-r3-09: fully_unmetered_delivered 无usage帧且无token_usage行 req=wtq04-main-l3-r3-09-c82940
- RED: L3/L3-r4-09: fully_unmetered_delivered 无usage帧且无token_usage行 req=wtq04-main-l3-r4-09-832025

注：隐藏辅助调用（Layer3 意图分类/sufficiency/HyDE/router embedding）不在 token_usage
计量范围——本表口径为「主生成计量成本」；辅助调用无计量即属漏计费面，
以 token_usage 行数与 attempt 数的差异另报（见 run_manifest.attempt_reconciliation）。

---

## 一审勘误注记（wtQ04R1 PASS_WITH_CHALLENGES；本文件为采集时点快照，原始行未改动）

本文件 generated=23:43:12 的 join 读数早于/部分早于终态库，一审共享库复验订正：
- fully_unmetered_delivered 合计 **14→12**（L3 4→2：L3-r3-09/L3-r4-09 已于 23:05:20/25 落库，本表该两行为采集竞态伪象——C-2）。
- 上方「billing_persistence_loss」152 行仍成立（终态仍无库行，红项④不变）。
- 辅助调用对账键 run_manifest.attempt_reconciliation 系一审 C-6 勘误补记（交付时不存在）。

权威口径以 run_manifest.json / diff_or_evidence_only.md 勘误值为准。