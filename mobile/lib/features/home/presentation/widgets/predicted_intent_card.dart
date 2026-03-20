import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_provider.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';

class PredictedIntentCard extends ConsumerWidget {
  const PredictedIntentCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final forecast = ref.watch(dashboardProvider).nextIntentForecast;
    if (forecast == null || forecast.title.isEmpty || forecast.summary.isEmpty) {
      return const SizedBox.shrink();
    }

    final confidencePercent = (forecast.confidence * 100).round();
    final sourceLabel = switch (forecast.predictionSource) {
      'glm_batch' => '长期预测',
      'rules' => '规则兜底',
      _ => forecast.predictionSource,
    };

    return ContentConstraint(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
        child: MaterialStyler(
          material: AppMaterials.ceramic.copyWith(
            backgroundGradient: LinearGradient(
              colors: [
                DS.info.withValues(alpha: 0.12),
                DS.brandPrimary.withValues(alpha: 0.06),
                DS.surfaceSecondary,
              ],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderColor: DS.info.withValues(alpha: 0.18),
            borderWidth: 1,
          ),
          borderRadius: DS.borderRadius20,
          padding: const EdgeInsets.all(DS.spacing16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    width: 36,
                    height: 36,
                    decoration: BoxDecoration(
                      color: DS.info.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Icon(
                      Icons.psychology_alt_rounded,
                      color: DS.info,
                      size: 18,
                    ),
                  ),
                  const SizedBox(width: DS.spacing12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '系统预测',
                          style: context.sparkleTypography.labelLarge.copyWith(
                            fontWeight: DS.fontWeightBold,
                          ),
                        ),
                        Text(
                          '基于画像、最近 24 小时行为与任务节奏',
                          style: context.sparkleTypography.labelSmall.copyWith(
                            color: DS.textSecondary,
                          ),
                        ),
                      ],
                    ),
                  ),
                  _Chip(label: '$confidencePercent%'),
                ],
              ),
              const SizedBox(height: DS.spacing12),
              Text(
                forecast.title,
                style: context.sparkleTypography.titleLarge.copyWith(
                  fontWeight: DS.fontWeightBold,
                ),
              ),
              const SizedBox(height: DS.spacing8),
              Text(
                forecast.summary,
                style: context.sparkleTypography.bodyMedium.copyWith(
                  color: DS.textSecondary,
                  height: 1.45,
                ),
              ),
              if (forecast.reasons.isNotEmpty) ...[
                const SizedBox(height: DS.spacing12),
                Wrap(
                  spacing: DS.spacing8,
                  runSpacing: DS.spacing8,
                  children: forecast.reasons.take(2).map((reason) {
                    return _Chip(
                      label: reason,
                      subdued: true,
                    );
                  }).toList(),
                ),
              ],
              const SizedBox(height: DS.spacing12),
              Row(
                children: [
                  Expanded(
                    child: SparkleButton(
                      label: '按这个继续',
                      icon: const Icon(Icons.auto_awesome_rounded),
                      onPressed: () async {
                        final prompt = forecast.suggestedPrompt.trim();
                        if (prompt.isEmpty) return;
                        if (context.mounted) {
                          context.go('/chat');
                        }
                        await Future<void>.delayed(
                          const Duration(milliseconds: 250),
                        );
                        await ref.read(chatProvider.notifier).sendMessage(prompt);
                      },
                    ),
                  ),
                  const SizedBox(width: DS.spacing8),
                  _Chip(
                    label: '${forecast.predictedWindow} · $sourceLabel',
                    subdued: true,
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Chip extends StatelessWidget {
  const _Chip({
    required this.label,
    this.subdued = false,
  });

  final String label;
  final bool subdued;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing8,
        vertical: DS.spacing6,
      ),
      decoration: BoxDecoration(
        color: subdued ? DS.surfaceOverlay : DS.info.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(
          color: subdued ? DS.borderSubtle : DS.info.withValues(alpha: 0.18),
        ),
      ),
      child: Text(
        label,
        style: context.sparkleTypography.labelSmall.copyWith(
          color: subdued ? DS.textSecondary : DS.info,
          fontWeight: DS.fontWeightBold,
        ),
      ),
    );
  }
}
