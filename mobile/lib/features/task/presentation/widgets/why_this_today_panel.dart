import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/task/data/models/priority_reasoning.dart';
import 'package:sparkle/features/task/data/repositories/priority_reasoning_repository.dart';

class WhyThisTodayPanel extends ConsumerStatefulWidget {
  const WhyThisTodayPanel({
    required this.taskId,
    super.key,
    this.reasoning,
    this.initiallyExpanded = false,
    this.margin = const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
  });

  final String taskId;
  final PriorityReasoning? reasoning;
  final bool initiallyExpanded;
  final EdgeInsetsGeometry margin;

  @override
  ConsumerState<WhyThisTodayPanel> createState() => _WhyThisTodayPanelState();
}

class _WhyThisTodayPanelState extends ConsumerState<WhyThisTodayPanel> {
  late bool _expanded = widget.initiallyExpanded;

  static String _t(String zh, String en) =>
      I18nService.instance.isChinese ? zh : en;

  @override
  Widget build(BuildContext context) {
    if (widget.taskId.isEmpty) return const SizedBox.shrink();

    final asyncReasoning = widget.reasoning == null
        ? ref.watch(priorityReasoningProvider(widget.taskId))
        : AsyncData<PriorityReasoning?>(widget.reasoning);

    return Container(
      margin: widget.margin,
      decoration: BoxDecoration(
        color: DS.surfaceHigh,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: DS.brandPrimary.withValues(alpha: 0.16)),
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          InkWell(
            onTap: () => setState(() => _expanded = !_expanded),
            child: Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: DS.spacing14,
                vertical: DS.spacing12,
              ),
              child: Row(
                children: [
                  Icon(
                    Icons.psychology_alt_outlined,
                    size: 18,
                    color: DS.brandPrimary,
                  ),
                  const SizedBox(width: DS.spacing8),
                  Expanded(
                    child: Text(
                      _t('为什么今天选这个？', 'Why this today?'),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: DS.textPrimary,
                        fontSize: DS.fontSizeSm,
                        fontWeight: DS.fontWeightBold,
                      ),
                    ),
                  ),
                  Icon(
                    _expanded
                        ? Icons.keyboard_arrow_up_rounded
                        : Icons.keyboard_arrow_down_rounded,
                    color: DS.textSecondary,
                  ),
                ],
              ),
            ),
          ),
          AnimatedCrossFade(
            firstChild: const SizedBox.shrink(),
            secondChild: _ExpandedReasoning(asyncReasoning: asyncReasoning),
            crossFadeState: _expanded
                ? CrossFadeState.showSecond
                : CrossFadeState.showFirst,
            duration: const Duration(milliseconds: 180),
          ),
        ],
      ),
    );
  }
}

class _ExpandedReasoning extends StatelessWidget {
  const _ExpandedReasoning({required this.asyncReasoning});

  final AsyncValue<PriorityReasoning?> asyncReasoning;

  static String _t(String zh, String en) =>
      I18nService.instance.isChinese ? zh : en;

