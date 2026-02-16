import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/features/seed_library/data/models/seed_template_model.dart';

class SeedTemplateRepository {
  SeedTemplateRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<List<SeedTemplatePack>> listPacks({
    String? scenarioType,
    String? visibility,
    int limit = 50,
  }) async {
    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.seedTemplatePacks,
        queryParameters: <String, dynamic>{
          if (scenarioType != null && scenarioType.isNotEmpty)
            'scenario_type': scenarioType,
          if (visibility != null && visibility.isNotEmpty)
            'visibility': visibility,
          'limit': limit,
        },
      );
      final items = ApiResponseParser.unwrapList(
        response.data,
        action: 'list seed template packs',
      );
      return items
          .whereType<Map<String, dynamic>>()
          .map(SeedTemplatePack.fromJson)
          .toList();
    } on DioException catch (e) {
      final error = _extractErrorDetail(e.response?.data) ??
          'Failed to load template packs';
      throw Exception(error);
    }
  }

  Future<List<SeedTemplateListItem>> listTemplatesByPack(
    String packId, {
    bool includeOfficial = true,
    int limit = 100,
  }) async {
    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.seedTemplatePackTemplates(packId),
        queryParameters: <String, dynamic>{
          'include_official': includeOfficial,
          'limit': limit,
        },
      );
      final items = ApiResponseParser.unwrapList(
        response.data,
        action: 'list templates by pack',
      );
      return items
          .whereType<Map<String, dynamic>>()
          .map(SeedTemplateListItem.fromJson)
          .toList();
    } on DioException catch (e) {
      final error =
          _extractErrorDetail(e.response?.data) ?? 'Failed to load templates';
      throw Exception(error);
    }
  }

  Future<SeedTemplateDetail> getTemplate(String templateId) async {
    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.seedTemplate(templateId),
      );
      final payload = ApiResponseParser.unwrapMap(
        response.data,
        action: 'get template',
      );
      return SeedTemplateDetail.fromJson(payload);
    } on DioException catch (e) {
      final error =
          _extractErrorDetail(e.response?.data) ?? 'Failed to load template';
      throw Exception(error);
    }
  }

  Future<List<SeedTemplateVersion>> listTemplateVersions(
    String templateId, {
    bool includeDraft = true,
    int limit = 50,
  }) async {
    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.seedTemplateVersions(templateId),
        queryParameters: <String, dynamic>{
          'include_draft': includeDraft,
          'limit': limit,
        },
      );
      final items = ApiResponseParser.unwrapList(
        response.data,
        action: 'list template versions',
      );
      return items
          .whereType<Map<String, dynamic>>()
          .map(SeedTemplateVersion.fromJson)
          .toList();
    } on DioException catch (e) {
      final error = _extractErrorDetail(e.response?.data) ??
          'Failed to load template versions';
      throw Exception(error);
    }
  }

  Future<void> subscribeTemplate(String templateId, {int priority = 0}) async {
    try {
      await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.seedTemplateSubscribe(templateId),
        data: <String, dynamic>{'priority': priority},
      );
    } on DioException catch (e) {
      final error = _extractErrorDetail(e.response?.data) ??
          'Failed to subscribe template';
      throw Exception(error);
    }
  }

  Future<void> unsubscribeTemplate(String templateId) async {
    try {
      await _apiClient.delete<dynamic>(
        ApiEndpoints.seedTemplateSubscribe(templateId),
      );
    } on DioException catch (e) {
      final error = _extractErrorDetail(e.response?.data) ??
          'Failed to unsubscribe template';
      throw Exception(error);
    }
  }

  Future<List<SeedTemplateSubscription>> getMyTemplateSubscriptions({
    bool onlyEnabled = true,
    int limit = 100,
  }) async {
    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.seedTemplateSubscriptionsMe,
        queryParameters: <String, dynamic>{
          'only_enabled': onlyEnabled,
          'limit': limit,
        },
      );
      final items = ApiResponseParser.unwrapList(
        response.data,
        action: 'list template subscriptions',
      );
      return items
          .whereType<Map<String, dynamic>>()
          .map(SeedTemplateSubscription.fromJson)
          .toList();
    } on DioException catch (e) {
      final error = _extractErrorDetail(e.response?.data) ??
          'Failed to load template subscriptions';
      throw Exception(error);
    }
  }

  Future<SeedTemplateInstantiateResult> instantiateTemplate(
    String templateId, {
    String? versionId,
    Map<String, dynamic>? variables,
    Map<String, dynamic>? templateInstantiationContext,
  }) async {
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.seedTemplateInstantiate(templateId),
        data: <String, dynamic>{
          if (versionId != null) 'version_id': versionId,
          'variables': variables ?? const <String, dynamic>{},
          if (templateInstantiationContext != null)
            'template_instantiation_context': templateInstantiationContext,
        },
      );
      final payload = ApiResponseParser.unwrapMap(
        response.data,
        action: 'instantiate template',
      );
      return SeedTemplateInstantiateResult.fromJson(payload);
    } on DioException catch (e) {
      final error = _extractErrorDetail(e.response?.data) ??
          'Failed to instantiate template';
      throw Exception(error);
    }
  }
}

final seedTemplateRepositoryProvider = Provider<SeedTemplateRepository>(
  (ref) => SeedTemplateRepository(ref.watch(apiClientProvider)),
);

String? _extractErrorDetail(dynamic payload) {
  if (payload is Map<String, dynamic>) {
    final detail = payload['detail'];
    if (detail is String && detail.isNotEmpty) {
      return detail;
    }
  }
  return null;
}
