# G-05 Galaxy 规模梯度性能汇总（wt395）

- generated_at: 2026-09-25T16:18:41.921127+00:00
- seed: 20260925 ｜ samples/操作: 30（p50/p95 口径 ≥30）
- 数据: 真实 ORM 行 + 真实 DashScope embedding（skip=False）
- 基线口径: 本机 Apple Silicon 容器栈（PG16+Redis 本地）headless 服务级时延; 非真机 FPS

## 规模梯度（ms）

| scale | 操作 | n | p50 | p95 | max | 备注 |
|---|---|---|---|---|---|---|
| 50 | graph_cold | 30 | 20.49 | 29.23 | 218.81 | nodes=50 errors=0 |
| 50 | graph_warm | 30 | 3.01 | 5.49 | 8.7 |  |
| 50 | graph_lod_zoom03 | 30 | 2.07 | 16.41 | 116.98 | lod_nodes=39/50 shrunk=True |
| 50 | graph_viewport_window | 30 | 12.59 | 16.46 | 19.58 | capped800=True nodes=50 |
| 50 | user_stats | 30 | 3.14 | 4.82 | 5.61 |  |
| 50 | predict_next_node | 30 | 5.92 | 10.58 | 12.96 |  |
| 50 | node_detail_grpc | 30 | 6.86 | 11.35 | 15.5 | errors=0 |
| 50 | learning_path_near | 30 | 2.57 | 3.27 | 3.42 |  |
| 50 | learning_path_far | 30 | 3.62 | 5.13 | 5.5 | path_found=True errors=0 |
| 50 | semantic_search | 30 | 9.43 | 352.01 | 415.86 | avg_hits=1.6 errors=0 |
| 500 | graph_cold | 30 | 70.78 | 197.34 | 206.33 | nodes=500 errors=0 |
| 500 | graph_warm | 30 | 16.98 | 150.61 | 195.12 |  |
| 500 | graph_lod_zoom03 | 30 | 9.85 | 33.29 | 235.4 | lod_nodes=336/500 shrunk=True |
| 500 | graph_viewport_window | 30 | 44.21 | 333.57 | 408.14 | capped800=True nodes=500 |
| 500 | user_stats | 30 | 5.52 | 7.54 | 8.27 |  |
| 500 | predict_next_node | 30 | 17.24 | 37.5 | 41.06 |  |
| 500 | node_detail_grpc | 30 | 8.42 | 11.53 | 35.38 | errors=0 |
| 500 | learning_path_near | 30 | 8.05 | 11.68 | 499.55 |  |
| 500 | learning_path_far | 30 | 7.95 | 10.6 | 11.6 | path_found=True errors=0 |
| 500 | semantic_search | 30 | 7.07 | 11.97 | 14.24 | avg_hits=1.6 errors=0 |
| 5000 | graph_cold | 30 | 876.01 | 1235.46 | 1402.39 | nodes=5000 errors=0 |
| 5000 | graph_warm | 30 | 125.54 | 823.79 | 1283.54 |  |
| 5000 | graph_lod_zoom03 | 30 | 81.15 | 2339.45 | 4057.86 | lod_nodes=3308/5000 shrunk=True |
| 5000 | graph_viewport_window | 30 | 59.89 | 82.99 | 87.47 | capped800=True nodes=800 |
| 5000 | user_stats | 30 | 3.92 | 6.31 | 7.59 |  |
| 5000 | predict_next_node | 30 | 4.9 | 7.63 | 8.61 |  |
| 5000 | node_detail_grpc | 30 | 3.07 | 3.98 | 5.99 | errors=0 |
| 5000 | learning_path_near | 30 | 25.52 | 38.5 | 4377.8 |  |
| 5000 | learning_path_far | 30 | 25.76 | 1141.24 | 2045.78 | path_found=False errors=0 |
| 5000 | semantic_search | 30 | 4.56 | 12.61 | 30.48 | avg_hits=1.0 errors=0 |

## 恢复风暴

