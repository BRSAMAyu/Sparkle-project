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
    final isCooling = widget.state == AuroraBandState.coolingDown &&
        widget.cooldownRemainingSeconds != null;
    final canExpand = hasCorrections || isCooling;

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
                  if (hasCorrections) ...[
                    const SizedBox(height: 8),
                    const Divider(height: 1, thickness: 0.5),
                    const SizedBox(height: 8),
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
                              I18nService.instance.isChinese
                                  ? '快速校准'
                                  : 'Quick Calibration',
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
    final zh = I18nService.instance.isChinese;
    if (_expanded) {
      return zh ? '双击收起校准选项' : 'Double tap to collapse calibration options';
    }
    return zh ? '双击展开校准选项' : 'Double tap to expand calibration options';
  }

  String _formatCooldown(int seconds) {
    final zh = I18nService.instance.isChinese;
    if (seconds <= 0) return zh ? '即将恢复' : 'Resuming soon';
    if (seconds < 60) return zh ? '$seconds秒后恢复' : 'Resuming in $seconds sec';
    final minutes = seconds ~/ 60;
    if (minutes < 60) return zh ? '$minutes分钟后恢复' : 'Resuming in $minutes min';
    final hours = minutes ~/ 60;
    final remainMinutes = minutes % 60;
    return zh
        ? '$hours小时$remainMinutes分钟后恢复'
        : 'Resuming in $hours hr $remainMinutes min';
  }

  _AuroraBandConfig get _stateConfig {
    final zh = I18nService.instance.isChinese;
    switch (widget.state) {
      case AuroraBandState.sensing:
        return _AuroraBandConfig(
          icon: Icons.wifi_tethering_rounded,
          title: zh ? 'Aurora · 轻量感知中' : 'Aurora · Lightweight Sensing',
          iconColor: DS.textTertiary,
          iconBgColor: DS.surfaceSecondary,
          bgColor: DS.surfaceHigh,
          borderColor: DS.borderSubtle,
        );
      case AuroraBandState.calibrated:
        return _AuroraBandConfig(
          icon: Icons.check_circle_outline,
          title: zh ? 'Aurora · 已校准' : 'Aurora · Calibrated',
          iconColor: DS.success,
          iconBgColor: DS.success.withValues(alpha: 0.1),
          bgColor: DS.success.withValues(alpha: 0.04),
          borderColor: DS.success.withValues(alpha: 0.15),
        );
      case AuroraBandState.riskDetected:
        return _AuroraBandConfig(
          icon: Icons.shield_outlined,
          title: zh ? 'Aurora · 发现策略风险' : 'Aurora · Strategy Risk Detected',
          iconColor: DS.warning,
          iconBgColor: DS.warning.withValues(alpha: 0.1),
          bgColor: DS.warning.withValues(alpha: 0.04),
          borderColor: DS.warning.withValues(alpha: 0.15),
        );
      case AuroraBandState.needsConfirmation:
        return _AuroraBandConfig(
          icon: Icons.help_outline,
          title: zh ? 'Aurora · 需要确认一个判断' : 'Aurora · Confirmation Needed',
          iconColor: DS.brandPrimary,
          iconBgColor: DS.brandPrimary.withValues(alpha: 0.1),
          bgColor: DS.brandPrimary.withValues(alpha: 0.04),
          borderColor: DS.brandPrimary.withValues(alpha: 0.15),
        );
      case AuroraBandState.calibrationAvailable:
        return _AuroraBandConfig(
          icon: Icons.tune_rounded,
          title: zh ? 'Aurora · 深度校准可用' : 'Aurora · Deep Calibration Available',
          iconColor: DS.info,
          iconBgColor: DS.info.withValues(alpha: 0.1),
          bgColor: DS.info.withValues(alpha: 0.04),
          borderColor: DS.info.withValues(alpha: 0.15),
        );
      case AuroraBandState.coolingDown:
        return _AuroraBandConfig(
          icon: Icons.ac_unit_rounded,
          title: zh ? 'Aurora · 冷却中' : 'Aurora · Cooling Down',
          iconColor: DS.textTertiary,
          iconBgColor: DS.surfaceSecondary,
          bgColor: DS.surfaceHigh,
          borderColor: DS.borderSubtle,
        );
      case AuroraBandState.sourceAware:
        return _AuroraBandConfig(
          icon: Icons.menu_book_outlined,
          title: zh
              ? 'Aurora · 已参考当前任务资料'
              : 'Aurora · Referenced Current Task Materials',
          iconColor: DS.info,
          iconBgColor: DS.info.withValues(alpha: 0.1),
          bgColor: DS.info.withValues(alpha: 0.04),
          borderColor: DS.info.withValues(alpha: 0.15),
        );
      case AuroraBandState.noSourcesUsed:
        return _AuroraBandConfig(
          icon: Icons.auto_awesome_outlined,
          title:
              zh ? 'Aurora · 本轮未调用课件' : 'Aurora · No Materials Used This Round',
          iconColor: DS.textTertiary,
          iconBgColor: DS.surfaceSecondary,
          bgColor: DS.surfaceHigh,
          borderColor: DS.borderSubtle,
        );
      case AuroraBandState.strategyActive:
        return _AuroraBandConfig(
          icon: Icons.trending_up_rounded,
          title: zh ? 'Aurora · 策略已激活' : 'Aurora · Strategy Active',
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
