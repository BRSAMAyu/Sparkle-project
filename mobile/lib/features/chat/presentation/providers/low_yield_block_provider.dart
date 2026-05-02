import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/services/app_event_stream_service.dart';

final lowYieldBlockProvider =
    StateNotifierProvider<LowYieldBlockNotifier, LowYieldBlockState>(
  LowYieldBlockNotifier.new,
);

class LowYieldBlockState {
  const LowYieldBlockState({
    this.current,
    this.handledIds = const <String>{},
  });

  final LowYieldBlock? current;
  final Set<String> handledIds;

  bool get isVisible => current != null && !handledIds.contains(current!.id);

  LowYieldBlockState copyWith({
    LowYieldBlock? current,
    Set<String>? handledIds,
    bool clearCurrent = false,
  }) =>
      LowYieldBlockState(
        current: clearCurrent ? null : current ?? this.current,
        handledIds: handledIds ?? this.handledIds,
      );
}

class LowYieldBlock {
  const LowYieldBlock({
    required this.id,
    required this.currentActivity,
    required this.reason,
    required this.suggestedAction,
    this.suggestedTaskId,
    this.suggestedRoute,
    this.traceId,
    this.deadlineLabel,
    this.goalLabel,
    this.rawPayload = const <String, dynamic>{},
  });

  factory LowYieldBlock.fromPayload(Map<String, dynamic> payload) {
    final id = _readString(payload, const [
          'id',
          'block_id',
          'intervention_id',
          'request_id',
          'trace_id',
        ]) ??
        'low-yield:${DateTime.now().millisecondsSinceEpoch}';
    final currentActivity = _readString(payload, const [
          'current_activity',
          'activity',
          'activity_type',
          'doing',
        ]) ??
        '';
    final reason = _readString(payload, const [
          'reason',
          'why_now',
          'deadline_reason',
          'block_reason',
          'recommendation',
        ]) ??
        '';
    final suggestedAction = _readString(payload, const [
          'suggested_action',
          'suggested_task',
          'alternative',
          'best_alternative',
          'target_activity',
        ]) ??
        '';
    return LowYieldBlock(
      id: id,
      currentActivity: currentActivity,
      reason: reason,
      suggestedAction: suggestedAction,
      suggestedTaskId: _readString(payload, const [
        'suggested_task_id',
        'target_task_id',
        'task_id',
      ]),
      suggestedRoute: _readString(payload, const ['route', 'deep_link']),
      traceId: _readString(payload, const ['trace_id']),
      deadlineLabel: _readString(payload, const ['deadline', 'deadline_label']),
      goalLabel: _readString(payload, const ['goal', 'goal_label']),
      rawPayload: payload,
    );
  }

  final String id;
  final String currentActivity;
  final String reason;
  final String suggestedAction;
  final String? suggestedTaskId;
  final String? suggestedRoute;
  final String? traceId;
  final String? deadlineLabel;
  final String? goalLabel;
  final Map<String, dynamic> rawPayload;

  String? get route {
    final explicit = suggestedRoute?.trim();
    if (explicit != null && explicit.isNotEmpty) return explicit;
    final taskId = suggestedTaskId?.trim();
    if (taskId != null && taskId.isNotEmpty) return '/tasks/$taskId';
    return null;
  }

  static String? _readString(Map<String, dynamic> payload, List<String> keys) {
    for (final key in keys) {
      final value = payload[key]?.toString().trim();
      if (value != null && value.isNotEmpty && value != 'null') {
        return value;
      }
    }
    return null;
  }
}

class LowYieldBlockNotifier extends StateNotifier<LowYieldBlockState> {
  LowYieldBlockNotifier(this._ref) : super(const LowYieldBlockState());

  final Ref _ref;

  void ingestPayload(Map<String, dynamic> payload) {
    final block = LowYieldBlock.fromPayload(payload);
    if (state.handledIds.contains(block.id)) {
      return;
    }
    state = state.copyWith(current: block);
  }

  void ingestMetadata(Map<String, dynamic>? metadata) {
    if (metadata == null || metadata.isEmpty) {
      return;
    }
    final payload = _extractPayload(metadata);
    if (payload == null || payload.isEmpty) {
      return;
    }
    ingestPayload(payload);
  }

  Future<void> accept(LowYieldBlock block) async {
    _markHandled(block.id);
    await _recordAction(block, 'accept');
  }

  Future<void> dismiss(LowYieldBlock block) async {
    _markHandled(block.id);
    await _recordAction(block, 'dismiss');
  }

  Future<void> correct(LowYieldBlock block) async {
    _markHandled(block.id);
    await _recordAction(block, 'correct');
  }

  void _markHandled(String id) {
    state = state.copyWith(
      handledIds: {...state.handledIds, id},
      clearCurrent: state.current?.id == id,
    );
  }

  Future<void> _recordAction(LowYieldBlock block, String action) async {
    unawaited(
      _ref.read(appEventStreamServiceProvider).ingestEvents([
        {
          'event_id':
              'low_yield_block_$action:${DateTime.now().millisecondsSinceEpoch}:${block.id}',
          'event_type': 'low_yield_block_action',
          'schema_version': 'event.v1',
          'source': 'chat_low_yield_block',
          'ts_ms': DateTime.now().millisecondsSinceEpoch,
          'entities': {
            'block_id': block.id,
            if (block.suggestedTaskId != null)
              'suggested_task_id': block.suggestedTaskId,
            if (block.traceId != null) 'trace_id': block.traceId,
          },
          'payload': {
            'action': action,
            'current_activity': block.currentActivity,
            'suggested_action': block.suggestedAction,
            ...block.rawPayload,
          },
        },
      ]),
    );
  }

  Map<String, dynamic>? _extractPayload(Map<String, dynamic> metadata) {
    const keys = [
      'low_yield_gentle_block',
      'low_yield_block',
      'low_yield_guard',
      'yield_check',
    ];
    for (final key in keys) {
      final value = metadata[key];
      if (value is Map<String, dynamic>) {
        return value;
      }
      if (value is Map) {
        return Map<String, dynamic>.from(value);
      }
    }
    if (metadata['event_type'] == 'low_yield_block') {
      final payload = metadata['event_payload'];
      if (payload is Map<String, dynamic>) {
        return payload;
      }
      if (payload is Map) {
        return Map<String, dynamic>.from(payload);
      }
      return metadata;
    }
    return null;
  }
}
