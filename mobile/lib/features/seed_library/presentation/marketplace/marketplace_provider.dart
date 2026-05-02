import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/seed_library/presentation/marketplace/marketplace_models.dart';
import 'package:sparkle/features/seed_library/presentation/marketplace/marketplace_repository.dart';

class MarketplaceState {
  const MarketplaceState({
    this.skills = const [],
    this.packs = const [],
    this.isLoading = false,
    this.error,
    this.lastAdoption,
  });

  final List<MarketplaceSkillCard> skills;
  final List<MarketplacePackCard> packs;
  final bool isLoading;
  final String? error;
  final MarketplaceAdoption? lastAdoption;

  MarketplaceState copyWith({
    List<MarketplaceSkillCard>? skills,
    List<MarketplacePackCard>? packs,
    bool? isLoading,
    String? error,
    MarketplaceAdoption? lastAdoption,
  }) =>
      MarketplaceState(
        skills: skills ?? this.skills,
        packs: packs ?? this.packs,
        isLoading: isLoading ?? this.isLoading,
        error: error,
        lastAdoption: lastAdoption ?? this.lastAdoption,
      );
}

class MarketplaceNotifier extends StateNotifier<MarketplaceState> {
  MarketplaceNotifier(this._repository) : super(const MarketplaceState()) {
    unawaited(refresh());
  }

  final MarketplaceRepository _repository;

  Future<void> refresh() async {
    state = state.copyWith(isLoading: true);
    try {
      final skills = await _repository.listSkills();
      final packs = await _repository.listPacks();
      state = state.copyWith(
        skills: skills,
        packs: packs,
        isLoading: false,
      );
    } catch (error) {
      state = state.copyWith(
        isLoading: false,
        error: error.toString().replaceFirst('Exception: ', ''),
      );
    }
  }

  Future<MarketplacePreview> previewSkill(String skillId) =>
      _repository.previewSkill(skillId);

  Future<MarketplacePreview> previewPack(String packId) =>
      _repository.previewPack(packId);

  Future<void> adoptSkill(
    String skillId, {
    required MarketplacePreview preview,
  }) async {
    final adoption = await _repository.adoptSkill(skillId, preview: preview);
    state = state.copyWith(lastAdoption: adoption);
    await refresh();
  }

  Future<void> adoptPack(
    String packId, {
    required MarketplacePreview preview,
  }) async {
    final adoption = await _repository.adoptPack(packId, preview: preview);
    state = state.copyWith(lastAdoption: adoption);
    await refresh();
  }
}

final marketplaceProvider =
    StateNotifierProvider<MarketplaceNotifier, MarketplaceState>(
  (ref) => MarketplaceNotifier(ref.watch(marketplaceRepositoryProvider)),
);
