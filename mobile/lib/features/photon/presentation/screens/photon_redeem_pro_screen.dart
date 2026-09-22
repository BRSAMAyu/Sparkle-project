import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/photon/data/models/photon_redeem_pro_model.dart';
import 'package:sparkle/features/photon/presentation/providers/photon_redeem_pro_provider.dart';

/// D-COMM-2：光子兑 Pro（「学出会员」有界兑换出口，`POST /photons/redeem-pro`）。
///
/// SPEC v1.0：必达项 2——① 光子资产卡（余额 + 可兑换基数两数分开，基数只由
/// 服务端响应揭示，不本地推算）；② 兑换动作卡（成本/时长/月顶三要素 + 确认
/// 对话框 + 有界终态反馈）。唯一交互 accent（brandPrimary，主按钮）；状态区分
/// 只用文字层级不作第二色。
///
/// 价值增量语气：这是学习奖励的出口——文案不含任何「购买/解锁」暗示。
class PhotonRedeemProScreen extends ConsumerStatefulWidget {
  const PhotonRedeemProScreen({super.key});

  @override
  ConsumerState<PhotonRedeemProScreen> createState() =>
      _PhotonRedeemProScreenState();
}

class _PhotonRedeemProScreenState extends ConsumerState<PhotonRedeemProScreen> {
  /// 最近一次兑换的服务端终态（基数/成本/时长以它为准；未动作前为 null）。
  PhotonRedeemProResult? _lastResult;
  bool _redeeming = false;

  Future<void> _redeem() async {
    final l10n = context.l10n;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => _RedeemConfirmDialog(
        cost: _lastResult?.costPhotons ?? photonRedeemProDisplayCost,
        days: _lastResult?.proDays ?? photonRedeemProDisplayDays,
      ),
    );
    if (confirmed != true || !mounted) {
      return;
    }
    setState(() => _redeeming = true);
    final result = await ref.read(photonRedeemProRepositoryProvider).redeem();
    if (!mounted) {
      return;
    }
    // 兑换响应后刷新快照（PHOTON-STATUS）：余额/基数/月顶回归服务端真值；
    // _lastResult 仍持本次终态做即时反馈，刷新到达后两源收敛一致。
    unawaited(ref.refresh(photonRedeemProOverviewProvider.future));
    setState(() {
      _redeeming = false;
      _lastResult = result;
    });
    switch (result.status) {
      case PhotonRedeemProStatus.ok:
        final expiresAt = result.entitlementExpiresAt;
        final dateLabel = expiresAt == null
            ? '--'
            : MaterialLocalizations.of(context).formatShortDate(expiresAt);
        AppFeedback.success(
          context,
          l10n.photonRedeemProSuccessToast(dateLabel),
        );
      case PhotonRedeemProStatus.insufficientBase:
        AppFeedback.error(context, l10n.photonRedeemProInsufficientBase);
      case PhotonRedeemProStatus.monthlyCapReached:
        AppFeedback.info(context, l10n.photonRedeemProCapUsed);
      case PhotonRedeemProStatus.insufficientBalance:
        AppFeedback.error(context, l10n.photonRedeemProInsufficientBalance);
      case PhotonRedeemProStatus.error:
        AppFeedback.error(context, l10n.photonRedeemProErrorToast);
    }
  }

  @override
  Widget build(BuildContext context) {
    final overviewAsync = ref.watch(photonRedeemProOverviewProvider);
    final colors = context.colors;
    final typo = context.typo;

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.of(context).maybePop(),
        ),
        title: Text(context.l10n.photonRedeemProTitle),
      ),
      child: ContentConstraint(
        child: SparkleRefreshIndicator(
          onRefresh: () =>
              ref.refresh(photonRedeemProOverviewProvider.future),
          child: overviewAsync.when(
            loading: () =>
                const _ScrollableStateFill(child: SparkleCardSkeleton()),
            error: (Object error, StackTrace stackTrace) => _ScrollableStateFill(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Padding(
                    padding: EdgeInsets.symmetric(horizontal: context.space.md),
                    child: CustomErrorWidget(
                      message:
                          context.l10n.photonRedeemProLoadFailed(error),
                    ),
                  ),
                  SizedBox(height: context.space.md),
                  SparkleButton(
                    key: const ValueKey('photon-redeem-pro-retry-button'),
                    variant: ButtonVariant.outline,
                    label: context.l10n.photonRedeemProRetry,
                    onPressed: () =>
                        ref.invalidate(photonRedeemProOverviewProvider),
                  ),
                ],
              ),
            ),
            data: (PhotonRedeemProOverview overview) {
              // 服务端真数优先：status 快照（PHOTON-STATUS）→ 兑换响应揭示值 →
              // 展示常量只作最后兜底。
              final balance = _lastResult?.balanceAfter ?? overview.balance;
              final cost = _lastResult?.costPhotons ??
                  overview.costPhotons ??
                  photonRedeemProDisplayCost;
              final days =
                  _lastResult?.proDays ?? overview.proDays ?? photonRedeemProDisplayDays;
              // 基数真源：status 快照先行（动作前即有真数），兑换响应揭示值兜底。
              final revealedBase = overview.redeemableBase ?? _lastResult?.redeemableBase;
              final capped = overview.redeemedThisMonth ||
                  _lastResult?.status == PhotonRedeemProStatus.monthlyCapReached ||
                  _lastResult?.status == PhotonRedeemProStatus.ok;
              // 不足预判与引擎拒绝顺序同序（基数 → 余额）：动作前即诚实呈现，
              // 不再等兑换失败后才揭示。
              final insufficientBase = _lastResult?.status ==
                      PhotonRedeemProStatus.insufficientBase ||
                  (revealedBase != null && revealedBase < cost);
              final insufficientBalance = balance < cost;
              final canRedeem =
                  !_redeeming && !capped && !insufficientBase && !insufficientBalance;

              return ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: EdgeInsets.all(context.space.md),
                children: [
                  _PhotonAssetCard(
                    balance: balance,
                    revealedBase: revealedBase,
                  ),
                  SizedBox(height: context.space.md),
                  _RedeemActionCard(
                    cost: cost,
                    days: days,
                    capped: capped,
                    canRedeem: canRedeem,
                    insufficientBalance: insufficientBalance,
                    insufficientBase: insufficientBase,
                    balance: balance,
                    revealedBase: revealedBase,
                    redeeming: _redeeming,
                    onRedeem: () => unawaited(_redeem()),
                  ),
                  SizedBox(height: context.space.md),
                  Text(
                    context.l10n.photonRedeemProSubtitle,
                    style:
                        typo.labelSmall.copyWith(color: colors.textTertiary),
                    textAlign: TextAlign.center,
                  ),
                ],
              );
            },
          ),
        ),
      ),
    );
  }
}

