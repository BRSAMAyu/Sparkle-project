import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/display/lexicon/error_lexicon.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/shop/data/repositories/shop_repository.dart';
import 'package:sparkle/features/shop/data/repositories/shop_repository_provider.dart';
import 'package:sparkle/shared/entities/shop_model.dart';

// ========== Shop Items State ==========

class ShopItemsState {
  ShopItemsState({
    this.items = const [],
    this.isLoading = false,
    this.error,
    this.itemsByCategory = const {},
  });
  final List<ShopItem> items;
  final bool isLoading;

  /// N15（A-SPEC3）：UI 可达错误字段只存类型化类别（渲染侧经
  /// error_lexicon owner 出人话）；原始异常细节只进 debugPrint 日志。
  final UiErrorCategory? error;
  final Map<String, List<ShopItem>> itemsByCategory;

  ShopItemsState copyWith({
    List<ShopItem>? items,
    bool? isLoading,
    UiErrorCategory? error,
    Map<String, List<ShopItem>>? itemsByCategory,
  }) =>
      ShopItemsState(
        items: items ?? this.items,
        isLoading: isLoading ?? this.isLoading,
        error: error ?? this.error,
        itemsByCategory: itemsByCategory ?? this.itemsByCategory,
      );

  /// Get items by type
  List<ShopItem> getItemsByType(ShopItemType type) =>
      itemsByCategory[type.name] ?? [];
}

// ========== Shop Items Provider ==========

class ShopItemsNotifier extends StateNotifier<ShopItemsState> {
  ShopItemsNotifier(this._repository, this._ref) : super(ShopItemsState()) {
    unawaited(loadShopItems());
  }

  final ShopRepository _repository;
  final Ref _ref;

  Future<void> loadShopItems({
    String? itemType,
    String? category,
    String? rarity,
    bool onlyAvailable = true,
  }) async {
    state = state.copyWith(isLoading: true);

    try {
      final items = await _repository.getShopItems(
        itemType: itemType,
        category: category,
        rarity: rarity,
        onlyAvailable: onlyAvailable,
      );

      // Group items by category
      final itemsByCategory = <String, List<ShopItem>>{};
      for (final item in items) {
        final category = item.itemType.name;
        itemsByCategory.putIfAbsent(category, () => []).add(item);
      }

      state = state.copyWith(
        items: items,
        itemsByCategory: itemsByCategory,
        isLoading: false,
      );
    } catch (e) {
      debugPrint('[shop] loadShopItems failed: $e');
      state = state.copyWith(
        isLoading: false,
        error: categorizeUiError(e),
      );
    }
  }

  Future<void> refresh() async {
    await loadShopItems();
  }

  Future<bool> purchaseItem(String itemId) async {
    try {
      await _repository.purchaseItem(itemId);
      // Refresh items to update ownership status
      await loadShopItems();
      await _ref.read(inventoryProvider.notifier).refresh();
      await _ref.read(authProvider.notifier).refreshUser();
      return true;
    } catch (e) {
      debugPrint('[shop] purchaseItem failed: $e');
      state = state.copyWith(
        error: categorizeUiError(e),
      );
      return false;
    }
  }
}

final shopItemsProvider =
    StateNotifierProvider<ShopItemsNotifier, ShopItemsState>((ref) {
  final repository = ref.watch(shopRepositoryProvider);
  return ShopItemsNotifier(repository, ref);
});

// ========== Inventory State ==========

class InventoryState {
  InventoryState({
    this.inventory = const {},
    this.isLoading = false,
    this.error,
  });
  final Map<String, List<InventoryItem>> inventory;
  final bool isLoading;

  /// N15（A-SPEC3）：UI 可达错误字段只存类型化类别（渲染侧经
  /// error_lexicon owner 出人话）；原始异常细节只进 debugPrint 日志。
  final UiErrorCategory? error;

  InventoryState copyWith({
    Map<String, List<InventoryItem>>? inventory,
    bool? isLoading,
    UiErrorCategory? error,
  }) =>
      InventoryState(
        inventory: inventory ?? this.inventory,
        isLoading: isLoading ?? this.isLoading,
        error: error ?? this.error,
      );

  List<InventoryItem> get skins => inventory['skins'] ?? [];
  List<InventoryItem> get titles => inventory['titles'] ?? [];
  List<InventoryItem> get consumables => inventory['consumables'] ?? [];
  List<InventoryItem> get boosts => inventory['boosts'] ?? [];
}

// ========== Inventory Provider ==========

class InventoryNotifier extends StateNotifier<InventoryState> {
  InventoryNotifier(this._repository, this._ref) : super(InventoryState()) {
    unawaited(loadInventory());
  }

