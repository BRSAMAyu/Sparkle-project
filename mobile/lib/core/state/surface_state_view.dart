import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/state/staged_loading.dart';
import 'package:sparkle/core/state/surface_state.dart';
import 'package:sparkle/core/state/surface_state_injection.dart';
import 'package:sparkle/l10n/app_localizations.dart';

/// U-06 统一状态渲染组件——所有核心表面的「现在发生什么 / 能做什么」
/// 唯一出口（STATE_MATRIX 22 态 × 统一用户语言）。
///
/// 渲染分派：
/// - 等待族（loading/longRunning）→ [StagedSurfaceLoader]（>500ms 升格
///   stage feedback，全程无裸 spinner）；
/// - 失败族 → 图标 + 标题 + 次级说明 + **至少一个可操作下一步**——调用方
///   按能力给回调（[onRetry] / [onBack] / …），组件按矩阵默认下一步
///   匹配渲染；调用方一个回调都没给时，失败态自动兜底「返回」
///   （Navigator.maybePop），杜绝死胡同（验收「所有错误有下一步」由本
///   构造保证，不靠调用点自觉）；
/// - offline/reconnecting → 非阻断条式（等待族语义 + 可解释动作）；
/// - partial → 次级提示条叠在 [contentBelow] 之上（部分数据仍可读）。
class SurfaceStateView extends StatelessWidget {
  const SurfaceStateView({
    required this.state,
    super.key,
    this.onRetry,
    this.onRefresh,
    this.onBack,
    this.onReauthenticate,
    this.onOpenSettings,
    this.onRespond,
    this.onDismiss,
    this.onReport,
    this.contentBelow,
    this.compact = false,
  });

  final SurfaceState state;

  /// 下一步回调——按表面能力提供，未提供的能力按钮不渲染。
  final VoidCallback? onRetry;
  final VoidCallback? onRefresh;
  final VoidCallback? onBack;
  final VoidCallback? onReauthenticate;
  final VoidCallback? onOpenSettings;
  final VoidCallback? onRespond;
  final VoidCallback? onDismiss;
  final VoidCallback? onReport;

  /// partial 态的主内容（部分数据可读 + 次级提示条）。
  final Widget? contentBelow;

