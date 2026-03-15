import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/plan/data/models/learning_path_progress_model.dart';
import 'package:sparkle/features/plan/data/repositories/plan_repository.dart';

final learningPathProgressProvider =
    FutureProvider.family<LearningPathProgressModel, String>(
  (ref, planId) async {
    final planRepo = ref.watch(planRepositoryProvider);
    return planRepo.getLearningPathProgress(planId);
  },
);
