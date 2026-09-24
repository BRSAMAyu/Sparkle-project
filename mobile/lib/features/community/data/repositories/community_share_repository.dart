import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/core/services/app_event_stream_service.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';

final communityShareRepositoryProvider = Provider((ref) {
  final apiClient = ref.watch(apiClientProvider);
  final eventStream = ref.watch(appEventStreamServiceProvider);
  return CommunityShareRepository(apiClient, eventStream);
});

class CommunityShareRepository {
  CommunityShareRepository(this._apiClient, this._eventStream);

  final ApiClient _apiClient;
  final AppEventStreamService _eventStream;

  /// Fetch shared resources with quality scoring info.
  Future<List<SharedResourceInfo>> fetchSharedResources({
    String sort = 'quality',
    String? resourceType,
    int limit = 20,
  }) async {
    final queryParams = <String, dynamic>{
      'sort': sort,
      'limit': limit,
    };
    if (resourceType != null) {
      queryParams['resource_type'] = resourceType;
    }

    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.communityResources,
      queryParameters: queryParams,
    );

    if (response.statusCode != 200) {
      throw Exception('Failed to fetch shared resources');
    }

    final data = response.data;
    // Backend returns {"resources": [...], "total": N, ...}
    List<dynamic> items;
    if (data is List) {
      items = data;
    } else if (data is Map<String, dynamic> && data['resources'] is List) {
      items = data['resources'] as List;
    } else {
      return [];
    }

    return items
        .whereType<Map<String, dynamic>>()
        .map(SharedResourceInfo.fromJson)
        .toList();
  }

  Future<Map<String, dynamic>> shareResource({
    required String resourceType,
    required String resourceId,
    String? targetGroupId,
    String? targetUserId,
    String permission = 'view',
    String? comment,
  }) async {
    final response = await _apiClient.post<dynamic>(
      ApiEndpoints.communityShare,
      data: {
        'resource_type': resourceType,
        'resource_id': resourceId,
        'target_group_id': targetGroupId,
        'target_user_id': targetUserId,
        'permission': permission,
        'comment': comment,
      },
    );

    if (response.statusCode != 200 && response.statusCode != 201) {
      throw Exception('Failed to share resource');
    }

    final data = ApiResponseParser.unwrapMap(
      response.data,
      action: 'shareResource',
    );
    await _eventStream.recordSharedResourceAction(
      action: 'created',
      sharedResourceId: data['id']?.toString() ?? '',
      resourceType: resourceType,
      resourceId: resourceId,
    );
    return data;
  }

  Future<Map<String, dynamic>> adoptResource({
    required String sharedResourceId,
  }) async {
    final trimmedId = sharedResourceId.trim();
    if (trimmedId.isEmpty) {
      throw Exception('Shared resource id is empty');
    }
    final response = await _apiClient.post<dynamic>(
      ApiEndpoints.adoptSharedResource(trimmedId),
    );
    if (response.statusCode != 200 && response.statusCode != 201) {
      throw Exception('Failed to adopt shared resource');
    }
    final data =
        ApiResponseParser.unwrapMap(response.data, action: 'adoptResource');
    await _eventStream.recordSharedResourceAction(
      action: 'adopted',
      sharedResourceId: sharedResourceId,
      resourceType: data['resource_type']?.toString() ?? 'unknown',
      adoptedEntityId: data['new_resource_id']?.toString(),
    );
    return data;
  }

  /// Reject a recommended community resource so it does not appear
  /// in future suggestions for this user.
  Future<void> rejectResource({
    required String sharedResourceId,
  }) async {
    final trimmedId = sharedResourceId.trim();
    if (trimmedId.isEmpty) return;

    try {
      await _apiClient.post<dynamic>(
        '/community/shared-resources/$trimmedId/reject',
      );
    } catch (_) {
      // Fallback: record rejection through event stream if server unreachable
      await _eventStream.recordSharedResourceAction(
        action: 'rejected',
        sharedResourceId: sharedResourceId,
        resourceType: 'community_share',
      );
    }
  }

  /// S-04：给同伴共享的成果一条反馈/ack。后端只落社群表面记录 + 事件，
  /// **不自动成为 mastery**——采纳与否由资源主人显式决定。
  Future<void> giveFeedback({
    required String sharedResourceId,
    required ResourceFeedbackVerdict verdict,
    String? comment,
  }) async {
    final trimmedId = sharedResourceId.trim();
    if (trimmedId.isEmpty) {
      throw Exception('Shared resource id is empty');
    }
    final response = await _apiClient.post<dynamic>(
      ApiEndpoints.sharedResourceFeedback(trimmedId),
      data: {
        'verdict': verdict.wireValue,
        if (comment != null && comment.isNotEmpty) 'comment': comment,
      },
    );
    if (response.statusCode != 200 && response.statusCode != 201) {
      throw Exception('Failed to give resource feedback');
    }
  }

  /// S-04：读取共享资源的反馈列表（读面含撤回标记，诚实展示）。
  Future<List<ResourceFeedbackItem>> fetchFeedback({
    required String sharedResourceId,
  }) async {
    final trimmedId = sharedResourceId.trim();
    if (trimmedId.isEmpty) {
      throw Exception('Shared resource id is empty');
    }
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.sharedResourceFeedback(trimmedId),
    );
    if (response.statusCode != 200) {
      throw Exception('Failed to fetch resource feedback');
    }
    final items = ApiResponseParser.unwrapList(
      response.data,
      action: 'fetchFeedback',
    );
    return items
        .whereType<Map<String, dynamic>>()
        .map(ResourceFeedbackItem.fromJson)
        .toList(growable: false);
  }

  /// S-04：资源主人把一条反馈**显式采纳**为 Goal 的 outcome evidence。
  /// 后端写 Goal 轨迹回执 + services/evidence 信念链，永不 bump mastery。
  Future<Map<String, dynamic>> adoptFeedbackAsEvidence({
    required String sharedResourceId,
    required String feedbackId,
    String? goalId,
  }) async {
    final trimmedId = sharedResourceId.trim();
    final trimmedFeedbackId = feedbackId.trim();
    if (trimmedId.isEmpty || trimmedFeedbackId.isEmpty) {
      throw Exception('Shared resource or feedback id is empty');
    }
    final response = await _apiClient.post<dynamic>(
      ApiEndpoints.sharedResourceFeedbackAdopt(trimmedId, trimmedFeedbackId),
      data: {
        if (goalId != null && goalId.isNotEmpty) 'goal_id': goalId,
      },
    );
    if (response.statusCode != 200 && response.statusCode != 201) {
      throw Exception('Failed to adopt feedback as evidence');
    }
    final data = ApiResponseParser.unwrapMap(
      response.data,
      action: 'adoptFeedbackAsEvidence',
    );
    await _eventStream.recordSharedResourceAction(
      action: 'feedback_adopted',
      sharedResourceId: sharedResourceId,
      resourceType: data['goal_id']?.toString() ?? 'unknown',
    );
    return data;
  }

  /// S-04：撤回自己共享的资源（派生引用由后端传播更新：反馈标记 + Goal 回执）。
  Future<void> retractResource({
    required String sharedResourceId,
  }) async {
    final trimmedId = sharedResourceId.trim();
    if (trimmedId.isEmpty) {
      throw Exception('Shared resource id is empty');
    }
    final response = await _apiClient.post<dynamic>(
      ApiEndpoints.sharedResourceRetract(trimmedId),
    );
    if (response.statusCode != 200 && response.statusCode != 201) {
      throw Exception('Failed to retract shared resource');
    }
  }
}

