/// V4-S03 · 平台语义触觉与去重（haptic-policy 锁面的单一权威）。
///
/// 契约真源：`v4/02_design/MOTION_AUDIO_HAPTICS.md` §触觉 + 事件乐谱触觉列。
/// 卡目标三件事，本文件逐件落成**机器可测**的门：
///
/// 1. **系统能力探测封装**——[resolveSparkleHapticCapability] 先探平台能力：
///    探测为不支持时**静默保持文本**，不震也不拿蜂鸣替代（乐谱原文「使用系统
///    语义/能力探测；不支持则不震，不能拿蜂鸣替代」）。
/// 2. **离散语义触觉**——乐谱触觉列收敛为封闭四槽 [SparkleSemanticHapticSlot]，
///    每槽映射到 Flutter `HapticFeedback` **官方 API** 一枚（
///    [kSparkleSemanticHapticPatterns]）：selection → selectionClick、轻触 →
///    lightImpact、成功 → successNotification、警示 → warningNotification。
///    只用平台语义 API、每次恰一枚，**不造自定义震动语言**（无组合脉冲、
///    无原始波形、无 amplitude 调制；源码棘轮测试钉死）。
/// 3. **native已有反馈避免双震 / 事件重播不震**——[SparkleSemanticHapticRequest]
///    的 `nativeHandled` 位让调用点声明「平台/框架此处已有系统触觉」（如
///    Material `enableFeedback` 按钮、日期/时间选择器滚轮、文本选择、长按菜单
///    ——框架层已调 `HapticFeedback`），命中即抑制（[SparkleHapticSuppression
///    .nativeFeedbackAlready]）；`isReplay` 位承接恢复重播（乐谱「恢复重播不
///    重复音/震」）；同槽短窗去重（[kSparkleHapticDedupeWindow]）兜住同一交互
///    内的叠加调用——同类事件短窗不重复触发。
///
/// 验收面（每条一个具名抑制原因，测试一正一反钉死）：
/// - 「无用户同意/已关闭/重播 = 0 触觉调用」→ [SparkleHapticSuppression
///   .userPreferenceOff]（偏好唯一权威 = U14 偏好面，读取
///   `SensoryFeedbackService.isHapticEnabled` 同键单源，不造第二权威）+
///   [SparkleHapticSuppression.eventReplay]。
/// - 「pending/unknown 不误用 success pattern」→ [SparkleHapticPhase.pending]/
///   [SparkleHapticPhase.unknown] 相位下**任何槽都不放行**（乐谱「冲突/未知/
///   失败」行触发条件是「明确操作失败」——未知不是失败，成功 pattern 更不可
///   借用），成功槽恒要求 [SparkleHapticPhase.terminalSuccess]（有 committed
///   回执的终态），警示槽恒要求 [SparkleHapticPhase.terminalFailure]。
/// - 「模拟器调用正确与真机舒适度分开出具结论」→ 本文件证据只覆盖**调用级**
///   （方法通道调用计数/模式选择/门控），硬件触感舒适度归真机面（Q06），未测
///   真机前一律记 DEVICE_UNVERIFIED（乐谱：「模拟器可测调用/去重/静音，不能
///   证明硬件触感舒适」）。
///
/// 口径协调（不另立第二权威，与在航线正交）：
/// - **音频**不归本表面：声侧继续走既有 `SensoryFeedbackService`（S02 音频
///   焦点策略面）；本文件零音频 API 引用（源码棘轮钉死）。
/// - **动效节奏**归 S01 `semantic_motion.dart`（motion-policy 锁面）；本表
///   只管触觉。
/// - **偏好键**归 U14（`sensory_feedback.haptic_enabled` 单源经
///   `SensoryFeedbackService` 读写）；本文件不新增任何偏好键。
/// - **重播抑制的第一道门**在 F03 适配器（event_id 去重集合）；本文件的
///   `isReplay` 位是触觉通道的第二道独立防线（防御纵深），不是替代。
/// - **V3 路径向后兼容**（卡 rollback 条款）：V3 UI 事件词表的触觉映射与其
///   成就双脉冲保留在 `SensoryFeedbackService`（V3 已 DONE 快照继承，不重写）；
///   V4 语义面（experience_event 呈现链）一律经本锁面。
library;

