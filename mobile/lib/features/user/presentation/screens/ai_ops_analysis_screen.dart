import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/app_feedback.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';

class AiOpsAnalysisScreen extends ConsumerStatefulWidget {
  const AiOpsAnalysisScreen({super.key});

  @override
  ConsumerState<AiOpsAnalysisScreen> createState() =>
      _AiOpsAnalysisScreenState();
}

class _AiOpsAnalysisScreenState extends ConsumerState<AiOpsAnalysisScreen> {
  int _days = 14;

  @override
  Widget build(BuildContext context) {
    final exportAsync = ref.watch(aiOpsExportProvider(_days));
    final predictionAsync = ref.watch(predictionAnalyticsByDaysProvider(_days));

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        title: Text(context.l10n.userAiOpsAnalysis),
        actions: [
          SparkleButton(
            label: context.l10n.userAiOpsCopyExport,
            onPressed: exportAsync.hasValue
                ? () => _copyExport(context, exportAsync.value!)
                : null,
            variant: ButtonVariant.ghost,
          ),
        ],
      ),
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(DS.spacing16),
        child: ContentConstraint(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SparkleStaggerItem(index: 0, child: _buildPeriodSelector()),
              const SizedBox(height: DS.spacing16),
              SparkleStaggerItem(
                index: 1,
                child: exportAsync.when(
                  data: (payload) => _buildOpsContent(context, payload),
                  loading: () => const GraphiteCardSurface(
                    child: LinearProgressIndicator(minHeight: 3),
                  ),
                  error: (error, _) => _buildErrorCard(
                    context.l10n.userAiOpsLoadFailed,
                    '$error',
                  ),
                ),
              ),
              const SizedBox(height: DS.spacing16),
              SparkleStaggerItem(
                index: 2,
                child: predictionAsync.when(
                  data: (payload) => _buildPredictionContent(context, payload),
                  loading: () => const GraphiteCardSurface(
                    child: LinearProgressIndicator(minHeight: 3),
                  ),
                  error: (error, _) => _buildErrorCard(
                    context.l10n.userAiOpsPredictFailed,
                    '$error',
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildPeriodSelector() => GraphiteCardSurface(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              context.l10n.userAiOpsAnalysisWindow,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              context.l10n.userAiOpsWindowHint,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.textSecondary,
                  ),
            ),
            const SizedBox(height: DS.spacing12),
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing8,
              children: [7, 14, 30]
                  .map(
                    (days) => ChoiceChip(
                      label: Text(context.l10n.aiopsDays(days)),
                      selected: _days == days,
                      onSelected: (_) => setState(() => _days = days),
                    ),
                  )
                  .toList(),
            ),
          ],
        ),
      );

  Widget _buildOpsContent(BuildContext context, Map<String, dynamic> payload) {
    final overview = (payload['overview'] as Map<String, dynamic>?) ??
        const <String, dynamic>{};
    final items = (payload['items'] as List<dynamic>? ?? const <dynamic>[])
        .whereType<Map<String, dynamic>>()
        .toList();
    final trendSeries =
        (payload['trend_series'] as List<dynamic>? ?? const <dynamic>[])
            .whereType<Map<String, dynamic>>()
            .toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        GraphiteCardSurface(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                context.l10n.userAiOpsDevOps,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: DS.fontWeightBold,
                    ),
              ),
              const SizedBox(height: DS.spacing8),
              Text(
                context.l10n.userAiOpsDevOpsHint,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.textSecondary,
                    ),
              ),
              const SizedBox(height: DS.spacing12),
              Wrap(
                spacing: DS.spacing8,
                runSpacing: DS.spacing8,
                children: [
                  _MetricChip(
                    label: context.l10n.userAiOpsSuccessRate,
                    value:
                        '${((overview['success_rate_percent'] as num?)?.toDouble() ?? 0).toStringAsFixed(1)}%',
                  ),
                  _MetricChip(
                    label: context.l10n.userAiOpsAvgFirstToken,
                    value:
                        '${((overview['avg_first_token_ms'] as num?)?.toDouble() ?? 0).toStringAsFixed(0)}ms',
                  ),
                  _MetricChip(
                    label: context.l10n.userAiOpsAvgTotalTime,
                    value:
                        '${((overview['avg_total_duration_ms'] as num?)?.toDouble() ?? 0).toStringAsFixed(0)}ms',
                  ),
                  _MetricChip(
                    label: 'Fallback',
                    value:
                        '${((overview['fallback_rate_percent'] as num?)?.toDouble() ?? 0).toStringAsFixed(1)}%',
                  ),
                  _MetricChip(
                    label: context.l10n.userAiOpsTotalCost,
                    value:
                        '\$${((overview['total_cost_usd'] as num?)?.toDouble() ?? 0).toStringAsFixed(4)}',
                  ),
                  _MetricChip(
                    label: context.l10n.userAiOpsExecutionConversion,
                    value:
                        '${((overview['execution_conversion_rate_percent'] as num?)?.toDouble() ?? 0).toStringAsFixed(1)}%',
                  ),
                  _MetricChip(
                    label: context.l10n.userAiOpsPromptHit,
                    value:
                        '${((overview['avg_prompt_utilization_percent'] as num?)?.toDouble() ?? 0).toStringAsFixed(1)}%',
                  ),
                  _MetricChip(
                    label: context.l10n.userAiOpsInferenceHit,
                    value:
                        '${((overview['avg_inference_utilization_percent'] as num?)?.toDouble() ?? 0).toStringAsFixed(1)}%',
                  ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: DS.spacing16),
        if (trendSeries.isNotEmpty)
          ...trendSeries.take(4).map(
                (series) => Padding(
                  padding: const EdgeInsets.only(bottom: DS.spacing12),
                  child: _TrendSeriesCard(series: series),
                ),
              ),
        if (items.isNotEmpty)
          GraphiteCardSurface(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  context.l10n.userAiOpsPatternDetails,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: DS.fontWeightBold,
                      ),
                ),
                const SizedBox(height: DS.spacing12),
                ...items.map(
                  (item) => Padding(
                    padding: const EdgeInsets.only(bottom: DS.spacing10),
                    child: _ModeBreakdownRow(item: item),
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }

  Widget _buildPredictionContent(
    BuildContext context,
    Map<String, dynamic> payload,
  ) {
    final funnel = (payload['funnel'] as Map<String, dynamic>?) ??
        const <String, dynamic>{};
    final bySurface = (payload['by_surface'] as Map<String, dynamic>?) ??
        const <String, dynamic>{};
    final topActions =
        (payload['top_actions'] as List<dynamic>? ?? const <dynamic>[])
            .whereType<Map<String, dynamic>>()
            .toList();

    return GraphiteCardSurface(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.userAiOpsPredictConversion,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: DS.fontWeightBold,
                ),
          ),
          const SizedBox(height: DS.spacing8),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: [
              _MetricChip(
                  label: context.l10n.userAiOpsExposures,
                  value: '${funnel['impressions'] ?? 0}'),
              _MetricChip(
                  label: context.l10n.userAiOpsAccepts,
                  value: '${funnel['accepts'] ?? 0}'),
              _MetricChip(
                  label: context.l10n.userAiOpsExecutions,
                  value: '${funnel['executions'] ?? 0}'),
              _MetricChip(
                label: 'CTR',
                value:
                    '${((funnel['ctr_percent'] as num?)?.toDouble() ?? 0).toStringAsFixed(1)}%',
              ),
              _MetricChip(
                label: context.l10n.userAiOpsAcceptToExec,
                value:
                    '${((funnel['accept_to_execution_percent'] as num?)?.toDouble() ?? 0).toStringAsFixed(1)}%',
              ),
            ],
          ),
          if (bySurface.isNotEmpty) ...[
            const SizedBox(height: DS.spacing12),
            Text(
              context.l10n.userAiOpsBySurface,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
            const SizedBox(height: DS.spacing8),
            ...bySurface.entries.map((entry) {
              final item = (entry.value as Map?)?.cast<String, dynamic>() ??
                  const <String, dynamic>{};
              return Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Text(
                  context.l10n.aiopsSurfaceRow(
                      _surfaceLabel(entry.key),
                      ((item['ctr_percent'] as num?)?.toDouble() ?? 0)
                          .toStringAsFixed(1),
                      ((item['execution_rate_percent'] as num?)?.toDouble() ??
                              0)
                          .toStringAsFixed(1)),
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              );
            }),
          ],
          if (topActions.isNotEmpty) ...[
            const SizedBox(height: DS.spacing12),
            Text(
              context.l10n.userAiOpsWorthOptimizing,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
            const SizedBox(height: DS.spacing8),
            ...topActions.take(5).map((item) {
              final actionType = item['action_type']?.toString() ?? 'unknown';
              final executions = item['linked_executions'] ?? 0;
              final rate =
                  (item['execution_rate_percent'] as num?)?.toDouble() ?? 0.0;
              return Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Text(
                  context.l10n.aiopsActionRow(
                      actionType, executions as int, rate.toStringAsFixed(1)),
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              );
            }),
          ],
        ],
      ),
    );
  }

  Widget _buildErrorCard(String title, String message) => GraphiteCardSurface(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
            const SizedBox(height: DS.spacing8),
            Text(message, style: Theme.of(context).textTheme.bodySmall),
          ],
        ),
      );

  Future<void> _copyExport(
    BuildContext context,
    Map<String, dynamic> payload,
  ) async {
    final pretty = const JsonEncoder.withIndent('  ').convert(payload);
    await Clipboard.setData(ClipboardData(text: pretty));
    if (!context.mounted) return;
    AppFeedback.success(context, context.l10n.userAiOpsExportCopied);
  }

  String _surfaceLabel(String surface) {
    switch (surface) {
      case 'dashboard':
        return context.l10n.userAiOpsDashboard;
      case 'chat_input':
        return context.l10n.userAiOpsChatInput;
      case 'chat':
        return context.l10n.userAiOpsChat;
      default:
        return surface;
    }
  }
}

