/// V4-F03 · 统一反馈呈现适配器（视觉/声/触唯一事件入口）。
///
/// 核心合同（`v4/02_design/MOTION_AUDIO_HAPTICS.md`）：「模型、业务代码和单独
/// 页面不得各自直接触发奖励。统一适配器消费已验证 ExperienceEvent，再按当前
/// 用户偏好、平台能力、应用可见性和证据新鲜度选 visual/audio/haptic。该事件
/// 是呈现投影，不新增第二个业务事实源；**缺回执时不发成功事件**。」
///
/// 三条卡验收的机制面（每条可失败，测试钉死）：
///
/// 1. **无 committed 回执不能触发成功；同 event 重播不重复震/音**——解析层
///    E1 门（state_confirmed ⇒ committed + receipt_ref，违者 ignore）+ 去重
///    集合按 [ExperienceEventModel.eventId]（内容寻址）抑制重播：重放不重复
///    感官、不重放庆祝动效，**文本状态仍恢复**（MOTION「恢复重放不重复音/
///    震/庆祝；文本状态仍恢复」）。
/// 2. **仅保存记忆不显示任务修改完成；证据登记不叫精通**——subject 语义
///    分层路由（封闭）：成功面孔 subject 封闭集 `{task, goal, plan}` 之外的
///    committed 事件**结构性**拿不到成功徽章与成功声/触；memory → 高亮 +
///    轻触（可选），证据登记（`evidence.registered`）→ 中性文案。冻结文案
///    表与 backend `app/core/experience_copy.py` v1 逐键镜像；全表无
///    「精通/已掌握」类词（mastery/deliverable 概念归 I07 锁面，本卡只预接
///    「不叫精通」的呈现纪律）。
/// 3. **断网未知状态仍可查，不渲染为绿色成功**——当前对象 version 未知
///    （`currentSubjectVersionToken == null`，含断网无法对账）→ 一律降级
///    [PixelRunState.unknown]（虚线 + 问号圈 + textSecondary），**绝不**借用
///    成功视觉；版本已知但与事件不符 → 过期抑制（无庆祝，仅中性文本）。
///
/// 视觉路径唯一：状态徽章一律经 F02 [PixelStateBadge] 族渲染（success 由
/// [PixelSuccessBadge] 单独承载——F02 红线：非成功树中不得出现该类型）；
/// 声/触经既有 [SensoryFeedbackService]（无第二发声/震动路径）。
library;

import 'package:flutter/foundation.dart';

import 'package:sparkle/core/design/pixel/pixel_state.dart';
import 'package:sparkle/core/experience/experience_event.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';

/// 冻结文案表（键→中文文案；与 backend `experience_copy.py`
/// `EXPERIENCE_COPY_TABLE` v1 逐键逐文案镜像；键集冻结，扩展 = 契约变更）。
const Map<String, String> kExperienceCopyTable = <String, String>{
  'task.committed': '任务已更新',
  'goal.committed': '目标已更新',
  'plan.committed': '计划已更新',
  'memory.saved': '记忆已保存',
  'run.completed': '运行已完成',
  'intervention.rendered': '已查看',
  'state.syncing': '同步中',
  'resume.available': '有可接续的进度',
  'correction.applied': '纠正已生效',
  'calibration.notice': '校准说明',
  'evidence.registered': '证据已登记',
  'progress.delta': '进度更新',
  'err.version_conflict': '你的设置已更新，需要重新生成',
  'err.unauthorized': '没有权限执行这个操作',
  'err.not_pending': '该操作已处理，无需重复确认',
  'err.expired': '该提案已过期，需要重新生成',
  'err.not_found': '没有找到对应的操作',
};

/// 成功面孔 subject 封闭集（唯一允许成功徽章 + 成功声/触的 subject 域）。
const Set<String> kSuccessFaceSubjectTypes = <String>{'task', 'goal', 'plan'};

/// 一次呈现决策的结果（语义分层后：动什么视觉、放什么声、震什么触）。
@immutable
class ExperienceFeedbackOutcome {
  const ExperienceFeedbackOutcome({
    required this.action,
    required this.copy,
    this.visualState,
    this.playsSuccessCue = false,
    this.playsSelectionCue = false,
    this.playsWarningCue = false,
  });

