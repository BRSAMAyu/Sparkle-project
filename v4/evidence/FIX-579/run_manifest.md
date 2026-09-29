# FIX-579 run_manifest — CI perf 阈值系统性 flake 的环境容差校准

- 卡：V3-FIX-579（P2，台账 460 行，三例定性 2026-09-30）
- 分支：`fix/v4/f579-ci-perf-threshold-tolerance`（自 main `89e6efad` 开出）
- worktree：`/Users/brsama/code/GitHub/wtF579`
- 代码修复 commit：`ad1dd9c4`（2 文件 +106/-4）
- 执行：FIX-579 agent，2026-09-29

## 缺陷定性（三例原始数据）

CI 共享 runner 比本地慢且方差大，两个绝对阈值测试的红绿落在噪声带：

| # | CI 轮次 | 测试 | 断言 | CI 实测 | 阈值 | 超出 | 结果 |
|---|---|---|---|---|---|---|---|
| ① | CI49 | `galaxy_performance_test.dart` 100 节点初始布局 | `lessThan(200ms)` | 244ms | 200ms | +22% | 红 → rerun 绿 |
| ② | CI50 | `semantic_motion_s01_test.dart` G+ 语义族滚帧均值 | `lessThan(70000μs)` | 70241μs | 70000μs | +0.3% | 红 → rerun 绿 |
| ③ | CI52 | 同② | 同② | 81496μs | 70000μs | +16.4% | 红 |

本地 M 系（fleet note #442 三连跑）：S01 滚帧 24.7 / 24.7–29.7ms 全绿（余量 2.4–2.8x）。
本卡执行时本地复测（证据 verification.md §1）：S01 26741/19119/30492μs；galaxy 110/61/61ms。

## CI/本地比值推导

| CI 实测 | ÷ 本地最好 24.7ms | ÷ 本地最差 29.7ms |
|---|---|---|
| 70241μs（CI50） | 2.84x | 2.37x |
| 81496μs（CI52） | 3.30x | 2.74x |
| 244ms（CI49，galaxy，本地本次 61–110ms） | 2.2–4.0x | 同左 |

→ 实测 CI/本地比约 2.4–3.3x（fleet note 取保守中带 2.5–2.9x）：绝对阈值落在共享 runner
噪声带内，红绿跟随 runner 负载漂移；本地余量巨大（≥2.4x）→ **非产品回归，系环境 flake**。

## 修法（显式治理变更，非静默放宽）

`const double kCiPerfTolerance = 1.5`，环境感知只对 CI 生效：

```dart
threshold * ((ciEnvironment ?? _runningOnCi) ? kCiPerfTolerance : 1.0)  // .round()
// _runningOnCi => Platform.environment.containsKey('GITHUB_ACTIONS')
```

- **本地严格口径 ×1.0 逐字节不变**：`200×1.0=200`、`70000×1.0=70000`（3 连跑打印实测证明）。
- 1.5x 的双向边距：CI 放宽界 300ms / 105000μs，吸收实测 runner 噪声峰值（244ms /
  81496μs，裕度 1.23x / 1.29x），真回归（≥~1.3–1.5x 量级）在 CI 上仍远超放宽界被拦截。
- 常量处注释签三例数据 + 比值依据 + 日期；测试内一正一反（参数注入模拟 CI 正例 /
  严格界原值反例）。

## 改动面（2 文件，仅两处已证 flaky 断言 + 各一正一反机制测试）

- `mobile/test/features/galaxy/performance/galaxy_performance_test.dart`：
  100 节点布局断言阈值经 `_ciTolerantMs()`；新增「CI 容差校准」组 2 测；
  `import 'dart:io'`；其余 8 个 perf 断言零触碰
- `mobile/test/core/design/semantic_motion_s01_test.dart`：
  G+ 滚帧断言阈值经 `_ciTolerantUs()`；新增「G2 CI 容差校准」组 2 测；
  H 组 `_frameThresholdUs` 零触碰
- 同模式其余绝对 perf 阈值：只登记不修（perf_threshold_candidates.md）

## 选型记录：env 检测 vs 注入

**混合式，以可行性为准**：`Platform.environment` 在 flutter test（Dart VM）内可读，
env 检测可行 → 生产断言走缺省真实检测；但 `Platform.environment` 只读、无法在测试进程内
覆写 → 正例经 `ciEnvironment: true` 显式参数注入模拟 CI。默认路径的真实检测另由
`GITHUB_ACTIONS=true` 进程级 e2e 实证（verification.md §4）。

## 红线

本地阈值一字不动（×1.0 等值，打印阈值实测 200/70000 原值）；不删断言不弱化语义
（仍 `lessThan`，仅 CI 侧放宽且签理由）；不趁便改其他测试（同模式只登记）；不 push；
`flutter test` 一律 `--concurrency=1`。
