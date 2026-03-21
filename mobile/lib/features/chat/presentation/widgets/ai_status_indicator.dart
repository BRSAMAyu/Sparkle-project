import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/components/atoms/ai_status_capsule.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/utils/ai_status_mapper.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/widgets/bgm_scope.dart';

/// AI 状态指示器
/// 显示 AI 的当前状态（THINKING, GENERATING, EXECUTING_TOOL 等）
class AiStatusIndicator extends StatefulWidget {
  const AiStatusIndicator({
    super.key,
    this.status,
    this.details,
    this.startedAtEpochMs,
  });
  final String? status;
  final String? details;
  final int? startedAtEpochMs;

  @override
  State<AiStatusIndicator> createState() => _AiStatusIndicatorState();
}

class _AiStatusIndicatorState extends State<AiStatusIndicator> {
  Timer? _ticker;

  @override
  void initState() {
    super.initState();
    _configureTicker();
  }

  @override
  void didUpdateWidget(covariant AiStatusIndicator oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.startedAtEpochMs != widget.startedAtEpochMs ||
        oldWidget.status != widget.status) {
      _configureTicker();
    }
  }

  @override
  void dispose() {
    _ticker?.cancel();
    super.dispose();
  }

  void _configureTicker() {
    _ticker?.cancel();
    if (widget.startedAtEpochMs == null || widget.status == null) {
      return;
    }
    _ticker = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) {
        setState(() {});
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final status = widget.status;
    if (status == null) {
      return const SizedBox.shrink();
    }

    final tone = AiStatusMapper.tone(status);
    final color = AiStatusMapper.toneToColor(tone, context);
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final reduceMotion = context.reduceMotion;
    final elapsedLabel = _elapsedLabel(widget.startedAtEpochMs);

    final trimmedDetails = widget.details?.trim();
    final hasDetails = trimmedDetails != null && trimmedDetails.isNotEmpty;
    final label = AiStatusMapper.label(status);
    final startColor = isDark
        ? Color.alphaBlend(
            color.withValues(alpha: 0.16),
            DS.surfaceSecondary,
          )
        : Color.alphaBlend(
            color.withValues(alpha: 0.08),
            DS.surfacePrimary,
          );
    final endColor = isDark
        ? Color.alphaBlend(
            DS.surfaceOverlay.withValues(alpha: 0.94),
            DS.surfaceSecondary,
          )
        : DS.surfaceSecondary;
    final cardBackground = LinearGradient(
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
      colors: [startColor, endColor],
    );
    final detailsBackground = isDark
        ? Colors.white.withValues(alpha: 0.04)
        : color.withValues(alpha: 0.06);
    final detailsColor = isDark ? DS.textSecondary : DS.textPrimary;

    final indicator = AnimatedContainer(
      duration: DS.motionDuration(
        SparkleMotionToken.standard,
        reduceMotion: reduceMotion,
      ),
      curve: DS.motionCurve(SparkleMotionToken.standard),
      padding: const EdgeInsets.symmetric(
        horizontal: 14,
        vertical: DS.spacing12,
      ),
      decoration: BoxDecoration(
        gradient: cardBackground,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: color.withValues(alpha: isDark ? 0.34 : 0.18),
        ),
        boxShadow: [
          BoxShadow(
            color: color.withValues(alpha: isDark ? 0.12 : 0.08),
            blurRadius: 18,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _StatusGlyph(
                color: color,
                icon: _statusIcon(status),
                reduceMotion: reduceMotion,
              ),
              const SizedBox(width: DS.spacing12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      label,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: context.sparkleTypography.labelLarge.copyWith(
                        color: DS.textPrimary,
                        fontWeight: DS.fontWeightBold,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      hasDetails ? '系统正在持续处理当前请求' : '实时思考中',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: context.sparkleTypography.labelSmall.copyWith(
                        color: DS.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
              if (elapsedLabel != null) ...[
                const SizedBox(width: DS.spacing10),
                _ElapsedBadge(
                  label: elapsedLabel,
                  color: color,
                ),
              ],
            ],
          ),
          if (hasDetails) ...[
            const SizedBox(height: DS.spacing10),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(
                horizontal: DS.spacing10,
                vertical: DS.spacing8,
              ),
              decoration: BoxDecoration(
                color: detailsBackground,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(
                  color: color.withValues(alpha: isDark ? 0.16 : 0.12),
                ),
              ),
              child: Text(
                trimmedDetails,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: DS.bodySmall.copyWith(
                  color: detailsColor,
                  height: 1.4,
                ),
              ),
            ),
          ],
        ],
      ),
    );

    final thinkingTrack = _bgmTrackForStatus(status);
    if (thinkingTrack == null) {
      return indicator;
    }
    return BgmScope(
      track: thinkingTrack,
      priority: BgmPriority.stage,
      child: indicator,
    );
  }

  String? _elapsedLabel(int? startedAtEpochMs) {
    if (startedAtEpochMs == null) return null;
    final elapsedMs =
        DateTime.now().millisecondsSinceEpoch - startedAtEpochMs;
    if (elapsedMs < 0) return null;
    final seconds = elapsedMs ~/ 1000;
    if (seconds < 60) {
      return '${seconds}s';
    }
    final minutes = seconds ~/ 60;
    final remainder = seconds % 60;
    return '${minutes}m ${remainder}s';
  }

  IconData _statusIcon(String status) {
    switch (status) {
      case 'THINKING':
        return Icons.psychology_alt_rounded;
      case 'GENERATING':
        return Icons.auto_awesome_rounded;
      case 'EXECUTING_TOOL':
        return Icons.construction_rounded;
      case 'SEARCHING':
        return Icons.travel_explore_rounded;
      case 'ANALYZING':
        return Icons.analytics_rounded;
      case 'PLANNING':
        return Icons.route_rounded;
      case 'REVIEWING':
        return Icons.fact_check_rounded;
      case 'WAITING':
        return Icons.hourglass_top_rounded;
      case 'ERROR':
        return Icons.error_outline_rounded;
      default:
        return Icons.bolt_rounded;
    }
  }

  BgmTrack? _bgmTrackForStatus(String status) {
    switch (status) {
      case 'THINKING':
      case 'ANALYZING':
      case 'PLANNING':
      case 'REVIEWING':
      case 'SEARCHING':
        return BgmTrack.thinking;
      default:
        return null;
    }
  }
}

