import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/plan/presentation/providers/sprint_actions_provider.dart';

/// Sprint action type
enum SprintActionType { complete, extend, abandon }

/// Shows sprint action dialog and returns the action type if confirmed
Future<SprintActionType?> showSprintActionsDialog(
  BuildContext context, {
  required String planId,
  required String planName,
}) =>
    showModalBottomSheet<SprintActionType>(
      context: context,
      backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
      builder: (context) => _SprintActionsSheet(
        planId: planId,
        planName: planName,
      ),
    );

/// Shows confirm complete dialog - returns true if confirmed
Future<bool> showConfirmCompleteDialog(
  BuildContext context, {
  required String planName,
}) async {
  final result = await showDialog<bool>(
    context: context,
    builder: (context) => _ConfirmCompleteDialog(planName: planName),
  );
  return result ?? false;
}

/// Shows extend sprint dialog - returns selected days or null
Future<int?> showExtendSprintDialog(
  BuildContext context, {
  required String planName,
}) async =>
    showDialog<int>(
      context: context,
      builder: (context) => _ExtendSprintDialog(planName: planName),
    );

/// Shows confirm abandon dialog - returns true if confirmed
Future<bool> showConfirmAbandonDialog(
  BuildContext context, {
  required String planName,
}) async {
  final result = await showDialog<bool>(
    context: context,
    builder: (context) => _ConfirmAbandonDialog(planName: planName),
  );
  return result ?? false;
}

/// Sprint actions bottom sheet
class _SprintActionsSheet extends ConsumerStatefulWidget {
  const _SprintActionsSheet({
    required this.planId,
    required this.planName,
  });

  final String planId;
  final String planName;

  @override
  ConsumerState<_SprintActionsSheet> createState() =>
      _SprintActionsSheetState();
}

class _SprintActionsSheetState extends ConsumerState<_SprintActionsSheet> {
  @override
  Widget build(BuildContext context) {
    final actionsState = ref.watch(sprintActionsProvider);

    // Show success/error messages
    if (actionsState.successMessage != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        AppFeedback.success(context, actionsState.successMessage!);
        ref.read(sprintActionsProvider.notifier).clearMessages();
        Navigator.of(context).pop();
      });
    }

    if (actionsState.error != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        AppFeedback.error(context, actionsState.error!);
        ref.read(sprintActionsProvider.notifier).clearMessages();
      });
    }

    return DecoratedBox(
      decoration: BoxDecoration(
        color: DS.surfacePrimary,
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(DS.spacing20),
          topRight: Radius.circular(DS.spacing20),
        ),
      ),
      child: SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Handle bar
            Container(
              margin: const EdgeInsets.only(top: DS.spacing12),
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: DS.surfaceTertiary,
                borderRadius: DS.borderRadiusFull,
              ),
            ),
            // Header
            Padding(
              padding: const EdgeInsets.all(DS.spacing20),
              child: Row(
                children: [
                  Icon(
                    Icons.flash_on_rounded,
                    color: DS.brandPrimaryConst,
                  ),
                  const SizedBox(width: DS.spacing12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '冲刺操作',
                          style: context.sparkleTypography.labelLarge.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        Text(
                          widget.planName,
                          style: context.sparkleTypography.labelSmall.copyWith(
                            color: DS.textSecondary,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const Divider(height: 1),
            // Actions
            if (actionsState.isProcessing)
              const Padding(
                padding: EdgeInsets.all(DS.spacing32),
                child: CircularProgressIndicator(),
              )
            else
              ListView(
                shrinkWrap: true,
                padding: const EdgeInsets.symmetric(vertical: DS.spacing8),
                children: [
                  _ActionTile(
                    icon: Icons.check_circle_rounded,
                    title: '完成冲刺',
                    subtitle: '标记冲刺为已完成并归档',
                    color: DS.semanticSuccess,
                    onTap: () => _handleComplete(context),
                  ),
                  _ActionTile(
                    icon: Icons.date_range_rounded,
                    title: '延长冲刺',
                    subtitle: '延长冲刺截止日期',
                    color: DS.info,
                    onTap: () => _handleExtend(context),
                  ),
                  _ActionTile(
                    icon: Icons.cancel_rounded,
                    title: '放弃冲刺',
                    subtitle: '放弃当前冲刺并归档',
                    color: DS.semanticError,
                    onTap: () => _handleAbandon(context),
                  ),
                ],
              ),
          ],
        ),
      ),
    );
  }

  Future<void> _handleComplete(BuildContext context) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => _ConfirmCompleteDialog(planName: widget.planName),
    );

    if ((confirmed ?? false) && mounted) {
      final success = await ref
          .read(sprintActionsProvider.notifier)
          .completeSprint(widget.planId);
      if (success && mounted) {
        Navigator.of(context).pop();
      }
    }
  }

  Future<void> _handleExtend(BuildContext context) async {
    final days = await showDialog<int>(
      context: context,
      builder: (context) => _ExtendSprintDialog(planName: widget.planName),
    );

    if (days != null && days > 0 && mounted) {
      final success = await ref
          .read(sprintActionsProvider.notifier)
          .extendSprint(widget.planId, days);
      if (success && mounted) {
        Navigator.of(context).pop();
      }
    }
  }

  Future<void> _handleAbandon(BuildContext context) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => _ConfirmAbandonDialog(planName: widget.planName),
    );

    if ((confirmed ?? false) && mounted) {
      final success = await ref
          .read(sprintActionsProvider.notifier)
          .abandonSprint(widget.planId, '');
      if (success && mounted) {
        Navigator.of(context).pop();
      }
    }
  }
}

