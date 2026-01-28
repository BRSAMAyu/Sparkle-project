import 'package:dio/dio.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/shared/entities/shop_model.dart';

/// Shop Repository
/// 商城数据仓库
class ShopRepository {
  ShopRepository(this._apiClient);
  final ApiClient _apiClient;

  /// Handle Dio exceptions
  T _handleDioError<T>(DioException e, String functionName) {
    final errorMessage = e.response?.data?['detail'] ??
        'An unknown error occurred in $functionName';
    throw Exception(errorMessage);
  }

  Map<String, dynamic> _unwrapResponseMap(dynamic data, {String? action}) {
    if (data is Map<String, dynamic>) {
      return data;
    }
    if (data == null) {
      throw Exception('${action ?? "Operation"} response is empty');
    }
    throw Exception('Unexpected response format');
  }

  List<dynamic> _unwrapResponseList(dynamic data) {
    if (data is List) {
      return data;
    }
    if (data is Map<String, dynamic>) {
      final listData = data['data'];
      if (listData is List) {
        return listData;
      }
    }
    throw Exception('Unexpected response format, expected List');
  }

  /// Get shop items list
  /// 获取商城物品列表
  Future<List<ShopItem>> getShopItems({
    String? itemType,
    String? category,
    String? rarity,
    bool onlyAvailable = true,
  }) async {
    try {
      final queryParams = <String, dynamic>{
        'only_available': onlyAvailable,
        if (itemType != null) 'item_type': itemType,
        if (category != null) 'category': category,
        if (rarity != null) 'rarity': rarity,
      };

      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.shopItems,
        queryParameters: queryParams,
      );

      final payload = _unwrapResponseMap(response.data, action: 'getShopItems');
      final dataList = payload['data'] as List<dynamic>?;

      if (dataList == null) {
        return [];
      }

      return dataList
          .map((json) => ShopItem.fromJson(json as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      return _handleDioError<List<ShopItem>>(e, 'getShopItems');
    }
  }

  /// Get shop item detail
  /// 获取商城物品详情
  Future<ShopItem> getShopItemDetail(String itemId) async {
    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        '${ApiEndpoints.shopItems}/$itemId',
      );

      final payload = _unwrapResponseMap(response.data, action: 'getShopItemDetail');
      final data = payload['data'] as Map<String, dynamic>?;

      if (data == null) {
        throw Exception('getShopItemDetail: data field is missing');
      }

      return ShopItem.fromJson(data);
    } on DioException catch (e) {
      return _handleDioError<ShopItem>(e, 'getShopItemDetail');
    }
  }

  /// Purchase item
  /// 购买物品
  Future<Map<String, dynamic>> purchaseItem(String itemId) async {
    try {
      final requestData = <String, dynamic>{
        'item_id': itemId,
      };

      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.shopPurchase,
        data: requestData,
      );

      final payload = _unwrapResponseMap(response.data, action: 'purchaseItem');
      final data = payload['data'] as Map<String, dynamic>?;

      if (data == null) {
        throw Exception('purchaseItem: data field is missing');
      }

      return data;
    } on DioException catch (e) {
      return _handleDioError<Map<String, dynamic>>(e, 'purchaseItem');
    }
  }

  /// Get purchase history
  /// 获取购买历史
  Future<List<ShopPurchase>> getPurchaseHistory({
    int limit = 20,
    int offset = 0,
  }) async {
    try {
      final queryParams = <String, dynamic>{
        'limit': limit,
        'offset': offset,
      };

      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.shopPurchases,
        queryParameters: queryParams,
      );

      final payload = _unwrapResponseMap(response.data, action: 'getPurchaseHistory');
      final dataList = payload['data'] as List<dynamic>?;

      if (dataList == null) {
        return [];
      }

      return dataList
          .map((json) => ShopPurchase.fromJson(json as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      return _handleDioError<List<ShopPurchase>>(e, 'getPurchaseHistory');
    }
  }

  /// Get user inventory
  /// 获取用户物品背包
  Future<Map<String, List<InventoryItem>>> getInventory() async {
    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.inventory,
      );

      final payload = _unwrapResponseMap(response.data, action: 'getInventory');
      final data = payload['data'] as Map<String, dynamic>?;

      if (data == null) {
        return {
          'skins': [],
          'titles': [],
          'consumables': [],
          'boosts': [],
        };
      }

      final inventory = <String, List<InventoryItem>>{};

      for (final category in ['skins', 'titles', 'consumables', 'boosts']) {
        final categoryList = data[category] as List<dynamic>?;
        if (categoryList != null) {
          inventory[category] = categoryList
              .map((json) => InventoryItem.fromJson(json as Map<String, dynamic>))
              .toList();
        } else {
          inventory[category] = [];
        }
      }

      return inventory;
    } on DioException catch (e) {
      return _handleDioError<Map<String, List<InventoryItem>>>(e, 'getInventory');
    }
  }

  /// Equip item (skin or title)
  /// 装备物品
  Future<Map<String, dynamic>> equipItem(String itemType, String? itemId) async {
    try {
      final requestData = <String, dynamic>{
        'item_type': itemType,
        if (itemId != null) 'item_id': itemId,
      };

      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.inventoryEquip,
        data: requestData,
      );

      final payload = _unwrapResponseMap(response.data, action: 'equipItem');
      final data = payload['data'] as Map<String, dynamic>?;

      if (data == null) {
        throw Exception('equipItem: data field is missing');
      }

      return data;
    } on DioException catch (e) {
      return _handleDioError<Map<String, dynamic>>(e, 'equipItem');
    }
  }

  /// Get owned item IDs
  /// 获取已拥有的物品ID列表
  Future<List<String>> getOwnedItems({String? itemType}) async {
    try {
      final queryParams = <String, dynamic>{
        if (itemType != null) 'item_type': itemType,
      };

      final response = await _apiClient.get<Map<String, dynamic>>(
        '${ApiEndpoints.inventory}/owned',
        queryParameters: queryParams,
      );

      final payload = _unwrapResponseMap(response.data, action: 'getOwnedItems');
      final data = payload['data'] as List<dynamic>?;

      if (data == null) {
        return [];
      }

      return data.map((id) => id.toString()).toList();
    } on DioException catch (e) {
      return _handleDioError<List<String>>(e, 'getOwnedItems');
    }
  }

  /// Use consumable
  /// 使用消耗品
  Future<Map<String, dynamic>> useConsumable(String consumableId, {int quantity = 1}) async {
    try {
      final requestData = <String, dynamic>{
        'quantity': quantity,
      };

      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.inventoryConsumablesUse(consumableId),
        data: requestData,
      );

      final payload = _unwrapResponseMap(response.data, action: 'useConsumable');
      final data = payload['data'] as Map<String, dynamic>?;

      if (data == null) {
        throw Exception('useConsumable: data field is missing');
      }

      return data;
    } on DioException catch (e) {
      return _handleDioError<Map<String, dynamic>>(e, 'useConsumable');
    }
  }
}