  /// 路由动作（观测/测试锚点）。
  final ExperienceFeedbackAction action;

  /// 冻结表文案（键集外 = 空串：不拼自由文本，不冒充语义）。
  final String copy;

  /// 状态徽章视觉（null = 无状态徽章，仅文案/高亮；success 值经
  /// [PixelStateBadge] 内部路由到 PixelSuccessBadge——唯一庆祝载体）。
  final PixelRunState? visualState;

  /// 成功声/触一次（仅成功面孔；重播/过期/未知恒 false）。
  final bool playsSuccessCue;

  /// 轻触（selection 级；memory 高亮可选轻反馈）。
  final bool playsSelectionCue;

  /// 警示触一次（明确操作失败；无连锁蜂鸣）。
  final bool playsWarningCue;

  /// 是否任何形式的庆祝（成功视觉或成功声/触）。
  bool get celebrates => playsSuccessCue || visualState == PixelRunState.success;
}

/// 呈现路由动作（封闭；观测与测试锚点）。
enum ExperienceFeedbackAction {
  /// 成功面孔：任务/目标/计划的 committed 回执（非重播、版本相符）。
  presentSuccess,

  /// 记忆已保存：高亮 + 可选轻触，永不成功面孔（卡验收 2）。
  presentHighlight,

  /// 中性信息呈现（运行完成/干预已查看/证据登记/同步中/纠正生效等）。
  presentNeutral,

  /// 失败呈现（terminal_failed：failed/conflict 徽章 + 警示触一次）。
  presentFailure,

  /// 当前对象版本未知（含断网对不上账）→ unknown 态，绝不成功视觉（卡验收 3）。
  presentUnknown,

  /// 同 event_id 重播：不重复震/音/庆祝；文本状态仍恢复。
  replaySuppressed,

  /// 事件版本与当前对象版本不符：过期抑制（无庆祝，仅中性文本）。
  staleVersionSuppressed,

  /// 结构违规/未注册形状：忽略 + 计数（绝不渲染任何成功类视觉）。
  ignoredInvalid,
}

/// 声/触出口抽象（默认实现委托既有 [SensoryFeedbackService]；测试注入记录器
/// ——适配器是唯一事件入口，本抽象不是第二发声路径，只是出口可替身）。
abstract class ExperienceSensorySink {
  Future<void> success();

  Future<void> selection();

  Future<void> warning();
}

/// 默认出口：委托既有 SensoryFeedbackService（统一感官服务，无第二路径）。
class SensoryFeedbackSink implements ExperienceSensorySink {
  const SensoryFeedbackSink();

  @override
  Future<void> success() => SensoryFeedbackService.emit(SensoryFeedbackEvent.success);

  @override
  Future<void> selection() => SensoryFeedbackService.emit(SensoryFeedbackEvent.selection);

  @override
  Future<void> warning() => SensoryFeedbackService.emit(SensoryFeedbackEvent.warning);
}

/// 统一反馈呈现适配器：experience_event.v1 → 视觉/声/触决策（唯一事件入口）。
class ExperienceFeedbackAdapter {
  ExperienceFeedbackAdapter({ExperienceSensorySink? sink})
      : _sink = sink ?? const SensoryFeedbackSink(),
        ignoredInvalidCount = 0;

  final ExperienceSensorySink _sink;

  /// replay 抑制集合（会话级；内容寻址 event_id——恢复重放不重复震/音）。
  final Set<String> _seenEventIds = <String>{};

  /// 结构违规/未注册形状事件的忽略计数（可观测面，B05 §8 双读纪律）。
  int ignoredInvalidCount;

  /// 断网/未知状态的查询面：unknown 徽章态（卡验收 3——仍可查，不渲染绿色）。
  static PixelRunState resolveUnknownDisplayState() => PixelRunState.unknown;