import 'package:flutter/foundation.dart';

import 'package:flutter/services.dart';

import 'package:sparkle/core/services/sensory_feedback_service.dart';

/// 语义触觉槽（乐谱触觉列 → 离散槽；封闭四元集，扩展 = 改设计契约）。
enum SparkleSemanticHapticSlot {
  /// 按压/选择行：「明确离散选择可系统selection；普通滚动无」。
  selection,

  /// 仅记忆已保存行「轻selection可选」/ 证据已登记行「可选轻impact」
  /// ——已确认结果面上的可选轻触，不用任务成功 pattern。
  lightImpact,

  /// 写入提交成功行 / 独立检验通过行：「系统success一次」。
  success,

  /// 冲突/未知/失败行：「明确操作失败可systemwarning一次」。
  warning,
}

/// 提交相（卡验收 2 的机制面：pending/unknown 不误用 success pattern）。
enum SparkleHapticPhase {
  /// 用户主动操作（按压/选择/轻触位）——非结果面。
  userInitiated,

  /// 处理中/待定：不产生任何触觉（成功 pattern 不可借用，警示也不可——
  /// 乐谱警示行触发条件是「明确操作失败」）。
  pending,

  /// 版本未知/断网未对账：不产生任何触觉（F03 presentUnknown 面同口径）。
  unknown,

  /// 已确认终态成功（committed 回执在手）。
  terminalSuccess,

  /// 已确认终态失败（明确操作失败）。
  terminalFailure,
}

/// 平台触觉能力（探测结论；封闭二元）。
enum SparkleHapticCapability { supported, unsupported }

/// 能力探测（纯函数；可注入替身）。
///
/// 产品面 = Flutter Mobile（iOS/Android）：两平台由系统语义 API 承载触觉。
/// 其余目标（web/desktop/fuchsia）按**保守侧**判不支持——静默保持文本，不震
/// 也不蜂鸣替代。macOS 触控板虽有 NSHapticFeedbackManager，但不在本卡产品面，
/// 留真机面（Q06）证实后再入表——「不支持」的代价是少震，「误支持」的代价是
/// 无证据的触觉承诺，按乐谱「不支持则不震」取前者。
SparkleHapticCapability resolveSparkleHapticCapability(TargetPlatform platform) {
  switch (platform) {
    case TargetPlatform.iOS:
    case TargetPlatform.android:
      return SparkleHapticCapability.supported;
    case TargetPlatform.macOS:
    case TargetPlatform.windows:
    case TargetPlatform.linux:
    case TargetPlatform.fuchsia:
      return SparkleHapticCapability.unsupported;
  }
}

/// 平台语义触觉模式（封闭七元 = Flutter `HapticFeedback` 官方 API 面一一对应；
/// 每次派发至多执行**一枚**，不组合、不调幅——不造自定义震动语言）。
enum SparkleHapticPattern {
  /// 系统选择咔哒（iOS selection changed / Android clock tick 语义）。
  selectionClick(HapticFeedback.selectionClick),

  /// 轻击打。
  lightImpact(HapticFeedback.lightImpact),

  /// 中击打。
  mediumImpact(HapticFeedback.mediumImpact),

  /// 重击打。
  heavyImpact(HapticFeedback.heavyImpact),

  /// 系统 success 通知触觉（iOS UINotificationFeedbackGenerator success；
  /// Android API 30+ CONFIRM，更早版本平台自身无效果——平台策略，不蜂鸣替代）。
  successNotification(HapticFeedback.successNotification),

  /// 系统 warning 通知触觉（iOS warning；Android API 30+ KEYBOARD_TAP）。
  warningNotification(HapticFeedback.warningNotification),

