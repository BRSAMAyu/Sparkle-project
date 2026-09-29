# FIX-579 R1 独立审查 receipt（2026-09-29）

- 审查人：独立审查员 R1（未参与实现）
- 被审：代码 `ad1dd9c4`（2 文件 +106/−4）｜分支头 `76d0d81a`｜base `89e6efad`
- worktree：`/Users/brsama/code/GitHub/wtF579`（BRSAMAyu/Sparkle-project）
- 资源红线遵守：全部 `flutter test --concurrency=1`；探针（mutation）已 `git checkout --` 还原，审查结束工作树干净、被审头不变。

## VERDICT: PASS_WITH_CHALLENGES

八靶全过；三例定性、修法、机制测试、mutation、台账闭账均独立复现成立。两处挑战（C1 容差余量、C3 候选清单缺登）不推翻修法，转后续观察/台账。

## 逐靶结论

1. **本地口径零变化（红线）— PASS**：diff 逐行核：仅两处已证 flaky 断言改经 `_ciTolerantMs/Us()`；本地（无 `GITHUB_ACTIONS`、无注入）`×1.0` 后 `.round()` 对 200/70000 精确等值。常量字节级核对 base（`S01_SCROLL_FRAME_US`=70000、`S01_FRAME_US`=33334、`GALAXY_LAYOUT_500/1000/100_MS`=1500/8000/200 均未动）。亲跑打印实证：S01 三轮 `70000 us`、galaxy 三轮 `200 ms`（S01 打印格式与 base 逐字一致；galaxy 打印为增量扩展、阈值值等值）。
2. **选型合理性 — PASS**：`Platform.environment` 于 Dart VM 可读（semantic 文件 base 即有 `import 'dart:io'`）；生产断言路径（semantic:469、galaxy:64）不带 `ciEnvironment` 参数→缺省走真实检测，注入仅存在于新增机制测试内不泄漏。进程级 e2e 亲复跑：`GITHUB_ACTIONS=true` 下 galaxy 13 passed 打印 `threshold 300 ms`、S01 24 passed 打印 `threshold 105000 us`（CI 模式下输出为 🎉 格式，与本地 `All tests passed` 系 reporter 差异）。
3. **容差 1.5x 推导 — PASS 附 C1/C2/C4**：算术复核全对：300/244=1.23x、105000/81496=1.29x；比值矩阵 2.37/2.84/2.74/3.30（全矩阵 2.37–3.30x）。1.5 低于矩阵下界 2.37，噪声吸收向成立；判别力代价已在 limitations #2 显式登记。挑战见 C1（余量偏薄）、C2（galaxy 注释借数）、C4（中带口径）。
4. **mutation 亲复现 — PASS**：恒等变异两 helper → galaxy CI+ 红 `Expected: <300> Actual: <200>`、semantic G2+ 红 `Expected: <105000> Actual: <70000>`（逐字与 verification.md §3 一致）；两反例（CI-/G2-）变异下仍绿（与 §3 声称一致，其断言对象不依赖 CI 分支）；还原后 CI+ 复绿、树清洁。首次 sed 无效 mutation 系已弃用的工作树尝试，无法考古复验，但如实弃用记录 + 有效 mutation 全复现，诚实性认可（C5 INFO）。
5. **3 连跑亲验 — PASS**：galaxy 3 轮 66/62/58ms、打印 200 ms、13 passed×3；S01 3 轮 37418/23821/24109μs、打印 70000 us、24 passed×3。全绿。
6. **越界排查 — PASS 附 C3**：H 组 `_frameThresholdUs`（33334）零触碰（:561-562 仍直引）；galaxy 其余 8 个 perf 断言零触碰（:91/:115/:141/:168/:201/:237/:267/:296）。候选清单抽样 4+ 文件：A 类 galaxy_semantics_perf:97 `lessThan(50000)` 无 env 开关 ✓、enhanced_intent_classifier:323,331 `lessThan(2)/(200)` ✓；B/C 类 widget_bench 六 env 键（:16-38）+ 内存预算（:294/:320）✓；非候选 chat_notifier:52 Stopwatch 仅作等待超时 ✓；`fromEnvironment` 交叉核对证实 g05/offline_crdt/enhanced_intent/chat_screen_basic/flutter_core_bench 无 env 开关（A 类归类正确）、galaxy_integration 恰一个 env 键（A+B 双列正确）。缺登见 C3。
7. **断言语义 — PASS**：两处仍 `lessThan`（非 lte 偷换）；全 diff 无 `skip:`、无 golden 改动；机制测试纯增量（2+2）。
8. **台账行 — PASS**：`v3/06_agent_fleet/DYNAMIC_ISSUES.md:460` V3-FIX-579 OPEN→FIXED@ad1dd9c4，闭账注记与实际修法/证据一致（diff 核于 76d0d81a）。

附核：ci.yml（:582/:587）无任何 `-D` 传入，limitations #4 叠加语义条款前提成立。

## 编号发现

