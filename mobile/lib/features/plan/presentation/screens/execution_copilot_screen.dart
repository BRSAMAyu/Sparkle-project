import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/plan/presentation/providers/execution_copilot_provider.dart';

class ExecutionCopilotScreen extends ConsumerStatefulWidget {
  const ExecutionCopilotScreen({
    required this.planId,
    super.key,
  });

  final String planId;

  @override
  ConsumerState<ExecutionCopilotScreen> createState() =>
      _ExecutionCopilotScreenState();
}

class _ExecutionCopilotScreenState
    extends ConsumerState<ExecutionCopilotScreen> {
  int _timelineDays = 7;

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(executionCopilotProvider(widget.planId));
    final notifier = ref.read(executionCopilotProvider(widget.planId).notifier);

    final copilot = _asMap(state.copilot);
    final timeline = _asMap(state.timeline);

    final checkpointSummary = _asMap(copilot['checkpoint_summary']);
    final todayActions = _asList(copilot['today_actions']);
    final blockers = _asList(copilot['blockers']);
    final suggestions = _asList(copilot['repair_suggestions']);
    final timelineRows = _asList(timeline['timeline']);
    final topBlockers = _asList(timeline['top_blockers']);

    return Scaffold(
      appBar: AppBar(
        title: const Text('执行驾驶舱'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: state.isLoading
                ? null
                : () => notifier.load(days: _timelineDays),
          ),
        ],
      ),
      body: ContentConstraint(
        child: RefreshIndicator(
          onRefresh: () => notifier.load(days: _timelineDays),
          child: ListView(
            padding: const EdgeInsets.all(DS.spacing16),
            children: [
              _buildHeaderCard(
                context,
                planName:
                    '${copilot['plan_name'] ?? timeline['plan_name'] ?? '当前计划'}',
                riskLevel: '${copilot['risk_level'] ?? 'unknown'}',
                hint: '${copilot['execution_copilot_hint'] ?? ''}',
              ),
              const SizedBox(height: DS.spacing12),
              _buildCheckpointSummary(checkpointSummary),
              const SizedBox(height: DS.spacing12),
              Row(
                children: [
                  Expanded(
                    child: FilledButton.icon(
                      onPressed: state.isSubmitting
                          ? null
                          : () async {
                              final ok = await notifier.adoptTodayTopActions(
                                timelineDays: _timelineDays,
                              );
                              if (!context.mounted) return;
                              if (ok) {
                                AppFeedback.success(context, '已采纳今日前三步');
                              } else {
                                AppFeedback.info(context, '暂无可采纳的今日行动');
                              }
                            },
                      icon: const Icon(Icons.playlist_add_check_rounded),
                      label: const Text('一键采纳今日三步'),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: DS.spacing12),
              _buildTodayActions(
                context,
                todayActions: todayActions,
                onDone: (taskId) async {
                  final ok = await notifier.submitCheckpoint(
                    status: 'done',
                    taskId: taskId,
                    timelineDays: _timelineDays,
                  );
                  if (!context.mounted) return;
                  if (ok) {
                    AppFeedback.success(context, '已记录完成');
                  } else {
                    AppFeedback.error(context, '记录失败，请稍后重试');
                  }
                },
                onSkip: (taskId) async {
                  final ok = await notifier.submitCheckpoint(
                    status: 'skipped',
                    taskId: taskId,
                    timelineDays: _timelineDays,
                  );
                  if (!context.mounted) return;
                  if (ok) {
                    AppFeedback.info(context, '已记录跳过');
                  } else {
                    AppFeedback.error(context, '记录失败，请稍后重试');
                  }
                },
              ),
              const SizedBox(height: DS.spacing12),
              _buildBlockersAndSuggestions(
                blockers: blockers,
                suggestions: suggestions,
              ),
              const SizedBox(height: DS.spacing12),
              _buildTimelineSection(
                context,
                timelineRows: timelineRows,
                topBlockers: topBlockers,
                selectedDays: _timelineDays,
                onDaysChanged: (days) async {
                  setState(() => _timelineDays = days);
                  await notifier.load(days: days);
                },
              ),
              if (state.error != null) ...[
                const SizedBox(height: DS.spacing12),
                Text(
                  state.error!,
                  style: TextStyle(color: DS.error),
                ),
              ],
              if (state.isLoading)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: DS.spacing20),
                  child: Center(child: CircularProgressIndicator()),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeaderCard(
    BuildContext context, {
    required String planName,
    required String riskLevel,
    required String hint,
  }) {
    final normalizedRisk = riskLevel.trim().toLowerCase();
    var riskColor = DS.success;
    var riskLabel = '低风险';
    if (normalizedRisk == 'medium') {
      riskColor = DS.warning;
      riskLabel = '中风险';
    } else if (normalizedRisk == 'high') {
      riskColor = DS.error;
      riskLabel = '高风险';
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(DS.spacing16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    planName,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: DS.spacing10,
                    vertical: DS.spacing4,
                  ),
                  decoration: BoxDecoration(
                    color: riskColor.withValues(alpha: 0.14),
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Text(
                    riskLabel,
                    style: TextStyle(
                      color: riskColor,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
            if (hint.isNotEmpty) ...[
              const SizedBox(height: DS.spacing8),
              Text(
                hint,
                style: Theme.of(context)
                    .textTheme
                    .bodyMedium
                    ?.copyWith(color: DS.textSecondary),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildCheckpointSummary(Map<String, dynamic> summary) {
    final due = _toInt(summary['due']);
    final done = _toInt(summary['done']);
    final skipped = _toInt(summary['skipped']);
    final doneRate = (_toDouble(summary['done_rate']) * 100).toStringAsFixed(0);
    final skipRate = (_toDouble(summary['skip_rate']) * 100).toStringAsFixed(0);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(DS.spacing16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Checkpoint 概览',
              style: TextStyle(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: DS.spacing10),
            Wrap(
              spacing: DS.spacing10,
              runSpacing: DS.spacing10,
              children: [
                _metricTile('应执行', '$due'),
                _metricTile('已完成', '$done'),
                _metricTile('已跳过', '$skipped'),
                _metricTile('完成率', '$doneRate%'),
                _metricTile('跳过率', '$skipRate%'),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _metricTile(String label, String value) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing10,
          vertical: DS.spacing8,
        ),
        decoration: BoxDecoration(
          color: DS.surfaceTertiary,
          borderRadius: BorderRadius.circular(10),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              label,
              style: TextStyle(fontSize: 12, color: DS.textSecondary),
            ),
            const SizedBox(height: 2),
            Text(value, style: const TextStyle(fontWeight: FontWeight.w700)),
          ],
        ),
      );

  Widget _buildTodayActions(
    BuildContext context, {
    required List<dynamic> todayActions,
    required Future<void> Function(String taskId) onDone,
    required Future<void> Function(String taskId) onSkip,
  }) {
    if (todayActions.isEmpty) {
      return const Card(
        child: Padding(
          padding: EdgeInsets.all(DS.spacing16),
          child: Text('今日暂无可执行动作，请先补齐计划任务。'),
        ),
      );
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(DS.spacing16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              '今日行动清单',
              style: TextStyle(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: DS.spacing10),
            ...todayActions.take(6).map((raw) {
              final item = _asMap(raw);
              final taskId = '${item['task_id'] ?? ''}';
              final title = '${item['title'] ?? '未命名任务'}';
              final estimatedMinutes = _toInt(item['estimated_minutes']);
              final status = '${item['status'] ?? ''}';

              return Container(
                margin: const EdgeInsets.only(bottom: DS.spacing10),
                padding: const EdgeInsets.all(DS.spacing12),
                decoration: BoxDecoration(
                  color: DS.surfaceSecondary,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: DS.spacing4),
                    Text(
                      '预计 $estimatedMinutes 分钟 · 状态 $status',
                      style: TextStyle(color: DS.textSecondary),
                    ),
                    const SizedBox(height: DS.spacing8),
                    Row(
                      children: [
                        Expanded(
                          child: OutlinedButton.icon(
                            onPressed:
                                taskId.isEmpty ? null : () => onSkip(taskId),
                            icon: const Icon(Icons.skip_next_rounded),
                            label: const Text('跳过'),
                          ),
                        ),
                        const SizedBox(width: DS.spacing8),
                        Expanded(
                          child: FilledButton.icon(
                            onPressed:
                                taskId.isEmpty ? null : () => onDone(taskId),
                            icon: const Icon(Icons.check_circle_rounded),
                            label: const Text('完成'),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              );
            }),
          ],
        ),
      ),
    );
  }

  Widget _buildBlockersAndSuggestions({
    required List<dynamic> blockers,
    required List<dynamic> suggestions,
  }) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(DS.spacing16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              '阻塞与纠偏',
              style: TextStyle(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: DS.spacing10),
            if (blockers.isEmpty)
              Text('当前未发现明显阻塞。', style: TextStyle(color: DS.textSecondary))
            else
              Wrap(
                spacing: DS.spacing8,
                runSpacing: DS.spacing8,
                children: blockers
                    .map((item) => Chip(label: Text(item.toString())))
                    .toList(),
              ),
            if (suggestions.isNotEmpty) ...[
              const SizedBox(height: DS.spacing10),
              ...suggestions.map(
                (item) => Padding(
                  padding: const EdgeInsets.only(bottom: DS.spacing6),
                  child: Text('• $item'),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildTimelineSection(
    BuildContext context, {
    required List<dynamic> timelineRows,
    required List<dynamic> topBlockers,
    required int selectedDays,
    required Future<void> Function(int days) onDaysChanged,
  }) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(DS.spacing16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Expanded(
                  child: Text(
                    '执行趋势',
                    style: TextStyle(fontWeight: FontWeight.w700),
                  ),
                ),
                ChoiceChip(
                  label: const Text('7天'),
                  selected: selectedDays == 7,
                  onSelected: (_) => onDaysChanged(7),
                ),
                const SizedBox(width: DS.spacing8),
                ChoiceChip(
                  label: const Text('14天'),
                  selected: selectedDays == 14,
                  onSelected: (_) => onDaysChanged(14),
                ),
              ],
            ),
            const SizedBox(height: DS.spacing10),
            if (timelineRows.isEmpty)
              Text('暂无趋势数据。', style: TextStyle(color: DS.textSecondary))
            else
              ...timelineRows.map((raw) {
                final row = _asMap(raw);
                final date = '${row['date'] ?? ''}';
                final due = _toInt(row['due']);
                final done = _toInt(row['done']);
                final skipped = _toInt(row['skipped']);
                final doneRate =
                    (_toDouble(row['done_rate']) * 100).toStringAsFixed(0);
                final topBlocker = '${row['top_blocker'] ?? ''}';

                return Container(
                  margin: const EdgeInsets.only(bottom: DS.spacing8),
                  padding: const EdgeInsets.all(DS.spacing10),
                  decoration: BoxDecoration(
                    color: DS.surfaceSecondary,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        date,
                        style: const TextStyle(fontWeight: FontWeight.w600),
                      ),
                      const SizedBox(height: DS.spacing4),
                      Text(
                        '应执行 $due · 完成 $done · 跳过 $skipped · 完成率 $doneRate%',
                        style: TextStyle(color: DS.textSecondary),
                      ),
                      if (topBlocker.isNotEmpty)
                        Padding(
                          padding: const EdgeInsets.only(top: DS.spacing4),
                          child: Text(
                            '主要阻塞: $topBlocker',
                            style: TextStyle(color: DS.warning),
                          ),
                        ),
                    ],
                  ),
                );
              }),
            if (topBlockers.isNotEmpty) ...[
              const SizedBox(height: DS.spacing8),
              Text(
                'Top Blockers: ${topBlockers.map((e) => _asMap(e)['blocker']).whereType<String>().join(' / ')}',
                style: TextStyle(color: DS.textSecondary),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Map<String, dynamic> _asMap(dynamic value) {
    if (value is Map<String, dynamic>) {
      return value;
    }
    if (value is Map) {
      return value.map((key, val) => MapEntry('$key', val));
    }
    return <String, dynamic>{};
  }

  List<dynamic> _asList(dynamic value) {
    if (value is List<dynamic>) {
      return value;
    }
    if (value is List) {
      return value.toList();
    }
    return const <dynamic>[];
  }

  int _toInt(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse('$value') ?? 0;
  }

  double _toDouble(dynamic value) {
    if (value is double) return value;
    if (value is num) return value.toDouble();
    return double.tryParse('$value') ?? 0.0;
  }
}
