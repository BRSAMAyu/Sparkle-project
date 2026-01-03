import 'dart:async';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'sync_queue.dart';

class NetworkMonitor {
  final Connectivity _connectivity = Connectivity();
  final OfflineSyncQueue _syncQueue;

  StreamSubscription? _subscription;

  NetworkMonitor(this._syncQueue);

  void startMonitoring() {
    _subscription = _connectivity.onConnectivityChanged.listen((result) {
      if (!result.contains(ConnectivityResult.none)) {
        // Network restored, trigger sync
        _syncQueue.syncPendingUpdates();
      }
    });
  }

  void stopMonitoring() {
    _subscription?.cancel();
  }
}
