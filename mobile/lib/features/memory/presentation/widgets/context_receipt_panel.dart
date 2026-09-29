import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/pixel/pixel_state.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/memory/data/context_receipt_models.dart';
import 'package:sparkle/features/memory/data/memory_provenance_repository.dart';
import 'package:sparkle/features/memory/presentation/providers/context_receipt_provider.dart';
import 'package:sparkle/features/memory/presentation/widgets/why_this_receipt_sheet.dart';
import 'package:sparkle/l10n/app_localizations.dart';

/// V4-U03 · 「这次的理解」回执面板（I06 `context_selection_receipt.v1`
/// 读面的唯一呈现位）。
///
/// 呈现纪律（SCREEN_FAMILIES「记忆 / Aurora / 我的理解」+ B05 合同 §7.1）：
/// - 回执说什么就显示什么：选中/拒用/原因全部来自服务端权威记录，未归因的
///   显式「未归因」，来源不可定位的显式「来源已不可定位」，绝不把不可核对
///   的条目渲染成已理解内容；
/// - 空态/未开启/断网/版本不支持四态彼此分立、诚实呈现，空集绝不冒充
///   「有依据」，失败绝不渲染为绿色成功（memory 操作永不成功面孔——F03）；
/// - 校准动作只绑定 resolution=resolved 的 selected 记忆 ref（忘记=真实
///   revoke 链）；解释缺失或「这次能带上的内容有限」**不禁用**更改与忘记
///   （验收③）。
class ContextReceiptPanel extends ConsumerStatefulWidget {
  const ContextReceiptPanel({super.key});

  @override
  ConsumerState<ContextReceiptPanel> createState() => _ContextReceiptPanelState();
}