- 冷缓存重连风暴: clients=16 rounds=5 ｜ 80 采样 p50=395.34 p95=666.64 max=709.71 errors=0 ｜ 节点数一致=True
- 尾部有界(最慢客户端 ≤ 冷缓存首拉 SLA 5000ms): max=709.71ms → True ｜ 观测: max/单发冷中位=1.31× ｜ 风暴后热取 78.31ms
- 多端 CRDT 并发同步: 16 次 p50=141.63 p95=141.78 errors=0 ｜ 风暴后 restore 合并态 16/16 台设备可读=True
- 混合数据面风暴(2×clients): p50=49.27 p95=800.4 max=844.97 errors=0

## graceful 降级断言

- vector_down_returns_empty_no_raise: True
- vector_down_semantic_search_no_raise: True
- vector_fuse_blown_after_not_configured: True
- keyword_fallback_still_works: True
- keyword_probe_keyword: transformer
- blocked_prereq_projection_runs: True

## 阈值判定（声明依据见 THRESHOLDS 与 raw_scale_perf.json）

- [PASS] 冷缓存图取数 p95≤2500ms @50 — p95=29.23ms
- [PASS] 冷缓存零错误且全图一致 @50 — errors=0
- [PASS] 热缓存图取数 p95≤800ms @50 — p95=5.49ms
- [PASS] viewport≤800 上限 @50 — nodes=50
- [PASS] 学习路径 p95≤500ms @50 — p95=5.13ms p50=3.62ms; 离群(>1s) far=0/30 near=0/30
- [PASS] 节点详情零错误 @50 — errors=0
- [PASS] 语义搜索(真实embedding) p95≤2000ms @50 — p95=352.01ms
- [PASS] 语义 top1 命中率≥0.6 @50 — hit_rate=1.0 off_domain_zero=1.0
- [PASS] 冷缓存图取数 p95≤2500ms @500 — p95=197.34ms
- [PASS] 冷缓存零错误且全图一致 @500 — errors=0
- [PASS] 热缓存图取数 p95≤800ms @500 — p95=150.61ms
- [PASS] LOD zoom<0.5 收窄 @500 — lod=336<full=500
- [PASS] viewport≤800 上限 @500 — nodes=500
- [PASS] 学习路径 p95≤500ms @500 — p95=10.6ms p50=7.95ms; 离群(>1s) far=0/30 near=0/30
- [PASS] 节点详情零错误 @500 — errors=0
- [PASS] 语义搜索(真实embedding) p95≤2000ms @500 — p95=11.97ms
- [PASS] 语义 top1 命中率≥0.6 @500 — hit_rate=1.0 off_domain_zero=1.0
- [PASS] 冷缓存图取数 p95≤5000ms @5000 — p95=1235.46ms
- [PASS] 冷缓存零错误且全图一致 @5000 — errors=0
- [FAIL] 热缓存图取数 p95≤800ms @5000 — p95=823.79ms
- [PASS] LOD zoom<0.5 收窄 @5000 — lod=3308<full=5000
- [PASS] viewport≤800 上限 @5000 — nodes=800
- [FAIL] 学习路径 p95≤500ms @5000 — p95=1141.24ms p50=25.76ms; 离群(>1s) far=2/30 near=1/30
- [PASS] 节点详情零错误 @5000 — errors=0
- [PASS] 语义搜索(真实embedding) p95≤2000ms @5000 — p95=12.61ms
- [PASS] 语义 top1 命中率≥0.6 @5000 — hit_rate=0.6 off_domain_zero=1.0
- [PASS] 重连风暴零错误且数据一致 — errors=0
- [PASS] 重连风暴尾部有界 — max=709.71ms
- [PASS] CRDT 风暴零错误且合并态可读 — restored=16/16
- [PASS] 混合风暴零错误 — errors=0
- [PASS] graceful: vector_down_returns_empty_no_raise — True
- [PASS] graceful: vector_down_semantic_search_no_raise — True
- [PASS] graceful: vector_fuse_blown_after_not_configured — True
- [PASS] graceful: keyword_fallback_still_works — True
- [PASS] graceful: blocked_prereq_projection_runs — True

总计 35 项判定, FAIL=2