/// 必达项 ①：光子资产卡——余额与可兑换基数两数分开，诚实区分口径。
class _PhotonAssetCard extends StatelessWidget {
  const _PhotonAssetCard({
    required this.balance,
    required this.revealedBase,
  });

  final int balance;

  /// 服务端已揭示的可兑换基数（null = 尚未由服务端核算，不展示数字）。
  final int? revealedBase;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final typo = context.typo;
    final l10n = context.l10n;
    final base = revealedBase;

    return GraphiteCardSurface(
      key: const ValueKey('photon-redeem-pro-asset-card'),
      surfaceRole: SparkleSurfaceRole.card,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            l10n.photonRedeemProBalanceLabel,
            style: typo.labelLarge.copyWith(color: colors.textSecondary),
          ),
          SizedBox(height: context.space.xs),
          Text(
            '$balance',
            key: const ValueKey('photon-redeem-pro-balance-value'),
            style: typo.displayLarge.copyWith(color: colors.textPrimary),
          ),
          SizedBox(height: context.space.md),
          Text(
            l10n.photonRedeemProBaseLabel,
            style: typo.labelLarge.copyWith(color: colors.textSecondary),
          ),
          SizedBox(height: context.space.xs),
          // 基数只由服务端揭示（响应带回），未揭示前不产出数字——诚实空态。
          if (base == null)
            Text(
              l10n.photonRedeemProBaseHint,
              key: const ValueKey('photon-redeem-pro-base-value'),
              style: typo.bodyMedium.copyWith(color: colors.textSecondary),
            )
          else
            Text(
              '$base',
              key: const ValueKey('photon-redeem-pro-base-value'),
              style: typo.displayLarge.copyWith(color: colors.textPrimary),
            ),
          SizedBox(height: context.space.xs),
          Text(
            l10n.photonRedeemProBaseNote,
            style: typo.labelSmall.copyWith(color: colors.textTertiary),
          ),
          // 诚实区分：基数 < 余额时，差额来自转账等不可兑换来源——如实注明。
          if (base != null && base < balance) ...[
            SizedBox(height: context.space.xs),
            Text(
              l10n.photonRedeemProTransferNote(balance - base),
              key: const ValueKey('photon-redeem-pro-transfer-note'),
              style: typo.labelSmall.copyWith(color: colors.textTertiary),
            ),
          ],
        ],
      ),
    );
  }
}

