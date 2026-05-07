import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/l10n/app_localizations.dart';

/// Aurora calibration panel — explicit Aurora 校准流程.
///
/// This is NOT a chat mode. It's a finite cognitive calibration flow:
/// observe → judge → acknowledge uncertainty → suggest → confirm → exit.
///
/// Triggered when user taps "重新校准" from contextual correction buttons.
/// Shows as a full-screen overlay or bottom sheet with structured steps.
class AuroraCalibrationPanel extends StatefulWidget {
  const AuroraCalibrationPanel({
    required this.observation,
    required this.judgment,
    this.uncertainty,
    this.suggestion,
    required this.confirmQuestion,
    required this.confirmOptions,
    this.onConfirm,
    this.onCustomResponse,
    this.onDismiss,
    super.key,
  });

  final String observation;
  final String judgment;
  final String? uncertainty;
  final String? suggestion;
  final String confirmQuestion;
  final List<String> confirmOptions;
  final ValueChanged<String>? onConfirm;
  final ValueChanged<String>? onCustomResponse;
  final VoidCallback? onDismiss;

  @override
  State<AuroraCalibrationPanel> createState() => _AuroraCalibrationPanelState();
}

class _AuroraCalibrationPanelState extends State<AuroraCalibrationPanel>
    with SingleTickerProviderStateMixin {
  late final AnimationController _slideController;
  late final Animation<Offset> _slideAnimation;
  _CalibrationPhase _phase = _CalibrationPhase.presenting;

  @override
  void initState() {
    super.initState();
    _slideController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 350),
    );
    _slideAnimation = Tween<Offset>(
      begin: const Offset(0, 0.3),
      end: Offset.zero,
    ).animate(CurvedAnimation(
      parent: _slideController,
      curve: Curves.easeOutCubic,
    ));
    unawaited(_slideController.forward());
  }

  @override
  void dispose() {
    _slideController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;

    return Container(
      decoration: BoxDecoration(
        color: DS.surfacePrimary,
        borderRadius:
            const BorderRadius.vertical(top: Radius.circular(DS.radius20)),
        border: Border.all(color: DS.borderSubtle),
        boxShadow: DS.shadowLg,
      ),
      child: SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildHandle(),
            Padding(
              padding: const EdgeInsets.fromLTRB(
                DS.spacing20,
                DS.spacing8,
                DS.spacing20,
                DS.spacing20,
              ),
              child: _phase == _CalibrationPhase.presenting
                  ? _buildPresentingContent(l10n)
                  : _buildConfirmedContent(l10n),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHandle() => Center(
        child: Container(
          margin: const EdgeInsets.only(top: DS.spacing12),
          width: 40,
          height: 4,
          decoration: BoxDecoration(
            color: DS.borderSubtle,
            borderRadius: BorderRadius.circular(2),
          ),
        ),
      );

  Widget _buildPresentingContent(AppLocalizations l10n) {
    return SlideTransition(
      position: _slideAnimation,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Title
          Row(
            children: [
              Icon(
                Icons.auto_fix_high_rounded,
                size: 20,
                color: DS.brandPrimary,
              ),
              const SizedBox(width: DS.spacing8),
              Text(
                l10n.auroraCalibrationTitle,
                style: DS.titleMedium.copyWith(
                  color: DS.textPrimary,
                  fontWeight: DS.fontWeightBold,
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing16),

          // Step 1: Observation
          _CalibrationStep(
            icon: Icons.visibility_outlined,
            label: l10n.auroraCalibrationObserved,
            content: widget.observation,
          ),
          const SizedBox(height: DS.spacing12),

          // Step 2: Judgment
          _CalibrationStep(
            icon: Icons.psychology_outlined,
            label: l10n.auroraCalibrationJudgment,
            content: widget.judgment,
          ),
          const SizedBox(height: DS.spacing12),

          // Step 3: Uncertainty (optional)
          if (widget.uncertainty != null &&
              widget.uncertainty!.trim().isNotEmpty) ...[
            _CalibrationStep(
              icon: Icons.help_outline_rounded,
              label: l10n.auroraCalibrationUncertainty,
              content: widget.uncertainty!,
              isDimmed: true,
            ),
            const SizedBox(height: DS.spacing12),
          ],

          // Step 4: Suggestion (optional)
          if (widget.suggestion != null &&
              widget.suggestion!.trim().isNotEmpty) ...[
            _CalibrationStep(
              icon: Icons.lightbulb_outline_rounded,
              label: l10n.auroraCalibrationSuggestion,
              content: widget.suggestion!,
            ),
            const SizedBox(height: DS.spacing16),
          ],

          // Step 5: Confirm question
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(DS.spacing14),
            decoration: BoxDecoration(
              color: DS.brandPrimary.withValues(alpha: 0.06),
              borderRadius: BorderRadius.circular(DS.radius12),
              border: Border.all(
                color: DS.brandPrimary.withValues(alpha: 0.2),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  l10n.auroraCalibrationConfirm,
                  style: DS.bodyMedium.copyWith(
                    color: DS.brandPrimary,
                    fontWeight: DS.fontWeightSemibold,
                  ),
                ),
                const SizedBox(height: DS.spacing6),
                Text(
                  widget.confirmQuestion,
                  style: DS.bodyMedium.copyWith(color: DS.textPrimary),
                ),
              ],
            ),
          ),
          const SizedBox(height: DS.spacing14),

          // Confirm options
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: [
              ...widget.confirmOptions.map(
                (option) => _ConfirmOptionChip(
                  label: option,
                  onTap: () => _handleConfirm(option),
                ),
              ),
              _ConfirmOptionChip(
                label: l10n.auroraActionDisagree,
                onTap: () => _handleCustomResponse(),
                isSecondary: true,
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildConfirmedContent(AppLocalizations l10n) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(
              Icons.check_circle_outline_rounded,
              size: 20,
              color: DS.success,
            ),
            const SizedBox(width: DS.spacing8),
            Text(
              l10n.auroraCalibrationExit,
              style: DS.bodyMedium.copyWith(
                color: DS.success,
                fontWeight: DS.fontWeightSemibold,
              ),
            ),
          ],
        ),
        const SizedBox(height: DS.spacing12),
        Text(
          l10n.auroraCalibrationComplete,
          style: DS.bodyMedium.copyWith(color: DS.textSecondary),
        ),
        const SizedBox(height: DS.spacing16),
        Align(
          alignment: Alignment.centerRight,
          child: TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: Text(l10n.auroraActionCloseDetails),
          ),
        ),
      ],
    );
  }

  void _handleConfirm(String option) {
    if (widget.onConfirm != null) {
      widget.onConfirm!(option);
    }
    setState(() => _phase = _CalibrationPhase.confirmed);
  }

  void _handleCustomResponse() {
    // For now, dismiss and let user type in standard input
    Navigator.of(context).pop();
    widget.onCustomResponse?.call('');
  }
}

/// Shows the Aurora calibration panel as a modal bottom sheet.
Future<void> showAuroraCalibration({
  required BuildContext context,
  required String observation,
  required String judgment,
  String? uncertainty,
  String? suggestion,
  required String confirmQuestion,
  required List<String> confirmOptions,
  ValueChanged<String>? onConfirm,
  ValueChanged<String>? onCustomResponse,
}) {
  return showSensoryModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    builder: (context) => Padding(
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom,
      ),
      child: AuroraCalibrationPanel(
        observation: observation,
        judgment: judgment,
        uncertainty: uncertainty,
        suggestion: suggestion,
        confirmQuestion: confirmQuestion,
        confirmOptions: confirmOptions,
        onConfirm: onConfirm,
        onCustomResponse: onCustomResponse,
      ),
    ),
  );
}

