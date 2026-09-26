import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:sparkle/core/display/lexicon/date_formatting.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/photon/presentation/providers/photon_provider.dart';
import 'package:sparkle/shared/entities/photon_model.dart';

/// Transaction History List Widget
class TransactionHistoryList extends ConsumerStatefulWidget {
  const TransactionHistoryList({super.key});

  @override
  ConsumerState<TransactionHistoryList> createState() =>
      _TransactionHistoryListState();
}

class _TransactionHistoryListState
    extends ConsumerState<TransactionHistoryList> {
  final ScrollController _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
  }

  @override
  void dispose() {
    _scrollController
      ..removeListener(_onScroll)
      ..dispose();
    super.dispose();
  }

  void _onScroll() {
    if (_scrollController.position.pixels >=
        _scrollController.position.maxScrollExtent * 0.8) {
      unawaited(
        ref.read(photonTransactionsProvider.notifier).loadTransactions(),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(photonTransactionsProvider);

    // 首载：骨架贴布局（PHOTON 卡 #7，A-SPEC2 PH-G5——裸 spinner 出局）。
    if (state.transactions.isEmpty && state.isLoading) {
      return const SingleChildScrollView(
        child: SparkleListSkeleton(),
      );
    }

    // 失败：人话三句式 + 重试（N9——异常细节不进 UI，provider 只给有界终态）。
    if (state.transactions.isEmpty && state.loadFailed) {
      return Center(
        child: CustomErrorWidget(
          key: const ValueKey('photon-transactions-error'),
          type: ErrorType.page,
          message: context.l10n.photonTransactionsLoadFailed,
          onRetry: () {
            unawaited(
              ref.read(photonTransactionsProvider.notifier).refresh(),
            );
          },
        ),
      );
    }

    if (state.transactions.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.receipt_long_outlined,
              size: 64,
              color: DS.textSecondary,
            ),
            const SizedBox(height: DS.lg),
            Text(
              context.l10n.photonTransactionsEmpty,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: DS.textSecondary,
                  ),
            ),
          ],
        ),
      );
    }

    return SparkleRefreshIndicator(
      onRefresh: () async {
        unawaited(ref.read(photonTransactionsProvider.notifier).refresh());
      },
      child: ListView.builder(
        controller: _scrollController,
        padding: const EdgeInsets.all(DS.lg),
        itemCount: state.transactions.length +
            (state.isLoading ? 1 : 0) +
            (state.hasMore ? 0 : 1),
        itemBuilder: (context, index) {
          // 分页尾：下一页的行骨架（贴布局，非 spinner）。
          if (index == state.transactions.length && state.isLoading) {
            return const Padding(
              padding: EdgeInsets.symmetric(vertical: DS.lg),
              child: SparkleCardSkeleton(),
            );
          }

          // End of list indicator
          if (index == state.transactions.length && !state.hasMore) {
            return Padding(
              padding: const EdgeInsets.all(DS.lg),
              child: Center(
                child: Text(
                  context.l10n.photonTransactionsEnd,
                  style: TextStyle(
                    color: DS.textSecondary,
                    fontSize: 14,
                  ),
                ),
              ),
            );
          }

          final transaction = state.transactions[index];
          final previousTransaction =
              index > 0 ? state.transactions[index - 1] : null;

          // Check if we should show date header
          final showDateHeader = previousTransaction == null ||
              !_isSameDay(
                transaction.createdAt,
                previousTransaction.createdAt,
              );

          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (showDateHeader)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  child: Text(
                    _formatDateHeader(context, transaction.createdAt),
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          color: DS.textSecondary,
                          fontWeight: DS.fontWeightSemibold,
                        ),
                  ),
                ),
              _TransactionItem(transaction: transaction),
              const SizedBox(height: 8),
            ],
          );
        },
      ),
    );
  }

  bool _isSameDay(DateTime date1, DateTime date2) =>
      date1.year == date2.year &&
      date1.month == date2.month &&
      date1.day == date2.day;

  // 日期分组头走唯一入口（X3/PH-G6：禁自算相对日与手拼 DateFormat）。
  String _formatDateHeader(BuildContext context, DateTime date) =>
      formatSparkleDayHeader(date, context.l10n);
}

class _TransactionItem extends StatelessWidget {
  const _TransactionItem({
    required this.transaction,
  });

  final PhotonTransaction transaction;

  @override
  Widget build(BuildContext context) {
    final isIncome = transaction.isIncome;

    return DecoratedBox(
      decoration: BoxDecoration(
        color: DS.surfacePrimary,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: DS.neutral200,
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(DS.lg),
        child: Row(
          children: [
            // Icon
            Container(
              width: 48,
              height: 48,
              decoration: BoxDecoration(
                color: isIncome
                    ? DS.success.withValues(alpha: 0.1)
                    : DS.warning.withValues(alpha: 0.1),
                shape: BoxShape.circle,
              ),
              child: Icon(
                _getTransactionIcon(transaction.transactionType),
                color: isIncome ? DS.success : DS.warning,
                size: 24,
              ),
            ),
            const SizedBox(width: 16),

            // Info
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    transaction.transactionTypeName,
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          fontWeight: DS.fontWeightSemibold,
                        ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    transaction.source ?? context.l10n.photonTransactionNoNote,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: DS.textSecondary,
                        ),
                  ),
                ],
              ),
            ),

            // Amount
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  '${isIncome ? '+' : '-'}${transaction.amount.abs()}',
                  style: TextStyle(
                    color: isIncome ? DS.success : DS.warning,
                    fontSize: 18,
                    fontWeight: DS.fontWeightBold,
                    fontFeatures: const [FontFeature.tabularFigures()],
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  formatSparkleClock(transaction.createdAt),
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: DS.textSecondary,
                        fontFeatures: const [FontFeature.tabularFigures()],
                      ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  IconData _getTransactionIcon(PhotonTransactionType type) {
    switch (type) {
      case PhotonTransactionType.grantAchievement:
        return Icons.emoji_events_outlined;
      case PhotonTransactionType.grantDailyFirst:
        return Icons.star_outline;
      case PhotonTransactionType.grantContract:
      case PhotonTransactionType.grantContractBonus:
        return Icons.task_alt_outlined;
      // V3-FIX-271：补值族图标（grant_bonus/contract_escrow/guest_seed/unknown）。
      case PhotonTransactionType.grantBonus:
        return Icons.bolt_outlined;
      case PhotonTransactionType.contractEscrow:
        return Icons.lock_outline;
      case PhotonTransactionType.guestSeed:
        return Icons.card_giftcard;
      case PhotonTransactionType.unknown:
        return Icons.help_outline;
      case PhotonTransactionType.deductContractStake:
        return Icons.warning_outlined;
      case PhotonTransactionType.purchase:
        return Icons.shopping_cart_outlined;
      case PhotonTransactionType.transferOut:
        return Icons.arrow_upward_outlined;
      case PhotonTransactionType.transferIn:
        return Icons.arrow_downward_outlined;
      case PhotonTransactionType.refund:
        return Icons.currency_exchange_outlined;
      case PhotonTransactionType.penalty:
        return Icons.gavel_outlined;
      case PhotonTransactionType.adminAdjustment:
        return Icons.admin_panel_settings_outlined;
      case PhotonTransactionType.redeemPro:
        return Icons.redeem_rounded;
    }
  }
}
