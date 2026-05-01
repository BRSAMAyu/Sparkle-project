import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/chat/presentation/widgets/causal_timeline_panel.dart';

class ContextReceiptBar extends StatelessWidget {
  const ContextReceiptBar({
    required this.rawMetadata,
    this.onActionSelected,
    super.key,
  });

  final Map<String, dynamic>? rawMetadata;
  final ValueChanged<String>? onActionSelected;

  @override
  Widget build(BuildContext context) {
    final receipt = _parseReceipt();
    if (receipt == null) return const SizedBox.shrink();

    return _ReceiptChip(
      receipt: receipt,
      onActionSelected: onActionSelected,
    );
  }

  Map<String, dynamic>? _parseReceipt() {
    if (rawMetadata == null) return null;
    final raw = rawMetadata!['context_receipt'];
    if (raw == null) return null;
    if (raw is Map<String, dynamic>) return raw;
    if (raw is String) {
      try {
        return json.decode(raw) as Map<String, dynamic>;
      } catch (_) {
        return null;
      }
    }
    return null;
  }
}

class _ReceiptChip extends StatelessWidget {
  const _ReceiptChip({
    required this.receipt,
    required this.onActionSelected,
  });

  final Map<String, dynamic> receipt;
  final ValueChanged<String>? onActionSelected;

  List<String> get _usedNames {
    final raw = receipt['used_names'];
    if (raw is List) return raw.map((e) => e.toString()).toList();
    return [];
  }

  List<String> get _excludedNames {
    final raw = receipt['excluded_names'];
    if (raw is List) return raw.map((e) => e.toString()).toList();
    return [];
  }

  @override
  Widget build(BuildContext context) {
    final usedCount = receipt['used_count'] as int? ?? 0;
    final excludedCount = receipt['excluded_count'] as int? ?? 0;
    final reason = receipt['decision_reason'] as String? ?? '';

    if (usedCount == 0 && reason.isEmpty) return const SizedBox.shrink();

    final hasDetail =
        _usedNames.isNotEmpty || _excludedNames.isNotEmpty || reason.isNotEmpty;

    return GestureDetector(
      onTap: hasDetail
          ? () {
              unawaited(
                SensoryFeedbackService.emit(SensoryFeedbackEvent.tap),
              );
              unawaited(
                showModalBottomSheet<void>(
                  context: context,
                  backgroundColor: Colors.transparent,
                  builder: (_) => _ReceiptDetailSheet(
                    receipt: receipt,
                    usedNames: _usedNames,
                    excludedNames: _excludedNames,
                    onActionSelected: onActionSelected,
                  ),
                ),
              );
            }
          : null,
      child: Container(
        margin: const EdgeInsets.only(top: 6, bottom: 2),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        decoration: BoxDecoration(
          color: DS.surfaceHigh.withValues(alpha: 0.6),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Row(
          children: [
            Icon(Icons.auto_awesome, size: 13, color: DS.brandPrimary),
            const SizedBox(width: 6),
            Expanded(
              child: Text(
                reason.isNotEmpty
                    ? reason
                    : 'Aurora · used $usedCount source${usedCount != 1 ? 's' : ''}${excludedCount > 0 ? ' / skipped $excludedCount' : ''}',
                style: DS.labelSmall.copyWith(color: DS.textSecondary),
                overflow: TextOverflow.ellipsis,
              ),
            ),
            if (usedCount > 0) _SourceCountBadge(count: usedCount),
            if (hasDetail) ...[
              const SizedBox(width: 4),
              Icon(Icons.chevron_right, size: 13, color: DS.textTertiary),
            ],
          ],
        ),
      ),
    );
  }
}

class _SourceCountBadge extends StatelessWidget {
  const _SourceCountBadge({required this.count});

  final int count;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
        decoration: BoxDecoration(
          color: DS.brandPrimary.withValues(alpha: 0.15),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Text(
          '$count',
          style: DS.labelSmall.copyWith(color: DS.brandPrimary, fontSize: 10),
        ),
      );
}

class _ReceiptDetailSheet extends StatelessWidget {
  const _ReceiptDetailSheet({
    required this.receipt,
    required this.usedNames,
    required this.excludedNames,
    required this.onActionSelected,
  });

  final Map<String, dynamic> receipt;
  final List<String> usedNames;
  final List<String> excludedNames;
  final ValueChanged<String>? onActionSelected;