  /// 紧凑形态（卡内/区块内）。
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final phase = state.phase;
    // offline/reconnecting 先于等待族判定：它们是「非阻断横幅 + 可解释
    // 动作」的降级/重连语义，不能被 isWait 吞成分阶加载（否则用户拿不到
    // 任何动作——reconnecting 死胡同正是覆盖率测试抓出的缺陷，勿回退）。
    if (phase == SurfacePhase.offline || phase == SurfacePhase.reconnecting) {
      return _StateBanner(
        state: _copy(context, state),
        tone: _StateTone.warning,
        icon: phase == SurfacePhase.offline
            ? Icons.cloud_off_rounded
            : Icons.sync_rounded,
        actions: _actionsFor(
          context,
          SurfaceStateMatrix.defaultNextSteps(phase),
        ),
      );
    }
    if (SurfaceStateMatrix.isWait(phase) || phase == SurfacePhase.initial) {
      // longRunning 是「>500ms 已成事实」的长等待：给可离开退路
      // （CORE_INTERACTION_PATTERNS #5）；快路径相位不留多余动作。
      return StagedSurfaceLoader(
        compact: compact,
        height: compact ? 72 : null,
        onLeave: phase == SurfacePhase.longRunning
            ? (onBack ?? () => Navigator.maybePop(context))
            : null,
      );
    }
    if (phase == SurfacePhase.partial) {
      final banner = _StateBanner(
        state: _copy(context, state),
        tone: _StateTone.warning,
        icon: Icons.warning_amber_rounded,
        actions: _actionsFor(
          context,
          SurfaceStateMatrix.defaultNextSteps(phase),
        ),
      );
      final below = contentBelow;
      if (below == null) return banner;
      return Column(
        mainAxisSize: MainAxisSize.min,
        children: [banner, below],
      );
    }
    if (phase == SurfacePhase.empty) {
      return const EmptyState();
    }
    if (phase == SurfacePhase.success) {
      return contentBelow ?? const SizedBox.shrink();
    }
    // U-08 a11y：失败族是状态突变（success→error 的整面切换），读屏
    // 用户扫焦到新内容前就要听到「出错了/下一步做什么」。整块 liveRegion
    // 使「标题+说明+下一步动作」进入视野即播报（WCAG 4.1.3 status
    // messages；ACCESSIBILITY.md「error 与 validation 可被辅助技术读出」）。
    return Semantics(
      container: true,
      liveRegion: true,
      child: _failureBodyInner(context, phase),
    );
  }

  /// 失败族渲染：图标 + 标题 + 说明 + 保证非空的下一步动作行。
  Widget _failureBodyInner(BuildContext context, SurfacePhase phase) {
    final copy = _copy(context, state);
    final steps = SurfaceStateMatrix.defaultNextSteps(phase);
    final actions = _actionsFor(context, steps);
    final body = Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(
          _iconFor(phase),
          size: compact ? DS.iconSizeLg : DS.iconSize3xl,
          color: DS.warning,
        ),
        const SizedBox(height: DS.spacing12),
        Text(
          copy.title,
          style: TextStyle(
            fontSize: compact ? DS.fontSizeBase : DS.fontSizeLg,
            fontWeight: DS.fontWeightSemibold,
            color: DS.textPrimary,
          ),
          textAlign: TextAlign.center,
        ),
        if (copy.detailText != null && copy.detailText!.isNotEmpty) ...[
          const SizedBox(height: DS.spacing8),
          Text(
            copy.detailText!,
            style: TextStyle(
              fontSize: DS.fontSizeSm,
              color: DS.textSecondary,
            ),
            textAlign: TextAlign.center,
          ),
        ],
        const SizedBox(height: DS.spacing16),
        Wrap(
          spacing: DS.spacing8,
          runSpacing: DS.spacing8,
          alignment: WrapAlignment.center,
          children: actions,
        ),
      ],
    );
    if (compact) {
      return Padding(
        padding: const EdgeInsets.all(DS.spacing12),
        child: body,
      );
    }
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(DS.spacing32),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: body,
        ),
      ),
    );
  }

  /// 矩阵默认下一步 → 按钮。**死胡同守卫**：调用方没给任何可用回调时，
  /// 失败态自动兜底「返回」（maybePop），保证动作行永不为空。
  List<Widget> _actionsFor(BuildContext context, List<SurfaceNextStep> steps) {
    final l10n = context.l10n;
    final widgets = <Widget>[];
    for (final step in steps) {
      final callback = _callbackFor(context, step);
      final label = _labelFor(l10n, step);
      if (callback == null || label == null) continue;
      widgets.add(
        SparkleButton(
          label: label,
          onPressed: callback,
          variant: step == SurfaceNextStep.retry
              ? ButtonVariant.primary
              : ButtonVariant.ghost,
          icon: Icon(_stepIcon(step), size: DS.iconSizeSm),
        ),
      );
    }
    // 死胡同守卫（扩大到一切要求用户行动的相位）：调用方没给任何可用
    // 回调时，自动兜底「返回」，动作行永不为空。
    final requiresAction =
        SurfaceStateMatrix.isFailure(state.phase) ||
            state.phase == SurfacePhase.awaitingClarification ||
            state.phase == SurfacePhase.proposalPending ||
            state.phase == SurfacePhase.awaitingUser;
    if (widgets.isEmpty && requiresAction) {
      widgets.add(
        SparkleButton.ghost(
          label: l10n.back,
          onPressed: () => Navigator.maybePop(context),
          icon: const Icon(Icons.arrow_back_rounded),
        ),
      );
    }
    return widgets;
  }

  VoidCallback? _callbackFor(BuildContext context, SurfaceNextStep step) =>
      switch (step) {
        SurfaceNextStep.retry => onRetry,
        SurfaceNextStep.refresh => onRefresh ?? onRetry,
        SurfaceNextStep.back =>
          onBack ?? (() => Navigator.maybePop(context)),
        SurfaceNextStep.reauthenticate => onReauthenticate,
        SurfaceNextStep.openSettings => onOpenSettings,
        SurfaceNextStep.respond => onRespond,
        SurfaceNextStep.wait => null,
        SurfaceNextStep.dismiss => onDismiss,
        SurfaceNextStep.report => onReport,
      };

  String? _labelFor(AppLocalizations l10n, SurfaceNextStep step) =>
      switch (step) {
        SurfaceNextStep.retry => l10n.retry,
        SurfaceNextStep.refresh => l10n.stateNextRefresh,
        SurfaceNextStep.back => l10n.back,
        SurfaceNextStep.reauthenticate => l10n.stateNextRelogin,
        SurfaceNextStep.openSettings => l10n.stateNextOpenSettings,
        SurfaceNextStep.respond => l10n.stateNextRespond,
        SurfaceNextStep.wait => null,
        SurfaceNextStep.dismiss => l10n.stateNextDismiss,
        SurfaceNextStep.report => l10n.stateNextReport,
      };

  IconData _stepIcon(SurfaceNextStep step) => switch (step) {
        SurfaceNextStep.retry => Icons.refresh_rounded,
        SurfaceNextStep.refresh => Icons.sync_rounded,
        SurfaceNextStep.back => Icons.arrow_back_rounded,
        SurfaceNextStep.reauthenticate => Icons.login_rounded,
        SurfaceNextStep.openSettings => Icons.settings_outlined,
        SurfaceNextStep.respond => Icons.arrow_forward_rounded,
        SurfaceNextStep.wait => Icons.hourglass_top_rounded,
        SurfaceNextStep.dismiss => Icons.check_rounded,
        SurfaceNextStep.report => Icons.feedback_outlined,
      };

  IconData _iconFor(SurfacePhase phase) => switch (phase) {
        SurfacePhase.errorTerminal => Icons.report_rounded,
        SurfacePhase.permissionDenied => Icons.lock_outline_rounded,
        SurfacePhase.authExpired => Icons.key_off_outlined,
        SurfacePhase.modelUnavailable => Icons.psychology_alt_outlined,
        SurfacePhase.toolUnavailable => Icons.extension_off_outlined,
        SurfacePhase.conflict => Icons.merge_type_rounded,
        SurfacePhase.unknownOutcome => Icons.help_outline_rounded,
        SurfacePhase.cancelled => Icons.cancel_outlined,
        SurfacePhase.revoked => Icons.delete_outline_rounded,
        _ => Icons.error_outline_rounded,
      };

  _StateCopy _copy(BuildContext context, SurfaceState state) {
    final l10n = context.l10n;
    final title = state.message ?? _defaultTitle(l10n, state.phase);
    final detail = state.detail;
    return _StateCopy(title: title, detailText: detail);
  }

  String _defaultTitle(AppLocalizations l10n, SurfacePhase phase) =>
      switch (phase) {
        SurfacePhase.partial => l10n.statePhasePartial,
        SurfacePhase.offline => l10n.statePhaseOffline,
        SurfacePhase.reconnecting => l10n.statePhaseReconnecting,
        SurfacePhase.permissionDenied => l10n.statePhasePermissionDenied,
        SurfacePhase.authExpired => l10n.statePhaseAuthExpired,
        SurfacePhase.modelUnavailable => l10n.statePhaseModelUnavailable,
        SurfacePhase.toolUnavailable => l10n.statePhaseToolUnavailable,
        SurfacePhase.conflict => l10n.statePhaseConflict,
        SurfacePhase.unknownOutcome => l10n.statePhaseUnknownOutcome,
        SurfacePhase.errorTerminal => l10n.statePhaseTerminal,
        SurfacePhase.cancelled => l10n.statePhaseCancelled,
        SurfacePhase.revoked => l10n.statePhaseRevoked,
        // 可恢复错误与既有词典共享口径（error_lexicon 单源）。
        _ => l10n.errorDefaultTitle,
      };
}

