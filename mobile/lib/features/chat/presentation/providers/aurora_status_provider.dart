import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';

/// Single Aurora modeling domain status.
class AuroraDomainStatus {
  const AuroraDomainStatus({
    required this.key,
    required this.label,
    required this.isCovered,
    required this.hasTension,
  });

  final String key;
  final String label;
  final bool isCovered;
  final bool hasTension;
}

/// Overall Aurora modeling status returned by the backend.
class AuroraModelingStatus {
  const AuroraModelingStatus({
    required this.auroraActive,
    required this.modelingComplete,
    required this.domains,
    required this.fetchedAt,
  });

  final bool auroraActive;
  final bool modelingComplete;
  final List<AuroraDomainStatus> domains;
  final DateTime fetchedAt;

  /// True when the cached data is older than [maxAge].
  bool isStale({required Duration maxAge}) =>
      DateTime.now().difference(fetchedAt) > maxAge;
}

/// Notifier that fetches and caches /aurora/modeling-status.
class AuroraStatusNotifier extends StateNotifier<AuroraModelingStatus?> {
  AuroraStatusNotifier(this._apiClient) : super(null);

  final ApiClient _apiClient;
  Timer? _refreshTimer;

  static const _cacheDuration = Duration(seconds: 30);

  /// Fetch modeling status from backend.  Results are cached for 30 s.
  Future<void> refresh() async {
    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.auroraModelingStatus,
      );
      final data = response.data;
      if (data == null) return;

      final rawDomains = data['domains'];
      final domains = <AuroraDomainStatus>[];
      if (rawDomains is Map<String, dynamic>) {
        for (final entry in rawDomains.entries) {
          final value = entry.value;
          if (value is Map<String, dynamic>) {
            domains.add(AuroraDomainStatus(
              key: entry.key,
              label: (value['label'] as String?) ?? entry.key,
              isCovered: (value['status'] as String?) == 'covered',
              hasTension: (value['has_tension'] as bool?) ?? false,
            ));
          }
        }
      }

      state = AuroraModelingStatus(
        auroraActive: (data['aurora_active'] as bool?) ?? false,
        modelingComplete: (data['modeling_complete'] as bool?) ?? false,
        domains: domains,
        fetchedAt: DateTime.now(),
      );
    } catch (_) {
      // Silently ignore -- the bar will remain in its previous state or null.
    }
  }

  /// Start a periodic refresh (e.g. while the chat screen is visible).
  void startPeriodicRefresh() {
    _refreshTimer?.cancel();
    // Initial fetch
    refresh();
    _refreshTimer = Timer.periodic(_cacheDuration, (_) => refresh());
  }

  /// Stop the periodic refresh.
  void stopPeriodicRefresh() {
    _refreshTimer?.cancel();
    _refreshTimer = null;
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }
}

/// Provider that creates the [AuroraStatusNotifier].
final auroraStatusProvider =
    StateNotifierProvider<AuroraStatusNotifier, AuroraModelingStatus?>(
  (ref) => AuroraStatusNotifier(ref.read(apiClientProvider)),
);
