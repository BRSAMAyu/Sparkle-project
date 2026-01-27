import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
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
    final response = await _apiClient.get<dynamic>('/capsules/today');
    return (response.data as List)
        .map((e) => CuriosityCapsuleModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// 标记为已读
  Future<void> markAsRead(String id) async {
    await _apiClient.post<dynamic>('/capsules/$id/read');
  }

  // ========== 新增方法 ==========

  /// 获取胶囊详情
  Future<CuriosityCapsuleModel> getCapsuleDetail(String id) async {
    final response = await _apiClient.get<dynamic>('/capsules/$id');
    return CuriosityCapsuleModel.fromJson(response.data as Map<String, dynamic>);
  }

  /// 获取收藏列表
  Future<List<dynamic>> getFavorites({
    int limit = 50,
    int offset = 0,
  }) async {
    final response = await _apiClient.get<dynamic>('/capsules/favorites', queryParameters: {
      'limit': limit,
      'offset': offset,
    },);
    return response.data as List;
  }

  /// 收藏/取消收藏胶囊
  Future<Map<String, dynamic>> toggleFavorite(
    String id, {
    String? note,
  }) async {
    final response = await _apiClient.post<dynamic>('/capsules/$id/favorite', queryParameters: {
      if (note != null) 'note': note,
    },);
    return response.data as Map<String, dynamic>;
  }

  /// 提交反馈
  Future<CapsuleFeedbackModel> submitFeedback(
    String id, {
    int? rating,
    bool? helpful,
    String? category,
    String? comment,
  }) async {
    final response = await _apiClient.post<dynamic>(
      '/capsules/$id/feedback',
      data: {
        if (rating != null) 'rating': rating,
        if (helpful != null) 'helpful': helpful,
        if (category != null) 'category': category,
        if (comment != null) 'comment': comment,
      },
    );
    return CapsuleFeedbackModel.fromJson(response.data as Map<String, dynamic>);
  }

  /// 分享胶囊
  Future<Map<String, dynamic>> shareCapsule(
    String id, {
    String? groupId,
    String? friendId,
    String? message,
  }) async {
    final response = await _apiClient.post<dynamic>(
      '/capsules/$id/share',
      data: {
        if (groupId != null) 'group_id': groupId,
        if (friendId != null) 'friend_id': friendId,
        if (message != null) 'message': message,
      },
    );
    return response.data as Map<String, dynamic>;
  }

  /// 获取生成任务列表
  Future<List<CapsuleGenerationJobModel>> getGenerationJobs({
    int limit = 20,
  }) async {
    final response = await _apiClient.get<dynamic>('/capsules/generation/jobs', queryParameters: {
      'limit': limit,
    },);
    return (response.data as List)
        .map((e) => CapsuleGenerationJobModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// 请求批量生成胶囊
  Future<Map<String, dynamic>> requestBatchGeneration({
    double depthPreference = 0.5,
    double curiosityPreference = 0.5,
    int? requestedCount,
  }) async {
    final response = await _apiClient.post<dynamic>(
      '/capsules/generate/batch',
      data: {
        'depth_preference': depthPreference,
        'curiosity_preference': curiosityPreference,
        if (requestedCount != null) 'requested_count': requestedCount,
      },
    );
    return response.data as Map<String, dynamic>;
  }

  /// 获取统计信息
  Future<CapsuleStatsModel> getStats() async {
    final response = await _apiClient.get<dynamic>('/capsules/stats');
    return CapsuleStatsModel.fromJson(response.data as Map<String, dynamic>);
  }

  /// 手动生成胶囊
  Future<CuriosityCapsuleModel> generateCapsule() async {
    final response = await _apiClient.post<dynamic>('/capsules/generate');
    return CuriosityCapsuleModel.fromJson(response.data as Map<String, dynamic>);
  }
}

final capsuleRepositoryProvider = Provider<CapsuleRepository>(
  (ref) => CapsuleRepository(ref.watch(apiClientProvider)),
);
