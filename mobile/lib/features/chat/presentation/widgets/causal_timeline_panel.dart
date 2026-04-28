import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

// ── Data models ──────────────────────────────────────────────────────────────

class TimelineCardModel {
  const TimelineCardModel({
    required this.cardId,
    required this.traceId,
    required this.mode,
    required this.headline,
    required this.summary,
    required this.evidenceChain,
    required this.userActions,
    required this.timestamp,
    this.cardType = 'causal',
  });

  final String cardId;
  final String traceId;
  final String mode;
  final String headline;
  final String summary;
  final List<Map<String, dynamic>> evidenceChain;
  final List<Map<String, String>> userActions;
  final String timestamp;
  final String cardType;

  static TimelineCardModel? fromJson(Map<String, dynamic>? json) {
    if (json == null) return null;
    return TimelineCardModel(
      cardId: json['card_id'] as String? ?? '',
      traceId: json['trace_id'] as String? ?? '',
      mode: json['mode'] as String? ?? 'compact',
      headline: json['headline'] as String? ?? '',
      summary: json['summary'] as String? ?? '',
      evidenceChain: (json['evidence_chain'] as List<dynamic>?)
              ?.map((e) => Map<String, dynamic>.from(e as Map))
              .toList() ??
          [],
      userActions: (json['user_actions'] as List<dynamic>?)
              ?.map(
                (e) => Map<String, String>.from(
                  (e as Map).map(
                    (k, v) => MapEntry(k.toString(), v.toString()),
                  ),
                ),
              )
              .toList() ??
          [],
      timestamp: json['timestamp'] as String? ?? '',
      cardType: json['card_type'] as String? ?? 'causal',
    );
  }
}

class CausalTimelineEntry {
  const CausalTimelineEntry({
    required this.traceId,
    required this.createdAt,
    required this.eventSummary,
    this.card,
  });

  final String traceId;
  final String createdAt;
  final String eventSummary;
  final TimelineCardModel? card;

  static CausalTimelineEntry fromJson(Map<String, dynamic> json) =>
      CausalTimelineEntry(
        traceId: json['trace_id'] as String? ?? '',
        createdAt: json['created_at'] as String? ?? '',
        eventSummary: json['event_summary'] as String? ?? '',
        card: TimelineCardModel.fromJson(
          json['card'] as Map<String, dynamic>?,
        ),
      );
}

// ── Provider ─────────────────────────────────────────────────────────────────

class CausalTimelineNotifier
    extends StateNotifier<AsyncValue<List<CausalTimelineEntry>>> {
  CausalTimelineNotifier(this._apiClient) : super(const AsyncValue.loading()) {
    unawaited(load());
  }

  final ApiClient _apiClient;

  Future<void> load({int limit = 10}) async {
    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.auroraSpineTimeline,
        queryParameters: <String, dynamic>{'limit': limit},
      );
      final data = response.data;
      if (data == null) {
        state = const AsyncValue.data([]);
        return;
      }
      final entriesRaw = data['entries'] as List<dynamic>? ?? [];
      final entries = entriesRaw
          .map(
            (e) =>
                CausalTimelineEntry.fromJson(e as Map<String, dynamic>),
          )
          .toList();
      state = AsyncValue.data(entries);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> submitCorrection({
    required String traceId,
    required String cardId,
    required String action,
    String? userExplanation,
  }) async {
    try {
      await _apiClient.post<void>(
        ApiEndpoints.auroraSpineTimelineCorrect,
        data: <String, dynamic>{
          'trace_id': traceId,
          'card_id': cardId,
          'action': action,
          if (userExplanation != null) 'user_explanation': userExplanation,
        },
      );
      await load();
    } catch (_) {}
  }
}

final causalTimelineProvider = StateNotifierProvider<CausalTimelineNotifier,
    AsyncValue<List<CausalTimelineEntry>>>(
  (ref) => CausalTimelineNotifier(ref.read(apiClientProvider)),
);

// ── Widget ───────────────────────────────────────────────────────────────────

