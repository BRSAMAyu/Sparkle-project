# SPARKLE Aurora Stage 28 Handoff

版本：v2.2 最终交付  
日期：2026-04-21  
阶段：Stage 28 Dispatch — Traits 弱先验

## 1. Final Accept Matrix

### 1.1 Workstream Matrix

| WS | 状态 | 证据 |
| --- | --- | --- |
| WS-TR-MODEL | PASS | `backend/app/core/user_insight_state.py` 新增 `BigFiveDimension` / `BigFiveTraits` / `UserInsightState.traits_prior` / `traits_coldstart_completed_at`；`backend/alembic/versions/s28a1b2c3d4_add_traits_prior_to_user_preferences.py`；`proto/user_state.proto` |
| WS-TR-NLP-OBSERVE | PASS | `backend/app/services/traits_nlp_observer_service.py`、`backend/app/services/traits_merge_service.py`、`backend/app/services/traits_bias_calibration.py`；`test_traits_nlp_observer.py`、`test_nlp_bias_calibration.py`、`test_nlp_single_call_no_direct_write.py` |
| WS-TR-COLDSTART | PASS | `backend/app/services/traits_coldstart_service.py`、`backend/app/api/v1/profile_transparency.py`、`mobile/lib/features/user/presentation/widgets/traits_coldstart_questionnaire.dart`；`docs/aurora/stage28_coldstart_questions.md` |
| WS-TR-AGGREGATOR | PASS | `backend/app/state_aggregator/schema.py` v1.9、`backend/app/state_aggregator/service.py`、`proto/user_state.proto`、`mobile/lib/features/user/presentation/widgets/traits_prior_card.dart` |
| WS-TR-GUARD | PASS | `scripts/stage28/check_rule_am_confidence_cap.py`、`check_trait_not_router.py`、`check_nlp_no_direct_write.py`、`check_trait_user_isolation.py`、`check_nlp_bias_calibration.py`、`check_traits_no_diagnostic_labels.py`、`gate_final.sh` |

### 1.2 Gate Matrix

| Gate 项 | 状态 | 备注 |
| --- | --- | --- |
| 5 WS PASS | PASS | 本地实现与定向测试均完成 |
| SQAM 四维 | PASS | 见第 6 节 |
| Backend 测试 ≥53 | PASS | 定向 Stage 28 套件 `53 passed` |
| Mobile 测试 ≥7 | PASS | `7 passed` |
| Governance guards 全绿 | PASS | `scripts/stage28/gate_final.sh` 全绿 |
| Baseline 回归 Stage 17-27 0 回归 | NOT FULLY RUN LOCAL | 本地未复跑全仓历史回归，仅完成 Stage 28 定向套件与 gate |
| confidence 超限用例 100% 拒绝写入 | PASS | `test_confidence_cap_enforcement.py` + Rule AM guard |
| Router 分支命中 traits 0 次 | PASS | 静态扫描 + 单测 |
| NLP 单次调用直接写 trait 0 次 | PASS | 架构隔离 + 单测 + guard |
| NLP 跨文化偏差率 <10% | PASS | 本地校准 `bias_rate = 0.0` |
| 跨用户攻击 100% 阻断 | PASS | 4 条隔离测试通过 |
| kill-switch 主+2子开关演练 | PASS | `test_traits_kill_switch.py` |
| 冷启动 3 问设计登记 | PASS | `docs/aurora/stage28_coldstart_questions.md` |
| 跨文化校准集登记 ≥5 样本 | PASS | `docs/aurora/stage28_nlp_bias_calibration.md` |
| 人格诊断标签扫描 0 命中 | PASS | `check_traits_no_diagnostic_labels.py` 通过 |

## 2. Path 选择 + 理由

本次交付选择 **Path A**。

理由：
- Model、ColdStart、NLP-Observe、Aggregator、Guard 五条链路均已落地。
- NLP 校准基线实测 `sample_count = 5`、`mismatches = 0`、`total_checks = 10`、`bias_rate = 0.0`，未触发 Path B。
- 主/子 kill-switch 与自动降级已完成实现与定向测试，未触发 Path C。

保留说明：
- 本地未执行 Stage 17-27 全量历史回归，因此最终大回归状态应以 CI 为准。

## 3. Big Five 字段冻结 + confidence 类型级约束证据

### 3.1 字段冻结

