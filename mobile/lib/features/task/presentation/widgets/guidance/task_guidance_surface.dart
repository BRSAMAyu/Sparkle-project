import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';
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
  // _loadingText moved to l10n: context.l10n.taskGuidanceLoading
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
        ? context.l10n.taskGuidanceUserLabel
        : context.l10n.taskGuidanceAiLabel;
    try {
      await notifier.createOrRefreshTaskGuidance(
        widget.task.id,
        audience: _selectedAudience,
        regenerate: regenerate,
      );
      if (!mounted) return;
      final zh = I18nService.instance.isChinese;
      AppFeedback.success(
        context,
        regenerate
            ? (zh ? '$label已刷新' : '$label refreshed')
            : (zh ? '$label已生成' : '$label generated'),
      );
    } catch (error) {
      if (!mounted) return;
      AppFeedback.error(
          context, context.l10n.taskGuidanceFailed(label, error.toString()));
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
                      context.l10n.taskGuidanceSubtitle,
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
            segments: [
              ButtonSegment(
                value: TaskGuidanceAudience.human,
                label: Text(context.l10n.taskGuidanceForSelf),
                icon: Icon(Icons.person_outline_rounded),
              ),
              ButtonSegment(
                value: TaskGuidanceAudience.ai,
                label: Text(context.l10n.taskGuidanceForAi),
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
                    ? context.l10n.taskGuidanceDefaultDelivery
                    : context.l10n.taskGuidanceOnDemand,
              ),
              if (guidance != null)
                _MetaPill(
                  icon: Icons.update_rounded,
                  label: context.l10n.taskGuidanceUpdatedAt(
                      DateFormat('MM-dd HH:mm')
                          .format(guidance.updatedAt.toLocal())),
                ),
              if (guidance != null)
                _MetaPill(
                  icon: Icons.policy_outlined,
                  label: guidance.policyVersion,
                ),
              if (stale)
                _MetaPill(
                  icon: Icons.warning_amber_rounded,
                  label: context.l10n.taskGuidanceStaleRefresh,
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
              content: hasContent ? content : context.l10n.taskGuidanceLoading,
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
                        ? (hasContent
                            ? context.l10n.taskGuidanceRefreshUser
                            : context.l10n.taskGuidanceGenerateUser)
                        : (hasContent
                            ? context.l10n.taskGuidanceRefreshAi
                            : context.l10n.taskGuidanceGenerateAi),
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
            isHuman
                ? context.l10n.taskGuidanceNoUserYet
                : context.l10n.taskGuidanceNoAiYet,
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: DS.fontWeightBold,
                ),
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            isHuman
                ? context.l10n.taskGuidanceUserEmpty
                : context.l10n.taskGuidanceAiEmpty,
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
              label: isHuman
                  ? context.l10n.taskGuidanceGenerateNow
                  : context.l10n.taskGuidanceGenerateAiOnDemand,
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
