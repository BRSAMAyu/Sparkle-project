import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/shared/entities/visual_element_model.dart';

/// Visual Element Repository
/// 视觉元素数据仓库
class VisualElementRepository {
  VisualElementRepository(this._apiClient);
  final ApiClient _apiClient;

  /// Handle Dio exceptions
  Never _handleDioError(DioException e, String functionName) {
    final responseData = e.response?.data;
    final detail = switch (responseData) {
      final Map<String, dynamic> map => map['detail'] as String?,
      final Map<dynamic, dynamic> map => map['detail'] as String?,
      _ => null,
    };
    final errorMessage = detail ?? 'An unknown error occurred in $functionName';
    throw Exception(errorMessage);
  }

  VisualElementListResponse _parseVisualElementListResponse(
    dynamic rawPayload, {
    required String action,
  }) {
    final payload = ApiResponseParser.unwrapMap(rawPayload, action: action);
    final rawItems = payload['items'];
    if (rawItems != null && rawItems is! List) {
      throw Exception('$action items payload is not a list');
    }

    final items = (rawItems as List<dynamic>? ?? const <dynamic>[]).map((json) {
      if (json is! Map<String, dynamic>) {
        throw Exception('$action item payload is not a JSON object');
      }
      return VisualElementModel.fromJson(json);
    }).toList();

    return VisualElementListResponse(
      items: items,
      total: (payload['total'] as num?)?.toInt() ?? items.length,
    );
  }

