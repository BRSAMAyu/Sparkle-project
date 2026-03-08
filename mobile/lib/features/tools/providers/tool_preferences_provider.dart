import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/services/user_preferences_service.dart';
import 'package:sparkle/features/tools/models/tool_preferences.dart';
import 'package:sparkle/features/tools/tool_registry.dart';

class ToolPreferencesNotifier extends StateNotifier<ToolPreferences> {
  ToolPreferencesNotifier(this._service)
      : super(
          ToolPreferences(
            pinnedToolIds: ToolRegistry.defaultPinnedToolIds,
            recentToolIds: [],
            isLoaded: _service == null,
          ),
        ) {
    if (_service != null) {
      unawaited(_load());
    }
  }

  static const String _storageKey = 'tool_preferences';
  static const int _maxRecentItems = 12;

  final UserPreferencesService? _service;

  Future<void> _load() async {
    final service = _service;
    if (service == null) {
      return;
    }
    final prefs = await service.getPreferences();
    final raw = prefs[_storageKey];
    if (raw is Map<String, dynamic>) {
      final loaded = ToolPreferences.fromJson(raw);
      state = loaded.copyWith(
        pinnedToolIds: loaded.pinnedToolIds.isEmpty
            ? ToolRegistry.defaultPinnedToolIds
            : _sanitizePinnedIds(loaded.pinnedToolIds),
        recentToolIds: _sanitizeIds(loaded.recentToolIds),
        isLoaded: true,
      );
      return;
    }

    state = state.copyWith(isLoaded: true);
    await _persist();
  }

  Future<void> togglePinned(String toolId) async {
    if (state.pinnedToolIds.contains(toolId)) {
      await unpin(toolId);
      return;
    }
    final next = <String>[...state.pinnedToolIds, toolId];
    state = state.copyWith(pinnedToolIds: _sanitizePinnedIds(next));
    await _persist();
  }

  Future<void> pin(String toolId) async {
    if (state.pinnedToolIds.contains(toolId)) {
      return;
    }
    state = state.copyWith(
      pinnedToolIds:
          _sanitizePinnedIds(<String>[...state.pinnedToolIds, toolId]),
    );
    await _persist();
  }

  Future<void> unpin(String toolId) async {
    state = state.copyWith(
      pinnedToolIds: state.pinnedToolIds.where((id) => id != toolId).toList(),
    );
    await _persist();
  }

  Future<void> reorderPinned(int oldIndex, int newIndex) async {
    final next = [...state.pinnedToolIds];
    if (oldIndex < 0 || oldIndex >= next.length) {
      return;
    }

    if (newIndex > oldIndex) {
      newIndex -= 1;
    }
    final item = next.removeAt(oldIndex);
    next.insert(newIndex, item);
    state = state.copyWith(pinnedToolIds: next);
    await _persist();
  }

  Future<void> recordRecent(String toolId) async {
    final next = <String>[
      toolId,
      ...state.recentToolIds.where((id) => id != toolId),
    ].take(_maxRecentItems).toList();
    state = state.copyWith(recentToolIds: next);
    await _persist();
  }

  Future<void> _persist() async {
    final service = _service;
    if (service == null) {
      return;
    }
    await service.updatePreferences({
      _storageKey: state.toJson(),
    });
  }

  List<String> _sanitizePinnedIds(List<String> ids) =>
      _dedupePreservingOrder(ids.where((id) => ToolRegistry.isPinnable(id)));

  List<String> _sanitizeIds(List<String> ids) => _dedupePreservingOrder(
        ids.where(ToolRegistry.contains),
      );

  List<String> _dedupePreservingOrder(Iterable<String> ids) {
    final seen = <String>{};
    final ordered = <String>[];
    for (final id in ids) {
      if (seen.add(id)) {
        ordered.add(id);
      }
    }
    return ordered;
  }
}

final toolPreferencesProvider =
    StateNotifierProvider<ToolPreferencesNotifier, ToolPreferences>(
  (ref) {
    UserPreferencesService? service;
    try {
      service = ref.watch(userPreferencesServiceProvider);
    } on UnimplementedError {
      service = null;
    }
    return ToolPreferencesNotifier(service);
  },
);
