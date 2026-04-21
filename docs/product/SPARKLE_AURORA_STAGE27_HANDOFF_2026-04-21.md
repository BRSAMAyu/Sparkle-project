# SPARKLE Aurora Stage 27 Handoff

日期：2026-04-21  
阶段：Stage 27 / Foresight Engine  
状态：Implementation complete, Stage 27 gate green

## 1. Final Accept Matrix

| Workstream / Gate | Status | Evidence |
| --- | --- | --- |
| WS-FS-EXTEND | PASS | `backend/app/services/predictive_service.py`, `backend/app/schemas/foresight.py`, 60s cache, `test_foresight_snapshot_schema.py`, `test_predictive_service_extension.py` |
| WS-FS-ATTRACTOR | PASS | `backend/app/services/persdyn_attractor_service.py`, `backend/app/models/aurora_stage27.py`, Alembic `s27a1b2c3d4`, Celery daily recompute, `test_persdyn_attractor_service.py`, `test_attractor_cold_start.py` |
| WS-FS-DEVIATION | PASS | `backend/app/services/foresight_deviation_service.py`, z-score threshold `1.5`, 3-day projection, `test_deviation_detector.py` |
| WS-FS-JITAI | PASS | `backend/app/services/jitai_trigger_service.py`, template registry, 24h cooldown, daily budget `<=3`, auto-downgrade, `test_jitai_trigger.py`, `test_jitai_budget_cooldown.py`, `test_jitai_template_no_llm.py` |
| WS-FS-GUARD | PASS | `state_aggregator` `v1.8 foresight_hint`, mobile read-only display, Stage 27 guard scripts, kill-switches, `test_aggregator_schema_v1_8.py`, `test_foresight_kill_switch.py`, `test_rule_al_not_router.py`, `test_foresight_router_zero_hit.py`, `test_persdyn_user_isolation.py` |
| Gate S27-FINAL | PASS | `bash scripts/stage27/gate_final.sh` green; backend Stage 27 matrix `56 passed`; mobile Stage 27 matrix `3 passed`; all Stage 27 governance scripts green |

## 2. Path Selection + Reason

选择：Path A

说明：
- `PredictiveService.build_foresight_snapshot()`、PersDyn attractor、deviation、JITAI、Aggregator `v1.8 foresight_hint`、mobile 只读展示、Rule AL guard、kill-switch 已全部落地。
- 运行时默认仍是安全态：`AURORA_FORESIGHT_MODE=off`。功能已具备 Path A 全量能力，但是否 live rollout 仍由主开关显式控制。
- `foresight_hint` 仅注入 prompt caveat，不进入任何 Router 分支条件。

## 3. PersDyn 5 维登记快照

登记文档：
- `docs/aurora/rule_al_persdyn_dimensions.md`

实现白名单：
- `study_pace`
- `completion_rate`
- `engagement_level`
- `mood_valence`
- `plan_adherence`

参数估计公式：
- `baseline`: EMA, `ema_t = 0.1 * x_t + 0.9 * ema_(t-1)`
- `variability`: latest 14-day population stddev
- `recovery_rate`: `max(0, -slope(abs(x_t - baseline)))`
- `confidence`: `<14` active days capped below `0.3`; `14-28` days linearly ramps to `0.95`

落地文件：
- `backend/app/services/persdyn_attractor_service.py`
- `backend/app/models/aurora_stage27.py`
- `backend/alembic/versions/s27a1b2c3d4_add_persdyn_attractors.py`

## 4. JITAI 模板库快照

登记文档：
- `docs/aurora/stage27_jitai_templates.md`

已登记模板数：`10`

模板覆盖：
- `study_pace`: above / below
- `completion_rate`: above / below
- `engagement_level`: above / below
- `mood_valence`: above / below
- `plan_adherence`: above / below

治理约束：
- 模板纯规则拼接，零 LLM
- 单条文案 `<= 80` 字符
- `scripts/stage27/check_jitai_template_registry.py` 对文档与代码做一致性校验

