import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';

enum SourceReceiptAction {
  confirm,
  correct,
  dismiss;

  String get wireValue => name;
}

class SourceExplanationItem {
  const SourceExplanationItem({
    required this.id,
    required this.title,
    this.type,
    this.relevance,
    this.reason,
    this.confidence,
  });

  factory SourceExplanationItem.fromValue(
    Object? value, {
    required int index,
    String? fallbackReason,
  }) {
    if (value is Map<Object?, Object?>) {
      final map = Map<String, dynamic>.from(value);
      final id = _stringValue(
        map['id'] ??
            map['source_id'] ??
            map['file_id'] ??
            map['document_id'] ??
            map['chunk_id'],
        fallback: 'source_$index',
      );
      return SourceExplanationItem(
        id: id,
        title: _stringValue(
          map['title'] ??
              map['name'] ??
              map['source_title'] ??
              map['file_name'] ??
              map['label'],
          fallback: id,
        ),
        type: _optionalString(map['type'] ?? map['source_type'] ?? map['kind']),
        relevance: _doubleValue(
          map['relevance'] ?? map['score'] ?? map['similarity'],
        ),
        reason: _optionalString(map['reason'] ?? map['why'] ?? fallbackReason),
        confidence: _doubleValue(map['confidence']),
      );
    }

    final title = value?.toString().trim() ?? '';
    return SourceExplanationItem(
      id: title.isEmpty ? 'source_$index' : title,
      title: title.isEmpty ? 'Source $index' : title,
      reason: fallbackReason,
    );
  }

  final String id;
  final String title;
  final String? type;
  final double? relevance;
  final String? reason;
  final double? confidence;
}

class SourceExplanationReceipt {
  const SourceExplanationReceipt({
    required this.receiptId,
    required this.usedSources,
    required this.unusedSources,
    this.reason,
    this.retrievalMode,
    this.confidence,
  });

  factory SourceExplanationReceipt.fromJson(Map<String, dynamic> json) {
    final reason = _optionalString(
      json['reason'] ?? json['decision_reason'] ?? json['summary'],
    );
    final usedRaw = _firstList(json, const [
      'used_sources',
      'used',
      'sources',
      'used_documents',
      'used_context',
    ]);
    final excludedRaw = _firstList(json, const [
      'unused_sources',
      'excluded_sources',
      'excluded',
      'skipped_sources',
      'not_used',
    ]);

    final usedFallbackNames = _stringList(json['used_names']);
    final excludedFallbackNames = _stringList(json['excluded_names']);
    final usedValues = usedRaw.isNotEmpty ? usedRaw : usedFallbackNames;
    final excludedValues =
        excludedRaw.isNotEmpty ? excludedRaw : excludedFallbackNames;

    return SourceExplanationReceipt(
      receiptId: _stringValue(
        json['receipt_id'] ?? json['response_id'] ?? json['id'] ?? json['type'],
        fallback: 'context_receipt',
      ),
      usedSources: usedValues
          .asMap()
          .entries
          .map(
            (entry) => SourceExplanationItem.fromValue(
              entry.value,
              index: entry.key + 1,
              fallbackReason: reason,
            ),
          )
          .where((item) => item.title.trim().isNotEmpty)
          .toList(growable: false),
      unusedSources: excludedValues
          .asMap()
          .entries
          .map(
            (entry) => SourceExplanationItem.fromValue(
              entry.value,
              index: entry.key + 1,
            ),
          )
          .where((item) => item.title.trim().isNotEmpty)
          .toList(growable: false),
      reason: reason,
      retrievalMode: _optionalString(json['retrieval_mode']),
      confidence: _doubleValue(json['confidence']),
    );
  }

  final String receiptId;
  final List<SourceExplanationItem> usedSources;
  final List<SourceExplanationItem> unusedSources;
  final String? reason;
  final String? retrievalMode;
  final double? confidence;

  bool get hasVisibleSources =>
      usedSources.isNotEmpty || unusedSources.isNotEmpty;

