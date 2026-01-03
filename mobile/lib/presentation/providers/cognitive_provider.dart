import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/data/models/behavior_pattern_model.dart';
import 'package:sparkle/data/models/cognitive_fragment_model.dart';
import 'package:sparkle/data/repositories/cognitive_repository.dart';
import 'package:sparkle/data/repositories/i_cognitive_repository.dart';
import 'package:sparkle/data/repositories/local_cognitive_repository.dart';
import 'package:sparkle/data/repositories/local_cognitive_repository.dart';
import 'package:sparkle/data/repositories/mock_cognitive_repository.dart';
import 'package:sparkle/data/repositories/mock_cognitive_repository.dart';
import 'package:sparkle/data/repositories/sync_cognitive_repository.dart';
import 'package:sparkle/data/repositories/sync_cognitive_repository.dart';

class CognitiveState {
// ... existing code ...
}

class CognitiveNotifier extends StateNotifier<CognitiveState> {
// ... existing code ...
}

final cognitiveRepositoryProvider = Provider<ICognitiveRepository>((ref) {
  // Toggle between Mock and Real API
  // In production, this should be controlled by environment variables or build flags
  const useMock = false; 
  
  if (useMock) {
    return MockCognitiveRepository();
  }

  final apiClient = ref.watch(apiClientProvider);
  final apiRepo = ApiCognitiveRepository(apiClient);
  final localRepo = LocalCognitiveRepository();
  
  return SyncCognitiveRepository(apiRepo, localRepo);
});
