import 'dart:async';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'sync_queue.dart';

class NetworkMonitor {
  final Connectivity _connectivity = Connectivity();
  final OfflineSyncQueue _syncQueue;

  StreamSubscription? _subscription;
  Timer? _debounceTimer;

  NetworkMonitor(this._syncQueue);

  void startMonitoring() {
    _subscription = _connectivity.onConnectivityChanged.listen((result) {
      if (_debounceTimer?.isActive ?? false) _debounceTimer!.cancel();
      
      _debounceTimer = Timer(const Duration(milliseconds: 500), () {
          if (!result.contains(ConnectivityResult.none)) {
            // Network restored, trigger sync
            _syncQueue.syncPendingUpdates();
          }
      });
    });
  }

  void stopMonitoring() {
    _debounceTimer?.cancel();
    _subscription?.cancel();
  }
}
