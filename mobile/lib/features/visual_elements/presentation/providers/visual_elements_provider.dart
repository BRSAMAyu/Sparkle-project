import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/visual_elements/data/repositories/visual_element_repository.dart';
import 'package:sparkle/shared/entities/visual_element_model.dart';

// ========== Visual Elements Extended State ==========

/// 排序选项
enum VisualElementSortBy {
  prestige,
  set,
  name,
  rarity,
  unlockDate,
  sortOrder,
}

/// 筛选选项
class VisualElementFilterOptions {
  const VisualElementFilterOptions({
    this.type,
    this.rarity,
    this.category,
    this.showUnlockedOnly = false,
    this.showEquippedOnly = false,
    this.sortBy = VisualElementSortBy.sortOrder,
  });

  final VisualElementType? type;
  final VisualElementRarity? rarity;
  final String? category;
  final bool showUnlockedOnly;
  final bool showEquippedOnly;
  final VisualElementSortBy sortBy;

  VisualElementFilterOptions copyWith({
    VisualElementType? type,
    VisualElementRarity? rarity,
    String? category,
    bool? showUnlockedOnly,
    bool? showEquippedOnly,
    VisualElementSortBy? sortBy,
  }) =>
      VisualElementFilterOptions(
        type: type ?? this.type,
        rarity: rarity ?? this.rarity,
        category: category ?? this.category,
        showUnlockedOnly: showUnlockedOnly ?? this.showUnlockedOnly,
        showEquippedOnly: showEquippedOnly ?? this.showEquippedOnly,
        sortBy: sortBy ?? this.sortBy,
      );

  bool get hasFilters =>
      type != null ||
      rarity != null ||
      category != null ||
      showUnlockedOnly ||
      showEquippedOnly;
}

/// 视觉元素状态
class VisualElementsState {
  VisualElementsState({
    this.allElements = const [],
    this.unlockedElements = const [],
    this.config,
    this.isLoading = false,
    this.isEquipping = false,
    this.error,
    this.filterOptions = const VisualElementFilterOptions(),
  });

  VisualElementsState.loading()
      : allElements = [],
        unlockedElements = [],
        config = null,
        isLoading = true,
        isEquipping = false,
        error = null,
        filterOptions = const VisualElementFilterOptions();

  VisualElementsState.error(String errorMessage)
      : allElements = [],
        unlockedElements = [],
        config = null,
        isLoading = false,
        isEquipping = false,
        error = errorMessage,
        filterOptions = const VisualElementFilterOptions();

  final List<VisualElementModel> allElements;
  final List<VisualElementModel> unlockedElements;
  final UserVisualConfig? config;
  final bool isLoading;
  final bool isEquipping;
  final String? error;
  final VisualElementFilterOptions filterOptions;

  /// 获取已解锁的元素 ID 集合
  Set<String> get unlockedIds => unlockedElements.map((e) => e.id).toSet();

  /// 获取已装备的元素 ID 集合
  Set<String> get equippedIds {
    final ids = <String>{};
    if (config?.equippedBackground != null) {
      ids.add(config!.equippedBackground!.id);
    }
    if (config?.equippedParticle != null) {
      ids.add(config!.equippedParticle!.id);
    }
    if (config?.equippedEffect != null) {
      ids.add(config!.equippedEffect!.id);
    }
    return ids;
  }

  /// 获取按类型分组的所有元素
  Map<VisualElementType, List<VisualElementModel>> get elementsByType {
    final map = <VisualElementType, List<VisualElementModel>>{};
    for (final element in filteredElements) {
      map.putIfAbsent(element.elementType, () => []).add(element);
    }
    return map;
  }

  /// 获取按类型分组的已解锁元素
  Map<VisualElementType, List<VisualElementModel>> get unlockedByType {
    final map = <VisualElementType, List<VisualElementModel>>{};
    for (final element in unlockedElements) {
      map.putIfAbsent(element.elementType, () => []).add(element);
    }
    return map;
  }

