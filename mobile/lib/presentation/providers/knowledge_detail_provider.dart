import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/data/models/knowledge_detail_model.dart';
import 'package:sparkle/data/repositories/galaxy_repository.dart';

/// Provider family for fetching knowledge node details
final knowledgeDetailProvider = FutureProvider.family<KnowledgeDetailResponse, String>(
  (ref, nodeId) async {
    final repository = ref.watch(galaxyRepositoryProvider);
    return repository.getNodeDetail(nodeId);
  },
);

/// Provider for toggling favorite status
final toggleFavoriteProvider = FutureProvider.family<void, String>(
  (ref, nodeId) async {
    final repository = ref.watch(galaxyRepositoryProvider);
    await repository.toggleFavorite(nodeId);
    // Invalidate the detail to refresh
    ref.invalidate(knowledgeDetailProvider(nodeId));
  },
);

/// Provider for pausing/resuming decay
final toggleDecayPauseProvider = FutureProvider.family<void, (String, bool)>(
  (ref, params) async {
    final (nodeId, pause) = params;
    final repository = ref.watch(galaxyRepositoryProvider);
    await repository.pauseDecay(nodeId, pause);
    // Invalidate the detail to refresh
    ref.invalidate(knowledgeDetailProvider(nodeId));
  },
);
