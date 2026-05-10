import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/home/presentation/providers/spine_status_band_provider.dart';

/// Aurora Status Band — persistent indicator on the dashboard showing
/// Aurora's current system state.
///
/// Vision section 15 / demo point #10: Users must see Aurora's state
/// at a glance. Tap to expand and see correction options.
class AuroraStatusBand extends StatefulWidget {
  const AuroraStatusBand({
    required this.state,
    this.label,
    this.correctionOptions = const [],
    this.cooldownRemainingSeconds,
    this.cooldownCanOverride = false,
    this.onTap,
    this.onCorrectionTap,
    this.onCooldownOverride,
    super.key,
  });

  final AuroraBandState state;
  final String? label;
  final List<CorrectionOption> correctionOptions;
  final int? cooldownRemainingSeconds;
  final bool cooldownCanOverride;
  final VoidCallback? onTap;
  final ValueChanged<CorrectionOption>? onCorrectionTap;
  final VoidCallback? onCooldownOverride;

  static AuroraBandState mapBandStatus(AuroraBandStatus status) =>
      switch (status) {
        AuroraBandStatus.sensing => AuroraBandState.sensing,
        AuroraBandStatus.calibrated => AuroraBandState.calibrated,
        AuroraBandStatus.riskFound => AuroraBandState.riskDetected,
        AuroraBandStatus.needsConfirm => AuroraBandState.needsConfirmation,
        AuroraBandStatus.calibrationAvailable =>
          AuroraBandState.calibrationAvailable,
        AuroraBandStatus.coolingDown => AuroraBandState.coolingDown,
      };

  @override
  State<AuroraStatusBand> createState() => _AuroraStatusBandState();
}

