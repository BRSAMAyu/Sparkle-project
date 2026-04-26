import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/network/dio_provider.dart';
import 'package:sparkle/core/services/app_event_stream_service.dart';
import 'package:sparkle/core/services/prediction_attribution_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_provider.dart';
import 'package:sparkle/features/focus/data/services/candidate_feedback_service.dart';
import 'package:sparkle/features/home/data/models/prediction_insight_data.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/dashboard_section.dart';

class PredictedIntentCard extends ConsumerStatefulWidget {
  const PredictedIntentCard({super.key});

  @override
  ConsumerState<PredictedIntentCard> createState() =>
      _PredictedIntentCardState();
}

class _PredictedIntentCardState extends ConsumerState<PredictedIntentCard> {
  static const _collapsedPrefKey = 'dashboard.predicted_intent_card.collapsed';

  bool _isContinuing = false;
  bool _isCollapsed = false;
  late final CandidateFeedbackService _feedbackService;
  late final AppEventStreamService _eventStream;
  late final PredictionAttributionService _predictionAttribution;
  String? _lastImpressionPredictionId;

  @override
  void initState() {
    super.initState();
    _feedbackService = CandidateFeedbackService(
      ref.read(dioProvider),
      accessTokenGetter: ref.read(authRepositoryProvider).getAccessToken,
    );
    _eventStream = ref.read(appEventStreamServiceProvider);
    _predictionAttribution = ref.read(predictionAttributionServiceProvider);
    unawaited(_loadCollapsedPreference());
  }

  Future<void> _loadCollapsedPreference() async {
    final prefs = await SharedPreferences.getInstance();
    final collapsed = prefs.getBool(_collapsedPrefKey) ?? false;
    if (!mounted) return;
    setState(() {
      _isCollapsed = collapsed;
    });
  }

  Future<void> _setCollapsed(bool value) async {
    if (_isCollapsed == value) return;
    setState(() {
      _isCollapsed = value;
    });
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_collapsedPrefKey, value);
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

    final l10n = context.l10n;
    final isChinese = Localizations.localeOf(context).languageCode == 'zh';
    final confidencePercent = (forecast.confidence * 100).round();
    final sourceLabel = _sourceLabel(forecast.predictionSource, isChinese: isChinese);
    final windowLabel = _windowLabel(forecast.predictedWindow, isChinese: isChinese);
    final actionLabel = _actionLabel(forecast.predictedActionType, isChinese: isChinese);
    final freshnessLabel = _freshnessLabel(forecast.generatedAt, isChinese: isChinese);
    final primaryAction = forecast.recommendedActions.isNotEmpty
        ? forecast.recommendedActions.first
        : null;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final promptPreview = forecast.suggestedPrompt.trim();

