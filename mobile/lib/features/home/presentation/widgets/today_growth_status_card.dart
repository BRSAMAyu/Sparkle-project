import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:sparkle/features/home/presentation/providers/home_growth_provider.dart';

class TodayGrowthStatusCard extends StatelessWidget {
  const TodayGrowthStatusCard({
    super.key,
    this.state,
    this.isLoading = false,
    this.onCreatePlan,
  });

  final HomeGrowthState? state;
  final bool isLoading;
  final VoidCallback? onCreatePlan;

  @override
  Widget build(BuildContext context) {
    if (isLoading || state == null) {
      return _GrowthStatusFrame(
        key: const ValueKey('today-growth-status-skeleton'),
        accentColor: DS.brandPrimary,
        child: const _GrowthStatusSkeleton(),
      );
    }

    final growthState = state!;
    if (!growthState.hasActivePlan) {
      return _GrowthStatusFrame(
        key: const ValueKey('today-growth-status-empty-plan'),
        accentColor: DS.brandPrimary,
        child: _NoActivePlanContent(onCreatePlan: onCreatePlan),
      );
    }

    final tone = _GrowthTone.resolve(growthState);
    final completionRate = growthState.completionRate;
    final taskLabel =
        '今天 ${growthState.tasksCompleted}/${growthState.tasksTotal} 项任务';
    final phaseLabel = growthState.activePlan?.phaseLabel ?? '进行中';

    return _GrowthStatusFrame(
      key: const ValueKey('today-growth-status-card'),
      accentColor: tone.color,
      child: ConstrainedBox(
        constraints: const BoxConstraints(minHeight: 126),
        child: Row(
          children: [
            _ProgressRing(
              progress: completionRate,
              color: tone.color,
            ),
            const SizedBox(width: DS.spacing16),
            Expanded(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    taskLabel,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: context.sparkleTypography.titleLarge.copyWith(
                      color: DS.textPrimary,
                      fontWeight: DS.fontWeightBold,
                    ),
                  ),
                  const SizedBox(height: DS.spacing8),
                  Text(
                    '计划健康度 ${_healthDots(growthState.planHealth)}',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: context.sparkleTypography.bodyMedium.copyWith(
                      color: DS.textSecondary,
                      height: 1.25,
                    ),
                  ),
                  const SizedBox(height: DS.spacing4),
                  Text(
                    '连续学习 ${growthState.streak} 天 🔥',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: context.sparkleTypography.bodyMedium.copyWith(
                      color: DS.textSecondary,
                      height: 1.25,
                    ),
                  ),
                  const SizedBox(height: DS.spacing10),
                  Text(
                    tone.message(growthState.nextAction),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: context.sparkleTypography.bodySmall.copyWith(
                      color: tone.color,
                      fontWeight: DS.fontWeightBold,
                      height: 1.3,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: DS.spacing10),
            _PhasePill(label: phaseLabel, accentColor: tone.color),
          ],
        ),
      ),
    );
  }
}

class _GrowthStatusFrame extends StatelessWidget {
  const _GrowthStatusFrame({
    required this.child,
    required this.accentColor,
    super.key,
  });

  final Widget child;
  final Color accentColor;

  @override
  Widget build(BuildContext context) => ContentConstraint(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(
            DS.spacing16,
            DS.spacing8,
            DS.spacing16,
            DS.spacing8,
          ),
          child: MaterialStyler(
            material: AppMaterials.ceramic(context).copyWith(
              backgroundGradient: LinearGradient(
                colors: [
                  accentColor.withValues(alpha: 0.14),
                  DS.surfacePrimaryElevated,
                  DS.surfaceSecondary,
                ],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderColor: accentColor.withValues(alpha: 0.2),
              borderWidth: 1,
              shadows: [
                BoxShadow(
                  color: accentColor.withValues(alpha: 0.08),
                  blurRadius: 24,
                  offset: const Offset(0, 12),
                ),
              ],
            ),
            borderRadius: DS.borderRadius20,
            padding: const EdgeInsets.all(DS.spacing18),
            child: child,
          ),
        ),
      );
}

class _GrowthStatusSkeleton extends StatelessWidget {
  const _GrowthStatusSkeleton();

  @override
  Widget build(BuildContext context) => ConstrainedBox(
        constraints: const BoxConstraints(minHeight: 126),
        child: const Row(
          children: [
            SparkleSkeleton(width: 64, height: 64, borderRadius: 999),
            SizedBox(width: DS.spacing16),
            Expanded(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SparkleSkeleton(width: 160, height: 22, borderRadius: 10),
                  SizedBox(height: DS.spacing12),
                  SparkleSkeleton(height: 14),
                  SizedBox(height: DS.spacing8),
                  SparkleSkeleton(width: 180, height: 14),
                  SizedBox(height: DS.spacing12),
                  SparkleSkeleton(width: 220, height: 14),
                ],
              ),
            ),
          ],
        ),
      );
}

