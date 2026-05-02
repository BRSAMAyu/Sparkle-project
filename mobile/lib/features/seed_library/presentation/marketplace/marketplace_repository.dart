import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/features/seed_library/presentation/marketplace/marketplace_models.dart';

class MarketplaceRepository {
  MarketplaceRepository(this._apiClient);

  final ApiClient _apiClient;

  String _message(DioException error) {
    final data = error.response?.data;
    if (data is Map<String, dynamic> && data['detail'] != null) {
      return data['detail'].toString();
    }
    if (data is String && data.trim().isNotEmpty) {
      return data.trim();
    }
    return 'Marketplace request failed';
  }

  Future<List<MarketplaceSkillCard>> listSkills() async {
    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.marketplaceSkills,
      );
      final items = response.data?['items'] as List<dynamic>? ?? const [];
      return items
          .map(
            (item) => MarketplaceSkillCard.fromJson(
              item as Map<String, dynamic>,
            ),
          )
          .toList();
    } on DioException catch (error) {
      throw Exception(_message(error));
    }
  }

  Future<List<MarketplacePackCard>> listPacks() async {
    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.marketplacePacks,
      );
      final items = response.data?['items'] as List<dynamic>? ?? const [];
      return items
          .map(
            (item) => MarketplacePackCard.fromJson(
              item as Map<String, dynamic>,
            ),
          )
          .toList();
    } on DioException catch (error) {
      throw Exception(_message(error));
    }
  }

  Future<MarketplacePreview> previewSkill(String skillId) async {
    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.marketplaceSkillPreview(skillId),
      );
      return MarketplacePreview.fromJson(response.data ?? const {});
    } on DioException catch (error) {
      throw Exception(_message(error));
    }
  }

  Future<MarketplacePreview> previewPack(String packId) async {
    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.marketplacePackPreview(packId),
      );
      return MarketplacePreview.fromJson(response.data ?? const {});
    } on DioException catch (error) {
      throw Exception(_message(error));
    }
  }

  Future<MarketplaceAdoption> adoptSkill(
    String skillId, {
    required MarketplacePreview preview,
  }) async {
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.marketplaceSkillAdopt(skillId),
        data: {
          'confirm': true,
          'context_signature': {
            'source': 'mobile_seed_library_marketplace',
            'preview_version': preview.version,
          },
        },
      );
      return MarketplaceAdoption.fromJson(response.data ?? const {});
    } on DioException catch (error) {
      throw Exception(_message(error));
    }
  }

  Future<MarketplaceAdoption> adoptPack(
    String packId, {
    required MarketplacePreview preview,
  }) async {
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.marketplacePackAdopt(packId),
        data: {
          'confirm': true,
          'context_signature': {
            'source': 'mobile_seed_library_marketplace',
            'preview_version': preview.version,
          },
        },
      );
      return MarketplaceAdoption.fromJson(response.data ?? const {});
    } on DioException catch (error) {
      throw Exception(_message(error));
    }
  }
}

final marketplaceRepositoryProvider = Provider<MarketplaceRepository>(
  (ref) => MarketplaceRepository(ref.watch(apiClientProvider)),
);
