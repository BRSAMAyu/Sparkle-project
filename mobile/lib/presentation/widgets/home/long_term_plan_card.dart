import 'dart:ui';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/presentation/providers/dashboard_provider.dart';

class LongTermPlanCard extends ConsumerWidget {
  const LongTermPlanCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dashboardState = ref.watch(dashboardProvider);
    final growth = dashboardState.growth;

    return GestureDetector(
      onTap: () => context.push('/growth'),
      child: ClipRRect(
        borderRadius: AppDesignTokens.borderRadius20,
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
          child: Container(
            decoration: BoxDecoration(
              color: AppDesignTokens.glassBackground,
              borderRadius: AppDesignTokens.borderRadius20,
              border: Border.all(color: AppDesignTokens.glassBorder),
            ),
            padding: const EdgeInsets.all(DS.lg),
            child: growth != null ? _buildContent(context, growth) : _buildEmptyState(context),
          ),
        ),
      ),
    );
  }

  Widget _buildContent(BuildContext context, GrowthData growth) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              '长期计划',
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w500,
                color: DS.brandPrimary70,
              ),
            ),
            Icon(Icons.spa_rounded, color: AppDesignTokens.success, size: 16),
          ],
        ),
        
        const Spacer(),
        
        Center(
          child: Column(
            children: [
              Text(
                '${(growth.progress * 100).toInt()}%',
                style: const TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                  color: AppDesignTokens.success,
                ),
              ),
              const SizedBox(height: DS.xs),
              SizedBox(
                height: 4,
                width: 60,
                child: LinearProgressIndicator(
                  value: growth.progress,
                  backgroundColor: DS.brandPrimary10,
                  valueColor: const AlwaysStoppedAnimation<Color>(AppDesignTokens.success),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ],
          ),
        ),

        const Spacer(),

        Text(
          growth.name,
          style: const TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w600,
            color: DS.brandPrimary,
          ),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
        const SizedBox(height: 2),
        Text(
          'Mastery: ${(growth.masteryLevel * 100).toInt()}%',
          style: TextStyle(
            fontSize: 10,
            color: DS.brandPrimary.withValues(alpha: 0.5),
          ),
        ),
      ],
    );
  }

  Widget _buildEmptyState(BuildContext context) {
    return const Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Icon(Icons.add_circle_outline, color: DS.brandPrimary30, size: 32),
        SizedBox(height: DS.sm),
        Text(
          '创建长期计划',
          style: TextStyle(fontSize: 12, color: DS.brandPrimary54),
        ),
      ],
    );
  }
}