class _ActionTile extends StatelessWidget {
  const _ActionTile({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.color,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => ListTile(
        leading: Container(
          padding: const EdgeInsets.all(DS.spacing8),
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.1),
            shape: BoxShape.circle,
          ),
          child: Icon(icon, color: color, size: DS.iconSizeSm),
        ),
        title: Text(
          title,
          style: context.sparkleTypography.bodyLarge.copyWith(
            fontWeight: FontWeight.w500,
          ),
        ),
        subtitle: Text(
          subtitle,
          style: context.sparkleTypography.labelSmall.copyWith(
            color: DS.textSecondary,
          ),
        ),
        trailing: const Icon(Icons.chevron_right_rounded),
        onTap: onTap,
      );
}

class _ConfirmCompleteDialog extends StatelessWidget {
  const _ConfirmCompleteDialog({required this.planName});

  final String planName;

  @override
  Widget build(BuildContext context) => AlertDialog(
        title: const Text('完成冲刺'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(
              Icons.check_circle_rounded,
              color: DS.semanticSuccess,
              size: 48,
            ),
            const SizedBox(height: DS.spacing16),
            Text(
              '确认完成「$planName」冲刺吗？',
              style: context.sparkleTypography.bodyMedium,
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              '完成后冲刺将被归档，无法再编辑。',
              style: context.sparkleTypography.labelSmall.copyWith(
                color: DS.textSecondary,
              ),
            ),
          ],
        ),
        actions: [
          SparkleButton.ghost(
            onPressed: () => Navigator.of(context).pop(false),
            label: '取消',
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: FilledButton.styleFrom(
              backgroundColor: DS.semanticSuccess,
            ),
            child: const Text('完成'),
          ),
        ],
      );
}

class _ConfirmAbandonDialog extends StatelessWidget {
  const _ConfirmAbandonDialog({required this.planName});

  final String planName;

  @override
  Widget build(BuildContext context) => AlertDialog(
        title: const Text('放弃冲刺'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(
              Icons.warning_rounded,
              color: DS.semanticError,
              size: 48,
            ),
            const SizedBox(height: DS.spacing16),
            Text(
              '确认放弃「$planName」冲刺吗？',
              style: context.sparkleTypography.bodyMedium,
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              '放弃后冲刺将被归档，当前进度将被保留。',
              style: context.sparkleTypography.labelSmall.copyWith(
                color: DS.textSecondary,
              ),
            ),
          ],
        ),
        actions: [
          SparkleButton.ghost(
            onPressed: () => Navigator.of(context).pop(false),
            label: '取消',
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: FilledButton.styleFrom(
              backgroundColor: DS.semanticError,
            ),
            child: const Text('放弃'),
          ),
        ],
      );
}

class _ExtendSprintDialog extends StatefulWidget {
  const _ExtendSprintDialog({required this.planName});

  final String planName;

  @override
  State<_ExtendSprintDialog> createState() => _ExtendSprintDialogState();
}

class _ExtendSprintDialogState extends State<_ExtendSprintDialog> {
  int _selectedDays = 3;
  final List<int> _dayOptions = [1, 3, 7, 14];

  @override
  Widget build(BuildContext context) => AlertDialog(
        title: const Text('延长冲刺'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(
              Icons.date_range_rounded,
              color: DS.info,
              size: 48,
            ),
            const SizedBox(height: DS.spacing16),
            Text(
              '延长「${widget.planName}」冲刺',
              style: context.sparkleTypography.bodyMedium,
            ),
            const SizedBox(height: DS.spacing16),
            Text(
              '选择延长天数',
              style: context.sparkleTypography.labelSmall.copyWith(
                color: DS.textSecondary,
              ),
            ),
            const SizedBox(height: DS.spacing8),
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing8,
              children: _dayOptions.map((days) {
                final isSelected = _selectedDays == days;
                return GestureDetector(
                  onTap: () => setState(() => _selectedDays = days),
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: DS.spacing16,
                      vertical: DS.spacing8,
                    ),
                    decoration: BoxDecoration(
                      color: isSelected ? DS.info : DS.surfaceSecondary,
                      borderRadius: DS.borderRadius8,
                      border: Border.all(
                        color: isSelected ? DS.info : DS.border,
                      ),
                    ),
                    child: Text(
                      '$days 天',
                      style: context.sparkleTypography.bodyMedium.copyWith(
                        color: isSelected ? DS.white : DS.textPrimary,
                        fontWeight:
                            isSelected ? FontWeight.w600 : FontWeight.normal,
                      ),
                    ),
                  ),
                );
              }).toList(),
            ),
          ],
        ),
        actions: [
          SparkleButton.ghost(
            onPressed: () => Navigator.of(context).pop(),
            label: '取消',
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(_selectedDays),
            style: FilledButton.styleFrom(
              backgroundColor: DS.info,
            ),
            child: Text('延长 $_selectedDays 天'),
          ),
        ],
      );
}
