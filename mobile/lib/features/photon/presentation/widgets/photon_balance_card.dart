import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/photon/photon_routes.dart';
import 'package:sparkle/features/photon/presentation/providers/photon_provider.dart';
import 'package:sparkle/features/photon/presentation/widgets/transaction_history_list.dart';

/// Photon Balance Card Widget
/// 光子余额卡片组件
class PhotonBalanceCard extends ConsumerWidget {
  const PhotonBalanceCard({
    super.key,
    this.onTap,
    this.showRefreshButton = true,
  });

  final VoidCallback? onTap;
  final bool showRefreshButton;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final balanceState = ref.watch(photonBalanceProvider);

    return GestureDetector(
      onTap: onTap ??
          () {
            context.push(PhotonRoutes.transactionHistory);
          },
      child: DecoratedBox(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [
              Theme.of(context).colorScheme.primary.withValues(alpha: 0.8),
              Theme.of(context).colorScheme.primary,
            ],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderRadius: BorderRadius.circular(16),
          boxShadow: [
            BoxShadow(
              color:
                  Theme.of(context).colorScheme.primary.withValues(alpha: 0.3),
              blurRadius: 12,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Row(
            children: [
              // Photon Icon
              Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(
                  color: DS.neutral0.withValues(alpha: 0.2),
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  Icons.flash_on_rounded,
                  color: DS.neutral0,
                  size: 32,
                ),
              ),
              const SizedBox(width: 16),

              // Balance Info
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      I18nService.instance.isChinese ? '光子积分' : 'Photon Balance',
                      style: TextStyle(
                        color: DS.neutral0.withValues(alpha: 0.9),
                        fontSize: 14,
                        fontWeight: DS.fontWeightMedium,
                      ),
                    ),
                    const SizedBox(height: 4),
                    if (balanceState.isLoading)
                      SizedBox(
                        height: 28,
                        width: 100,
                        child: LinearProgressIndicator(
                          color: DS.neutral0,
                          backgroundColor: DS.neutral0.withValues(alpha: 0.24),
                        ),
                      )
                    else if (balanceState.error != null)
                      Text(
                        I18nService.instance.isChinese ? '加载失败' : 'Load Failed',
                        style: TextStyle(
                          color: DS.neutral0.withValues(alpha: 0.7),
                          fontSize: 20,
                          fontWeight: DS.fontWeightBold,
                        ),
                      )
                    else
                      Text(
                        '${balanceState.balance?.balance ?? 0}',
                        style: TextStyle(
                          color: DS.neutral0,
                          fontSize: 28,
                          fontWeight: DS.fontWeightBold,
                          fontFeatures: const [FontFeature.tabularFigures()],
                        ),
                      ),
                  ],
                ),
              ),

              // Refresh Button
              if (showRefreshButton)
                SparkleIconButton(
                  variant: ButtonVariant.ghost,
                  size: 36,
                  onPressed: () {
                    ref.read(photonBalanceProvider.notifier).refreshBalance();
                  },
                  icon: Icon(
                    Icons.refresh_rounded,
                    color: DS.neutral0.withValues(alpha: 0.9),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

// Placeholder for transaction history screen
class TransactionHistoryScreen extends ConsumerWidget {
  const TransactionHistoryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) => Scaffold(
        appBar: AppBar(
          title: Text(I18nService.instance.isChinese ? '交易历史' : 'Transaction History'),
        ),
        body: const ContentConstraint(
          child: TransactionHistoryList(),
        ),
      );
}
