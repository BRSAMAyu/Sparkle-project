import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:isar/isar.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/offline/offline_providers.dart';
import 'package:sparkle/core/offline/sync_engine.dart';
import 'package:sparkle/core/offline/sync_metadata.dart';
import 'package:sparkle/l10n/app_localizations.dart';

class SyncCenterStats {
  SyncCenterStats({
    required this.pendingByTopic,
    required this.totalPending,
    required this.lastSuccessAt,
  });

  final Map<String, int> pendingByTopic;
  final int totalPending;
  final DateTime? lastSuccessAt;
}

extension SyncStatusL10n on SyncStatus {
  String localizedLabel(AppLocalizations l10n) {
    switch (this) {
      case SyncStatus.pending:
        return l10n.syncCenterStatusPending;
      case SyncStatus.failed:
        return l10n.syncCenterStatusFailed;
      case SyncStatus.waitingAck:
        return l10n.syncCenterStatusWaitingAck;
      case SyncStatus.synced:
        return l10n.commonSynced;
      case SyncStatus.conflict:
        return l10n.commonWarning;
    }
  }
}

@immutable
class SyncCenterQuery {
  const SyncCenterQuery({
    this.statusFilter,
    this.topicFilter,
    this.limit = 200,
  });

  final SyncStatus? statusFilter;
  final String? topicFilter;
  final int limit;

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is SyncCenterQuery &&
          runtimeType == other.runtimeType &&
          statusFilter == other.statusFilter &&
          topicFilter == other.topicFilter &&
          limit == other.limit;

  @override
  int get hashCode => Object.hash(statusFilter, topicFilter, limit);
}

final syncCenterServiceProvider = Provider<SyncCenterService>((ref) {
  final localDb = ref.watch(localDatabaseProvider);
  final syncEngine = ref.watch(syncEngineProvider);
  return SyncCenterService(localDb, syncEngine);
});

final syncCenterStatsProvider = StreamProvider<SyncCenterStats>((ref) async* {
  final localDb = ref.watch(localDatabaseProvider);
  final prefs = await SharedPreferences.getInstance();

  yield await _computeStats(localDb, prefs);

  await for (final _ in localDb.isar.outboxItems.watchLazy()) {
    yield await _computeStats(localDb, prefs);
  }
});

final syncCenterItemsProvider = StreamProvider.autoDispose
    .family<List<OutboxItem>, SyncCenterQuery>((ref, query) async* {
  final service = ref.watch(syncCenterServiceProvider);
  yield await service.fetchItems(query);

  await for (final _ in service.watchChanges()) {
    yield await service.fetchItems(query);
  }
});

Future<SyncCenterStats> _computeStats(
  LocalDatabase localDb,
  SharedPreferences prefs,
) async {
  final items = await localDb.isar.outboxItems
      .filter()
      .group(
        (q) => q
            .statusEqualTo(SyncStatus.pending)
            .or()
            .statusEqualTo(SyncStatus.waitingAck),
      )
      .count();

  final pendingByTopic = <String, int>{};
  final topics = <String>['cognitive', 'knowledge', 'crdt', 'analytics'];
  for (final topic in topics) {
    final count = await localDb.isar.outboxItems
        .filter()
        .topicEqualTo(topic)
        .and()
        .group(
          (q) => q
              .statusEqualTo(SyncStatus.pending)
              .or()
              .statusEqualTo(SyncStatus.waitingAck),
        )
        .count();
    if (count > 0) {
      pendingByTopic[topic] = count;
    }
  }

  final legacyCount = await localDb.isar.outboxItems
      .filter()
      .topicIsNull()
      .and()
      .group(
        (q) => q
            .statusEqualTo(SyncStatus.pending)
            .or()
            .statusEqualTo(SyncStatus.waitingAck),
      )
      .count();
  if (legacyCount > 0) {
    pendingByTopic['legacy'] = legacyCount;
  }

  final lastSuccessRaw = prefs.getString(SyncMetadataKeys.lastSuccessAt);
  final lastSuccessAt =
      lastSuccessRaw != null ? DateTime.tryParse(lastSuccessRaw) : null;

  return SyncCenterStats(
    pendingByTopic: pendingByTopic,
    totalPending: items,
    lastSuccessAt: lastSuccessAt,
  );
}

class SyncCenterService {
  SyncCenterService(this._localDb, this._syncEngine);

  final LocalDatabase _localDb;
  final SyncEngine _syncEngine;

  Stream<void> watchChanges() => _localDb.isar.outboxItems.watchLazy();