`UserInsightState` 扩展字段：
- `traits_prior: BigFiveTraits`
- `traits_coldstart_completed_at: str | None`

`BigFiveTraits` 五维冻结为：
- `openness`
- `conscientiousness`
- `extraversion`
- `agreeableness`
- `neuroticism`

每维结构冻结为：
- `value: float[-1, 1]`
- `confidence: float[0, 0.3]`
- `evidence_count: int`
- `last_observed_at`
- `source: 'coldstart' | 'nlp_observed' | 'merged'`

### 3.2 类型级约束证据

约束位置：
- `backend/app/core/user_insight_state.py`
- `BigFiveDimension.validate_value`
- `BigFiveDimension.validate_confidence`
- `BigFiveDimension.validate_evidence_count`

实测证据：
- `test_big_five_model.py`
- `test_confidence_cap_enforcement.py`
- 边界通过：`confidence == 0.3`
- 超限拒绝：`confidence == 0.31`

### 3.3 迁移证据

- Alembic migration：`backend/alembic/versions/s28a1b2c3d4_add_traits_prior_to_user_preferences.py`
- 迁移链已修正到 `down_revision = "s27a1b2c3d4"`
- 本地执行 `cd backend && .venv/bin/alembic heads` 结果：`s28a1b2c3d4 (head)`

## 4. 冷启动 3 问问卷登记快照

登记文件：
- `docs/aurora/stage28_coldstart_questions.md`

问卷快照：
1. 开始新目标时，你更像哪种方式？
   映射：`openness`、`conscientiousness`
2. 遇到难题时，你更容易从哪里补能量？
   映射：`extraversion`、`agreeableness`
3. 当计划被打乱时，你通常最先出现什么反应？
   映射：`neuroticism`、`conscientiousness`

设计约束：
- 纯选项式，不开放自由填空
- 每题均含 `skip`
- 跳过后 `traits_prior` 保持空值路径
- 冷启动单维初始 `confidence <= 0.2`

落地位置：
- Backend：`backend/app/services/traits_coldstart_service.py`
- API：`backend/app/api/v1/profile_transparency.py`
- Mobile：`mobile/lib/features/user/presentation/widgets/traits_coldstart_questionnaire.dart`

## 5. NLP 跨文化校准集快照 + 偏差率实测

登记文件：
- `docs/aurora/stage28_nlp_bias_calibration.md`

当前校准集：
- `zh-CN / structured_planner`
- `en-US / social_energized`
- `ja-JP / quiet_reflective`
- `es-ES / steady_low_dramatic`
- `ar / warm_collaborative`

实测结果：
- `sample_count = 5`
- `mismatches = 0`
- `total_checks = 10`
- `bias_rate = 0.0`
- `passed = true`

运行证据：
- `scripts/stage28/check_nlp_bias_calibration.py`
- `backend/tests/unit/test_nlp_bias_calibration.py`
- `bash scripts/stage28/gate_final.sh`

## 6. SQAM 四维证据

| 维度 | 状态 | 证据 |
| --- | --- | --- |
| ID1 | PASS | 五维命名固定；source 固定为 `coldstart / nlp_observed / merged`；字段定义位于 `backend/app/core/user_insight_state.py` |
| ST1 | PASS | merge 规则在 `backend/app/services/traits_merge_service.py` 为确定性逻辑；同输入序列同结果 |
| DP1 | PASS | 校准偏差率 `0.0 < 0.1`；confidence 分布通过 `TRAITS_CONFIDENCE_DISTRIBUTION` 记录 |
| SM1 | PASS | 运行时指标由 `sparkle_traits_coldstart_total`、`sparkle_traits_nlp_observation_total`、`sparkle_traits_merged_total`、`sparkle_traits_confidence_distribution` 落地；`router.hit.zero` 由 guard + test 证据链保证 |

指标映射：
- `coldstart.completed` → `sparkle_traits_coldstart_total{outcome="completed"}`
- `coldstart.skipped` → `sparkle_traits_coldstart_total{outcome="skipped"}`
- `nlp.observed` → `sparkle_traits_nlp_observation_total{outcome="observed"}`
- `nlp.skipped.cooldown` → `sparkle_traits_nlp_observation_total{outcome="cooldown"}`
- `nlp.bias.detected` → `sparkle_traits_nlp_observation_total{outcome="bias_detected"}`
- `trait.merged` → `sparkle_traits_merged_total{source=...}`
- `confidence.distribution` → `sparkle_traits_confidence_distribution`
- `router.hit.zero` → `scripts/stage28/check_trait_not_router.py` + `backend/tests/unit/test_traits_router_zero_hit.py`

