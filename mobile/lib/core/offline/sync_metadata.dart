class SyncMetadataKeys {
  static const String lastSuccessAt = 'sync_last_success_at';
  static const String lastRetryAction = 'sync_last_retry_action';
  static const String cognitiveQueueMigrationStatus =
      'cognitive_queue_migration_status';
}

class SyncMetadataValues {
  static const String migrationMigrating = 'migrating';
  static const String migrationMigrated = 'migrated';
}