/// 必达项 ②：兑换动作卡——成本/时长/月顶三要素 + 确认对话框 + 有界终态。
class _RedeemActionCard extends StatelessWidget {
  const _RedeemActionCard({
    required this.cost,
    required this.days,
    required this.capped,
    required this.canRedeem,
    required this.insufficientBalance,
    required this.insufficientBase,
    required this.balance,
    required this.revealedBase,
    required this.redeeming,
    required this.onRedeem,
  });

  final int cost;
  final int days;
  final bool capped;
  final bool canRedeem;
  final bool insufficientBalance;
  final bool insufficientBase;
  final int balance;
  final int? revealedBase;
  final bool redeeming;
  final VoidCallback onRedeem;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final typo = context.typo;
    final l10n = context.l10n;

    String? stateNote;
    if (insufficientBase) {
      stateNote = l10n.photonRedeemProInsufficientBase;
    } else if (insufficientBalance) {
      stateNote = l10n.photonRedeemProInsufficientBalance;
    }

    return GraphiteCardSurface(
      key: const ValueKey('photon-redeem-pro-action-card'),
      surfaceRole: SparkleSurfaceRole.card,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _FactorRow(label: l10n.photonRedeemProCostLabel, value: '$cost'),
          SizedBox(height: context.space.sm),
          _FactorRow(
            label: l10n.photonRedeemProDurationLabel,
            value: l10n.photonRedeemProDays(days),
          ),
          SizedBox(height: context.space.sm),
          _FactorRow(
            label: l10n.photonRedeemProCapLabel,
            value: capped
                ? l10n.photonRedeemProCapUsed
                : l10n.photonRedeemProCapAvailable,
          ),
          SizedBox(height: context.space.md),
          SparkleButton(
            key: const ValueKey('photon-redeem-pro-action-button'),
            label: l10n.photonRedeemProAction,
            onPressed: canRedeem ? onRedeem : null,
            loading: redeeming,
            disabled: !canRedeem,
            expand: true,
          ),
          if (stateNote != null) ...[
            SizedBox(height: context.space.sm),
            Text(
              key: const ValueKey('photon-redeem-pro-state-note'),
              stateNote,
              style: typo.bodySmall.copyWith(color: colors.textSecondary),
            ),
          ],
        ],
      ),
    );
  }
}

/// 三要素行：label 左、value 右；唯一 accent 纪律——状态差异只走文字层级。
class _FactorRow extends StatelessWidget {
  const _FactorRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final typo = context.typo;
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: typo.bodyMedium.copyWith(color: colors.textSecondary),
        ),
        Text(
          value,
          style: typo.bodyMedium.copyWith(
            color: colors.textPrimary,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }
}

/// 不可逆动作确认面（照 ConfirmationDialog/购买确认先例：AlertDialog + ghost/primary）。
class _RedeemConfirmDialog extends StatelessWidget {
  const _RedeemConfirmDialog({required this.cost, required this.days});

  final int cost;
  final int days;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return AlertDialog(
      title: Text(l10n.photonRedeemProConfirmTitle),
      content: Text(l10n.photonRedeemProConfirmContent(cost, days)),
      actions: [
        SparkleButton(
          label: MaterialLocalizations.of(context).cancelButtonLabel,
          variant: ButtonVariant.ghost,
          onPressed: () => Navigator.of(context).pop(false),
        ),
        SparkleButton(
          key: const ValueKey('photon-redeem-pro-confirm-button'),
          label: l10n.photonRedeemProConfirmAction,
          onPressed: () => Navigator.of(context).pop(true),
        ),
      ],
    );
  }
}

class _ScrollableStateFill extends StatelessWidget {
  const _ScrollableStateFill({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
        builder: (context, constraints) => ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          children: [
            SizedBox(
              height: constraints.maxHeight,
              child: child,
            ),
          ],
        ),
      );
}
