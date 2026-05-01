import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/utils/text_rendering.dart';
import 'package:sparkle/core/widgets/sparkle_markdown.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/features/task/utils/task_identity.dart';
import 'package:sparkle/shared/entities/task_model.dart';

class TaskGuidanceSurface extends ConsumerStatefulWidget {
  const TaskGuidanceSurface({required this.task, super.key});

  final TaskModel task;

  @override
  ConsumerState<TaskGuidanceSurface> createState() =>
      _TaskGuidanceSurfaceState();
}

class _TaskGuidanceSurfaceState extends ConsumerState<TaskGuidanceSurface> {
  static const _loadingText = '正在整理这张任务的闭环执行指南...';
  TaskGuidanceAudience _selectedAudience = TaskGuidanceAudience.human;
  bool _humanPrimed = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      unawaited(_primeHumanGuidance());
    });
  }

  @override
  void didUpdateWidget(covariant TaskGuidanceSurface oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.task.id != widget.task.id) {
      _selectedAudience = TaskGuidanceAudience.human;
      _humanPrimed = false;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        unawaited(_primeHumanGuidance());
      });
    }
  }

  String _guidanceKey(TaskGuidanceAudience audience) =>
      '${widget.task.id}::${audience.wireValue}';

  bool get _canRequestGuidance => isServerTaskId(widget.task.id);

  Future<void> _primeHumanGuidance() async {
    if (_humanPrimed || !_canRequestGuidance || !mounted) {
      return;
    }
    _humanPrimed = true;
    final notifier = ref.read(taskListProvider.notifier);
    final cached = ref
        .read(taskListProvider)
        .taskGuidance[_guidanceKey(TaskGuidanceAudience.human)];
    if (cached != null) {
      return;
    }

    final existing = await notifier.loadTaskGuidance(
      widget.task.id,
    );
    if (!mounted || existing != null) {
      return;
    }

    await notifier.createOrRefreshTaskGuidance(
      widget.task.id,
    );
  }

  Future<void> _selectAudience(TaskGuidanceAudience audience) async {
    if (_selectedAudience == audience) return;
    setState(() => _selectedAudience = audience);
    if (!_canRequestGuidance) return;
    if (audience == TaskGuidanceAudience.human) {
      await _primeHumanGuidance();
      return;
    }

    final key = _guidanceKey(audience);
    final cached = ref.read(taskListProvider).taskGuidance[key];
    if (cached == null) {
      await ref.read(taskListProvider.notifier).loadTaskGuidance(
            widget.task.id,
            audience: audience,
          );
    }
  }

  Future<void> _generateSelected({bool regenerate = false}) async {
    if (!_canRequestGuidance) return;
    final notifier = ref.read(taskListProvider.notifier);
    final label = _selectedAudience == TaskGuidanceAudience.human
        ? '用户版任务指南'
        : 'AI 版本任务指南';
    try {
      await notifier.createOrRefreshTaskGuidance(
        widget.task.id,
        audience: _selectedAudience,
        regenerate: regenerate,
      );
      if (!mounted) return;
      AppFeedback.success(
        context,
        regenerate ? '$label已刷新' : '$label已生成',
      );
    } catch (error) {
      if (!mounted) return;
      AppFeedback.error(context, '$label生成失败：$error');
    }
  }

  @override
  Widget build(BuildContext context) {
    final taskState = ref.watch(taskListProvider);
    final guidance = taskState.taskGuidance[_guidanceKey(_selectedAudience)];
    final isLoading = taskState.taskGuidanceInFlight
        .contains(_guidanceKey(_selectedAudience));
    final stale = guidance?.sourceTaskUpdatedAt != null &&
        guidance!.sourceTaskUpdatedAt!.isBefore(widget.task.updatedAt);
    final humanFallback = widget.task.guideContent != null &&
            widget.task.guideContent!.trim().isNotEmpty
        ? widget.task.guideContent!.trim()
        : null;
    final content = guidance?.content.trim().isNotEmpty ?? false
        ? guidance!.content.trim()
        : (_selectedAudience == TaskGuidanceAudience.human
            ? humanFallback
            : null);
    final hasContent = content != null && content.isNotEmpty;
    final canRefresh = _canRequestGuidance;

    return GraphiteCardSurface(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      context.l10n.taskGuideTitle,
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                            fontWeight: DS.fontWeightBold,
                          ),
                    ),
                    const SizedBox(height: DS.spacing4),
                    Text(
                      '用户版默认生成，AI 版按需补全，始终围绕当前任务上下文。',
                      style: DS.bodySmall.copyWith(color: DS.textSecondary),
                    ),
                  ],
                ),
              ),
              if (isLoading)
                const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
            ],
          ),
          const SizedBox(height: DS.spacing16),
          SegmentedButton<TaskGuidanceAudience>(
            segments: const [
              ButtonSegment(
                value: TaskGuidanceAudience.human,
                label: Text('给自己看'),
                icon: Icon(Icons.person_outline_rounded),
              ),
              ButtonSegment(
                value: TaskGuidanceAudience.ai,
                label: Text('给 AI 用'),
                icon: Icon(Icons.auto_awesome_rounded),
              ),
            ],
            selected: {_selectedAudience},
            onSelectionChanged: (selection) {
              final audience = selection.first;
              unawaited(_selectAudience(audience));
            },
          ),
          const SizedBox(height: DS.spacing12),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: [
              _MetaPill(
                icon: _selectedAudience == TaskGuidanceAudience.human
                    ? Icons.visibility_outlined
                    : Icons.smart_toy_outlined,
                label: _selectedAudience == TaskGuidanceAudience.human
                    ? '默认闭环交付'
                    : '按需生成',
              ),
              if (guidance != null)
                _MetaPill(
                  icon: Icons.update_rounded,
                  label:
                      '更新于 ${DateFormat('MM-dd HH:mm').format(guidance.updatedAt.toLocal())}',
                ),
              if (guidance != null)
                _MetaPill(
                  icon: Icons.policy_outlined,
                  label: guidance.policyVersion,
                ),
              if (stale)
                const _MetaPill(
                  icon: Icons.warning_amber_rounded,
                  label: '任务已变更，建议刷新',
                  tone: _MetaTone.warning,
                ),
            ],
          ),
          const SizedBox(height: DS.spacing16),
          if (!hasContent && !isLoading)
            _GuidanceEmptyState(
              audience: _selectedAudience,
              canGenerate: _canRequestGuidance,
              onGenerate: canRefresh ? _generateSelected : null,
            )
          else
            _GuidanceContent(
              content: hasContent ? content : _loadingText,
              isMarkdown:
                  (guidance?.contentFormat ?? 'markdown').toLowerCase() ==
                          'markdown' &&
                      _selectedAudience == TaskGuidanceAudience.human,
            ),
          if (canRefresh) ...[
            const SizedBox(height: DS.spacing16),
            Row(
              children: [
                Expanded(
                  child: SparkleButton(
                    variant: ButtonVariant.ghost,
                    onPressed: isLoading
                        ? null
                        : () => _generateSelected(regenerate: hasContent),
                    disabled: isLoading,
                    icon: Icon(
                      hasContent
                          ? Icons.refresh_rounded
                          : Icons.auto_awesome_rounded,
                    ),
                    label: _selectedAudience == TaskGuidanceAudience.human
                        ? (hasContent ? '刷新用户版' : '生成用户版')
                        : (hasContent ? '刷新 AI 版' : '生成 AI 版'),
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

class _GuidanceContent extends StatelessWidget {
  const _GuidanceContent({
    required this.content,
    required this.isMarkdown,
  });

  final String content;
  final bool isMarkdown;

  @override
  Widget build(BuildContext context) {
    if (isMarkdown) {
      return Container(
        width: double.infinity,
        padding: const EdgeInsets.all(DS.spacing16),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: DS.borderRadius12,
          border: Border.all(color: DS.neutral200),
          boxShadow: DS.shadowSm,
        ),
        child: SparkleMarkdown(
          content: content,
          textColor: DS.textPrimary,
          codeBackgroundColor: DS.neutral100,
          linkColor: DS.primaryBase,
          contentRole: SparkleMarkdownRole.taskGuide,
        ),
      );
    }
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        color: DS.neutral50,
        borderRadius: DS.borderRadius12,
        border: Border.all(color: DS.neutral200),
      ),
      child: SelectableText(
        content,
        style: DS.bodySmall.copyWith(
          color: DS.textPrimary,
          fontFamily: 'monospace',
          fontFamilyFallback: sparkleFontFallback,
          height: 1.55,
        ),
      ),
    );
  }
}

class _GuidanceEmptyState extends StatelessWidget {
  const _GuidanceEmptyState({
    required this.audience,
    required this.canGenerate,
    required this.onGenerate,
  });

  final TaskGuidanceAudience audience;
  final bool canGenerate;
  final VoidCallback? onGenerate;

  @override
  Widget build(BuildContext context) {
    final isHuman = audience == TaskGuidanceAudience.human;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: DS.borderRadius12,
        border: Border.all(color: DS.neutral200),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            isHuman ? '还没有用户版任务指南' : 'AI 版本尚未生成',
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: DS.fontWeightBold,
                ),
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            isHuman
                ? 'Sparkle 会默认给这张任务准备用户版指南，帮助你直接执行，不需要跳去别的 AI 工具。'
                : '只有你明确需要时，才会生成给 AI 使用的版本，保留当前任务上下文和约束。',
            style: DS.bodySmall.copyWith(
              color: DS.textSecondary,
              height: 1.5,
            ),
          ),
          if (canGenerate && onGenerate != null) ...[
            const SizedBox(height: DS.spacing12),
            SparkleButton(
              variant: ButtonVariant.ghost,
              onPressed: onGenerate,
              disabled: onGenerate == null,
              icon: Icon(
                isHuman ? Icons.auto_awesome_rounded : Icons.smart_toy_outlined,
              ),
              label: isHuman ? '立即生成用户版' : '按需生成 AI 版',
            ),
          ],
        ],
      ),
    );
  }
}

enum _MetaTone { neutral, warning }

class _MetaPill extends StatelessWidget {
  const _MetaPill({
    required this.icon,
    required this.label,
    this.tone = _MetaTone.neutral,
  });

  final IconData icon;
  final String label;
  final _MetaTone tone;

  @override
  Widget build(BuildContext context) {
    final isWarning = tone == _MetaTone.warning;
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing10,
        vertical: DS.spacing6,
      ),
      decoration: BoxDecoration(
        color: isWarning
            ? DS.warning.withValues(alpha: 0.12)
            : DS.surfaceSecondary,
        borderRadius: DS.borderRadiusFull,
        border: Border.all(
          color:
              isWarning ? DS.warning.withValues(alpha: 0.3) : DS.borderSubtle,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            icon,
            size: 14,
            color: isWarning ? DS.warning : DS.textSecondary,
          ),
          const SizedBox(width: DS.spacing6),
          Text(
            label,
            style: DS.labelSmall.copyWith(
              color: isWarning ? DS.warning : DS.textSecondary,
              fontWeight: DS.fontWeightMedium,
            ),
          ),
        ],
      ),
    );
  }
}
