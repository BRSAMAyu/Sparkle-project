import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/shop/data/repositories/shop_repository.dart';
import 'package:sparkle/features/shop/presentation/providers/shop_provider.dart';
import 'package:sparkle/shared/entities/shop_model.dart';
import 'package:sparkle/shared/entities/user_brief.dart';
import 'package:sparkle/shared/entities/user_model.dart';

class TestShopRepository implements ShopRepository {
  int getShopItemsCalls = 0;
  int purchaseItemCalls = 0;
  int getPurchaseHistoryCalls = 0;
  int getInventoryCalls = 0;
  int equipItemCalls = 0;
  int getOwnedItemsCalls = 0;

  Future<List<ShopItem>> Function({
    String? itemType,
    String? category,
    String? rarity,
    bool onlyAvailable,
  })? getShopItemsHandler;
  Future<Map<String, dynamic>> Function(String itemId)? purchaseItemHandler;
  Future<List<ShopPurchase>> Function({int limit, int offset})?
      getPurchaseHistoryHandler;
  Future<Map<String, List<InventoryItem>>> Function()? getInventoryHandler;
  Future<Map<String, dynamic>> Function({
    required String itemType,
    String? itemId,
  })? equipItemHandler;
  Future<List<String>> Function({String? itemType})? getOwnedItemsHandler;

  @override
  Future<List<ShopItem>> getShopItems({
    String? itemType,
    String? category,
    String? rarity,
    bool onlyAvailable = true,
  }) async {
    getShopItemsCalls += 1;
    final handler = getShopItemsHandler;
    if (handler != null) {
      return handler(
        itemType: itemType,
        category: category,
        rarity: rarity,
        onlyAvailable: onlyAvailable,
      );
    }
    return [];
  }

  @override
  Future<ShopItem> getShopItemDetail(String itemId) {
    throw UnimplementedError();
  }

  @override
  Future<Map<String, dynamic>> purchaseItem(String itemId) async {
    purchaseItemCalls += 1;
    final handler = purchaseItemHandler;
    if (handler != null) {
      return handler(itemId);
    }
    return {'success': true};
  }

  @override
  Future<List<ShopPurchase>> getPurchaseHistory({
    int limit = 20,
    int offset = 0,
  }) async {
    getPurchaseHistoryCalls += 1;
    final handler = getPurchaseHistoryHandler;
    if (handler != null) {
      return handler(limit: limit, offset: offset);
    }
    return [];
  }

  @override
  Future<Map<String, List<InventoryItem>>> getInventory() async {
    getInventoryCalls += 1;
    final handler = getInventoryHandler;
    if (handler != null) {
      return handler();
    }
    return {
      'skins': [],
      'titles': [],
      'consumables': [],
      'boosts': [],
    };
  }

  @override
  Future<Map<String, dynamic>> equipItem({
    required String itemType,
    String? itemId,
  }) async {
    equipItemCalls += 1;
    final handler = equipItemHandler;
    if (handler != null) {
      return handler(itemType: itemType, itemId: itemId);
    }
    return {'success': true};
  }

  @override
  Future<List<String>> getOwnedItems({String? itemType}) async {
    getOwnedItemsCalls += 1;
    final handler = getOwnedItemsHandler;
    if (handler != null) {
      return handler(itemType: itemType);
    }
    return [];
  }

  @override
  Future<Map<String, dynamic>> useConsumable(
    String consumableId, {
    int quantity = 1,
  }) {
    throw UnimplementedError();
  }
}

ShopItem buildShopItem({
  required String id,
  required String name,
  required ShopItemType itemType,
  String category = 'skins',
  int pricePhotons = 100,
  ItemRarity rarity = ItemRarity.common,
  int sortOrder = 0,
  bool hasDiscount = false,
  bool isInStock = true,
  bool isOwned = false,
  bool isAvailable = true,
  bool isLimited = false,
}) =>
    ShopItem(
      id: id,
      name: name,
      itemType: itemType,
      category: category,
      pricePhotons: pricePhotons,
      rarity: rarity,
      sortOrder: sortOrder,
      hasDiscount: hasDiscount,
      isInStock: isInStock,
      isOwned: isOwned,
      isAvailable: isAvailable,
      isLimited: isLimited,
    );

