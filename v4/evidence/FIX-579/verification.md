# FIX-579 verification — 全部命令 2026-09-29 实测于 wtF579

环境：macOS arm64（M 系），Flutter 3.41.3 stable；`flutter test` 一律 `--concurrency=1`。

## §1 本地 3 连跑（严格界生效实证，全部绿）

`flutter test --concurrency=1 <file>` 连续三轮，打印中的 threshold 即断言实际取值：

**semantic_motion_s01_test.dart（24 测/轮，原 22 + 新增 G2 2 测）**

| 轮 | G+ 滚帧均值 | 打印阈值 | 结果 |
|---|---|---|---|
| 1 | 26741μs | **70000 us**（严格原值） | All tests passed |
| 2 | 19119μs | **70000 us** | All tests passed |
| 3 | 30492μs | **70000 us** | All tests passed |

**galaxy_performance_test.dart（13 测/轮，原 11 + 新增 2 测）**

| 轮 | 100 节点布局 | 打印阈值 | 结果 |
|---|---|---|---|
| 1 | 110ms | **200 ms**（严格原值） | All tests passed |
| 2 | 61ms | **200 ms** | All tests passed |
| 3 | 61ms | **200 ms** | All tests passed |

本地严格口径逐值不变：×1.0 后 `.round()` == 原常量，打印实测 200/70000 与改动前字面一致。
S01 本轮三跑 19.1–30.5ms 与台账 24.7–29.7ms 同带，余量 ≥2.3x。

## §2 flutter analyze 零

```
flutter analyze test/core/design/semantic_motion_s01_test.dart \
  test/features/galaxy/performance/galaxy_performance_test.dart
→ No issues found! (ran in 16.5s)
```

## §3 mutation：去 CI 分支 → 模拟 CI 正例红

变异（工作树临时改动，`git checkout --` 还原，分支零残留）：
两 helper 函数体改为恒严格——`_ciTolerantUs(...) => baseUs; // MUTATION-F579: CI 分支去除`。

首次尝试以 sed 行替换注入注释吞掉箭头函数 `;` → 编译失败（无效 mutation，弃用，
还原后以 perl 多行替换重做——记录如实）。

有效 mutation 下跑两正例：

```
galaxy CI+：Expected: <300>  Actual: <200>   → 红 ✓（0 -1）
semantic G2+：Expected: <105000>  Actual: <70000> → 红 ✓（0 -1）
```

正例非恒真实证：容差确实经 CI 分支生效，去除即红。反例（CI-）在 mutation 下仍绿
（其断言对象=严格界，本就不依赖 CI 分支）——机制一正一反分工明确。

## §4 GITHUB_ACTIONS=true 进程级 e2e（真实 env 检测缺省路径）

```
GITHUB_ACTIONS=true flutter test --concurrency=1 test/features/galaxy/performance/galaxy_performance_test.dart
→ 100 nodes initial layout: 56ms (threshold 300 ms)   🎉 13 tests passed
GITHUB_ACTIONS=true flutter test --concurrency=1 test/core/design/semantic_motion_s01_test.dart
→ S01 scroll avg frame time: 23233us (threshold 105000 us)   🎉 24 tests passed
```

托管 runner 的检测面（`GITHUB_ACTIONS` ∈ `Platform.environment`）端到端实证：
不注入参数、仅环境变量，阈值即放宽 1.5x 且全部通过。

## §5 容差前后对照表

| 测试 | 阈值常量 | 改前断言 | 改后断言（本地） | 改后断言（CI） | 噪声峰值裕度 | 真回归拦截 |
|---|---|---|---|---|---|---|
| galaxy 100 节点布局 | `GALAXY_LAYOUT_100_MS`=200ms | `< 200ms` | `< 200ms`（等值） | `< 300ms` | 300/244=**1.23x** | 2x 回归→CI≈488ms>300 红 |
| S01 G+ 滚帧均值 | `S01_SCROLL_FRAME_US`=70000μs | `< 70000μs` | `< 70000μs`（等值） | `< 105000μs` | 105000/81496=**1.29x** | 1.5x 回归→CI≈105–125k>105k 红（临界）；2x→≥140k 红 |

## §6 三例原始数据与比值推导

原始数据（fleet 登记 + /tmp/ci52_failed.log，fleet note #442）：

- CI49：galaxy 100 节点布局 **244ms** vs 200ms（+22%），首轮红 → rerun 绿
- CI50：S01 滚帧 **70241μs** vs 70000μs（+0.3%），首轮红 → rerun 绿
- CI52：同测试 **81496μs**（+16.4%），红（/tmp/ci52_failed.log）
- 本地 M 系 3 连跑（登记时）：S01 **24.7 / 24.7–29.7ms** 全绿（余量 2.4–2.8x）

比值矩阵（CI 实测 ÷ 本地）：

| | ÷24.7ms（本地最好） | ÷29.7ms（本地最差） |
|---|---|---|
| 70241μs | 2.84x | 2.37x |
| 81496μs | 3.30x | 2.74x |

→ 全矩阵 2.37–3.30x；fleet note 取保守中带 **2.5–2.9x** 为容差定标依据。
galaxy CI49 244ms ÷ 本卡本地实测 61–110ms = 2.2–4.0x，同量级。

定标逻辑：1.5x 容差使 CI 界（105ms/300ms）落在「实测噪声峰值（81.5/244）之上
1.23–1.29x」与「温和真回归（CI 侧 ≥1.3–1.5x 即超界）之下」，双向均有边距；
本地严格界继续全量把关。
