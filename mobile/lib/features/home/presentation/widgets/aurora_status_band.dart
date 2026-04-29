import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
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
    this.onTap,
    this.onCorrectionTap,
    super.key,
  });

  final AuroraBandState state;
  final String? label;
  final List<CorrectionOption> correctionOptions;
  final VoidCallback? onTap;
  final ValueChanged<CorrectionOption>? onCorrectionTap;

  static AuroraBandState mapBandStatus(AuroraBandStatus status) => switch (status) {
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

    return GestureDetector(
      onTap: () {
        SensoryFeedbackService.emit(SensoryFeedbackEvent.tap);
        if (hasCorrections) {
          setState(() => _expanded = !_expanded);
        } else {
          widget.onTap?.call();
        }
      },
      child: AnimatedContainer(
        duration: _animDuration,
        curve: Curves.easeInOutCubic,
        margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
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
                  child: Icon(config.icon, size: 14, color: config.iconColor),
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
            if (_expanded && hasCorrections) ...[
              const SizedBox(height: 8),
              const Divider(height: 1, thickness: 0.5),
              const SizedBox(height: 8),
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: widget.correctionOptions.map((opt) {
                  return ActionChip(
                    label: Text(
                      opt.label,
                      style: DS.labelSmall.copyWith(fontSize: 11),
                    ),
                    onPressed: () {
                      SensoryFeedbackService.emit(SensoryFeedbackEvent.tap);
                      widget.onCorrectionTap?.call(opt);
                    },
                    backgroundColor: DS.surfaceHigh,
                    side: BorderSide(
                      color: opt.isDisconfirming
                          ? DS.warning.withValues(alpha: 0.3)
                          : DS.borderSubtle,
                    ),
                  );
                }).toList(),
              ),
            ],
          ],
        ),
      ),
    );
  }

  _AuroraBandConfig get _stateConfig {
    switch (widget.state) {
      case AuroraBandState.sensing:
        return _AuroraBandConfig(
          icon: Icons.wifi_tethering_rounded,
          title: 'Aurora · 轻量感知中',
          iconColor: DS.textTertiary,
          iconBgColor: DS.surfaceSecondary,
          bgColor: DS.surfaceHigh,
          borderColor: DS.borderSubtle,
        );
      case AuroraBandState.calibrated:
        return _AuroraBandConfig(
          icon: Icons.check_circle_outline,
          title: 'Aurora · 已校准',
          iconColor: DS.success,
          iconBgColor: DS.success.withValues(alpha: 0.1),
          bgColor: DS.success.withValues(alpha: 0.04),
          borderColor: DS.success.withValues(alpha: 0.15),
        );
      case AuroraBandState.riskDetected:
        return _AuroraBandConfig(
          icon: Icons.shield_outlined,
          title: 'Aurora · 发现策略风险',
          iconColor: DS.warning,
          iconBgColor: DS.warning.withValues(alpha: 0.1),
          bgColor: DS.warning.withValues(alpha: 0.04),
          borderColor: DS.warning.withValues(alpha: 0.15),
        );
      case AuroraBandState.needsConfirmation:
        return _AuroraBandConfig(
          icon: Icons.help_outline,
          title: 'Aurora · 需要确认一个判断',
          iconColor: DS.brandPrimary,
          iconBgColor: DS.brandPrimary.withValues(alpha: 0.1),
          bgColor: DS.brandPrimary.withValues(alpha: 0.04),
          borderColor: DS.brandPrimary.withValues(alpha: 0.15),
        );
      case AuroraBandState.calibrationAvailable:
        return _AuroraBandConfig(
          icon: Icons.tune_rounded,
          title: 'Aurora · 深度校准可用',
          iconColor: DS.info,
          iconBgColor: DS.info.withValues(alpha: 0.1),
          bgColor: DS.info.withValues(alpha: 0.04),
          borderColor: DS.info.withValues(alpha: 0.15),
        );
      case AuroraBandState.coolingDown:
        return _AuroraBandConfig(
          icon: Icons.ac_unit_rounded,
          title: 'Aurora · 冷却中',
          iconColor: DS.textTertiary,
          iconBgColor: DS.surfaceSecondary,
          bgColor: DS.surfaceHigh,
          borderColor: DS.borderSubtle,
        );
      case AuroraBandState.sourceAware:
        return _AuroraBandConfig(
          icon: Icons.menu_book_outlined,
          title: 'Aurora · 已参考当前任务资料',
          iconColor: DS.info,
          iconBgColor: DS.info.withValues(alpha: 0.1),
          bgColor: DS.info.withValues(alpha: 0.04),
          borderColor: DS.info.withValues(alpha: 0.15),
        );
      case AuroraBandState.noSourcesUsed:
        return _AuroraBandConfig(
          icon: Icons.auto_awesome_outlined,
          title: 'Aurora · 本轮未调用课件',
          iconColor: DS.textTertiary,
          iconBgColor: DS.surfaceSecondary,
          bgColor: DS.surfaceHigh,
          borderColor: DS.borderSubtle,
        );
      case AuroraBandState.strategyActive:
        return _AuroraBandConfig(
          icon: Icons.trending_up_rounded,
          title: 'Aurora · 策略已激活',
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
