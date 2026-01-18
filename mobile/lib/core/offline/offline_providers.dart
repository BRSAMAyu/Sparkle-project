import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/offline/sync_engine.dart';
import 'package:sparkle/core/services/websocket_service.dart';

final webSocketServiceProvider =
    Provider<WebSocketService>((ref) => WebSocketService());

final syncEngineProvider = Provider<SyncEngine>((ref) {
  final localDb = ref.watch(localDatabaseProvider);
  final wsService = ref.watch(webSocketServiceProvider);
  final apiClient = ref.watch(apiClientProvider);
  final engine = SyncEngine(localDb, wsService, apiClient)..start();
  ref.onDispose(engine.stop);
  return engine;
});