## 7. Trait-Dynamic 冲突解析测试矩阵

实现位置：
- `backend/app/services/traits_guardrails.py`
- `resolve_trait_vs_dynamic(trait, dynamic_state) -> dynamic_state`

硬编码原则：
- Traits 与 Dynamic States 冲突时，**Dynamic 永胜**

测试矩阵：
- `test_dynamic_state_wins_for_focus_mode`
- `test_dynamic_state_wins_for_tone_selection`
- `test_dynamic_state_wins_even_when_trait_is_none`
- `test_dynamic_state_wins_even_when_empty`

对应文件：
- `backend/tests/unit/test_trait_dynamic_conflict_resolution.py`

## 8. Aggregator v1.9 diff + proto 同步证据

### 8.1 Aggregator 变更

变更位置：
- `backend/app/state_aggregator/schema.py`
- `backend/app/state_aggregator/service.py`

变更内容：
- schema version：`user_state.v1.8` → `user_state.v1.9`
- 新增 `traits_prior` field envelope
- TTL 固定 `30s`
- 仅输出 `confidence >= 0.1` 的维度
- 输出结构：`{ dim, value, confidence, source }`

### 8.2 Proto 证据

变更位置：
- `proto/user_state.proto`

新增消息：
- `TraitPriorDimensionValue`
- `TraitsPriorSummaryValue`
- `TraitsPriorSummaryField`

`UserStateV1` 新字段：
- `traits_prior = 15`

### 8.3 三端同步证据

已确认：
- Proto source：`proto/user_state.proto`
- Backend 聚合消费：`backend/app/state_aggregator/schema.py`、`backend/app/state_aggregator/service.py`
- Mobile generated stubs：`mobile/lib/gen/user_state.pb.dart`、`mobile/lib/gen/user_state.pbjson.dart`

生成命令：
- `make proto-gen`

本地结果：
- Docker fallback 后 host toolchain 生成成功
- 输出包含：`Synced 8 Python protobuf runtime stubs.`

说明：
- 本 Stage 未观察到 Go gateway 对 `traits_prior` 的直接消费改动，当前用户态展示路径已由 Backend Aggregator + Mobile 端完成闭环。

## 9. Router 分支 0 命中证据

规则：
- Traits 永不进入 Router 分支

证据链：
- Guard：`scripts/stage28/check_trait_not_router.py`
- 单测：`backend/tests/unit/test_traits_router_zero_hit.py`
- 聚合设计：`traits_prior` 为只读 summary，未注入 routing engine

本地结果：
- `Trait router zero-hit check passed`
- `test_router_modules_do_not_read_traits_prior`
- `test_routing_engine_does_not_reference_traits_prior`

## 10. 跨用户攻击用例清单 + 阻断证据

测试文件：
- `backend/tests/unit/test_trait_user_isolation.py`

覆盖用例：
1. 只收集本人 `ChatMessage.user_id == target_user_id` 文本
2. register observation 仅更新目标用户 observation state
3. merge 仅写目标用户 `traits_prior`
4. 多 session 下仍不读取他人文本

补充 guard：
- `scripts/stage28/check_trait_user_isolation.py`

结论：
- 本地 4/4 用例通过
- 跨用户 observation / merge / text collection 均被阻断

## 11. LLM 预算实测（调用次数 / p95 / 成本）

### 11.1 预算约束已落地

配置位置：
- `backend/app/config/settings.py`

当前阈值：
- `AURORA_TRAITS_NLP_COOLDOWN_HOURS = 24`
- `AURORA_TRAITS_NLP_BIAS_THRESHOLD = 0.10`
- `AURORA_TRAITS_NLP_MAX_DAYS = 30`
- `AURORA_TRAITS_NLP_MAX_COST_USD = 0.003`
- `AURORA_TRAITS_NLP_P95_MS_BUDGET = 800`

代码落点：
- 24h 冷却：`backend/app/services/traits_nlp_observer_service.py`
- p95 检测：同文件 `elapsed_ms > settings.AURORA_TRAITS_NLP_P95_MS_BUDGET`
- 自动降级：`backend/app/services/aurora_stage28_traits_kill_switch_service.py`

### 11.2 本地实测边界

