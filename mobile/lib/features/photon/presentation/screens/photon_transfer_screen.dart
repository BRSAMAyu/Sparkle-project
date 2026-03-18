import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/app_feedback.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/photon/presentation/providers/photon_provider.dart';

/// Photon Transfer Screen
/// 光子转账界面
class PhotonTransferScreen extends ConsumerStatefulWidget {
  const PhotonTransferScreen({super.key});

  @override
  ConsumerState<PhotonTransferScreen> createState() =>
      _PhotonTransferScreenState();
}

class _PhotonTransferScreenState extends ConsumerState<PhotonTransferScreen> {
  final _formKey = GlobalKey<FormState>();
  final _recipientIdController = TextEditingController();
  final _amountController = TextEditingController();
  final _messageController = TextEditingController();

  bool _isTransferring = false;

  @override
  void dispose() {
    _recipientIdController.dispose();
    _amountController.dispose();
    _messageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final balanceState = ref.watch(photonBalanceProvider);
    final isGuestMode = ref.watch(guestServiceProvider).isGuestMode;
    final currentBalance = balanceState.balance?.balance ?? 0;

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        title: const Text('转账光子'),
      ),
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(DS.xl),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Guest mode warning banner
              if (isGuestMode)
                Container(
                  margin: const EdgeInsets.only(bottom: DS.lg),
                  padding: const EdgeInsets.all(DS.md),
                  decoration: BoxDecoration(
                    color: DS.warningLight,
                    borderRadius: BorderRadius.circular(DS.radiusMd),
                    border: Border.all(color: DS.warning.withValues(alpha: 0.3)),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.info_outline, color: DS.warning),
                      const SizedBox(width: DS.sm),
                      Expanded(
                        child: Text(
                          '访客模式不支持转账功能，请注册账户体验完整功能',
                          style: TextStyle(color: DS.warning),
                        ),
                      ),
                    ],
                  ),
                ),

              // Current Balance Card
              GraphiteCardSurface(
                surfaceRole: SparkleSurfaceRole.accent,
                child: Row(
                  children: [
                    Icon(
                      Icons.flash_on_rounded,
                      color: DS.neutral0,
                      size: 32,
                    ),
                    const SizedBox(width: 16),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '当前余额',
                          style: TextStyle(
                            color: DS.neutral0.withValues(alpha: 0.9),
                            fontSize: 14,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          '$currentBalance',
                          style: TextStyle(
                            color: DS.neutral0,
                            fontSize: 28,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 32),

              // Recipient ID
              Text(
                '接收人ID',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
              const SizedBox(height: 8),
              TextFormField(
                controller: _recipientIdController,
                decoration: const InputDecoration(
                  hintText: '请输入用户ID',
                  prefixIcon: Icon(Icons.person_outline),
                  border: OutlineInputBorder(),
                ),
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return '请输入接收人ID';
                  }
                  return null;
                },
              ),

              const SizedBox(height: DS.xl),

              // Amount
              Text(
                '转账数量',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
              const SizedBox(height: 8),
              TextFormField(
                controller: _amountController,
                keyboardType: TextInputType.number,
                decoration: InputDecoration(
                  hintText: '请输入转账数量',
                  prefixIcon: const Icon(Icons.flash_on_outlined),
                  suffixIcon: SparkleIconButton(
                    variant: ButtonVariant.ghost,
                    size: 32,
                    icon: const Icon(Icons.add_circle_outline),
                    onPressed: () {
                      // Show quick amount options
                      _showAmountSelector(currentBalance);
                    },
                  ),
                  border: const OutlineInputBorder(),
                ),
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return '请输入转账数量';
                  }
                  final amount = int.tryParse(value);
                  if (amount == null || amount <= 0) {
                    return '请输入有效的数量';
                  }
                  if (amount > currentBalance) {
                    return '余额不足';
                  }
                  if (amount > 10000) {
                    return '单次转账不能超过10000光子';
                  }
                  return null;
                },
              ),

              const SizedBox(height: DS.xl),

              // Message (Optional)
              Text(
                '附言（可选）',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
              const SizedBox(height: 8),
              TextFormField(
                controller: _messageController,
                maxLines: 3,
                maxLength: 200,
                decoration: const InputDecoration(
                  hintText: '说点什么...',
                  border: OutlineInputBorder(),
                ),
              ),

              const SizedBox(height: 32),

              // Transfer Button
              SizedBox(
                width: double.infinity,
                height: 48,
                child: SparkleButton(
                  label: '确认转账',
                  expand: true,
                  onPressed: isGuestMode || _isTransferring
                      ? null
                      : () {
                          if (_formKey.currentState!.validate()) {
                            _confirmTransfer(currentBalance);
                          }
                        },
                  loading: _isTransferring,
                ),
              ),

              const SizedBox(height: 16),

              // Info Text
              Text(
                '• 转账后无法撤销\n• 单次转账上限10000光子\n• 请确认接收人ID正确',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.textSecondary,
                    ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _showAmountSelector(int currentBalance) {
    final quickAmounts = [100, 500, 1000, 2000, 5000];

    showModalBottomSheet<void>(
      context: context,
      builder: (context) => Container(
        padding: const EdgeInsets.all(DS.lg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '选择金额',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: DS.lg),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: quickAmounts.map((amount) {
                final isEnabled = amount <= currentBalance;
                return ActionChip(
                  label: Text('$amount'),
                  onPressed: isEnabled
                      ? () {
                          _amountController.text = amount.toString();
                          Navigator.of(context).pop();
                        }
                      : null,
                  backgroundColor: isEnabled
                      ? Theme.of(context).colorScheme.primary
                      : DS.surfaceTertiary,
                  labelStyle: TextStyle(
                    color: isEnabled ? DS.neutral0 : DS.textSecondary,
                  ),
                );
              }).toList(),
            ),
          ],
        ),
      ),
    );
  }

  void _confirmTransfer(int currentBalance) {
    final amount = int.parse(_amountController.text);
    final recipientId = _recipientIdController.text;

    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('确认转账'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('接收人ID：$recipientId'),
            const SizedBox(height: DS.sm),
            Text('转账数量：$amount 光子'),
            const SizedBox(height: DS.sm),
            Text('剩余余额：${currentBalance - amount} 光子'),
            if (_messageController.text.isNotEmpty) ...[
              const SizedBox(height: DS.sm),
              Text('附言：${_messageController.text}'),
            ],
            const SizedBox(height: DS.lg),
            const Text('转账后无法撤销，确认继续？'),
          ],
        ),
        actions: [
          SparkleButton.ghost(
            label: '取消',
            onPressed: () => Navigator.of(context).pop(),
          ),
          SparkleButton(
            label: '确认',
            onPressed: () {
              Navigator.of(context).pop();
              unawaited(_performTransfer());
            },
          ),
        ],
      ),
    );
  }

  Future<void> _performTransfer() async {
    setState(() {
      _isTransferring = true;
    });

    try {
      final repository = ref.read(photonRepositoryProvider);
      await repository.transferPhotons(
        recipientId: _recipientIdController.text.trim(),
        amount: int.parse(_amountController.text),
        message: _messageController.text.trim().isNotEmpty
            ? _messageController.text.trim()
            : null,
      );

      if (mounted) {
        AppFeedback.success(context, '转账成功');
        // Refresh balance
        ref.read(photonBalanceProvider.notifier).refreshBalance();
        Navigator.of(context).pop();
      }
    } catch (e) {
      if (mounted) {
        AppFeedback.error(context, '转账失败：$e');
      }
    } finally {
      if (mounted) {
        setState(() {
          _isTransferring = false;
        });
      }
    }
  }
}