/// Full-screen bottom sheet panel showing the Causal Audit Timeline.
/// Each entry shows a compact card; tapping expands to the full evidence chain.
class CausalTimelinePanel extends ConsumerWidget {
  const CausalTimelinePanel({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final timeline = ref.watch(causalTimelineProvider);

    return Container(
      decoration: BoxDecoration(
        color: DS.surfacePanel,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: SafeArea(
        top: false,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            _Handle(),
            _Header(onRefresh: () => ref.read(causalTimelineProvider.notifier).load()),
            Flexible(
              child: timeline.when(
                loading: () => const _LoadingState(),
                error: (e, _) => _ErrorState(
                  onRetry: () =>
                      ref.read(causalTimelineProvider.notifier).load(),
                ),
                data: (entries) => entries.isEmpty
                    ? const _EmptyState()
                    : _EntryList(
                        entries: entries,
                        onCorrect: (entry, action, explanation) => ref
                            .read(causalTimelineProvider.notifier)
                            .submitCorrection(
                              traceId: entry.traceId,
                              cardId: entry.card?.cardId ?? entry.traceId,
                              action: action,
                              userExplanation: explanation,
                            ),
                      ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Handle extends StatelessWidget {
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(top: 12, bottom: 4),
        child: Center(
          child: Container(
            width: 36,
            height: 4,
            decoration: BoxDecoration(
              color: DS.borderSubtle,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
        ),
      );
}

class _Header extends StatelessWidget {
  const _Header({required this.onRefresh});

  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(20, 8, 8, 8),
        child: Row(
          children: [
            Icon(Icons.timeline, size: 18, color: DS.brandPrimary),
            const SizedBox(width: 10),
            Text(
              context.l10n.chatCausalWhyDecisions,
              style: DS.bodySmall.copyWith(
                color: DS.textPrimary,
                fontWeight: FontWeight.w700,
              ),
            ),
            const Spacer(),
            IconButton(
              icon: Icon(Icons.refresh, size: 18, color: DS.textTertiary),
              onPressed: onRefresh,
              tooltip: '刷新',
              padding: const EdgeInsets.all(8),
              constraints: const BoxConstraints(minWidth: 40, minHeight: 40),
            ),
          ],
        ),
      );
}

class _LoadingState extends StatelessWidget {
  const _LoadingState();

  @override
  Widget build(BuildContext context) => const Padding(
        padding: EdgeInsets.all(40),
        child: Center(child: CircularProgressIndicator()),
      );
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.onRetry});

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.error_outline, color: DS.textTertiary, size: 32),
            const SizedBox(height: 12),
            Text(
              context.l10n.chatCausalLoadFailed,
              style: DS.bodySmall.copyWith(color: DS.textSecondary),
            ),
            const SizedBox(height: 12),
            TextButton(onPressed: onRetry, child: const Text('重试')),
          ],
        ),
      );
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.all(40),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.history_toggle_off, color: DS.textTertiary, size: 36),
            const SizedBox(height: 12),
            Text(
              context.l10n.chatCausalNoRecords,
              style: DS.bodySmall.copyWith(color: DS.textSecondary),
            ),
            const SizedBox(height: 4),
            Text(
              context.l10n.chatCausalNoRecordsHint,
              style: DS.labelSmall.copyWith(color: DS.textTertiary),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      );
}

class _EntryList extends StatelessWidget {
  const _EntryList({required this.entries, required this.onCorrect});

  final List<CausalTimelineEntry> entries;
  final void Function(
    CausalTimelineEntry entry,
    String action,
    String? explanation,
  ) onCorrect;

  @override
  Widget build(BuildContext context) => ListView.separated(
        shrinkWrap: true,
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
        itemCount: entries.length,
        separatorBuilder: (_, __) => const SizedBox(height: 8),
        itemBuilder: (_, i) => _TimelineEntryCard(
          entry: entries[i],
          onCorrect: onCorrect,
        ),
      );
}

class _TimelineEntryCard extends StatefulWidget {
  const _TimelineEntryCard({required this.entry, required this.onCorrect});

  final CausalTimelineEntry entry;
  final void Function(
    CausalTimelineEntry entry,
    String action,
    String? explanation,
  ) onCorrect;

  @override
  State<_TimelineEntryCard> createState() => _TimelineEntryCardState();
}

class _TimelineEntryCardState extends State<_TimelineEntryCard> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final card = widget.entry.card;
    final headline =
        card?.headline ?? widget.entry.eventSummary;
    final summary = card?.summary ?? '';
    final evidenceChain = card?.evidenceChain ?? [];
    final userActions = card?.userActions ?? [];

    return AnimatedContainer(
      duration: const Duration(milliseconds: 220),
      decoration: BoxDecoration(
        color: DS.surfaceHigh,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: DS.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Compact row
          InkWell(
            borderRadius: BorderRadius.circular(14),
            onTap: () {
              SensoryFeedbackService.emit(SensoryFeedbackEvent.tap);
              setState(() => _expanded = !_expanded);
            },
            child: Padding(
              padding: const EdgeInsets.fromLTRB(14, 12, 12, 12),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _CardTypeIcon(cardType: card?.cardType ?? 'causal'),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          headline,
                          style: DS.bodySmall.copyWith(
                            color: DS.textPrimary,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        if (!_expanded && summary.isNotEmpty) ...[
                          const SizedBox(height: 2),
                          Text(
                            summary,
                            style: DS.labelSmall
                                .copyWith(color: DS.textSecondary),
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ],
                      ],
                    ),
                  ),
                  const SizedBox(width: 4),
                  Icon(
                    _expanded
                        ? Icons.keyboard_arrow_up
                        : Icons.keyboard_arrow_down,
                    size: 18,
                    color: DS.textTertiary,
                  ),
                ],
              ),
            ),
          ),

