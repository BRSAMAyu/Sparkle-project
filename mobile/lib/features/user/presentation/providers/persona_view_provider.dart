import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/user/data/repositories/user_repository.dart';

final transparentProfileProvider =
    FutureProvider<Map<String, dynamic>>((ref) async {
  final repo = ref.watch(userRepositoryProvider);
  return repo.fetchTransparentProfile();
});

final systemUpdatesProvider =
    FutureProvider<List<Map<String, dynamic>>>((ref) async {
  final repo = ref.watch(userRepositoryProvider);
  return repo.fetchSystemUpdates();
});

final inferredPreferencesProvider =
    FutureProvider<List<Map<String, dynamic>>>((ref) async {
  final repo = ref.watch(userRepositoryProvider);
  return repo.fetchInferredPreferences();
});

final activePoliciesProvider =
    FutureProvider<List<Map<String, dynamic>>>((ref) async {
  final repo = ref.watch(userRepositoryProvider);
  return repo.fetchActivePolicies();
});
