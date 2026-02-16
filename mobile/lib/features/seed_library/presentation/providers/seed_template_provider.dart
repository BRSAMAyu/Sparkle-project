import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/seed_library/data/models/seed_template_model.dart';
import 'package:sparkle/features/seed_library/data/repositories/seed_template_repository.dart';

final seedTemplatePacksProvider =
    FutureProvider.family<List<SeedTemplatePack>, String?>((ref, scenarioType) {
  final repo = ref.watch(seedTemplateRepositoryProvider);
  return repo.listPacks(
    scenarioType: scenarioType,
    limit: 100,
  );
});

final seedTemplatesByPackProvider =
    FutureProvider.family<List<SeedTemplateListItem>, String>((ref, packId) {
  final repo = ref.watch(seedTemplateRepositoryProvider);
  return repo.listTemplatesByPack(packId);
});

final seedTemplateDetailProvider =
    FutureProvider.family<SeedTemplateDetail, String>((ref, templateId) {
  final repo = ref.watch(seedTemplateRepositoryProvider);
  return repo.getTemplate(templateId);
});

final seedTemplateVersionsProvider =
    FutureProvider.family<List<SeedTemplateVersion>, String>((ref, templateId) {
  final repo = ref.watch(seedTemplateRepositoryProvider);
  return repo.listTemplateVersions(templateId);
});

final seedTemplateSubscriptionsProvider =
    FutureProvider<List<SeedTemplateSubscription>>((ref) {
  final repo = ref.watch(seedTemplateRepositoryProvider);
  return repo.getMyTemplateSubscriptions();
});

class SeedTemplateInstantiateState {
  const SeedTemplateInstantiateState({
    this.isLoading = false,
    this.result,
    this.error,
  });

  final bool isLoading;
  final SeedTemplateInstantiateResult? result;
  final String? error;

  static const Object _unset = Object();

  SeedTemplateInstantiateState copyWith({
    bool? isLoading,
    SeedTemplateInstantiateResult? result,
    Object? error = _unset,
  }) =>
      SeedTemplateInstantiateState(
        isLoading: isLoading ?? this.isLoading,
        result: result ?? this.result,
        error: identical(error, _unset) ? this.error : error as String?,
      );
}

class SeedTemplateInstantiateNotifier
    extends StateNotifier<SeedTemplateInstantiateState> {
  SeedTemplateInstantiateNotifier(this._repo)
      : super(const SeedTemplateInstantiateState());

  final SeedTemplateRepository _repo;

  Future<void> instantiate({
    required String templateId,
    String? versionId,
    Map<String, dynamic>? variables,
    Map<String, dynamic>? context,
  }) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final result = await _repo.instantiateTemplate(
        templateId,
        versionId: versionId,
        variables: variables,
        templateInstantiationContext: context,
      );
      state = state.copyWith(isLoading: false, result: result);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  void clearResult() {
    state = const SeedTemplateInstantiateState();
  }
}

final seedTemplateInstantiateProvider = StateNotifierProvider.autoDispose<
    SeedTemplateInstantiateNotifier, SeedTemplateInstantiateState>(
  (ref) => SeedTemplateInstantiateNotifier(
    ref.watch(seedTemplateRepositoryProvider),
  ),
);
