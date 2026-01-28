// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'shop_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

ShopItem _$ShopItemFromJson(Map<String, dynamic> json) => ShopItem(
      id: json['id'] as String,
      name: json['name'] as String,
      description: json['description'] as String?,
      itemType: $enumDecode(_$ShopItemTypeEnumMap, json['itemType']),
      category: json['category'] as String,
      pricePhotons: (json['pricePhotons'] as num).toInt(),
      originalPrice: (json['originalPrice'] as num?)?.toInt(),
      discountPercent: (json['discountPercent'] as num?)?.toInt(),
      isAvailable: json['isAvailable'] as bool,
      isLimited: json['isLimited'] as bool,
      stockQuantity: (json['stockQuantity'] as num?)?.toInt(),
      iconUrl: json['iconUrl'] as String?,
      rarity: $enumDecode(_$ItemRarityEnumMap, json['rarity']),
      itemConfig: json['itemConfig'] as Map<String, dynamic>?,
      sortOrder: (json['sortOrder'] as num).toInt(),
      hasDiscount: json['hasDiscount'] as bool,
      isInStock: json['isInStock'] as bool,
      isOwned: json['isOwned'] as bool,
    );

Map<String, dynamic> _$ShopItemToJson(ShopItem instance) => <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'description': instance.description,
      'itemType': _$ShopItemTypeEnumMap[instance.itemType]!,
      'category': instance.category,
      'pricePhotons': instance.pricePhotons,
      'originalPrice': instance.originalPrice,
      'discountPercent': instance.discountPercent,
      'isAvailable': instance.isAvailable,
      'isLimited': instance.isLimited,
      'stockQuantity': instance.stockQuantity,
      'iconUrl': instance.iconUrl,
      'rarity': _$ItemRarityEnumMap[instance.rarity]!,
      'itemConfig': instance.itemConfig,
      'sortOrder': instance.sortOrder,
      'hasDiscount': instance.hasDiscount,
      'isInStock': instance.isInStock,
      'isOwned': instance.isOwned,
    };

const _$ShopItemTypeEnumMap = {
  ShopItemType.skin: 'skin',
  ShopItemType.title: 'title',
  ShopItemType.consumable: 'consumable',
  ShopItemType.boost: 'boost',
};

const _$ItemRarityEnumMap = {
  ItemRarity.common: 'common',
  ItemRarity.rare: 'rare',
  ItemRarity.epic: 'epic',
  ItemRarity.legendary: 'legendary',
};

ShopPurchase _$ShopPurchaseFromJson(Map<String, dynamic> json) => ShopPurchase(
      id: json['id'] as String,
      itemId: json['itemId'] as String,
      itemName: json['itemName'] as String,
      itemIconUrl: json['itemIconUrl'] as String?,
      itemType: $enumDecode(_$ShopItemTypeEnumMap, json['itemType']),
      pricePaid: (json['pricePaid'] as num).toInt(),
      photonBalanceBefore: (json['photonBalanceBefore'] as num).toInt(),
      photonBalanceAfter: (json['photonBalanceAfter'] as num).toInt(),
      createdAt: DateTime.parse(json['createdAt'] as String),
    );

Map<String, dynamic> _$ShopPurchaseToJson(ShopPurchase instance) =>
    <String, dynamic>{
      'id': instance.id,
      'itemId': instance.itemId,
      'itemName': instance.itemName,
      'itemIconUrl': instance.itemIconUrl,
      'itemType': _$ShopItemTypeEnumMap[instance.itemType]!,
      'pricePaid': instance.pricePaid,
      'photonBalanceBefore': instance.photonBalanceBefore,
      'photonBalanceAfter': instance.photonBalanceAfter,
      'createdAt': instance.createdAt.toIso8601String(),
    };

InventoryItem _$InventoryItemFromJson(Map<String, dynamic> json) =>
    InventoryItem(
      id: json['id'] as String,
      name: json['name'] as String,
      iconUrl: json['iconUrl'] as String?,
      itemType: $enumDecode(_$ShopItemTypeEnumMap, json['itemType']),
      rarity: $enumDecode(_$ItemRarityEnumMap, json['rarity']),
      category: json['category'] as String,
      quantity: (json['quantity'] as num).toInt(),
      isEquipped: json['isEquipped'] as bool,
      expiresAt: json['expiresAt'] == null
          ? null
          : DateTime.parse(json['expiresAt'] as String),
      itemConfig: json['itemConfig'] as Map<String, dynamic>?,
    );

Map<String, dynamic> _$InventoryItemToJson(InventoryItem instance) =>
    <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'iconUrl': instance.iconUrl,
      'itemType': _$ShopItemTypeEnumMap[instance.itemType]!,
      'rarity': _$ItemRarityEnumMap[instance.rarity]!,
      'category': instance.category,
      'quantity': instance.quantity,
      'isEquipped': instance.isEquipped,
      'expiresAt': instance.expiresAt?.toIso8601String(),
      'itemConfig': instance.itemConfig,
    };
