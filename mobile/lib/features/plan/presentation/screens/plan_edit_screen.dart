import 'package:flutter/material.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/features/plan/presentation/screens/plan_create_screen.dart';

class PlanEditScreen extends ConsumerWidget {
  const PlanEditScreen({required this.planId, super.key});

  final String planId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final planAsync = ref.watch(planDetailProvider(planId));

    return planAsync.when(
      data: (plan) => PlanCreateScreen(
        initialPlan: plan,
        editingPlanId: planId,
      ),
      loading: () => const SparklePageScaffold(
        role: SparklePageRole.content,
        child: Center(
          child: CircularProgressIndicator(),
        ),
      ),
      error: (error, _) => SparklePageScaffold(
        role: SparklePageRole.content,
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(DS.spacing24),
            child: Text(
              '计划加载失败：$error',
              style: DS.bodyMedium.copyWith(color: DS.textSecondary),
              textAlign: TextAlign.center,
            ),
          ),
        ),
      ),
    );
  }
}
