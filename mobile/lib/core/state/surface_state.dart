import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/display/lexicon/error_lexicon.dart';

/// U-06 状态矩阵单一事实源（v3/04_ux/STATE_MATRIX.md 的 1:1 代码化）。
///
/// STATE_MATRIX 要求「所有可交互核心能力至少检查」的 22 个状态在此
/// 逐条建模；[SurfacePhase] 的取值集与矩阵文档逐行对齐，禁止在
/// feature 内自造第四套空/错/加载枚举（本卡 Locks: mobile-state-patterns）。
///
/// 分工边界（Forbidden：不重建既有权威真源）：
/// - 「异常 → 类别」判定与「类别 → 文案」翻译的唯一 owner 仍是
///   `core/display/lexicon/error_lexicon.dart`；本文件只做
///   「类别 → 矩阵相位」的**纯绑定**（switch 直出，无判定逻辑）；
/// - 「错误/等待的装饰预算」由 U-02 `tokens_v2/state_tokens.dart` 承担，
///   视觉消费点按 `SparkleStateMood.attention` 预算渲染。
///
/// 用户语言不变式：任何 [SurfacePhase.isFailure] 为真的相位，用户必须
/// 拿到至少一个可操作的下一步（[defaultNextSteps] 非空且非 wait-only），
/// 由 `surface_state_view.dart` 的渲染契约强制。
enum SurfacePhase {
  /// initial / no data——首帧未决。
  initial,

  /// loading <500ms——骨架/细进度即可，无需文字。
  loading,

  /// long-running stage——超过 500ms 的长等待，必须给 stage feedback。
  longRunning,

  /// empty——空数据。
  empty,

  /// partial data——部分数据可用（部分失败时主内容仍可读）。
  partial,

  /// success。
  success,

  /// error recoverable——可重试错误。
  errorRecoverable,

  /// error terminal——不可恢复错误（给返回/重建入口，不给死胡同）。
  errorTerminal,

  /// offline——离线（展示缓存快照时必须同时声明时点）。
  offline,

  /// reconnecting——连接中断自动重连中。
  reconnecting,

  /// permission denied——系统能力权限被拒。
  permissionDenied,

  /// auth expired——登录态过期。
  authExpired,

  /// model unavailable——AI 模型暂不可用。
  modelUnavailable,

  /// tool unavailable——工具/依赖服务暂不可用。
  toolUnavailable,

  /// awaiting clarification——等待用户澄清（Sparkle 的一次提问）。
  awaitingClarification,

  /// proposal pending confirmation——提案待确认（propose before mutate）。
  proposalPending,

  /// executing——已确认，执行中。
  executing,

  /// awaiting user——Hybrid run 中「轮到你了」。
  awaitingUser,

  /// conflict / version changed——内容已被他人/他端更新。
  conflict,

  /// unknown outcome——结果未知（不造确定性，给核查入口）。
  unknownOutcome,

  /// cancelled——用户主动取消。
  cancelled,

  /// deleted / revoked——资源已删除或被撤销。
  revoked,
}

/// 下一步动作类型（统一用户语言：同类动作全站同名同位）。
enum SurfaceNextStep {
  /// 重试当前操作。
  retry,

  /// 刷新/重新拉取（与 retry 的差异：重进数据面而非重放请求）。
  refresh,

  /// 返回上一级（终结错误的退路）。
  back,

  /// 重新登录（authExpired 专用）。
  reauthenticate,

  /// 去系统设置开权限（permissionDenied 专用）。
  openSettings,

  /// 去处理/去回应（awaiting clarification/user、proposal）。
  respond,

  /// 稍后自动恢复（reconnecting/executing 等等待族的可解释「等待」）。
  wait,

  /// 知道了（可关闭的提示）。
  dismiss,

  /// 反馈问题（unknown outcome 的兜底出路）。
  report,
}

/// 矩阵相位元数据与不变式（判定唯一出处，渲染层只消费）。
abstract final class SurfaceStateMatrix {
  /// STATE_MATRIX 全集（22 态，与文档逐行对齐）。
  static const List<SurfacePhase> allPhases = SurfacePhase.values;

  /// 失败/异常族相位——「核心 Journey 自动注入 ≥12 类失败状态」的
  /// 注入面即本清单（当前 14 类 ≥ 12 达标）。
  static const List<SurfacePhase> failurePhases = [
    SurfacePhase.errorRecoverable,
    SurfacePhase.errorTerminal,
    SurfacePhase.offline,
    SurfacePhase.reconnecting,
    SurfacePhase.permissionDenied,
    SurfacePhase.authExpired,
    SurfacePhase.modelUnavailable,
    SurfacePhase.toolUnavailable,
    SurfacePhase.conflict,
    SurfacePhase.partial,
    SurfacePhase.unknownOutcome,
    SurfacePhase.cancelled,
    SurfacePhase.revoked,
    SurfacePhase.longRunning,
  ];

  /// 等待族相位（stage feedback 契约的适用范围）。
  static const List<SurfacePhase> waitPhases = [
    SurfacePhase.loading,
    SurfacePhase.longRunning,
    SurfacePhase.reconnecting,
    SurfacePhase.executing,
  ];

  static bool isFailure(SurfacePhase phase) => failurePhases.contains(phase);

  static bool isWait(SurfacePhase phase) => waitPhases.contains(phase);