          // Expanded section
          if (_expanded) ...[
            Divider(height: 1, color: DS.borderSubtle),
            Padding(
              padding: const EdgeInsets.fromLTRB(14, 10, 14, 4),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (summary.isNotEmpty) ...[
                    Text(
                      summary,
                      style: DS.labelSmall.copyWith(color: DS.textSecondary),
                    ),
                    const SizedBox(height: 10),
                  ],
                  if (evidenceChain.isNotEmpty) ...[
                    Text(
                      context.l10n.chatCausalDecisionChain,
                      style: DS.labelSmall.copyWith(
                        color: DS.textTertiary,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 6),
                    ...evidenceChain.map(
                      (step) => _EvidenceStep(step: step),
                    ),
                    const SizedBox(height: 10),
                  ],
                  if (userActions.isNotEmpty) ...[
                    Wrap(
                      spacing: 6,
                      runSpacing: 6,
                      children: userActions
                          .map(
                            (action) => _ActionChip(
                              label: action['label'] ?? action['action'] ?? '',
                              onTap: () => _handleAction(
                                action['action'] ?? 'correct',
                              ),
                            ),
                          )
                          .toList(),
                    ),
                    const SizedBox(height: 8),
                  ],
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  void _handleAction(String action) {
    SensoryFeedbackService.emit(SensoryFeedbackEvent.selection);
    if (action == 'correct') {
      _showCorrectionInput(action);
    } else {
      widget.onCorrect(widget.entry, action, null);
    }
  }

  Future<void> _showCorrectionInput(String action) async {
    final controller = TextEditingController();
    final result = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: DS.surfacePanel,
        title: Text(
          context.l10n.chatCausalTellMeWrong,
          style: DS.bodySmall.copyWith(color: DS.textPrimary),
        ),
        content: TextField(
          controller: controller,
          decoration: InputDecoration(
            hintText: context.l10n.chatCausalDescribeCorrect,
            hintStyle: DS.labelSmall.copyWith(color: DS.textTertiary),
          ),
          style: DS.bodySmall.copyWith(color: DS.textPrimary),
          maxLines: 3,
          autofocus: true,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('取消'),
          ),
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(controller.text.trim()),
            child: const Text('提交'),
          ),
        ],
      ),
    );
    controller.dispose();
    if (result != null && result.isNotEmpty) {
      widget.onCorrect(widget.entry, action, result);
    }
  }
}

class _CardTypeIcon extends StatelessWidget {
  const _CardTypeIcon({required this.cardType});

  final String cardType;

  @override
  Widget build(BuildContext context) {
    final (icon, color) = switch (cardType) {
      'self_correction' => (Icons.auto_fix_high, DS.warning),
      'divine_moment' => (Icons.star_outline_rounded, DS.brandPrimary),
      _ => (Icons.account_tree_outlined, DS.info),
    };
    return Icon(icon, size: 16, color: color);
  }
}

class _EvidenceStep extends StatelessWidget {
  const _EvidenceStep({required this.step});

  final Map<String, dynamic> step;

  @override
  Widget build(BuildContext context) {
    final label = step['label'] as String? ?? '';
    final detail = step['detail'] as String? ?? '';
    final type = step['type'] as String? ?? '';

    final (icon, color) = switch (type) {
      'signal' => (Icons.sensors, DS.brandPrimary),
      'policy' => (Icons.policy_outlined, DS.warning),
      'directive' => (Icons.send_outlined, DS.success),
      'outcome' => (Icons.check_circle_outline, DS.info),
      _ => (Icons.circle_outlined, DS.textTertiary),
    };

    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 13, color: color),
          const SizedBox(width: 6),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: DS.labelSmall.copyWith(
                    color: DS.textSecondary,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                if (detail.isNotEmpty)
                  Text(
                    detail,
                    style: DS.labelSmall
                        .copyWith(color: DS.textTertiary, fontSize: 10),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ActionChip extends StatelessWidget {
  const _ActionChip({required this.label, required this.onTap});

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(
            color: DS.brandPrimary.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: DS.brandPrimary.withValues(alpha: 0.22),
            ),
          ),
          child: Text(
            label,
            style: DS.labelSmall.copyWith(
              color: DS.brandPrimary,
              fontWeight: FontWeight.w500,
            ),
          ),
        ),
      );
}