  /// 呈现一次事件（解析 → 重播抑制 → version 校验 → 语义分层路由）。
  ///
  /// [currentSubjectVersionToken]：当前已知的对象版本 token；null 表示当前
  /// 版本未知（断网/未装载），此时 committed 成功类事件一律降级 unknown 态。
  ExperienceFeedbackOutcome present(
    Map<String, dynamic>? json, {
    String? currentSubjectVersionToken,
  }) {
    final event = ExperienceEventModel.tryParse(json);
    if (event == null) {
      ignoredInvalidCount++;
      return const ExperienceFeedbackOutcome(action: ExperienceFeedbackAction.ignoredInvalid, copy: '');
    }

    final copy = kExperienceCopyTable[event.presentation.copyKey] ?? '';

    // —— replay 抑制（去重键 = 内容寻址 event_id；先记 id，再分流）——
    final isReplay = _seenEventIds.contains(event.eventId);
    _seenEventIds.add(event.eventId);
    if (isReplay) {
      // 重播：感官全关、无庆祝徽章（不重放上升动效）；文本状态仍恢复。
      return ExperienceFeedbackOutcome(
        action: ExperienceFeedbackAction.replaySuppressed,
        copy: copy,
      );
    }

    // —— kind 语义路由（解析层已强制 E1/E2）——
    if (event.commitState == 'error' || event.kind == 'terminal_failed') {
      // 失败面：version_conflict → conflict 徽章；其余 → failed 徽章。
      // 永不成功视觉（卡验收 3/契约 E2）；警示触一次（明确操作失败）。
      final state = event.errorState == 'version_conflict'
          ? PixelRunState.conflict
          : PixelRunState.failed;
      return ExperienceFeedbackOutcome(
        action: ExperienceFeedbackAction.presentFailure,
        copy: copy,
        visualState: state,
        playsWarningCue: true,
      );
    }

    if (!event.isSuccessKind) {
      // 非成功面孔 kind（syncing/resume/correction/calibration/progress_delta）：
      // 中性信息呈现，无庆祝、无声/触（证据登记 =「证据已登记」，非精通）。
      return ExperienceFeedbackOutcome(
        action: ExperienceFeedbackAction.presentNeutral,
        copy: copy,
      );
    }

    // —— 成功面孔 kind（state_confirmed + committed）：version 校验先行 ——
    if (currentSubjectVersionToken == null) {
      // 当前版本未知（断网/未对账）：unknown 态仍可查，不渲染绿色成功。
      return ExperienceFeedbackOutcome(
        action: ExperienceFeedbackAction.presentUnknown,
        copy: copy,
        visualState: PixelRunState.unknown,
      );
    }
    if (currentSubjectVersionToken != event.subject.versionToken) {
      // 过期事件（对象已前进）：抑制庆祝，仅中性文本。
      return ExperienceFeedbackOutcome(
        action: ExperienceFeedbackAction.staleVersionSuppressed,
        copy: copy,
      );
    }

    // —— subject 语义分层（封闭路由：记忆保存 ≠ 任务修改完成）——
    final subjectType = event.subject.type;
    if (kSuccessFaceSubjectTypes.contains(subjectType)) {
      return ExperienceFeedbackOutcome(
        action: ExperienceFeedbackAction.presentSuccess,
        copy: copy,
        visualState: PixelRunState.success,
        playsSuccessCue: true,
      );
    }
    if (subjectType == 'memory') {
      // 仅保存记忆：来源高亮 + 可选轻触；不用任务成功音/徽章（MOTION 乐谱行）。
      return ExperienceFeedbackOutcome(
        action: ExperienceFeedbackAction.presentHighlight,
        copy: copy,
        playsSelectionCue: true,
      );
    }
    // run / intervention：中性信息（运行完成/已查看），无庆祝。
    return ExperienceFeedbackOutcome(
      action: ExperienceFeedbackAction.presentNeutral,
      copy: copy,
    );
  }

  /// 感官出口（视觉由 [ExperienceFeedbackOutcome.visualState] 承载，声/触由
  /// 调用方在本出口触发——保证声/触也只经适配器决策发生）。
  Future<void> emitSensory(ExperienceFeedbackOutcome outcome) async {
    if (outcome.playsSuccessCue) {
      await _sink.success();
    }
    if (outcome.playsSelectionCue) {
      await _sink.selection();
    }
    if (outcome.playsWarningCue) {
      await _sink.warning();
    }
  }

  /// 测试/会话复位（清空去重集合与计数，不动偏好）。
  void reset() {
    _seenEventIds.clear();
    ignoredInvalidCount = 0;
  }
}
