import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:isar/isar.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/services/websocket_service.dart';

class FlutterCRDTPersistence {
  FlutterCRDTPersistence(this._localDb, this._wsService);
  final LocalDatabase _localDb;
  final WebSocketService _wsService;

  Future<void> saveLocalUpdate(String galaxyId, List<int> update) async {
    // 1. 保存到本地数据库 (Save to local DB)
    await _localDb.isar.writeTxn(() async {
      final snapshot = LocalCRDTSnapshot()
        ..galaxyId = galaxyId
        ..updateData = update
        ..timestamp = DateTime.now()
        ..synced = false;

      await _localDb.isar.localCRDTSnapshots.put(snapshot);
    });

    // 2. 尝试同步到服务器 (Try to sync to server)
    if (await _isOnline()) {
      _wsService.send({
        'type': 'collaborative_update',
        'galaxy_id': galaxyId,
        'update': update, // List<int> will be encoded by WebSocketService
        'timestamp': DateTime.now().millisecondsSinceEpoch,
      });

      // Update sync status if we assume it's sent
      // In a robust system, we should wait for an ACK
    }
  }

  Future<List<int>?> restoreFromLocal(String galaxyId) async {
    final snapshot = await _localDb.isar.localCRDTSnapshots
        .filter()
        .galaxyIdEqualTo(galaxyId)
        .sortByTimestampDesc()
        .findFirst();

    if (snapshot != null) {
      return snapshot.updateData;
    }
    return null;
  }

  Future<bool> _isOnline() async {
    final connectivityResult = await Connectivity().checkConnectivity();
    return !connectivityResult.contains(ConnectivityResult.none);
  }
}
