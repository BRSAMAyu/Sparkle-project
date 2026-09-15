import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/shared/entities/visual_element_model.dart';

// ========== Visual Element State ==========

class VisualElementState {
  VisualElementState({
    this.allElements = const [],
    this.unlockedElements = const [],
    this.config,
    this.isLoading = false,
    this.error,
  });

  VisualElementState.loading()
      : allElements = [],
        unlockedElements = [],
        config = null,
        isLoading = true,
        error = null;

  VisualElementState.error(String errorMessage)
      : allElements = [],
        unlockedElements = [],
        config = null,
        isLoading = false,
        error = errorMessage;

  final List<VisualElementModel> allElements;
  final List<VisualElementModel> unlockedElements;
  final UserVisualConfig? config;
  final bool isLoading;
  final String? error;

  /// 获取按类型分组的已解锁元素
  Map<VisualElementType, List<VisualElementModel>> get unlockedByType {
    final map = <VisualElementType, List<VisualElementModel>>{};
    for (final element in unlockedElements) {
      map.putIfAbsent(element.elementType, () => []).add(element);
    }
    return map;
  }

  /// 获取已解锁的背景
  List<VisualElementModel> get unlockedBackgrounds =>
      unlockedElements.where((e) => e.elementType == VisualElementType.background).toList();

  /// 获取已解锁的粒子
  List<VisualElementModel> get unlockedParticles =>
      unlockedElements.where((e) => e.elementType == VisualElementType.particle).toList();

  /// 获取已解锁的特效
  List<VisualElementModel> get unlockedEffects =>
      unlockedElements.where((e) => e.elementType == VisualElementType.effect).toList();

  VisualElementState copyWith({
    List<VisualElementModel>? allElements,
    List<VisualElementModel>? unlockedElements,
    UserVisualConfig? config,
    bool? isLoading,
    String? error,
  }) =>
      VisualElementState(
        allElements: allElements ?? this.allElements,
        unlockedElements: unlockedElements ?? this.unlockedElements,
        config: config ?? this.config,
        isLoading: isLoading ?? this.isLoading,
        error: error,
      );
}

// ========== Visual Element Notifier ==========

class VisualElementNotifier extends StateNotifier<VisualElementState> {
  VisualElementNotifier(this._apiClient) : super(VisualElementState());

  final ApiClient _apiClient;

