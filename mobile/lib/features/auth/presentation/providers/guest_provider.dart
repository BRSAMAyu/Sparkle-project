import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/services/guest_service.dart';

/// SharedPreferences Provider
final sharedPreferencesProvider = Provider<SharedPreferences>((ref) {
  throw UnimplementedError('SharedPreferences must be overridden in main.dart');
});

/// GuestService Provider
final guestServiceProvider = Provider<GuestService>((ref) {
  final prefs = ref.watch(sharedPreferencesProvider);
  return GuestService(prefs);
});
