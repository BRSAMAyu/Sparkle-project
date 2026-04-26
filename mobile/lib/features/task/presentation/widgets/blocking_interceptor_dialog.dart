import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/app_feedback.dart';
import 'package:sparkle/core/design/widgets/custom_button.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/cognitive/presentation/providers/cognitive_provider.dart';

class BlockingInterceptorDialog extends ConsumerStatefulWidget {
  const BlockingInterceptorDialog({
    required this.taskId,
    required this.onAbandonConfirmed,
    super.key,
  });
  final String taskId;
  final VoidCallback onAbandonConfirmed;

  @override
  ConsumerState<BlockingInterceptorDialog> createState() =>
      _BlockingInterceptorDialogState();
}

class _BlockingInterceptorDialogState
    extends ConsumerState<BlockingInterceptorDialog> {
  final TextEditingController _controller = TextEditingController();
  String? _selectedReason;
  bool _isSubmitting = false;

  @override
  void initState() {
    super.initState();
    unawaited(
      SensoryFeedbackService.emit(
        SensoryFeedbackEvent.warning,
        enableSound: false,
      ),
    );
  }

  List<String> _reasons(BuildContext context) => [
        context.l10n.blockingReasonEfficiency,
        context.l10n.blockingReasonInterrupted,
        context.l10n.blockingReasonPerfectionism,
        context.l10n.blockingReasonTooHard,
        context.l10n.blockingReasonNoMood,
      ];

  Future<void> _submit() async {
    final content = _selectedReason ?? _controller.text.trim();
    if (content.isEmpty) {
      unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.warning));
      ScaffoldMessenger.of(context).showSnackBar(
        SparkleSnackBar.warning(context.l10n.blockingSelectReason),
      );
      return;
    }

    setState(() => _isSubmitting = true);
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm));

    try {
      // 1. Record Cognitive Fragment
      await ref.read(cognitiveProvider.notifier).createFragment(
            content: content,
            sourceType: 'interceptor',
            taskId: widget.taskId,
          );

      // 2. Abandon Task (Handled by callback or here? Callback usually just closes UI or triggers repo)
      // The parent usually calls abandonTask API.
      // But we want to record fragment BEFORE abandoning? Or in parallel?
      // Let's assume onAbandonConfirmed handles the actual task abandonment.

      widget.onAbandonConfirmed();

      if (mounted) {
        Navigator.of(context).pop(); // Close dialog
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SparkleSnackBar.error(context.l10n.submitFailedWithError(e)),
        );
        setState(() => _isSubmitting = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final reasons = _reasons(context);
    final selectedReason =
        _selectedReason == null || !reasons.contains(_selectedReason)
            ? 'other'
            : _selectedReason;

    return Dialog(
      shape: const RoundedRectangleBorder(borderRadius: DS.borderRadius20),
      child: Padding(
        padding: const EdgeInsets.all(DS.spacing20),
        child: SingleChildScrollView(
          child: SparkleStaggerItem(
            index: 0,
            offset: 0.04,
            child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(DS.sm),
                    decoration: BoxDecoration(
                      color: DS.warning.withValues(alpha: 0.1),
                      shape: BoxShape.circle,
                    ),
                    child: Icon(Icons.block, color: DS.warning),
                  ),
                  const SizedBox(width: DS.spacing12),
                  Expanded(
                    child: Text(
                      l10n.blockingTitle,
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                            fontWeight: DS.fontWeightBold,
                          ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: DS.spacing16),
              Text(
                l10n.blockingDescription,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: DS.neutral600,
                    ),
              ),
              const SizedBox(height: DS.spacing20),
              RadioGroup<String>(
                groupValue: selectedReason,
                onChanged: (value) {
                  unawaited(
                    SensoryFeedbackService.emit(
                      SensoryFeedbackEvent.selection,
                      enableSound: false,
                    ),
                  );
                  setState(() => _selectedReason = value);
                },
                child: Column(
                  children: [
                    // Preset Options
                    ...reasons.map(
                      (reason) => RadioListTile<String>(
                        title: Text(reason),
                        value: reason,
                        contentPadding: EdgeInsets.zero,
                        activeColor: DS.primaryBase,
                      ),
                    ),

                    // Other/Custom Input
                    RadioListTile<String>(
                      title: Text(l10n.blockingOtherReason),
                      value: 'other',
                      contentPadding: EdgeInsets.zero,
                      activeColor: DS.primaryBase,
                    ),
                  ],
                ),
              ),
              if (_selectedReason == 'other')
                TextField(
                  controller: _controller,
                  decoration: InputDecoration(
                    hintText: l10n.blockingReasonHint,
                    isDense: true,
                  ),
                ),
              const SizedBox(height: DS.spacing24),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  SparkleButton.ghost(
                    label: l10n.cancel,
                    onPressed: () {
                      unawaited(
                        SensoryFeedbackService.emit(
                          SensoryFeedbackEvent.tap,
                          enableSound: false,
                        ),
                      );
                      Navigator.of(context).pop();
                    },
                  ),
                  const SizedBox(width: DS.spacing12),
                  CustomButton.primary(
                    text: l10n.blockingConfirmAbandon,
                    icon: Icons.check,
                    onPressed: _isSubmitting ? () {} : _submit,
                    isLoading: _isSubmitting,
                    size: CustomButtonSize.small,
                    customGradient: DS.warningGradient, // Orange/Red warning
                  ),
                ],
              ),
            ],
            ),
          ),
        ),
      ),
    );
  }
}