本地已确认：
- 单用户最多 1 次 / 24h 由代码硬约束
- 温度固定 `temperature = 0.2`
- 单次调用不直写 trait，只产 observation candidate

本地未完成：
- 无真实线上样本的调用次数 / 成本 / p95 统计快照
- 因此成本与延迟在本 handoff 中为“预算已布防”，非“生产流量实测”

结论：
- 预算 guard 已落地
- 生产实测应由 Stage 28 上线后 telemetry 补齐

## 12. 类型化判断标签扫描证据

Guard：
- `scripts/stage28/check_traits_no_diagnostic_labels.py`

本地结果：
- `No diagnostic labels detected`

文档/Prompt 约束：
- NLP system prompt 仅允许输出 Big Five 候选增量
- 冷启动文档与校准文档统一改为“行为倾向”描述，不输出类型化判断

## 13. 测试精确计数 + guard 清单

### 13.1 Backend Tests

已跑 Stage 28 定向套件：
- `backend/tests/unit/test_big_five_model.py`
- `backend/tests/unit/test_trait_dynamic_conflict_resolution.py`
- `backend/tests/unit/test_traits_nlp_observer.py`
- `backend/tests/unit/test_nlp_bias_calibration.py`
- `backend/tests/unit/test_nlp_single_call_no_direct_write.py`
- `backend/tests/unit/test_coldstart_service.py`
- `backend/tests/unit/test_coldstart_skip_path.py`
- `backend/tests/unit/test_aggregator_schema_v1_9.py`
- `backend/tests/unit/test_traits_router_zero_hit.py`
- `backend/tests/unit/test_traits_kill_switch.py`
- `backend/tests/unit/test_traits_auto_downgrade.py`
- `backend/tests/unit/test_trait_user_isolation.py`
- `backend/tests/unit/test_confidence_cap_enforcement.py`

本地结果：
- 定向全量：`53 passed in 7.15s`
- gate 子集：`43 passed in 6.29s`

### 13.2 Mobile Tests

已跑：
- `mobile/test/widget/coldstart_questionnaire_test.dart`
- `mobile/test/widget/traits_prior_display_test.dart`

本地结果：
- `7 passed`

### 13.3 Governance Guards

已跑：
- `scripts/stage28/check_rule_am_confidence_cap.py`
- `scripts/stage28/check_trait_not_router.py`
- `scripts/stage28/check_nlp_no_direct_write.py`
- `scripts/stage28/check_trait_user_isolation.py`
- `scripts/stage28/check_nlp_bias_calibration.py`
- `scripts/stage28/check_traits_no_diagnostic_labels.py`
- `scripts/stage28/gate_final.sh`

结果：
- 全绿

## 14. Stage 29 前置条件清单（SRL 初值接口）

Stage 29 可直接依赖的输入：
- `UserInsightState.traits_prior`
- `UserInsightState.traits_coldstart_completed_at`
- `BigFiveTraits.active_dimensions()`
- Aggregator `traits_prior` summary 输出

接口行为约束：
- Traits 仅作为弱先验
- 若 `traits_prior` 为空，Stage 29 必须走“无 prior”路径
- Dynamic States 冲突优先级始终高于 Traits
- Traits 不可反向写入 Bayesian / Reflection / Foresight

建议 Stage 29 接入顺序：
1. 先接 `traits_prior` 只读初值读取
2. 再接“无 prior”兜底路径
3. 最后接与 Dynamic States 的运行时冲突裁决

## 附：本地执行记录

已执行命令摘要：
- `backend/.venv/bin/pytest ...` → `53 passed`
- `cd mobile && flutter test test/widget/coldstart_questionnaire_test.dart test/widget/traits_prior_display_test.dart` → `7 passed`
- `bash scripts/stage28/gate_final.sh` → guards 全绿 + `43 passed`
- `cd backend && .venv/bin/alembic heads` → `s28a1b2c3d4 (head)`
- `make proto-gen` → 成功，host toolchain fallback 后完成同步

## 最终结论

Stage 28 采用 **Path A** 完成交付，Rule AM 的四条硬边界已经在模型层、合并层、Router 隔离层、guard/测试层形成闭环。

当前唯一显式保留项是：**Stage 17-27 全量历史回归未在本地完整复跑**。除该项外，Stage 28 自身的模型、冷启动、NLP 反偏差、聚合摘要、kill-switch、自动降级、用户隔离与文档登记均已达到 handoff 状态。
