import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/custom_button.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';

/// Plan Switch Confirmation Dialog
///
/// A polished confirmation dialog shown when user attempts to
/// switch plan context with unsaved messages.
class PlanSwitchConfirmationDialog extends StatelessWidget {
  const PlanSwitchConfirmationDialog({
    super.key,
    required this.targetPlanName,
    required this.unsavedMessageCount,
    required this.onConfirm,
    required this.onCancel,
  });

  final String targetPlanName;
  final int unsavedMessageCount;
  final VoidCallback onConfirm;
  final VoidCallback onCancel;

  @override
  Widget build(BuildContext context) {
    final l10n = I18nService.instance.l10n;

    return Dialog(
      backgroundColor: Colors.transparent,
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 24),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              DS.surfacePrimary,
              Color.alphaBlend(
                DS.warning.withValues(alpha: 0.04),
                DS.surfaceSecondary,
              ),
            ],
          ),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: DS.borderSubtle,
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.08),
              blurRadius: 24,
              offset: const Offset(0, 8),
            ),
          ],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Animated warning icon
            _buildAnimatedHeader(context),

            // Content section
            Padding(
              padding: const EdgeInsets.fromLTRB(
                DS.spacing24,
                DS.spacing8,
                DS.spacing24,
                DS.spacing20,
              ),
              child: Column(
                children: [
                  // Title
                  Text(
                    l10n.chatPlanSwitchTitle,
                    style: TextStyle(
                      fontSize: DS.fontSizeLg,
                      fontWeight: DS.fontWeightBold,
                      color: DS.textPrimary,
                    ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: DS.spacing12),

                  // Message
                  Text(
                    l10n.chatPlanSwitchMessage,
                    style: TextStyle(
                      fontSize: DS.fontSizeBase,
                      color: DS.textSecondary,
                      height: 1.5,
                    ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: DS.spacing16),

                  // Unsaved count warning
                  if (unsavedMessageCount > 0)
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: DS.spacing12,
                        vertical: DS.spacing8,
                      ),
                      decoration: BoxDecoration(
                        color: DS.warning.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            Icons.warning_amber_rounded,
                            size: DS.iconSizeSm,
                            color: DS.warning,
                          ),
                          const SizedBox(width: DS.spacing8),
                          Flexible(
                            child: Text(
                              l10n.chatPlanSwitchUnsavedCount(unsavedMessageCount),
                              style: TextStyle(
                                fontSize: DS.fontSizeSm,
                                color: DS.warning,
                                fontWeight: DS.fontWeightMedium,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                ],
              ),
            ),

            // Action buttons
            Padding(
              padding: const EdgeInsets.fromLTRB(
                DS.spacing16,
                0,
                DS.spacing16,
                DS.spacing20,
              ),
              child: Row(
                children: [
                  // Cancel button
                  Expanded(
                    child: CustomButton.secondary(
                      text: context.l10n.cancel,
                      onPressed: () {
                        SensoryFeedbackService.emit(SensoryFeedbackEvent.tap);
                        onCancel();
                      },
                      size: CustomButtonSize.medium,
                    ),
                  ),
                  const SizedBox(width: DS.spacing12),
                  // Confirm button
                  Expanded(
                    child: CustomButton.primary(
                      text: context.l10n.confirm,
                      onPressed: () {
                        SensoryFeedbackService.emit(
                          SensoryFeedbackEvent.confirm,
                        );
                        onConfirm();
                      },
                      size: CustomButtonSize.medium,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAnimatedHeader(BuildContext context) {
    return Container(
      padding: const EdgeInsets.only(top: DS.spacing24),
      child: TweenAnimationBuilder<double>(
        tween: Tween(begin: 0, end: 1),
        duration: const Duration(milliseconds: 400),
        curve: Curves.easeOutBack,
        builder: (context, value, child) {
          return Transform.scale(
            scale: value,
            child: Container(
              padding: const EdgeInsets.all(DS.spacing16),
              decoration: BoxDecoration(
                color: DS.warning.withValues(alpha: 0.15),
                shape: BoxShape.circle,
              ),
              child: Icon(
                Icons.swap_horiz_rounded,
                size: DS.iconSizeLg,
                color: DS.warning,
              ),
            ),
          );
        },
      ),
    );
  }
}
