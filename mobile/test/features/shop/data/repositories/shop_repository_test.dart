import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/shop/data/repositories/shop_repository.dart';
import 'package:sparkle/shared/entities/shop_model.dart';

class MockApiClient extends Mock implements ApiClient {}

void main() {
  late MockApiClient mockApiClient;
  late ShopRepository repository;

  setUp(() {
    mockApiClient = MockApiClient();
    repository = ShopRepository(mockApiClient);
  });

  group('ShopRepository - getShopItems', () {
    test('returns shop items list from API', () async {
      final responseData = {
        'success': true,
        'data': [
          {
            'id': 'skin_001',
            'name': 'Test Skin',
            'description': 'A test skin',
            'item_type': 'skin',
            'category': 'skins',
            'price_photons': 100,
            'original_price': null,
            'discount_percent': null,
            'is_available': true,
            'is_limited': false,
            'stock_quantity': null,
            'icon_url': 'https://example.com/skin.png',
            'rarity': 'common',
            'item_config': {'skin_id': 'skin_001'},
            'sort_order': 1,
            'has_discount': false,
            'is_in_stock': true,
            'is_owned': false,
          },
          {
            'id': 'boost_001',
            'name': 'Test Boost',
            'description': '2x experience',
            'item_type': 'consumable',
            'category': 'boosts',
            'price_photons': 50,
            'original_price': 100,
            'discount_percent': 50,
            'is_available': true,
            'is_limited': true,
            'stock_quantity': 10,
            'icon_url': 'https://example.com/boost.png',
            'rarity': 'rare',
            'item_config': {'effect_type': 'exp_boost'},
            'sort_order': 2,
            'has_discount': true,
            'is_in_stock': true,
            'is_owned': false,
          },
        ],
        'meta': {
          'total_count': 2,
        },
      };

      when(
        mockApiClient.get<Map<String, dynamic>>(
          '/shop/items',
          queryParameters: {
            'only_available': true,
          },
        ),
      ).thenAnswer(
        (_) async => Response(
          requestOptions: RequestOptions(path: '/shop/items'),
          data: responseData,
        ),
      );

      final result = await repository.getShopItems();

      expect(result.length, 2);
      expect(result[0].id, 'skin_001');
      expect(result[0].itemType, ShopItemType.skin);
      expect(result[0].pricePhotons, 100);
      expect(result[0].hasDiscount, false);

      expect(result[1].id, 'boost_001');
      expect(result[1].itemType, ShopItemType.consumable);
      expect(result[1].hasDiscount, true);
      expect(result[1].discountPercent, 50);
    });

    test('filters items by type', () async {
      when(
        mockApiClient.get<Map<String, dynamic>>(
          '/shop/items',
          queryParameters: argThat(
            (Map<String, dynamic> params) => params['item_type'] == 'skin',
            named: 'queryParameters',
          ),
        ),
      ).thenAnswer(
        (_) async => Response(
          requestOptions: RequestOptions(path: '/shop/items'),
          data: {
            'success': true,
            'data': [
              {
                'id': 'skin_001',
                'name': 'Test Skin',
                'item_type': 'skin',
                'category': 'skins',
                'price_photons': 100,
                'is_available': true,
                'is_limited': false,
                'rarity': 'common',
                'sort_order': 1,
                'has_discount': false,
                'is_in_stock': true,
                'is_owned': false,
              },
            ],
          },
        ),
      );

      final result = await repository.getShopItems(itemType: 'skin');

      expect(result.length, 1);
      expect(result[0].itemType, ShopItemType.skin);
    });

    test('returns empty list when no items', () async {
      when(
        mockApiClient.get<Map<String, dynamic>>(
          any,
          queryParameters: anyNamed('queryParameters'),
        ),
      ).thenAnswer(
        (_) async => Response(
          requestOptions: RequestOptions(path: '/shop/items'),
          data: {
            'success': true,
            'data': [],
          },
        ),
      );

      final result = await repository.getShopItems();

      expect(result, isEmpty);
    });
  });

  group('ShopRepository - purchaseItem', () {
    test('successfully purchases item', () async {
      final itemId = 'skin_001';

      final responseData = {
        'success': true,
        'message': 'Purchase successful',
        'data': {
          'success': true,
          'purchase_id': 'purchase-123',
          'item_id': itemId,
          'item_name': 'Test Skin',
          'price_paid': 100,
          'balance_before': 500,
          'balance_after': 400,
          'item_type': 'skin',
          'rarity': 'common',
        },
        'item': {
          'id': itemId,
          'name': 'Test Skin',
        },
        'balance_before': 500,
        'balance_after': 400,
        'price_paid': 100,
      };

      when(
        mockApiClient.post<Map<String, dynamic>>(
            '/shop/purchase',
            data: argThat(
              (Map<String, dynamic> data) => data['item_id'] == itemId,
              named: 'data',
            ),
          ),
      ).thenAnswer(
        (_) async => Response(
          requestOptions: RequestOptions(path: '/shop/purchase'),
          data: responseData,
        ),
      );

      final result = await repository.purchaseItem(itemId);

      expect(result['success'], isTrue);
      expect(result['price_paid'], 100);
      expect(result['balance_before'], 500);
      expect(result['balance_after'], 400);

      verify(mockApiClient.post<Map<String, dynamic>>(
        '/shop/purchase',
        data: anyNamed('data'),
      )).called(1);
    });

    test('throws exception on insufficient balance', () async {
      when(
        mockApiClient.post<Map<String, dynamic>>(
          '/shop/purchase',
          data: anyNamed('data'),
        ),
      ).thenThrow(
        DioException(
          requestOptions: RequestOptions(path: '/shop/purchase'),
          type: DioExceptionType.badResponse,
          response: Response(
            requestOptions: RequestOptions(path: '/shop/purchase'),
            data: {'detail': 'Insufficient photon balance'},
            statusCode: 400,
          ),
        ),
      );

      expect(
        () => repository.purchaseItem('skin_001'),
        throwsA(isA<Exception>().having(
          (e) => e.toString(),
          'message',
          contains('Insufficient photon balance'),
        )),
      );
    });

    test('throws exception on out of stock', () async {
      when(
        mockApiClient.post<Map<String, dynamic>>(
          '/shop/purchase',
          data: anyNamed('data'),
        ),
      ).thenThrow(
        DioException(
          requestOptions: RequestOptions(path: '/shop/purchase'),
          type: DioExceptionType.badResponse,
          response: Response(
            requestOptions: RequestOptions(path: '/shop/purchase'),
            data: {'detail': 'Item is out of stock'},
            statusCode: 400,
          ),
        ),
      );

      expect(
        () => repository.purchaseItem('limited_item'),
        throwsA(isA<Exception>().having(
          (e) => e.toString(),
          'message',
          contains('out of stock'),
        )),
      );
    });
  });

  group('ShopRepository - getPurchaseHistory', () {
    test('returns purchase history', () async {
      final responseData = {
        'success': true,
        'data': [
          {
            'id': 'purchase-1',
            'item_id': 'skin_001',
            'item_name': 'Test Skin',
            'item_icon_url': 'https://example.com/skin.png',
            'item_type': 'skin',
            'price_paid': 100,
            'photon_balance_before': 500,
            'photon_balance_after': 400,
            'created_at': '2024-01-28T10:00:00.000Z',
          },
          {
            'id': 'purchase-2',
            'item_id': 'boost_001',
            'item_name': 'Test Boost',
            'item_type': 'consumable',
            'price_paid': 50,
            'photon_balance_before': 400,
            'photon_balance_after': 350,
            'created_at': '2024-01-28T11:00:00.000Z',
          },
        ],
        'meta': {
          'total_count': 2,
          'limit': 20,
          'offset': 0,
          'has_next': false,
        },
      };

      when(
        mockApiClient.get<Map<String, dynamic>>(
          '/shop/purchases',
          queryParameters: {
            'limit': 20,
            'offset': 0,
          },
        ),
      ).thenAnswer(
        (_) async => Response(
          requestOptions: RequestOptions(path: '/shop/purchases'),
          data: responseData,
        ),
      );

      final result = await repository.getPurchaseHistory();

      expect(result.length, 2);
      expect(result[0].itemName, 'Test Skin');
      expect(result[0].pricePaid, 100);
      expect(result[1].itemName, 'Test Boost');
      expect(result[1].pricePaid, 50);
    });

    test('paginates correctly', () async {
      when(
        mockApiClient.get<Map<String, dynamic>>(
          '/shop/purchases',
          queryParameters: argThat(
            (Map<String, dynamic> params) =>
                params['limit'] == 10 && params['offset'] == 10,
            named: 'queryParameters',
          ),
        ),
      ).thenAnswer(
        (_) async => Response(
          requestOptions: RequestOptions(path: '/shop/purchases'),
          data: {
            'success': true,
            'data': [
              {
                'id': 'purchase-2',
                'item_id': 'skin_002',
                'item_name': 'Another Skin',
                'item_type': 'skin',
                'price_paid': 200,
                'photon_balance_before': 300,
                'photon_balance_after': 100,
                'created_at': '2024-01-28T12:00:00.000Z',
              },
            ],
          },
        ),
      );

      final result = await repository.getPurchaseHistory(
        limit: 10,
        offset: 10,
      );

      expect(result.length, 1);
      expect(result[0].itemName, 'Another Skin');
    });
  });

  group('ShopRepository - getInventory', () {
    test('returns user inventory grouped by type', () async {
      final responseData = {
        'success': true,
        'data': {
          'skins': [
            {
              'id': 'skin_001',
              'name': 'Test Skin',
              'icon_url': 'https://example.com/skin.png',
              'item_type': 'skin',
              'rarity': 'common',
              'category': 'skins',
              'quantity': 1,
              'is_equipped': true,
              'expires_at': null,
              'item_config': {'skin_id': 'skin_001'},
            },
          ],
          'titles': [],
          'consumables': [
            {
              'id': 'boost_001',
              'name': 'Test Boost',
              'icon_url': 'https://example.com/boost.png',
              'item_type': 'consumable',
              'rarity': 'rare',
              'category': 'boosts',
              'quantity': 3,
              'is_equipped': false,
              'expires_at': '2024-02-28T10:00:00.000Z',
              'item_config': {'effect_type': 'exp_boost'},
            },
          ],
          'boosts': [],
        },
        'meta': {
          'total_skins': 1,
          'total_titles': 0,
          'total_consumables': 1,
          'total_boosts': 0,
          'total_items': 2,
        },
      };

      when(
        mockApiClient.get<Map<String, dynamic>>('/inventory'),
      ).thenAnswer(
        (_) async => Response(
          requestOptions: RequestOptions(path: '/inventory'),
          data: responseData,
        ),
      );

      final result = await repository.getInventory();

      expect(result['skins']?.length, 1);
      expect(result['skins']?[0].isEquipped, isTrue);
      expect(result['titles']?.length, 0);
      expect(result['consumables']?.length, 1);
      expect(result['consumables']?[0].quantity, 3);
    });
  });

  group('ShopRepository - equipItem', () {
    test('successfully equips item', () async {
      final itemId = 'skin_001';
      final itemType = 'skin';

      final responseData = {
        'success': true,
        'message': 'Item equipped',
        'data': {
          'success': true,
          'item_id': itemId,
          'item_name': 'Test Skin',
          'equipped_at': '2024-01-28T10:00:00.000Z',
        },
      };

      when(
        mockApiClient.post<Map<String, dynamic>>(
          '/inventory/equip',
          data: argThat(
            (Map<String, dynamic> data) =>
                data['item_id'] == itemId && data['item_type'] == itemType,
            named: 'data',
          ),
        ),
      ).thenAnswer(
        (_) async => Response(
          requestOptions: RequestOptions(path: '/inventory/equip'),
          data: responseData,
        ),
      );

      final result = await repository.equipItem(
        itemId: itemId,
        itemType: itemType,
      );

      expect(result['success'], isTrue);
      expect(result['item_id'], itemId);

      verify(mockApiClient.post<Map<String, dynamic>>(
        '/inventory/equip',
        data: anyNamed('data'),
      )).called(1);
    });
  });

  group('ShopRepository - getOwnedItems', () {
    test('returns list of owned item IDs', () async {
      final responseData = {
        'success': true,
        'data': ['skin_001', 'skin_002', 'title_001'],
        'meta': {
          'total_count': 3,
          'item_type': 'all',
        },
      };

      when(
        mockApiClient.get<Map<String, dynamic>>(
          '/inventory/owned',
          queryParameters: {},
        ),
      ).thenAnswer(
        (_) async => Response(
          requestOptions: RequestOptions(path: '/inventory/owned'),
          data: responseData,
        ),
      );

      final result = await repository.getOwnedItems();

      expect(result.length, 3);
      expect(result, contains('skin_001'));
      expect(result, contains('skin_002'));
      expect(result, contains('title_001'));
    });

    test('filters by item type', () async {
      when(
        mockApiClient.get<Map<String, dynamic>>(
          '/inventory/owned',
          queryParameters: argThat(
            (Map<String, dynamic> params) => params['item_type'] == 'skin',
            named: 'queryParameters',
          ),
        ),
      ).thenAnswer(
        (_) async => Response(
          requestOptions: RequestOptions(path: '/inventory/owned'),
          data: {
            'success': true,
            'data': ['skin_001', 'skin_002'],
            'meta': {'total_count': 2, 'item_type': 'skin'},
          },
        ),
      );

      final result = await repository.getOwnedItems(itemType: 'skin');

      expect(result.length, 2);
      expect(result, everyElement(startsWith('skin_')));
    });
  });

  group('ShopRepository - useConsumable', () {
    test('successfully uses consumable', () async {
      final consumableId = 'boost_001';
      final quantity = 2;

      final responseData = {
        'success': true,
        'message': 'Consumable used',
        'data': {
          'effect': 'exp_boost',
          'duration_hours': 24,
          'multiplier': 2.0,
        },
        'remaining_quantity': 1,
      };

      when(
        mockApiClient.post<Map<String, dynamic>>(
          '/inventory/consumables/use',
          data: argThat(
            (Map<String, dynamic> data) =>
                data['consumable_id'] == consumableId &&
                data['quantity'] == quantity,
            named: 'data',
          ),
        ),
      ).thenAnswer(
        (_) async => Response(
          requestOptions: RequestOptions(path: '/inventory/consumables/use'),
          data: responseData,
        ),
      );

      final result = await repository.useConsumable(
        consumableId: consumableId,
        quantity: quantity,
      );

      expect(result['effect'], 'exp_boost');
      expect(result['remaining_quantity'], 1);
    });

    test('throws exception when insufficient quantity', () async {
      when(
        mockApiClient.post<Map<String, dynamic>>(
          '/inventory/consumables/use',
          data: anyNamed('data'),
        ),
      ).thenThrow(
        DioException(
          requestOptions: RequestOptions(path: '/inventory/consumables/use'),
          type: DioExceptionType.badResponse,
          response: Response(
            requestOptions: RequestOptions(path: '/inventory/consumables/use'),
            data: {'detail': 'Insufficient consumable quantity'},
            statusCode: 400,
          ),
        ),
      );

      expect(
        () => repository.useConsumable(consumableId: 'boost_001'),
        throwsA(isA<Exception>()),
      );
    });
  });

  group('ShopItem Model', () {
    test('returns correct rarity color', () {
      final commonItem = ShopItem(
        id: '1',
        name: 'Common',
        itemType: ShopItemType.skin,
        category: 'skins',
        pricePhotons: 100,
        rarity: ItemRarity.common,
        sortOrder: 1,
        hasDiscount: false,
        isInStock: true,
        isOwned: false,
      );

      expect(commonItem.rarityColor, '#9E9E9E');

      final rareItem = ShopItem(
        id: '2',
        name: 'Rare',
        itemType: ShopItemType.skin,
        category: 'skins',
        pricePhotons: 200,
        rarity: ItemRarity.rare,
        sortOrder: 1,
        hasDiscount: false,
        isInStock: true,
        isOwned: false,
      );

      expect(rareItem.rarityColor, '#2196F3');
    });

    test('returns correct item type display name', () {
      final skinItem = ShopItem(
        id: '1',
        name: 'Skin',
        itemType: ShopItemType.skin,
        category: 'skins',
        pricePhotons: 100,
        rarity: ItemRarity.common,
        sortOrder: 1,
        hasDiscount: false,
        isInStock: true,
        isOwned: false,
      );

      expect(skinItem.itemTypeName, '皮肤');

      final titleItem = ShopItem(
        id: '2',
        name: 'Title',
        itemType: ShopItemType.title,
        category: 'titles',
        pricePhotons: 150,
        rarity: ItemRarity.rare,
        sortOrder: 1,
        hasDiscount: false,
        isInStock: true,
        isOwned: false,
      );

      expect(titleItem.itemTypeName, '称号');
    });
  });

  group('InventoryItem Model', () {
    test('correctly identifies expired items', () {
      final expiredItem = InventoryItem(
        id: '1',
        name: 'Expired Boost',
        itemType: ShopItemType.consumable,
        rarity: ItemRarity.common,
        category: 'boosts',
        quantity: 1,
        isEquipped: false,
        expiresAt: DateTime(2024, 1, 1), // Past date
      );

      expect(expiredItem.isExpired, isTrue);
      expect(expiredItem.isValid, isFalse);
    });

    test('correctly identifies valid items', () {
      final validItem = InventoryItem(
        id: '2',
        name: 'Valid Boost',
        itemType: ShopItemType.consumable,
        rarity: ItemRarity.rare,
        category: 'boosts',
        quantity: 5,
        isEquipped: false,
        expiresAt: DateTime.now().add(Duration(days: 30)), // Future date
      );

      expect(validItem.isExpired, isFalse);
      expect(validItem.isValid, isTrue);
    });

    test('items without expiration are always valid', () {
      final perpetualItem = InventoryItem(
        id: '3',
        name: 'Perpetual Skin',
        itemType: ShopItemType.skin,
        rarity: ItemRarity.legendary,
        category: 'skins',
        quantity: 1,
        isEquipped: false,
        expiresAt: null,
      );

      expect(perpetualItem.isExpired, isFalse);
      expect(perpetualItem.isValid, isTrue);
    });
  });
}
