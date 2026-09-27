# WT698 · V3-FIX-384 收口笔记

- 分支：`agent/node-b/wt698/fix384`（基线 61239f06 = main @ worktree 创建时点；未 push）
- 代码 commit：`f590fc2a`（closes V3-FIX-384）
- 台账 commit：见分支末位 commit（本目录 + DYNAMIC_ISSUES.md）

## 1. 定位证据

- 目标面：`mobile/lib/features/aurora/presentation/widgets/aurora_calibration_strip.dart:178`（基线行号）
  的展开/收起 `AnimatedSize`，修前消费
  `DS.motionDuration(SparkleMotionToken.standard, reduceMotion: context.reduceMotion)`
  ——`reduceMotion` 下即 `Duration.zero`（`design_system.dart:1087` motionDuration
  reduceMotion 分支实证）。
- 宿主：`mobile/lib/features/home/presentation/screens/dashboard_screen.dart:1298`
  `const AuroraCalibrationStrip()`（dashboard 低层渲染面，`!hasNoGoals` 分支 sliver 列表尾）。
- reduceMotion 真源：`sparkle_context_extension.dart:39-44`
  `MediaQuery.disableAnimations || accessibleNavigation`；U-02 低刺激档经
  `emotion_responsive_theme.dart:189 disableAnimations: true` 驱动同一路径。
- 登记：wt694 审查 V3-FIX-374 时普查新发现（`v3-output/WT694-REVIEW2/review.md`
  裁决一 19 处 AnimatedSize 三分表「消费 reduceMotion·未修未登记」唯一漏修面）。
  注意：384 行此前仅存在于 review.md，`v3/06_agent_fleet/DYNAMIC_ISSUES.md` 在本
  分支基线上尚无该行（main 36fddd4e 亦无，git grep 复核），本卡按 7 列格式补登
  FIXED 行。

## 2. 修复（374 同款「禁动效不装壳」，语义等价替换）

`aurora_calibration_strip.dart`（仅此一处产品码改动）：

- 展开体提取为局部 `calibrationBody`（`_expanded ? Padding(...) : SizedBox.shrink()`，
  内容逐字未动）；
- `context.reduceMotion` 为真 → 直接挂载 `calibrationBody`（零时长 AnimatedSize 的
  行为等价物，不装动画外壳）；否则照旧装 `AnimatedSize`（duration 改传
  `DS.motionDuration(SparkleMotionToken.standard)` 不带 reduceMotion 形参——该分支
  reduceMotion 恒 false，行为与修前 standard 档逐位一致）；
- 不新增壳组件、不改产品语义；头部 `AnimatedRotation`（:164）按 374 口径保留
  （零时长仅影响绘制不参与布局）。

## 3. 回归锁扩展（374/375 渲染树断言锁推广到 dashboard 面）

`mobile/test/widget/chat_bubble_reduced_motion_test.dart` 新增两组（原 374 两组不动）：

- **低刺激档红锁**：真实 dashboard provider 管道（存量
  `test/features/home/dashboard_test_harness.dart` 的 `buildDashboardWidgetHarness`
  + `extraOverrides` 钉 `auroraCalibrationSurfaceProvider` 确定性 fixture）+ 真实
  `AuroraCalibrationStrip`；pump 后 tap 头部 InkWell 展开，断言
  ① 条面真实渲染守卫（防锁空转）② 展开内容可见 ③ 全程零 `RenderAnimatedSize`
  框架断言 ④ 渲染树枚举零 `Duration.zero` RenderAnimatedSize（374 锁同款判据）。
- **standard 档对照组**：同宿主 `EmotionResponsiveConfig.normal()`，展开后
  `AnimatedSize` 外壳仍在（findsWidgets）+ 内容可见——钉死不因修复砍掉 standard 档动画。

## 4. 红绿实证（真实运行输出）

修后（`flutter test test/widget/chat_bubble_reduced_motion_test.dart`）：

```
00:00 +1: standard 档 ChatBubble 保留 AnimatedSize 动画外壳
00:00 +2: V3-FIX-384: dashboard 低刺激档 AuroraCalibrationStrip 展开零 RenderAnimatedSize 断言、渲染树无零时长 AnimatedSize
00:01 +3: V3-FIX-384 对照: standard 档 AuroraCalibrationStrip 保留 AnimatedSize 动画外壳
00:01 +4: All tests passed!
```

修前红验证（`git stash push -- <strip 文件>` 临时还原修前版本后同命令）：

```
00:01 +2 -1: V3-FIX-384: dashboard 低刺激档 AuroraCalibrationStrip 展开零 RenderAnimatedSize 断言、渲染树无零时长 AnimatedSize [E]
  Expected: empty
  Actual: [
00:01 +3 -1: Some tests failed.
```

即修前不仅结构性判据红（渲染树存在零时长 AnimatedSize），且捕获到**真实
RenderAnimatedSize 框架断言**（animatedSizeErrors 非空）——wt694「同机制未收口，
未做全栈复现」的定性由本红测补齐为全栈复现实锤；崩溃路径 = 低刺激档展开校准条。

## 5. 门禁

- `flutter analyze`（worktree 全量）：`No issues found! (ran in 15.3s)`
- 台账 `python3 scripts/devtools/ledger_union_merge.py --verify v3/06_agent_fleet/DYNAMIC_ISSUES.md`：
  `verify 通过：289 行，裸管分布 {8: 289}，零冲突标记，ID 无重号，状态枚举合法`
- gen 目录按 wt482/374 先例主仓 `cp -RL` 不入库；golden/证据 PNG 未碰；未 push。

## 6. 余量（不占本卡）

- 全 lib 其余 `reduceMotion` 消费点未逐一复审（wt694 三分表口径：修后面 =
  chat_bubble/SparkleExitTransition/aurora_calibration_strip 三处消费 + 375 在册
  两处硬编码不接线面）。若后续普查发现新漏修面，编号用 V3-FIX-387（385/386 已占）。
