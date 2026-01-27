import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/l10n/app_localizations.dart';

/// 计划编辑屏幕 - 占位页面
class PlanEditScreen extends StatelessWidget {
  const PlanEditScreen({required this.planId, super.key});
  final String planId;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
        appBar: AppBar(
          title: Text(l10n.editPlan),
          leading: IconButton(
            icon: const Icon(Icons.arrow_back),
            onPressed: () => context.pop(),
          ),
        ),
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.construction, size: 80, color: DS.brandPrimary),
              const SizedBox(height: DS.lg),
              Text(
                l10n.planEditInProgress,
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: DS.sm),
              Text(
                '${l10n.planId}: $planId',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: DS.sm),
              Text(
                l10n.featureInDevelopment,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: DS.xl),
              SparkleButton.primary(
                  label: l10n.back, onPressed: () => context.pop(),),
            ],
          ),
        ),
      );
  }
}
