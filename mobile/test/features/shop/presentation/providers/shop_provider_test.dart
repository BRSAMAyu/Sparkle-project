import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/shop/data/repositories/shop_repository.dart';
import 'package:sparkle/features/shop/presentation/providers/shop_provider.dart';
import 'package:sparkle/shared/entities/shop_model.dart';

class MockShopRepository extends Mock implements ShopRepository {}

class MockApiClient extends Mock implements ApiClient {}

void main() {
  late MockShopRepository mockRepository;
  late ProviderContainer container;

  setUp(() {
    mockRepository = MockShopRepository();
    container = ProviderContainer(
      overrides: [
        shopRepositoryProvider.overrideWithValue(mockRepository),
      ],
    );
  });

  tearDown(() {
    container.dispose();
  });

  group('ShopItemsProvider', () {
    test('loads shop items on initialization', () async {
      final items = [
        ShopItem(
          id: 'skin_001',
          name: 'Test Skin',
          itemType: ShopItemType.skin,
          category: 'skins',
          pricePhotons: 100,
          rarity: ItemRarity.common,
          sortOrder: 1,
          hasDiscount: false,
          isInStock: true,
          isOwned: false,
        ),
        ShopItem(
          id: 'boost_001',
          name: 'Test Boost',
          itemType: ShopItemType.consumable,
          category: 'boosts',
          pricePhotons: 50,
          rarity: ItemRarity.rare,
          sortOrder: 2,
          hasDiscount: false,
          isInStock: true,
          isOwned: false,
        ),
      ];

      when(mockRepository.getShopItems(
        onlyAvailable: true,
      )).thenAnswer((_) async => items);

      container.read(shopItemsProvider);

      await Future.delayed(Duration.zero);

      final state = container.read(shopItemsProvider);

      expect(state.isLoading, isFalse);
      expect(state.items.length, 2);
      expect(state.error, isNull);
      expect(state.itemsByCategory['skin']?.length, 1);
      expect(state.itemsByCategory['consumable']?.length, 1);

      verify(mockRepository.getShopItems(onlyAvailable: true)).called(1);
    });

    test('groups items by category correctly', () async {
      final items = [
        ShopItem(
          id: 'skin_001',
          name: 'Skin 1',
          itemType: ShopItemType.skin,
          category: 'skins',
          pricePhotons: 100,
          rarity: ItemRarity.common,
          sortOrder: 1,
          hasDiscount: false,
          isInStock: true,
          isOwned: false,
        ),
        ShopItem(
          id: 'skin_002',
          name: 'Skin 2',
          itemType: ShopItemType.skin,
          category: 'skins',
          pricePhotons: 200,
          rarity: ItemRarity.rare,
          sortOrder: 2,
          hasDiscount: false,
          isInStock: true,
          isOwned: false,
        ),
        ShopItem(
          id: 'boost_001',
          name: 'Boost',
          itemType: ShopItemType.consumable,
          category: 'boosts',
          pricePhotons: 50,
          rarity: ItemRarity.common,
          sortOrder: 3,
          hasDiscount: false,
          isInStock: true,
          isOwned: false,
        ),
      ];

      when(mockRepository.getShopItems(
        onlyAvailable: true,
      )).thenAnswer((_) async => items);

      container.read(shopItemsProvider);
      await Future.delayed(Duration.zero);

      final state = container.read(shopItemsProvider);

      expect(state.itemsByCategory['skin']?.length, 2);
      expect(state.itemsByCategory['consumable']?.length, 1);
      expect(state.getItemsByType(ShopItemType.skin).length, 2);
      expect(state.getItemsByType(ShopItemType.consumable).length, 1);
    });

    test('handles load errors gracefully', () async {
      when(mockRepository.getShopItems(
        onlyAvailable: true,
      )).thenThrow(Exception('Network error'));

      container.read(shopItemsProvider);

      await Future.delayed(Duration.zero);

      final state = container.read(shopItemsProvider);

      expect(state.isLoading, isFalse);
      expect(state.items, isEmpty);
      expect(state.error, contains('Network error'));
    });

    test('purchaseItem updates items and returns success', () async {
      final items = [
        ShopItem(
          id: 'skin_001',
          name: 'Test Skin',
          itemType: ShopItemType.skin,
          category: 'skins',
          pricePhotons: 100,
          rarity: ItemRarity.common,
          sortOrder: 1,
          hasDiscount: false,
          isInStock: true,
          isOwned: false,
        ),
      ];

      when(mockRepository.getShopItems(onlyAvailable: true))
          .thenAnswer((_) async => items);

      when(mockRepository.purchaseItem('skin_001'))
          .thenAnswer((_) async => {'success': true});

      // Initial load
      container.read(shopItemsProvider);
      await Future.delayed(Duration.zero);

      // Purchase item
      final notifier = container.read(shopItemsProvider.notifier);
      final result = await notifier.purchaseItem('skin_001');

      expect(result, isTrue);

      // Should refresh items after purchase
      verify(mockRepository.getShopItems(onlyAvailable: true)).called(2);
    });

    test('purchaseItem handles errors and updates error state', () async {
      final items = [
        ShopItem(
          id: 'skin_001',
          name: 'Test Skin',
          itemType: ShopItemType.skin,
          category: 'skins',
          pricePhotons: 100,
          rarity: ItemRarity.common,
          sortOrder: 1,
          hasDiscount: false,
          isInStock: true,
          isOwned: false,
        ),
      ];

      when(mockRepository.getShopItems(onlyAvailable: true))
          .thenAnswer((_) async => items);

      when(mockRepository.purchaseItem('skin_001'))
          .thenThrow(Exception('Insufficient balance'));

      container.read(shopItemsProvider);
      await Future.delayed(Duration.zero);

      final notifier = container.read(shopItemsProvider.notifier);
      final result = await notifier.purchaseItem('skin_001');

      expect(result, isFalse);

      final state = container.read(shopItemsProvider);
      expect(state.error, contains('Insufficient balance'));
    });

    test('refresh reloads items', () async {
      final items = [
        ShopItem(
          id: 'skin_001',
          name: 'Test Skin',
          itemType: ShopItemType.skin,
          category: 'skins',
          pricePhotons: 100,
          rarity: ItemRarity.common,
          sortOrder: 1,
          hasDiscount: false,
          isInStock: true,
          isOwned: false,
        ),
      ];

      when(mockRepository.getShopItems(onlyAvailable: true))
          .thenAnswer((_) async => items);

      container.read(shopItemsProvider);
      await Future.delayed(Duration.zero);

      // Clear the calls
      reset(mockRepository);

      when(mockRepository.getShopItems(onlyAvailable: true))
          .thenAnswer((_) async => items);

      final notifier = container.read(shopItemsProvider.notifier);
      await notifier.refresh();

      await Future.delayed(Duration.zero);

      verify(mockRepository.getShopItems(onlyAvailable: true)).called(1);
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

      when(mockRepository.getPurchaseHistory(limit: 20, offset: 0))
          .thenAnswer((_) async => purchases);

      container.read(purchaseHistoryProvider);

      await Future.delayed(Duration.zero);

      final state = container.read(purchaseHistoryProvider);

      expect(state.isLoading, isFalse);
      expect(state.purchases.length, 1);
      expect(state.purchases[0].itemName, 'Test Skin');
      expect(state.hasMore, isTrue);
    });

    test('loads more history with pagination', () async {
      final page1 = [
        ShopPurchase(
          id: 'purchase-1',
          itemId: 'skin_001',
          itemName: 'Skin 1',
          itemType: ShopItemType.skin,
          pricePaid: 100,
          photonBalanceBefore: 500,
          photonBalanceAfter: 400,
          createdAt: DateTime(2024, 1, 28),
        ),
      ];

      final page2 = [
        ShopPurchase(
          id: 'purchase-2',
          itemId: 'skin_002',
          itemName: 'Skin 2',
          itemType: ShopItemType.skin,
          pricePaid: 200,
          photonBalanceBefore: 400,
          photonBalanceAfter: 200,
          createdAt: DateTime(2024, 1, 28, 11, 0),
        ),
      ];

      when(mockRepository.getPurchaseHistory(limit: 20, offset: 0))
          .thenAnswer((_) async => page1);

      when(mockRepository.getPurchaseHistory(limit: 20, offset: 1))
          .thenAnswer((_) async => page2);

      container.read(purchaseHistoryProvider);
      await Future.delayed(Duration.zero);

      final notifier = container.read(purchaseHistoryProvider.notifier);
      await notifier.loadPurchaseHistory();

      await Future.delayed(Duration.zero);

      final state = container.read(purchaseHistoryProvider);

      expect(state.purchases.length, 2);
      expect(state.currentOffset, 1);
    });

    test('handles empty purchase history', () async {
      when(mockRepository.getPurchaseHistory(limit: 20, offset: 0))
          .thenAnswer((_) async => []);

      container.read(purchaseHistoryProvider);

      await Future.delayed(Duration.zero);

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

      when(mockRepository.getPurchaseHistory(limit: 20, offset: 0))
          .thenAnswer((_) async => purchases);

      container.read(purchaseHistoryProvider);
      await Future.delayed(Duration.zero);

      reset(mockRepository);
      when(mockRepository.getPurchaseHistory(limit: 20, offset: 0))
          .thenAnswer((_) async => purchases);

      final notifier = container.read(purchaseHistoryProvider.notifier);
      await notifier.refresh();

      await Future.delayed(Duration.zero);

      final state = container.read(purchaseHistoryProvider);

      expect(state.purchases.length, 1);
      expect(state.currentOffset, 0);
    });
  });

  group('InventoryProvider', () {
    test('loads user inventory', () async {
      final inventory = {
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

      when(mockRepository.getInventory())
          .thenAnswer((_) async => inventory);

      container.read(inventoryProvider);

      await Future.delayed(Duration.zero);

      final state = container.read(inventoryProvider);

      expect(state.isLoading, isFalse);
      expect(state.skins.length, 1);
      expect(state.titles, isEmpty);
      expect(state.consumables, isEmpty);
      expect(state.boosts, isEmpty);
    });

    test('equipItem updates inventory', () async {
      final inventory = {
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

      when(mockRepository.getInventory())
          .thenAnswer((_) async => inventory);

      when(mockRepository.equipItem(
        itemId: 'skin_001',
        itemType: 'skin',
      )).thenAnswer((_) async => {'success': true});

      container.read(inventoryProvider);
      await Future.delayed(Duration.zero);

      final notifier = container.read(inventoryProvider.notifier);
      final result = await notifier.equipItem(
        itemId: 'skin_001',
        itemType: 'skin',
      );

      expect(result, isTrue);
      verify(mockRepository.getInventory()).called(2); // Initial + after equip
    });

    test('handles equip errors gracefully', () async {
      final inventory = {
        'skins': [],
        'titles': [],
        'consumables': [],
        'boosts': [],
      };

      when(mockRepository.getInventory())
          .thenAnswer((_) async => inventory);

      when(mockRepository.equipItem(
        itemId: 'skin_001',
        itemType: 'skin',
      )).thenThrow(Exception('Item not owned'));

      container.read(inventoryProvider);
      await Future.delayed(Duration.zero);

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
      final inventory = {
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

      when(mockRepository.getInventory())
          .thenAnswer((_) async => inventory);

      container.read(inventoryProvider);
      await Future.delayed(Duration.zero);

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

      when(mockRepository.getOwnedItems())
          .thenAnswer((_) async => ownedIds);

      final future = container.read(ownedItemsProvider);
      final result = await future;

      expect(result.length, 3);
      expect(result, contains('skin_001'));
      expect(result, contains('title_001'));

      verify(mockRepository.getOwnedItems()).called(1);
    });

    test('handles empty owned items', () async {
      when(mockRepository.getOwnedItems())
          .thenAnswer((_) async => []);

      final future = container.read(ownedItemsProvider);
      final result = await future;

      expect(result, isEmpty);
    });
  });

  group('ShopItemsState', () {
    test('copyWith updates state correctly', () {
      final items = [
        ShopItem(
          id: 'skin_001',
          name: 'Test Skin',
          itemType: ShopItemType.skin,
          category: 'skins',
          pricePhotons: 100,
          rarity: ItemRarity.common,
          sortOrder: 1,
          hasDiscount: false,
          isInStock: true,
          isOwned: false,
        ),
      ];

      final state = ShopItemsState(
        items: items,
        isLoading: false,
        error: null,
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
        ShopItem(
          id: 'skin_001',
          name: 'Skin 1',
          itemType: ShopItemType.skin,
          category: 'skins',
          pricePhotons: 100,
          rarity: ItemRarity.common,
          sortOrder: 1,
          hasDiscount: false,
          isInStock: true,
          isOwned: false,
        ),
        ShopItem(
          id: 'boost_001',
          name: 'Boost',
          itemType: ShopItemType.consumable,
          category: 'boosts',
          pricePhotons: 50,
          rarity: ItemRarity.rare,
          sortOrder: 2,
          hasDiscount: false,
          isInStock: true,
          isOwned: false,
        ),
      ];

      final state = ShopItemsState(
        items: items,
        isLoading: false,
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
        isLoading: false,
        hasMore: true,
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
        hasMore: true,
        currentOffset: 0,
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
      final inventory = {
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
      final inventory = {
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
      final item = ShopItem(
        id: 'skin_001',
        name: 'Test Skin',
        itemType: ShopItemType.skin,
        category: 'skins',
        pricePhotons: 100,
        rarity: ItemRarity.common,
        sortOrder: 1,
        hasDiscount: false,
        isInStock: true,
        isOwned: false,
      );

      container.read(selectedShopItemProvider.notifier).state = item;

      final selectedItem = container.read(selectedShopItemProvider);

      expect(selectedItem?.id, 'skin_001');
      expect(selectedItem?.name, 'Test Skin');
    });

    test('can be cleared', () {
      final item = ShopItem(
        id: 'skin_001',
        name: 'Test Skin',
        itemType: ShopItemType.skin,
        category: 'skins',
        pricePhotons: 100,
        rarity: ItemRarity.common,
        sortOrder: 1,
        hasDiscount: false,
        isInStock: true,
        isOwned: false,
      );

      container.read(selectedShopItemProvider.notifier).state = item;

      expect(container.read(selectedShopItemProvider), isNotNull);

      container.read(selectedShopItemProvider.notifier).state = null;

      expect(container.read(selectedShopItemProvider), isNull);
    });
  });

  group('Provider Lifecycle', () {
    test('all providers dispose properly', () {
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

      // Should not throw
      expect(() => testContainer.dispose(), returnsNormally);
    });
  });
}
