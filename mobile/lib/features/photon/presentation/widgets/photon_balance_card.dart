import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/photon/presentation/providers/photon_provider.dart';

/// Photon Balance Card Widget
/// 光子余额卡片组件
class PhotonBalanceCard extends ConsumerWidget {
  const PhotonBalanceCard({
    Key? key,
    this.onTap,
    this.showRefreshButton = true,
  }) : super(key: key);

  final VoidCallback? onTap;
  final bool showRefreshButton;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final balanceState = ref.watch(photonBalanceProvider);

    return GestureDetector(
      onTap: onTap ??
          () {
            // Navigate to transaction history
            Navigator.of(context).push(
              MaterialPageRoute<void>(
                builder: (context) => const TransactionHistoryScreen(),
              ),
            );
          },
      child: Container(
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
              color: Theme.of(context).colorScheme.primary.withValues(alpha: 0.3),
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
                  color: Colors.white.withValues(alpha: 0.2),
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  Icons.flash_on_rounded,
                  color: Colors.white,
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
                      '光子积分',
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.9),
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    const SizedBox(height: 4),
                    if (balanceState.isLoading)
                      const SizedBox(
                        height: 28,
                        width: 100,
                        child: LinearProgressIndicator(
                          color: Colors.white,
                          backgroundColor: Colors.white24,
                        ),
                      )
                    else if (balanceState.error != null)
                      Text(
                        '加载失败',
                        style: TextStyle(
                          color: Colors.white.withValues(alpha: 0.7),
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                        ),
                      )
                    else
                      Text(
                        '${balanceState.balance?.balance ?? 0}',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 28,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                  ],
                ),
              ),

              // Refresh Button
              if (showRefreshButton)
                IconButton(
                  onPressed: () {
                    ref.read(photonBalanceProvider.notifier).refreshBalance();
                  },
                  icon: Icon(
                    Icons.refresh_rounded,
                    color: Colors.white.withValues(alpha: 0.9),
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
  const TransactionHistoryScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('交易历史'),
      ),
      body: const Center(
        child: Text('Transaction History - To be implemented'),
      ),
    );
  }
}