class _ContextReceiptPanelState extends ConsumerState<ContextReceiptPanel> {
  /// 忘记操作的进行中/结果面（本面板局部；真实后端结果，绝不本地编造）。
  final Set<String> _pendingForgets = <String>{};
  String? _lastForgottenRef;
  String? _forgetError;

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(contextReceiptProvider);
    final l10n = context.l10n;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          l10n.contextReceiptSectionTitle,
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                color: DS.textPrimary,
                fontWeight: DS.fontWeightBold,
              ),
        ),
        const SizedBox(height: DS.sm),
        _body(context, state),
      ],
    );
  }

  Widget _body(BuildContext context, ContextReceiptState state) {
    final l10n = context.l10n;
    switch (state.phase) {
      case ContextReceiptPhase.loading:
        return Padding(
          padding: const EdgeInsets.symmetric(vertical: DS.lg),
          child: Center(child: LoadingIndicator.circular(strokeWidth: 2)),
        );
      case ContextReceiptPhase.offline:
        // 断网诚实态：与空数据分立，绝不渲染成「这次没有回执」。
        return _honestStateCard(
          context,
          text: state.errorMessage == null
              ? l10n.contextReceiptOffline
              : l10n.contextReceiptOfflineDetail(state.errorMessage!),
          actionLabel: l10n.retry,
          onAction: () => ref.read(contextReceiptProvider.notifier).refresh(),
        );
      case ContextReceiptPhase.modeGated:
        return _honestStateCard(context, text: _modeGatedCopy(context, state.mode));
      case ContextReceiptPhase.empty:
        return _honestStateCard(context, text: l10n.contextReceiptEmpty);
      case ContextReceiptPhase.unsupported:
        return _honestStateCard(context, text: l10n.contextReceiptUnsupported);
      case ContextReceiptPhase.ready:
        return _readyBody(context, state.view!);
    }
  }

  String _modeGatedCopy(BuildContext context, String mode) {
    final l10n = context.l10n;
    switch (mode) {
      case 'off':
        return l10n.contextReceiptModeOff;
      case 'shadow':
        return l10n.contextReceiptModeShadow;
      default:
        // 词表外模式不猜语义：原样透传（诚实未知）。
        return l10n.contextReceiptModeOther(mode);
    }
  }

  Widget _readyBody(BuildContext context, ContextReceiptView view) {
    final l10n = context.l10n;
    final calibratable = view.calibratableMemories();
    final unresolvedSelected = view.selectedCount - view.resolvedSelectedCount;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          l10n.contextReceiptIntro(_roleLabel(context, view.selectionRole)),
          style: TextStyle(color: DS.textSecondary, fontSize: DS.fontSizeSm),
        ),
        if (view.whyNowStatement != null) ...[
          const SizedBox(height: DS.sm),
          Text(
            l10n.contextReceiptWhyNowTitle,
            style: TextStyle(
              color: DS.textPrimary,
              fontSize: DS.fontSizeSm,
              fontWeight: DS.fontWeightSemibold,
            ),
          ),
          const SizedBox(height: DS.xs),
          Text(
            '${view.whyNowStatement}'
            '${view.whyNowBand == null ? '' : '（${_bandLabel(context, view.whyNowBand!)}）'}',
            style: TextStyle(color: DS.textSecondary, fontSize: DS.fontSizeSm),
          ),
        ],
        const SizedBox(height: DS.sm),
        if (view.candidatesUnknown)
          // 旧生产者：候选明细未知——显式「暂缺」，不当空集渲染为
          // 「这次没有引用」（unknown ≠ 空，合同读侧语义）。
          Text(
            l10n.contextReceiptCandidatesUnknown,
            style: TextStyle(color: DS.textSecondary, fontSize: DS.fontSizeSm),
          )
        else if (view.selectedCount == 0)
          Text(
            l10n.contextReceiptSelectedNone,
            style: TextStyle(color: DS.textSecondary, fontSize: DS.fontSizeSm),
          )
        else ...[
          Text(
            l10n.contextReceiptSelectedTitle(view.resolvedSelectedCount, view.selectedCount),
            style: TextStyle(
              color: DS.textPrimary,
              fontSize: DS.fontSizeSm,
              fontWeight: DS.fontWeightSemibold,
            ),
          ),
          if (unresolvedSelected > 0)
            Padding(
              padding: const EdgeInsets.only(top: DS.xs),
              child: Text(
                l10n.contextReceiptUnattributedSelected(unresolvedSelected),
                style: TextStyle(color: DS.textSecondary, fontSize: DS.fontSizeSm),
              ),
            ),
          // 可校准行：只绑定 resolved 的 selected 记忆（来源已核对才可操作）。
          for (final memory in calibratable)
            _CalibratableMemoryRow(
              key: ValueKey('context-receipt-forget-${memory.ref}'),
              memory: memory,
              pending: _pendingForgets.contains(memory.ref),
              forgotten: _lastForgottenRef == memory.ref,
              onForget: () => _forget(context, memory),
            ),
        ],
        if (view.rejectedByReason.isNotEmpty || view.unknownReasonCount > 0) ...[
          const SizedBox(height: DS.sm),
          Text(
            l10n.contextReceiptRejectedTitle,
            style: TextStyle(
              color: DS.textPrimary,
              fontSize: DS.fontSizeSm,
              fontWeight: DS.fontWeightSemibold,
            ),
          ),
          const SizedBox(height: DS.xs),
          for (final entry in view.rejectedByReason.entries)
            Padding(
              padding: const EdgeInsets.only(bottom: DS.xs),
              child: Text(
                '· ${_reasonLabel(context, entry.key)}（${entry.value}）',
                style: TextStyle(color: DS.textSecondary, fontSize: DS.fontSizeSm),
              ),
            ),
          if (view.unknownReasonCount > 0)
            Padding(
              padding: const EdgeInsets.only(bottom: DS.xs),
              child: Text(
                // 未归因显式呈现——不猜标签、不静默丢弃。
                l10n.contextReceiptReasonUnknownCount(view.unknownReasonCount),
                style: TextStyle(color: DS.textSecondary, fontSize: DS.fontSizeSm),
              ),
            ),
        ],
        if (view.budgetLimited)
          Padding(
            padding: const EdgeInsets.only(top: DS.xs),
            child: Text(
              // 验收③：预算面只作如实说明，绝不禁用更改/忘记。
              l10n.contextReceiptBudgetNote,
              style: TextStyle(color: DS.textSecondary, fontSize: DS.fontSizeSm),
            ),
          ),
        if (_forgetError != null)
          Padding(
            padding: const EdgeInsets.only(top: DS.sm),
            child: Text(
              _forgetError!,
              style: TextStyle(color: DS.error, fontSize: DS.fontSizeSm),
            ),
          ),
      ],
    );
  }

  String _roleLabel(BuildContext context, String role) {
    final l10n = context.l10n;
    return switch (role) {
      'chat_context' => l10n.contextReceiptRoleChatContext,
      'proposal_basis' => l10n.contextReceiptRoleProposalBasis,
      'resume_view' => l10n.contextReceiptRoleResumeView,
      'intervention_targeting' => l10n.contextReceiptRoleIntervention,
      _ => l10n.contextReceiptRoleUnknown,
    };
  }

  String _bandLabel(BuildContext context, String band) {
    final l10n = context.l10n;
    return switch (band) {
      'high' => l10n.contextReceiptWhyNowBandHigh,
      'medium' => l10n.contextReceiptWhyNowBandMedium,
      'low' => l10n.contextReceiptWhyNowBandLow,
      _ => l10n.contextReceiptWhyNowBandUnknown,
    };
  }

  String _reasonLabel(BuildContext context, String code) {
    final l10n = context.l10n;
    return switch (code) {
      'out_of_scope_memory' => l10n.contextReceiptReasonOutOfScope,
      'stale_epoch' => l10n.contextReceiptReasonStale,
      'utility_gate_rejected' => l10n.contextReceiptReasonLowUtility,
      'conflicts_confirmed_preference' => l10n.contextReceiptReasonConflicts,
      'permission_denied' => l10n.contextReceiptReasonPermission,
      'budget_exhausted' => l10n.contextReceiptReasonBudget,
      'duplicate' => l10n.contextReceiptReasonDuplicate,
      'expired' => l10n.contextReceiptReasonExpired,
      _ => l10n.contextReceiptReasonUnknownCount(1),
    };
  }

  Widget _honestStateCard(
    BuildContext context, {
    required String text,
    String? actionLabel,
    VoidCallback? onAction,
  }) =>
      GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        padding: const EdgeInsets.all(DS.spacing12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              text,
              style: TextStyle(color: DS.textSecondary, fontSize: DS.fontSizeSm),
            ),
            if (actionLabel != null && onAction != null) ...[
              const SizedBox(height: DS.sm),
              SparkleButton.ghost(label: actionLabel, onPressed: onAction),
            ],
          ],
        ),
      );

  /// 忘记（真实变更链：POST /memory/provenance/items/{kind}/{id}/revoke）。
  ///
  /// 反馈纪律（F03）：memory 无 committed 呈现事件——成功只有中性文案确认，
  /// 永不成功徽章/成功声触；失败如实文字（无 detail 用通用失败文案）。
  Future<void> _forget(BuildContext context, CalibratableMemory memory) async {
    final l10n = context.l10n;
    final confirmed = await showUnderstandingConfirmDialog(
      context,
      title: l10n.understandingDeleteTitle,
      body: l10n.understandingDeleteBody,
      confirmLabel: l10n.understandingActionDelete,
      destructive: true,
    );
    if (confirmed == null || !mounted) {
      return;
    }
    setState(() {
      _pendingForgets.add(memory.ref);
      _forgetError = null;
      _lastForgottenRef = null;
    });
    try {
      final result = await ref.read(memoryProvenanceRepositoryProvider).revokeItem(
            memory.kind,
            memory.id,
            reason: 'user_revoked',
          );
      if (!mounted) {
        return;
      }
      // 后端诚实契约：只有真正进入撤销终态才报 revoked=true。
      if (result['revoked'] != true) {
        throw StateError(result['status']?.toString() ?? 'revoke failed');
      }
      setState(() {
        _pendingForgets.remove(memory.ref);
        _lastForgottenRef = memory.ref;
      });
    } catch (e) {
      if (!mounted) {
        return;
      }
      setState(() {
        _pendingForgets.remove(memory.ref);
        // 如实失败面：有 detail 用 detail，无 detail 用错误本义，均包在
        // 「没有成功：…」用户语言里（绝不渲染为成功/中性误报）。
        _forgetError = context.l10n
            .understandingToastFailedDetail(provenanceErrorDetail(e) ?? '$e');
      });
    }
  }
}