  /// 相位默认下一步（渲染层在调用方未显式给动作时的兜底语言）。
  ///
  /// 不变式：失败族必有非 [SurfaceNextStep.wait] 的可操作动作；
  /// 等待族的「等待」必须可解释（reconnecting/executing 带 wait）。
  static List<SurfaceNextStep> defaultNextSteps(SurfacePhase phase) =>
      switch (phase) {
        SurfacePhase.initial ||
        SurfacePhase.loading ||
        SurfacePhase.success ||
        SurfacePhase.empty =>
          const [],
        SurfacePhase.longRunning => const [SurfaceNextStep.back],
        SurfacePhase.partial => const [SurfaceNextStep.retry],
        SurfacePhase.errorRecoverable => const [SurfaceNextStep.retry],
        SurfacePhase.errorTerminal => const [SurfaceNextStep.back],
        SurfacePhase.offline => const [SurfaceNextStep.retry],
        // reconnecting 的「等待」只是解释（自动重连中）；可操作退路是
        // 返回——失败族不变式（必有非 wait 动作）钉死，勿删。
        SurfacePhase.reconnecting => const [
          SurfaceNextStep.wait,
          SurfaceNextStep.back,
        ],
        SurfacePhase.permissionDenied => const [SurfaceNextStep.openSettings],
        SurfacePhase.authExpired => const [SurfaceNextStep.reauthenticate],
        SurfacePhase.modelUnavailable => const [SurfaceNextStep.retry],
        SurfacePhase.toolUnavailable => const [SurfaceNextStep.retry],
        SurfacePhase.awaitingClarification ||
        SurfacePhase.proposalPending ||
        SurfacePhase.awaitingUser =>
          const [SurfaceNextStep.respond],
        SurfacePhase.executing => const [SurfaceNextStep.wait],
        SurfacePhase.conflict => const [SurfaceNextStep.refresh],
        SurfacePhase.unknownOutcome => const [
          SurfaceNextStep.refresh,
          SurfaceNextStep.report,
        ],
        SurfacePhase.cancelled => const [SurfaceNextStep.retry],
        SurfacePhase.revoked => const [SurfaceNextStep.back],
      };

  /// 失败族缺省必须带可操作（非 wait）下一步——测试钉死的不变式。
  static bool hasActionableNextStep(SurfacePhase phase) =>
      defaultNextSteps(phase).any((s) => s != SurfaceNextStep.wait);
}

/// 不可变表面状态值：相位 + 可选的人类可读补充。
@immutable
class SurfaceState {
  const SurfaceState(this.phase, {this.message, this.detail});

  final SurfacePhase phase;

  /// 覆盖默认标题的文案（应已本地化；由调用方经词典/arb 出词）。
  final String? message;

  /// 次级说明（诊断码等降级显示内容）。
  final String? detail;

  SurfaceState copyWith({SurfacePhase? phase, String? message, String? detail}) =>
      SurfaceState(
        phase ?? this.phase,
        message: message ?? this.message,
        detail: detail ?? this.detail,
      );

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is SurfaceState &&
          other.phase == phase &&
          other.message == message &&
          other.detail == detail;

  @override
  int get hashCode => Object.hash(phase, message, detail);

  @override
  String toString() => 'SurfaceState($phase, message: $message)';
}

/// 「既有词典类别 → 矩阵相位」唯一绑定表。
///
/// 纯绑定（switch 直出），判定仍单源 [categorizeUiError]；N35 的
/// offlineQueued 不是故障，落 [SurfacePhase.executing]（已受理、
/// 同步执行中语义），绝不落 unknown 错误通道。
SurfacePhase surfacePhaseFromUiErrorCategory(UiErrorCategory category) =>
    switch (category) {
      UiErrorCategory.network => SurfacePhase.errorRecoverable,
      UiErrorCategory.serviceDegraded => SurfacePhase.modelUnavailable,
      UiErrorCategory.timeout => SurfacePhase.errorRecoverable,
      UiErrorCategory.auth => SurfacePhase.authExpired,
      UiErrorCategory.server => SurfacePhase.errorRecoverable,
      UiErrorCategory.notFound => SurfacePhase.revoked,
      UiErrorCategory.rateLimit => SurfacePhase.errorRecoverable,
      UiErrorCategory.format => SurfacePhase.errorRecoverable,
      UiErrorCategory.offlineQueued => SurfacePhase.executing,
      UiErrorCategory.unknown => SurfacePhase.unknownOutcome,
    };

/// 任意异常 → 矩阵相位（判定走既有共享判定表，本函数零新增判定）。
SurfacePhase surfacePhaseFromError(Object? error) =>
    surfacePhaseFromUiErrorCategory(categorizeUiError(error));

/// AsyncValue 接缝适配：让既有 `.when` 面可以零成本换轨到矩阵语义。
///
/// - loading → [SurfacePhase.loading]（>500ms 的 stage feedback 由
///   `StagedSurfaceLoader` 在渲染层升格，不在状态层猜时间）；
/// - error → 判定走 [surfacePhaseFromError]；
/// - data 由调用方声明空/部分/成功（业务空态只有业务层知道）。
SurfaceState surfaceStateFromAsync<T>(AsyncValue<T> async, {Object? data}) {
  if (async.isLoading) {
    return const SurfaceState(SurfacePhase.loading);
  }
  final error = async.error;
  if (error != null || async.hasError) {
    return SurfaceState(surfacePhaseFromError(error));
  }
  if (async.hasValue && data == null) {
    return const SurfaceState(SurfacePhase.success);
  }
  return SurfaceState(
    data == null ? SurfacePhase.empty : SurfacePhase.success,
  );
}
