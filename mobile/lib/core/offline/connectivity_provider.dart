import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// TASK-013: Connectivity state for offline-aware UI.
///
/// Watches Connectivity changes and emits a coarse `isOnline` boolean. UI
/// components can `ref.watch(isOnlineProvider)` to render banners or to short-
/// circuit network calls in favor of the offline outbox.
final connectivityStreamProvider = StreamProvider<List<ConnectivityResult>>(
  (ref) {
    final connectivity = Connectivity();
    return connectivity.onConnectivityChanged;
  },
);

final isOnlineProvider = Provider<bool>((ref) {
  final asyncValue = ref.watch(connectivityStreamProvider);
  return asyncValue.maybeWhen(
    data: (results) => !results.contains(ConnectivityResult.none),
    orElse: () => true, // optimistic default
  );
});