  /// 系统 error 通知触觉（iOS error；Android API 30+ REJECT）。
  errorNotification(HapticFeedback.errorNotification);

  const SparkleHapticPattern(this.play);

  /// 执行该模式（官方 API 静态方法直引；经 [SparkleHapticChannel] 出口）。
  final Future<void> Function() play;
}

/// 乐谱触觉列 → 官方模式映射（唯一映射表；iOS/Android 同表——平台差异由
/// 官方 API 的引擎实现承载，本表不按平台分裂、不自造平台方言）。
const Map<SparkleSemanticHapticSlot, SparkleHapticPattern> kSparkleSemanticHapticPatterns =
    <SparkleSemanticHapticSlot, SparkleHapticPattern>{
  SparkleSemanticHapticSlot.selection: SparkleHapticPattern.selectionClick,
  SparkleSemanticHapticSlot.lightImpact: SparkleHapticPattern.lightImpact,
  SparkleSemanticHapticSlot.success: SparkleHapticPattern.successNotification,
  SparkleSemanticHapticSlot.warning: SparkleHapticPattern.warningNotification,
};

/// 槽位 ↔ 放行相（封闭表）：outcome 槽恒要求已确认终态；pending/unknown 不在
/// 任何槽的放行集——「不误用 success pattern」的结构面。
const Map<SparkleSemanticHapticSlot, Set<SparkleHapticPhase>> kSparkleHapticSlotPhases =
    <SparkleSemanticHapticSlot, Set<SparkleHapticPhase>>{
  SparkleSemanticHapticSlot.selection: <SparkleHapticPhase>{
    SparkleHapticPhase.userInitiated,
  },
  SparkleSemanticHapticSlot.lightImpact: <SparkleHapticPhase>{
    SparkleHapticPhase.userInitiated,
    SparkleHapticPhase.terminalSuccess,
  },
  SparkleSemanticHapticSlot.success: <SparkleHapticPhase>{
    SparkleHapticPhase.terminalSuccess,
  },
  SparkleSemanticHapticSlot.warning: <SparkleHapticPhase>{
    SparkleHapticPhase.terminalFailure,
  },
};

/// 同槽去重窗（「同类事件短窗不重复触发」）。
///
/// 值 = 覆盖同一交互内叠加调用的短窗（按压与成功是**不同槽**，不受本窗合并
/// ——乐谱「提交按钮的按压反馈立即，成功反馈在回执后；两者不可合并」由槽位
/// 分离保证，与本窗正交）。改值 = 改设计契约，须同步 MOTION 文档与测试。
const Duration kSparkleHapticDedupeWindow = Duration(milliseconds: 500);

/// 一次触觉派发请求（全部位显式；无默认终态，杜绝调用方顺手传错相）。
@immutable
class SparkleSemanticHapticRequest {
  const SparkleSemanticHapticRequest({
    required this.slot,
    required this.phase,
    this.isReplay = false,
    this.nativeHandled = false,
  });

  /// 语义槽。
  final SparkleSemanticHapticSlot slot;

  /// 提交相（outcome 槽必须如实声明终态，见 [kSparkleHapticSlotPhases]）。
  final SparkleHapticPhase phase;

  /// 恢复重播位：true = 本事件是历史重放（乐谱「恢复重播不重复音/震」）。
  final bool isReplay;

  /// native 已有反馈位：调用点声明平台/框架此处已有系统触觉（Material
  /// enableFeedback、选择器滚轮、文本选择、长按菜单等）——避免双震。
  final bool nativeHandled;
}

/// 抑制原因（封闭；每验收面一个具名值，测试与观测计数共用）。
enum SparkleHapticSuppression {
  /// 放行（非抑制）。
  none,

  /// 用户偏好关闭或未装配（无用户同意 → 0 触觉调用；唯一权威 = U14 偏好面）。
  userPreferenceOff,