  @override
  Widget build(BuildContext context) => asyncReasoning.when(
        loading: () => const Padding(
          padding: EdgeInsets.fromLTRB(
            DS.spacing14,
            0,
            DS.spacing14,
            DS.spacing14,
          ),
          child: LinearProgressIndicator(minHeight: 3),
        ),
        error: (_, __) => Padding(
          padding: const EdgeInsets.fromLTRB(
            DS.spacing14,
            0,
            DS.spacing14,
            DS.spacing14,
          ),
          child: Text(
            _t('暂时无法读取推荐依据', 'Reasoning unavailable for now'),
            style: TextStyle(color: DS.textSecondary, fontSize: DS.fontSizeXs),
          ),
        ),
        data: (reasoning) {
          if (reasoning == null) {
            return Padding(
              padding: const EdgeInsets.fromLTRB(
                DS.spacing14,
                0,
                DS.spacing14,
                DS.spacing14,
              ),
              child: Text(
                _t('正在整理推荐依据', 'Preparing reasoning'),
                style: TextStyle(
                  color: DS.textSecondary,
                  fontSize: DS.fontSizeXs,
                ),
              ),
            );
          }
          return Padding(
            padding: const EdgeInsets.fromLTRB(
              DS.spacing14,
              0,
              DS.spacing14,
              DS.spacing14,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  reasoning.primaryReason,
                  style: TextStyle(
                    color: DS.textPrimary,
                    fontSize: DS.fontSizeMd,
                    fontWeight: DS.fontWeightBold,
                    height: 1.35,
                  ),
                ),
                const SizedBox(height: DS.spacing12),
                ...reasoning.supportingSignals
                    .take(4)
                    .map(_SignalWeightBar.new),
                if (reasoning.alternativeOptionsSkipped.isNotEmpty) ...[
                  const SizedBox(height: DS.spacing8),
                  Text(
                    _t('跳过的备选', 'Skipped options'),
                    style: TextStyle(
                      color: DS.textSecondary,
                      fontSize: DS.fontSizeXs,
                      fontWeight: DS.fontWeightBold,
                    ),
                  ),
                  const SizedBox(height: DS.spacing6),
                  ...reasoning.alternativeOptionsSkipped
                      .take(2)
                      .map(_SkippedOptionRow.new),
                ],
              ],
            ),
          );
        },
      );
}

class _SignalWeightBar extends StatelessWidget {
  const _SignalWeightBar(this.signal);

  final PrioritySignal signal;

  static String _t(String zh, String en) =>
      I18nService.instance.isChinese ? zh : en;

  @override
  Widget build(BuildContext context) {
    final value = signal.weight.clamp(0.0, 1.0);
    return Padding(
      padding: const EdgeInsets.only(bottom: DS.spacing10),
      child: Row(
        children: [
          SizedBox(
            width: 118,
            child: Text(
              _label(signal.type),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                color: DS.textPrimary,
                fontSize: DS.fontSizeXs,
                fontWeight: DS.fontWeightMedium,
              ),
            ),
          ),
          const SizedBox(width: DS.spacing8),
          Expanded(
            child: Tooltip(
              message: signal.detail,
              child: SizedBox(
                height: 8,
                child: LayoutBuilder(
                  builder: (context, constraints) => Stack(
                    children: [
                      Container(
                        decoration: BoxDecoration(
                          color: DS.brandPrimary.withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(999),
                        ),
                      ),
                      AnimatedContainer(
                        duration: const Duration(milliseconds: 220),
                        width: constraints.maxWidth * value,
                        decoration: BoxDecoration(
                          color: DS.brandPrimary,
                          borderRadius: BorderRadius.circular(999),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(width: DS.spacing8),
          SizedBox(
            width: 36,
            child: Text(
              '${(value * 100).round()}%',
              textAlign: TextAlign.right,
              style: TextStyle(color: DS.textSecondary, fontSize: 11),
            ),
          ),
        ],
      ),
    );
  }

  static String _label(String type) {
    switch (type) {
      case 'spaced_repetition':
        return _t('间隔复习', 'Review');
      case 'goal_progress':
        return _t('目标推进', 'Goal');
      case 'energy_match':
        return _t('精力匹配', 'Energy');
      case 'social_context':
        return _t('社群信号', 'Social');
      default:
        return type;
    }
  }
}

class _SkippedOptionRow extends StatelessWidget {
  const _SkippedOptionRow(this.option);

  final AlternativeOptionSkipped option;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: DS.spacing6),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(
              Icons.subdirectory_arrow_right_rounded,
              size: 16,
              color: DS.textSecondary,
            ),
            const SizedBox(width: DS.spacing6),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    option.title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: DS.textPrimary,
                      fontSize: DS.fontSizeXs,
                      fontWeight: DS.fontWeightMedium,
                    ),
                  ),
                  Text(
                    option.reason,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: DS.textSecondary,
                      fontSize: 11,
                      height: 1.25,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
}