void main() {
  late TestShopRepository mockRepository;
  late _FakeAuthNotifier authNotifier;
  late ProviderContainer container;

  setUp(() {
    mockRepository = TestShopRepository();
    authNotifier = _FakeAuthNotifier();
    container = ProviderContainer(
      overrides: [
        shopRepositoryProvider.overrideWithValue(mockRepository),
        authProvider.overrideWith((ref) => authNotifier),
      ],
    );
  });

  tearDown(() {
    container.dispose();
  });

  group('ShopItemsProvider', () {
    test('loads shop items on initialization', () async {
      final items = [
        buildShopItem(
          id: 'skin_001',
          name: 'Test Skin',
          itemType: ShopItemType.skin,
          sortOrder: 1,
        ),
        buildShopItem(
          id: 'boost_001',
          name: 'Test Boost',
          itemType: ShopItemType.consumable,
          category: 'boosts',
          pricePhotons: 50,
          rarity: ItemRarity.rare,
          sortOrder: 2,
        ),
      ];

      mockRepository.getShopItemsHandler = ({
        String? itemType,
        String? category,
        String? rarity,
        bool onlyAvailable = true,
      }) async =>
          items;

      container.read(shopItemsProvider);

      await Future<void>.delayed(Duration.zero);

      final state = container.read(shopItemsProvider);

      expect(state.isLoading, isFalse);
      expect(state.items.length, 2);
      expect(state.error, isNull);
      expect(state.itemsByCategory['skin']?.length, 1);
      expect(state.itemsByCategory['consumable']?.length, 1);

      expect(mockRepository.getShopItemsCalls, 1);
    });

    test('groups items by category correctly', () async {
      final items = [
        buildShopItem(
          id: 'skin_001',
          name: 'Skin 1',
          itemType: ShopItemType.skin,
          sortOrder: 1,
        ),
        buildShopItem(
          id: 'skin_002',
          name: 'Skin 2',
          itemType: ShopItemType.skin,
          pricePhotons: 200,
          rarity: ItemRarity.rare,
          sortOrder: 2,
        ),
        buildShopItem(
          id: 'boost_001',
          name: 'Boost',
          itemType: ShopItemType.consumable,
          category: 'boosts',
          pricePhotons: 50,
          sortOrder: 3,
        ),
      ];

      mockRepository.getShopItemsHandler = ({
        String? itemType,
        String? category,
        String? rarity,
        bool onlyAvailable = true,
      }) async =>
          items;

      container.read(shopItemsProvider);
      await Future<void>.delayed(Duration.zero);

      final state = container.read(shopItemsProvider);

      expect(state.itemsByCategory['skin']?.length, 2);
      expect(state.itemsByCategory['consumable']?.length, 1);
      expect(state.getItemsByType(ShopItemType.skin).length, 2);
      expect(state.getItemsByType(ShopItemType.consumable).length, 1);
    });

    test('handles load errors gracefully', () async {
      mockRepository.getShopItemsHandler = ({
        String? itemType,
        String? category,
        String? rarity,
        bool onlyAvailable = true,
      }) async {
        throw Exception('Network error');
      };

      container.read(shopItemsProvider);

      await Future<void>.delayed(Duration.zero);

      final state = container.read(shopItemsProvider);

      expect(state.isLoading, isFalse);
      expect(state.items, isEmpty);
      expect(state.error, contains('Network error'));
    });

    test('purchaseItem updates items and returns success', () async {
      final items = [
        buildShopItem(
          id: 'skin_001',
          name: 'Test Skin',
          itemType: ShopItemType.skin,
          sortOrder: 1,
        ),
      ];

      mockRepository.getShopItemsHandler = ({
        String? itemType,
        String? category,
        String? rarity,
        bool onlyAvailable = true,
      }) async =>
          items;

      mockRepository.purchaseItemHandler = (itemId) async => {'success': true};

      // Initial load
      container.read(shopItemsProvider);
      await Future<void>.delayed(Duration.zero);

      // Purchase item
      final notifier = container.read(shopItemsProvider.notifier);
      final result = await notifier.purchaseItem('skin_001');

      expect(result, isTrue);

      // Should refresh items after purchase
      expect(mockRepository.getShopItemsCalls, 2);
      expect(mockRepository.getInventoryCalls, greaterThanOrEqualTo(2));
      expect(authNotifier.refreshUserCalls, 1);
    });

    test('purchaseItem handles errors and updates error state', () async {
      final items = [
        buildShopItem(
          id: 'skin_001',
          name: 'Test Skin',
          itemType: ShopItemType.skin,
          sortOrder: 1,
        ),
      ];

      mockRepository.getShopItemsHandler = ({
        String? itemType,
        String? category,
        String? rarity,
        bool onlyAvailable = true,
      }) async =>
          items;

      mockRepository.purchaseItemHandler = (itemId) async {
        throw Exception('Insufficient balance');
      };

      container.read(shopItemsProvider);
      await Future<void>.delayed(Duration.zero);

      final notifier = container.read(shopItemsProvider.notifier);
      final result = await notifier.purchaseItem('skin_001');

      expect(result, isFalse);

      final state = container.read(shopItemsProvider);
      expect(state.error, contains('Insufficient balance'));
    });

    test('refresh reloads items', () async {
      final items = [
        buildShopItem(
          id: 'skin_001',
          name: 'Test Skin',
          itemType: ShopItemType.skin,
          sortOrder: 1,
        ),
      ];

      mockRepository.getShopItemsHandler = ({
        String? itemType,
        String? category,
        String? rarity,
        bool onlyAvailable = true,
      }) async =>
          items;

      container.read(shopItemsProvider);
      await Future<void>.delayed(Duration.zero);

      mockRepository.getShopItemsCalls = 0;
      mockRepository.getShopItemsHandler = ({
        String? itemType,
        String? category,
        String? rarity,
        bool onlyAvailable = true,
      }) async =>
          items;

      final notifier = container.read(shopItemsProvider.notifier);
      await notifier.refresh();

      await Future<void>.delayed(Duration.zero);

      expect(mockRepository.getShopItemsCalls, 1);
    });
  });

  group('PurchaseHistoryProvider', () {
    test('loads purchase history', () async {
      final purchases = [
        ShopPurchase(
          id: 'purchase-1',
          itemId: 'skin_001',
          itemName: 'Test Skin',
          itemType: ShopItemType.skin,
          pricePaid: 100,
          photonBalanceBefore: 500,
          photonBalanceAfter: 400,
          createdAt: DateTime(2024, 1, 28),
        ),
      ];

      mockRepository.getPurchaseHistoryHandler = ({
        int limit = 20,
        int offset = 0,
      }) async =>
          purchases;

      container.read(purchaseHistoryProvider);

      final notifier = container.read(purchaseHistoryProvider.notifier);
      await notifier.loadPurchaseHistory();

      final state = container.read(purchaseHistoryProvider);

      expect(state.isLoading, isFalse);
      expect(state.purchases.length, 1);
      expect(state.purchases[0].itemName, 'Test Skin');
      expect(state.hasMore, isFalse);
    });

    test('loads more history with pagination', () async {
      final page1 = List.generate(
        20,
        (index) => ShopPurchase(
          id: 'purchase-${index + 1}',
          itemId: 'skin_${index + 1}',
          itemName: 'Skin ${index + 1}',
          itemType: ShopItemType.skin,
          pricePaid: 100,
          photonBalanceBefore: 500,
          photonBalanceAfter: 400,
          createdAt: DateTime(2024, 1, 28),
        ),
      );

      final page2 = [
        ShopPurchase(
          id: 'purchase-2',
          itemId: 'skin_002',
          itemName: 'Skin 2',
          itemType: ShopItemType.skin,
          pricePaid: 200,
          photonBalanceBefore: 400,
          photonBalanceAfter: 200,
          createdAt: DateTime(2024, 1, 28, 11),
        ),
      ];

      mockRepository.getPurchaseHistoryHandler = ({
        int limit = 20,
        int offset = 0,
      }) async {
        if (offset == 0) {
          return page1;
        }
        return page2;
      };

      container.read(purchaseHistoryProvider);
      final notifier = container.read(purchaseHistoryProvider.notifier);
      await notifier.loadPurchaseHistory();

      await notifier.loadPurchaseHistory();

      await Future<void>.delayed(Duration.zero);

      final state = container.read(purchaseHistoryProvider);

      expect(state.purchases.length, 21);
      expect(state.currentOffset, 21);
    });

    test('handles empty purchase history', () async {
      mockRepository.getPurchaseHistoryHandler = ({
        int limit = 20,
        int offset = 0,
      }) async =>
          [];

      container.read(purchaseHistoryProvider);
      final notifier = container.read(purchaseHistoryProvider.notifier);
      await notifier.loadPurchaseHistory();

      final state = container.read(purchaseHistoryProvider);

      expect(state.isLoading, isFalse);
      expect(state.purchases, isEmpty);
      expect(state.hasMore, isFalse);
    });

    test('refresh clears and reloads history', () async {
      final purchases = [
        ShopPurchase(
          id: 'purchase-1',
          itemId: 'skin_001',
          itemName: 'Test Skin',
          itemType: ShopItemType.skin,
          pricePaid: 100,
          photonBalanceBefore: 500,
          photonBalanceAfter: 400,
          createdAt: DateTime(2024, 1, 28),
        ),
      ];

      mockRepository.getPurchaseHistoryHandler = ({
        int limit = 20,
        int offset = 0,
      }) async =>
          purchases;

      container.read(purchaseHistoryProvider);
      final notifier = container.read(purchaseHistoryProvider.notifier);
      await notifier.loadPurchaseHistory();

      mockRepository.getPurchaseHistoryCalls = 0;
      mockRepository.getPurchaseHistoryHandler = ({
        int limit = 20,
        int offset = 0,
      }) async =>
          purchases;

      await notifier.refresh();

      await Future<void>.delayed(Duration.zero);

      final state = container.read(purchaseHistoryProvider);

      expect(state.purchases.length, 1);
      expect(state.currentOffset, 1);
    });
  });

  group('InventoryProvider', () {
    test('loads user inventory', () async {
      final inventory = <String, List<InventoryItem>>{
        'skins': [
          InventoryItem(
            id: 'skin_001',
            name: 'Test Skin',
            itemType: ShopItemType.skin,
            rarity: ItemRarity.common,
            category: 'skins',
            quantity: 1,
            isEquipped: false,
          ),
        ],
        'titles': [],
        'consumables': [],
        'boosts': [],
      };

      mockRepository.getInventoryHandler = () async => inventory;

      container.read(inventoryProvider);

      await Future<void>.delayed(Duration.zero);

      final state = container.read(inventoryProvider);

      expect(state.isLoading, isFalse);
      expect(state.skins.length, 1);
      expect(state.titles, isEmpty);
      expect(state.consumables, isEmpty);
      expect(state.boosts, isEmpty);
    });

    test('equipItem updates inventory', () async {
      final inventory = <String, List<InventoryItem>>{
        'skins': [
          InventoryItem(
            id: 'skin_001',
            name: 'Test Skin',
            itemType: ShopItemType.skin,
            rarity: ItemRarity.common,
            category: 'skins',
            quantity: 1,
            isEquipped: false,
          ),
        ],
        'titles': [],
        'consumables': [],
        'boosts': [],
      };

      mockRepository.getInventoryHandler = () async => inventory;
      mockRepository.equipItemHandler = ({
        required String itemType,
        String? itemId,
      }) async =>
          {'success': true};

      container.read(inventoryProvider);
      await Future<void>.delayed(Duration.zero);

      final notifier = container.read(inventoryProvider.notifier);
      final result = await notifier.equipItem(
        itemId: 'skin_001',
        itemType: 'skin',
      );

      expect(result, isTrue);
      expect(mockRepository.getInventoryCalls, 2); // Initial + after equip
      expect(authNotifier.refreshUserCalls, 1);
    });

    test('handles equip errors gracefully', () async {
      final inventory = <String, List<InventoryItem>>{
        'skins': [],
        'titles': [],
        'consumables': [],
        'boosts': [],
      };

      mockRepository.getInventoryHandler = () async => inventory;
      mockRepository.equipItemHandler = ({
        required String itemType,
        String? itemId,
      }) async {
        throw Exception('Item not owned');
      };

      container.read(inventoryProvider);
      await Future<void>.delayed(Duration.zero);

      final notifier = container.read(inventoryProvider.notifier);
      final result = await notifier.equipItem(
        itemId: 'skin_001',
        itemType: 'skin',
      );

      expect(result, isFalse);

      final state = container.read(inventoryProvider);
      expect(state.error, contains('Item not owned'));
    });

    test('provides convenient getters for item categories', () async {
      final inventory = <String, List<InventoryItem>>{
        'skins': [
          InventoryItem(
            id: 'skin_001',
            name: 'Skin 1',
            itemType: ShopItemType.skin,
            rarity: ItemRarity.common,
            category: 'skins',
            quantity: 1,
            isEquipped: true,
          ),
          InventoryItem(
            id: 'skin_002',
            name: 'Skin 2',
            itemType: ShopItemType.skin,
            rarity: ItemRarity.rare,
            category: 'skins',
            quantity: 1,
            isEquipped: false,
          ),
        ],
        'titles': [
          InventoryItem(
            id: 'title_001',
            name: 'Test Title',
            itemType: ShopItemType.title,
            rarity: ItemRarity.legendary,
            category: 'titles',
            quantity: 1,
            isEquipped: false,
          ),
        ],
        'consumables': [],
        'boosts': [],
      };

      mockRepository.getInventoryHandler = () async => inventory;

      container.read(inventoryProvider);
      await Future<void>.delayed(Duration.zero);

      final state = container.read(inventoryProvider);

      expect(state.skins.length, 2);
      expect(state.skins[0].isEquipped, isTrue);
      expect(state.titles.length, 1);
      expect(state.consumables, isEmpty);
    });
  });

  group('OwnedItemsProvider', () {
    test('loads owned item IDs', () async {
      final ownedIds = ['skin_001', 'skin_002', 'title_001'];

      mockRepository.getOwnedItemsHandler =
          ({String? itemType}) async => ownedIds;

      final result = await container.read(ownedItemsProvider.future);

      expect(result.length, 3);
      expect(result, contains('skin_001'));
      expect(result, contains('title_001'));

      expect(mockRepository.getOwnedItemsCalls, 1);
    });

    test('handles empty owned items', () async {
      mockRepository.getOwnedItemsHandler = ({String? itemType}) async => [];

      final result = await container.read(ownedItemsProvider.future);

      expect(result, isEmpty);
    });
  });

  group('ShopItemsState', () {
    test('copyWith updates state correctly', () {
      final items = [
        buildShopItem(
          id: 'skin_001',
          name: 'Test Skin',
          itemType: ShopItemType.skin,
          sortOrder: 1,
        ),
      ];

      final state = ShopItemsState(
        items: items,
        itemsByCategory: {},
      );

      final updated = state.copyWith(
        isLoading: true,
      );

      expect(updated.items, items);
      expect(updated.isLoading, isTrue);
      expect(updated.error, isNull);
    });

    test('getItemsByType filters correctly', () {
      final items = [
        buildShopItem(
          id: 'skin_001',
          name: 'Skin 1',
          itemType: ShopItemType.skin,
          sortOrder: 1,
        ),
        buildShopItem(
          id: 'boost_001',
          name: 'Boost',
          itemType: ShopItemType.consumable,
          category: 'boosts',
          pricePhotons: 50,
          rarity: ItemRarity.rare,
          sortOrder: 2,
        ),
      ];

      final state = ShopItemsState(
        items: items,
        itemsByCategory: {
          'skin': [items[0]],
          'consumable': [items[1]],
        },
      );

      final skins = state.getItemsByType(ShopItemType.skin);
      final consumables = state.getItemsByType(ShopItemType.consumable);

      expect(skins.length, 1);
      expect(skins[0].id, 'skin_001');
      expect(consumables.length, 1);
      expect(consumables[0].id, 'boost_001');
    });
  });

  group('PurchaseHistoryState', () {
    test('tracks pagination state correctly', () {
      final purchases = [
        ShopPurchase(
          id: 'p1',
          itemId: 'skin_001',
          itemName: 'Skin',
          itemType: ShopItemType.skin,
          pricePaid: 100,
          photonBalanceBefore: 500,
          photonBalanceAfter: 400,
          createdAt: DateTime(2024, 1, 28),
        ),
      ];

      final state = PurchaseHistoryState(
        purchases: purchases,
        currentOffset: 1,
      );

      expect(state.purchases.length, 1);
      expect(state.hasMore, isTrue);
      expect(state.currentOffset, 1);
    });

    test('copyWith updates pagination state', () {
      final state = PurchaseHistoryState(
        purchases: [],
        isLoading: true,
      );

      final updated = state.copyWith(
        isLoading: false,
        currentOffset: 20,
        hasMore: false,
      );

      expect(updated.isLoading, isFalse);
      expect(updated.currentOffset, 20);
      expect(updated.hasMore, isFalse);
    });
  });

  group('InventoryState', () {
    test('provides category-based accessors', () {
      final inventory = <String, List<InventoryItem>>{
        'skins': [
          InventoryItem(
            id: 'skin_001',
            name: 'Skin',
            itemType: ShopItemType.skin,
            rarity: ItemRarity.common,
            category: 'skins',
            quantity: 1,
            isEquipped: false,
          ),
        ],
        'titles': [],
        'consumables': [],
        'boosts': [],
      };

      final state = InventoryState(inventory: inventory);

      expect(state.skins.length, 1);
      expect(state.titles, isEmpty);
      expect(state.consumables, isEmpty);
      expect(state.boosts, isEmpty);
    });

    test('copyWith preserves inventory structure', () {
      final inventory = <String, List<InventoryItem>>{
        'skins': [],
        'titles': [],
        'consumables': [],
        'boosts': [],
      };

      final state = InventoryState(inventory: inventory);
      final updated = state.copyWith(isLoading: true);

      expect(updated.inventory, inventory);
      expect(updated.isLoading, isTrue);
    });
  });

  group('SelectedShopItemProvider', () {
    test('stores selected shop item', () {
      final item = buildShopItem(
        id: 'skin_001',
        name: 'Test Skin',
        itemType: ShopItemType.skin,
        sortOrder: 1,
      );

      container.read(selectedShopItemProvider.notifier).state = item;

      final selectedItem = container.read(selectedShopItemProvider);

      expect(selectedItem?.id, 'skin_001');
      expect(selectedItem?.name, 'Test Skin');
    });

    test('can be cleared', () {
      final item = buildShopItem(
        id: 'skin_001',
        name: 'Test Skin',
        itemType: ShopItemType.skin,
        sortOrder: 1,
      );

      container.read(selectedShopItemProvider.notifier).state = item;

      expect(container.read(selectedShopItemProvider), isNotNull);

      container.read(selectedShopItemProvider.notifier).state = null;

      expect(container.read(selectedShopItemProvider), isNull);
    });
  });

  group('Provider Lifecycle', () {
    test('all providers dispose properly', () async {
      final testContainer = ProviderContainer(
        overrides: [
          shopRepositoryProvider.overrideWithValue(mockRepository),
        ],
      );

      // Initialize all providers
      testContainer.read(shopItemsProvider);
      testContainer.read(purchaseHistoryProvider);
      testContainer.read(inventoryProvider);
      testContainer.read(ownedItemsProvider);

      await Future<void>.delayed(Duration.zero);

      // Should not throw
      expect(testContainer.dispose, returnsNormally);
    });
  });
}

