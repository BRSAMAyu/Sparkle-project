import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';

/// Aurora Status Band — persistent indicator on the dashboard showing
/// Aurora's current system state.
///
/// Vision section 15 / demo point #10: Users must see Aurora's state
/// at a glance (已校准 / 发现风险 / 需要确认 / 资料感知 / 未用资料).
class AuroraStatusBand extends StatelessWidget {
  const AuroraStatusBand({
    required this.state,
    this.label,
    this.onTap,
    super.key,
  });

  final AuroraBandState state;
  final String? label;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final config = _stateConfig;
    return GestureDetector(
      onTap: () {
        SensoryFeedbackService.emit(SensoryFeedbackEvent.tap);
        onTap?.call();
      },
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: config.bgColor,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: config.borderColor),
        ),
        child: Row(
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
                  if (label != null && label!.isNotEmpty)
                    Text(
                      label!,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: DS.labelSmall.copyWith(
                        color: DS.textSecondary,
                        fontSize: 11,
                      ),
                    ),
                ],
              ),
            ),
            Icon(
              Icons.chevron_right_rounded,
              size: 16,
              color: DS.textTertiary,
            ),
          ],
        ),
      ),
    );
  }

  _AuroraBandConfig get _stateConfig {
    switch (state) {
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

enum AuroraBandState {
  calibrated,
  riskDetected,
  needsConfirmation,
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
