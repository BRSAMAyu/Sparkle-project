import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/task/data/models/execution_intent_model.dart';
import 'package:sparkle/features/task/data/models/execution_record_model.dart';
import 'package:sparkle/features/task/presentation/widgets/execution_result_renderer.dart';

class ExecutionApprovalCard extends StatefulWidget {
  const ExecutionApprovalCard({
    required this.record,
    required this.intent,
    required this.onConfirm,
    required this.onReject,
    super.key,
    this.isLoading = false,
  });

  final ExecutionRecordModel record;
  final ExecutionIntentModel intent;
  final VoidCallback onConfirm;
  final VoidCallback onReject;
  final bool isLoading;

  @override
  State<ExecutionApprovalCard> createState() => _ExecutionApprovalCardState();
}

class _ExecutionApprovalCardState extends State<ExecutionApprovalCard> {
  bool _expanded = false;

  String _parsedOutputSummary() {
    final parsed = widget.record.parsedOutput;
    if (parsed == null || parsed.isEmpty) {
      return 'AI 已准备好结果，等待你确认。';
    }
    return parsed.entries
        .map((entry) => '${entry.key}: ${entry.value}')
        .join('\n')
        .trim();
  }

  String _formatDuration(int? durationMs) {
    if (durationMs == null || durationMs <= 0) {
      return '未记录';
    }
    final duration = Duration(milliseconds: durationMs);
    if (duration.inMinutes >= 1) {
      final seconds = duration.inSeconds % 60;
      return '${duration.inMinutes}分${seconds > 0 ? '$seconds秒' : ''}';
    }
    return '${(duration.inMilliseconds / 1000).toStringAsFixed(1)}秒';
  }

  Color _trustColor() {
    switch (widget.record.trustLevel.toLowerCase()) {
      case 'trusted':
        return DS.semanticSuccess;
      case 'validated':
        return DS.info;
      default:
        return DS.semanticWarning;
    }
  }

  @override
  Widget build(BuildContext context) {
    final parsedOutput =
        widget.record.resultPreview ??
        widget.record.parsedOutput ??
        const <String, dynamic>{};

    return SparkleStaggerItem(
      index: 0,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(DS.spacing16),
        decoration: BoxDecoration(
          color: DS.surfacePrimary,
          borderRadius: BorderRadius.circular(16),
          boxShadow: [
            BoxShadow(
              color: DS.textPrimary.withValues(alpha: 0.06),
              blurRadius: 8,
              offset: const Offset(0, 2),
            ),
          ],
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _TargetComparison(
              goal: widget.intent.goal,
              resultSummary: _parsedOutputSummary(),
            ),
            const SizedBox(height: DS.spacing12),
            Row(
              children: [
                Expanded(
                  child: _MetricChip(
                    icon: Icons.timer_outlined,
                    label: _formatDuration(widget.record.durationMs),
                  ),
                ),
                const SizedBox(width: DS.spacing8),
                Expanded(
                  child: _MetricChip(
                    icon: Icons.construction_outlined,
                    label: '工具 ${widget.record.toolCallsCount} 次',
                  ),
                ),
                const SizedBox(width: DS.spacing8),
                Expanded(
                  child: _MetricChip(
                    icon: Icons.verified_outlined,
                    label: widget.record.trustLabel,
                    accentColor: _trustColor(),
                  ),
                ),
              ],
            ),
            const SizedBox(height: DS.spacing12),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(DS.spacing12),
              decoration: BoxDecoration(
                color: DS.surfaceSecondary,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '结果预览',
                    style: DS.bodySmall.copyWith(
                      fontWeight: DS.fontWeightBold,
                      color: DS.textSecondary,
                    ),
                  ),
                  const SizedBox(height: DS.spacing8),
                  ExecutionResultRenderer(
                    parsedOutput: parsedOutput,
                    artifacts: widget.record.artifacts,
                    expanded: _expanded,
                  ),
                  const SizedBox(height: DS.spacing8),
                  TextButton(
                    onPressed: () => setState(() => _expanded = !_expanded),
                    child: Text(_expanded ? '收起详情' : '查看详情'),
                  ),
                  if (widget.record.comparisonSummary != null) ...[
                    const SizedBox(height: DS.spacing8),
                    _InfoPanel(
                      title: widget.record.comparisonSummary!['headline']
                              ?.toString() ??
                          '结果对比',
                      message: widget.record.comparisonSummary!['summary']
                              ?.toString() ??
                          '',
                      color: DS.info,
                    ),
                  ],
                  if (widget.record.qualityWarnings.isNotEmpty) ...[
                    const SizedBox(height: DS.spacing8),
                    ...widget.record.qualityWarnings.map(
                      (warning) => Padding(
                        padding: const EdgeInsets.only(bottom: DS.spacing6),
                        child: _InfoPanel(
                          title: '自验证提示',
                          message: warning['message']?.toString() ?? '',
                          color: DS.semanticWarning,
                        ),
                      ),
                    ),
                  ],
                  if (widget.record.replaySteps.isNotEmpty) ...[
                    const SizedBox(height: DS.spacing8),
                    Text(
                      '执行回放',
                      style: DS.bodySmall.copyWith(
                        fontWeight: DS.fontWeightBold,
                        color: DS.textSecondary,
                      ),
                    ),
                    const SizedBox(height: DS.spacing8),
                    ...widget.record.replaySteps.map(
                      (step) => Padding(
                        padding: const EdgeInsets.only(bottom: DS.spacing6),
                        child: _ReplayStepTile(step: step),
                      ),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: DS.spacing16),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: widget.isLoading
                        ? null
                        : () {
                            unawaited(
                              SensoryFeedbackService.emit(
                                SensoryFeedbackEvent.warning,
                              ),
                            );
                            widget.onReject();
                          },
                    style: OutlinedButton.styleFrom(
                      minimumSize: const Size.fromHeight(48),
                      side: BorderSide(color: DS.semanticError),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(20),
                      ),
                    ),
                    child: Text(
                      '退回修改',
                      style: DS.bodyMedium.copyWith(color: DS.semanticError),
                    ),
                  ),
                ),
                const SizedBox(width: DS.spacing12),
                Expanded(
                  child: FilledButton(
                    onPressed: widget.isLoading
                        ? null
                        : () {
                            unawaited(
                              SensoryFeedbackService.emit(
                                SensoryFeedbackEvent.confirm,
                              ),
                            );
                            widget.onConfirm();
                          },
                    style: FilledButton.styleFrom(
                      minimumSize: const Size.fromHeight(48),
                      backgroundColor: DS.semanticSuccess,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(20),
                      ),
                    ),
                    child: widget.isLoading
                        ? SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              valueColor: AlwaysStoppedAnimation<Color>(
                                DS.surfacePrimary,
                              ),
                            ),
                          )
                        : Text(
                            '采纳结果',
                            style: DS.bodyMedium.copyWith(color: DS.white),
                          ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _InfoPanel extends StatelessWidget {
  const _InfoPanel({
    required this.title,
    required this.message,
    required this.color,
  });

  final String title;
  final String message;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(DS.spacing10),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: color.withValues(alpha: 0.16)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: DS.bodySmall.copyWith(
                color: color,
                fontWeight: DS.fontWeightBold,
              ),
            ),
            if (message.trim().isNotEmpty) ...[
              const SizedBox(height: DS.spacing4),
              Text(
                message,
                style: DS.bodySmall.copyWith(
                  color: DS.textPrimary,
                  height: 1.45,
                ),
              ),
            ],
          ],
        ),
      );
}

