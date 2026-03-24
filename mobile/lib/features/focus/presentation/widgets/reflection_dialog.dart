import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/utils/theme_utils.dart';
import 'package:sparkle/features/cognitive/presentation/providers/cognitive_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';

class ReflectionDialog extends ConsumerStatefulWidget {
  const ReflectionDialog({super.key});

  @override
  ConsumerState<ReflectionDialog> createState() => _ReflectionDialogState();
}

class _ReflectionDialogState extends ConsumerState<ReflectionDialog> {
  String? _feeling;
  final TextEditingController _noteController = TextEditingController();
  bool _isSubmitting = false;

  Future<void> _submit() async {
    if (_feeling == null) return;

    setState(() => _isSubmitting = true);

    try {
      unawaited(
        SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm),
      );
      final l10n = context.l10n;
      final content = l10n.focusReflectionSummary(
        _feelingLabel(l10n, _feeling!),
        _noteController.text,
      );

      // Create Fragment
      await ref.read(cognitiveProvider.notifier).createFragment(
            content: content,
            sourceType: 'reflection',
            // taskId: we could pass task id if available
          );

      if (mounted) {
        context.pop(true);
        AppFeedback.success(context, l10n.focusReflectionSaved);
      }
    } catch (e) {
      if (mounted) {
        AppFeedback.error(
          context,
          context.l10n.focusReflectionSaveFailed(e.toString()),
        );
      }
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  void dispose() {
    _noteController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final moods = _moodOptions(l10n);
    return AlertDialog(
      backgroundColor: DS.deepSpaceEnd,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      title: Text(
        l10n.focusReflectionTitle,
        style: TextStyle(
          color: DS.brandPrimaryConst,
          fontWeight: FontWeight.bold,
        ),
      ),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SparkleStaggerItem(
            index: 0,
            child: Text(
              l10n.focusReflectionPrompt,
              style: TextStyle(color: DS.brandPrimaryConst),
            ),
          ),
          const SizedBox(height: 12),
          SparkleStaggerWrap(
            children: moods
                .map(
                  (entry) => ChoiceChip(
                    label: Text(entry.$2),
                    selected: _feeling == entry.$1,
                    onSelected: (b) {
                      unawaited(
                        SensoryFeedbackService.emit(
                          SensoryFeedbackEvent.selection,
                        ),
                      );
                      setState(() => _feeling = b ? entry.$1 : null);
                    },
                    backgroundColor: DS.brandPrimary.withValues(alpha: 0.1),
                    selectedColor: DS.brandPrimary,
                    labelStyle: TextStyle(
                      color: _feeling == entry.$1
                          ? ThemeUtils.getContrastSafeText(
                              DS.brandPrimary,
                              darkText: DS.textPrimary,
                            )
                          : DS.brandPrimaryConst,
                    ),
                  ),
                )
                .toList(),
          ),
          const SizedBox(height: 16),
          SparkleStaggerItem(
            index: 1,
            child: TextField(
              controller: _noteController,
              decoration: InputDecoration(
                hintText: l10n.focusReflectionNoteHint,
                hintStyle:
                    TextStyle(color: DS.brandPrimary.withValues(alpha: 0.5)),
                enabledBorder: OutlineInputBorder(
                  borderSide:
                      BorderSide(color: DS.brandPrimary.withValues(alpha: 0.3)),
                  borderRadius: BorderRadius.circular(12),
                ),
                focusedBorder: OutlineInputBorder(
                  borderSide: BorderSide(color: DS.brandPrimary),
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
              style: TextStyle(color: DS.brandPrimaryConst),
              maxLines: 2,
            ),
          ),
        ],
      ),
      actions: [
        SparkleButton(
          label: l10n.commonSkip,
          variant: ButtonVariant.ghost,
          onPressed: () => context.pop(false),
        ),
        SparkleButton(
          label: l10n.commonSave,
          loading: _isSubmitting,
          onPressed: _feeling != null && !_isSubmitting
              ? () {
                  unawaited(_submit());
                }
              : null,
        ),
      ],
    );
  }

  List<(String, String)> _moodOptions(AppLocalizations l10n) => [
        ('flow', l10n.focusReflectionMoodFlow),
        ('focused', l10n.focusReflectionMoodFocused),
        ('okay', l10n.focusReflectionMoodOkay),
        ('distracted', l10n.focusReflectionMoodDistracted),
        ('tired', l10n.focusReflectionMoodTired),
      ];

  String _feelingLabel(AppLocalizations l10n, String code) {
    for (final mood in _moodOptions(l10n)) {
      if (mood.$1 == code) {
        return mood.$2;
      }
    }
    return code;
  }
}
