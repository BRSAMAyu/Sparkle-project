import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

final predictionAttributionServiceProvider =
    Provider<PredictionAttributionService>(
  (ref) => PredictionAttributionService(),
);

class PredictionAttributionService {
  static const String _prefsKey = 'prediction_attribution_queue';
  static const Duration _retentionWindow = Duration(hours: 24);
  static const int _maxEntries = 12;

  Future<void> rememberAcceptedPrediction({
    required String predictionId,
    required String candidateId,
    required String actionType,
    required String surface,
    String? horizon,
    String? source,
    String? suggestedPrompt,
    String? entityType,
    String? entityId,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    final items = await _readItems(prefs);
    final nowMs = DateTime.now().millisecondsSinceEpoch;
    items
      ..removeWhere((item) => item['prediction_id'] == predictionId)
      ..insert(0, {
        'prediction_id': predictionId,
        'candidate_id': candidateId,
        'action_type': actionType,
        'surface': surface,
        'horizon': horizon,
        'source': source,
        'suggested_prompt': suggestedPrompt,
        'entity_type': entityType,
        'entity_id': entityId,
        'accepted_at_ms': nowMs,
      });
    await _writeItems(prefs, _prune(items));
  }

  Future<Map<String, dynamic>?> consumeForExecution({
    required String executionType,
    String? entityType,
    String? entityId,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    final items = await _readItems(prefs);
    final pruned = _prune(items);

    final index = pruned.indexWhere(
      (item) =>
          _matchesExecution(item['action_type']?.toString(), executionType),
    );
    if (index < 0) {
      await _writeItems(prefs, pruned);
      return null;
    }

    final match = Map<String, dynamic>.from(pruned.removeAt(index));
    if (entityType != null) {
      match['executed_entity_type'] = entityType;
    }
    if (entityId != null) {
      match['executed_entity_id'] = entityId;
    }
    await _writeItems(prefs, pruned);
    return match;
  }

  bool _matchesExecution(String? actionType, String executionType) {
    final normalized = actionType ?? '';
    switch (executionType) {
      case 'task':
        return {
          'create_task',
          'resume_task',
          'resume_priority_task',
        }.contains(normalized);
      case 'focus':
        return normalized == 'start_focus';
      case 'plan':
        return {
          'study_plan',
          'plan_next_step',
          'review_progress',
        }.contains(normalized);
      default:
        return false;
    }
  }

  List<Map<String, dynamic>> _prune(List<Map<String, dynamic>> items) {
    final cutoffMs =
        DateTime.now().subtract(_retentionWindow).millisecondsSinceEpoch;
    final filtered = items.where((item) {
      final acceptedAt = item['accepted_at_ms'];
      return acceptedAt is int && acceptedAt >= cutoffMs;
    }).toList();
    if (filtered.length <= _maxEntries) {
      return filtered;
    }
    return filtered.take(_maxEntries).toList();
  }

  Future<List<Map<String, dynamic>>> _readItems(SharedPreferences prefs) async {
    final raw = prefs.getString(_prefsKey);
    if (raw == null || raw.isEmpty) {
      return <Map<String, dynamic>>[];
    }
    try {
      final decoded = jsonDecode(raw);
      if (decoded is List) {
        return decoded
            .whereType<Map<Object?, Object?>>()
            .map(Map<String, dynamic>.from)
            .toList();
      }
    } catch (error) {
      debugPrint('Failed to decode prediction attribution queue: $error');
    }
    return <Map<String, dynamic>>[];
  }

  Future<void> _writeItems(
    SharedPreferences prefs,
    List<Map<String, dynamic>> items,
  ) =>
      prefs.setString(_prefsKey, jsonEncode(items));
}
