import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/memory/data/memory_provenance_models.dart';

/// M-08 provenance API 的客户端薄层（U-03 读/改面）。
///
/// 端点与语义全部来自真实后端（backend/app/api/v1/memory_provenance.py），
/// 走 [ApiClient] 既有鉴权链；本层不做业务推理、不造数据：
/// 读失败原样上抛，由上层决定呈现；404 与跨用户不可区分（后端法则）。
class MemoryProvenanceRepository {
  MemoryProvenanceRepository(this._apiClient);

  final ApiClient _apiClient;

  static const String _base = '/memory/provenance';

  /// GET /memory/provenance/items — 四组条目（服务端已分组打标）。
  Future<ProvenanceListResult> listItems({
    UnderstandingBucket? bucket,
    String? kind,
    int limit = 200,
    int offset = 0,
    bool includeInactive = false,
  }) async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      '$_base/items',
      queryParameters: {
        if (bucket != null) 'bucket': bucket.name,
        if (kind != null) 'kind': kind,
        'limit': limit,
        'offset': offset,
        'include_inactive': includeInactive,
      },
    );
    return ProvenanceListResult.fromJson(
      response.data ?? <String, dynamic>{},
    );
  }

  /// GET /memory/provenance/items/{kind}/{id}/source — 查看来源。
  Future<ProvenanceSourceInfo> getSource({
    required String kind,
    required String id,
  }) async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      '$_base/items/$kind/$id/source',
    );
    return ProvenanceSourceInfo.fromJson(response.data ?? <String, dynamic>{});
  }

  /// GET /memory/provenance/items/{kind}/{id}/scope — scope 读。
  Future<Map<String, dynamic>> getScope({
    required String kind,
    required String id,
  }) async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      '$_base/items/$kind/$id/scope',
    );
    return response.data ?? <String, dynamic>{};
  }

  /// PUT /memory/provenance/items/{kind}/{id}/scope — 暂时不用/恢复/仅此 Goal。
  /// action ∈ pause | resume | link_plan | link_task（后两者仅 goal）。
  Future<Map<String, dynamic>> updateScope(
    String kind,
    String id, {
    required String action,
    String? planId,
    String? taskId,
    String? reason,
  }) async {
    final response = await _apiClient.put<Map<String, dynamic>>(
      '$_base/items/$kind/$id/scope',
      data: {
        'action': action,
        if (planId != null) 'plan_id': planId,
        if (taskId != null) 'task_id': taskId,
        if (reason != null) 'reason': reason,
      },
    );
    return response.data ?? <String, dynamic>{};
  }

  /// POST /memory/provenance/items/{kind}/{id}/update — 用户修改（纠正）。
  /// episodic → supersede（返回新 id + superseded_id）；preference → 版本链；
  /// goal → 字段更新。语义归后端服务层。
  Future<ProvenanceMemoryItem> updateItem(
    String kind,
    String id, {
    String? content,
    Map<String, Object>? prefValue,
    String? title,
    String? goalStatus,
    String? reason,
  }) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      '$_base/items/$kind/$id/update',
      data: {
        if (content != null) 'content': content,
        if (prefValue != null) 'pref_value': prefValue,
        if (title != null) 'title': title,
        if (goalStatus != null) 'goal_status': goalStatus,
        if (reason != null) 'reason': reason,
      },
    );
    return ProvenanceMemoryItem.fromJson(response.data ?? <String, dynamic>{});
  }

  /// POST /memory/provenance/items/{kind}/{id}/revoke — 用户删除。
  Future<Map<String, dynamic>> revokeItem(
    String kind,
    String id, {
    String? reason,
  }) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      '$_base/items/$kind/$id/revoke',
      data: {if (reason != null) 'reason': reason},
    );
    return response.data ?? <String, dynamic>{};
  }

  /// POST /memory/provenance/why-this — 按使用回执查"为什么用这条"。
  Future<WhyThisResult> whyThis({
    required String memoryRef,
    int? version,
    String? packId,
    List<String> whyIncluded = const [],
    List<Map<String, Object>> internalOnly = const [],
  }) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      '$_base/why-this',
      data: {
        'memory_ref': memoryRef,
        if (version != null) 'version': version.toString(),
        if (packId != null) 'pack_id': packId,
        'why_included': whyIncluded,
        'internal_only': internalOnly,
      },
    );
    return WhyThisResult.fromJson(response.data ?? <String, dynamic>{});
  }
}

final memoryProvenanceRepositoryProvider = Provider<MemoryProvenanceRepository>(
  (ref) => MemoryProvenanceRepository(ref.watch(apiClientProvider)),
);

/// 从 DioException 提取后端 detail（用户语言错误面；无 detail 时返回 null）。
String? provenanceErrorDetail(Object error) {
  if (error is DioException) {
    final data = error.response?.data;
    if (data is Map<String, dynamic>) {
      final detail = data['detail'];
      if (detail is String && detail.trim().isNotEmpty) {
        return detail.trim();
      }
    }
  }
  return null;
}
