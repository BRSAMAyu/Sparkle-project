import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/dio_provider.dart';
import 'package:sparkle/core/services/app_event_stream_service.dart';
import 'package:sparkle/core/services/prediction_attribution_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_provider.dart';
import 'package:sparkle/features/focus/data/services/candidate_feedback_service.dart';
import 'package:sparkle/features/home/data/models/prediction_insight_data.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';

class PredictedIntentCard extends ConsumerStatefulWidget {
  const PredictedIntentCard({super.key});

  @override
  ConsumerState<PredictedIntentCard> createState() =>
      _PredictedIntentCardState();
}

class _PredictedIntentCardState extends ConsumerState<PredictedIntentCard> {
  bool _isContinuing = false;
  late final CandidateFeedbackService _feedbackService;
  late final AppEventStreamService _eventStream;
  late final PredictionAttributionService _predictionAttribution;
  String? _lastImpressionPredictionId;

  @override
  void initState() {
    super.initState();
    _feedbackService = CandidateFeedbackService(ref.read(dioProvider));
    _eventStream = ref.read(appEventStreamServiceProvider);
    _predictionAttribution = ref.read(predictionAttributionServiceProvider);
  }

  @override
  Widget build(BuildContext context) {
    final forecast = ref.watch(dashboardProvider).nextIntentForecast;
    if (forecast == null ||
        forecast.title.isEmpty ||
        forecast.summary.isEmpty) {
      return const SizedBox.shrink();
    }
    _recordImpressionIfNeeded(forecast);

    final confidencePercent = (forecast.confidence * 100).round();
    final sourceLabel = switch (forecast.predictionSource) {
      'glm_batch' => '长期预测',
      'rules' => '规则兜底',
      _ => forecast.predictionSource,
    };
    final windowLabel = _windowLabel(forecast.predictedWindow);
    final actionLabel = _actionLabel(forecast.predictedActionType);
    final freshnessLabel = _freshnessLabel(forecast.generatedAt);
    final primaryAction = forecast.recommendedActions.isNotEmpty
        ? forecast.recommendedActions.first
        : null;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final promptPreview = forecast.suggestedPrompt.trim();
    final gradientStart = isDark
        ? Color.alphaBlend(
            DS.info.withValues(alpha: 0.16),
            DS.surfaceSecondary,
          )
        : DS.info.withValues(alpha: 0.1);
    final gradientMid = isDark
        ? Color.alphaBlend(
            DS.brandPrimary.withValues(alpha: 0.12),
            DS.surfaceSecondary,
          )
        : DS.brandPrimary.withValues(alpha: 0.05);
    final gradientEnd = isDark ? DS.surfaceOverlay : DS.surfaceSecondary;

    return ContentConstraint(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
        child: MaterialStyler(
          material: AppMaterials.ceramic.copyWith(
            backgroundGradient: LinearGradient(
              colors: [gradientStart, gradientMid, gradientEnd],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderColor: DS.info.withValues(alpha: isDark ? 0.22 : 0.16),
            borderWidth: 1,
            shadows: [
              BoxShadow(
                color: DS.info.withValues(alpha: isDark ? 0.12 : 0.06),
                blurRadius: 20,
                offset: const Offset(0, 10),
              ),
            ],
          ),
          borderRadius: DS.borderRadius20,
          padding: const EdgeInsets.all(DS.spacing16),
          child: Stack(
            children: [
              Positioned(
                right: -10,
                top: -12,
                child: IgnorePointer(
                  child: Container(
                    width: 96,
                    height: 96,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: RadialGradient(
                        colors: [
                          DS.info.withValues(alpha: isDark ? 0.14 : 0.12),
                          Colors.transparent,
                        ],
                      ),
                    ),
                  ),
                ),
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        width: 40,
                        height: 40,
                        decoration: BoxDecoration(
                          color: DS.info.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(
                            color: DS.info.withValues(alpha: 0.16),
                          ),
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
                              style:
                                  context.sparkleTypography.labelLarge.copyWith(
                                fontWeight: DS.fontWeightBold,
                              ),
                            ),
                            Text(
                              '基于画像、最近 24 小时行为与任务节奏',
                              style:
                                  context.sparkleTypography.labelSmall.copyWith(
                                color: DS.textSecondary,
                              ),
                            ),
                          ],
                        ),
                      ),
                      _Chip(label: '$confidencePercent%'),
                    ],
                  ),
                  const SizedBox(height: 14),
                  Text(
                    forecast.title,
                    style: context.sparkleTypography.titleLarge.copyWith(
                      fontWeight: DS.fontWeightBold,
                      height: 1.15,
                    ),
                  ),
                  const SizedBox(height: DS.spacing8),
                  Text(
                    forecast.summary,
                    style: context.sparkleTypography.bodyMedium.copyWith(
                      color: DS.textSecondary,
                      height: 1.5,
                    ),
                  ),
                  const SizedBox(height: DS.spacing12),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(DS.spacing12),
                    decoration: BoxDecoration(
                      color: isDark
                          ? Colors.white.withValues(alpha: 0.04)
                          : DS.surfaceOverlay,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(
                        color: DS.borderSubtle,
                      ),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '建议接续',
                          style: context.sparkleTypography.labelSmall.copyWith(
                            color: DS.textTertiary,
                            fontWeight: DS.fontWeightBold,
                          ),
                        ),
                        const SizedBox(height: DS.spacing6),
                        Text(
                          promptPreview.isEmpty
                              ? '预测结果已生成，等待可继续指令'
                              : promptPreview,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: context.sparkleTypography.bodyMedium.copyWith(
                            color: DS.textPrimary,
                            height: 1.45,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: DS.spacing12),
                  Row(
                    children: [
                      Expanded(
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(999),
                          child: LinearProgressIndicator(
                            minHeight: 6,
                            value: forecast.confidence.clamp(0.0, 1.0),
                            backgroundColor: DS.surfaceTertiary,
                            valueColor: AlwaysStoppedAnimation<Color>(DS.info),
                          ),
                        ),
                      ),
                      const SizedBox(width: DS.spacing10),
                      Text(
                        '可信度 $confidencePercent%',
                        style: context.sparkleTypography.labelSmall.copyWith(
                          color: DS.textSecondary,
                          fontWeight: DS.fontWeightBold,
                        ),
                      ),
                    ],
                  ),
                  if (forecast.reasons.isNotEmpty) ...[
                    const SizedBox(height: DS.spacing12),
                    Wrap(
                      spacing: DS.spacing8,
                      runSpacing: DS.spacing8,
                      children: forecast.reasons
                          .take(3)
                          .map(
                            (reason) => _Chip(
                              label: reason,
                              subdued: true,
                            ),
                          )
                          .toList(),
                    ),
                  ],
                  if (forecast.allExplanationLines.isNotEmpty) ...[
                    const SizedBox(height: DS.spacing12),
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(DS.spacing12),
                      decoration: BoxDecoration(
                        color: isDark
                            ? Colors.white.withValues(alpha: 0.03)
                            : DS.surfaceSecondary,
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '为什么这样预测',
                            style:
                                context.sparkleTypography.labelSmall.copyWith(
                              color: DS.textTertiary,
                              fontWeight: DS.fontWeightBold,
                            ),
                          ),
                          const SizedBox(height: DS.spacing6),
                          ...forecast.allExplanationLines.take(3).map(
                                (line) => Padding(
                                  padding: const EdgeInsets.only(bottom: 4),
                                  child: Text(
                                    '• $line',
                                    style: context.sparkleTypography.bodyMedium
                                        .copyWith(
                                      color: DS.textSecondary,
                                      height: 1.45,
                                    ),
                                  ),
                                ),
                              ),
                        ],
                      ),
                    ),
                  ],
                  const SizedBox(height: 14),
                  SparkleButton(
                    label: _isContinuing
                        ? '正在衔接…'
                        : ((primaryAction?.label.isNotEmpty ?? false)
                            ? primaryAction!.label
                            : '按这个继续'),
                    icon: Icon(
                      _isContinuing
                          ? Icons.sync_rounded
                          : Icons.auto_awesome_rounded,
                    ),
                    loading: _isContinuing,
                    expand: true,
                    disabled: _isContinuing ||
                        (promptPreview.isEmpty && primaryAction == null),
                    onPressed: _isContinuing ||
                            (promptPreview.isEmpty && primaryAction == null)
                        ? null
                        : () => _handleContinue(forecast),
                  ),
                  const SizedBox(height: DS.spacing10),
                  Wrap(
                    spacing: DS.spacing8,
                    runSpacing: DS.spacing8,
                    children: [
                      _Chip(label: actionLabel, subdued: true),
                      _Chip(label: windowLabel, subdued: true),
                      _Chip(label: sourceLabel, subdued: true),
                      if (freshnessLabel != null)
                        _Chip(label: freshnessLabel, subdued: true),
                    ],
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _recordImpressionIfNeeded(PredictionInsightData forecast) {
    if (_lastImpressionPredictionId == forecast.predictionId) {
      return;
    }
    _lastImpressionPredictionId = forecast.predictionId;
    unawaited(_feedbackService.recordFeedback(
      candidateId: forecast.trackingCandidateId,
      actionType: forecast.trackingActionType,
      feedbackType: 'impression',
      contextSnapshot: _feedbackContext(forecast),
    ));
    unawaited(_eventStream.recordPredictionFeedback(
      predictionId: forecast.predictionId,
      feedbackType: 'impression',
      actionType: forecast.trackingActionType,
      surface: forecast.surface ?? 'dashboard',
      suggestedPrompt: forecast.suggestedPrompt,
      entityType: forecast.entityCard?.entityType,
      entityId: forecast.entityCard?.entityId,
    ));
  }

  Future<void> _handleContinue(PredictionInsightData forecast) async {
    if (_isContinuing) {
      return;
    }
    final primaryAction = forecast.recommendedActions.isNotEmpty
        ? forecast.recommendedActions.first
        : null;
    final prompt =
        (primaryAction?.suggestedPrompt ?? forecast.suggestedPrompt).trim();

    final chatNotifier = ref.read(chatProvider.notifier);
    setState(() {
      _isContinuing = true;
    });

    try {
      _feedbackService.recordFeedback(
        candidateId: forecast.trackingCandidateId,
        actionType: forecast.trackingActionType,
        feedbackType: 'accept',
        contextSnapshot: _feedbackContext(forecast),
      );
      unawaited(_eventStream.recordPredictionFeedback(
        predictionId: forecast.predictionId,
        feedbackType: 'accept',
        actionType: forecast.trackingActionType,
        surface: forecast.surface ?? 'dashboard',
        suggestedPrompt: prompt,
        entityType: forecast.entityCard?.entityType,
        entityId: forecast.entityCard?.entityId,
      ));
      unawaited(
        _predictionAttribution.rememberAcceptedPrediction(
          predictionId: forecast.predictionId,
          candidateId: forecast.trackingCandidateId,
          actionType: forecast.trackingActionType,
          surface: forecast.surface ?? 'dashboard',
          horizon: forecast.horizon,
          source: forecast.predictionSource,
          suggestedPrompt: prompt,
          entityType: forecast.entityCard?.entityType,
          entityId: forecast.entityCard?.entityId,
        ),
      );
      await SensoryFeedbackService.emit(SensoryFeedbackEvent.navigation);
      if (!mounted) return;
      final route = primaryAction?.targetRoute ?? '/chat';
      context.go(route);
      await Future<void>.delayed(const Duration(milliseconds: 280));
      if (route == '/chat' && prompt.isNotEmpty) {
        await chatNotifier.sendMessage(prompt);
      }
      ref.invalidate(dashboardProvider);
    } catch (_) {
      if (mounted) {
        AppFeedback.error(context, '继续对话时出现问题，请稍后重试');
      }
    } finally {
      if (mounted) {
        setState(() {
          _isContinuing = false;
        });
      }
    }
  }

  Map<String, dynamic> _feedbackContext(PredictionInsightData forecast) => {
        'prediction': {
          'prediction_id': forecast.predictionId,
          'horizon': forecast.horizon,
          'surface': forecast.surface ?? 'dashboard',
          'source': forecast.predictionSource,
          'tier': forecast.predictionTier,
          'action_type': forecast.predictedActionType,
        },
      };

  String _actionLabel(String actionType) {
    switch (actionType) {
      case 'resume_priority_task':
      case 'resume_task':
        return '继续重点任务';
      case 'study_plan':
        return '生成学习计划';
      case 'error_diagnosis':
        return '问题诊断';
      case 'create_task':
        return '落成任务';
      case 'translate':
        return '即时结果';
      case 'review_progress':
        return '复盘进展';
      case 'plan_next_step':
        return '规划下一步';
      case 'reflection':
        return '快速反思';
      default:
        return '预测意图';
    }
  }

  String _windowLabel(String window) {
    switch (window) {
      case 'now':
        return '就是现在';
      case 'next_30m':
        return '未来 30 分钟';
      case 'next_1h':
        return '未来 1 小时';
      case 'next_2h':
        return '未来 2 小时';
      case 'next_6h':
        return '未来 6 小时';
      case 'today':
        return '今天内';
      default:
        return window.replaceAll('_', ' ');
    }
  }

  String? _freshnessLabel(DateTime? generatedAt) {
    if (generatedAt == null) return null;
    final diff = DateTime.now().difference(generatedAt);
    if (diff.inMinutes < 1) {
      return '刚刚更新';
    }
    if (diff.inHours < 1) {
      return '${diff.inMinutes} 分钟前';
    }
    if (diff.inDays < 1) {
      return '${diff.inHours} 小时前';
    }
    return '${diff.inDays} 天前';
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
  Widget build(BuildContext context) => Container(
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