  /// 获取筛选后的元素列表
  List<VisualElementModel> get filteredElements {
    var filtered = allElements;

    if (filterOptions.type != null) {
      filtered =
          filtered.where((e) => e.elementType == filterOptions.type).toList();
    }

    if (filterOptions.rarity != null) {
      filtered =
          filtered.where((e) => e.rarity == filterOptions.rarity).toList();
    }

    if (filterOptions.category != null) {
      filtered =
          filtered.where((e) => e.category == filterOptions.category).toList();
    }

    if (filterOptions.showUnlockedOnly) {
      final unlockedIdSet = unlockedIds;
      filtered = filtered.where((e) => unlockedIdSet.contains(e.id)).toList();
    }

    if (filterOptions.showEquippedOnly) {
      final equippedIdSet = equippedIds;
      filtered = filtered.where((e) => equippedIdSet.contains(e.id)).toList();
    }

    // 排序
    return filtered
      ..sort((a, b) {
        switch (filterOptions.sortBy) {
          case VisualElementSortBy.prestige:
            final visibility = b.visibilityWeight.compareTo(a.visibilityWeight);
            if (visibility != 0) return visibility;
            return a.sortOrder.compareTo(b.sortOrder);
          case VisualElementSortBy.set:
            final setCompare = (a.setId ?? 'zzzz').compareTo(b.setId ?? 'zzzz');
            if (setCompare != 0) return setCompare;
            return b.visibilityWeight.compareTo(a.visibilityWeight);
          case VisualElementSortBy.name:
            return a.name.compareTo(b.name);
          case VisualElementSortBy.rarity:
            // legendary > epic > rare > common
            final rarityOrder = {
              VisualElementRarity.legendary: 4,
              VisualElementRarity.epic: 3,
              VisualElementRarity.rare: 2,
              VisualElementRarity.common: 1,
            };
            return rarityOrder[b.rarity]!.compareTo(rarityOrder[a.rarity]!);
          case VisualElementSortBy.unlockDate:
            // 按解锁时间排序（已解锁的排前面）
            final aUnlocked = unlockedIds.contains(a.id);
            final bUnlocked = unlockedIds.contains(b.id);
            if (aUnlocked && !bUnlocked) return -1;
            if (!aUnlocked && bUnlocked) return 1;
            return a.sortOrder.compareTo(b.sortOrder);
          case VisualElementSortBy.sortOrder:
            return a.sortOrder.compareTo(b.sortOrder);
        }
      });
  }

  /// 获取所有分类
  List<String> get allCategories {
    final categories = <String>{};
    for (final element in allElements) {
      if (element.category != null) {
        categories.add(element.category!);
      }
    }
    return categories.toList()..sort();
  }

  /// 获取统计信息
  VisualElementStats get stats => VisualElementStats(
        totalCount: allElements.length,
        unlockedCount: unlockedElements.length,
        equippedCount: equippedIds.length,
        byType: {
          for (final type in VisualElementType.values)
            type: allElements.where((e) => e.elementType == type).length,
        },
        unlockedByType: {
          for (final type in VisualElementType.values)
            type: unlockedElements.where((e) => e.elementType == type).length,
        },
      );

  VisualElementsState copyWith({
    List<VisualElementModel>? allElements,
    List<VisualElementModel>? unlockedElements,
    UserVisualConfig? config,
    bool? isLoading,
    bool? isEquipping,
    String? error,
    VisualElementFilterOptions? filterOptions,
  }) =>
      VisualElementsState(
        allElements: allElements ?? this.allElements,
        unlockedElements: unlockedElements ?? this.unlockedElements,
        config: config ?? this.config,
        isLoading: isLoading ?? this.isLoading,
        isEquipping: isEquipping ?? this.isEquipping,
        error: error,
        filterOptions: filterOptions ?? this.filterOptions,
      );
}

/// 视觉元素统计信息
class VisualElementStats {
  VisualElementStats({
    required this.totalCount,
    required this.unlockedCount,
    required this.equippedCount,
    required this.byType,
    required this.unlockedByType,
  });

  final int totalCount;
  final int unlockedCount;
  final int equippedCount;
  final Map<VisualElementType, int> byType;
  final Map<VisualElementType, int> unlockedByType;

  double get unlockProgress =>
      totalCount > 0 ? unlockedCount / totalCount : 0.0;
}

// ========== Visual Elements Notifier ==========

class VisualElementsNotifier extends StateNotifier<VisualElementsState> {
  VisualElementsNotifier(this._repository) : super(VisualElementsState());

  final VisualElementRepository _repository;

  /// 加载所有数据
  Future<void> loadAll() async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final results = await Future.wait([
        _repository.getVisualElements(),
        _repository.getUnlockedElements(),
        _repository.getUserConfig(),
      ]);