class _FakeAuthNotifier extends AuthNotifier {
  _FakeAuthNotifier() : super(_UnusedAuthRepository()) {
    state = AuthState(
      isLoading: false,
      isAuthenticated: true,
      user: UserModel(
        id: '00000000-0000-0000-0000-000000000001',
        username: 'shop_test_user',
        email: 'shop@example.com',
        flameLevel: 3,
        flameBrightness: 0.8,
        depthPreference: 0.5,
        curiosityPreference: 0.5,
        isActive: true,
        status: UserStatus.online,
        createdAt: DateTime(2026, 1, 1),
        updatedAt: DateTime(2026, 1, 1),
      ),
    );
  }

  int refreshUserCalls = 0;

  @override
  Future<void> checkAuthStatus() async {}

  @override
  Future<void> refreshUser() async {
    refreshUserCalls += 1;
  }
}

class _UnusedAuthRepository extends AuthRepository {
  _UnusedAuthRepository()
      : super(_UnusedApiClient(), const FlutterSecureStorage());

  @override
  Future<bool> isLoggedIn() async => true;

  @override
  Future<UserModel> getCurrentUser() async => UserModel(
        id: '00000000-0000-0000-0000-000000000001',
        username: 'shop_test_user',
        email: 'shop@example.com',
        flameLevel: 3,
        flameBrightness: 0.8,
        depthPreference: 0.5,
        curiosityPreference: 0.5,
        isActive: true,
        status: UserStatus.online,
        createdAt: DateTime(2026, 1, 1),
        updatedAt: DateTime(2026, 1, 1),
      );

  @override
  Future<void> logout({bool keepDemoMode = false}) async {}
}

class _UnusedApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