  /// Get all visual elements
  Future<VisualElementListResponse> getVisualElements({
    VisualElementType? type,
    VisualElementRarity? rarity,
    String? category,
    bool unlockedOnly = false,
  }) async {
    if (DemoDataService.isDemoMode) {
      return _getDemoVisualElements();
    }

    try {
      final locale = I18nService.instance.currentLocale.languageCode;
      final queryParams = <String, dynamic>{
        'locale': locale,
        if (type != null) 'element_type': type.name,
        if (rarity != null) 'rarity': rarity.name,
        if (category != null) 'category': category,
        'unlocked_only': unlockedOnly,
      };

      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.visualElements,
        queryParameters: queryParams,
      );
      return _parseVisualElementListResponse(
        response.data,
        action: 'getVisualElements',
      );
    } on DioException catch (e) {
      return _handleDioError(e, 'getVisualElements');
    } on FormatException catch (e) {
      throw Exception('Failed to parse getVisualElements response: $e');
    } on TypeError catch (e) {
      throw Exception('Failed to parse getVisualElements response: $e');
    }
  }

  /// Get unlocked visual elements
  Future<VisualElementListResponse> getUnlockedElements({
    VisualElementType? type,
  }) async {
    if (DemoDataService.isDemoMode) {
      final all = _getDemoVisualElements();
      return VisualElementListResponse(
        items: all.items.where((e) => e.isUnlocked).toList(),
        total: all.items.where((e) => e.isUnlocked).length,
      );
    }

    try {
      final locale = I18nService.instance.currentLocale.languageCode;
      final queryParams = <String, dynamic>{
        'locale': locale,
        if (type != null) 'element_type': type.name,
      };

      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.visualElementsUnlocked,
        queryParameters: queryParams,
      );
      return _parseVisualElementListResponse(
        response.data,
        action: 'getUnlockedElements',
      );
    } on DioException catch (e) {
      return _handleDioError(e, 'getUnlockedElements');
    } on FormatException catch (e) {
      throw Exception('Failed to parse getUnlockedElements response: $e');
    } on TypeError catch (e) {
      throw Exception('Failed to parse getUnlockedElements response: $e');
    }
  }

  /// Get user visual config
  Future<UserVisualConfig> getUserConfig() async {
    if (DemoDataService.isDemoMode) {
      return _getDemoUserConfig();
    }

    try {
      final locale = I18nService.instance.currentLocale.languageCode;
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.visualElementsConfig,
        queryParameters: {'locale': locale},
      );

      final payload = response.data;
      if (payload == null) {
        return UserVisualConfig();
      }

      return UserVisualConfig.fromJson(payload);
    } on DioException catch (e) {
      return _handleDioError(e, 'getUserConfig');
    }
  }

  /// Equip a visual element
  Future<EquipElementResponse> equipElement(String elementId) async {
    if (DemoDataService.isDemoMode) {
      // Simulate equip
      return EquipElementResponse(
        success: true,
        message: 'Equipped successfully',
        config: _getDemoUserConfig(),
      );
    }

    try {
      final locale = I18nService.instance.currentLocale.languageCode;
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.visualElementEquip(elementId),
        queryParameters: {'locale': locale},
      );

      final payload = response.data;
      if (payload == null) {
        throw Exception('equipElement response is empty');
      }

      return EquipElementResponse.fromJson(payload);
    } on DioException catch (e) {
      return _handleDioError(e, 'equipElement');
    }
  }

  /// Unequip a visual element
  Future<EquipElementResponse> unequipElement(VisualElementType type) async {
    if (DemoDataService.isDemoMode) {
      return EquipElementResponse(
        success: true,
        message: 'Unequipped successfully',
        config: UserVisualConfig(),
      );
    }

    try {
      final locale = I18nService.instance.currentLocale.languageCode;
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.visualElementUnequip(type.name),
        queryParameters: {'locale': locale},
      );

      final payload = response.data;
      if (payload == null) {
        throw Exception('unequipElement response is empty');
      }

      return EquipElementResponse.fromJson(payload);
    } on DioException catch (e) {
      return _handleDioError(e, 'unequipElement');
    }
  }

  /// Unlock elements by achievement
  Future<List<VisualElementModel>> unlockByAchievement(
    String achievementId,
  ) async {
    if (DemoDataService.isDemoMode) {
      return [];
    }

    try {
      final locale = I18nService.instance.currentLocale.languageCode;
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.visualElementsUnlockByAchievement,
        queryParameters: {
          'achievement_id': achievementId,
          'locale': locale,
        },
      );

      final payload = response.data;
      if (payload == null) {
        return [];
      }

      final items = payload['items'] as List<dynamic>?;
      return items
              ?.map(
                (e) => VisualElementModel.fromJson(e as Map<String, dynamic>),
              )
              .toList() ??
          [];
    } on DioException catch (e) {
      return _handleDioError(e, 'unlockByAchievement');
    }
  }

  /// Get default visual elements
  Future<VisualElementListResponse> getDefaultElements() async {
    if (DemoDataService.isDemoMode) {
      final all = _getDemoVisualElements();
      return VisualElementListResponse(
        items: all.items.where((e) => e.isDefault).toList(),
        total: all.items.where((e) => e.isDefault).length,
      );
    }

    try {
      final locale = I18nService.instance.currentLocale.languageCode;
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.visualElementsDefaults,
        queryParameters: {'locale': locale},
      );

      return _parseVisualElementListResponse(
        response.data,
        action: 'getDefaultElements',
      );
    } on DioException catch (e) {
      return _handleDioError(e, 'getDefaultElements');
    } on FormatException catch (e) {
      throw Exception('Failed to parse getDefaultElements response: $e');
    } on TypeError catch (e) {
      throw Exception('Failed to parse getDefaultElements response: $e');
    }
  }

  // ========== Demo Data ==========

  VisualElementListResponse _getDemoVisualElements() =>
      VisualElementListResponse(
        items: [
          // Backgrounds — ink-blue base (墨兰底色系), deep understated premium
          VisualElementModel(
            id: 'bg_default_dark',
            name: '深邃夜空',
            description: '默认墨蓝渐变背景，沉静而内敛',
            elementType: VisualElementType.background,
            rarity: VisualElementRarity.common,
            unlockSource: VisualElementUnlockSource.system,
            isDefault: true,
            sortOrder: 0,
            category: 'space',
            config: {
              'gradient': {
                'colors': ['#0d1117', '#161b22', '#1c2533'],
              },
            },
            isUnlocked: true,
            isEquipped: true,
          ),
          VisualElementModel(
            id: 'bg_aurora',
            name: '极光之夜',
            description: '墨蓝底色上的幽绿极光，静谧而神秘',
            elementType: VisualElementType.background,
            rarity: VisualElementRarity.rare,
            unlockSource: VisualElementUnlockSource.achievement,
            isDefault: false,
            sortOrder: 10,
            category: 'nature',
            config: {
              'gradient': {
                'colors': ['#0d1117', '#14202e', '#1a3040'],
              },
              'aurora_colors': ['#3fb68b', '#2dd4bf', '#22d3ee'],
            },
          ),
          VisualElementModel(
            id: 'bg_sunset',
            name: '暮色余晖',
            description: '温暖的琥珀色调融入深蓝底色',
            elementType: VisualElementType.background,
            rarity: VisualElementRarity.rare,
            unlockSource: VisualElementUnlockSource.achievement,
            isDefault: false,
            sortOrder: 20,
            category: 'nature',
            config: {
              'gradient': {
                'colors': ['#1a1a2e', '#2a2040', '#3d2b50'],
              },
            },
            isUnlocked: true,
          ),
          VisualElementModel(
            id: 'bg_nebula',
            name: '星云漫游',
            description: '深邃墨蓝中的幽紫星云流转',
            elementType: VisualElementType.background,
            rarity: VisualElementRarity.epic,
            unlockSource: VisualElementUnlockSource.achievement,
            isDefault: false,
            sortOrder: 30,
            category: 'space',
            config: {
              'gradient': {
                'colors': ['#0d1117', '#1a1832', '#16213e'],
              },
              'nebula_colors': ['#6366f1', '#818cf8', '#a78bfa'],
            },
          ),
          VisualElementModel(
            id: 'bg_cyberpunk',
            name: '赛博朋克',
            description: '墨蓝基底上的霓虹线条，未来感十足',
            elementType: VisualElementType.background,
            rarity: VisualElementRarity.epic,
            unlockSource: VisualElementUnlockSource.shop,
            isDefault: false,
            sortOrder: 40,
            category: 'cyberpunk',
            config: {
              'gradient': {
                'colors': ['#0d1117', '#111827', '#1e293b'],
              },
              'neon_colors': ['#06b6d4', '#8b5cf6', '#f59e0b'],
            },
          ),
          VisualElementModel(
            id: 'bg_event_starlight',
            name: '流星庆典',
            description: '限时活动专属，墨蓝夜空中的金色流星雨',
            elementType: VisualElementType.background,
            rarity: VisualElementRarity.legendary,
            unlockSource: VisualElementUnlockSource.event,
            isDefault: false,
            sortOrder: 50,
            category: 'space',
            config: {
              'gradient': {
                'colors': ['#0d1117', '#162032', '#1a2a4a'],
              },
              'aurora_colors': ['#f59e0b', '#fbbf24', '#7dd3fc'],
            },
            unlockRequirement: {
              'event_end_at': '2026-04-15T00:00:00Z',
            },
          ),
          // Particles
          VisualElementModel(
            id: 'particle_default_stars',
            name: '繁星点点',
            description: '默认闪烁星星粒子',
            elementType: VisualElementType.particle,
            rarity: VisualElementRarity.common,
            unlockSource: VisualElementUnlockSource.system,
            isDefault: true,
            sortOrder: 0,
            category: 'space',
            config: {
              'count': 50,
              'shape': 'star',
              'colors': ['#e2e8f0', '#fbbf24', '#94a3b8'],
            },
            isUnlocked: true,
            isEquipped: true,
          ),
          VisualElementModel(
            id: 'particle_cherry_blossom',
            name: '樱花纷飞',
            description: '粉色花瓣下落效果',
            elementType: VisualElementType.particle,
            rarity: VisualElementRarity.rare,
            unlockSource: VisualElementUnlockSource.achievement,
            isDefault: false,
            sortOrder: 10,
            category: 'nature',
            config: {
              'count': 30,
              'shape': 'petal',
              'colors': ['#f9a8d4', '#f472b6', '#ec4899'],
            },
          ),
          VisualElementModel(
            id: 'particle_firefly',
            name: '萤火虫',
            description: '黄绿色闪烁漂浮效果',
            elementType: VisualElementType.particle,
            rarity: VisualElementRarity.rare,
            unlockSource: VisualElementUnlockSource.achievement,
            isDefault: false,
            sortOrder: 20,
            category: 'nature',
            config: {
              'count': 20,
              'shape': 'circle',
              'colors': ['#86efac', '#a3e635', '#fde047'],
            },
            isUnlocked: true,
          ),
          VisualElementModel(
            id: 'particle_snow',
            name: '漫天飞雪',
            description: '白色雪花飘落效果',
            elementType: VisualElementType.particle,
            rarity: VisualElementRarity.rare,
            unlockSource: VisualElementUnlockSource.achievement,
            isDefault: false,
            sortOrder: 30,
            category: 'nature',
            config: {
              'count': 60,
              'shape': 'snowflake',
              'colors': ['#e2e8f0', '#f1f5f9', '#cbd5e1'],
            },
          ),
          VisualElementModel(
            id: 'particle_energy',
            name: '能量粒子',
            description: '多彩能量漂浮效果',
            elementType: VisualElementType.particle,
            rarity: VisualElementRarity.epic,
            unlockSource: VisualElementUnlockSource.achievement,
            isDefault: false,
            sortOrder: 40,
            category: 'abstract',
            config: {
              'count': 40,
              'shape': 'circle',
              'colors': ['#f87171', '#2dd4bf', '#38bdf8'],
            },
          ),
          // Effects
          VisualElementModel(
            id: 'effect_default_glow',
            name: '柔光',
            description: '默认中心柔光效果',
            elementType: VisualElementType.effect,
            rarity: VisualElementRarity.common,
            unlockSource: VisualElementUnlockSource.system,
            isDefault: true,
            sortOrder: 0,
            category: 'ambient',
            config: {
              'effect_type': 'pulse_glow',
              'intensity': 0.3,
              'color': '#e2e8f0',
            },
            isUnlocked: true,
            isEquipped: true,
          ),
          VisualElementModel(
            id: 'effect_pulse',
            name: '脉动光环',
            description: '中心脉动光环效果',
            elementType: VisualElementType.effect,
            rarity: VisualElementRarity.rare,
            unlockSource: VisualElementUnlockSource.achievement,
            isDefault: false,
            sortOrder: 10,
            category: 'ambient',
            config: {
              'effect_type': 'pulse_ring',
              'intensity': 0.6,
              'color': '#2dd4bf',
            },
          ),
          VisualElementModel(
            id: 'effect_gravity_wave',
            name: '引力波',
            description: '涟漪扩散效果',
            elementType: VisualElementType.effect,
            rarity: VisualElementRarity.epic,
            unlockSource: VisualElementUnlockSource.achievement,
            isDefault: false,
            sortOrder: 20,
            category: 'space',
            config: {
              'effect_type': 'gravity_wave',
              'intensity': 0.8,
              'color': '#818cf8',
            },
          ),
        ],
        total: 13,
      );

  UserVisualConfig _getDemoUserConfig() {
    final all = _getDemoVisualElements();
    return UserVisualConfig(
      equippedBackground: all.items.firstWhere(
        (e) => e.elementType == VisualElementType.background && e.isEquipped,
        orElse: () => all.items.firstWhere(
          (e) => e.elementType == VisualElementType.background && e.isDefault,
        ),
      ),
      equippedParticle: all.items.firstWhere(
        (e) => e.elementType == VisualElementType.particle && e.isEquipped,
        orElse: () => all.items.firstWhere(
          (e) => e.elementType == VisualElementType.particle && e.isDefault,
        ),
      ),
      equippedEffect: all.items.firstWhere(
        (e) => e.elementType == VisualElementType.effect && e.isEquipped,
        orElse: () => all.items.firstWhere(
          (e) => e.elementType == VisualElementType.effect && e.isDefault,
        ),
      ),
    );
  }
}

/// Provider for VisualElementRepository
final visualElementRepositoryProvider =
    Provider<VisualElementRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return VisualElementRepository(apiClient);
});
