import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/dio_provider.dart';
import 'package:sparkle/features/focus/data/services/candidate_feedback_service.dart';
import 'package:sparkle/features/home/data/models/prediction_insight_data.dart';
import 'package:sparkle/features/home/presentation/providers/intent_prediction_provider.dart';

/// Intent prediction bar - Fixed above OmniBar
class IntentPredictionBar extends ConsumerStatefulWidget {
  const IntentPredictionBar({
    super.key,
    this.showIdle = true,
  });

  final bool showIdle;

  @override
  ConsumerState<IntentPredictionBar> createState() =>
      _IntentPredictionBarState();
}

class _IntentPredictionBarState extends ConsumerState<IntentPredictionBar> {
  late final CandidateFeedbackService _feedbackService;
  String? _lastImpressionPredictionId;

  @override
  void initState() {
    super.initState();
    _feedbackService = CandidateFeedbackService(ref.read(dioProvider));
  }

  @override
  Widget build(BuildContext context) {
    final brightness = Theme.of(context).brightness;
    final predictionState = ref.watch(intentPredictionProvider);
    final insight = predictionState.typingInsight;
    final predictions = predictionState.isTyping
        ? predictionState.typingPredictions
        : (widget.showIdle ? predictionState.idlePredictions : <PredictedAction>[]);

    if (predictions.isEmpty) {
      return const SizedBox.shrink();
    }
    _recordImpressionIfNeeded(insight);

    return MaterialStyler(
      key: ValueKey('intent_prediction_bar_$brightness'),
      material: AppMaterials.neoGlass.copyWith(
        backgroundColor: DS.surfacePrimary.withValues(alpha: 0.8),
      ),
      borderRadius: DS.borderRadiusFull,
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing12,
        vertical: DS.spacing6,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (insight != null) ...[
            Text(
              insight.title,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: context.sparkleTypography.labelSmall.copyWith(
                color: DS.textSecondary,
                fontWeight: DS.fontWeightBold,
              ),
            ),
            const SizedBox(height: DS.spacing4),
          ],
          SizedBox(
            height: 36,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              itemCount: predictions.length,
              separatorBuilder: (context, index) =>
                  const SizedBox(width: DS.spacing8),
              itemBuilder: (context, index) {
                final prediction = predictions[index];
                return _PredictionChip(
                  key: ValueKey('prediction_${index}_$brightness'),
                  prediction: prediction,
                );
              },
            ),
          ),
          if (insight != null && insight.summary.isNotEmpty) ...[
            const SizedBox(height: DS.spacing4),
            Text(
              insight.summary,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: context.sparkleTypography.labelSmall.copyWith(
                color: DS.textTertiary,
              ),
            ),
          ],
        ],
      ),
    );
  }

  void _recordImpressionIfNeeded(PredictionInsightData? insight) {
    if (insight == null) {
      return;
    }
    if (_lastImpressionPredictionId == insight.predictionId) {
      return;
    }
    _lastImpressionPredictionId = insight.predictionId;
    unawaited(_feedbackService.recordFeedback(
      candidateId: insight.trackingCandidateId,
      actionType: insight.trackingActionType,
      feedbackType: 'impression',
      contextSnapshot: {
        'prediction': {
          'prediction_id': insight.predictionId,
          'horizon': insight.horizon,
          'surface': insight.surface ?? 'chat_input',
          'source': insight.predictionSource,
          'tier': insight.predictionTier,
          'action_type': insight.predictedActionType,
        },
      },
    ));
  }
}

class _PredictionChip extends StatelessWidget {
  const _PredictionChip({
    required this.prediction,
    super.key,
  });

  final PredictedAction prediction;

  @override
  Widget build(BuildContext context) => Tooltip(
        message: prediction.reason ?? prediction.label,
        child: InkWell(
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
        ),
      );
}
