import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/custom_button.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

/// 退出确认步骤
enum ExitStep { first, second, third }

/// 三重确认退出对话框
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
  ExitStep _currentStep = ExitStep.first;
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
    if (_currentStep == ExitStep.third) {
      widget.onConfirmExit();
    } else {
      setState(() {
        _currentStep = ExitStep.values[_currentStep.index + 1];
      });
    }
  }

  void _cancel() {
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.tap));
    widget.onCancel();
  }

  @override
  Widget build(BuildContext context) => SlideTransition(
        position: _slideAnimation,
        child: Dialog(
          backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
          insetPadding: const EdgeInsets.all(DS.xl),
          child: Container(
            padding: const EdgeInsets.all(DS.xl),
            decoration: BoxDecoration(
              color: DS.deepSpaceSurface,
              borderRadius: BorderRadius.circular(20),
              border: Border.all(
                color: DS.brandPrimary.withValues(alpha: 0.1),
              ),
              boxShadow: [
                BoxShadow(
                  color: DS.brandPrimary.withValues(alpha: 0.5),
                  blurRadius: 20,
                  spreadRadius: 5,
                ),
              ],
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                // Progress Indicator
                _buildProgressIndicator(),
                const SizedBox(height: DS.xl),

                // Icon
                _buildIcon(),
                const SizedBox(height: DS.lg),

                // Title
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

                // Message
                Text(
                  _getMessage(),
                  style: TextStyle(
                    color: DS.brandPrimary.withValues(alpha: 0.7),
                    fontSize: 14,
                    height: 1.5,
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: DS.xl),

                // Buttons
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
                        customGradient: _currentStep == ExitStep.third
                            ? DS.errorGradient
                            : null,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      );

  Widget _buildProgressIndicator() => Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: List.generate(3, (index) {
          final isActive = index <= _currentStep.index;
          return Container(
            width: 24,
            height: 4,
            margin: const EdgeInsets.symmetric(horizontal: 4),
            decoration: BoxDecoration(
              color: isActive
                  ? DS.primaryBase
                  : DS.brandPrimary.withValues(alpha: 0.2),
              borderRadius: BorderRadius.circular(2),
            ),
          );
        }),
      );

  Widget _buildIcon() {
    IconData icon;
    Color color;

    switch (_currentStep) {
      case ExitStep.first:
        icon = Icons.pause_circle_outline_rounded;
        color = DS.warning;
      case ExitStep.second:
        icon = Icons.warning_amber_rounded;
        color = DS.warning;
      case ExitStep.third:
        icon = Icons.exit_to_app_rounded;
        color = DS.error;
    }

    return Container(
      padding: const EdgeInsets.all(DS.lg),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        shape: BoxShape.circle,
      ),
      child: Icon(icon, color: color, size: 40),
    );
  }

  String _getTitle() {
    final l10n = context.l10n;
    switch (_currentStep) {
      case ExitStep.first:
        return l10n.focusExitTitleStep1;
      case ExitStep.second:
        return l10n.focusExitTitleStep2;
      case ExitStep.third:
        return l10n.focusExitTitleStep3;
    }
  }

  String _getMessage() {
    final l10n = context.l10n;
    switch (_currentStep) {
      case ExitStep.first:
        return l10n.focusExitMessageStep1;
      case ExitStep.second:
        return l10n.focusExitMessageStep2(widget.elapsedMinutes);
      case ExitStep.third:
        return l10n.focusExitMessageStep3;
    }
  }

  String _getCancelText() {
    final l10n = context.l10n;
    switch (_currentStep) {
      case ExitStep.first:
        return l10n.focusExitCancelStep1;
      case ExitStep.second:
        return l10n.back;
      case ExitStep.third:
        return l10n.cancel;
    }
  }

  String _getConfirmText() {
    final l10n = context.l10n;
    switch (_currentStep) {
      case ExitStep.first:
        return l10n.focusExitConfirmStep1;
      case ExitStep.second:
        return l10n.focusExitConfirmStep2;
      case ExitStep.third:
        return l10n.focusExitConfirmStep3;
    }
  }
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