  @override
  Widget build(BuildContext context) {
    final reason = receipt['decision_reason'] as String? ?? '';
    final retrievalMode = receipt['retrieval_mode'] as String? ?? '';

    return Container(
      decoration: BoxDecoration(
        color: DS.surfacePanel,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
      ),
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Center(
            child: Container(
              width: 36,
              height: 4,
              decoration: BoxDecoration(
                color: DS.borderSubtle,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Icon(Icons.auto_awesome, size: 16, color: DS.brandPrimary),
              const SizedBox(width: 8),
              Text(
                context.l10n.chatContextDetail,
                style: DS.bodySmall.copyWith(
                  color: DS.textPrimary,
                  fontWeight: FontWeight.w600,
                ),
              ),
              if (retrievalMode.isNotEmpty) ...[
                const Spacer(),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: DS.brandPrimary.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    retrievalMode,
                    style: DS.labelSmall
                        .copyWith(color: DS.brandPrimary, fontSize: 10),
                  ),
                ),
              ],
            ],
          ),
          if (reason.isNotEmpty) ...[
            const SizedBox(height: 12),
            Text(
              reason,
              style: DS.labelSmall.copyWith(color: DS.textSecondary),
            ),
          ],
          if (usedNames.isNotEmpty) ...[
            const SizedBox(height: 14),
            _SectionHeader(
              icon: Icons.check_circle_outline,
              label: context.l10n.chatContextUsed(usedNames.length),
              color: DS.success,
            ),
            const SizedBox(height: 6),
            ...usedNames.map(
              (name) => _SourceRow(name: name, isUsed: true),
            ),
          ],
          if (excludedNames.isNotEmpty) ...[
            const SizedBox(height: 14),
            _SectionHeader(
              icon: Icons.cancel_outlined,
              label: context.l10n.chatContextUnused(excludedNames.length),
              color: DS.textTertiary,
            ),
            const SizedBox(height: 6),
            ...excludedNames.map(
              (name) => _SourceRow(name: name, isUsed: false),
            ),
          ],
          if (onActionSelected != null) ...[
            const SizedBox(height: 14),
            _ReceiptActionChips(
              usedNames: usedNames,
              onActionSelected: onActionSelected!,
            ),
          ],
          const SizedBox(height: 12),
          // Link to full causal timeline
          GestureDetector(
            onTap: () {
              unawaited(
                SensoryFeedbackService.emit(SensoryFeedbackEvent.tap),
              );
              Navigator.of(context).pop();
              unawaited(
                showModalBottomSheet<void>(
                  context: context,
                  backgroundColor: Colors.transparent,
                  isScrollControlled: true,
                  builder: (_) => DraggableScrollableSheet(
                    expand: false,
                    initialChildSize: 0.7,
                    minChildSize: 0.4,
                    maxChildSize: 0.92,
                    builder: (_, controller) => const CausalTimelinePanel(),
                  ),
                ),
              );
            },
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.timeline, size: 13, color: DS.brandPrimary),
                const SizedBox(width: 4),
                Text(
                  context.l10n.chatContextViewDecisionChain,
                  style: DS.labelSmall.copyWith(color: DS.brandPrimary),
                ),
              ],
            ),
          ),
          const SizedBox(height: 8),
        ],
      ),
    );
  }
}

class _ReceiptActionChips extends StatelessWidget {
  const _ReceiptActionChips({
    required this.usedNames,
    required this.onActionSelected,
  });

  final List<String> usedNames;
  final ValueChanged<String> onActionSelected;

  @override
  Widget build(BuildContext context) {
    final s = I18nService.instance;
    final actions = [
      _ReceiptAction(
        icon: Icons.menu_book_outlined,
        label: s.isChinese ? '按课件重讲' : 'Reteach from slides',
        prompt: s.isChinese
            ? '请按我已上传/选中的课件重新讲一遍，优先引用刚才使用的资料。'
            : 'Please reteach based on my uploaded/selected materials, prioritizing the ones just used.',
      ),
      _ReceiptAction(
        icon: Icons.block_outlined,
        label: s.isChinese ? '排除此资料' : 'Exclude this source',
        prompt: usedNames.isEmpty
            ? (s.isChinese ? '请暂时排除刚才使用的资料，换一种解释。' : 'Please exclude the source just used and explain differently.')
            : (s.isChinese
                ? '请暂时排除这些资料：${usedNames.join('、')}，换一种解释。'
                : 'Please exclude these sources: ${usedNames.join(', ')}, and explain differently.'),
      ),
      _ReceiptAction(
        icon: Icons.history_edu_outlined,
        label: s.isChinese ? '换成历年真题' : 'Use past exams',
        prompt: s.isChinese
            ? '请换成历年真题/典型题视角来讲，并说明为什么这样选资料。'
            : 'Please switch to a past-exam / classic-problem perspective and explain why these sources were chosen.',
      ),
    ];

    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: actions
          .map(
            (action) => _ReceiptActionChip(
              action: action,
              onTap: () {
                unawaited(
                  SensoryFeedbackService.emit(SensoryFeedbackEvent.selection),
                );
                Navigator.of(context).pop();
                onActionSelected(action.prompt);
              },
            ),
          )
          .toList(),
    );
  }
}

class _ReceiptAction {
  const _ReceiptAction({
    required this.icon,
    required this.label,
    required this.prompt,
  });

  final IconData icon;
  final String label;
  final String prompt;
}

class _ReceiptActionChip extends StatelessWidget {
  const _ReceiptActionChip({
    required this.action,
    required this.onTap,
  });

  final _ReceiptAction action;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(8),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
          decoration: BoxDecoration(
            color: DS.surfaceHigh.withValues(alpha: 0.72),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: DS.borderSubtle),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(action.icon, size: 14, color: DS.brandPrimary),
              const SizedBox(width: 5),
              Text(
                action.label,
                style: DS.labelSmall.copyWith(
                  color: DS.textPrimary,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
      );
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({
    required this.icon,
    required this.label,
    required this.color,
  });

  final IconData icon;
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          Icon(icon, size: 13, color: color),
          const SizedBox(width: 5),
          Text(
            label,
            style: DS.labelSmall.copyWith(
              color: color,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      );
}

class _SourceRow extends StatelessWidget {
  const _SourceRow({required this.name, required this.isUsed});

  final String name;
  final bool isUsed;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 4),
        child: Row(
          children: [
            Icon(
              isUsed ? Icons.description_outlined : Icons.block_outlined,
              size: 13,
              color: isUsed
                  ? DS.textSecondary
                  : DS.textTertiary.withValues(alpha: 0.6),
            ),
            const SizedBox(width: 6),
            Expanded(
              child: Text(
                name,
                style: DS.labelSmall.copyWith(
                  color: isUsed ? DS.textSecondary : DS.textTertiary,
                ),
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
      );
}