class _StateCopy {
  const _StateCopy({required this.title, this.detailText});

  final String title;
  final String? detailText;
}

enum _StateTone { warning, error }

/// 非阻断状态条（offline/reconnecting/partial——等待与降级语义，
/// 不抢占主内容）。
class _StateBanner extends StatelessWidget {
  const _StateBanner({
    required this.state,
    required this.tone,
    required this.icon,
    this.actions = const [],
  });

  final _StateCopy state;
  final _StateTone tone;
  final IconData icon;
  final List<Widget> actions;

  @override
  Widget build(BuildContext context) {
    final color = tone == _StateTone.error ? DS.error : DS.warning;
    // U-08 a11y：offline/reconnecting/partial 是非阻断状态条，视觉上不
    // 抢占主内容，但读屏不能漏——liveRegion 让降级/重连/部分数据的出现
    // 与解除都被自动播报（不靠颜色单独传达，条内自带图标+文字）。
    return Semantics(
      container: true,
      liveRegion: true,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing16,
          vertical: DS.spacing8,
        ),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.10),
          border:
              Border(bottom: BorderSide(color: color.withValues(alpha: 0.3))),
        ),
        child: Row(
          children: [
            Icon(icon, size: DS.iconSizeSm, color: color),
            const SizedBox(width: DS.spacing8),
            Expanded(
              child: Text(
                state.title,
                style:
                    TextStyle(fontSize: DS.fontSizeSm, color: DS.textPrimary),
              ),
            ),
            ...actions,
          ],
        ),
      ),
    );
  }
}

