import 'dart:convert';

import 'package:hive_flutter/hive_flutter.dart';
import 'package:isar/isar.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/offline/outbox_dedupe_key.dart';
import 'package:sparkle/core/offline/sync_metadata.dart';
import 'package:sparkle/core/tracing/tracing_service.dart';
import 'package:sparkle/features/cognitive/data/models/cognitive_fragment_model.dart';
import 'package:uuid/uuid.dart';

class LocalCognitiveRepository {
  LocalCognitiveRepository({LocalDatabase? localDb})
      : _localDb = localDb ?? LocalDatabase();

  static const String _boxName = 'cognitive_offline_queue';
  final LocalDatabase _localDb;
  final Uuid _uuid = const Uuid();

  Future<void> _ensureBoxOpen() async {
    if (!Hive.isBoxOpen(_boxName)) {
      await Hive.openBox<String>(_boxName);
    }
  }

  Future<void> queueFragment(CognitiveFragmentCreate data) async {
    await migrateToOutboxIfNeeded();
    final traceId = TracingService.instance.createTraceId();
    final payload = data.toJson();
    final fragmentId = payload['id'] as String? ?? _uuid.v4();
    payload['id'] = fragmentId;
    final dedupeKey = OutboxDedupeKey.cognitiveCreate(fragmentId);

    final existing = await _localDb.isar.outboxItems
        .filter()
        .dedupeKeyEqualTo(dedupeKey)
        .findFirst();
    if (existing != null) {
      return;
    }

    final item = OutboxItem()
      ..uuid = _uuid.v4()
      ..type = 'cognitive_fragment_create'
      ..topic = 'cognitive'
      ..opType = 'create'
      ..entityType = 'cognitive_fragment'
      ..entityId = fragmentId
      ..payloadJson = jsonEncode(payload)
      ..dedupeKey = dedupeKey
      ..createdAt = DateTime.now()
      ..priority = 5
      ..requiresAuth = true
      ..traceId = traceId
      ..status = SyncStatus.pending;

    await _localDb.isar.writeTxn(() async {
      await _localDb.isar.outboxItems.put(item);
    });
  }

  Future<List<Map<String, dynamic>>> getQueueRaw() async {
    await migrateToOutboxIfNeeded();
    final pending = await _localDb.isar.outboxItems
        .filter()
        .topicEqualTo('cognitive')
        .statusEqualTo(SyncStatus.pending)
        .sortByCreatedAt()
        .findAll();

    return pending
        .map((e) => jsonDecode(e.payloadJson ?? '{}') as Map<String, dynamic>)
        .toList();
  }

  Future<void> removeFromQueue(int index) async {
    await _ensureBoxOpen();
    final box = Hive.box<String>(_boxName);
    await box.deleteAt(index);
  }

  Future<void> clearQueue() async {
    await _ensureBoxOpen();
    final box = Hive.box<String>(_boxName);
    await box.clear();
  }

  Future<void> migrateToOutboxIfNeeded() async {
    final prefs = await SharedPreferences.getInstance();
    final status =
        prefs.getString(SyncMetadataKeys.cognitiveQueueMigrationStatus);
    if (status == SyncMetadataValues.migrationMigrated) return;

    await _ensureBoxOpen();
    final box = Hive.box<String>(_boxName);
    if (box.isEmpty) {
      await prefs.setString(
        SyncMetadataKeys.cognitiveQueueMigrationStatus,
        SyncMetadataValues.migrationMigrated,
      );
      return;
    }

    await prefs.setString(
      SyncMetadataKeys.cognitiveQueueMigrationStatus,
      SyncMetadataValues.migrationMigrating,
    );

    final items = box.values.toList();
    await _localDb.isar.writeTxn(() async {
      for (final raw in items) {
        final payload = jsonDecode(raw) as Map<String, dynamic>;
        final fragmentId = (payload['id'] as String?) ?? _uuid.v4();
        payload['id'] = fragmentId;
        final dedupeKey = OutboxDedupeKey.cognitiveCreate(fragmentId);

        final existing = await _localDb.isar.outboxItems
            .filter()
            .dedupeKeyEqualTo(dedupeKey)
            .findFirst();
        if (existing != null) {
          continue;
        }

        final outboxItem = OutboxItem()
          ..uuid = _uuid.v4()
          ..type = 'cognitive_fragment_create'
          ..topic = 'cognitive'
          ..opType = 'create'
          ..entityType = 'cognitive_fragment'
          ..entityId = fragmentId
          ..payloadJson = jsonEncode(payload)
          ..dedupeKey = dedupeKey
          ..createdAt = DateTime.now()
          ..priority = 5
          ..requiresAuth = true
          ..traceId = TracingService.instance.createTraceId()
          ..status = SyncStatus.pending;

        await _localDb.isar.outboxItems.put(outboxItem);
      }
    });

    await box.clear();
    await prefs.setString(
      SyncMetadataKeys.cognitiveQueueMigrationStatus,
      SyncMetadataValues.migrationMigrated,
    );
  }
}