// ── Internal widgets ────────────────────────────────────────────

enum _CalibrationPhase { presenting, confirmed }

class _CalibrationStep extends StatelessWidget {
  const _CalibrationStep({
    required this.icon,
    required this.label,
    required this.content,
    this.isDimmed = false,
  });

  final IconData icon;
  final String label;
  final String content;
  final bool isDimmed;

  @override
  Widget build(BuildContext context) {
    final contentColor = isDimmed ? DS.textSecondary : DS.textPrimary;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 16, color: contentColor.withValues(alpha: 0.7)),
        const SizedBox(width: DS.spacing10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: TextStyle(
                  color: contentColor.withValues(alpha: 0.7),
                  fontSize: 11,
                  fontWeight: DS.fontWeightSemibold,
                ),
              ),
              const SizedBox(height: DS.spacing4),
              Text(
                content,
                style: DS.bodyMedium.copyWith(
                  color: contentColor,
                  height: 1.4,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _ConfirmOptionChip extends StatelessWidget {
  const _ConfirmOptionChip({
    required this.label,
    required this.onTap,
    this.isSecondary = false,
  });

  final String label;
  final VoidCallback onTap;
  final bool isSecondary;

  @override
  Widget build(BuildContext context) {
    if (isSecondary) {
      return Semantics(
        button: true,
        label: 'Chat aurora calibration panel control 1',
        child: GestureDetector(
          onTap: onTap,
          child: Container(
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing14,
              vertical: DS.spacing8,
            ),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(999),
              border: Border.all(color: DS.borderSubtle),
            ),
            child: Text(
              label,
              style: TextStyle(
                color: DS.textSecondary,
                fontSize: DS.fontSizeSm,
              ),
            ),
          ),
        ),
      );
    }
    return Semantics(
      button: true,
      label: 'Chat aurora calibration panel control 2',
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing14,
            vertical: DS.spacing8,
          ),
          decoration: BoxDecoration(
            color: DS.brandPrimary.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(999),
            border: Border.all(
              color: DS.brandPrimary.withValues(alpha: 0.25),
            ),
          ),
          child: Text(
            label,
            style: TextStyle(
              color: DS.brandPrimary,
              fontSize: DS.fontSizeSm,
              fontWeight: DS.fontWeightMedium,
            ),
          ),
        ),
      ),
    );
  }
}