- **C1（MEDIUM，挑战）**：容差余量偏薄，残留 CI flake 概率非可忽略。`mobile/test/core/design/semantic_motion_s01_test.dart:56`（kCiPerfTolerance=1.5）。放宽界仅高于实测 CI 噪声峰值 1.23x/1.29x；R1 独立复跑 S01 第 1 轮测得 **37418μs**，劣于证据全带（19119–30492μs），本地余量仅 1.87x（低于登记的 2.4–2.8x 带）。按高端 CI/本地比（3.30x）投影，该档本地值对应 CI ≈123ms > 105000μs 界 → CI 仍可能红。复现：`cd mobile && flutter test --concurrency=1 test/core/design/semantic_motion_s01_test.dart`（多轮取方差）。结论：修法方向与数据成立，但 1.5x 应视为**暂定值**——limitations #5 已登记「真实托管 runner 下一轮自然运行」为终证，若 CI 再红应上调系数或改测量法（warm-up/多采样，归基建卡），而非再调阈值。
- **C2（LOW）**：galaxy 文件注释 `真回归（本地余量 2.4x+…）`（galaxy_performance_test.dart:34 附近）系借用 S01 数字；galaxy 实测本地余量 1.8–3.4x（110ms 最差轮 → 200/110=1.82x）。不影响结论（本地严格界仍在），建议后续措辞按测试各自口径修正。
- **C3（LOW）**：候选清单缺登一处 A 类阈值。`mobile/test/performance/widget_bench_test.dart:110`：`GalaxyScreen build` `expect(elapsedMilliseconds, lessThan(100))` 为裸绝对时间阈值（无 env 开关），同文件仅被归 B/C 类。清单自称 grep 逐一提取，此处漏网；且属 galaxy 家族（与两例 flaky 同特性族），建议台账转登记供 owner 观察。不涉本卡修面。
- **C4（INFO）**：「保守中带 2.5–2.9x」口径偏宽：比值矩阵 4 格中 2 格（2.37、3.30）落在带外。定标结论不受影响（1.5 < 全矩阵下界 2.37），引用时宜直接用全矩阵 2.37–3.30x。
- **C5（INFO）**：首次 sed 无效 mutation 为已弃用工作树尝试，无法考古复验；有效 mutation 全量复现 + 如实弃用记录，诚实性认可。

## 命令与 exit code 清单（R1 亲跑，2026-09-29，wtF579/mobile）

| # | 命令 | 结果 | exit |
|---|---|---|---|
| 1 | `git status` / `rev-parse HEAD ad1dd9c4 89e6efad` | clean；76d0d81a/ad1dd9c4/89e6efad 均符 | 0 |
| 2 | `flutter analyze test/core/design/semantic_motion_s01_test.dart test/features/galaxy/performance/galaxy_performance_test.dart` | No issues found! | 0 |
| 3 | `flutter test --concurrency=1 …galaxy_performance_test.dart` ×3 | 66/62/58ms (threshold 200 ms)；+13 passed ×3 | 0 |
| 4 | `flutter test --concurrency=1 …semantic_motion_s01_test.dart` ×3 | 37418/23821/24109μs (threshold 70000 us)；+24 passed ×3 | 0 |
| 5 | `GITHUB_ACTIONS=true flutter test --concurrency=1 …galaxy…` | 57ms (threshold 300 ms)；🎉 13 tests passed | 0 |
| 6 | `GITHUB_ACTIONS=true flutter test --concurrency=1 …s01…` | 19305μs (threshold 105000 us)；🎉 24 tests passed | 0 |
| 7 | python3 精确串替换注入恒等 mutation（两 helper） | MUTATED ×2 | 0 |
| 8 | mutation：`flutter test --concurrency=1 …galaxy… --plain-name "CI+"` | 红：Expected \<300\> / Actual \<200\> | 1 |
| 9 | mutation：`…s01… --plain-name "G2+"` | 红：Expected \<105000\> / Actual \<70000\> | 1 |
| 10 | mutation：`--plain-name "CI-"` / `--plain-name "G2-"` | 均绿（+1 passed） | 0 |
| 11 | `git checkout -- <两文件>` + `git status --porcelain` | RESTORED_CLEAN | 0 |
| 12 | 还原后 `--plain-name "CI+"` 复跑 | 绿（+1 passed） | 0 |
| 13 | `grep ci.yml -D` 核对 | 无 -D | 0 |
| 14 | 终态 `git status --porcelain` + `rev-parse HEAD` | clean；76d0d81a 不变 | 0 |

## 裁决依据小结

红线（本地口径零变化）成立且有打印实证；机制一正一反经 mutation 亲证非恒真；三例定性与比值推导数据复核无误；越界零触碰核实；台账闭账属实。C1 为已登记取舍下的实质性挑战（余量偏薄、终证待真实 runner），C2/C3 为LOW 修正项，均转台账/后续轮次，不改 PASS_WITH_CHALLENGES 之外的可能。
