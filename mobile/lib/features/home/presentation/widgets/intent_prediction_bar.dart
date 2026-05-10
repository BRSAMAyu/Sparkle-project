import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/dio_provider.dart';
import 'package:sparkle/features/focus/data/services/candidate_feedback_service.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/home/data/models/prediction_insight_data.dart';
import 'package:sparkle/features/home/presentation/providers/intent_prediction_provider.dart';

/// Intent prediction bar - Fixed above OmniBar
class IntentPredictionBar extends ConsumerStatefulWidget {
  const IntentPredictionBar({
    super.key,
    this.showIdle = true,
    this.chatStyle = false,
  });

  final bool showIdle;
  final bool chatStyle;

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
    _feedbackService = CandidateFeedbackService(
      ref.read(dioProvider),
      accessTokenGetter: ref.read(authRepositoryProvider).getAccessToken,
    );
  }

  @override
  Widget build(BuildContext context) {
    final brightness = Theme.of(context).brightness;
    final predictionState = ref.watch(intentPredictionProvider);
    final insight = predictionState.typingInsight;
    final predictions = predictionState.isTyping
        ? predictionState.typingPredictions
        : (widget.showIdle
            ? predictionState.idlePredictions
            : <PredictedAction>[]);

    if (predictions.isEmpty) {
      return const SizedBox.shrink();
    }
    _recordImpressionIfNeeded(insight);

    if (widget.chatStyle) {
      return _buildChatPredictionBar(
        context,
        brightness: brightness,
        insight: insight,
        predictions: predictions,
      );
    }

    return MaterialStyler(
      key: ValueKey('intent_prediction_bar_$brightness'),
      material: AppMaterials.neoGlass(context).copyWith(
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
            Row(
              children: [
                Icon(
                  Icons.auto_awesome_rounded,
                  size: 14,
                  color: DS.textSecondary,
                ),
                const SizedBox(width: DS.spacing6),
                Expanded(
                  child: Text(
                    insight.title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: context.sparkleTypography.labelSmall.copyWith(
                      color: DS.textSecondary,
                      fontWeight: DS.fontWeightBold,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: DS.spacing6),
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
            const SizedBox(height: DS.spacing6),
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

  Widget _buildChatPredictionBar(
    BuildContext context, {
    required Brightness brightness,
    required PredictionInsightData? insight,
    required List<PredictedAction> predictions,
  }) =>
      MaterialStyler(
      key: ValueKey('intent_prediction_chat_bar_$brightness'),
      material: AppMaterials.neoGlass(context).copyWith(
        backgroundColor: DS.surfacePanel.withValues(alpha: 0.74),
        borderColor: DS.borderSubtle.withValues(alpha: 0.72),
      ),
      borderRadius: DS.borderRadius16,
      padding: const EdgeInsets.all(DS.spacing12),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 24,
                height: 24,
                decoration: BoxDecoration(
                  color: DS.brandPrimary.withValues(alpha: 0.12),
                  borderRadius: DS.borderRadius8,
                ),
                child: Icon(
                  Icons.auto_awesome_rounded,
                  size: 14,
                  color: DS.brandPrimary,
                ),
              ),
              const SizedBox(width: DS.spacing8),
              Expanded(
                child: Text(
                  context.l10n.intentPredictionSuggested,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: context.sparkleTypography.labelSmall.copyWith(
                    color: DS.textPrimary,
                    fontWeight: DS.fontWeightBold,
                  ),
                ),
              ),
            ],
          ),
          if (insight != null) ...[
            const SizedBox(height: DS.spacing8),
            Text(
              insight.title,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: context.sparkleTypography.bodyMedium.copyWith(
                color: DS.textPrimary,
                fontWeight: DS.fontWeightMedium,
                height: 1.35,
              ),
            ),
          ],
          const SizedBox(height: DS.spacing10),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: predictions
                .take(3)
                .toList(growable: false)
                .asMap()
                .entries
                .map(
                  (entry) => _PredictionChip(
                    key: ValueKey('prediction_${entry.key}_$brightness'),
                    prediction: entry.value,
                    compact: true,
                  ),
                )
                .toList(),
          ),
          if (insight != null && insight.summary.isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            Text(
              insight.summary,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: context.sparkleTypography.labelSmall.copyWith(
                color: DS.textTertiary,
                height: 1.35,
              ),
            ),
          ],
        ],
      ),
    );

  void _recordImpressionIfNeeded(PredictionInsightData? insight) {
    if (insight == null) {
      return;
    }
    if (_lastImpressionPredictionId == insight.predictionId) {
      return;
    }
    _lastImpressionPredictionId = insight.predictionId;
    unawaited(
      _feedbackService.recordFeedback(
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
      ),
    );
  }
}

class _PredictionChip extends StatelessWidget {
  const _PredictionChip({
    required this.prediction,
    super.key,
    this.compact = false,
  });

  final PredictedAction prediction;
  final bool compact;

  @override
  Widget build(BuildContext context) => Tooltip(
        message: prediction.reason ?? prediction.label,
        child: InkWell(
          onTap: prediction.action,
          borderRadius: compact ? DS.borderRadius12 : DS.borderRadiusFull,
          child: Container(
            padding: EdgeInsets.symmetric(
              horizontal: compact ? DS.spacing10 : DS.spacing12,
              vertical: compact ? DS.spacing6 : DS.spacing4,
            ),
            decoration: BoxDecoration(
              color: compact
                  ? (prediction.color?.withValues(alpha: 0.12) ??
                      DS.brandPrimary.withValues(alpha: 0.08))
                  : (prediction.color?.withValues(alpha: 0.15) ??
                      DS.brandPrimary.withValues(alpha: 0.1)),
              borderRadius: compact ? DS.borderRadius12 : DS.borderRadiusFull,
              border: Border.all(
                color: compact
                    ? (prediction.color?.withValues(alpha: 0.2) ??
                        DS.brandPrimary.withValues(alpha: 0.16))
                    : (prediction.color?.withValues(alpha: 0.3) ??
                        DS.brandPrimary.withValues(alpha: 0.2)),
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
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: context.sparkleTypography.labelSmall.copyWith(
                    color: prediction.color ?? DS.brandPrimary,
                    fontWeight: DS.fontWeightMedium,
                  ),
                ),
              ],
            ),
          ),
        ),
      );
}
