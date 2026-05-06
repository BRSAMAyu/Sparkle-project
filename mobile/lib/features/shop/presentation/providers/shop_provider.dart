import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/shop/data/repositories/shop_repository.dart';
import 'package:sparkle/shared/entities/shop_model.dart';

// ========== Repository Provider ==========

final shopRepositoryProvider = Provider<ShopRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return ShopRepository(apiClient);
});

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
  final String? error;
  final Map<String, List<ShopItem>> itemsByCategory;

  ShopItemsState copyWith({
    List<ShopItem>? items,
    bool? isLoading,
    String? error,
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
      state = state.copyWith(
        isLoading: false,
        error: e.toString().replaceAll('Exception: ', ''),
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
      state = state.copyWith(
        error: e.toString().replaceAll('Exception: ', ''),
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

// ========== Purchase History State ==========

class PurchaseHistoryState {
  PurchaseHistoryState({
    this.purchases = const [],
    this.isLoading = false,
    this.error,
    this.hasMore = true,
    this.currentOffset = 0,
  });
  final List<ShopPurchase> purchases;
  final bool isLoading;
  final String? error;
  final bool hasMore;
  final int currentOffset;

  PurchaseHistoryState copyWith({
    List<ShopPurchase>? purchases,
    bool? isLoading,
    String? error,
    bool? hasMore,
    int? currentOffset,
  }) =>
      PurchaseHistoryState(
        purchases: purchases ?? this.purchases,
        isLoading: isLoading ?? this.isLoading,
        error: error ?? this.error,
        hasMore: hasMore ?? this.hasMore,
        currentOffset: currentOffset ?? this.currentOffset,
      );
}

// ========== Purchase History Provider ==========

class PurchaseHistoryNotifier extends StateNotifier<PurchaseHistoryState> {
  PurchaseHistoryNotifier(this._repository) : super(PurchaseHistoryState());

  final ShopRepository _repository;
  static const int _limit = 20;

  Future<void> loadPurchaseHistory({bool refresh = false}) async {
    if (refresh) {
      state = state.copyWith(
        purchases: [],
        currentOffset: 0,
        hasMore: true,
      );
    }

    if (state.isLoading || !state.hasMore) return;

    state = state.copyWith(isLoading: true);

    try {
      final purchases = await _repository.getPurchaseHistory(
        offset: state.currentOffset,
      );

      final newPurchases = [
        ...state.purchases,
        ...purchases,
      ];

      state = state.copyWith(
        purchases: newPurchases,
        isLoading: false,
        hasMore: purchases.length >= _limit,
        currentOffset: state.currentOffset + purchases.length,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString().replaceAll('Exception: ', ''),
      );
    }
  }

  Future<void> refresh() async {
    await loadPurchaseHistory(refresh: true);
  }
}

// ========== Inventory State ==========

class InventoryState {
  InventoryState({
    this.inventory = const {},
    this.isLoading = false,
    this.error,
  });
  final Map<String, List<InventoryItem>> inventory;
  final bool isLoading;
  final String? error;

  InventoryState copyWith({
    Map<String, List<InventoryItem>>? inventory,
    bool? isLoading,
    String? error,
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
      state = state.copyWith(
        isLoading: false,
        error: e.toString().replaceAll('Exception: ', ''),
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
      state = state.copyWith(
        isLoading: false,
        error: e.toString().replaceAll('Exception: ', ''),
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
