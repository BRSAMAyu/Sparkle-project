# GALAXY-TEST-ISO — galaxy widget 测试隔离债收口报告

- worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt59`，base = `c4ca4b13`（FIX-55/V25）
- 日期：2026-09-21
- 类型：LIGHT（flutter test 诊断+修复，零模拟器零浏览器）

## 一句话结论

**不存在真实的跨文件状态污染**。目录套件唯一红 = `galaxy_screen_test.dart` retry 用例的**独立测试基建缺陷**（裸 `MaterialApp` 缺 DS 主题，`SparkleThemeExtension` 未注册）；债项登记的「first_load 单跑绿随目录红」在本 base 上经 5 轮目录级复跑（并发×3、`--concurrency=1` 顺序×1、integration+performance+unit+widget 全量×1）**均不可复现**，判定为并发跑进度输出交错导致的**误归因**（详见下文证据）。

## 污染链定位过程

1. **复现基线**：单跑 `galaxy_first_load_empty_state_test.dart` → 2/2 绿（与债项一致）。
2. **目录跑**：`flutter test test/features/galaxy/widget/` → `+20 -1`。**红的是 retry 用例（`galaxy_screen_test.dart`），不是 first_load**。连续 3 轮并发跑结果完全一致。
3. **顺序跑排除并发干扰**：`--concurrency=1` 整目录 → 仍 `+20 -1`，唯一红仍是 retry。若存在测试间状态泄漏（同 isolate 内顺序执行最容易复现的形态），顺序跑应当红得更稳定；实际 first_load 顺序跑依旧绿。
4. **全量跑**：`flutter test test/features/galaxy/`（integration+performance+unit+widget 共 105 测试）→ `+104 -1`，唯一红仍是 retry。
5. **retry 单跑**：单文件跑 retry 用例**同样红** → 根本不存在「单跑绿随目录红」的隔离问题，retry 是无条件红。
6. **物理机制排除**：flutter test 每个测试文件运行在**独立 isolate**，Dart 静态/单例（`SharedPreferences.setMockInitialValues`、`I18nService.instance`、`ViewStorageService` 等）天然无法跨文件泄漏；本套件也无共享进程级可变状态。

### 「first_load 随目录红」误归因的来源（高置信推断）

并发跑时 flutter test 的进度行按文件交错输出，**携带 `-1` 计数的那一行往往显示的是别的文件名**。实测第 1/3 轮目录跑中均出现：

```
00:03 +15 -1: .../galaxy_first_load_empty_state_test.dart: V24: first graph load ...
00:03 +15 -1: .../galaxy_screen_test.dart: Galaxy Widget Tests GalaxyScreen shows retry state and reloads after retry [E]
```

`-1` 落在 first_load 的行上、`[E]` 才是真正红的 retry 行。扫一眼输出的 Worker 极易读成「first_load 随目录红了」。retry 红的可见症状（`Multiple exceptions (4)` + 大段 `SparkleThemeExtension is not registered on ThemeData` 栈）又发生在真实 `GalaxyScreen` 构建中，进一步加深「环境/污染」错觉。

## 根因（retry 用例，独立存量红）

`galaxy_screen_test.dart` 的 `GalaxyScreen shows retry state and reloads after retry` 用真实 `GalaxyScreen` 挂在**无 `theme` 的裸 `MaterialApp`** 上。`GalaxyScreen` 内 `SparkleRefreshIndicator`（galaxy_screen.dart:2837）build 时经 `context.sparkle.colors` 取色，触发：

```
SparkleThemeExtension is not registered on ThemeData.
'sparkle_context_extension.dart': Failed assertion: line 11 pos 7: 'extension != null'
```

断言在首帧 + 后续每次 pump 反复抛（共 4 次异常），错误面板替换内容 → `find.textContaining('galaxy 500')` 找到 0 个 → 用例红。同文件其余用例只用自建探针 widget 不触 DS 主题，故只有这一条红。FIX-52（V24）与 V25 两批测试都带 `theme: AppThemes.lightTheme` 并留有注释「需挂 DS 主题，否则 SparkleThemeExtension 未注册」，本用例是更早批次漏挂的存量。

## 修法（最小侵入，2 处）

文件：`mobile/test/features/galaxy/widget/galaxy_screen_test.dart`

1. 增 `import 'package:sparkle/core/design/design_system.dart';`
2. retry 用例的 `MaterialApp` 补 `theme: AppThemes.lightTheme`（附注释说明原因）。

无 `skip`、无删测、未动任何产品代码与共享 fixture。

## 全绿证据

| 跑法 | 结果 |
| --- | --- |
| `flutter test test/features/galaxy/widget/galaxy_screen_test.dart`（修复后单文件） | **9/9 All tests passed** |
| `flutter test test/features/galaxy/widget/galaxy_first_load_empty_state_test.dart`（单文件回归） | **2/2 All tests passed** |
| `flutter test test/features/galaxy/widget/`（整目录一次跑，修复后） | **21/21 All tests passed** |
| `flutter test test/features/galaxy/`（integration+performance+unit+widget 全量） | **105/105 All tests passed** |

galaxy unit 目录随全量跑通过，未见同款问题（unit 用例不挂真实 GalaxyScreen，无 DS 主题依赖面）。

## 诚实申报

1. **「测试间污染」未找到实证且不可复现**：本报告结论是「债项登记的 first_load 目录红 = 输出交错误归因 + retry 独立红的合并症状」，而非修复了一个真实泄漏。若后续在其他 base/机器上稳定复现 first_load 随目录红，需按本报告第「污染链定位过程」第 3 步先跑 `--concurrency=1` 再下结论。
2. 本机 5 轮目录级跑均在 swap 空闲 ≥1.2G、load <8 窗口内完成；未复现 ≠ 永不存在，但顺序跑（状态泄漏最易复现的形态）也已覆盖。
3. `mobile/lib/gen/` 按纪律从主仓只读复制（生成物，不入 patch）。
4. retry 用例修复后新走到此前从未到达的断言路径（错误面板真实渲染），本轮 105/105 稳定；若产品侧后续改 `GalaxyError` 文案格式，`textContaining('galaxy 500')` 需同步。