    if (_isCollapsed) {
      return ContentConstraint(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(
            DS.spacing16,
            0,
            DS.spacing16,
            DS.spacing10,
          ),
          child: DashboardSectionShell(
            tone: DashboardSurfaceTone.summary,
            padding: const EdgeInsets.symmetric(
              horizontal: 14,
              vertical: DS.spacing12,
            ),
            child: DashboardSectionHeader(
              icon: Icons.psychology_alt_rounded,
              accentColor: DS.info,
              title: l10n.predictedIntentCollapsedTitle,
              summary: freshnessLabel == null
                  ? l10n.predictedIntentCollapsedExpand
                  : '${l10n.predictedIntentCollapsedUpdated} $freshnessLabel',
              trailing: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  _Chip(label: '$confidencePercent%', subdued: true),
                  const SizedBox(width: DS.spacing8),
                  SparkleIconButton(
                    variant: ButtonVariant.ghost,
                    size: 34,
                    onPressed: () => _setCollapsed(false),
                    icon: const Icon(
                      Icons.unfold_more_rounded,
                      size: 18,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
    }

    return ContentConstraint(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          DS.spacing16,
          0,
          DS.spacing16,
          DS.spacing10,
        ),
        child: DashboardSectionShell(
          tone: DashboardSurfaceTone.summary,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              DashboardSectionHeader(
                icon: Icons.psychology_alt_rounded,
                iconSize: 40,
                accentColor: DS.info,
                title: l10n.predictedIntentTitle,
                summary: l10n.predictedIntentSummary,
                trailing: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    _Chip(label: '$confidencePercent%'),
                    const SizedBox(width: DS.spacing8),
                    SparkleIconButton(
                      variant: ButtonVariant.ghost,
                      size: 34,
                      onPressed: () => _setCollapsed(true),
                      icon: const Icon(
                        Icons.visibility_off_rounded,
                        size: 18,
                      ),
                    ),
                  ],
                ),
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
                      l10n.predictedIntentSuggestedCont,
                      style: context.sparkleTypography.labelSmall.copyWith(
                        color: DS.textTertiary,
                        fontWeight: DS.fontWeightBold,
                      ),
                    ),
                    const SizedBox(height: DS.spacing6),
                    Text(
                      promptPreview.isEmpty
                          ? (l10n.predictedIntentWaiting)
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
              if (forecast.withinCategoryPreference != null) ...[
                const SizedBox(height: DS.spacing12),
                _WithinCategoryPreferencePanel(
                  preference: forecast.withinCategoryPreference!,
                  isChinese: isChinese,
                  isDark: isDark,
                ),
              ],
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
                    isChinese
                        ? '可信度 $confidencePercent%'
                        : 'Confidence $confidencePercent%',
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
                        l10n.predictedIntentWhy,
                        style: context.sparkleTypography.labelSmall.copyWith(
                          color: DS.textTertiary,
                          fontWeight: DS.fontWeightBold,
                        ),
                      ),
                      const SizedBox(height: DS.spacing6),
                      ...forecast.allExplanationLines.take(3).map(
                            (line) => Padding(
                              padding: const EdgeInsets.only(bottom: 4),
                              child: Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Container(
                                    width: 5,
                                    height: 5,
                                    margin: const EdgeInsets.only(
                                      top: 8,
                                      right: 8,
                                    ),
                                    decoration: BoxDecoration(
                                      color: DS.textSecondary,
                                      shape: BoxShape.circle,
                                    ),
                                  ),
                                  Expanded(
                                    child: Text(
                                      line,
                                      style: context
                                          .sparkleTypography.bodyMedium
                                          .copyWith(
                                        color: DS.textSecondary,
                                        height: 1.45,
                                      ),
                                    ),
                                  ),
                                ],
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
                    ? (l10n.predictedIntentContinuing)
                    : ((primaryAction?.label.isNotEmpty ?? false)
                        ? primaryAction!.label
                        : (l10n.predictedIntentContinue)),
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
        ),
      ),
    );
  }

  void _recordImpressionIfNeeded(PredictionInsightData forecast) {
    if (_lastImpressionPredictionId == forecast.predictionId) {
      return;
    }
    _lastImpressionPredictionId = forecast.predictionId;
    unawaited(
      _feedbackService.recordFeedback(
        candidateId: forecast.trackingCandidateId,
        actionType: forecast.trackingActionType,
        feedbackType: 'impression',
        contextSnapshot: _feedbackContext(forecast),
      ),
    );
    unawaited(
      _eventStream.recordPredictionFeedback(
        predictionId: forecast.predictionId,
        feedbackType: 'impression',
        actionType: forecast.trackingActionType,
        surface: forecast.surface ?? 'dashboard',
        suggestedPrompt: forecast.suggestedPrompt,
        entityType: forecast.entityCard?.entityType,
        entityId: forecast.entityCard?.entityId,
      ),
    );
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
      unawaited(
        _feedbackService.recordFeedback(
          candidateId: forecast.trackingCandidateId,
          actionType: forecast.trackingActionType,
          feedbackType: 'accept',
          contextSnapshot: _feedbackContext(forecast),
        ),
      );
      unawaited(
        _eventStream.recordPredictionFeedback(
          predictionId: forecast.predictionId,
          feedbackType: 'accept',
          actionType: forecast.trackingActionType,
          surface: forecast.surface ?? 'dashboard',
          suggestedPrompt: prompt,
          entityType: forecast.entityCard?.entityType,
          entityId: forecast.entityCard?.entityId,
        ),
      );
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
      await SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm);
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
        AppFeedback.error(
          context,
          context.l10n.predictedIntentError,
        );
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

  String _actionLabel(String actionType, {required bool isChinese}) {
    switch (actionType) {
      case 'resume_priority_task':
      case 'resume_task':
        return isChinese ? '继续重点任务' : 'Resume Priority Task';
      case 'study_plan':
        return isChinese ? '生成学习计划' : 'Build Study Plan';
      case 'error_diagnosis':
        return isChinese ? '问题诊断' : 'Diagnose Issue';
      case 'create_task':
        return isChinese ? '落成任务' : 'Turn Into Task';
      case 'translate':
        return isChinese ? '即时结果' : 'Instant Result';
      case 'review_progress':
        return isChinese ? '复盘进展' : 'Review Progress';
      case 'plan_next_step':
        return isChinese ? '规划下一步' : 'Plan Next Step';
      case 'reflection':
        return isChinese ? '快速反思' : 'Quick Reflection';
      default:
        return isChinese ? '预测意图' : 'Predicted Intent';
    }
  }

  String _windowLabel(String window, {required bool isChinese}) {
    switch (window) {
      case 'now':
        return isChinese ? '就是现在' : 'Right Now';
      case 'next_30m':
        return isChinese ? '未来 30 分钟' : 'Next 30 Minutes';
      case 'next_1h':
        return isChinese ? '未来 1 小时' : 'Next Hour';
      case 'next_2h':
        return isChinese ? '未来 2 小时' : 'Next 2 Hours';
      case 'next_6h':
        return isChinese ? '未来 6 小时' : 'Next 6 Hours';
      case 'today':
        return isChinese ? '今天内' : 'Later Today';
      default:
        return window.replaceAll('_', ' ');
    }
  }

  String _sourceLabel(String source, {required bool isChinese}) {
    switch (source) {
      case 'glm_batch':
        return isChinese ? '长期预测' : 'Long-Range Forecast';
      case 'rules':
        return isChinese ? '规则兜底' : 'Rules Fallback';
      default:
        return source;
    }
  }

  String? _freshnessLabel(DateTime? generatedAt, {required bool isChinese}) {
    if (generatedAt == null) return null;
    final diff = DateTime.now().difference(generatedAt);
    if (diff.inMinutes < 1) {
      return isChinese ? '刚刚更新' : 'just now';
    }
    if (diff.inHours < 1) {
      return isChinese ? '${diff.inMinutes} 分钟前' : '${diff.inMinutes} min ago';
    }
    if (diff.inDays < 1) {
      return isChinese ? '${diff.inHours} 小时前' : '${diff.inHours} hr ago';
    }
    return isChinese ? '${diff.inDays} 天前' : '${diff.inDays} d ago';
  }
}

class _WithinCategoryPreferencePanel extends StatelessWidget {
  const _WithinCategoryPreferencePanel({
    required this.preference,
    required this.isChinese,
    required this.isDark,
  });