  Future<List<OutboxItem>> fetchItems(SyncCenterQuery query) async {
    final limit = query.limit;
    if (query.statusFilter != null) {
      return _fetchByStatus(query.statusFilter!, query, limit);
    }

    final combined = <OutboxItem>[];
    combined.addAll(await _fetchByStatus(SyncStatus.failed, query, limit));
    if (combined.length < limit) {
      combined.addAll(
        await _fetchByStatus(
          SyncStatus.waitingAck,
          query,
          limit - combined.length,
        ),
      );
    }
    if (combined.length < limit) {
      combined.addAll(
        await _fetchByStatus(
          SyncStatus.pending,
          query,
          limit - combined.length,
        ),
      );
    }
    return combined;
  }

  Future<void> retryItem(Id outboxId) async {
    await _recordRetryAction('retry_item');
    await _localDb.isar.writeTxn(() async {
      final item = await _localDb.isar.outboxItems.get(outboxId);
      if (item == null) return;
      item.status = SyncStatus.pending;
      item.nextAttemptAt = null;
      item.lastSentAt = null;
      item.error = null;
      item.lastErrorCode = null;
      await _localDb.isar.outboxItems.put(item);
    });

    await _syncEngine.processNow(force: true);
  }

  Future<void> retryFailed({int limit = 200}) async {
    await _recordRetryAction('retry_failed');
    final failed = await _fetchByStatus(
      SyncStatus.failed,
      const SyncCenterQuery(),
      limit,
    );

    await _localDb.isar.writeTxn(() async {
      for (final item in failed) {
        item.status = SyncStatus.pending;
        item.nextAttemptAt = null;
        item.lastSentAt = null;
        item.error = null;
        item.lastErrorCode = null;
        await _localDb.isar.outboxItems.put(item);
      }
    });

    await _syncEngine.processNow(force: true);
  }

  Future<void> retryAll() async {
    await _recordRetryAction('retry_all');
    await _syncEngine.processNow(force: true);
  }

  Future<String> buildDiagnostics({int limit = 50}) async {
    final prefs = await SharedPreferences.getInstance();
    final migrationState =
        prefs.getString(SyncMetadataKeys.cognitiveQueueMigrationStatus) ??
            'unknown';
    final lastSuccess =
        prefs.getString(SyncMetadataKeys.lastSuccessAt) ?? 'unknown';
    final lastRetryAction =
        prefs.getString(SyncMetadataKeys.lastRetryAction) ?? 'unknown';

    final totalPending = await _localDb.isar.outboxItems
        .filter()
        .statusEqualTo(SyncStatus.pending)
        .count();
    final totalFailed = await _localDb.isar.outboxItems
        .filter()
        .statusEqualTo(SyncStatus.failed)
        .count();
    final totalWaiting = await _localDb.isar.outboxItems
        .filter()
        .statusEqualTo(SyncStatus.waitingAck)
        .count();

    final failedItems = await _fetchByStatus(
      SyncStatus.failed,
      const SyncCenterQuery(),
      limit,
    );
    final traceIds =
        failedItems.map((e) => e.traceId).whereType<String>().take(20).toList();

    final buffer = StringBuffer()
      ..writeln('app_version: unknown')
      ..writeln('migration_state: $migrationState')
      ..writeln('last_success_at: $lastSuccess')
      ..writeln('last_retry_action: $lastRetryAction')
      ..writeln('pending: $totalPending')
      ..writeln('failed: $totalFailed')
      ..writeln('waiting_ack: $totalWaiting')
      ..writeln('failed_trace_ids: ${traceIds.join(', ')}');

    return buffer.toString();
  }

  Future<void> _recordRetryAction(String action) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(SyncMetadataKeys.lastRetryAction, action);
  }

  Future<List<OutboxItem>> _fetchByStatus(
    SyncStatus status,
    SyncCenterQuery query,
    int limit,
  ) async {
    var qb = _localDb.isar.outboxItems.filter().statusEqualTo(status);

    final topic = query.topicFilter;
    if (topic != null && topic != 'all') {
      if (topic == 'legacy') {
        qb = qb.and().topicIsNull();
      } else {
        qb = qb.and().topicEqualTo(topic);
      }
    }

    final items = await qb.limit(limit).findAll();
    if (status == SyncStatus.failed) {
      items.sort((a, b) {
        final fallback = DateTime(3000);
        final aNext = a.nextAttemptAt ?? fallback;
        final bNext = b.nextAttemptAt ?? fallback;
        final nextCompare = aNext.compareTo(bNext);
        if (nextCompare != 0) {
          return nextCompare;
        }
        return b.attemptCount.compareTo(a.attemptCount);
      });
      return items;
    }
    if (status == SyncStatus.waitingAck) {
      items.sort((a, b) {
        final fallback = DateTime(3000);
        final aLast = a.lastSentAt ?? fallback;
        final bLast = b.lastSentAt ?? fallback;
        return aLast.compareTo(bLast);
      });
      return items;
    }

    items.sort((a, b) => b.createdAt.compareTo(a.createdAt));
    return items;
  }
}
