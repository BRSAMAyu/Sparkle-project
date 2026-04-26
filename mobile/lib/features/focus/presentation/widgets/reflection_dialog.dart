import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/cognitive/presentation/providers/cognitive_provider.dart';

class ReflectionDialog extends ConsumerStatefulWidget {
  const ReflectionDialog({super.key});

  @override
  ConsumerState<ReflectionDialog> createState() => _ReflectionDialogState();
}

class _ReflectionDialogState extends ConsumerState<ReflectionDialog> {
  final TextEditingController _stuckController = TextEditingController();
  final TextEditingController _methodController = TextEditingController();
  final TextEditingController _adjustmentController = TextEditingController();
  bool _isSubmitting = false;

  Future<void> _submit() async {
    if (_stuckController.text.trim().isEmpty) return;

    setState(() => _isSubmitting = true);

    try {
      unawaited(
        SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm),
      );
      final content = _buildReflectionContent();

      await ref.read(cognitiveProvider.notifier).createFragment(
            content: content,
            sourceType: 'reflection',
          );

      if (mounted) {
        context.pop(true);
        AppFeedback.success(context, context.l10n.focusReflectionSaved);
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

  String _buildReflectionContent() {
    final parts = <String>[
      '专注复盘',
      '卡点：${_stuckController.text.trim()}',
    ];
    if (_methodController.text.trim().isNotEmpty) {
      parts.add('有效方法：${_methodController.text.trim()}');
    }
    if (_adjustmentController.text.trim().isNotEmpty) {
      parts.add('下次调整：${_adjustmentController.text.trim()}');
    }
    return parts.join('\n');
  }

  String _copyForLocale({
    required String zh,
    required String en,
  }) {
    final code = Localizations.localeOf(context).languageCode.toLowerCase();
    return code.startsWith('zh') ? zh : en;
  }

  @override
  void dispose() {
    _stuckController.dispose();
    _methodController.dispose();
    _adjustmentController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
        backgroundColor: DS.deepSpaceEnd,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Text(
          context.l10n.focusReflectionTitle,
          style: TextStyle(
            color: DS.brandPrimaryConst,
            fontWeight: FontWeight.bold,
          ),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              _copyForLocale(
                zh: '花半分钟记一下这次卡点，我会把它留给之后的你。',
                en: 'Take half a minute to capture the friction so future-you can use it.',
              ),
              style: TextStyle(color: DS.brandPrimaryConst),
            ),
            const SizedBox(height: 16),
            _ReflectionPromptField(
              label: _copyForLocale(
                zh: '这个任务中你卡在哪里了？',
                en: 'Where did you get stuck in this session?',
              ),
              hint: _copyForLocale(
                zh: '例如：刚坐下还行，但一写题就不知道从哪里下手',
                en: 'Example: once I started, I did not know how to begin.',
              ),
              controller: _stuckController,
              onChanged: (_) => setState(() {}),
            ),
            const SizedBox(height: 12),
            _ReflectionPromptField(
              label: _copyForLocale(
                zh: '哪个方法让你觉得有进展？',
                en: 'What helped you feel progress?',
              ),
              hint: _copyForLocale(
                zh: '例如：先把题目条件圈出来，再动笔',
                en: 'Example: marking the givens before solving.',
              ),
              controller: _methodController,
            ),
            const SizedBox(height: 12),
            _ReflectionPromptField(
              label: _copyForLocale(
                zh: '下次会换什么做法？',
                en: 'What would you change next time?',
              ),
              hint: _copyForLocale(
                zh: '例如：先做 5 分钟预热，再开始正式专注',
                en: 'Example: do a five-minute warm-up before deep focus.',
              ),
              controller: _adjustmentController,
            ),
          ],
        ),
        actions: [
          SparkleButton(
            label: context.l10n.commonSkip,
            variant: ButtonVariant.ghost,
            onPressed: () => context.pop(false),
          ),
          SparkleButton(
            label: context.l10n.commonSave,
            loading: _isSubmitting,
            onPressed: _stuckController.text.trim().isNotEmpty && !_isSubmitting
                ? () {
                    unawaited(_submit());
                  }
                : null,
          ),
        ],
      );
}

class _ReflectionPromptField extends StatelessWidget {
  const _ReflectionPromptField({
    required this.label,
    required this.hint,
    required this.controller,
    this.onChanged,
  });

  final String label;
  final String hint;
  final TextEditingController controller;
  final ValueChanged<String>? onChanged;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: TextStyle(
              color: DS.brandPrimaryConst,
              fontWeight: DS.fontWeightSemibold,
            ),
          ),
          const SizedBox(height: 8),
          TextField(
            controller: controller,
            onChanged: onChanged,
            maxLines: 3,
            decoration: InputDecoration(
              hintText: hint,
              hintStyle: TextStyle(
                color: DS.brandPrimary.withValues(alpha: 0.5),
              ),
              enabledBorder: OutlineInputBorder(
                borderSide: BorderSide(
                  color: DS.brandPrimary.withValues(alpha: 0.3),
                ),
                borderRadius: BorderRadius.circular(12),
              ),
              focusedBorder: OutlineInputBorder(
                borderSide: BorderSide(color: DS.brandPrimary),
                borderRadius: const BorderRadius.all(Radius.circular(12)),
              ),
            ),
            style: TextStyle(color: DS.brandPrimaryConst),
          ),
        ],
      );
}