  final WithinCategoryPreferenceData preference;
  final bool isChinese;
  final bool isDark;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing12),
      decoration: BoxDecoration(
        color: isDark
            ? Colors.white.withValues(alpha: 0.035)
            : DS.surfaceSecondary,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: DS.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            isChinese ? '同类请求里的近期偏好' : 'Recent same-category signal',
            style: context.sparkleTypography.labelSmall.copyWith(
              color: DS.textTertiary,
              fontWeight: DS.fontWeightBold,
            ),
          ),
          const SizedBox(height: DS.spacing6),
          Text(
            _hintText(),
            style: context.sparkleTypography.bodyMedium.copyWith(
              color: DS.textPrimary,
              height: 1.45,
            ),
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            _caveatText(),
            style: context.sparkleTypography.bodySmall.copyWith(
              color: DS.textSecondary,
              height: 1.45,
            ),
          ),
        ],
      ),
    );
  }

  String _hintText() {
    final categoryLabel = _categoryLabel(
      preference.requestCategory,
      isChinese: isChinese,
    );
    final toolLabel = _toolLabel(
      preference.preferredTool,
      isChinese: isChinese,
    );
    if (isChinese) {
      return '在$categoryLabel里，近期结果更常把「$toolLabel」推到前面。';
    }
    return 'Inside $categoryLabel, recent results have more often favored "$toolLabel" first.';
  }

  String _caveatText() {
    if (isChinese) {
      return '仅基于同类请求里的近期结果，不代表 Sparkle 理解了你的完整工作流。';
    }
    return 'Based only on recent results inside this request category. It does not mean Sparkle understands your whole workflow.';
  }

  String _categoryLabel(String raw, {required bool isChinese}) {
    final normalized = raw.trim().toLowerCase();
    if (isChinese) {
      switch (normalized) {
        case 'plan':
          return '规划类请求';
        case 'task':
          return '任务类请求';
        case 'focus':
          return '专注支持类请求';
        case 'growth':
          return '成长推进类请求';
        case 'query':
          return '查询类请求';
        case 'knowledge':
          return '知识类请求';
        case 'review':
          return '复盘类请求';
        case 'research':
          return '研究类请求';
        case 'memory':
          return '记忆整理类请求';
        case 'cognitive':
          return '认知整理类请求';
        default:
          return '同类请求';
      }
    }

    switch (normalized) {
      case 'plan':
        return 'planning requests';
      case 'task':
        return 'task requests';
      case 'focus':
        return 'focus-support requests';
      case 'growth':
        return 'growth requests';
      case 'query':
        return 'query requests';
      case 'knowledge':
        return 'knowledge requests';
      case 'review':
        return 'review requests';
      case 'research':
        return 'research requests';
      case 'memory':
        return 'memory requests';
      case 'cognitive':
        return 'cognitive requests';
      default:
        return 'similar requests';
    }
  }

  String _toolLabel(String raw, {required bool isChinese}) {
    final normalized = raw.trim().toLowerCase();
    if (isChinese) {
      switch (normalized) {
        case 'create_plan':
          return '生成计划';
        case 'generate_tasks_for_plan':
          return '展开计划步骤';
        case 'create_task':
          return '落成任务';
        case 'list_tasks':
          return '查看任务列表';
        case 'update_task':
          return '更新任务';
        case 'query_knowledge':
          return '查询知识';
        case 'explain_concept':
          return '解释概念';
        case 'review_progress':
          return '复盘进度';
        case 'generate_summary':
          return '生成总结';
        case 'suggest_schedule':
          return '建议排期';
        default:
          return _humanizeSnakeCase(normalized, upperFirst: false);
      }
    }

    switch (normalized) {
      case 'create_plan':
        return 'Create Plan';
      case 'generate_tasks_for_plan':
        return 'Expand Plan Steps';
      case 'create_task':
        return 'Create Task';
      case 'list_tasks':
        return 'List Tasks';
      case 'update_task':
        return 'Update Task';
      case 'query_knowledge':
        return 'Query Knowledge';
      case 'explain_concept':
        return 'Explain Concept';
      case 'review_progress':
        return 'Review Progress';
      case 'generate_summary':
        return 'Generate Summary';
      case 'suggest_schedule':
        return 'Suggest Schedule';
      default:
        return _humanizeSnakeCase(normalized, upperFirst: true);
    }
  }

  String _humanizeSnakeCase(String raw, {required bool upperFirst}) {
    final words = raw
        .split('_')
        .where((part) => part.trim().isNotEmpty)
        .toList(growable: false);
    if (words.isEmpty) {
      return raw;
    }
    final normalized = words.map((word) {
      if (!upperFirst) {
        return word;
      }
      return '${word[0].toUpperCase()}${word.substring(1)}';
    }).join(upperFirst ? ' ' : '');
    if (!upperFirst) {
      return normalized;
    }
    return normalized;
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
