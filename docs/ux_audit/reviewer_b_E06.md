# Reviewer B — E06: 学习预测→实际准确度反馈闭环
Timestamp: 2026-04-26T03:45:00+08:00
Chain Index: 24

## Chain Flow Summary

The chain covers TheaterService 学习预测的完整反馈闭环：生成预测→采纳为计划→到期自动回填实际值→校准偏差→影响下次预测。该闭环设计完整，覆盖自动回填（Celery daily）、手动回填（UI 校准 Tab）、校准偏差应用（`_apply_calibration_bias`）三条路径。Simulation 与 Theater 双向关联，仿真结果中暴露的知识盲区会通过 `SimulationGapRevealed` 事件流入 GalaxyEventConsumer。

## Critical Issues 🔴

无。

## Major Issues 🟡

**1. `_compute_actual_from_prediction` 仅在 adopted plan 存在时才能自动计算 completion_rate**

- File: `backend/app/services/theater/prediction_theater_service.py:1850-1856`
- Expected: 用户未采纳预测路径但通过其他方式完成了学习时，系统仍能自动回填 completion
- Actual: `resolved_completion` 仅在 `adopted_plan_id` 不为 None 时从 `plan.progress` 读取。如果用户没有采纳路径（仅做参考），completion_rate 永远为 0.0，导致 accuracy_score 被严重低估
- Evidence: `"resolved_completion: float | None = None; adopted_plan_id = ...; if adopted_plan_id is not None: ... plan.progress"` — 没有其他 completion 来源的 fallback
- Impact: 自动回填逻辑对「仅参考未采纳」的预测永远给出 completion=0.0，accuracy_score 不反映真实学习效果，污染校准基线

**2. Celery 任务 `check_prediction_accuracy` 每日仅运行一次且在凌晨 4:10，到期的预测最多等 24 小时才被自动回填**

- File: `backend/app/core/celery_app.py:1069-1072`
- Expected: 预测到期后尽快触发回填，或在用户打开 App 时即时检查
- Actual: Celery beat 配置为 `crontab(hour=4, minute=10)` 每天仅一次。如果用户在到期日白天活跃使用 App，不会触发任何自动回填
- Evidence: `"theater-prediction-accuracy-daily": { "schedule": crontab(hour=4, minute=10) }`
- Impact: 延迟不严重（最多 24h），但用户可能在"校准"Tab 看到 pending 状态较久

## Minor Issues 🟢

**1. `_topic_calibration_signal` 查询使用 `ilike` 无索引提示，高频使用时可能慢查询**

- File: `backend/app/services/theater/prediction_theater_service.py:1753-1755`
- Evidence: `TheaterPrediction.topic.ilike(f"%{topic}%")` — 全模糊匹配在数据量大时走全表扫描
- Impact: 短期可忽略，长期（100+ predictions/user）可能变慢

**2. Mobile 校准 Tab 中回填表单的 mastery 控件使用 slider 但无当前 Galaxy mastery 参考值显示**

- File: `mobile/lib/features/theater/presentation/screens/knowledge_theater_screen.dart:652-693`
- Evidence: 用户填写 actual_mastery 时无法看到当前 Galaxy 节点的真实 mastery 作为参考，只能凭记忆填写
- Impact: 用户填写偏差增大，降低校准数据质量

**3. `SimulationGapRevealed` 事件发布使用 bare except 忽略所有异常**

- File: `backend/app/services/simulation/simulation_engine.py:1720-1733`
- Evidence: `except Exception: continue` — 如果 event_bus 连接失败，所有 gap 事件静默丢失，无日志记录
- Impact: 缺乏可观测性，但不会导致用户可见错误

## Working Well ✅

- **完整的闭环设计**: 预测生成→`_build_prediction_calibration` 读取历史校准→`_apply_calibration_bias` 修正新预测→`record_actual_outcome` 回填→`auto_check_predictions` 自动化→循环。三层闭环（Celery auto + UI manual + calibration bias application）设计合理。

- **DB + Redis 双层持久化**: `TheaterPrediction` model 将 `accuracy_status`、`accuracy_due_on`、`accuracy_summary` 提升为独立列（非仅 JSONB），Celery 可以直接查询而无需依赖 Redis 热缓存。Redis miss 时有 DB fallback (`_get_pending_predictions:1672-1691`)。

- **移动端 repository 完整**: `theater_repository.dart` 实现了 `recordActuals`、`getAccuracy`、`getAccuracyOverview` 全部 API 调用（198-277行），Provider 有 `recordActualOutcome` 方法（311-340行），UI 有校准 Tab 和回填表单（652-693行）。

- **预测区间反馈**: `_build_accuracy_tracking` 会生成 `within_range` 布尔判断，比较实际值是否落在预测区间内（272-277行），不仅依赖绝对误差。

- **Simulation ↔ Theater 双向连接**: Simulation 屏幕有「以此推演」按钮可跳转 Theater（simulation_screen.dart:3008-3010），Theater 屏幕有「验证路径」按钮跳转 Simulation（knowledge_theater_screen.dart:64-82），sourcePredictionId 通过 URL 参数透传。

- **经验校准**: Stage 4 修复后的 `_build_prediction_calibration` 使用 `completion_bias_mean`、`mastery_bias_mean`、`coverage_rate` 等统计量，sample_count >= 5 时标记 `data_status: "calibrated"`（2762行）。

## Files Examined

- `backend/app/services/theater/prediction_theater_service.py` (3614 lines — core service)
- `backend/app/services/simulation/simulation_engine.py` (1786 lines — simulation engine)
- `backend/app/models/theater_prediction.py` (97 lines — DB model)
- `backend/app/api/v1/theater.py` (202 lines — REST API)
- `backend/app/core/celery_tasks.py` (lines 631-681 — auto-check task)
- `backend/app/core/celery_app.py` (lines 1069-1073 — beat schedule)
- `mobile/lib/features/theater/data/repositories/theater_repository.dart` (302 lines — API client)
- `mobile/lib/features/theater/presentation/providers/theater_provider.dart` (576 lines — state)
- `mobile/lib/features/theater/presentation/screens/knowledge_theater_screen.dart` (4700+ lines — UI)
- `mobile/lib/features/theater/data/models/theater_models.dart` (accuracy models at 430-800+)
- `mobile/lib/features/theater/theater_routes.dart` (34 lines — routing)
- `mobile/lib/features/simulation/presentation/screens/simulation_screen.dart` (theater bridge)

## Confidence: High — 核心闭环代码全部亲自阅读确认，关键行号已引用。唯一未覆盖的是 `PredictionAccuracyTracker` 的 Redis TTL 和清理逻辑（非核心链路）。