/// 单条可校准记忆行：类型 + 来源已核对 + [忘记]（键盘可达、语义命名）。
class _CalibratableMemoryRow extends StatelessWidget {
  const _CalibratableMemoryRow({
    required this.memory,
    required this.pending,
    required this.forgotten,
    required this.onForget,
    super.key,
  });

  final CalibratableMemory memory;
  final bool pending;
  final bool forgotten;
  final VoidCallback onForget;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Padding(
      padding: const EdgeInsets.only(top: DS.xs),
      child: Row(
        children: [
          Expanded(
            child: Text(
              '${_kindLabel(l10n)} · ${l10n.contextReceiptSourceResolved}',
              style: TextStyle(color: DS.textSecondary, fontSize: DS.fontSizeSm),
            ),
          ),
          if (forgotten)
            Text(
              l10n.contextReceiptForgotten,
              style: TextStyle(color: DS.textSecondary, fontSize: DS.fontSizeSm),
            )
          else
            SparkleButton(
              label: l10n.understandingActionDelete,
              variant: ButtonVariant.ghost,
              disabled: pending,
              onPressed: pending ? () {} : onForget,
            ),
        ],
      ),
    );
  }

  String _kindLabel(AppLocalizations l10n) => switch (memory.kind) {
        'episodic' => l10n.contextReceiptKindEpisodic,
        'preference' => l10n.contextReceiptKindPreference,
        'goal' => l10n.contextReceiptKindGoal,
        _ => l10n.contextReceiptKindOther(memory.kind),
      };
}

/// scope 校准冲突内联面（V3 四组视图 + 本面板共用语义）：
/// conflict 徽章（F02 状态族，非成功视觉）+ 如实文案 + 重新核对动作。
class ScopeConflictBanner extends StatelessWidget {
  const ScopeConflictBanner({required this.onRetry, super.key});

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Padding(
      padding: const EdgeInsets.only(top: DS.xs),
      child: Row(
        children: [
          const PixelStateBadge(state: PixelRunState.conflict, dense: true),
          const SizedBox(width: DS.sm),
          Expanded(
            child: Text(
              l10n.contextScopeConflictCopy,
              style: TextStyle(color: DS.textSecondary, fontSize: DS.fontSizeSm),
            ),
          ),
          SparkleButton.ghost(
            label: l10n.contextConflictRefresh,
            onPressed: onRetry,
          ),
        ],
      ),
    );
  }
}