/// AI 状态气泡（紧凑版，用于聊天气泡中）
class AiStatusBubble extends StatelessWidget {
  const AiStatusBubble({
    required this.status,
    super.key,
  });
  final String status;

  @override
  Widget build(BuildContext context) {
    final tone = AiStatusMapper.tone(status);
    final color = AiStatusMapper.toneToColor(tone, context);

    return AiStatusCapsule(
      label: AiStatusMapper.compactLabel(status),
      color: color,
      dense: true,
    );
  }
}

class _StatusGlyph extends StatelessWidget {
  const _StatusGlyph({
    required this.color,
    required this.icon,
    required this.reduceMotion,
  });

  final Color color;
  final IconData icon;
  final bool reduceMotion;

  @override
  Widget build(BuildContext context) {
    final pulseOn = reduceMotion
        ? false
        : (DateTime.now().millisecondsSinceEpoch ~/ 1000).isEven;

    return Container(
      width: 36,
      height: 36,
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: color.withValues(alpha: 0.18),
        ),
      ),
      child: Stack(
        alignment: Alignment.center,
        children: [
          AnimatedScale(
            scale: pulseOn ? 1 : 0.78,
            duration: reduceMotion
                ? Duration.zero
                : const Duration(milliseconds: 720),
            curve: Curves.easeOut,
            child: AnimatedOpacity(
              opacity: pulseOn ? 0.18 : 0.08,
              duration: reduceMotion
                  ? Duration.zero
                  : const Duration(milliseconds: 720),
              child: Container(
                width: 18,
                height: 18,
                decoration: BoxDecoration(
                  color: color,
                  shape: BoxShape.circle,
                ),
              ),
            ),
          ),
          Icon(
            icon,
            color: color,
            size: 18,
          ),
        ],
      ),
    );
  }
}

class _ElapsedBadge extends StatelessWidget {
  const _ElapsedBadge({
    required this.label,
    required this.color,
  });

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing10,
        vertical: DS.spacing6,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(
          color: color.withValues(alpha: 0.16),
        ),
      ),
      child: Text(
        label,
        style: context.sparkleTypography.labelSmall.copyWith(
          color: color,
          fontWeight: DS.fontWeightBold,
          fontFeatures: const [FontFeature.tabularFigures()],
        ),
      ),
    );
}