class _TrendSeriesCard extends StatelessWidget {
  const _TrendSeriesCard({required this.series});

  final Map<String, dynamic> series;

  @override
  Widget build(BuildContext context) {
    final points = (series['points'] as List<dynamic>? ?? const <dynamic>[])
        .whereType<Map<String, dynamic>>()
        .toList();
    final chatMode = series['chat_mode']?.toString() ?? 'standard';
    final latest = points.isNotEmpty ? points.last : const <String, dynamic>{};

    return GraphiteCardSurface(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            _chatModeLabel(context, chatMode),
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: DS.fontWeightBold,
                ),
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            context.l10n.aiopsTrendDesc,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.textSecondary,
                ),
          ),
          const SizedBox(height: DS.spacing12),
          _TrendBarRow(
            label: context.l10n.aiopsTotalTime,
            points: points,
            valueKey: 'avg_total_duration_ms',
            valueFormatter: (value) => '${value.toStringAsFixed(0)}ms',
            color: DS.brandPrimary,
          ),
          const SizedBox(height: DS.spacing10),
          _TrendBarRow(
            label: context.l10n.userAiOpsSuccessRate,
            points: points,
            valueKey: 'success_rate_percent',
            valueFormatter: (value) => '${value.toStringAsFixed(1)}%',
            color: DS.success,
          ),
          const SizedBox(height: DS.spacing10),
          _TrendBarRow(
            label: context.l10n.userAiOpsExecutionConversion,
            points: points,
            valueKey: 'execution_conversion_rate_percent',
            valueFormatter: (value) => '${value.toStringAsFixed(1)}%',
            color: DS.warning,
          ),
          const SizedBox(height: DS.spacing12),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: [
              _MetricChip(
                label: context.l10n.aiopsLatestRequests,
                value: '${latest['requests_total'] ?? 0}',
              ),
              _MetricChip(
                label: context.l10n.aiopsLatestFallback,
                value:
                    '${((latest['fallback_rate_percent'] as num?)?.toDouble() ?? 0).toStringAsFixed(1)}%',
              ),
              _MetricChip(
                label: context.l10n.aiopsLatestCost,
                value:
                    '\$${((latest['total_cost_usd'] as num?)?.toDouble() ?? 0).toStringAsFixed(4)}',
              ),
            ],
          ),
        ],
      ),
    );
  }

  String _chatModeLabel(BuildContext context, String value) {
    switch (value) {
      case 'standard':
        return context.l10n.userAiOpsStandardChat;
      case 'study_plan':
        return context.l10n.userAiOpsStudyPlanning;
      case 'deep_analysis':
        return context.l10n.userAiOpsDeepAnalysis;
      case 'error_diagnosis':
        return context.l10n.userAiOpsDiagnosisCorrection;
      case 'expert_auto':
        return context.l10n.userAiOpsExpertCollaboration;
      default:
        return value;
    }
  }
}