      state = VisualElementsState(
        allElements: (results[0] as VisualElementListResponse).items,
        unlockedElements: (results[1] as VisualElementListResponse).items,
        config: results[2] as UserVisualConfig,
        isLoading: false,
        filterOptions: state.filterOptions,
      );
    } catch (e) {
      state = VisualElementsState.error('Failed to load visual elements: $e');
    }
  }

  /// 刷新数据
  Future<void> refresh() async {
    await loadAll();
  }

  /// 设置筛选选项
  void setFilterOptions(VisualElementFilterOptions options) {
    state = state.copyWith(filterOptions: options);
  }

  /// 清除筛选
  void clearFilters() {
    state = state.copyWith(
      filterOptions: const VisualElementFilterOptions(),
    );
  }

  /// 装备元素
  Future<bool> equipElement(String elementId) async {
    state = state.copyWith(isEquipping: true);

    try {
      final response = await _repository.equipElement(elementId);
      if (response.success) {
        // 更新配置
        state = state.copyWith(
          config: response.config,
          isEquipping: false,
        );

        // 刷新已解锁列表以更新装备状态
        await _refreshUnlockedElements();
        return true;
      }

      state = state.copyWith(isEquipping: false);
      return false;
    } catch (e) {
      state = state.copyWith(isEquipping: false);
      return false;
    }
  }

  /// 卸下元素
  Future<bool> unequipElement(VisualElementType type) async {
    state = state.copyWith(isEquipping: true);

    try {
      final response = await _repository.unequipElement(type);
      if (response.success) {
        state = state.copyWith(
          config: response.config,
          isEquipping: false,
        );

        await _refreshUnlockedElements();
        return true;
      }

      state = state.copyWith(isEquipping: false);
      return false;
    } catch (e) {
      state = state.copyWith(isEquipping: false);
      return false;
    }
  }

  /// 根据成就解锁元素
  Future<List<VisualElementModel>> unlockByAchievement(
    String achievementId,
  ) async {
    try {
      final unlocked = await _repository.unlockByAchievement(achievementId);

      if (unlocked.isNotEmpty) {
        await _refreshUnlockedElements();
      }

      return unlocked;
    } catch (e) {
      return [];
    }
  }

  /// 刷新已解锁元素
  Future<void> _refreshUnlockedElements() async {
    try {
      final response = await _repository.getUnlockedElements();
      state = state.copyWith(unlockedElements: response.items);
    } catch (e) {
      // Ignore refresh errors
    }
  }
}

// ========== Providers ==========

/// Visual Elements Notifier Provider
final visualElementsNotifierProvider =
    StateNotifierProvider<VisualElementsNotifier, VisualElementsState>((ref) {
  final repository = ref.watch(visualElementRepositoryProvider);
  return VisualElementsNotifier(repository);
});

/// 所有元素列表
final allElementsProvider = Provider<List<VisualElementModel>>((ref) {
  final state = ref.watch(visualElementsNotifierProvider);
  return state.allElements;
});

/// 已解锁元素列表
final unlockedElementsProvider = Provider<List<VisualElementModel>>((ref) {
  final state = ref.watch(visualElementsNotifierProvider);
  return state.unlockedElements;
});

/// 当前配置
final visualConfigProvider = Provider<UserVisualConfig?>((ref) {
  final state = ref.watch(visualElementsNotifierProvider);
  return state.config;
});

/// 已装备的背景
final equippedBackgroundProvider = Provider<VisualElementModel?>((ref) {
  final state = ref.watch(visualElementsNotifierProvider);
  return state.config?.equippedBackground;
});

/// 已装备的粒子
final equippedParticleProvider = Provider<VisualElementModel?>((ref) {
  final state = ref.watch(visualElementsNotifierProvider);
  return state.config?.equippedParticle;
});

/// 已装备的特效
final equippedEffectProvider = Provider<VisualElementModel?>((ref) {
  final state = ref.watch(visualElementsNotifierProvider);
  return state.config?.equippedEffect;
});

/// 按类型分组的元素
final elementsByTypeProvider =
    Provider<Map<VisualElementType, List<VisualElementModel>>>((ref) {
  final state = ref.watch(visualElementsNotifierProvider);
  return state.elementsByType;
});

/// 筛选后的元素
final filteredElementsProvider = Provider<List<VisualElementModel>>((ref) {
  final state = ref.watch(visualElementsNotifierProvider);
  return state.filteredElements;
});

/// 所有分类
final allCategoriesProvider = Provider<List<String>>((ref) {
  final state = ref.watch(visualElementsNotifierProvider);
  return state.allCategories;
});

/// 统计信息
final visualElementStatsProvider = Provider<VisualElementStats>((ref) {
  final state = ref.watch(visualElementsNotifierProvider);
  return state.stats;
});

/// 检查元素是否已解锁
final isElementUnlockedProvider = Provider.family<bool, String>((ref, id) {
  final state = ref.watch(visualElementsNotifierProvider);
  return state.unlockedIds.contains(id);
});

/// 检查元素是否已装备
final isElementEquippedProvider = Provider.family<bool, String>((ref, id) {
  final state = ref.watch(visualElementsNotifierProvider);
  return state.equippedIds.contains(id);
});
