import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/galaxy/data/models/user_galaxy_contribution.dart';
import 'package:sparkle/features/galaxy/data/repositories/enhanced_galaxy_repository.dart';

final galaxyContributionProvider =
    FutureProvider.autoDispose<UserGalaxyContribution>((ref) async {
  final repository = ref.watch(enhancedGalaxyRepositoryProvider);
  final result = await repository.getContributionStats();
  if (result.data != null) {
    return result.data!;
  }
  throw Exception(result.error ?? 'Failed to load galaxy contribution stats');
});
