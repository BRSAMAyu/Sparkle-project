/// V4-S01 · 语义乐谱动效预算（motion-policy 锁面的单一权威表）。
///
/// 契约真源：`v4/02_design/MOTION_AUDIO_HAPTICS.md` 事件乐谱的按压/提案/
/// 回执/证据/里程碑行。本文件把这些乐谱行变成**机器可测**的预算常量与
/// 范围校验——卡验收「enter/state/milestone 预算可测」的机制面：预算偏离
/// 乐谱窗口时 [SparkleSemanticMotionBudgets.validateAgainstScore] 显形，
/// 测试一正一反钉死。
///
/// 口径协调（不另立第二权威）：
/// - **reduce-motion 判定**一律走 MediaQuery 双源并集（`context.reduceMotion`
///   = 系统 disableAnimations ∨ accessibleNavigation ∪ app 内叠加，F06/
///   A-SPEC6 N32/AX-G5 统一口径；禁 `platformDispatcher` 直读）；
/// - **静态分支语义** = 「不装动画壳、直落终态」，**不通配 Duration.zero**
///   （V3-FIX-374：零时长 AnimatedSize 在 performLayout 期间同步变更触发
///   框架断言；且零时长仍是动画通路——静态分支才是真减法）；
/// - **低刺激档**（U-02 `StimulationLevel.low`）的通用令牌收缩在
///   `resolveSparkleMotionTokens`（sparkle_theme_extension.dart），与本表
///   正交：档位收缩通用动效令牌，本表冻结乐谱语义槽预算；
/// - **成功声/触**不归本表面：唯一感官出口是 F03 ExperienceFeedbackAdapter
///   （缺回执不发成功；重播不重复震/音）。本表只承载视觉动效节奏。
library;

import 'package:flutter/foundation.dart';

/// 语义乐谱动效槽（乐谱行 → 机器槽位映射）。
enum SparkleSemanticMotionSlot {
  /// 按压/选择：乐谱「80ms 轻压 1–2dp，焦点不移动」。
  press,

  /// 提案出现：乐谱「160–220ms 从纸面抬起」；不表示完成。
  proposalEnter,

  /// 写入提交成功的状态替换：乐谱「标题/状态 160ms 替换」。
  receiptReplace,

  /// 证据已登记：乐谱「小印章 160ms」；文字不说已掌握。
  evidenceStamp,

  /// 独立检验通过（里程碑）：乐谱「星点连线 ≤650ms，可跳过」。
  milestone,
}

/// 单槽乐谱窗口（毫秒闭区间 + 设计文档行原文，供违例信息回显）。
@immutable
class SemanticMotionWindow {
  const SemanticMotionWindow(this.minMs, this.maxMs, this.scoreLine);

  final int minMs;
  final int maxMs;

  /// MOTION_AUDIO_HAPTICS.md 事件乐谱行原文（违例信息直接引用，可对照）。
  final String scoreLine;

  bool contains(int ms) => ms >= minMs && ms <= maxMs;
}

/// 乐谱窗口表（与 MOTION_AUDIO_HAPTICS.md 事件乐谱逐行对齐；改窗口 =
/// 改设计契约，须先改乐谱文档）。
const Map<SparkleSemanticMotionSlot, SemanticMotionWindow>
    kSemanticMotionScoreWindows = <SparkleSemanticMotionSlot, SemanticMotionWindow>{
  SparkleSemanticMotionSlot.press:
      SemanticMotionWindow(80, 80, '80ms轻压1–2dp，焦点不移动'),
  SparkleSemanticMotionSlot.proposalEnter:
      SemanticMotionWindow(160, 220, '160–220ms从纸面抬起'),
  SparkleSemanticMotionSlot.receiptReplace:
      SemanticMotionWindow(160, 160, '标题/状态160ms替换'),
  SparkleSemanticMotionSlot.evidenceStamp:
      SemanticMotionWindow(160, 160, '小印章160ms'),
  SparkleSemanticMotionSlot.milestone:
      SemanticMotionWindow(0, 650, '星点连线≤650ms，可跳过'),
};

/// 语义乐谱预算（默认值 = 乐谱点值/区间中值的落点）。
///
/// 「预算可测」面：默认实例必须过 [validateAgainstScore]（测试钉死）；
/// 任何槽位被改出乐谱窗口 → 校验返回具名违例。里程碑上限 650ms 与
/// PixelSuccessBadge 既有 `milestoneMax ?? 650ms` 同源（V4-F06 已落）。
@immutable
class SparkleSemanticMotionBudgets {
  const SparkleSemanticMotionBudgets({
    this.press = const Duration(milliseconds: 80),
    this.proposalEnter = const Duration(milliseconds: 200),
    this.receiptReplace = const Duration(milliseconds: 160),
    this.evidenceStamp = const Duration(milliseconds: 160),
    this.milestone = const Duration(milliseconds: 650),
  });

  final Duration press;
  final Duration proposalEnter;
  final Duration receiptReplace;
  final Duration evidenceStamp;
  final Duration milestone;

  /// 按槽取预算（组件消费面；避免调用方散落 switch）。
  Duration forSlot(SparkleSemanticMotionSlot slot) => switch (slot) {
        SparkleSemanticMotionSlot.press => press,
        SparkleSemanticMotionSlot.proposalEnter => proposalEnter,
        SparkleSemanticMotionSlot.receiptReplace => receiptReplace,
        SparkleSemanticMotionSlot.evidenceStamp => evidenceStamp,
        SparkleSemanticMotionSlot.milestone => milestone,
      };

  /// 预算 ↔ 乐谱窗口校验：返回违例清单（空 = 合规）。
  List<String> validateAgainstScore() {
    final violations = <String>[];
    for (final slot in SparkleSemanticMotionSlot.values) {
      final window = kSemanticMotionScoreWindows[slot]!;
      final ms = forSlot(slot).inMilliseconds;
      if (!window.contains(ms)) {
        violations.add(
          '$slot: ${ms}ms 超出乐谱窗口 [${window.minMs}, ${window.maxMs}]ms'
          '（乐谱行：${window.scoreLine}）',
        );
      }
    }
    return violations;
  }
}

/// 全局唯一默认预算实例（组件默认消费面；测试反例自建变异实例）。
const SparkleSemanticMotionBudgets kSparkleSemanticMotionBudgets =
    SparkleSemanticMotionBudgets();
