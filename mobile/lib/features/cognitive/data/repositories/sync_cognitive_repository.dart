import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:sparkle/features/cognitive/data/models/behavior_pattern_model.dart';
import 'package:sparkle/features/cognitive/data/models/cognitive_fragment_model.dart';
import 'package:sparkle/features/cognitive/data/repositories/cognitive_repository.dart'; // ApiCognitiveRepository
import 'package:sparkle/features/cognitive/data/repositories/i_cognitive_repository.dart';
import 'package:sparkle/features/cognitive/data/repositories/local_cognitive_repository.dart';
import 'package:uuid/uuid.dart';

class SyncCognitiveRepository implements ICognitiveRepository {
  SyncCognitiveRepository(this._apiRepository, this._localRepository);

  final ApiCognitiveRepository _apiRepository;
  final LocalCognitiveRepository _localRepository;
  final _uuid = const Uuid();

  @override
  Future<CognitiveFragmentModel> createFragment(
      CognitiveFragmentCreate data,) async {
    // Patch 1: Front-end leads ID generation
    final fragmentId = data.id ?? _uuid.v4();
    final dataWithId = CognitiveFragmentCreate(
      id: fragmentId,
      content: data.content,
      sourceType: data.sourceType,
      taskId: data.taskId,
    );

    try {
      // 1. Try API
      final result = await _apiRepository.createFragment(dataWithId);

      // 2. If successful, check if we have pending items to sync (opportunistic sync)
      _syncPendingInBackground();

      return result;
    } catch (e) {
      debugPrint('🌐 Network failed, saving locally: $e');

      // 3. If failed, save locally with the same ID
      await _localRepository.queueFragment(dataWithId);

      // 4. Return a "Pending" model for optimistic UI
      return CognitiveFragmentModel(
        id: fragmentId,
        userId: 'current_user',
        sourceType: data.sourceType,
        content: data.content,
        taskId: data.taskId,
        createdAt: DateTime.now(),
        sentiment: 'neutral',
        tags: ['pending_sync'],
      );
    }
  }

  @override
  Future<List<CognitiveFragmentModel>> getFragments(
      {int limit = 20, int skip = 0,}) async {
    var apiFragments = <CognitiveFragmentModel>[];
    try {
      apiFragments =
          await _apiRepository.getFragments(limit: limit, skip: skip);
    } catch (e) {
      debugPrint('🌐 Failed to fetch API fragments: $e');
    }

    // Load pending local fragments
    final pendingMaps = await _localRepository.getQueueRaw();
    final pendingFragments = pendingMaps.cast<Map<String, dynamic>>()
        .map(
          (map) => CognitiveFragmentModel(
            id: (map['id'] as String?) ?? 'local_pending_${map.hashCode}',
            userId: 'current_user',
            sourceType: (map['source_type'] as String?) ?? 'unknown',
            content: (map['content'] as String?) ?? '',
            taskId: map['task_id'] as String?,
            createdAt: DateTime.now(),
            sentiment: 'neutral',
            tags: ['pending'],
          ),
        )
        .toList();

    // Merge: Deduplicate by ID (API data takes precedence if ID exists in both)
    final merged = <String, CognitiveFragmentModel>{};
    for (final f in apiFragments) {
      merged[f.id] = f;
    }
    for (final f in pendingFragments) {
      if (!merged.containsKey(f.id)) {
        merged[f.id] = f;
      }
    }

    final resultList = merged.values.toList()
      // Sort by created_at desc (local items will be at top if approximate date is now)
      ..sort((a, b) => b.createdAt.compareTo(a.createdAt));
    return resultList;
  }

  @override
  Future<List<BehaviorPatternModel>> getBehaviorPatterns() =>
      _apiRepository.getBehaviorPatterns();

  /// Try to sync pending fragments
  Future<void> syncPending() async {
    final pending = (await _localRepository.getQueueRaw())
        .cast<Map<String, dynamic>>();
    if (pending.isEmpty) return;

    debugPrint('🔄 Syncing ${pending.length} pending fragments...');

    // Process in order
    // Note: This is a simple implementation.
    // Robust way: lock the queue, process, remove success ones.

    // We iterate backwards to allow safe removal or use a copy
    // Actually, simple queue consumption:

    final toRemoveIndices = <int>[];

    for (var i = 0; i < pending.length; i++) {
      final item = pending[i];
      try {
        final data = CognitiveFragmentCreate(
          id: item['id'] as String?,
          content: (item['content'] as String?) ?? '',
          sourceType: (item['source_type'] as String?) ?? 'unknown',
          taskId: item['task_id'] as String?,
        );

        await _apiRepository.createFragment(data);
        toRemoveIndices.add(i);
      } catch (e) {
        debugPrint('❌ Sync failed for item $i: $e');
        // Stop on first error to preserve order? Or continue?
        // Let's stop to avoid out-of-order issues if significant
        break;
      }
    }

    // Remove synced items (in reverse order to keep indices valid)
    for (final index in toRemoveIndices.reversed) {
      await _localRepository.removeFromQueue(index);
    }

    debugPrint('✅ Synced ${toRemoveIndices.length} items.');
  }

  void _syncPendingInBackground() {
    // Fire and forget
    unawaited(
      syncPending().catchError(
        (Object e) => debugPrint('Background sync failed: $e'),
      ),
    );
  }
}
