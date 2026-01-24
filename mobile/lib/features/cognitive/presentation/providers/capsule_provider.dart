import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/cognitive/data/models/capsule_feedback_model.dart';
import 'package:sparkle/features/cognitive/data/models/capsule_generation_job_model.dart';
import 'package:sparkle/features/cognitive/data/models/capsule_stats_model.dart';
import 'package:sparkle/features/cognitive/data/models/curiosity_capsule_model.dart';
import 'package:sparkle/features/cognitive/data/repositories/capsule_repository.dart';

/// 胶囊列表状态通知器
class CapsuleNotifier extends StateNotifier<AsyncValue<List<CuriosityCapsuleModel>>> {
  CapsuleNotifier(this._repository) : super(const AsyncValue.loading()) {
    fetchTodayCapsules();
  }
  final CapsuleRepository _repository;

  Future<void> fetchTodayCapsules() async {
    try {
      final capsules = await _repository.getTodayCapsules();
      state = AsyncValue.data(capsules);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> markAsRead(String id) async {
    try {
      await _repository.markAsRead(id);
      // Optimistic update
      state.whenData((capsules) {
        state = AsyncValue.data(
          capsules.map((c) {
            if (c.id == id) {
              return c.copyWith(isRead: true);
            }
            return c;
          }).toList(),
        );
      });
    } catch (e) {
      // Error handling - refresh to revert
      fetchTodayCapsules();
    }
  }

  Future<void> toggleFavorite(String id, {String? note}) async {
    try {
      final result = await _repository.toggleFavorite(id, note: note);
      final isFavorited = result['is_favorited'] as bool;

      // Optimistic update
      state.whenData((capsules) {
        state = AsyncValue.data(
          capsules.map((c) {
            if (c.id == id) {
              return c.copyWith(isFavorite: isFavorited);
            }
            return c;
          }).toList(),
        );
      });
    } catch (e) {
      // Error handling
      fetchTodayCapsules();
    }
  }
}

/// 胶囊生成任务状态通知器
class GenerationJobsNotifier extends StateNotifier<AsyncValue<List<CapsuleGenerationJobModel>>> {
  GenerationJobsNotifier(this._repository) : super(const AsyncValue.data([]));

  final CapsuleRepository _repository;

  Future<void> fetchJobs({int limit = 20}) async {
    try {
      state = const AsyncValue.loading();
      final jobs = await _repository.getGenerationJobs(limit: limit);
      state = AsyncValue.data(jobs);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<String?> requestBatchGeneration({
    double depthPreference = 0.5,
    double curiosityPreference = 0.5,
    int? requestedCount,
  }) async {
    try {
      final result = await _repository.requestBatchGeneration(
        depthPreference: depthPreference,
        curiosityPreference: curiosityPreference,
        requestedCount: requestedCount,
      );
      final taskId = result['task_id'] as String?;

      // 刷新任务列表
      await fetchJobs();

      return taskId;
    } catch (e, st) {
      state = AsyncValue.error(e, st);
      return null;
    }
  }
}

/// 胶囊统计状态通知器
class CapsuleStatsNotifier extends StateNotifier<AsyncValue<CapsuleStatsModel?>> {
  CapsuleStatsNotifier(this._repository) : super(const AsyncValue.data(null));

  final CapsuleRepository _repository;

  Future<void> fetchStats() async {
    try {
      state = const AsyncValue.loading();
      final stats = await _repository.getStats();
      state = AsyncValue.data(stats);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }
}

/// 胶囊详情状态通知器
class CapsuleDetailNotifier extends StateNotifier<AsyncValue<CuriosityCapsuleModel?>> {
  CapsuleDetailNotifier(this._repository) : super(const AsyncValue.data(null));

  final CapsuleRepository _repository;

  Future<void> fetchDetail(String id) async {
    try {
      state = const AsyncValue.loading();
      final capsule = await _repository.getCapsuleDetail(id);
      state = AsyncValue.data(capsule);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<CapsuleFeedbackModel?> submitFeedback(
    String id, {
    int? rating,
    bool? helpful,
    String? category,
    String? comment,
  }) async {
    try {
      final feedback = await _repository.submitFeedback(
        id,
        rating: rating,
        helpful: helpful,
        category: category,
        comment: comment,
      );

      // 刷新详情以更新反馈计数
      await fetchDetail(id);

      return feedback;
    } catch (e) {
      return null;
    }
  }
}

// ========== Providers ==========

final capsuleProvider = StateNotifierProvider<CapsuleNotifier,
    AsyncValue<List<CuriosityCapsuleModel>>>(
  (ref) => CapsuleNotifier(ref.watch(capsuleRepositoryProvider)),
);

final generationJobsProvider = StateNotifierProvider<GenerationJobsNotifier,
    AsyncValue<List<CapsuleGenerationJobModel>>>(
  (ref) => GenerationJobsNotifier(ref.watch(capsuleRepositoryProvider)),
);

final capsuleStatsProvider = StateNotifierProvider<CapsuleStatsNotifier,
    AsyncValue<CapsuleStatsModel?>>(
  (ref) => CapsuleStatsNotifier(ref.watch(capsuleRepositoryProvider)),
);

/// 获取胶囊详情的 Provider 家族
final capsuleDetailProvider = StateNotifierProvider.family<CapsuleDetailNotifier,
    AsyncValue<CuriosityCapsuleModel?>, String>(
  (ref, id) => CapsuleDetailNotifier(ref.watch(capsuleRepositoryProvider)),
);
