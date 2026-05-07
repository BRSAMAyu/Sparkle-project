import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/memory_api_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';

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

  Future<void> _markWrong() async {
    if (_submitting) return;
    final id = widget.memory['id']?.toString().trim() ?? '';
    final type = widget.memory['type']?.toString().trim();
    final content = widget.memory['content']?.toString().trim() ?? '';
    final prompt = S.chatMemoryNotRightPrompt(content);
    final memoryType = type != null && type.isNotEmpty ? type : 'episodic';

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

