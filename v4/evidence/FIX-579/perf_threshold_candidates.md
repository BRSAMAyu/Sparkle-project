# FIX-579 同模式排查 — mobile/test 绝对 perf 阈值候选清单（只登记，不修）

排查法：`grep -rl "Stopwatch|elapsedMicroseconds|elapsedMilliseconds|avg_frame|frameTime|p95|FrameTiming" mobile/test`，
再对命中文件逐一提取绝对阈值断言（`lessThan/lessThanOrEqualTo` + 时间/内存语义）。
CI 面为 `.github/workflows/ci.yml` 的 `flutter test --coverage`（默认全量 test/）。

**修面限定：仅两例已证 flaky 者（galaxy 100 节点布局、S01 G+ 滚帧）已修；下列候选
未经 CI 红绿实证，本卡不越权修改，留待各 owner 在出现 flake 实证后套用同模式。**

## A 类：无环境开关的绝对阈值（同模式最直接候选）

| 文件:行 | 断言 | 阈值 | 备注 |
|---|---|---|---|
| `test/features/galaxy/performance/galaxy_semantics_perf_test.dart:97` | 300 节点拖拽 avgFrameMicros | `< 50000μs` | 与 S01 G+ 同族（滚帧均值），最优先观察 |
| `test/features/galaxy/integration/galaxy_integration_test.dart:58` | 布局耗时 | `< 10ms` | 单位极小，噪声敏感 |
| `test/features/galaxy/performance/g05_galaxy_frame_budget_test.dart:154,156` | 拖拽 avg / p95 | `< 50ms` / `< 100ms` | reason 自述「只防病理性回退」，口径已偏松 |
| `test/core/offline/offline_crdt_document_test.dart:153` | 1000 ops merge | `< 200ms` | |
| `test/unit/enhanced_intent_classifier_test.dart:323,331` | avg 分类耗时 / 批量 | `< 2ms` / `< 200ms` | `< 2ms` 单位极小 |
| `test/widget/chat_screen_basic_test.dart:567,591` | 首帧/交互 | `< 2000ms` / `< 500ms` | 阈值宽，风险低 |
| `test/performance/flutter_core_bench_test.dart:31,52,77,100,137,167,201,225,257,315-317` | 框架基准族 | `< 5/10/100/200/500/5000ms`、`< 50000μs`、结果表 | 密集绝对阈值面 |

## B 类：已有 `int.fromEnvironment` -D 逃生门、但无 CI 自动容差

| 文件:行 | env 键 | 默认阈值 |
|---|---|---|
| `test/performance/widget_bench_test.dart:65,89,149,192,227,266` | `PLAN_REVIEW_BUILD_MS`/`TASK_BOARD_BUILD_MS`/`CHAT_LIST_BUILD_MS`/`PLAN_REVIEW_REBUILD_MS`/`PLAN_REVIEW_FRAME_US`/`SCROLL_FRAME_US` | 各自默认值 |
| `test/features/galaxy/integration/galaxy_integration_test.dart:237` | `GALAXY_PIPELINE_500_MS` | 500 节点管线 |
| `test/features/galaxy/performance/galaxy_performance_test.dart`（未修的其余阈值） | `GALAXY_LAYOUT_500_MS`/`GALAXY_LAYOUT_1000_MS` | 1500ms / 8000ms |

注：B 类若 CI 出现 flake，可二选一：CI 侧 `-D`（现有口径）或本卡同模式 `kCiPerfTolerance`。

## C 类：内存预算（非时间量纲，暂不适用慢机比值）

- `test/performance/widget_bench_test.dart:294`（`< 500KB`）、`:320`（`< 5MB`）

## 明确不属于候选

- `test/unit/chat_notifier_first_event_guard_test.dart:52`、`test/widget/chat_screen_basic_test.dart`
  其余 Stopwatch 用途：仅打印/统计，无阈值断言
- `semantic_motion_s01_test.dart` H 组 `_frameThresholdUs`（33334μs）：同文件但未证 flaky，
  本卡零触碰（同文件其余 22 测 CI50/CI52 rerun 全绿）
