import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/memory_api_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/memory/data/memory_provenance_models.dart';
import 'package:sparkle/features/memory/presentation/widgets/why_this_receipt_sheet.dart';

class MemoryReferenceReceipt extends ConsumerWidget {
  const MemoryReferenceReceipt({
    required this.rawMetadata,
    this.onActionSelected,
    super.key,
  });

  final Map<String, dynamic>? rawMetadata;
  final ValueChanged<String>? onActionSelected;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final receipt = _parseReceipt();
    if (receipt == null) return const SizedBox.shrink();
    final memories = _parseMemories(receipt);
    if (memories.isEmpty) return const SizedBox.shrink();

    return Semantics(
      button: true,
      label: S.chatMemoryAuroraUsedCount(memories.length),
      child: Semantics(
        button: true,
        label: 'Chat memory reference receipt control 1',
        child: InkWell(
          borderRadius: BorderRadius.circular(8),
          onTap: () {
            unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.tap));
            unawaited(
              showSensoryModalBottomSheet<void>(
                context: context,
                isScrollControlled: true,
                builder: (_) => _MemoryReceiptSheet(
                  receipt: receipt,
                  memories: memories,
                  onActionSelected: onActionSelected,
                ),
              ),
            );
          },
          child: Container(
            margin: const EdgeInsets.only(top: 6, bottom: 2),
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
            decoration: BoxDecoration(
              color: DS.surfaceHigh.withValues(alpha: 0.58),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: DS.borderSubtle),
            ),
            child: Row(
              children: [
                Icon(
                  Icons.psychology_alt_outlined,
                  size: 13,
                  color: DS.brandPrimary,
                ),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    S.chatMemoryUsedCount(memories.length),
                    style: DS.labelSmall.copyWith(color: DS.textSecondary),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                _CountBadge(count: memories.length),
                const SizedBox(width: 4),
                Icon(Icons.chevron_right, size: 13, color: DS.textTertiary),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Map<String, dynamic>? _parseReceipt() {
    final raw = rawMetadata?['memory_reference_receipt'];
    if (raw == null) return null;
    if (raw is Map<String, dynamic>) return raw;
    if (raw is Map) return Map<String, dynamic>.from(raw);
    if (raw is String) {
      try {
        final decoded = json.decode(raw);
        if (decoded is Map<String, dynamic>) return decoded;
        if (decoded is Map) return Map<String, dynamic>.from(decoded);
      } catch (_) {
        return null;
      }
    }
    return null;
  }

  List<Map<String, dynamic>> _parseMemories(Map<String, dynamic> receipt) {
    final raw = receipt['referenced_memories'];
    if (raw is! List) return const [];
    return raw
        .whereType<Map<Object?, Object?>>()
        .map(Map<String, dynamic>.from)
        .where((item) => (item['content']?.toString().trim() ?? '').isNotEmpty)
        .take(5)
        .toList();
  }
}

class _MemoryReceiptSheet extends StatelessWidget {
  const _MemoryReceiptSheet({
    required this.receipt,
    required this.memories,
    required this.onActionSelected,
  });

  final Map<String, dynamic> receipt;
  final List<Map<String, dynamic>> memories;
  final ValueChanged<String>? onActionSelected;

  @override
  Widget build(BuildContext context) {
    final reason = receipt['decision_reason']?.toString().trim() ?? '';
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
                Icon(
                  Icons.psychology_alt_outlined,
                  size: 16,
                  color: DS.brandPrimary,
                ),
                const SizedBox(width: 8),
                Text(
                  S.chatMemoryRelatedMemories,
                  style: DS.bodySmall.copyWith(
                    color: DS.textPrimary,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            if (reason.isNotEmpty) ...[
              const SizedBox(height: 10),
              Text(
                reason,
                style: DS.labelSmall.copyWith(color: DS.textSecondary),
              ),
            ],
            const SizedBox(height: 12),
            ConstrainedBox(
              constraints: BoxConstraints(
                maxHeight: MediaQuery.of(context).size.height * 0.64,
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
        ),
      ),
    );
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

  /// M-10 深链：从 chat 引用回执进入这条记忆对应的理解条目。
  ///
  /// 打开的是 U-03 why-this receipt（M-08 真实 API
  /// POST /memory/provenance/why-this）：来源/被选原因/治理历史 +
  /// 「这不对」真实纠正环（supersede → 失效链 → 全部个性化面重算）。
  /// 引用行只带 kind+id，按 C-01 `memory://<kind>/<id>` 方案构造最小
  /// 真源指针；条目已不存在时后端 404，sheet 显示诚实的加载失败态。
  void _openUnderstanding() {
    final navigator = Navigator.of(context);
    final kind = _memoryKind();
    final id = widget.memory['id']?.toString().trim() ?? '';
    if (id.isEmpty) {
      return;
    }
    final item = ProvenanceMemoryItem(
      kind: kind,
      id: id,
      ref: 'memory://$kind/$id',
      bucket: UnderstandingBucket.uncertain,
      bucketLabel: '',
      content: widget.memory['content']?.toString().trim() ?? '',
      status: 'active',
      scope: const <String, dynamic>{},
      correctionCount: 0,
      evidenceMissing: false,
      confidenceTier: 'tentative',
      confidenceTierLabel: '',
      sourceLabel: '',
      sourceKnown: false,
      actions: const <String>[],
    );
    if (navigator.canPop()) {
      navigator.pop();
    }
    unawaited(unawaitedWhyThis(navigator.context, ref, item));
  }

  String _memoryKind() {
    final type = widget.memory['type']?.toString().trim();
    return type != null && type.isNotEmpty ? type : 'episodic';
  }

  Future<void> _markWrong() async {
    if (_submitting) return;
    final id = widget.memory['id']?.toString().trim() ?? '';
    final content = widget.memory['content']?.toString().trim() ?? '';
    final prompt = S.chatMemoryNotRightPrompt(content);
    final memoryType = _memoryKind();

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
          Text(
            content,
            style: DS.bodySmall.copyWith(color: DS.textPrimary),
          ),
          if (meta.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(
              meta,
              style: DS.labelSmall.copyWith(color: DS.textTertiary),
            ),
          ],
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              // M-10 深链：为什么有这条 → 对应理解条目（why-this receipt）。
              Semantics(
                button: true,
                label: S.understandingActionWhy,
                child: TextButton.icon(
                  style: TextButton.styleFrom(
                    visualDensity: VisualDensity.compact,
                    foregroundColor: DS.textSecondary,
                    padding: const EdgeInsets.symmetric(horizontal: 8),
                  ),
                  onPressed: _openUnderstanding,
                  icon: const Icon(Icons.help_outline_rounded, size: 14),
                  label: Text(S.understandingActionWhy),
                ),
              ),
              const SizedBox(width: 4),
              Semantics(
                button: true,
                label: S.chatMemoryNotRight,
                child: OutlinedButton.icon(
                  style: OutlinedButton.styleFrom(
                    visualDensity: VisualDensity.compact,
                    foregroundColor: DS.warning,
                    side:
                        BorderSide(color: DS.warning.withValues(alpha: 0.45)),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                  onPressed: _submitting ? null : _markWrong,
                  icon: _submitting
                      ? LoadingIndicator.circular(
                          size: 12,
                          strokeWidth: 2,
                          color: DS.warning,
                          liveRegion: false,
                      )
                      : const Icon(Icons.flag_outlined, size: 14),
                  label: Text(S.chatMemoryNotRightShort),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  /// M-10 copy 终审：回执行不再展示无来源出处的精确百分比（内部参数），
  /// 与理解面同一套定性层级词，阈值与后端 `_confidence_label` 同口径。
  String _confidenceLabel(Object? raw) {
    final value = raw is num ? raw.toDouble() : double.tryParse('$raw');
    if (value == null) return '';
    if (value >= 0.75) return S.understandingConfidenceHigh;
    if (value >= 0.45) return S.understandingConfidenceMedium;
    return S.understandingConfidenceLow;
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
