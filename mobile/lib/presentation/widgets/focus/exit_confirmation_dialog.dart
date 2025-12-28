import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/presentation/widgets/common/custom_button.dart';

/// 退出确认步骤
enum ExitStep { first, second, third }

/// 三重确认退出对话框
class ExitConfirmationDialog extends StatefulWidget {

  const ExitConfirmationDialog({
    required this.elapsedMinutes, required this.onConfirmExit, required this.onCancel, super.key,
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
    ).animate(CurvedAnimation(
      parent: _slideController,
      curve: Curves.easeOut,
    ),);
    _slideController.forward();
  }

  @override
  void dispose() {
    _slideController.dispose();
    super.dispose();
  }

  void _nextStep() {
    HapticFeedback.lightImpact();
    if (_currentStep == ExitStep.third) {
      widget.onConfirmExit();
    } else {
      setState(() {
        _currentStep = ExitStep.values[_currentStep.index + 1];
      });
    }
  }

  void _cancel() {
    HapticFeedback.lightImpact();
    widget.onCancel();
  }

  @override
  Widget build(BuildContext context) => SlideTransition(
      position: _slideAnimation,
      child: Dialog(
        backgroundColor: Colors.transparent,
        insetPadding: EdgeInsets.all(DS.xl),
        child: Container(
          padding: EdgeInsets.all(DS.xl),
          decoration: BoxDecoration(
            color: AppDesignTokens.deepSpaceSurface,
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
              SizedBox(height: DS.xl),

              // Icon
              _buildIcon(),
              SizedBox(height: DS.lg),

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
              SizedBox(height: DS.md),

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
              SizedBox(height: DS.xl),

              // Buttons
              Row(
                children: [
                  Expanded(
                    child: CustomButton.secondary(
                      text: _getCancelText(),
                      onPressed: _cancel,
                      size: CustomButtonSize.medium,
                    ),
                  ),
                  SizedBox(width: DS.lg),
                  Expanded(
                    child: CustomButton.primary(
                      text: _getConfirmText(),
                      onPressed: _nextStep,
                      customGradient: _currentStep == ExitStep.third
                          ? AppDesignTokens.errorGradient
                          : null,
                      size: CustomButtonSize.medium,
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
                ? AppDesignTokens.primaryBase
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
        color = AppDesignTokens.warning;
      case ExitStep.second:
        icon = Icons.warning_amber_rounded;
        color = AppDesignTokens.warning;
      case ExitStep.third:
        icon = Icons.exit_to_app_rounded;
        color = AppDesignTokens.error;
    }

    return Container(
      padding: EdgeInsets.all(DS.lg),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        shape: BoxShape.circle,
      ),
      child: Icon(icon, color: color, size: 40),
    );
  }

  String _getTitle() {
    switch (_currentStep) {
      case ExitStep.first:
        return '确定要退出正念模式吗？';
      case ExitStep.second:
        return '即将退出';
      case ExitStep.third:
        return '最后确认';
    }
  }

  String _getMessage() {
    switch (_currentStep) {
      case ExitStep.first:
        return '你正处于专注状态，退出可能会影响专注效果。';
      case ExitStep.second:
        return '你已经专注了 ${widget.elapsedMinutes} 分钟，确定要离开吗？';
      case ExitStep.third:
        return '再坚持一下！放弃会中断你的专注记录。';
    }
  }

  String _getCancelText() {
    switch (_currentStep) {
      case ExitStep.first:
        return '继续专注';
      case ExitStep.second:
        return '返回';
      case ExitStep.third:
        return '取消';
    }
  }

  String _getConfirmText() {
    switch (_currentStep) {
      case ExitStep.first:
        return '确认退出';
      case ExitStep.second:
        return '继续退出';
      case ExitStep.third:
        return '确定退出';
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