class _AuroraStatusBandState extends State<AuroraStatusBand>
    with SingleTickerProviderStateMixin {
  bool _expanded = false;

  static const Duration _animDuration = Duration(milliseconds: 200);

  @override
  Widget build(BuildContext context) {
    final config = _stateConfig;
    final hasCorrections = widget.correctionOptions.isNotEmpty;
    final hasExplanation = widget.label?.trim().isNotEmpty ?? false;
    final isCooling = widget.state == AuroraBandState.coolingDown &&
        widget.cooldownRemainingSeconds != null;
    final canExpand = hasCorrections || hasExplanation || isCooling;

    return Semantics(
      container: true,
      explicitChildNodes: true,
      button: true,
      label: _semanticLabel(config),
      hint: canExpand ? _expandHint : null,
      onTap: () => _activateBand(canExpand: canExpand),
      child: FocusableActionDetector(
        shortcuts: const <ShortcutActivator, Intent>{
          SingleActivator(LogicalKeyboardKey.enter): ActivateIntent(),
          SingleActivator(LogicalKeyboardKey.space): ActivateIntent(),
        },
        actions: <Type, Action<Intent>>{
          ActivateIntent: CallbackAction<ActivateIntent>(
            onInvoke: (_) {
              _activateBand(canExpand: canExpand);
              return null;
            },
          ),
        },
        child: GestureDetector(
          onTap: () => _activateBand(canExpand: canExpand),
          child: AnimatedContainer(
            duration: _animDuration,
            curve: Curves.easeInOutCubic,
            margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            constraints: const BoxConstraints(minHeight: 48),
            decoration: BoxDecoration(
              color: config.bgColor,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: config.borderColor),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Row(
                  children: [
                    Container(
                      width: 28,
                      height: 28,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        color: config.iconBgColor,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child:
                          Icon(config.icon, size: 14, color: config.iconColor),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            config.title,
                            style: DS.labelSmall.copyWith(
                              color: DS.textPrimary,
                              fontWeight: FontWeight.w600,
                              fontSize: 12,
                            ),
                          ),
                          if (widget.label != null && widget.label!.isNotEmpty)
                            Text(
                              widget.label!,
                              maxLines: _expanded ? 3 : 1,
                              overflow: TextOverflow.ellipsis,
                              style: DS.labelSmall.copyWith(
                                color: DS.textSecondary,
                                fontSize: 11,
                              ),
                            ),
                        ],
                      ),
                    ),
                    AnimatedRotation(
                      duration: _animDuration,
                      turns: _expanded ? 0.25 : 0,
                      child: Icon(
                        hasCorrections
                            ? Icons.chevron_right_rounded
                            : Icons.chevron_right_rounded,
                        size: 16,
                        color: DS.textTertiary,
                      ),
                    ),
                  ],
                ),
                if (_expanded) ...[
                  if (hasExplanation) ...[
                    const SizedBox(height: 8),
                    const Divider(height: 1, thickness: 0.5),
                    const SizedBox(height: 8),
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Icon(
                          Icons.fact_check_outlined,
                          size: 14,
                          color: DS.textSecondary,
                        ),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(
                            _expandedExplanation,
                            style: DS.labelSmall.copyWith(
                              color: DS.textSecondary,
                              fontSize: 11,
                              height: 1.35,
                            ),
                          ),
                        ),
                      ],
                    ),
                    if (!hasCorrections && widget.onTap != null) ...[
                      const SizedBox(height: 8),
                      Align(
                        alignment: Alignment.centerLeft,
                        child: TextButton.icon(
                          onPressed: widget.onTap,
                          icon: const Icon(Icons.chat_bubble_outline, size: 14),
                          label: Text(
                            I18nService.instance.l10n.auroraCorrectInChat,
                            style: DS.labelSmall.copyWith(fontSize: 11),
                          ),
                          style: TextButton.styleFrom(
                            minimumSize: const Size(44, 36),
                            padding: const EdgeInsets.symmetric(
                              horizontal: 8,
                              vertical: 4,
                            ),
                          ),
                        ),
                      ),
                    ],
                  ],
                  if (hasCorrections) ...[
                    if (!hasExplanation) ...[
                      const SizedBox(height: 8),
                      const Divider(height: 1, thickness: 0.5),
                    ],
                    const SizedBox(height: 8),
                    Text(
                      I18nService.instance.l10n.auroraIfReadOffCorrectHere,
                      style: DS.labelSmall.copyWith(
                        color: DS.textTertiary,
                        fontSize: 11,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Wrap(
                      spacing: 6,
                      runSpacing: 6,
                      children: widget.correctionOptions
                          .map(
                            (opt) => Semantics(
                              container: true,
                              button: true,
                              label: opt.label,
                              onTap: () => _selectCorrection(opt),
                              child: ExcludeSemantics(
                                child: ActionChip(
                                  label: Text(
                                    opt.label,
                                    style: DS.labelSmall.copyWith(fontSize: 11),
                                  ),
                                  onPressed: () => _selectCorrection(opt),
                                  backgroundColor: DS.surfaceHigh,
                                  side: BorderSide(
                                    color: opt.isDisconfirming
                                        ? DS.warning.withValues(alpha: 0.3)
                                        : DS.borderSubtle,
                                  ),
                                ),
                              ),
                            ),
                          )
                          .toList(),
                    ),
                  ],
                  if (widget.state == AuroraBandState.coolingDown &&
                      widget.cooldownRemainingSeconds != null) ...[
                    const SizedBox(height: 8),
                    const Divider(height: 1, thickness: 0.5),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Icon(
                          Icons.timer_outlined,
                          size: 14,
                          color: DS.textSecondary,
                        ),
                        const SizedBox(width: 4),
                        Text(
                          _formatCooldown(widget.cooldownRemainingSeconds!),
                          style: DS.labelSmall.copyWith(
                            color: DS.textSecondary,
                            fontSize: 11,
                          ),
                        ),
                        const Spacer(),
                        if (widget.cooldownCanOverride)
                          TextButton(
                            onPressed: () {
                              unawaited(
                                SensoryFeedbackService.emit(
                                  SensoryFeedbackEvent.tap,
                                ),
                              );
                              widget.onCooldownOverride?.call();
                            },
                            style: TextButton.styleFrom(
                              minimumSize: const Size(44, 44),
                              padding: const EdgeInsets.symmetric(
                                horizontal: 8,
                                vertical: 4,
                              ),
                            ),
                            child: Text(
                              I18nService.instance.l10n.auroraQuickCalibration,
                              style: DS.labelSmall.copyWith(
                                color: DS.brandPrimary,
                                fontSize: 11,
                              ),
                            ),
                          ),
                      ],
                    ),
                  ],
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }

  void _activateBand({required bool canExpand}) {
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.tap));
    if (canExpand) {
      setState(() => _expanded = !_expanded);
    } else {
      widget.onTap?.call();
    }
  }

  void _selectCorrection(CorrectionOption option) {
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.tap));
    widget.onCorrectionTap?.call(option);
  }

  String _semanticLabel(_AuroraBandConfig config) {
    final label = widget.label?.trim();
    if (label == null || label.isEmpty) {
      return config.title;
    }
    return '${config.title}. $label';
  }

  String get _expandHint {
    if (_expanded) {
      return I18nService.instance.l10n.auroraCollapseHint;
    }
    return I18nService.instance.l10n.auroraExpandHint;
  }

  String _formatCooldown(int seconds) {
    final l10n = I18nService.instance.l10n;
    if (seconds <= 0) return l10n.auroraCoolingDownResumingSoon;
    if (seconds < 60) return l10n.auroraCooldownSec(seconds);
    final minutes = seconds ~/ 60;
    if (minutes < 60) return l10n.auroraCooldownMin(minutes);
    final hours = minutes ~/ 60;
    final remainMinutes = minutes % 60;
    return l10n.auroraCooldownHr(hours, remainMinutes);
  }

  String get _expandedExplanation {
    final l10n = I18nService.instance.l10n;
    final label = widget.label?.trim() ?? '';
    if (label.isEmpty) {
      return l10n.auroraExpandedExplanationDefault;
    }
    return '${l10n.auroraExpandedExplanationPrefix}$label';
  }

  _AuroraBandConfig get _stateConfig {
    final l10n = I18nService.instance.l10n;
    switch (widget.state) {
      case AuroraBandState.sensing:
        return _AuroraBandConfig(
          icon: Icons.wifi_tethering_rounded,
          title: l10n.auroraSensing,
          iconColor: DS.textTertiary,
          iconBgColor: DS.surfaceSecondary,
          bgColor: DS.surfaceHigh,
          borderColor: DS.borderSubtle,
        );
      case AuroraBandState.calibrated:
        return _AuroraBandConfig(
          icon: Icons.check_circle_outline,
          title: l10n.auroraCalibrated,
          iconColor: DS.success,
          iconBgColor: DS.success.withValues(alpha: 0.1),
          bgColor: DS.success.withValues(alpha: 0.04),
          borderColor: DS.success.withValues(alpha: 0.15),
        );
      case AuroraBandState.riskDetected:
        return _AuroraBandConfig(
          icon: Icons.shield_outlined,
          title: l10n.auroraRiskDetected,
          iconColor: DS.warning,
          iconBgColor: DS.warning.withValues(alpha: 0.1),
          bgColor: DS.warning.withValues(alpha: 0.04),
          borderColor: DS.warning.withValues(alpha: 0.15),
        );
      case AuroraBandState.needsConfirmation:
        return _AuroraBandConfig(
          icon: Icons.help_outline,
          title: l10n.auroraNeedsConfirm,
          iconColor: DS.brandPrimary,
          iconBgColor: DS.brandPrimary.withValues(alpha: 0.1),
          bgColor: DS.brandPrimary.withValues(alpha: 0.04),
          borderColor: DS.brandPrimary.withValues(alpha: 0.15),
        );
      case AuroraBandState.calibrationAvailable:
        return _AuroraBandConfig(
          icon: Icons.tune_rounded,
          title: l10n.auroraCalibrationAvailable,
          iconColor: DS.info,
          iconBgColor: DS.info.withValues(alpha: 0.1),
          bgColor: DS.info.withValues(alpha: 0.04),
          borderColor: DS.info.withValues(alpha: 0.15),
        );
      case AuroraBandState.coolingDown:
        return _AuroraBandConfig(
          icon: Icons.ac_unit_rounded,
          title: l10n.auroraCoolingDown,
          iconColor: DS.textTertiary,
          iconBgColor: DS.surfaceSecondary,
          bgColor: DS.surfaceHigh,
          borderColor: DS.borderSubtle,
        );
      case AuroraBandState.sourceAware:
        return _AuroraBandConfig(
          icon: Icons.menu_book_outlined,
          title: l10n.auroraSourceAware,
          iconColor: DS.info,
          iconBgColor: DS.info.withValues(alpha: 0.1),
          bgColor: DS.info.withValues(alpha: 0.04),
          borderColor: DS.info.withValues(alpha: 0.15),
        );
      case AuroraBandState.noSourcesUsed:
        return _AuroraBandConfig(
          icon: Icons.auto_awesome_outlined,
          title: l10n.auroraNoSourcesUsed,
          iconColor: DS.textTertiary,
          iconBgColor: DS.surfaceSecondary,
          bgColor: DS.surfaceHigh,
          borderColor: DS.borderSubtle,
        );
      case AuroraBandState.strategyActive:
        return _AuroraBandConfig(
          icon: Icons.trending_up_rounded,
          title: l10n.auroraStrategyActive,
          iconColor: DS.success,
          iconBgColor: DS.success.withValues(alpha: 0.1),
          bgColor: DS.success.withValues(alpha: 0.04),
          borderColor: DS.success.withValues(alpha: 0.15),
        );
    }
  }
}

/// 9 states: 6 from backend + 3 legacy (sourceAware, noSourcesUsed, strategyActive).
enum AuroraBandState {
  sensing,
  calibrated,
  riskDetected,
  needsConfirmation,
  calibrationAvailable,
  coolingDown,
  sourceAware,
  noSourcesUsed,
  strategyActive,
}

class _AuroraBandConfig {
  const _AuroraBandConfig({
    required this.icon,
    required this.title,
    required this.iconColor,
    required this.iconBgColor,
    required this.bgColor,
    required this.borderColor,
  });

  final IconData icon;
  final String title;
  final Color iconColor;
  final Color iconBgColor;
  final Color bgColor;
  final Color borderColor;
}
