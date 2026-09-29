import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/cognitive/presentation/providers/cognitive_provider.dart';

/// V4-U09：专注结束的「成果或跳过」面。
///
/// 卡口径：结束可记录成果或跳过，**不强制长反思**——
/// - 「跳过」与「记录」是一等路径（同权重按钮，点空白处亦可离开）；
/// - 只有一句可选短字段，没有多字段长表单，字段必填即强制反思（旧
///   ReflectionDialog 的卡点字段必填 + barrierDismissible:false 强制弹层，
///   已随本卡移除）；
/// - 计时口径：展示实际专注分钟（实测），与任务估时分列，估时不顶替实测
///   （与 U08 actualMinutes 同口径）；
/// - 记录失败如实报错（不庆祝），sheet 保持打开，「跳过」始终可用。
///
/// [showFocusSessionOutcomeSheet] 返回是否写入了成果记录（true=记录，
/// false=跳过/留空）。
Future<bool> showFocusSessionOutcomeSheet(
  BuildContext context, {
  required String? taskId,
  required String? taskTitle,
  required int actualMinutes,
  int plannedMinutes = 0,
}) async =>
    await showSensoryDialog<bool>(
      context: context,
      // showSensoryDialog 默认 barrierDismissible=true：点空白处即按「跳过」
      // 离开（本函数 ?? false 兜底）——不存在不可关闭的强制 trap。
      builder: (dialogContext) => FocusSessionOutcomeSheet(
        taskId: taskId,
        taskTitle: taskTitle,
        actualMinutes: actualMinutes,
        plannedMinutes: plannedMinutes,
      ),
    ) ??
    false;

class FocusSessionOutcomeSheet extends ConsumerStatefulWidget {
  const FocusSessionOutcomeSheet({
    required this.actualMinutes,
    this.taskId,
    this.taskTitle,
    this.plannedMinutes = 0,
    super.key,
  });

  final String? taskId;
  final String? taskTitle;
  final int actualMinutes;
  final int plannedMinutes;

  @override
  ConsumerState<FocusSessionOutcomeSheet> createState() =>
      _FocusSessionOutcomeSheetState();
}

class _FocusSessionOutcomeSheetState
    extends ConsumerState<FocusSessionOutcomeSheet> {
  final TextEditingController _outcomeController = TextEditingController();
  bool _isSaving = false;

  @override
  void dispose() {
    _outcomeController.dispose();
    super.dispose();
  }

  /// 「跳过」一等路径：不写任何东西直接离开。
  void _skip() {
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.tap));
    Navigator.of(context).pop(false);
  }

  /// 「记录成果」：留空视同跳过（不强制输入才许离开）。
  Future<void> _record() async {
    final note = _outcomeController.text.trim();
    if (note.isEmpty) {
      _skip();
      return;
    }

    setState(() => _isSaving = true);
    try {
      unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm));
      final zh = I18nService.instance.isChinese;
      final header = zh
          ? '专注成果 · ${widget.taskTitle ?? ''}'
              '（实际 ${widget.actualMinutes} 分钟）'
          : 'Focus outcome · ${widget.taskTitle ?? ''} '
              '(actual ${widget.actualMinutes} min)';
      final fragment = await ref.read(cognitiveProvider.notifier).createFragment(
            content: note.isEmpty ? header : '$header\n$note',
            sourceType: 'reflection',
            taskId: widget.taskId,
          );

      if (!mounted) return;
      if (fragment == null) {
        // 记录失败如实呈现（不庆祝、不假装已保存）；跳过仍可用。
        // N9：用户面用人话（同步失败+可重试），原始 error 留日志。
        debugPrint(
          'Focus outcome fragment not saved: '
          '${ref.read(cognitiveProvider).error}',
        );
        AppFeedback.error(
          context,
          context.l10n.focusReflectionSaveFailed(
            context.l10n.taskExecutionSyncFailed,
          ),
        );
        setState(() => _isSaving = false);
        return;
      }
      Navigator.of(context).pop(true);
      if (mounted) {
        AppFeedback.success(context, context.l10n.focusReflectionSaved);
      }
    } catch (e) {
      // N9：原始异常只进日志；用户面用人话模板（发生什么+影响+可重试）。
      debugPrint('Focus outcome fragment save failed: $e');
      if (mounted) {
        AppFeedback.error(
          context,
          context.l10n.focusReflectionSaveFailed(
            context.l10n.taskExecutionSyncFailed,
          ),
        );
        setState(() => _isSaving = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Dialog(
      backgroundColor: Colors.transparent,
      insetPadding: const EdgeInsets.all(DS.spacing20),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 420),
        child: GraphiteModalSurface(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                l10n.focusReflectionTitle,
                style: DS.titleLarge.copyWith(
                  fontWeight: DS.fontWeightBold,
                  color: DS.textPrimary,
                ),
              ),
              const SizedBox(height: DS.spacing12),
              // 计时口径：实测为主行；估时（若有）只作对照注脚，分列展示，
              // 估时不顶替实测（U08 actualMinutes 同口径的用户可见面）。
              Text(
                l10n.focusOutcomeActualMinutes(widget.actualMinutes),
                style: DS.titleMedium.copyWith(color: DS.textPrimary),
              ),
              if (widget.plannedMinutes > 0) ...[
                const SizedBox(height: DS.spacing4),
                Text(
                  l10n.focusOutcomePlanMinutes(widget.plannedMinutes),
                  style: DS.bodySmall.copyWith(color: DS.textSecondary),
                ),
              ],
              const SizedBox(height: DS.spacing12),
              Text(
                l10n.focusOutcomeHint,
                style: DS.bodySmall.copyWith(
                  color: DS.textSecondary,
                  height: 1.45,
                ),
              ),
              const SizedBox(height: DS.spacing12),
              Text(
                l10n.focusOutcomeFieldLabel,
                style: DS.bodySmall.copyWith(
                  color: DS.textPrimary,
                  fontWeight: DS.fontWeightSemibold,
                ),
              ),
              const SizedBox(height: DS.spacing4),
              TextField(
                key: const Key('focus-outcome-field'),
                controller: _outcomeController,
                maxLines: 2,
                minLines: 1,
                enabled: !_isSaving,
                decoration: InputDecoration(
                  hintText: l10n.focusOutcomeFieldHint,
                  hintStyle: TextStyle(
                    color: DS.textSecondary.withValues(alpha: 0.7),
                  ),
                  enabledBorder: OutlineInputBorder(
                    borderSide: BorderSide(color: DS.borderSubtle),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderSide: BorderSide(color: DS.primaryBase),
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                style: TextStyle(color: DS.textPrimary),
              ),
              const SizedBox(height: DS.spacing16),
              Row(
                children: [
                  // 「跳过」一等路径：与「记录」同权重的可见按钮。
                  Expanded(
                    child: SparkleButton(
                      key: const Key('focus-outcome-skip'),
                      label: l10n.commonSkip,
                      variant: ButtonVariant.ghost,
                      onPressed: _isSaving ? null : _skip,
                    ),
                  ),
                  const SizedBox(width: DS.spacing12),
                  Expanded(
                    child: SparkleButton(
                      key: const Key('focus-outcome-record'),
                      label: l10n.focusOutcomeRecord,
                      loading: _isSaving,
                      onPressed: _isSaving ? null : () { unawaited(_record()); },
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