## 5. SQAM 四维证据

| 维度 | Status | Evidence |
| --- | --- | --- |
| ID1 | PASS | 5 个维度固定登记于 `rule_al_persdyn_dimensions.md`；`PersDynAttractorService.DIMENSIONS` 与模板/测试一致；事件名唯一：`attractor_updated`、`jitai_triggered` |
| ST1 | PASS | `test_foresight_snapshot_schema.py::test_foresight_snapshot_uses_sixty_second_cache`；`build_foresight_snapshot()` 对同 user 同模式命中同一 cache key，纯统计路径稳定 |
| DP1 | PASS | 冷启动过滤：`test_attractor_cold_start.py` 3/3 green；合成收敛数据见第 6 节，平均 variability 斜率 `< 0` |
| SM1 | PASS | Metrics wired: `sparkle_foresight_snapshot_generated_total`, `sparkle_foresight_snapshot_latency_seconds`, `sparkle_persdyn_attractor_updated_total`, `sparkle_foresight_deviation_detected_total`, `sparkle_jitai_triggered_total`, `sparkle_jitai_skipped_total` |

## 6. Attractor 收敛性实测

本地 synthetic convergence run（前 14 天高波动，后 14 天稳定）：

| Checkpoint | Avg Variability |
| --- | --- |
| `2026-04-07` | `0.6169` |
| `2026-04-14` | `0.2367` |
| `2026-04-21` | `0.1863` |

平均 variability slope：`-0.2153`

补充说明：
- 这是本地 in-memory synthetic harness，不是生产流量回放。
- 结果满足 Stage 27 DP1 目标：14 天后 variability 下降斜率 `< 0`。

## 7. JITAI 误触发率实测

本地 synthetic runs：

基线 run：
- `triggered = 3`
- `misfires = 0`
- `misfire_rate = 0.0`
- mode 保持：`deviation=live`, `jitai=live`

降级演练 run：
- 连续 3 日，每日 `triggered = 10`, `misfires = 2`
- 3 日 misfire rates: `[0.2, 0.2, 0.2]`
- 自动降级结果：`deviation=shadow`, `jitai=shadow`

实现补丁：
- `JITAITrigger.RATE_RETENTION_DAYS = 4`
- 目的：确保连续 3 日误触发窗口在 rate counter 层面可观测，不会在次日零点前被提早清空

## 8. Aggregator v1.8 Diff + Proto 三端同步证据

Aggregator schema diff：
- `backend/app/state_aggregator/schema.py`
  - `user_state.v1.7` -> `user_state.v1.8`
  - 新增 `ForesightConfidenceItemValue`
  - 新增 `ForesightHintSummaryValue`
  - 新增 `foresight_hint`
- `backend/app/state_aggregator/service.py`
  - `FIELD_TTLS_SECONDS["foresight_hint"] = 30`
  - 新增 `_build_foresight_hint_summary()`

API / surface diff：
- `backend/app/api/v1/memory.py`
  - 新增 `/memory/accountability/foresight-hint`
- `backend/app/api/v1/accountability.py`
  - dashboard 新增 `foresight_hint`
- `mobile/lib/features/memory/presentation/screens/memory_panel_screen.dart`
  - 只读展示“前瞻提示”
- `mobile/lib/features/community/presentation/screens/accountability_detail_screen.dart`
  - 只读展示 foresight card

Proto diff：
- `proto/user_state.proto`
  - 新增 `ForesightConfidenceItemValue`
  - 新增 `ForesightHintSummaryValue`
  - 新增 `ForesightHintSummaryField`
  - `UserStateV1.foresight_hint = 14`

Proto sync evidence：
- `make proto-gen` green
- dockerized toolchain pull failed on `sparkle/proto-toolchain:latest`
- host toolchain fallback succeeded
- generated outputs verified in:
  - `backend/gateway/gen/userstate/v1/user_state.pb.go`
  - `mobile/lib/gen/user_state.pb.dart`
  - `mobile/lib/gen/user_state.pbjson.dart`

