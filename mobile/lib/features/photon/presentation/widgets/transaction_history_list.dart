import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/features/photon/presentation/providers/photon_provider.dart';
import 'package:sparkle/shared/entities/photon_model.dart';

/// Transaction History List Widget
/// 交易历史列表组件
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
    _scrollController.removeListener(_onScroll);
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (_scrollController.position.pixels >=
        _scrollController.position.maxScrollExtent * 0.8) {
      ref.read(photonTransactionsProvider.notifier).loadTransactions();
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(photonTransactionsProvider);

    if (state.transactions.isEmpty && state.isLoading) {
      return const Center(
        child: CircularProgressIndicator(),
      );
    }

    if (state.transactions.isEmpty && state.error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.error_outline,
              size: 64,
              color: Colors.red,
            ),
            const SizedBox(height: 16),
            Text(
              state.error!,
              style: Theme.of(context).textTheme.bodyLarge,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: () {
                ref.read(photonTransactionsProvider.notifier).refresh();
              },
              child: const Text('重试'),
            ),
          ],
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
              color: Colors.grey[400],
            ),
            const SizedBox(height: 16),
            Text(
              '暂无交易记录',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: Colors.grey[600],
                  ),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () async {
        ref.read(photonTransactionsProvider.notifier).refresh();
      },
      child: ListView.builder(
        controller: _scrollController,
        padding: const EdgeInsets.all(16),
        itemCount: state.transactions.length +
            (state.isLoading ? 1 : 0) +
            (state.hasMore ? 0 : 1),
        itemBuilder: (context, index) {
          // Loading indicator at the bottom
          if (index == state.transactions.length) {
            return const Padding(
              padding: EdgeInsets.all(16),
              child: Center(
                child: CircularProgressIndicator(),
              ),
            );
          }

          // End of list indicator
          if (index == state.transactions.length + 1 && !state.hasMore) {
            return Padding(
              padding: const EdgeInsets.all(16),
              child: Center(
                child: Text(
                  '没有更多记录了',
                  style: TextStyle(
                    color: Colors.grey[600],
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
                    _formatDateHeader(transaction.createdAt),
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          color: Colors.grey[600],
                          fontWeight: FontWeight.w600,
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

  bool _isSameDay(DateTime date1, DateTime date2) => date1.year == date2.year &&
        date1.month == date2.month &&
        date1.day == date2.day;

  String _formatDateHeader(DateTime date) {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final transactionDate = DateTime(date.year, date.month, date.day);

    final difference = today.difference(transactionDate).inDays;

    if (difference == 0) {
      return '今天';
    } else if (difference == 1) {
      return '昨天';
    } else if (difference < 7) {
      return '$difference天前';
    } else {
      return DateFormat('yyyy年MM月dd日').format(date);
    }
  }
}

class _TransactionItem extends StatelessWidget {
  const _TransactionItem({
    super.key,
    required this.transaction,
  });

  final PhotonTransaction transaction;

  @override
  Widget build(BuildContext context) {
    final isIncome = transaction.isIncome;

    return DecoratedBox(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: Colors.grey[200]!,
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            // Icon
            Container(
              width: 48,
              height: 48,
              decoration: BoxDecoration(
                color: isIncome
                    ? Colors.green.withValues(alpha: 0.1)
                    : Colors.orange.withValues(alpha: 0.1),
                shape: BoxShape.circle,
              ),
              child: Icon(
                _getTransactionIcon(transaction.transactionType),
                color: isIncome ? Colors.green : Colors.orange,
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
                          fontWeight: FontWeight.w600,
                        ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    transaction.source ?? '无备注',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Colors.grey[600],
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
                    color: isIncome ? Colors.green : Colors.orange,
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  DateFormat('HH:mm').format(transaction.createdAt),
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Colors.grey[600],
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
    }
  }
}