/// S-04：同伴反馈封闭词表（与后端 schemas.FeedbackVerdict 对齐）。
enum ResourceFeedbackVerdict {
  helpful('helpful'),
  insightful('insightful'),
  applied('applied');

  const ResourceFeedbackVerdict(this.wireValue);
  final String wireValue;
}

/// S-04：共享资源反馈条目（手写解析，读面诚实透出撤回/采纳标记）。
class ResourceFeedbackItem {
  const ResourceFeedbackItem({
    required this.id,
    required this.sharedResourceId,
    required this.verdict,
    this.comment,
    this.giverName,
    this.adoptedAt,
    this.retractedAt,
  });

  factory ResourceFeedbackItem.fromJson(Map<String, dynamic> json) {
    String? s(dynamic raw) => raw?.toString();
    return ResourceFeedbackItem(
      id: s(json['id']) ?? '',
      sharedResourceId: s(json['shared_resource_id']) ?? '',
      verdict: s(json['verdict']) ?? 'helpful',
      comment: s(json['comment']),
      giverName: s((json['feedback_by'] as Map<String, dynamic>?)?['nickname']) ??
          s((json['feedback_by'] as Map<String, dynamic>?)?['username']),
      adoptedAt: s(json['adopted_at']),
      retractedAt: s(json['retracted_at']),
    );
  }

  final String id;
  final String sharedResourceId;
  final String verdict;
  final String? comment;
  final String? giverName;
  final String? adoptedAt;
  final String? retractedAt;

  bool get isRetracted => retractedAt != null;
  bool get isAdopted => adoptedAt != null;
}