  final ShopRepository _repository;
  final Ref _ref;

  Future<void> loadInventory() async {
    state = state.copyWith(isLoading: true);

    try {
      final inventory = await _repository.getInventory();
      state = state.copyWith(
        inventory: inventory,
        isLoading: false,
      );
    } catch (e) {
      debugPrint('[shop] loadInventory failed: $e');
      state = state.copyWith(
        isLoading: false,
        error: categorizeUiError(e),
      );
    }
  }

  Future<bool> equipItem({
    required String itemId,
    required String itemType,
  }) async {
    state = state.copyWith(isLoading: true);

    try {
      await _repository.equipItem(itemId: itemId, itemType: itemType);
      // Refresh inventory to update equipped status
      await loadInventory();
      await _ref.read(authProvider.notifier).refreshUser();
      return true;
    } catch (e) {
      debugPrint('[shop] equipItem failed: $e');
      state = state.copyWith(
        isLoading: false,
        error: categorizeUiError(e),
      );
      return false;
    }
  }

  Future<void> refresh() async {
    await loadInventory();
  }
}

final inventoryProvider =
    StateNotifierProvider<InventoryNotifier, InventoryState>((ref) {
  final repository = ref.watch(shopRepositoryProvider);
  return InventoryNotifier(repository, ref);
});

// ========== Purchase History State ==========

class PurchaseHistoryState {
  PurchaseHistoryState({
    this.purchases = const [],
    this.isLoading = false,
    this.error,
    this.currentOffset = 0,
    this.hasMore = true,
  });
  final List<ShopPurchase> purchases;
  final bool isLoading;

  /// N15（A-SPEC3）：UI 可达错误字段只存类型化类别（渲染侧经
  /// error_lexicon owner 出人话）；原始异常细节只进 debugPrint 日志。
  final UiErrorCategory? error;
  final int currentOffset;
  final bool hasMore;

  PurchaseHistoryState copyWith({
    List<ShopPurchase>? purchases,
    bool? isLoading,
    UiErrorCategory? error,
    int? currentOffset,
    bool? hasMore,
  }) =>
      PurchaseHistoryState(
        purchases: purchases ?? this.purchases,
        isLoading: isLoading ?? this.isLoading,
        error: error ?? this.error,
        currentOffset: currentOffset ?? this.currentOffset,
        hasMore: hasMore ?? this.hasMore,
      );
}

// ========== Purchase History Provider ==========

class PurchaseHistoryNotifier extends StateNotifier<PurchaseHistoryState> {
  PurchaseHistoryNotifier(this._repository) : super(PurchaseHistoryState());

  final ShopRepository _repository;

  Future<void> refresh() async {
    state = PurchaseHistoryState();
    await loadPurchaseHistory();
  }

  Future<void> loadPurchaseHistory({int limit = 20, int offset = 0}) async {
    state = state.copyWith(isLoading: true);
    try {
      final purchases = await _repository.getPurchaseHistory(
        limit: limit,
        offset: offset,
      );
      state = state.copyWith(
        purchases: purchases,
        isLoading: false,
        currentOffset: offset,
        hasMore: purchases.length >= limit,
      );
    } catch (e) {
      debugPrint('[shop] loadPurchaseHistory failed: $e');
      state = state.copyWith(
        isLoading: false,
        error: categorizeUiError(e),
      );
    }
  }

  Future<void> loadMore({int limit = 20}) async {
    if (state.isLoading || !state.hasMore) return;
    final offset = state.currentOffset + limit;
    try {
      final more = await _repository.getPurchaseHistory(
        limit: limit,
        offset: offset,
      );
      state = state.copyWith(
        purchases: [...state.purchases, ...more],
        currentOffset: offset,
        hasMore: more.length >= limit,
      );
    } catch (e) {
      debugPrint('[shop] loadMore purchase history failed: $e');
      state = state.copyWith(
        error: categorizeUiError(e),
      );
    }
  }
}

final purchaseHistoryProvider = StateNotifierProvider<PurchaseHistoryNotifier,
    PurchaseHistoryState>((ref) {
  final repository = ref.watch(shopRepositoryProvider);
  return PurchaseHistoryNotifier(repository);
});

// ========== Owned Items Provider ==========

final ownedItemsProvider = FutureProvider<List<String>>((ref) async {
  final repository = ref.watch(shopRepositoryProvider);
  return repository.getOwnedItems();
});

// ========== Selected Shop Item Provider ==========

final selectedShopItemProvider = StateProvider<ShopItem?>((ref) => null);
