import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/components/atoms/semantic_pill.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/widgets/action_proposal/proposal_card_models.dart';

export 'proposal_card_models.dart'
    show
        ActionProposalCardData,
        ProposalActionGuard,
        ProposalCardStatus,
        ProposalDiffEntry,
        ProposalTurnOwnership,
        proposalActionIdempotencyKey,
        proposalOwnershipFromWire,
        proposalStatusFromWire;

/// U-04 · 统一 Action Proposal 卡片（chat / task 单一组件双挂载）.
///
/// 职责（V3-4 / GJ06 / GJ07）：
/// 1. **turn ownership**：非技术化显示"你做 / Sparkle做 / 一起做"+ 当前轮到谁，
///    用户无需读日志即知道该自己出手还是等 Sparkle；
/// 2. **propose before mutate**：有 diff 时展示"会改动什么"（现在 → 改成）；
/// 3. **状态诚实**：awaiting user / running / partial / unknown / committed /
///    cancelled / expired / rejected / conflict 全覆盖；unknown **不显示成功**
///    （X-08 P2：委托路径可能不发完成事件——呈现"结果待确认"）；
/// 4. **幂等 UI 面**：确认/拒绝/取消经 [ProposalActionGuard] 防抖（在途重入
///    复用同一 Future，双击不双发），并以稳定幂等键透传给回调，由调用方放入
///    command path（服务端幂等真源在 X-09，此处不重建）。
///
/// 组件为纯展示：所有网络行为经回调注入，不持有 provider/仓库依赖，
/// 因此 chat（widget payload）与 task（proposal inbox provider）可以
/// 挂载同一组件并保证行为一致。
class ActionProposalCard extends StatefulWidget {
  const ActionProposalCard({
    required this.data,
    required this.onApprove,
    required this.onReject,
    super.key,
    this.onCancel,
    this.onReview,
    this.onRefresh,
    this.compact = false,
    this.guard,
  });

  final ActionProposalCardData data;

  /// 确认执行（awaitingUser 态主操作）。回调收到稳定幂等键，调用方应将其
  /// 透传给 `POST /action-proposals/{id}/approve` 的 idempotency_key。
  final Future<void> Function(String idempotencyKey) onApprove;

  /// 拒绝（awaitingUser 态次操作）。
  final Future<void> Function(String idempotencyKey) onReject;

  /// 取消（running / awaitingUser 态可选操作；terminal_reason=user_cancelled）。
  final Future<void> Function(String idempotencyKey)? onCancel;

  /// conflict 态的"再看一遍"（调用方决定如何重取最新内容）。
  final VoidCallback? onReview;

  /// unknown 态的"刷新结果"（调用方决定如何重查权威回执）。
  final VoidCallback? onRefresh;

  /// task 页嵌入列表时可用紧凑形态。
  final bool compact;

  /// 外部注入的防抖守卫（同卡多实例共享时可传入；缺省实例内部自建）。
  final ProposalActionGuard? guard;

  @override
  State<ActionProposalCard> createState() => _ActionProposalCardState();
}

class _ActionProposalCardState extends State<ActionProposalCard> {
  late ProposalActionGuard _guard;
  ProposalCardStatus? _localStatus;
  String? _localNotice;

  @override
  void initState() {
    super.initState();
    _guard = widget.guard ?? ProposalActionGuard();
  }