/// 表面状态闸门——核心表面接矩阵的**唯一接入点**。
///
/// 职责：
/// 1. debug 注入拦截：有注入时以注入相位渲染（走与真实错误相同的
///    [SurfaceStateView] 分支）；release 恒等直通；
/// 2. 矩阵分派：success → [content]；empty → [emptyBuilder]（缺省
///    EmptyState）；其余 → [SurfaceStateView]（partial 自动叠主内容）。
///
/// 用法（真实接缝）：
/// ```dart
/// SurfaceStateGate(
///   surfaceId: 'community.feed',
///   state: surfaceStateFromAsync(feedAsync),
///   content: () => FeedList(page),
///   emptyBuilder: () => EmptyState.noChats(),
///   viewCallbacks: SurfaceStateCallbacks(onRetry: refresh),
/// )
/// ```
class SurfaceStateGate extends ConsumerWidget {
  const SurfaceStateGate({
    required this.surfaceId,
    required this.state,
    required this.content,
    super.key,
    this.emptyBuilder,
    this.partialContent,
    this.onRetry,
    this.onRefresh,
    this.onBack,
    this.onReauthenticate,
    this.onOpenSettings,
    this.onRespond,
    this.onDismiss,
    this.onReport,
  });

  /// 登记表口径的表面 id（见 coreSurfaceIds）。
  final String surfaceId;

  /// 由调用方真实接缝解析出的状态（AsyncValue/业务态 → SurfaceState）。
  final SurfaceState state;

  final WidgetBuilder content;

  /// 业务空态（业务空语义只有业务层知道；缺省通用 EmptyState）。
  final WidgetBuilder? emptyBuilder;

  /// partial 态的主内容 builder——**独立于 [content]**：partial 相位下
  /// 调用方的真实数据接缝可能根本没有值（如注入/真实错误叠加），走
  /// [content] 可能对未决 AsyncValue 取值崩溃；未提供时只渲染降级横幅。
  final WidgetBuilder? partialContent;

  final VoidCallback? onRetry;
  final VoidCallback? onRefresh;
  final VoidCallback? onBack;
  final VoidCallback? onReauthenticate;
  final VoidCallback? onOpenSettings;
  final VoidCallback? onRespond;
  final VoidCallback? onDismiss;
  final VoidCallback? onReport;

  static Widget _defaultEmpty(BuildContext context) => const EmptyState();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final overrides = ref.watch(surfaceStateOverridesProvider);
    final injected = resolveInjectedSurfaceState(overrides, surfaceId);
    final effective = injected ?? state;
    return _dispatch(context, effective);
  }

  Widget _dispatch(BuildContext context, SurfaceState effective) {
    switch (effective.phase) {
      case SurfacePhase.success:
        return content(context);
      case SurfacePhase.empty:
        // 空态绝不能隐式回落到 [content]——content 通常要求真实数据
        // 已就绪（requireValue/非空断言），注入或真实边缘序下取值会崩。
        // 未声明 emptyBuilder 时统一落通用 EmptyState。
        return (emptyBuilder ?? _defaultEmpty)(context);
      case SurfacePhase.partial:
        return SurfaceStateView(
          state: effective,
          contentBelow: partialContent?.call(context),
          onRetry: onRetry,
          onRefresh: onRefresh,
          onBack: onBack,
        );
      case SurfacePhase.initial:
      case SurfacePhase.loading:
      case SurfacePhase.longRunning:
      case SurfacePhase.errorRecoverable:
      case SurfacePhase.errorTerminal:
      case SurfacePhase.offline:
      case SurfacePhase.reconnecting:
      case SurfacePhase.permissionDenied:
      case SurfacePhase.authExpired:
      case SurfacePhase.modelUnavailable:
      case SurfacePhase.toolUnavailable:
      case SurfacePhase.awaitingClarification:
      case SurfacePhase.proposalPending:
      case SurfacePhase.executing:
      case SurfacePhase.awaitingUser:
      case SurfacePhase.conflict:
      case SurfacePhase.unknownOutcome:
      case SurfacePhase.cancelled:
      case SurfacePhase.revoked:
        return SurfaceStateView(
          state: effective,
          onRetry: onRetry,
          onRefresh: onRefresh,
          onBack: onBack,
          onReauthenticate: onReauthenticate,
          onOpenSettings: onOpenSettings,
          onRespond: onRespond,
          onDismiss: onDismiss,
          onReport: onReport,
        );
    }
  }
}
