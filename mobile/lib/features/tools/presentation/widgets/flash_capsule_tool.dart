// ignore_for_file: discarded_futures, unawaited_futures

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/cognitive/data/models/cognitive_fragment_model.dart';
import 'package:sparkle/features/cognitive/presentation/providers/cognitive_provider.dart';
import 'package:sparkle/features/error_book/error_book.dart';
import 'package:sparkle/features/tools/models/tool_definition.dart';
import 'package:sparkle/features/tools/presentation/widgets/tool_shell.dart';
import 'package:sparkle/shared/entities/cognitive_analysis.dart';

const List<String> _errorTypes = [
  'concept_confusion',
  'calculation_error',
  'misreading',
  'knowledge_fading',
  'wrong_method',
  'other',
];

String _errorTypeLabel(AppLocalizations l, String key) => switch (key) {
  'concept_confusion' => l.fcConceptConfusion,
  'calculation_error' => l.fcCalculationError,
  'misreading' => l.fcMisreading,
  'knowledge_fading' => l.fcKnowledgeFading,
  'wrong_method' => l.fcWrongMethod,
  _ => l.fcOther,
};

class _SubjectOption {
  const _SubjectOption(this.code);

  final String code;
}

const List<_SubjectOption> _subjectOptions = [
  _SubjectOption('math'),
  _SubjectOption('physics'),
  _SubjectOption('chemistry'),
  _SubjectOption('biology'),
  _SubjectOption('english'),
  _SubjectOption('chinese'),
  _SubjectOption('computer'),
  _SubjectOption('other'),
];

String _subjectLabel(AppLocalizations l, String code) => switch (code) {
  'math' => l.fcSubjectMath,
  'physics' => l.fcSubjectPhysics,
  'chemistry' => l.fcSubjectChemistry,
  'biology' => l.fcSubjectBiology,
  'english' => l.fcSubjectEnglish,
  'chinese' => l.fcSubjectChinese,
  'computer' => l.fcSubjectComputer,
  _ => l.fcOther,
};

class FlashCapsuleTool extends ConsumerStatefulWidget {
  const FlashCapsuleTool({
    super.key,
    this.taskId,
    this.initialSubject,
    this.surface = ToolSurface.page,
  });

  final String? taskId;
  final String? initialSubject;
  final ToolSurface surface;

  @override
  ConsumerState<FlashCapsuleTool> createState() => _FlashCapsuleToolState();
}

class _FlashCapsuleToolState extends ConsumerState<FlashCapsuleTool> {
  final _topicController = TextEditingController();
  final _descriptionController = TextEditingController();

  late String _selectedSubjectCode;
  String _selectedErrorType = _errorTypes[0];
  bool _isSubmitting = false;

