import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/memory_api_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/chat/presentation/widgets/causal_timeline_panel.dart';

class AuroraReceiptChip extends StatefulWidget {
  const AuroraReceiptChip({
    required this.receipt,
    this.onActionSelected,
    super.key,
  });

  final Map<String, dynamic> receipt;
  final ValueChanged<String>? onActionSelected;

  @override
  State<AuroraReceiptChip> createState() => _AuroraReceiptChipState();
}

class _AuroraReceiptChipState extends State<AuroraReceiptChip> {
  bool _dismissed = false;

  String get _dismissKey {
    final id = widget.receipt['receipt_id']?.toString() ??
        widget.receipt['response_id']?.toString() ??
        '';
    return 'aurora_receipt_dismissed_$id';
  }

  @override
  void initState() {
    super.initState();
    _restoreDismissState();
  }

  Future<void> _restoreDismissState() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      if (!mounted) return;
      final dismissed = prefs.getBool(_dismissKey) ?? false;
      if (dismissed && !_dismissed) {
        setState(() => _dismissed = true);
      }
    } catch (_) {}
  }

  Future<void> _persistDismiss() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool(_dismissKey, true);
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    if (_dismissed) return const SizedBox.shrink();

    final receipt = widget.receipt;
    final onActionSelected = widget.onActionSelected;
    final receiptType = normalizeAuroraReceiptType(receipt);

    final isSocialSource = receiptType == kSourceContextReceiptType &&
        receipt['source_kind'] == 'social';
    final isMemory = receiptType == kMemoryReferenceReceiptType;
    final isSource = receiptType == kSourceContextReceiptType;
    final isNextAction = receiptType == kNextActionReceiptType;

    final memories = _parseMemories(receipt);
    final usedNames = _parseUsedNames(receipt);
    final excludedNames = _parseExcludedNames(receipt);
    final usedTools = _parseUsedTools(receipt);
    final whatChanged = _parseWhatChanged(receipt);
    final usedCount = (receipt['used_count'] as int? ?? 0) +
        (receipt['tool_count'] as int? ?? usedTools.length);

    if (isMemory && memories.isEmpty) return const SizedBox.shrink();
    if (isSource &&
        usedCount == 0 &&
        !_hasDetailContent(receipt, memories, usedNames, excludedNames,
            usedTools, whatChanged)) {
      return const SizedBox.shrink();
    }

    final summary = _summary(context, receipt, isMemory, isSocialSource,
        isSource, isNextAction, memories, usedCount, excludedNames);
    if (summary.isEmpty) return const SizedBox.shrink();

    final hasDetail = _hasDetailContent(
        receipt, memories, usedNames, excludedNames, usedTools, whatChanged);
    final icon = _iconFor(isMemory, isSocialSource, isSource, isNextAction);
    final title = _title(
        context, receipt, isMemory, isSocialSource, isSource, isNextAction);

    return Semantics(
      button: hasDetail,
      liveRegion: true,
      label: summary,
      child: Container(
        margin: const EdgeInsets.only(top: 6, bottom: 2),
        child: Semantics(
          button: true,
          label: 'Chat aurora receipt chip control 1',
          child: InkWell(
            borderRadius: BorderRadius.circular(8),
            onTap: hasDetail
                ? () {
                    unawaited(
                      SensoryFeedbackService.emit(SensoryFeedbackEvent.tap),
                    );
                    unawaited(
                      showModalBottomSheet<void>(
                        context: context,
                        backgroundColor: Colors.transparent,
                        isScrollControlled: true,
                        builder: (_) => _AuroraReceiptDetailSheet(
                          receipt: receipt,
                          receiptType: receiptType,
                          title: title,
                          summary: summary,
                          icon: icon,
                          memories: memories,
                          usedNames: usedNames,
                          excludedNames: excludedNames,
                          usedTools: usedTools,
                          whatChanged: whatChanged,
                          isSocialSource: isSocialSource,
                          onActionSelected: onActionSelected,
                        ),
                      ),
                    );
                  }
                : null,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
              decoration: BoxDecoration(
                color: DS.surfaceHigh.withValues(alpha: 0.6),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: DS.borderSubtle),
              ),
              child: Row(
                children: [
                  Icon(icon, size: 13, color: DS.brandPrimary),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      summary,
                      style: DS.labelSmall.copyWith(color: DS.textSecondary),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  if (isMemory && memories.isNotEmpty)
                    _CountBadge(count: memories.length),
                  if (isSource && usedCount > 0) _CountBadge(count: usedCount),
                  if (hasDetail) ...[
                    const SizedBox(width: 4),
                    Icon(Icons.chevron_right, size: 13, color: DS.textTertiary),
                  ],
                  Semantics(
                    button: true,
                    label: S.chatReceiptDismiss,
                    child: GestureDetector(
                      onTap: () {
                        unawaited(SensoryFeedbackService.emit(
                            SensoryFeedbackEvent.selection));
                        setState(() => _dismissed = true);
                        unawaited(_persistDismiss());
                      },
                      child: Padding(
                        padding: const EdgeInsets.only(left: 4),
                        child: Icon(Icons.close_rounded,
                            size: 13, color: DS.textTertiary),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

// ── Parsed receipt helpers ────────────────────────────────────

List<Map<String, dynamic>> _parseMemories(Map<String, dynamic> receipt) {
  final raw = receipt['referenced_memories'];
  if (raw is! List) return const [];
  return raw
      .whereType<Map<Object?, Object?>>()
      .map(Map<String, dynamic>.from)
      .where((item) => (item['content']?.toString().trim() ?? '').isNotEmpty)
      .take(5)
      .toList(growable: false);
}

List<String> _parseUsedNames(Map<String, dynamic> receipt) {
  final raw = receipt['used_names'];
  if (raw is List) return raw.map((item) => item.toString()).toList();
  final events = receipt['events'];
  if (events is List) {
    return events
        .whereType<Map<String, dynamic>>()
        .map((event) => event['label']?.toString() ?? '')
        .where((label) => label.isNotEmpty)
        .toSet()
        .toList();
  }
  return const [];
}

List<String> _parseExcludedNames(Map<String, dynamic> receipt) {
  final raw = receipt['excluded_names'];
  if (raw is List) return raw.map((item) => item.toString()).toList();
  return const [];
}

List<Map<String, String>> _parseUsedTools(Map<String, dynamic> receipt) {
  final raw = receipt['used_tools'];
  if (raw is! List) return const [];
  return raw
      .whereType<Map<Object?, Object?>>()
      .map(
        (item) => {
          'name': item['name']?.toString() ?? '',
          'summary': item['summary']?.toString() ?? '',
          'privacy_note': item['privacy_note']?.toString() ?? '',
        },
      )
      .where(
        (item) => item['name']!.isNotEmpty || item['summary']!.isNotEmpty,
      )
      .toList(growable: false);
}

List<String> _parseWhatChanged(Map<String, dynamic> receipt) {
  final raw = receipt['what_changed'];
  if (raw is List) {
    return raw
        .map((item) => item.toString().trim())
        .where((item) => item.isNotEmpty)
        .toList(growable: false);
  }
  return const [];
}

bool _hasDetailContent(
  Map<String, dynamic> receipt,
  List<Map<String, dynamic>> memories,
  List<String> usedNames,
  List<String> excludedNames,
  List<Map<String, String>> usedTools,
  List<String> whatChanged,
) =>
    memories.isNotEmpty ||
    usedNames.isNotEmpty ||
    excludedNames.isNotEmpty ||
    usedTools.isNotEmpty ||
    whatChanged.isNotEmpty ||
    (receipt['decision_reason']?.toString().trim().isNotEmpty ?? false) ||
    (receipt['summary']?.toString().trim().isNotEmpty ?? false);

String _summary(
  BuildContext context,
  Map<String, dynamic> receipt,
  bool isMemory,
  bool isSocialSource,
  bool isSource,
  bool isNextAction,
  List<Map<String, dynamic>> memories,
  int usedCount,
  List<String> excludedNames,
) {
  final summary = receipt['summary']?.toString().trim();
  if (summary != null && summary.isNotEmpty) return summary;
  final reason = receipt['decision_reason']?.toString().trim();
  if (reason != null && reason.isNotEmpty) return reason;
  if (isMemory) {
    final count = memories.length;
    return S.chatMemoryUsedCount(count);
  }
  if (isSocialSource) return context.l10n.chatSocialContextUsed;
  if (isSource) {
    return context.l10n.chatContextReceiptSummary(
      usedCount,
      excludedNames.length,
    );
  }
  if (isNextAction) {
    return S.chatReceiptAuroraChangedNext;
  }
  return S.chatReceiptAuroraAdjustedExperience;
}

String _title(
  BuildContext context,
  Map<String, dynamic> receipt,
  bool isMemory,
  bool isSocialSource,
  bool isSource,
  bool isNextAction,
) {
  final title = receipt['detail_title']?.toString().trim();
  if (title != null && title.isNotEmpty) return title;
  if (isMemory) return context.l10n.chatMemoryReferenceDetailTitle;
  if (isSocialSource) return context.l10n.chatSocialContextDetail;
  if (isSource) return context.l10n.chatContextDetail;
  if (isNextAction) {
    return S.chatReceiptActionChange;
  }
  return S.chatReceiptExperienceChange;
}

IconData _iconFor(
    bool isMemory, bool isSocialSource, bool isSource, bool isNextAction) {
  if (isMemory) return Icons.psychology_alt_outlined;
  if (isSocialSource) return Icons.groups_2_outlined;
  if (isSource) return Icons.auto_awesome;
  if (isNextAction) return Icons.tune_rounded;
  return Icons.auto_fix_high_outlined;
}

class _AuroraReceiptDetailSheet extends StatelessWidget {
  const _AuroraReceiptDetailSheet({
    required this.receipt,
    required this.receiptType,
    required this.title,
    required this.summary,
    required this.icon,
    required this.memories,
    required this.usedNames,
    required this.excludedNames,
    required this.usedTools,
    required this.whatChanged,
    required this.isSocialSource,
    required this.onActionSelected,
  });

  final Map<String, dynamic> receipt;
  final String receiptType;
  final String title;
  final String summary;
  final IconData icon;
  final List<Map<String, dynamic>> memories;
  final List<String> usedNames;
  final List<String> excludedNames;
  final List<Map<String, String>> usedTools;
  final List<String> whatChanged;
  final bool isSocialSource;
  final ValueChanged<String>? onActionSelected;

  bool get _isSource => receiptType == kSourceContextReceiptType;

  bool get _isMemory => receiptType == kMemoryReferenceReceiptType;

  bool get _isNextAction => receiptType == kNextActionReceiptType;

  @override
  Widget build(BuildContext context) {
    final retrievalMode = receipt['retrieval_mode']?.toString().trim() ?? '';
    final privacyBoundary =
        receipt['privacy_boundary']?.toString().trim() ?? '';

    return Container(
      decoration: BoxDecoration(
        color: DS.surfacePanel,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
      ),
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
      child: SafeArea(
        top: false,
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
                Icon(icon, size: 16, color: DS.brandPrimary),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    title,
                    style: DS.bodySmall.copyWith(
                      color: DS.textPrimary,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                if (retrievalMode.isNotEmpty)
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: DS.brandPrimary.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      retrievalMode,
                      style: DS.labelSmall.copyWith(
                        color: DS.brandPrimary,
                        fontSize: 10,
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              summary,
              style: DS.labelSmall.copyWith(color: DS.textSecondary),
            ),
            if (privacyBoundary.isNotEmpty) ...[
              const SizedBox(height: 10),
              Text(
                privacyBoundary,
                style: DS.labelSmall.copyWith(color: DS.textTertiary),
              ),
            ],
            if (whatChanged.isNotEmpty) ...[
              const SizedBox(height: 14),
              _SectionHeader(
                icon: Icons.auto_fix_high_outlined,
                label: S.chatReceiptChangedThisTurn,
                color: DS.brandPrimary,
              ),
              const SizedBox(height: 6),
              ...whatChanged.map(
                (item) => _SourceRow(name: item, isUsed: true),
              ),
            ],
            if (memories.isNotEmpty) ...[
              const SizedBox(height: 12),
              ConstrainedBox(
                constraints: BoxConstraints(
                  maxHeight: MediaQuery.of(context).size.height * 0.54,
                ),
                child: SingleChildScrollView(
                  child: Column(
                    children: memories
                        .map(
                          (memory) => _MemoryReceiptRow(
                            memory: memory,
                            responseId: receipt['response_id']?.toString(),
                            onActionSelected: onActionSelected,
                          ),
                        )
                        .toList(),
                  ),
                ),
              ),
            ],
            if (usedNames.isNotEmpty) ...[
              const SizedBox(height: 14),
              _SectionHeader(
                icon: isSocialSource
                    ? Icons.groups_2_outlined
                    : Icons.check_circle_outline,
                label: context.l10n.chatContextUsed(usedNames.length),
                color: DS.success,
              ),
              const SizedBox(height: 6),
              ...usedNames.map((name) => _SourceRow(name: name, isUsed: true)),
            ],
            if (usedTools.isNotEmpty) ...[
              const SizedBox(height: 14),
              _SectionHeader(
                icon: Icons.build_circle_outlined,
                label: context.l10n.chatContextUsedTools(usedTools.length),
                color: DS.brandPrimary,
              ),
              const SizedBox(height: 6),
              ...usedTools.map((tool) => _ToolSourceRow(tool: tool)),
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
            if (onActionSelected != null && !_isMemory) ...[
              const SizedBox(height: 14),
              _ReceiptActionChips(
                receipt: receipt,
                receiptType: receiptType,
                usedNames: usedNames,
                isSocialSource: isSocialSource,
                onActionSelected: onActionSelected!,
              ),
            ],
            if (_isSource && !isSocialSource) ...[
              const SizedBox(height: 12),
              _DecisionChainLink(),
            ],
            if (_isNextAction && receipt['correctable'] == true) ...[
              const SizedBox(height: 8),
              Text(
                S.chatReceiptJudgmentAccurate,
                style: DS.labelSmall.copyWith(color: DS.textTertiary),
              ),
            ],
            const SizedBox(height: 8),
          ],
        ),
      ),
    );
  }
}

class _ReceiptActionChips extends StatelessWidget {
  const _ReceiptActionChips({
    required this.receipt,
    required this.receiptType,
    required this.usedNames,
    required this.isSocialSource,
    required this.onActionSelected,
  });

  final Map<String, dynamic> receipt;
  final String receiptType;
  final List<String> usedNames;
  final bool isSocialSource;
  final ValueChanged<String> onActionSelected;

  @override
  Widget build(BuildContext context) {
    final actions = _actions(context);
    if (actions.isEmpty) return const SizedBox.shrink();

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

  List<_ReceiptAction> _actions(BuildContext context) {
    final custom = receipt['correction_actions'];
    if (custom is List && custom.isNotEmpty) {
      return custom
          .whereType<Map<Object?, Object?>>()
          .map(
            (item) => _ReceiptAction(
              icon: _actionIcon(receiptType),
              label: item['label']?.toString() ?? '',
              prompt: item['prompt']?.toString() ?? '',
            ),
          )
          .where((item) => item.label.isNotEmpty && item.prompt.isNotEmpty)
          .toList(growable: false);
    }

    if (receiptType == kNextActionReceiptType) {
      final options = receipt['correction_options'];
      if (options is List) {
        return options
            .map((item) => item.toString().trim())
            .where((item) => item.isNotEmpty)
            .map(
              (option) => _ReceiptAction(
                icon: Icons.tune_rounded,
                label: option,
                prompt: S.chatAuroraReassessAction(option),
              ),
            )
            .toList(growable: false);
      }
      return [
        _ReceiptAction(
          icon: Icons.report_outlined,
          label: S.chatAuroraChangeNotRight,
          prompt: S.chatAuroraChangeNotRightPrompt,
        ),
      ];
    }

    if (receiptType == kAuroraExperienceReceiptType) {
      return [
        _ReceiptAction(
          icon: Icons.tune_rounded,
          label: S.chatAuroraRecalibrate,
          prompt: S.chatAuroraRecalibratePrompt,
        ),
      ];
    }

    if (isSocialSource) {
      return [
        _ReceiptAction(
          icon: Icons.block_outlined,
          label: context.l10n.chatSocialContextDisableAction,
          prompt: context.l10n.chatSocialContextDisablePrompt,
        ),
      ];
    }

    return [
      _ReceiptAction(
        icon: Icons.menu_book_outlined,
        label: S.chatAuroraReteachFromSlides,
        prompt: S.chatAuroraReteachPrompt,
      ),
      _ReceiptAction(
        icon: Icons.block_outlined,
        label: S.chatAuroraExcludeSource,
        prompt: usedNames.isEmpty
            ? S.chatAuroraExcludeSourcePrompt
            : S.chatAuroraExcludeSourcesPrompt(usedNames.join(S.recommendationListSeparator)),
      ),
      _ReceiptAction(
        icon: Icons.history_edu_outlined,
        label: S.chatAuroraUsePastExams,
        prompt: S.chatAuroraUsePastExamsPrompt,
      ),
    ];
  }

  IconData _actionIcon(String type) {
    if (type == kNextActionReceiptType) return Icons.tune_rounded;
    if (type == kAuroraExperienceReceiptType) return Icons.auto_fix_high;
    return Icons.block_outlined;
  }
}

class _MemoryReceiptRow extends ConsumerStatefulWidget {
  const _MemoryReceiptRow({
    required this.memory,
    required this.responseId,
    required this.onActionSelected,
  });

  final Map<String, dynamic> memory;
  final String? responseId;
  final ValueChanged<String>? onActionSelected;

  @override
  ConsumerState<_MemoryReceiptRow> createState() => _MemoryReceiptRowState();
}

class _MemoryReceiptRowState extends ConsumerState<_MemoryReceiptRow> {
  bool _submitting = false;

  Future<void> _markWrong() async {
    if (_submitting) return;
    final id = widget.memory['id']?.toString().trim() ?? '';
    final type = widget.memory['type']?.toString().trim();
    final content = widget.memory['content']?.toString().trim() ?? '';
    final memoryType = type != null && type.isNotEmpty ? type : 'episodic';
    final prompt = S.chatMemoryNotRightPrompt(content);

    setState(() => _submitting = true);
    try {
      if (id.isNotEmpty) {
        await ref.read(memoryApiServiceProvider).correctMemory(
              type: memoryType,
              id: id,
              action: 'lower_confidence',
              reason: 'memory_reference_receipt',
            );
      }
      if (mounted) {
        widget.onActionSelected?.call(prompt);
        Navigator.of(context).pop();
      }
    } catch (_) {
      if (mounted) {
        AppFeedback.error(
          context,
          S.chatMemoryCorrectionFailed,
        );
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final content = widget.memory['content']?.toString().trim() ?? '';
    final timeAgo = widget.memory['time_ago']?.toString().trim() ?? '';
    final source = widget.memory['source']?.toString().trim() ?? '';
    final confidence = _confidenceLabel(widget.memory['confidence']);
    final confirmed = widget.memory['user_confirmed'] == true;
    final meta = [
      if (timeAgo.isNotEmpty) timeAgo,
      if (source.isNotEmpty) source,
      if (confidence.isNotEmpty) confidence,
      if (confirmed)
        S.chatMemoryConfirmed
      else
        S.chatMemoryNeedsConfirmation,
    ].join(' · ');

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: DS.surfaceHigh.withValues(alpha: 0.62),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: DS.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(content, style: DS.bodySmall.copyWith(color: DS.textPrimary)),
          if (meta.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(meta, style: DS.labelSmall.copyWith(color: DS.textTertiary)),
          ],
          const SizedBox(height: 8),
          Align(
            alignment: Alignment.centerRight,
            child: Semantics(
              button: true,
              label: S.chatMemoryNotRight,
              child: OutlinedButton.icon(
                style: OutlinedButton.styleFrom(
                  visualDensity: VisualDensity.compact,
                  foregroundColor: DS.warning,
                  side: BorderSide(color: DS.warning.withValues(alpha: 0.45)),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(8),
                  ),
                ),
                onPressed: _submitting ? null : _markWrong,
                icon: _submitting
                    ? SizedBox(
                        width: 12,
                        height: 12,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: DS.warning,
                        ),
                      )
                    : const Icon(Icons.flag_outlined, size: 14),
                label: Text(S.chatMemoryNotRightShort),
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _confidenceLabel(Object? raw) {
    final value = raw is num ? raw.toDouble() : double.tryParse('$raw');
    if (value == null) return '';
    return S.chatMemoryConfidencePercent((value * 100).round());
  }
}

class _DecisionChainLink extends StatelessWidget {
  @override
  Widget build(BuildContext context) => Semantics(
        button: true,
        label: 'Chat aurora receipt chip control 2',
        child: GestureDetector(
          onTap: () {
            unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.tap));
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
      );
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
  Widget build(BuildContext context) => Semantics(
        button: true,
        label: action.label,
        child: InkWell(
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

class _ToolSourceRow extends StatelessWidget {
  const _ToolSourceRow({required this.tool});

  final Map<String, String> tool;

  @override
  Widget build(BuildContext context) {
    final name = tool['name'] ?? '';
    final summary = tool['summary'] ?? '';
    final privacyNote = tool['privacy_note'] ?? '';
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.build_circle_outlined, size: 13, color: DS.brandPrimary),
          const SizedBox(width: 6),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  name.isEmpty ? summary : name,
                  style: DS.labelSmall.copyWith(
                    color: DS.textPrimary,
                    fontWeight: FontWeight.w600,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
                if (summary.isNotEmpty && summary != name)
                  Text(
                    summary,
                    style: DS.labelSmall.copyWith(color: DS.textSecondary),
                    overflow: TextOverflow.ellipsis,
                  ),
                if (privacyNote.isNotEmpty)
                  Text(
                    privacyNote,
                    style: DS.labelSmall.copyWith(color: DS.textTertiary),
                    overflow: TextOverflow.ellipsis,
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _CountBadge extends StatelessWidget {
  const _CountBadge({required this.count});

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

const kAuroraExperienceReceiptType = 'aurora_experience_receipt';
const kMemoryReferenceReceiptType = 'memory_reference_receipt';
const kSourceContextReceiptType = 'source_context_receipt';
const kNextActionReceiptType = 'next_action_changed_by_aurora';

String normalizeAuroraReceiptType(Map<String, dynamic> receipt) {
  final rawType = (receipt['receipt_type'] ?? receipt['type'] ?? '')
      .toString()
      .trim()
      .toLowerCase();
  if (rawType == kAuroraExperienceReceiptType) {
    return kAuroraExperienceReceiptType;
  }
  if (rawType == kMemoryReferenceReceiptType ||
      receipt['referenced_memories'] is List) {
    return kMemoryReferenceReceiptType;
  }
  if (rawType == kSourceContextReceiptType ||
      rawType == 'context_receipt' ||
      rawType == 'social_context_receipt' ||
      receipt['used_tools'] is List ||
      receipt['used_names'] is List) {
    return kSourceContextReceiptType;
  }
  if (rawType == kNextActionReceiptType ||
      rawType == 'spine_receipt' ||
      rawType == 'strategy_adjustment') {
    return kNextActionReceiptType;
  }
  return kAuroraExperienceReceiptType;
}
