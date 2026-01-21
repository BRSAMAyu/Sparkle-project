// Conditional import based on platform
import 'dart:io' show Platform;

// Use different implementations for web and other platforms
import 'local_database_web.dart' if (dart.library.io) 'local_database_native.dart';

// Common enum used by both implementations
enum SyncStatus {
  pending,
  synced,
  conflict,
  failed,
  waitingAck,
}
