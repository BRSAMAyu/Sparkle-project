# SPARKLE Aurora Stage 26 Handoff

日期：2026-04-21  
阶段：Stage 26 / Scene Consolidation  
状态：Implementation complete, gate green

## 1. Final Accept Matrix

| Workstream / Gate | Status | Evidence |
| --- | --- | --- |
| WS-SC-MODEL | PASS | `Scene` ORM, Alembic `s26a1b2c3d4`, Pydantic scene schemas, stable hash contract, `test_scene_model.py` |
| WS-SC-CLUSTER | PASS | `backend/app/services/scene_consolidation_service.py`, Rule AK dual-parameter merge logic, batch backfill, `test_scene_cluster_incremental.py`, `test_scene_cluster_algorithm_constraint.py` |
| WS-SC-QUALITY | PASS | Rule-based title/summary, `quality_score` function, aggregator filtering, telemetry, `test_scene_quality_score.py`, `test_scene_title_rule_based.py` |
| WS-SC-AGGREGATOR | PASS | `user_state.v1.7`, `recent_scenes`, proto regen, `/memory/accountability/recent-scenes`, mobile memory panel block, `test_aggregator_schema_v1_7.py`, `scene_recent_summary_test.dart` |
| WS-SC-KILL | PASS | `AURORA_SCENE_MODE`, runtime toggle service, auto downgrade, governance scripts, `bash scripts/stage26/gate_final.sh`, `test_scene_kill_switch.py`, `test_scene_auto_downgrade.py`, `test_rule_ak_algorithm_constraint.py` |
| Gate S26-FINAL | PASS | `bash scripts/stage26/gate_final.sh` green; backend scene matrix `46 passed`; mobile recent scene matrix `3 passed` |

## 2. Path Selection + Reason

选择：Path A

说明：
- Scene 模型、增量聚类、质量评分、Aggregator `v1.7 recent_scenes`、mobile 只读展示、kill-switch 与自动降级都已落地。
- 运行时默认仍为 `AURORA_SCENE_MODE=off`，用于安全上线；切到 `live` 后即进入 Path A 全量能力，切到 `shadow` 即自动回落 Path B。

## 3. Algorithm Lock

选型：threshold-based incremental clustering

锁定参数：
- Similarity threshold：`0.75`
- Time window：`72h`
- Aggregator quality threshold：`0.6`
- Centroid update strategy：算术平均（full member re-read + mean embedding），不使用 EMA
- Algorithm version：`scene.v1`

Rule AK compliance:
- 同时要求 similarity threshold + time window，任一缺失即 `ValueError`
- 禁止 K 类算法：`scripts/stage26/check_rule_ak_algorithm_constraint.py`
- `scene_id = sha256(user_id | algorithm_version | sorted(member_memory_ids))`
- 标题/摘要完全规则拼接，无 LLM import / 无 LLM call
- 仅按 `user_id` 查询候选 scene，且对成员 memory 再做一次 user_id 校验

## 4. SQAM Evidence

| 维度 | Evidence |
| --- | --- |
| ID1 | `test_scene_idempotency.py` 4/4 green；`scripts/stage26/check_scene_idempotency.py` green |
| ST1 | `test_scene_cluster_incremental.py::test_scene_backfill_groups_history_deterministically` 与 `test_scene_idempotency.py::test_backfill_three_replays_produce_same_scene_set` |
| DP1 | 合成 100-event baseline: `quality_avg=0.95`, `filtered_rate=0.0` |
| SM1 | Metrics wired: `sparkle_scene_created_total`, `sparkle_scene_merged_total`, `sparkle_scene_quality_avg`, `sparkle_scene_filtered_below_threshold_total`, `sparkle_cluster_latency_seconds`, `sparkle_cluster_batch_throughput`, plus `sparkle_scene_quality_distribution` |

## 5. Quality Distribution Measurement

合成基线（100 events / 2 semantic scenes / sqlite test harness）：
- `scene_count = 2`
- `quality_avg = 0.95`
- `filtered_rate = 0.0`
- `single_event_p95_ms = 4.845`
- `batch_100_total_ms = 348.791`