class _NoActivePlanContent extends StatelessWidget {
  const _NoActivePlanContent({this.onCreatePlan});

  final VoidCallback? onCreatePlan;

  @override
  Widget build(BuildContext context) => ConstrainedBox(
        constraints: const BoxConstraints(minHeight: 126),
        child: Row(
          children: [
            Container(
              width: 64,
              height: 64,
              decoration: BoxDecoration(
                color: DS.brandPrimary.withValues(alpha: 0.12),
                borderRadius: DS.borderRadiusFull,
                border: Border.all(
                  color: DS.brandPrimary.withValues(alpha: 0.18),
                ),
              ),
              child: Icon(
                Icons.auto_awesome_rounded,
                color: DS.brandPrimary,
                size: 28,
              ),
            ),
            const SizedBox(width: DS.spacing16),
            Expanded(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '开始制定你的第一个计划',
                    style: context.sparkleTypography.titleLarge.copyWith(
                      color: DS.textPrimary,
                      fontWeight: DS.fontWeightBold,
                    ),
                  ),
                  const SizedBox(height: DS.spacing6),
                  Text(
                    '我会把目标拆成今天就能迈出的一小步。',
                    style: context.sparkleTypography.bodySmall.copyWith(
                      color: DS.textSecondary,
                      height: 1.35,
                    ),
                  ),
                  const SizedBox(height: DS.spacing12),
                  SparkleButton(
                    label: '开始制定你的第一个计划',
                    size: ButtonSize.small,
                    icon: const Icon(Icons.add_rounded),
                    onPressed: onCreatePlan,
                    disabled: onCreatePlan == null,
                  ),
                ],
              ),
            ),
          ],
        ),
      );
}

class _ProgressRing extends StatelessWidget {
  const _ProgressRing({
    required this.progress,
    required this.color,
  });

  final double progress;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final clampedProgress = progress.clamp(0, 1).toDouble();
    final percent = (clampedProgress * 100).round();
    return SizedBox(
      width: 66,
      height: 66,
      child: Stack(
        alignment: Alignment.center,
        children: [
          SizedBox(
            width: 62,
            height: 62,
            child: CircularProgressIndicator(
              key: const ValueKey('today-growth-progress'),
              value: clampedProgress,
              strokeWidth: 7,
              strokeCap: StrokeCap.round,
              backgroundColor: color.withValues(alpha: 0.16),
              valueColor: AlwaysStoppedAnimation<Color>(color),
            ),
          ),
          Text(
            '$percent%',
            style: context.sparkleTypography.labelLarge.copyWith(
              color: DS.textPrimary,
              fontWeight: DS.fontWeightBold,
            ),
          ),
        ],
      ),
    );
  }
}

class _PhasePill extends StatelessWidget {
  const _PhasePill({
    required this.label,
    required this.accentColor,
  });

  final String label;
  final Color accentColor;

  @override
  Widget build(BuildContext context) => ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 108),
        child: Container(
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing10,
            vertical: DS.spacing8,
          ),
          decoration: BoxDecoration(
            color: accentColor.withValues(alpha: 0.12),
            borderRadius: DS.borderRadiusFull,
            border: Border.all(color: accentColor.withValues(alpha: 0.2)),
          ),
          child: Text(
            label,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            textAlign: TextAlign.center,
            style: context.sparkleTypography.labelSmall.copyWith(
              color: accentColor,
              fontWeight: DS.fontWeightBold,
              height: 1.2,
            ),
          ),
        ),
      );
}

class _GrowthTone {
  const _GrowthTone({
    required this.color,
    required this.messageBuilder,
  });

  final Color color;
  final String Function(HomeGrowthTask? nextAction) messageBuilder;

  String message(HomeGrowthTask? nextAction) => messageBuilder(nextAction);

  static _GrowthTone resolve(HomeGrowthState state) {
    if (state.tasksTotal > 0 && state.tasksCompleted >= state.tasksTotal) {
      return _GrowthTone(
        color: DS.success,
        messageBuilder: (_) => '今天收束得很漂亮，可以带着成就感收尾。',
      );
    }
    if (state.tasksCompleted > 0) {
      return _GrowthTone(
        color: DS.info,
        messageBuilder: (_) => '保持这个节奏，下一步已经很清楚。',
      );
    }
    return _GrowthTone(
      color: DS.warning,
      messageBuilder: (nextAction) {
        final title = nextAction?.title.trim();
        if (title == null || title.isEmpty) {
          return '今天的第一件事是选一个轻量任务。';
        }
        return '今天的第一件事是$title。';
      },
    );
  }
}

String _healthDots(double healthScore) {
  final filled = healthScore <= 0 ? 0 : (healthScore.clamp(0, 1) * 5).ceil();
  return List<String>.generate(5, (index) => index < filled ? '●' : '○').join();
}