  static SourceExplanationReceipt? fromMetadata(
    Map<String, dynamic>? metadata,
  ) {
    if (metadata == null || metadata.isEmpty) return null;

    final candidates = <Map<String, dynamic>>[];
    for (final key in const [
      'context_receipt',
      'social_context_receipt',
      'source_context_receipt',
    ]) {
      final decoded = _decodeMap(metadata[key]);
      if (decoded != null) candidates.add(decoded);
    }

    final auroraReceipts = _decodeList(metadata['aurora_receipts']);
    for (final receipt in auroraReceipts) {
      final type = receipt['receipt_type']?.toString() ??
          receipt['type']?.toString() ??
          '';
      if (type.contains('source') || type.contains('context')) {
        candidates.add(receipt);
      }
    }

    if (candidates.isEmpty) return null;
    final receipts = candidates
        .map(SourceExplanationReceipt.fromJson)
        .where((receipt) => receipt.hasVisibleSources)
        .toList(growable: false);
    if (receipts.isEmpty) return null;
    if (receipts.length == 1) return receipts.first;

    return SourceExplanationReceipt(
      receiptId: receipts.first.receiptId,
      usedSources: _dedupeItems(
        receipts.expand((receipt) => receipt.usedSources),
      ),
      unusedSources: _dedupeItems(
        receipts.expand((receipt) => receipt.unusedSources),
      ),
      reason: receipts.map((receipt) => receipt.reason).firstWhere(
            (reason) => reason != null && reason.trim().isNotEmpty,
            orElse: () => null,
          ),
      retrievalMode: receipts.first.retrievalMode,
      confidence: receipts
          .map((receipt) => receipt.confidence)
          .firstWhere((value) => value != null, orElse: () => null),
    );
  }
}

class SourceExplanationActions {
  const SourceExplanationActions(this._ref);

  final Ref _ref;

  Future<void> submitAction({
    required String receiptId,
    required SourceReceiptAction action,
  }) async {
    await _ref.read(apiClientProvider).post<dynamic>(
      '/signals/receipt-action',
      data: {
        'receipt_id': receiptId,
        'action': action.wireValue,
      },
    );
    _ref.invalidate(sourceExplanationProvider);
  }
}

final sourceExplanationProvider =
    FutureProvider<SourceExplanationReceipt?>((ref) async {
  final response = await ref.read(apiClientProvider).get<dynamic>(
        '/signals/context-receipt',
      );
  final data = _decodeMap(response.data);
  final receipt = _decodeMap(data?['receipt']);
  if (receipt == null) return null;
  final parsed = SourceExplanationReceipt.fromJson(receipt);
  return parsed.hasVisibleSources ? parsed : null;
});

final sourceExplanationActionsProvider =
    Provider<SourceExplanationActions>(SourceExplanationActions.new);

List<SourceExplanationItem> _dedupeItems(
  Iterable<SourceExplanationItem> items,
) {
  final seen = <String>{};
  final result = <SourceExplanationItem>[];
  for (final item in items) {
    final key = '${item.id}|${item.title}';
    if (seen.add(key)) result.add(item);
  }
  return result;
}

List<dynamic> _firstList(Map<String, dynamic> json, List<String> keys) {
  for (final key in keys) {
    final value = json[key];
    if (value is List && value.isNotEmpty) return value;
  }
  return const [];
}

List<String> _stringList(Object? value) {
  if (value is! List) return const [];
  return value
      .map((item) => item.toString().trim())
      .where((item) => item.isNotEmpty)
      .toList(growable: false);
}

Map<String, dynamic>? _decodeMap(Object? raw) {
  if (raw is Map<String, dynamic>) return raw;
  if (raw is Map<Object?, Object?>) return Map<String, dynamic>.from(raw);
  if (raw is String && raw.trim().isNotEmpty) {
    try {
      final decoded = json.decode(raw);
      if (decoded is Map<String, dynamic>) return decoded;
      if (decoded is Map<Object?, Object?>) {
        return Map<String, dynamic>.from(decoded);
      }
    } catch (_) {
      return null;
    }
  }
  return null;
}

List<Map<String, dynamic>> _decodeList(Object? raw) {
  var decoded = raw;
  if (raw is String && raw.trim().isNotEmpty) {
    try {
      decoded = json.decode(raw);
    } catch (_) {
      return const [];
    }
  }
  if (decoded is! List) return const [];
  return decoded
      .whereType<Map<Object?, Object?>>()
      .map(Map<String, dynamic>.from)
      .toList(growable: false);
}

String _stringValue(Object? value, {required String fallback}) {
  final text = value?.toString().trim();
  return text == null || text.isEmpty ? fallback : text;
}

String? _optionalString(Object? value) {
  final text = value?.toString().trim();
  return text == null || text.isEmpty ? null : text;
}

double? _doubleValue(Object? value) {
  if (value is num) return value.toDouble();
  if (value is String) return double.tryParse(value);
  return null;
}
