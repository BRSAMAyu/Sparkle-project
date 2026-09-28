import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

/// 目标上下文头（旅程页钉子）：从目标进入的每一面都携带「当前目标 +
/// 继续当前动作」——不回到空白搜索页丢上下文（SCREEN_FAMILIES「星图/学习/错题/
/// 资料」段；U10 验收1 的呈现面）。
class LearningContextHeader extends StatelessWidget {
  const LearningContextHeader({
    required this.goalTitle,
    required this.continueLabel,
    required this.onContinue,
    super.key,
    this.segmentBadgeLabel,
  });

  final String goalTitle;
  final String continueLabel;
  final VoidCallback onContinue;

  /// 当前段徽标（如「练习」/「检验」；空则不显示）。
  final String? segmentBadgeLabel;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = context.l10n;
    return Container(
      key: const Key('learning_context_header'),
      width: double.infinity,
      padding: const EdgeInsets.all(DS.md),
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: theme.dividerColor),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Semantics(
            label: l10n.learningContextGoalSemantics(goalTitle),
            child: Row(
              children: [
                Icon(Icons.flag_rounded, size: 18, color: DS.textSecondary),
                const SizedBox(width: DS.xs),
                Expanded(
                  child: Text(
                    goalTitle,
                    style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                if (segmentBadgeLabel != null && segmentBadgeLabel!.isNotEmpty)
                  Container(
                    key: const Key('learning_segment_badge'),
                    padding: const EdgeInsets.symmetric(horizontal: DS.sm, vertical: DS.xs),
                    decoration: BoxDecoration(
                      color: DS.brandPrimary.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(999),
                    ),
                    child: Text(
                      segmentBadgeLabel!,
                      style: theme.textTheme.labelSmall?.copyWith(color: DS.brandPrimary),
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(height: DS.sm),
          // 读屏语义：FilledButton 自带文本朗读（button=true），不重复包
          // Semantics label（否则「继续当前动作：…」播报两遍）。
          SizedBox(
            width: double.infinity,
            child: FilledButton.tonal(
              key: const Key('learning_continue_action'),
              onPressed: onContinue,
              child: Text(continueLabel),
            ),
          ),
        ],
      ),
    );
  }
}
