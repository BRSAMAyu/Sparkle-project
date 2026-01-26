import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/home/presentation/providers/intent_prediction_provider.dart';

/// Intent prediction bar - Fixed above OmniBar
class IntentPredictionBar extends ConsumerWidget {
  const IntentPredictionBar({
    super.key,
    this.showIdle = true,
  });

  final bool showIdle;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final predictionState = ref.watch(intentPredictionProvider);
    final predictions = predictionState.isTyping
        ? predictionState.typingPredictions
        : (showIdle ? predictionState.idlePredictions : <PredictedAction>[]);

    if (predictions.isEmpty) {
      return const SizedBox.shrink();
    }

    return MaterialStyler(
      material: AppMaterials.neoGlass.copyWith(
        backgroundColor: DS.surfacePrimary.withValues(alpha: 0.8),
      ),
      borderRadius: DS.borderRadiusFull,
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing12,
        vertical: DS.spacing6,
      ),
      child: SizedBox(
        height: 36,
        child: ListView.separated(
          scrollDirection: Axis.horizontal,
          itemCount: predictions.length,
          separatorBuilder: (context, index) =>
              const SizedBox(width: DS.spacing8),
          itemBuilder: (context, index) {
            final prediction = predictions[index];
            return _PredictionChip(prediction: prediction);
          },
        ),
      ),
    );
  }
}

class _PredictionChip extends StatelessWidget {
  const _PredictionChip({required this.prediction});

  final PredictedAction prediction;

  @override
  Widget build(BuildContext context) => InkWell(
      onTap: prediction.action,
      borderRadius: DS.borderRadiusFull,
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing12,
          vertical: DS.spacing4,
        ),
        decoration: BoxDecoration(
          color: prediction.color?.withValues(alpha: 0.15) ??
              DS.brandPrimary.withValues(alpha: 0.1),
          borderRadius: DS.borderRadiusFull,
          border: Border.all(
            color: prediction.color?.withValues(alpha: 0.3) ??
                DS.brandPrimary.withValues(alpha: 0.2),
            width: 1,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              prediction.icon,
              size: DS.iconSizeXs,
              color: prediction.color ?? DS.brandPrimary,
            ),
            const SizedBox(width: DS.spacing6),
            Text(
              prediction.label,
              style: context.sparkleTypography.labelSmall.copyWith(
                color: prediction.color ?? DS.brandPrimary,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
}
