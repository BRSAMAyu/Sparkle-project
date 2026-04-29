import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/design/widgets/app_feedback.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
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
        title: Text(context.l10n.ptTitle),
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
                    borderRadius: BorderRadius.circular(DS.borderRadiusMD),
                    border:
                        Border.all(color: DS.warning.withValues(alpha: 0.3)),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.info_outline, color: DS.warning),
                      const SizedBox(width: DS.sm),
                      Expanded(
                        child: Text(
                          context.l10n.ptGuestWarning,
                          style: TextStyle(color: DS.warning),
                        ),
                      ),
                    ],
                  ),
                ),

              // Current Balance Card
              SparkleStaggerItem(
                index: 0,
                child: GraphiteCardSurface(
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
                            context.l10n.ptCurrentBalance,
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
              ),

              const SizedBox(height: 32),

              // Recipient ID
              SparkleStaggerItem(
                index: 1,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      context.l10n.ptRecipientId,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                    ),
                    const SizedBox(height: 8),
                    TextFormField(
                      controller: _recipientIdController,
                      decoration: InputDecoration(
                        hintText: context.l10n.ptRecipientIdHint,
                        prefixIcon: Icon(Icons.person_outline),
                        border: OutlineInputBorder(),
                      ),
                      validator: (value) {
                        if (value == null || value.isEmpty) {
                          return context.l10n.ptRecipientIdRequired;
                        }
                        return null;
                      },
                    ),
                  ],
                ),
              ),

              const SizedBox(height: DS.xl),

              // Amount
              SparkleStaggerItem(
                index: 2,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      context.l10n.ptAmount,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                    ),
                    const SizedBox(height: 8),
                    TextFormField(
                      controller: _amountController,
                      keyboardType: TextInputType.number,
                      decoration: InputDecoration(
                        hintText: context.l10n.ptAmountHint,
                        prefixIcon: const Icon(Icons.flash_on_outlined),
                        suffixIcon: SparkleIconButton(
                          variant: ButtonVariant.ghost,
                          size: 32,
                          icon: const Icon(Icons.add_circle_outline),
                          onPressed: () {
                            unawaited(
                              SensoryFeedbackService.emit(
                                SensoryFeedbackEvent.sheetOpen,
                              ),
                            );
                            _showAmountSelector(currentBalance);
                          },
                        ),
                        border: const OutlineInputBorder(),
                      ),
                      validator: (value) {
                        if (value == null || value.isEmpty) {
                          return context.l10n.ptAmountRequired;
                        }
                        final amount = int.tryParse(value);
                        if (amount == null || amount <= 0) {
                          return context.l10n.ptAmountInvalid;
                        }
                        if (amount > currentBalance) {
                          return context.l10n.ptInsufficientBalance;
                        }
                        if (amount > 10000) {
                          return context.l10n.ptAmountExceedLimit;
                        }
                        return null;
                      },
                    ),
                  ],
                ),
              ),

              const SizedBox(height: DS.xl),

              // Message (Optional)
              SparkleStaggerItem(
                index: 3,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      context.l10n.ptMessageOptional,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                    ),
                    const SizedBox(height: 8),
                    TextFormField(
                      controller: _messageController,
                      maxLines: 3,
                      maxLength: 200,
                      decoration: InputDecoration(
                        hintText: context.l10n.ptMessageHint,
                        border: OutlineInputBorder(),
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 32),

              // Transfer Button
              SparkleStaggerItem(
                index: 4,
                child: SizedBox(
                  width: double.infinity,
                  height: 48,
                  child: SparkleButton(
                    label: context.l10n.ptConfirmTransfer,
                    expand: true,
                    onPressed: isGuestMode || _isTransferring
                        ? null
                        : () {
                            if (_formKey.currentState!.validate()) {
                              unawaited(
                                SensoryFeedbackService.emit(
                                  SensoryFeedbackEvent.confirm,
                                ),
                              );
                              _confirmTransfer(currentBalance);
                            }
                          },
                    loading: _isTransferring,
                  ),
                ),
              ),

              const SizedBox(height: 16),

              // Info Text
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        width: 5,
                        height: 5,
                        margin: const EdgeInsets.only(right: 8),
                        decoration: BoxDecoration(
                          color: DS.textSecondary,
                          shape: BoxShape.circle,
                        ),
                      ),
                      Expanded(child: Text(context.l10n.ptCannotUndo)),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      Container(
                        width: 5,
                        height: 5,
                        margin: const EdgeInsets.only(right: 8),
                        decoration: BoxDecoration(
                          color: DS.textSecondary,
                          shape: BoxShape.circle,
                        ),
                      ),
                      Expanded(child: Text(context.l10n.ptLimitNote)),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      Container(
                        width: 5,
                        height: 5,
                        margin: const EdgeInsets.only(right: 8),
                        decoration: BoxDecoration(
                          color: DS.textSecondary,
                          shape: BoxShape.circle,
                        ),
                      ),
                      Expanded(child: Text(context.l10n.ptVerifyRecipient)),
                    ],
                  ),
                ],
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
              context.l10n.ptSelectAmount,
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
                          unawaited(
                            SensoryFeedbackService.emit(
                              SensoryFeedbackEvent.selection,
                            ),
                          );
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
        title: Text(context.l10n.ptConfirmDialogTitle),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(context.l10n.ptRecipientLabel(recipientId)),
            const SizedBox(height: DS.sm),
            Text(context.l10n.ptAmountLabel(amount)),
            const SizedBox(height: DS.sm),
            Text(context.l10n.ptRemainingLabel(currentBalance - amount)),
            if (_messageController.text.isNotEmpty) ...[
              const SizedBox(height: DS.sm),
              Text(context.l10n.ptMessageLabel(_messageController.text)),
            ],
            const SizedBox(height: DS.lg),
            Text(context.l10n.ptConfirmWarning),
          ],
        ),
        actions: [
          SparkleButton.ghost(
            label: context.l10n.ptCancel,
            onPressed: () {
              unawaited(
                SensoryFeedbackService.emit(
                  SensoryFeedbackEvent.selection,
                ),
              );
              Navigator.of(context).pop();
            },
          ),
          SparkleButton(
            label: context.l10n.ptConfirm,
            onPressed: () {
              unawaited(
                SensoryFeedbackService.emit(
                  SensoryFeedbackEvent.confirm,
                ),
              );
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
        unawaited(
          SensoryFeedbackService.emit(SensoryFeedbackEvent.success),
        );
        AppFeedback.success(context, context.l10n.ptSuccess);
        // Refresh balance
        ref.read(photonBalanceProvider.notifier).refreshBalance();
        Navigator.of(context).pop();
      }
    } catch (e) {
      if (mounted) {
        AppFeedback.error(context, context.l10n.ptFailed(e.toString()));
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