  /// 平台能力不支持（静默保持文本，不蜂鸣替代）。
  platformUnsupported,

  /// 事件重播（恢复重放不重复震）。
  eventReplay,

  /// 相位不放行（pending/unknown 或槽/相不符——success pattern 不可误用）。
  phaseNotHapticEligible,

  /// native/框架此处已有系统触觉（避免双震）。
  nativeFeedbackAlready,

  /// 同槽去重窗内（同类事件短窗不重复触发）。
  dedupedWithinWindow,
}

/// 一次派发决策（可观测；pattern 仅在放行时非空）。
@immutable
class SparkleHapticDecision {
  const SparkleHapticDecision({
    required this.allowed,
    required this.suppression,
    this.pattern,
  });

  const SparkleHapticDecision.allowed(this.pattern)
      : allowed = true,
        suppression = SparkleHapticSuppression.none;

  const SparkleHapticDecision.suppressed(SparkleHapticSuppression reason)
      : allowed = false,
        suppression = reason,
        pattern = null;

  final bool allowed;

  /// 放行时为 [SparkleHapticSuppression.none]。
  final SparkleHapticSuppression suppression;

  final SparkleHapticPattern? pattern;
}

/// 纯门（无状态；决策输入全部显式传入，测试一正一反直钉）。
abstract final class SparkleSemanticHapticGate {
  /// 按乐谱顺序裁决：偏好 → 能力 → 重播 → 相位 → native 双震 → 去重窗。
  /// 先到先止，抑制原因即首个命中门。
  static SparkleHapticDecision decide({
    required SparkleSemanticHapticRequest request,
    required bool preferenceEnabled,
    required SparkleHapticCapability capability,
    required bool sameSlotWithinDedupeWindow,
  }) {
    // 1. 无用户同意/已关闭 → 0 触觉调用（U14 偏好面唯一权威）。
    if (!preferenceEnabled) {
      return const SparkleHapticDecision.suppressed(SparkleHapticSuppression.userPreferenceOff);
    }
    // 2. 能力不支持 → 静默保持文本（不震、不蜂鸣替代）。
    if (capability == SparkleHapticCapability.unsupported) {
      return const SparkleHapticDecision.suppressed(SparkleHapticSuppression.platformUnsupported);
    }
    // 3. 事件重播 → 不震（乐谱「恢复重播不重复音/震」）。
    if (request.isReplay) {
      return const SparkleHapticDecision.suppressed(SparkleHapticSuppression.eventReplay);
    }
    // 4. 相位不放行：pending/unknown 不产生任何触觉；outcome 槽恒要求已确认
    //    终态（success pattern 只属于有回执的终态成功）。
    if (!kSparkleHapticSlotPhases[request.slot]!.contains(request.phase)) {
      return const SparkleHapticDecision.suppressed(SparkleHapticSuppression.phaseNotHapticEligible);
    }
    // 5. native 已有反馈 → 不叠加（避免双震）。
    if (request.nativeHandled) {
      return const SparkleHapticDecision.suppressed(SparkleHapticSuppression.nativeFeedbackAlready);
    }
    // 6. 同槽去重窗 → 不重复触发。
    if (sameSlotWithinDedupeWindow) {
      return const SparkleHapticDecision.suppressed(SparkleHapticSuppression.dedupedWithinWindow);
    }
    final pattern = kSparkleSemanticHapticPatterns[request.slot];
    if (pattern == null) {
      // 封闭表健全性防线（不可达面）：无模式 = 无触觉（fail-safe 同向）。
      return const SparkleHapticDecision.suppressed(SparkleHapticSuppression.phaseNotHapticEligible);
    }
    return SparkleHapticDecision.allowed(pattern);
  }
}

/// 唯一震动出口抽象（默认实现 = Flutter `HapticFeedback` 官方 API；测试注入
/// 记录器）。V4 语义面的物理震动出口**只有本通道**——第二处直调
/// `HapticFeedback.*` 的新增即违锁（源码棘轮测试钉死）。
abstract class SparkleHapticChannel {
  const SparkleHapticChannel();

