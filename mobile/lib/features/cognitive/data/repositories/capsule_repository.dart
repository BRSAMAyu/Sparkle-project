import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/cognitive/data/models/capsule_feedback_model.dart';
import 'package:sparkle/features/cognitive/data/models/capsule_generation_job_model.dart';
import 'package:sparkle/features/cognitive/data/models/capsule_stats_model.dart';
import 'package:sparkle/features/cognitive/data/models/curiosity_capsule_model.dart';

/// 胶囊仓库 - 支持增强功能
class CapsuleRepository {
  CapsuleRepository(this._apiClient);
  final ApiClient _apiClient;

  // ========== 原有方法（向后兼容） ==========

  /// 获取今日胶囊
  Future<List<CuriosityCapsuleModel>> getTodayCapsules() async {
    if (DemoDataService.isDemoMode) {
      return DemoDataService().demoCuriosityCapsules;
    }
    final response = await _apiClient.get<dynamic>('/capsules/today');
    final data = ApiResponseParser.unwrapList(response.data, action: 'getTodayCapsules');
    return data
        .map((e) => CuriosityCapsuleModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// 标记为已读
  Future<void> markAsRead(String id) async {
    if (DemoDataService.isDemoMode) return;
    await _apiClient.post<dynamic>('/capsules/$id/read');
  }

  // ========== 新增方法 ==========

  /// 获取胶囊详情
  Future<CuriosityCapsuleModel> getCapsuleDetail(String id) async {
    if (DemoDataService.isDemoMode) {
      return DemoDataService()
          .demoCuriosityCapsules
          .firstWhere((c) => c.id == id, orElse: () => DemoDataService().demoCuriosityCapsules.first,);
    }
    final response = await _apiClient.get<dynamic>('/capsules/$id');
    final payload = ApiResponseParser.unwrapMap(response.data, action: 'getCapsuleDetail');
    return CuriosityCapsuleModel.fromJson(payload);
  }

  /// 获取收藏列表
  Future<List<dynamic>> getFavorites({
    int limit = 50,
    int offset = 0,
  }) async {
    if (DemoDataService.isDemoMode) {
      final favorites = DemoDataService()
          .demoCuriosityCapsules
          .where((c) => c.isFavorite)
          .toList();
      return favorites
          .skip(offset)
          .take(limit)
          .map((c) => c.toJson())
          .toList();
    }
    final response = await _apiClient.get<dynamic>('/capsules/favorites', queryParameters: {
      'limit': limit,
      'offset': offset,
    },);
    return ApiResponseParser.unwrapList(response.data, action: 'getFavorites');
  }

  /// 收藏/取消收藏胶囊
  Future<Map<String, dynamic>> toggleFavorite(
    String id, {
    String? note,
  }) async {
    if (DemoDataService.isDemoMode) {
      final capsule = DemoDataService()
          .demoCuriosityCapsules
          .firstWhere((c) => c.id == id, orElse: () => DemoDataService().demoCuriosityCapsules.first,);
      return {
        'capsule_id': capsule.id,
        'is_favorited': !capsule.isFavorite,
        if (note != null) 'note': note,
      };
    }
    final response = await _apiClient.post<dynamic>('/capsules/$id/favorite', queryParameters: {
      if (note != null) 'note': note,
    },);
    return ApiResponseParser.unwrapMap(response.data, action: 'toggleFavorite');
  }

  /// 提交反馈
  Future<CapsuleFeedbackModel> submitFeedback(
    String id, {
    int? rating,
    bool? helpful,
    String? category,
    String? comment,
  }) async {
    if (DemoDataService.isDemoMode) {
      return CapsuleFeedbackModel(
        id: 'demo_feedback_${DateTime.now().millisecondsSinceEpoch}',
        capsuleId: id,
        createdAt: DateTime.now(),
        rating: rating,
        helpful: helpful,
        category: category,
        comment: comment,
      );
    }
    final response = await _apiClient.post<dynamic>(
      '/capsules/$id/feedback',
      data: {
        if (rating != null) 'rating': rating,
        if (helpful != null) 'helpful': helpful,
        if (category != null) 'category': category,
        if (comment != null) 'comment': comment,
      },
    );
    final payload = ApiResponseParser.unwrapMap(response.data, action: 'submitFeedback');
    return CapsuleFeedbackModel.fromJson(payload);
  }

  /// 分享胶囊
  Future<Map<String, dynamic>> shareCapsule(
    String id, {
    String? groupId,
    String? friendId,
    String? message,
  }) async {
    if (DemoDataService.isDemoMode) {
      return {
        'capsule_id': id,
        'shared': true,
        if (groupId != null) 'group_id': groupId,
        if (friendId != null) 'friend_id': friendId,
        if (message != null) 'message': message,
      };
    }
    final response = await _apiClient.post<dynamic>(
      '/capsules/$id/share',
      data: {
        if (groupId != null) 'group_id': groupId,
        if (friendId != null) 'friend_id': friendId,
        if (message != null) 'message': message,
      },
    );
    return ApiResponseParser.unwrapMap(response.data, action: 'shareCapsule');
  }

  /// 获取生成任务列表
  Future<List<CapsuleGenerationJobModel>> getGenerationJobs({
    int limit = 20,
  }) async {
    if (DemoDataService.isDemoMode) {
      return [
        CapsuleGenerationJobModel(
          id: 'demo_job_1',
          status: JobStatus.completed.value,
          generationType: GenerationType.daily.value,
          depthPreference: 0.7,
          curiosityPreference: 0.6,
          requestedCount: 6,
          actualCount: 6,
          capsuleIds: DemoDataService()
              .demoCuriosityCapsules
              .map((c) => c.id)
              .toList(),
          progress: 1.0,
          durationMs: 4200,
          createdAt: DateTime.now().subtract(const Duration(hours: 3)),
          completedAt: DateTime.now().subtract(const Duration(hours: 2, minutes: 50)),
        ),
      ];
    }
    final response = await _apiClient.get<dynamic>('/capsules/generation/jobs', queryParameters: {
      'limit': limit,
    },);
    final data = ApiResponseParser.unwrapList(response.data, action: 'getGenerationJobs');
    return data
        .map((e) => CapsuleGenerationJobModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// 请求批量生成胶囊
  Future<Map<String, dynamic>> requestBatchGeneration({
    double depthPreference = 0.5,
    double curiosityPreference = 0.5,
    int? requestedCount,
  }) async {
    if (DemoDataService.isDemoMode) {
      return {
        'task_id': 'demo_capsule_batch_${DateTime.now().millisecondsSinceEpoch}',
        'requested_count': requestedCount ?? 3,
        'status': 'queued',
      };
    }
    final response = await _apiClient.post<dynamic>(
      '/capsules/generate/batch',
      data: {
        'depth_preference': depthPreference,
        'curiosity_preference': curiosityPreference,
        if (requestedCount != null) 'requested_count': requestedCount,
      },
    );
    return ApiResponseParser.unwrapMap(response.data, action: 'requestBatchGeneration');
  }

  /// 获取统计信息
  Future<CapsuleStatsModel> getStats() async {
    if (DemoDataService.isDemoMode) {
      return CapsuleStatsModel(
        totalReceived: 42,
        totalRead: 31,
        totalFavorited: 7,
        totalFeedbackGiven: 9,
        averageRatingGiven: 4.6,
      );
    }
    final response = await _apiClient.get<dynamic>('/capsules/stats');
    final payload = ApiResponseParser.unwrapMap(response.data, action: 'getStats');
    return CapsuleStatsModel.fromJson(payload);
  }

  /// 手动生成胶囊
  Future<CuriosityCapsuleModel> generateCapsule() async {
    if (DemoDataService.isDemoMode) {
      return DemoDataService().demoCuriosityCapsules.first;
    }
    final response = await _apiClient.post<dynamic>('/capsules/generate');
    final payload = ApiResponseParser.unwrapMap(response.data, action: 'generateCapsule');
    return CuriosityCapsuleModel.fromJson(payload);
  }
}

final capsuleRepositoryProvider = Provider<CapsuleRepository>(
  (ref) => CapsuleRepository(ref.watch(apiClientProvider)),
);
