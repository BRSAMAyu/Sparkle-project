import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/custom_button.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';

/// 单次确认退出对话框
class ExitConfirmationDialog extends StatefulWidget {
  const ExitConfirmationDialog({
    required this.elapsedMinutes,
    required this.onConfirmExit,
    required this.onCancel,
    super.key,
  });
  final int elapsedMinutes;
  final VoidCallback onConfirmExit;
  final VoidCallback onCancel;

  @override
  State<ExitConfirmationDialog> createState() => _ExitConfirmationDialogState();
}

class _ExitConfirmationDialogState extends State<ExitConfirmationDialog>
    with SingleTickerProviderStateMixin {
  late AnimationController _slideController;
  late Animation<Offset> _slideAnimation;

  @override
  void initState() {
    super.initState();
    _slideController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 200),
    );
    _slideAnimation = Tween<Offset>(
      begin: const Offset(0, 1),
      end: Offset.zero,
    ).animate(
      CurvedAnimation(
        parent: _slideController,
        curve: Curves.easeOut,
      ),
    );
    _slideController.forward();
  }

  @override
  void dispose() {
    _slideController.dispose();
    super.dispose();
  }

  void _nextStep() {
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.tap));
    widget.onConfirmExit();
  }

  void _cancel() {
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.tap));
    widget.onCancel();
  }

  @override
  Widget build(BuildContext context) => SlideTransition(
        position: _slideAnimation,
        child: Material(
          type: MaterialType.transparency,
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Padding(
                padding: const EdgeInsets.all(DS.xl),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(24),
                  child: Container(
                    padding: const EdgeInsets.all(DS.xl),
                    decoration: BoxDecoration(
                      color: DS.deepSpaceSurface,
                      borderRadius: BorderRadius.circular(24),
                      border: Border.all(
                        color: DS.brandPrimary.withValues(alpha: 0.14),
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: DS.brandPrimary.withValues(alpha: 0.22),
                          blurRadius: 28,
                          offset: const Offset(0, 16),
                        ),
                      ],
                    ),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        _buildIcon(),
                        const SizedBox(height: DS.lg),
                        Text(
                          _getTitle(),
                          style: TextStyle(
                            color: DS.brandPrimaryConst,
                            fontSize: 20,
                            fontWeight: FontWeight.bold,
                          ),
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: DS.md),
                        Text(
                          _getMessage(),
                          style: TextStyle(
                            color: DS.brandPrimary.withValues(alpha: 0.78),
                            fontSize: 14,
                            height: 1.5,
                          ),
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: DS.xl),
                        Row(
                          children: [
                            Expanded(
                              child: CustomButton.secondary(
                                text: _getCancelText(),
                                onPressed: _cancel,
                              ),
                            ),
                            const SizedBox(width: DS.lg),
                            Expanded(
                              child: CustomButton.primary(
                                text: _getConfirmText(),
                                onPressed: _nextStep,
                                customGradient: DS.errorGradient,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      );

  Widget _buildIcon() => Container(
      padding: const EdgeInsets.all(DS.lg),
      decoration: BoxDecoration(
        color: DS.warning.withValues(alpha: 0.12),
        shape: BoxShape.circle,
      ),
      child: Icon(
        Icons.exit_to_app_rounded,
        color: DS.warning,
        size: 40,
      ),
    );

  String _getTitle() => context.l10n.focusExitTitleStep1;

  String _getMessage() => context.l10n.focusExitMessageStep2(
        widget.elapsedMinutes,
      );

  String _getCancelText() => context.l10n.cancel;

  String _getConfirmText() => context.l10n.focusExitConfirmStep3;
}

/// 显示退出确认对话框
Future<bool> showExitConfirmation(
  BuildContext context, {
  required int elapsedMinutes,
}) async {
  final result = await showDialog<bool>(
    context: context,
    barrierDismissible: false,
    barrierColor: DS.brandPrimary.withValues(alpha: 0.7),
    builder: (context) => ExitConfirmationDialog(
      elapsedMinutes: elapsedMinutes,
      onConfirmExit: () => Navigator.of(context).pop(true),
      onCancel: () => Navigator.of(context).pop(false),
    ),
  );
  return result ?? false;
}