  Future<void> play(SparkleHapticPattern pattern);
}

/// 默认出口：官方 `HapticFeedback` API（引擎侧承载 iOS/Android 平台语义）。
class HapticFeedbackChannel extends SparkleHapticChannel {
  const HapticFeedbackChannel();

  @override
  Future<void> play(SparkleHapticPattern pattern) => pattern.play();
}

/// 语义触觉派发器：纯门 [SparkleSemanticHapticGate] + 去重窗状态 + 可观测计数。
///
/// 偏好读取默认接 `SensoryFeedbackService.isHapticEnabled`（U14 偏好面写入门
/// 控的同一持久键——不造第二权威）。测试经 [resetForTest] 清态、经构造参数注入
/// 探针/时钟/通道替身。
class SemanticHapticDispatcher {
  SemanticHapticDispatcher({
    Future<bool> Function()? preferenceReader,
    SparkleHapticChannel channel = const HapticFeedbackChannel(),
    SparkleHapticCapability Function(TargetPlatform platform)? capabilityProbe,
    this.dedupeWindow = kSparkleHapticDedupeWindow,
    DateTime Function()? clock,
  })  : _preferenceReader = preferenceReader ?? SensoryFeedbackService.isHapticEnabled,
        _channel = channel,
        _capabilityProbe = capabilityProbe ?? resolveSparkleHapticCapability,
        _clock = clock ?? DateTime.now;

  /// 去重窗（暴露给观测/测试；改默认值 = 改契约）。
  final Duration dedupeWindow;

  final Future<bool> Function() _preferenceReader;
  final SparkleHapticChannel _channel;
  final SparkleHapticCapability Function(TargetPlatform platform) _capabilityProbe;
  final DateTime Function() _clock;

  /// 全局默认派发器（产品装配面；测试经构造自建实例 + [resetForTest] 清态，
  /// 不复用全局单例）。
  static final SemanticHapticDispatcher instance = SemanticHapticDispatcher();

  final Map<SparkleSemanticHapticSlot, DateTime> _lastFiredAt = <SparkleSemanticHapticSlot, DateTime>{};

  /// 派发计数（调用级证据面：模拟器/测试环境认这个）。
  int firedCount = 0;

  /// 按模式分列的放行计数。
  final Map<SparkleHapticPattern, int> firedByPattern = <SparkleHapticPattern, int>{};

  /// 按抑制原因分列的抑制计数（none 恒不入表）。
  final Map<SparkleHapticSuppression, int> suppressedBy = <SparkleHapticSuppression, int>{};

  /// 派发一次：裁决 →（放行）经唯一通道执行一枚官方模式并记去重窗。
  Future<SparkleHapticDecision> dispatch(
    SparkleSemanticHapticRequest request,
  ) async {
    final now = _clock();
    final last = _lastFiredAt[request.slot];
    final withinWindow = last != null && now.difference(last) < dedupeWindow;
    final decision = SparkleSemanticHapticGate.decide(
      request: request,
      preferenceEnabled: await _preferenceReader(),
      capability: _capabilityProbe(defaultTargetPlatform),
      sameSlotWithinDedupeWindow: withinWindow,
    );
    if (!decision.allowed) {
      suppressedBy[decision.suppression] = (suppressedBy[decision.suppression] ?? 0) + 1;
      return decision;
    }
    _lastFiredAt[request.slot] = now;
    firedCount++;
    firedByPattern[decision.pattern!] = (firedByPattern[decision.pattern!] ?? 0) + 1;
    await _channel.play(decision.pattern!);
    return decision;
  }

  /// 会话/测试复位（清去重窗与计数；不动偏好——偏好归 U14 持久层）。
  void resetForTest() {
    _lastFiredAt.clear();
    firedCount = 0;
    firedByPattern.clear();
    suppressedBy.clear();
  }
}