class _TrendBarRow extends StatelessWidget {
  const _TrendBarRow({
    required this.label,
    required this.points,
    required this.valueKey,
    required this.valueFormatter,
    required this.color,
  });

  final String label;
  final List<Map<String, dynamic>> points;
  final String valueKey;
  final String Function(double value) valueFormatter;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final values = points
        .map((point) => (point[valueKey] as num?)?.toDouble() ?? 0.0)
        .toList();
    final maxValue = values.isEmpty
        ? 0.0
        : values.reduce((current, next) => current > next ? current : next);
    final latest = values.isNotEmpty ? values.last : 0.0;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                label,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      fontWeight: DS.fontWeightBold,
                    ),
              ),
            ),
            Text(
              valueFormatter(latest),
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
        const SizedBox(height: 6),
        SizedBox(
          height: 54,
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              for (var index = 0; index < points.length; index++) ...[
                Expanded(
                  child: Padding(
                    padding: EdgeInsets.only(
                      right: index == points.length - 1 ? 0 : 4,
                    ),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.end,
                      children: [
                        Expanded(
                          child: Align(
                            alignment: Alignment.bottomCenter,
                            child: FractionallySizedBox(
                              heightFactor: maxValue <= 0
                                  ? 0.08
                                  : (values[index] / maxValue).clamp(0.08, 1.0),
                              child: Container(
                                decoration: BoxDecoration(
                                  color: color.withValues(alpha: 0.84),
                                  borderRadius: BorderRadius.circular(8),
                                ),
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          _shortDate(points[index]['date']?.toString() ?? ''),
                          style:
                              Theme.of(context).textTheme.labelSmall?.copyWith(
                                    color: DS.textSecondary,
                                  ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ],
    );
  }

  String _shortDate(String value) {
    final parts = value.split('-');
    if (parts.length != 3) return value;
    return '${parts[1]}/${parts[2]}';
  }
}

class _ModeBreakdownRow extends StatelessWidget {
  const _ModeBreakdownRow({required this.item});

  final Map<String, dynamic> item;

  @override
  Widget build(BuildContext context) {
    final chatMode = item['chat_mode']?.toString() ?? 'standard';
    final successRate =
        (item['success_rate_percent'] as num?)?.toDouble() ?? 0.0;
    final fallbackRate =
        (item['fallback_rate_percent'] as num?)?.toDouble() ?? 0.0;
    final cost = (item['total_cost_usd'] as num?)?.toDouble() ?? 0.0;
    final avgFirst = (item['avg_first_token_ms'] as num?)?.toDouble() ?? 0.0;
    final avgTotal = (item['avg_total_duration_ms'] as num?)?.toDouble() ?? 0.0;
    final executionRate =
        (item['execution_conversion_rate_percent'] as num?)?.toDouble() ?? 0.0;

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: DS.surfacePrimary,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: DS.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            _chatModeLabel(context, chatMode),
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  fontWeight: DS.fontWeightBold,
                ),
          ),
          const SizedBox(height: 6),
          Text(
            context.l10n.aiopsFirstPacket(avgFirst.toStringAsFixed(0),
                avgTotal.toStringAsFixed(0), successRate.toStringAsFixed(1)),
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: 2),
          Text(
            context.l10n.aiopsFallbackCost(fallbackRate.toStringAsFixed(1),
                cost.toStringAsFixed(4), executionRate.toStringAsFixed(1)),
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.textSecondary,
                ),
          ),
          const SizedBox(height: 2),
          Text(
            context.l10n.aiopsPromptHit(
                ((item['avg_prompt_utilization_percent'] as num?)?.toDouble() ??
                        0)
                    .toStringAsFixed(1),
                ((item['avg_inference_utilization_percent'] as num?)
                            ?.toDouble() ??
                        0)
                    .toStringAsFixed(1),
                (item['prompt_utilization_known_count'] ?? 0) as int,
                (item['inference_utilization_known_count'] ?? 0) as int),
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.textSecondary,
                ),
          ),
        ],
      ),
    );
  }

  String _chatModeLabel(BuildContext context, String value) {
    switch (value) {
      case 'standard':
        return context.l10n.userAiOpsStandardChat;
      case 'study_plan':
        return context.l10n.userAiOpsStudyPlanning;
      case 'deep_analysis':
        return context.l10n.userAiOpsDeepAnalysis;
      case 'error_diagnosis':
        return context.l10n.userAiOpsDiagnosisCorrection;
      case 'expert_auto':
        return context.l10n.userAiOpsExpertCollaboration;
      default:
        return value;
    }
  }
}

class _MetricChip extends StatelessWidget {
  const _MetricChip({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing10,
          vertical: DS.spacing8,
        ),
        decoration: BoxDecoration(
          color: DS.surfacePrimary,
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              label,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: DS.textSecondary,
                  ),
            ),
            const SizedBox(height: 2),
            Text(
              value,
              style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
          ],
        ),
      );
}