  @override
  void didUpdateWidget(covariant ActionProposalCard oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.guard != widget.guard) {
      _guard = widget.guard ?? ProposalActionGuard();
    }
    if (oldWidget.data.proposalId != widget.data.proposalId ||
        oldWidget.data.status != widget.data.status) {
      // 数据真源更新（父层刷新）→ 清除本地临时态，跟随真源。
      _localStatus = null;
      _localNotice = null;
    }
  }

  ProposalCardStatus get _status => _localStatus ?? widget.data.status;

  bool get _busy => _guard.isBusy;

  Future<void> _runCommand(
    String action,
    Future<void> Function(String idempotencyKey)? callback,
  ) async {
    if (callback == null) return;
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
    // 立即反映在途态：按钮切换为"正在处理…"并禁用（防抖 UI 面）。
    if (mounted) setState(() {});
    try {
      // 防抖 + 幂等键透传：在途重入复用同一 Future（双击不双发）。
      await _guard.run(
        action,
        () => callback(widget.data.idempotencyKeyFor(action)),
      );
      if (!mounted) return;
      setState(() {
        switch (action) {
          case 'approve':
            // 乐观进入"结果待确认"：在权威回执回来之前不显示成功。
            _localStatus = ProposalCardStatus.unknown;
            _localNotice = null;
          case 'reject':
            _localStatus = ProposalCardStatus.rejected;
          case 'cancel':
            _localStatus = ProposalCardStatus.cancelled;
        }
      });
    } catch (_) {
      if (!mounted) return;
      // 失败不伪装成功：回到 awaitingUser，由调用方/上层负责错误反馈。
      setState(() {
        _localStatus = widget.data.status;
        _localNotice = null;
      });
    } finally {
      if (mounted) setState(() {});
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final data = widget.data;
    final status = _status;

    final ownershipLabel = switch (data.ownership) {
      ProposalTurnOwnership.human => l10n.proposalOwnershipHuman,
      ProposalTurnOwnership.agent => l10n.proposalOwnershipAgent,
      ProposalTurnOwnership.hybrid => l10n.proposalOwnershipHybrid,
    };
    final turnLine = switch (status) {
      ProposalCardStatus.awaitingUser ||
      ProposalCardStatus.conflict =>
        data.ownership == ProposalTurnOwnership.human
            ? l10n.proposalTurnYours
            : l10n.proposalTurnTogether,
      ProposalCardStatus.running => l10n.proposalTurnSparkle,
      _ => data.ownership == ProposalTurnOwnership.agent
          ? l10n.proposalTurnSparkle
          : l10n.proposalTurnYours,
    };
    final statusLabel = _statusLabel(l10n, status);
    final hint = _statusHint(l10n, status);

    final tone = _statusTone(status);
    final actions = _buildActions(context, status);

    return Semantics(
      container: true,
      label: l10n.proposalTurnA11y(ownershipLabel),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(DS.spacing16),
        decoration: BoxDecoration(
          color: context.colors.surfacePrimary,
          borderRadius: DS.borderRadius16,
          border: Border.all(color: _toneColor(tone).withValues(alpha: 0.28)),
          boxShadow: DS.shadowSm,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              children: [
                SemanticPill(
                  label: ownershipLabel,
                  tone: PillTone.brand,
                  icon: _ownershipIcon(data.ownership),
                  dense: widget.compact,
                ),
                const SizedBox(width: DS.spacing8),
                SemanticPill(
                  label: statusLabel,
                  tone: tone,
                  dense: widget.compact,
                ),
                const Spacer(),
                Semantics(
                  label: l10n.proposalTurnA11y(turnLine),
                  child: Text(
                    turnLine,
                    style: context.typo.labelSmall.copyWith(
                      color: context.colors.textSecondary,
                    ),
                  ),
                ),
              ],
            ),
            if (data.title != null || data.summary != null) ...[
              const SizedBox(height: DS.spacing8),
              Text(
                data.title ?? data.summary ?? '',
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: context.typo.titleSmall.copyWith(
                  color: context.colors.textPrimary,
                ),
              ),
            ],
            if (data.title != null && data.summary != null) ...[
              const SizedBox(height: DS.spacing4),
              Text(
                data.summary!,
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
                style: context.typo.bodySmall.copyWith(
                  color: context.colors.textSecondary,
                  height: 1.42,
                ),
              ),
            ],
            if (hint != null) ...[
              const SizedBox(height: DS.spacing8),
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(
                    _statusIcon(status),
                    size: DS.iconSizeSm,
                    color: _toneColor(tone),
                  ),
                  const SizedBox(width: DS.spacing6),
                  Expanded(
                    child: Text(
                      _localNotice ?? hint,
                      style: context.typo.bodySmall.copyWith(
                        color: _toneColor(tone),
                        height: 1.42,
                      ),
                    ),
                  ),
                ],
              ),
            ],
            if (data.diff.isNotEmpty && !_isTerminal(status)) ...[
              const SizedBox(height: DS.spacing10),
              _DiffSection(
                entries: data.diff,
                compact: widget.compact,
              ),
            ],
            if (status == ProposalCardStatus.committed &&
                data.receiptSummary != null) ...[
              const SizedBox(height: DS.spacing8),
              Text(
                data.receiptSummary!,
                style: context.typo.bodySmall.copyWith(
                  color: context.colors.textSecondary,
                ),
              ),
            ],
            if (actions.isNotEmpty) ...[
              const SizedBox(height: DS.spacing12),
              Row(
                children: [
                  for (var i = 0; i < actions.length; i++) ...[
                    if (i > 0) const SizedBox(width: DS.spacing8),
                    Expanded(child: actions[i]),
                  ],
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  List<Widget> _buildActions(BuildContext context, ProposalCardStatus status) {
    final l10n = context.l10n;
    final busy = _busy;
    switch (status) {
      case ProposalCardStatus.awaitingUser:
        return [
          SparkleButton(
            label: busy ? l10n.proposalConfirming : l10n.proposalActionApprove,
            onPressed:
                busy ? null : () => unawaited(_runCommand('approve', widget.onApprove)),
          ),
          SparkleButton(
            label: l10n.proposalActionReject,
            variant: ButtonVariant.ghost,
            onPressed:
                busy ? null : () => unawaited(_runCommand('reject', widget.onReject)),
          ),
          if (widget.onCancel != null)
            SparkleButton(
              label: l10n.proposalActionCancel,
              variant: ButtonVariant.ghost,
              onPressed: busy
                  ? null
                  : () => unawaited(_runCommand('cancel', widget.onCancel)),
            ),
        ];
      case ProposalCardStatus.running:
        return [
          if (widget.onCancel != null)
            SparkleButton(
              label: l10n.proposalActionCancel,
              variant: ButtonVariant.ghost,
              onPressed: busy
                  ? null
                  : () => unawaited(_runCommand('cancel', widget.onCancel)),
            ),
        ];
      case ProposalCardStatus.unknown:
        return [
          if (widget.onRefresh != null)
            SparkleButton(
              label: l10n.proposalActionRefresh,
              variant: ButtonVariant.outline,
              onPressed: widget.onRefresh,
            ),
        ];
      case ProposalCardStatus.conflict:
        return [
          if (widget.onReview != null)
            SparkleButton(
              label: l10n.proposalActionReview,
              variant: ButtonVariant.outline,
              onPressed: widget.onReview,
            ),
        ];
      case ProposalCardStatus.partial:
      case ProposalCardStatus.committed:
      case ProposalCardStatus.cancelled:
      case ProposalCardStatus.expired:
      case ProposalCardStatus.rejected:
        return const <Widget>[];
    }
  }

  bool _isTerminal(ProposalCardStatus status) =>
      status == ProposalCardStatus.committed ||
      status == ProposalCardStatus.cancelled ||
      status == ProposalCardStatus.expired ||
      status == ProposalCardStatus.rejected;

  String _statusLabel(AppLocalizations l10n, ProposalCardStatus status) =>
      switch (status) {
        ProposalCardStatus.awaitingUser => l10n.proposalStatusAwaitingUser,
        ProposalCardStatus.running => l10n.proposalStatusRunning,
        ProposalCardStatus.partial => l10n.proposalStatusPartial,
        ProposalCardStatus.unknown => l10n.proposalStatusUnknown,
        ProposalCardStatus.committed => l10n.proposalStatusCommitted,
        ProposalCardStatus.cancelled => l10n.proposalStatusCancelled,
        ProposalCardStatus.expired => l10n.proposalStatusExpired,
        ProposalCardStatus.rejected => l10n.proposalStatusRejected,
        ProposalCardStatus.conflict => l10n.proposalStatusConflict,
      };

  String? _statusHint(AppLocalizations l10n, ProposalCardStatus status) =>
      switch (status) {
        ProposalCardStatus.awaitingUser => l10n.proposalAwaitingUserHint,
        ProposalCardStatus.running => l10n.proposalRunningHint,
        ProposalCardStatus.partial => l10n.proposalPartialHint,
        ProposalCardStatus.unknown => l10n.proposalUnknownHint,
        ProposalCardStatus.committed => l10n.proposalCommittedHint,
        ProposalCardStatus.cancelled => l10n.proposalCancelledHint,
        ProposalCardStatus.expired => l10n.proposalExpiredHint,
        ProposalCardStatus.rejected => l10n.proposalRejectedHint,
        ProposalCardStatus.conflict => l10n.proposalConflictHint,
      };

  PillTone _statusTone(ProposalCardStatus status) => switch (status) {
        ProposalCardStatus.awaitingUser => PillTone.brand,
        ProposalCardStatus.running => PillTone.info,
        ProposalCardStatus.partial => PillTone.warning,
        // unknown 是中性等待，不是成功——刻意不用 success 色。
        ProposalCardStatus.unknown => PillTone.info,
        ProposalCardStatus.committed => PillTone.success,
        ProposalCardStatus.cancelled => PillTone.neutral,
        ProposalCardStatus.expired => PillTone.neutral,
        ProposalCardStatus.rejected => PillTone.neutral,
        ProposalCardStatus.conflict => PillTone.warning,
      };

  IconData _statusIcon(ProposalCardStatus status) => switch (status) {
        ProposalCardStatus.awaitingUser => Icons.how_to_reg_outlined,
        ProposalCardStatus.running => Icons.autorenew_rounded,
        ProposalCardStatus.partial => Icons.pending_actions_rounded,
        ProposalCardStatus.unknown => Icons.help_outline_rounded,
        ProposalCardStatus.committed => Icons.check_circle_outline_rounded,
        ProposalCardStatus.cancelled => Icons.block_rounded,
        ProposalCardStatus.expired => Icons.schedule_outlined,
        ProposalCardStatus.rejected => Icons.do_not_disturb_outlined,
        ProposalCardStatus.conflict => Icons.sync_problem_outlined,
      };

  IconData _ownershipIcon(ProposalTurnOwnership ownership) =>
      switch (ownership) {
        ProposalTurnOwnership.human => Icons.person_outline_rounded,
        ProposalTurnOwnership.agent => Icons.smart_toy_outlined,
        ProposalTurnOwnership.hybrid => Icons.group_outlined,
      };

  Color _toneColor(PillTone tone) => switch (tone) {
        PillTone.info => DS.info,
        PillTone.success => DS.success,
        PillTone.warning => DS.warning,
        PillTone.danger => DS.error,
        PillTone.neutral => DS.neutral600,
        PillTone.brand => DS.brandPrimary,
      };
}

/// diff 区块：「会改动什么」——现在 → 改成.
class _DiffSection extends StatelessWidget {
  const _DiffSection({required this.entries, required this.compact});

  final List<ProposalDiffEntry> entries;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing12),
      decoration: BoxDecoration(
        color: context.colors.surfaceSecondary,
        borderRadius: DS.borderRadius12,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            l10n.proposalDiffTitle,
            style: context.typo.labelSmall.copyWith(
              color: context.colors.textSecondary,
            ),
          ),
          const SizedBox(height: DS.spacing8),
          for (final entry in entries.take(compact ? 2 : 4))
            Padding(
              padding: const EdgeInsets.only(bottom: DS.spacing6),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (entry.field.isNotEmpty) ...[
                    Text(
                      entry.field,
                      style: context.typo.labelSmall.copyWith(
                        color: context.colors.textSecondary,
                      ),
                    ),
                    const SizedBox(width: DS.spacing8),
                  ],
                  Expanded(
                    child: Text.rich(
                      TextSpan(
                        children: [
                          if (entry.before != null) ...[
                            TextSpan(
                              text: '${l10n.proposalDiffBefore} ',
                              style: context.typo.bodySmall.copyWith(
                                color: context.colors.neutral500,
                              ),
                            ),
                            TextSpan(
                              text: entry.before,
                              style: context.typo.bodySmall.copyWith(
                                color: context.colors.neutral500,
                                decoration: TextDecoration.lineThrough,
                              ),
                            ),
                            const TextSpan(text: '  '),
                          ],
                          if (entry.after != null) ...[
                            TextSpan(
                              text: '${l10n.proposalDiffAfter} ',
                              style: context.typo.bodySmall.copyWith(
                                color: context.colors.textSecondary,
                              ),
                            ),
                            TextSpan(
                              text: entry.after,
                              style: context.typo.bodySmall.copyWith(
                                color: context.colors.textPrimary,
                                fontWeight: DS.fontWeightSemibold,
                              ),
                            ),
                          ],
                        ],
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            ),
          if (entries.length > (compact ? 2 : 4))
            Text(
              '+${entries.length - (compact ? 2 : 4)}',
              style: context.typo.labelSmall.copyWith(
                color: context.colors.neutral500,
              ),
            ),
        ],
      ),
    );
  }
}
