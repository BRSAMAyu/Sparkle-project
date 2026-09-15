import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:sparkle/features/chat/presentation/widgets/aurora_receipt_chip.dart';
import 'package:sparkle/features/chat/presentation/widgets/calibration_receipt_chip.dart';

class ContextReceiptBar extends StatelessWidget {
  const ContextReceiptBar({
    required this.rawMetadata,
    this.enabledReceiptTypes,
    this.onActionSelected,
    super.key,
  });

  final Map<String, dynamic>? rawMetadata;
  final Set<String>? enabledReceiptTypes;
  final ValueChanged<String>? onActionSelected;

  @override
  Widget build(BuildContext context) {
    final calibrationReceipts = _parseCalibrationReceipts()
        .where(_isCalibrationReceiptEnabled)
        .toList(growable: false);
    final receipts =
        _parseReceipts().where(_isReceiptEnabled).toList(growable: false);
    if (calibrationReceipts.isEmpty && receipts.isEmpty) {
      return const SizedBox.shrink();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        ...calibrationReceipts.map(
          (receipt) => CalibrationReceiptChip(receipt: receipt),
        ),
        ...receipts.map(
          (receipt) => AuroraReceiptChip(
            receipt: receipt,
            onActionSelected: onActionSelected,
          ),
        ),
      ],
    );
  }

  bool _isCalibrationReceiptEnabled(Map<String, dynamic> receipt) {
    final enabled = enabledReceiptTypes;
    if (enabled == null) return true;
    return enabled.contains(kCalibrationReceiptType) ||
        enabled.contains(kAuroraExperienceReceiptType);
  }

  bool _isReceiptEnabled(Map<String, dynamic> receipt) {
    final enabled = enabledReceiptTypes;
    if (enabled == null) return true;
    return enabled.contains(normalizeAuroraReceiptType(receipt));
  }

  List<Map<String, dynamic>> _parseReceipts() {
    final metadata = rawMetadata;
    if (metadata == null) return const [];

    final receipts = <Map<String, dynamic>>[];
    final unified = _decodeList(metadata['aurora_receipts']);
    for (final receipt in unified) {
      if (!isCalibrationReceipt(receipt)) {
        _addReceipt(receipts, receipt);
      }
    }

    _addReceipt(
      receipts,
      _withType(
        _decodeReceipt(metadata['session_adaptation']),
        kAuroraExperienceReceiptType,
        sourceKey: 'session_adaptation',
      ),
    );
    _addReceipt(
      receipts,
      _withType(
        _decodeReceipt(metadata['adaptation_summary']),
        kAuroraExperienceReceiptType,
        sourceKey: 'adaptation_summary',
      ),
    );
    _addReceipt(
      receipts,
      _withType(
        _decodeReceipt(metadata['memory_reference_receipt']),
        kMemoryReferenceReceiptType,
      ),
    );
    _addReceipt(
      receipts,
      _withType(
        _decodeReceipt(metadata['social_context_receipt']),
        kSourceContextReceiptType,
        sourceKey: 'social_context_receipt',
        sourceKind: 'social',
      ),
    );
    _addReceipt(
      receipts,
      _withType(
        _decodeReceipt(metadata['context_receipt']),
        kSourceContextReceiptType,
        sourceKey: 'context_receipt',
        sourceKind: 'materials',
      ),
    );
    _addReceipt(
      receipts,
      _withType(
        _decodeReceipt(metadata['spine_receipt']),
        kNextActionReceiptType,
        sourceKey: 'spine_receipt',
      ),
    );

    receipts.sort((a, b) => _receiptPriority(a).compareTo(_receiptPriority(b)));
    return receipts;
  }

  List<Map<String, dynamic>> _parseCalibrationReceipts() {
    final metadata = rawMetadata;
    if (metadata == null) return const [];

    final receipts = <Map<String, dynamic>>[];
    for (final receipt in _decodeList(metadata['aurora_receipts'])) {
      if (isCalibrationReceipt(receipt)) {
        _addCalibrationReceipt(receipts, receipt);
      }
    }
    _addCalibrationReceipt(
      receipts,
      _withType(
        _decodeReceipt(metadata['calibration_receipt']),
        kCalibrationReceiptType,
        sourceKey: 'calibration_receipt',
      ),
    );
    return receipts;
  }

  int _receiptPriority(Map<String, dynamic> receipt) {
    switch (normalizeAuroraReceiptType(receipt)) {
      case kAuroraExperienceReceiptType:
        return 0;
      case kMemoryReferenceReceiptType:
        return 1;
      case kSourceContextReceiptType:
        return 2;
      case kNextActionReceiptType:
        return 3;
      default:
        return 99;
    }
  }

  void _addReceipt(
    List<Map<String, dynamic>> receipts,
    Map<String, dynamic>? receipt,
  ) {
    if (receipt == null || receipt.isEmpty) return;
    final type = normalizeAuroraReceiptType(receipt);
    final id = receipt['receipt_id']?.toString().trim() ??
        receipt['response_id']?.toString().trim() ??
        '';
    final sourceKey = receipt['source_key']?.toString().trim() ?? '';
    final summary = receipt['summary']?.toString().trim() ??
        receipt['decision_reason']?.toString().trim() ??
        '';
    final key = '$type|$id|$sourceKey|$summary';
    final duplicate = receipts.any((existing) {
      final existingType = normalizeAuroraReceiptType(existing);
      final existingId = existing['receipt_id']?.toString().trim() ??
          existing['response_id']?.toString().trim() ??
          '';
      final existingSource = existing['source_key']?.toString().trim() ?? '';
      final existingSummary = existing['summary']?.toString().trim() ??
          existing['decision_reason']?.toString().trim() ??
          '';
      return '$existingType|$existingId|$existingSource|$existingSummary' ==
          key;
    });
    if (!duplicate) receipts.add(receipt);
  }

  void _addCalibrationReceipt(
    List<Map<String, dynamic>> receipts,
    Map<String, dynamic>? receipt,
  ) {
    if (receipt == null || receipt.isEmpty) return;
    final id = receipt['correction_id']?.toString().trim() ??
        receipt['receipt_id']?.toString().trim() ??
        '';
    final sourceKey = receipt['source_key']?.toString().trim() ?? '';
    final summary = CalibrationReceiptViewData.fromReceipt(receipt).summary;
    final key = '$id|$sourceKey|$summary';
    final duplicate = receipts.any((existing) {
      final existingId = existing['correction_id']?.toString().trim() ??
          existing['receipt_id']?.toString().trim() ??
          '';
      final existingSource = existing['source_key']?.toString().trim() ?? '';
      final existingSummary =
          CalibrationReceiptViewData.fromReceipt(existing).summary;
      return '$existingId|$existingSource|$existingSummary' == key;
    });
    if (!duplicate) receipts.add(receipt);
  }

  Map<String, dynamic>? _withType(
    Map<String, dynamic>? receipt,
    String type, {
    String? sourceKey,
    String? sourceKind,
  }) {
    if (receipt == null) return null;
    return {
      ...receipt,
      'receipt_type': receipt['receipt_type'] ?? type,
      if (sourceKey != null) 'source_key': receipt['source_key'] ?? sourceKey,
      if (sourceKind != null)
        'source_kind': receipt['source_kind'] ?? sourceKind,
    };
  }

  List<Map<String, dynamic>> _decodeList(dynamic raw) {
    final decoded = _decode(raw);
    if (decoded is! List) return const [];
    return decoded
        .whereType<Map<Object?, Object?>>()
        .map(Map<String, dynamic>.from)
        .toList(growable: false);
  }

  Map<String, dynamic>? _decodeReceipt(dynamic raw) {
    final decoded = _decode(raw);
    if (decoded is Map<String, dynamic>) return decoded;
    if (decoded is Map) return Map<String, dynamic>.from(decoded);
    return null;
  }

  dynamic _decode(dynamic raw) {
    if (raw == null) return null;
    if (raw is Map || raw is List) return raw;
    if (raw is String) {
      try {
        return json.decode(raw);
      } catch (_) {
        return null;
      }
    }
    return null;
  }
}
