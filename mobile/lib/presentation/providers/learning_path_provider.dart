import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/data/repositories/learning_path_repository.dart';
import 'package:sparkle/domain/models/learning_path_node.dart';

final learningPathProvider = FutureProvider.family<List<LearningPathNode>, String>((ref, targetNodeId) async {
  final repository = ref.watch(learningPathRepositoryProvider);
  return repository.getLearningPath(targetNodeId);
});