  @override
  void initState() {
    super.initState();
    _selectedSubjectCode = _resolveInitialSubject(widget.initialSubject);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      unawaited(_loadHistory());
    });
  }

  @override
  void dispose() {
    _topicController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  String _resolveInitialSubject(String? initialSubject) {
    if (initialSubject == null || initialSubject.trim().isEmpty) {
      return _subjectOptions.first.code;
    }
    final normalized = initialSubject.trim().toLowerCase();
    final match = _subjectOptions.cast<_SubjectOption?>().firstWhere(
          (subject) => subject!.code == normalized,
          orElse: () => null,
        );
    return match?.code ?? _subjectOptions.first.code;
  }

  CognitiveDimension _inferCognitiveDimension() {
    switch (_selectedErrorType) {
      case 'concept_confusion':
      case 'knowledge_fading':
        return CognitiveDimension.memory;
      case 'calculation_error':
      case 'wrong_method':
        return CognitiveDimension.application;
      case 'misreading':
        return CognitiveDimension.analysis;
      default:
        return CognitiveDimension.analysis;
    }
  }

  Future<void> _loadHistory({bool silent = true}) async {
    try {
      await ref.read(cognitiveProvider.notifier).loadFragments(limit: 50);
    } catch (e) {
      if (!silent && mounted) {
        AppFeedback.error(context, context.l10n.toolsFlashLoadFailed(e.toString()));
      }
    }
  }

  List<CognitiveFragmentModel> _historyEntries(
    List<CognitiveFragmentModel> items,
  ) {
    final result = items
        .where(
          (item) =>
              item.sourceType == 'flash_capsule' ||
              item.sourceType == 'capsule',
        )
        .toList()
      ..sort((left, right) => right.createdAt.compareTo(left.createdAt));
    return result;
  }

  Future<void> _openHistory() async {
    await _loadHistory(silent: false);
    if (!mounted) {
      return;
    }

    final history = _historyEntries(ref.read(cognitiveProvider).fragments);

    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) {
        final theme = Theme.of(context);
        return SafeArea(
          child: Container(
            constraints: BoxConstraints(
              maxHeight: MediaQuery.of(context).size.height * 0.8,
            ),
            decoration: BoxDecoration(
              color: DS.surfacePrimary,
              borderRadius: const BorderRadius.vertical(
                top: Radius.circular(28),
              ),
            ),
            child: Padding(
              padding: const EdgeInsets.fromLTRB(
                DS.spacing20,
                DS.spacing16,
                DS.spacing20,
                DS.spacing24,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Center(
                    child: Container(
                      width: 42,
                      height: 4,
                      decoration: BoxDecoration(
                        color: DS.border,
                        borderRadius: DS.borderRadiusFull,
                      ),
                    ),
                  ),
                  const SizedBox(height: DS.spacing16),
                  Text(
                    context.l10n.flashCapsuleHistory,
                    style: theme.textTheme.titleLarge?.copyWith(
                      fontWeight: DS.fontWeightBold,
                    ),
                  ),
                  const SizedBox(height: DS.spacing8),
                  Text(
                    history.isEmpty ? context.l10n.flashCapsuleHistoryEmpty : context.l10n.flashCapsuleHistoryDesc,
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: DS.textSecondary,
                      height: 1.5,
                    ),
                  ),
                  const SizedBox(height: DS.spacing16),
                  Expanded(
                    child: history.isEmpty
                        ? ToolEmptyState(
                            icon: Icons.history_rounded,
                            title: context.l10n.flashCapsuleNoHistory,
                            description: context.l10n.flashCapsuleNoHistoryDesc,
                            accentColor: DS.warning,
                          )
                        : ListView.separated(
                            itemCount: history.length,
                            separatorBuilder: (_, __) =>
                                const SizedBox(height: DS.spacing12),
                            itemBuilder: (context, index) {
                              final item = history[index];
                              final lines = item.content
                                  .split('\n')
                                  .map((line) => line.trim())
                                  .where((line) => line.isNotEmpty)
                                  .toList(growable: false);
                              final title =
                                  lines.isEmpty ? context.l10n.flashCapsuleUnnamed : lines.first;
                              final detail = lines.length > 1
                                  ? lines.skip(1).join('\n')
                                  : context.l10n.flashCapsuleNoDesc;
                              final pending = (item.tags ?? const <String>[])
                                  .contains('pending_sync');

                              return DecoratedBox(
                                decoration: BoxDecoration(
                                  color: DS.surfaceSecondary,
                                  borderRadius: DS.borderRadius16,
                                  border: Border.all(color: DS.border),
                                ),
                                child: Padding(
                                  padding: const EdgeInsets.all(DS.spacing16),
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Row(
                                        children: [
                                          Expanded(
                                            child: Text(
                                              title,
                                              style: theme.textTheme.titleMedium
                                                  ?.copyWith(
                                                fontWeight: DS.fontWeightBold,
                                              ),
                                            ),
                                          ),
                                          _HistoryChip(
                                            label: item.sourceType ==
                                                    'flash_capsule'
                                                ? context.l10n.flashCapsuleTagFlash
                                                : context.l10n.flashCapsuleTagThink,
                                          ),
                                          if (pending) ...[
                                            const SizedBox(width: DS.spacing8),
                                            _HistoryChip(label: context.l10n.flashCapsuleSyncPending),
                                          ],
                                        ],
                                      ),
                                      const SizedBox(height: DS.spacing10),
                                      Text(
                                        detail,
                                        style: theme.textTheme.bodyMedium
                                            ?.copyWith(
                                          color: DS.textSecondary,
                                          height: 1.5,
                                        ),
                                      ),
                                      const SizedBox(height: DS.spacing10),
                                      Text(
                                        _formatTimestamp(item.createdAt),
                                        style: theme.textTheme.labelSmall
                                            ?.copyWith(
                                          color: DS.textTertiary,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              );
                            },
                          ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  Future<void> _submit() async {
    final topic = _topicController.text.trim();
    final description = _descriptionController.text.trim();
    if (topic.isEmpty || description.isEmpty) {
      AppFeedback.info(context, context.l10n.fcFillRequired);
      return;
    }

    if (mounted) {
      setState(() => _isSubmitting = true);
    }

    try {
      final selectedSubject = _subjectOptions.firstWhere(
        (item) => item.code == _selectedSubjectCode,
        orElse: () => _subjectOptions.first,
      );
      final fragment =
          await ref.read(cognitiveProvider.notifier).createFragment(
                content: '[$_selectedErrorType] $topic\n$description',
                sourceType: 'flash_capsule',
                taskId: widget.taskId,
              );
      if (fragment == null) {
        throw Exception(context.l10n.fcSaveFailed);
      }

      var syncedToErrorBook = true;
      try {
        await ref.read(errorOperationsProvider.notifier).createError(
              questionText: topic,
              userAnswer: description,
              subject: selectedSubject.code,
              chapter: selectedSubject.code,
            );
      } catch (_) {
        syncedToErrorBook = false;
      }

      await _loadHistory();

      unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.success));
      if (mounted) {
        Navigator.pop(context);
        if (syncedToErrorBook) {
          AppFeedback.success(context, context.l10n.fcSavedWithSync);
        } else {
          AppFeedback.info(context, context.l10n.fcSavedSyncLater);
        }
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isSubmitting = false);
        AppFeedback.error(context, context.l10n.toolsFlashSaveFailed(e.toString()));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final accent = DS.warning;
    final cognitiveState = ref.watch(cognitiveProvider);
    final historyCount = _historyEntries(cognitiveState.fragments).length;
    return ToolShell(
      surface: widget.surface,
      icon: Icons.lightbulb_outline_rounded,
      title: context.l10n.toolsFlashTitle,
      subtitle: context.l10n.toolsFlashSubtitle,
      accentColor: accent,
      compactHeader: true,
      heroChips: [
        ToolHeroChip(
          label: context.l10n.toolsFlashSubjectCount(_subjectOptions.length),
          accentColor: accent,
          icon: Icons.category_rounded,
        ),
        ToolHeroChip(
          label: _selectedErrorType,
          accentColor: accent,
          icon: Icons.label_rounded,
        ),
        ToolHeroChip(
          label: historyCount == 0 ? context.l10n.flashCapsuleNoHistory : context.l10n.fcHistoryCount(historyCount),
          accentColor: accent,
          icon: Icons.history_rounded,
        ),
      ],
      body: Column(
        children: [
          ToolSectionCard(
            accentColor: accent,
            title: context.l10n.toolsFlashContent,
            subtitle: context.l10n.toolsFlashContentDesc,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _SubjectDropdown(
                  value: _selectedSubjectCode,
                  subjects: _subjectOptions,
                  onChanged: (value) {
                    if (value == null) {
                      return;
                    }
                    setState(() => _selectedSubjectCode = value);
                  },
                ),
                const SizedBox(height: DS.spacing16),
                TextField(
                  controller: _topicController,
                  decoration: InputDecoration(
                    labelText: context.l10n.toolsFlashKnowledge,
                    hintText: context.l10n.toolsFlashKnowledgeHint,
                  ),
                  onChanged: (_) => setState(() {}),
                ),
                const SizedBox(height: DS.spacing16),
                Align(
                  alignment: Alignment.centerLeft,
                  child: Wrap(
                    spacing: DS.spacing10,
                    runSpacing: DS.spacing10,
                    children: _errorTypes
                        .map(
                          (type) => ToolChoiceChip(
                            label: _errorTypeLabel(context.l10n, type),
                            selected: _selectedErrorType == type,
                            onTap: () => setState(() {
                              _selectedErrorType = type;
                            }),
                            accentColor: accent,
                          ),
                        )
                        .toList(),
                  ),
                ),
                const SizedBox(height: DS.spacing16),
                TextField(
                  controller: _descriptionController,
                  maxLines: 8,
                  decoration: InputDecoration(
                    labelText: context.l10n.toolsFlashErrorDesc,
                    hintText: context.l10n.toolsFlashErrorDescHint,
                    alignLabelWithHint: true,
                  ),
                  onChanged: (_) => setState(() {}),
                ),
              ],
            ),
          ),
          const SizedBox(height: DS.spacing16),
          ToolMetricRow(
            children: [
              ToolMetricCard(
                label: context.l10n.toolsFlashKnowledgeLen,
                value: '${_topicController.text.trim().length}',
                accentColor: accent,
                icon: Icons.topic_rounded,
              ),
              ToolMetricCard(
                label: context.l10n.toolsFlashDescLen,
                value: '${_descriptionController.text.trim().length}',
                accentColor: accent,
                icon: Icons.notes_rounded,
              ),
              ToolMetricCard(
                label: context.l10n.toolsFlashCognitiveDim,
                value: _inferCognitiveDimension().label,
                accentColor: accent,
                icon: Icons.psychology_alt_rounded,
              ),
            ],
          ),
        ],
      ),
      footer: LayoutBuilder(
        builder: (context, constraints) {
          final compact = constraints.maxWidth < 520;
          final historyButton = SparkleButton(
            label: context.l10n.toolsFlashViewHistory,
            variant: ButtonVariant.ghost,
            onPressed: _isSubmitting ? null : _openHistory,
            icon: const Icon(Icons.history_rounded),
            expand: true,
          );
          final saveButton = SparkleButton(
            label: _isSubmitting ? context.l10n.fcRecording : context.l10n.toolsFlashSaveCapsule,
            onPressed: _isSubmitting ? null : _submit,
            icon: const Icon(Icons.check_rounded),
            loading: _isSubmitting,
            expand: true,
          );

          if (compact) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                historyButton,
                const SizedBox(height: DS.spacing12),
                saveButton,
              ],
            );
          }

          return Row(
            children: [
              Expanded(child: historyButton),
              const SizedBox(width: DS.spacing12),
              Expanded(child: saveButton),
            ],
          );
        },
      ),
    );
  }

  String _formatTimestamp(DateTime value) {
    final month = value.month.toString().padLeft(2, '0');
    final day = value.day.toString().padLeft(2, '0');
    final hour = value.hour.toString().padLeft(2, '0');
    final minute = value.minute.toString().padLeft(2, '0');
    return '${value.year}-$month-$day $hour:$minute';
  }
}

class _SubjectDropdown extends StatelessWidget {
  const _SubjectDropdown({
    required this.value,
    required this.subjects,
    required this.onChanged,
  });

  final String value;
  final List<_SubjectOption> subjects;
  final ValueChanged<String?> onChanged;

  @override
  Widget build(BuildContext context) => DecoratedBox(
        decoration: BoxDecoration(
          color: DS.surfacePrimary,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: DS.spacing12),
          child: DropdownButtonHideUnderline(
            child: DropdownButton<String>(
              value: value,
              isExpanded: true,
              hint: Text(context.l10n.toolsFlashSelectSubject),
              items: subjects
                  .map(
                    (subject) => DropdownMenuItem<String>(
                      value: subject.code,
                      child: Text(_subjectLabel(AppLocalizations.of(context)!, subject.code)),
                    ),
                  )
                  .toList(),
              onChanged: onChanged,
            ),
          ),
        ),
      );
}

class _HistoryChip extends StatelessWidget {
  const _HistoryChip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) => DecoratedBox(
        decoration: BoxDecoration(
          color: DS.warning.withValues(alpha: 0.12),
          borderRadius: DS.borderRadiusFull,
        ),
        child: Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing8,
            vertical: DS.spacing4,
          ),
          child: Text(
            label,
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
                  color: DS.warning,
                  fontWeight: DS.fontWeightBold,
                ),
          ),
        ),
      );
}