  /// 加载所有视觉元素
  Future<void> loadAllElements({
    VisualElementType? type,
    VisualElementRarity? rarity,
    String? category,
  }) async {
    state = state.copyWith(isLoading: true);

    try {
    final queryParams = <String, dynamic>{};
      if (type != null) {
        queryParams['element_type'] = type.name;
      }
      if (rarity != null) {
        queryParams['rarity'] = rarity.name;
      }
      if (category != null) {
        queryParams['category'] = category;
      }

    final response = await _apiClient.get<Map<String, dynamic>>(
        '/visual-elements',
        queryParameters: queryParams,
      );

    final data = response.data;
    if (data != null) {
      final listResponse = VisualElementListResponse.fromJson(data);
      state = state.copyWith(
        allElements: listResponse.items,
        isLoading: false,
      );
    }
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: 'Failed to load visual elements: $e',
      );
    }
  }

  /// 加载用户已解锁的元素
  Future<void> loadUnlockedElements({VisualElementType? type}) async {
    state = state.copyWith(isLoading: true);

    try {
    final queryParams = <String, dynamic>{};
      if (type != null) {
        queryParams['element_type'] = type.name;
      }

    final response = await _apiClient.get<Map<String, dynamic>>(
        '/visual-elements/unlocked',
        queryParameters: queryParams,
      );

    final data = response.data;
    if (data != null) {
      final listResponse = VisualElementListResponse.fromJson(data);
      state = state.copyWith(
        unlockedElements: listResponse.items,
        isLoading: false,
      );
    }
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: 'Failed to load unlocked elements: $e',
      );
    }
  }

  /// 加载用户当前配置
  Future<void> loadConfig() async {
    try {
    final response = await _apiClient.get<Map<String, dynamic>>('/visual-elements/config');
    final data = response.data;
    if (data != null) {
      final config = UserVisualConfig.fromJson(data);
      state = state.copyWith(config: config);
    }
    } catch (e) {
      // 如果加载失败， 使用空配置
      state = state.copyWith(config: UserVisualConfig());
    }
  }

  /// 装备视觉元素
  Future<bool> equipElement(String elementId) async {
    try {
    final response = await _apiClient.post<Map<String, dynamic>>(
        '/visual-elements/$elementId/equip',
      );
    final data = response.data;
    if (data != null) {
      final equipResponse = EquipElementResponse.fromJson(data);
      if (equipResponse.success) {
        state = state.copyWith(config: equipResponse.config);
        return true;
      }
    }
      return false;
    } catch (e) {
      return false;
    }
  }

  /// 卸下视觉元素
  Future<bool> unequipElement(VisualElementType type) async {
    try {
    final response = await _apiClient.post<Map<String, dynamic>>(
        '/visual-elements/${type.name}/unequip',
      );
    final data = response.data;
    if (data != null) {
      final equipResponse = EquipElementResponse.fromJson(data);
      if (equipResponse.success) {
        state = state.copyWith(config: equipResponse.config);
        return true;
      }
    }
    return false;
    } catch (e) {
      return false;
    }
  }

  /// 刷新所有数据
  Future<void> refresh() async {
    await Future.wait([
      loadAllElements(),
      loadUnlockedElements(),
      loadConfig(),
    ]);
  }

  /// 根据成就解锁视觉元素（内部使用）
  Future<List<VisualElementModel>> unlockByAchievement(String achievementId) async {
    try {
    final response = await _apiClient.post<Map<String, dynamic>>(
        '/visual-elements/unlock-by-achievement',
        queryParameters: {'achievement_id': achievementId},
      );

    final data = response.data;
    if (data != null && data['items'] != null) {
      final items = data['items'] as List<dynamic>;
      final unlocked = items
          .map((e) => VisualElementModel.fromJson(e as Map<String, dynamic>))
          .toList();

      // 刷新已解锁列表
      await loadUnlockedElements();

      return unlocked;
    }
    } catch (e) {
      return [];
    }
    return [];
  }
}

// ========== Providers ==========

/// Visual Element State Provider
final visualElementProvider =
    StateNotifierProvider<VisualElementNotifier, VisualElementState>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return VisualElementNotifier(apiClient);
});

/// 用户当前装备的背景
final equippedBackgroundProvider = Provider<VisualElementModel?>((ref) {
  final state = ref.watch(visualElementProvider);
  return state.config?.equippedBackground;
});

/// 用户当前装备的粒子
final equippedParticleProvider = Provider<VisualElementModel?>((ref) {
  final state = ref.watch(visualElementProvider);
  return state.config?.equippedParticle;
});

/// 用户当前装备的特效
final equippedEffectProvider = Provider<VisualElementModel?>((ref) {
  final state = ref.watch(visualElementProvider);
  return state.config?.equippedEffect;
});

/// 按类型分组的所有元素
final elementsByTypeProvider =
    Provider<Map<VisualElementType, List<VisualElementModel>>>((ref) {
  final state = ref.watch(visualElementProvider);
  final map = <VisualElementType, List<VisualElementModel>>{};
  for (final element in state.allElements) {
    map.putIfAbsent(element.elementType, () => []).add(element);
  }
  return map;
});

/// 按稀有度分组的所有元素
final elementsByRarityProvider =
    Provider<Map<VisualElementRarity, List<VisualElementModel>>>((ref) {
  final state = ref.watch(visualElementProvider);
  final map = <VisualElementRarity, List<VisualElementModel>>{};
  for (final element in state.allElements) {
    map.putIfAbsent(element.rarity, () => []).add(element);
  }
  return map;
});
