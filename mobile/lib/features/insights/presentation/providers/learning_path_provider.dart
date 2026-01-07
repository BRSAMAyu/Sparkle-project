import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/insights/data/repositories/learning_path_repository.dart';
import 'package:sparkle/features/insights/data/models/learning_path_node.dart';

final learningPathProvider =
    FutureProvider.family<List<LearningPathNode>, String>(
        (ref, targetNodeId) async {
  final repository = ref.watch(learningPathRepositoryProvider);
  return repository.getLearningPath(targetNodeId);
});