## 9. Router 分支 0 命中证据

Rule AL evidence：
- `scripts/stage27/check_rule_al_foresight_not_router.py` green
- `backend/tests/unit/test_rule_al_not_router.py` `2 passed`
- `backend/tests/unit/test_foresight_router_zero_hit.py` `2 passed`

静态约束：
- Router tree 未引用 `foresight_hint`
- Router tree 未引用 `attractors`
- Router tree 未引用 `deviations`
- Router tree 未调用 `build_foresight_snapshot()`

## 10. 跨用户攻击用例清单 + 阻断证据

覆盖攻击面：
1. PersDyn snapshot 读取其他用户 attractor rows
2. attractor upsert 覆盖其他用户维度行
3. `build_current_observation()` 混入其他用户行为信号
4. 空 user_id / 非 owner 查询进入 Stage 27 路径

阻断证据：
- `backend/tests/unit/test_persdyn_user_isolation.py` `4 passed`
- `scripts/stage27/check_persdyn_user_isolation.py` green
- `PersDynAttractorService` 查询全部强制 `user_id == owner`
- `PredictiveService` / `PersDynAttractorService` / `JITAITrigger` 均要求非空 `user_id`

## 11. 测试精确计数 + Guard 清单

Stage 27 gate：
- backend: `56 passed`
- mobile: `3 passed`

Extra regression evidence：
- Stage 26 gate rerun: backend `46 passed`, mobile `3 passed`
- targeted smoke: `test_memory_inferred_write_lane.py` + `test_aggregator_schema_v1_6.py` => `7 passed`

Key Stage 27 test files：
- `test_foresight_snapshot_schema.py` `5 passed`
- `test_predictive_service_extension.py` `4 passed`
- `test_persdyn_attractor_service.py` `9 passed`
- `test_attractor_cold_start.py` `3 passed`
- `test_deviation_detector.py` `6 passed`
- `test_jitai_trigger.py` `8 passed`
- `test_jitai_budget_cooldown.py` `4 passed`
- `test_jitai_template_no_llm.py` `2 passed`
- `test_aggregator_schema_v1_8.py` `3 passed`
- `test_foresight_kill_switch.py` `4 passed`
- `test_rule_al_not_router.py` `2 passed`
- `test_foresight_router_zero_hit.py` `2 passed`
- `test_persdyn_user_isolation.py` `4 passed`

Governance guards：
- `scripts/stage27/check_rule_al_foresight_not_router.py`
- `scripts/stage27/check_foresight_no_llm_import.py`
- `scripts/stage27/check_persdyn_user_isolation.py`
- `scripts/stage27/check_jitai_template_registry.py`
- `scripts/stage27/gate_final.sh`

## 12. Stage 28 前置条件清单

已满足：
1. `PredictiveService` 已统一暴露 `build_foresight_snapshot()`
2. Scene / Reflection 已成为 PersDyn 输入源
3. Foresight 已被严格锁定在 prompt caveat surface
4. kill-switch 主开关 + 3 个子开关已落地
5. JITAI 模板库、维度登记、Rule AL 静态 guard 已接好

Stage 28 建议承接：
1. 在不碰 Router 的前提下，为 prompt composer 增加更细的 caveat 注入策略
2. 将 `jitai.triggered/skipped` 与运营观测面板联通，开始记录真实误触发率
3. 若准备 rollout，先保持 `AURORA_FORESIGHT_MODE=off`，在真实流量上走 `shadow` 观测后再切 `live`
4. 若需要更强实证，补生产样本回放 benchmark，而不是继续只依赖 synthetic harness

## Appendix. Performance Snapshot

本地 synthetic benchmark（20 users / 28-day seeded histories / single snapshot per user）：
- `p50_ms = 14.012`
- `p95_ms = 20.801`
- `max_ms = 27.302`

说明：
- benchmark 使用 in-memory sqlite + seeded Stage 25/26 style signals
- 已满足 Stage 27 snapshot `p95 <= 150ms` 目标