说明：
- 这是本地 synthetic benchmark，不是线上生产流量回放。
- 已满足 Stage 26 目标阈值：single-event p95 `< 80ms`、100-event batch `< 5s`。

## 6. Idempotency Regression Evidence

稳定性证据：
- `build_scene_id()` 对 member order 去序、去重后稳定输出
- 同一流重复处理不会新增重复 scene
- backfill 连续 3 次重跑得到相同 scene 集
- algorithm version 变化会显式生成不同 `scene_id`

相关文件：
- `backend/tests/unit/test_scene_idempotency.py`
- `scripts/stage26/check_scene_idempotency.py`

## 7. Aggregator v1.7 Diff + Proto Sync

Schema diff:
- `backend/app/state_aggregator/schema.py`
  - `user_state.v1.6` -> `user_state.v1.7`
  - 新增 `RecentSceneItemValue`
  - 新增 `RecentScenesSummaryValue`
  - 新增 `recent_scenes`
- `backend/app/state_aggregator/service.py`
  - `FIELD_TTLS_SECONDS["recent_scenes"] = 30`
  - 新增 `_build_recent_scenes_summary()`

Proto diff:
- `proto/user_state.proto`
  - 新增 `RecentSceneItemValue`
  - 新增 `RecentScenesSummaryValue`
  - 新增 `RecentScenesSummaryField`
  - `UserStateV1.recent_scenes = 13`

Sync evidence:
- `make proto-gen` succeeded
- Dockerized toolchain fallback failed pulling `sparkle/proto-toolchain:latest`
- Host toolchain fallback succeeded and synced generated stubs
- Generated outputs updated in:
  - `backend/app/gen/...`
  - `backend/gateway/gen/...`
  - `mobile/lib/gen/...`

## 8. Cross-User Attack Cases + Blocking Evidence

覆盖的攻击面：
1. 外部 scene 候选伪装为高相似度，尝试被另一用户 memory 合并
2. scene 中混入 foreign `member_memory_ids`
3. Aggregator recent scene 拉取跨用户泄漏
4. `expected_user_id` 与 scene owner 不匹配时的错误访问

阻断证据：
- `backend/tests/unit/test_scene_user_isolation.py` 4/4 green
- `scripts/stage26/check_scene_user_isolation.py` green
- `SceneConsolidationService.assert_scene_user_isolation()` 在 merge/read 路径上做硬校验

## 9. Test Counts + Guard Inventory

Backend scene matrix:
- `46 passed`

Extra regression smoke:
- `test_aggregator_schema_v1_6.py` `3 passed`
- `test_memory_inferred_write_lane.py` `4 passed`

Mobile:
- `scene_recent_summary_test.dart` `3 passed`
- memory panel related regression smoke green:
  - `memory_panel_v2_test.dart`
  - `memory_panel_screen_test.dart`
  - `features/memory/presentation/screens/memory_panel_screen_test.dart`
  - `features/memory/presentation/widgets/subject_type_filter_test.dart`

Governance guards:
- `scripts/stage26/check_rule_ak_algorithm_constraint.py`
- `scripts/stage26/check_scene_idempotency.py`
- `scripts/stage26/check_scene_user_isolation.py`
- `scripts/stage26/check_scene_no_llm_import.py`
- `scripts/stage26/gate_final.sh`

## 10. Stage 27 Preconditions

已满足：
- Scene 只读 Aggregator surface 已稳定
- recent scene summaries 已进入 mobile memory panel
- quality threshold / downgrade path / runtime mode 已成型
- Rule AK 治理 guard 已接入

Stage 27 建议直接承接：
1. 让 Foresight / JITAI 只读消费 `recent_scenes`
2. 增加 scene-level trend / recurrence signal，不改写 Router
3. 如果需要线上 rollout，先把 `AURORA_SCENE_MODE` 从 `off` 切 `shadow`，确认质量均值与 filtered rate，再切 `live`
4. 如需真实生产基线，补线上样本回放 benchmark，而不是继续依赖 synthetic benchmark
