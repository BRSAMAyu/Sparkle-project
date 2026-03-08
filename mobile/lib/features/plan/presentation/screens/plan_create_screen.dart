import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/l10n/app_localizations.dart';

/// 计划创建屏幕 - 占位页面
class PlanCreateScreen extends StatelessWidget {
  const PlanCreateScreen({super.key, this.planType});
  final String? planType;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    if (l10n == null) {
      return const SparklePageScaffold(
        role: SparklePageRole.content,
        child: Center(child: CircularProgressIndicator()),
      );
    }
    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        title: Text(planType == 'growth'
            ? l10n.createGrowthPlan
            : l10n.createSprintPlan),
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          size: DS.touchTargetMinSize,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      child: ContentConstraint(
        child: Center(
          child: GraphiteCardSurface(
            surfaceRole: SparkleSurfaceRole.card,
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.construction, size: 80, color: DS.brandPrimary),
                const SizedBox(height: DS.lg),
                Text(
                  l10n.featureComingSoon,
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const SizedBox(height: DS.sm),
                Text(
                  l10n.stayTuned,
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: DS.xl),
                SparkleButton.primary(
                  label: l10n.back,
                  onPressed: () => context.pop(),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