class _ReplayStepTile extends StatelessWidget {
  const _ReplayStepTile({required this.step});

  final Map<String, dynamic> step;

  @override
  Widget build(BuildContext context) {
    final failed = step['status']?.toString() == 'failed';
    final durationMs = (step['duration_ms'] as num?)?.toInt();
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing10),
      decoration: BoxDecoration(
        color: DS.surfacePrimary,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: DS.borderSubtle),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            failed ? Icons.error_outline_rounded : Icons.play_circle_outline,
            size: 18,
            color: failed ? DS.semanticError : DS.info,
          ),
          const SizedBox(width: DS.spacing8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  step['label']?.toString() ?? '执行步骤',
                  style: DS.bodyMedium.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
                ),
                if ((step['preview']?.toString() ?? '').isNotEmpty) ...[
                  const SizedBox(height: DS.spacing4),
                  Text(
                    step['preview'].toString(),
                    style: DS.bodySmall.copyWith(
                      color: DS.textSecondary,
                      height: 1.45,
                    ),
                  ),
                ],
              ],
            ),
          ),
          if (durationMs != null && durationMs > 0)
            Text(
              '${(durationMs / 1000).toStringAsFixed(durationMs >= 1000 ? 1 : 0)}s',
              style: DS.bodySmall.copyWith(color: DS.textTertiary),
            ),
        ],
      ),
    );
  }
}

class _TargetComparison extends StatelessWidget {
  const _TargetComparison({
    required this.goal,
    required this.resultSummary,
  });

  final String goal;
  final String resultSummary;

  @override
  Widget build(BuildContext context) => Container(
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing12),
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: _CompareBlock(label: '目标', content: goal),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: DS.spacing8),
            child: Icon(
              Icons.arrow_forward_rounded,
              color: DS.textTertiary,
            ),
          ),
          Expanded(
            child: _CompareBlock(label: 'AI结果', content: resultSummary),
          ),
        ],
      ),
    );
}

class _CompareBlock extends StatelessWidget {
  const _CompareBlock({
    required this.label,
    required this.content,
  });

  final String label;
  final String content;

  @override
  Widget build(BuildContext context) => Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: DS.bodySmall.copyWith(
            color: DS.textSecondary,
            fontWeight: DS.fontWeightBold,
          ),
        ),
        const SizedBox(height: DS.spacing4),
        Text(
          content,
          maxLines: 4,
          overflow: TextOverflow.ellipsis,
          style: DS.bodySmall.copyWith(color: DS.textPrimary),
        ),
      ],
    );
}

class _MetricChip extends StatelessWidget {
  const _MetricChip({
    required this.icon,
    required this.label,
    this.accentColor,
  });

  final IconData icon;
  final String label;
  final Color? accentColor;

  @override
  Widget build(BuildContext context) => Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing10,
        vertical: DS.spacing8,
      ),
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: accentColor ?? DS.textSecondary),
          const SizedBox(width: DS.spacing6),
          Expanded(
            child: Text(
              label,
              overflow: TextOverflow.ellipsis,
              style: DS.bodySmall.copyWith(
                color: accentColor ?? DS.textSecondary,
                fontSize: 12,
              ),
            ),
          ),
        ],
      ),
    );
}
