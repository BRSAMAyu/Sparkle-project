// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'shop_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

ShopItem _$ShopItemFromJson(Map<String, dynamic> json) => ShopItem(
      id: json['id'] as String,
      name: json['name'] as String,
      itemType: $enumDecode(_$ShopItemTypeEnumMap, json['item_type']),
      category: json['category'] as String,
      pricePhotons: (json['price_photons'] as num).toInt(),
      isAvailable: json['is_available'] as bool,
      isLimited: json['is_limited'] as bool,
      rarity: $enumDecode(_$ItemRarityEnumMap, json['rarity']),
      sortOrder: (json['sort_order'] as num).toInt(),
      hasDiscount: json['has_discount'] as bool,
      isInStock: json['is_in_stock'] as bool,
      isOwned: json['is_owned'] as bool,
      description: json['description'] as String?,
      originalPrice: (json['original_price'] as num?)?.toInt(),
      discountPercent: (json['discount_percent'] as num?)?.toInt(),
      stockQuantity: (json['stock_quantity'] as num?)?.toInt(),
      iconUrl: json['icon_url'] as String?,
      itemConfig: json['item_config'] as Map<String, dynamic>?,
    );

Map<String, dynamic> _$ShopItemToJson(ShopItem instance) => <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'description': instance.description,
      'item_type': _$ShopItemTypeEnumMap[instance.itemType]!,
      'category': instance.category,
      'price_photons': instance.pricePhotons,
      'original_price': instance.originalPrice,
      'discount_percent': instance.discountPercent,
      'is_available': instance.isAvailable,
      'is_limited': instance.isLimited,
      'stock_quantity': instance.stockQuantity,
      'icon_url': instance.iconUrl,
      'rarity': _$ItemRarityEnumMap[instance.rarity]!,
      'item_config': instance.itemConfig,
      'sort_order': instance.sortOrder,
      'has_discount': instance.hasDiscount,
      'is_in_stock': instance.isInStock,
      'is_owned': instance.isOwned,
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
      itemId: json['item_id'] as String,
      itemName: json['item_name'] as String,
      itemType: $enumDecode(_$ShopItemTypeEnumMap, json['item_type']),
      pricePaid: (json['price_paid'] as num).toInt(),
      photonBalanceBefore: (json['photon_balance_before'] as num).toInt(),
      photonBalanceAfter: (json['photon_balance_after'] as num).toInt(),
      createdAt: DateTime.parse(json['created_at'] as String),
      itemIconUrl: json['item_icon_url'] as String?,
    );

Map<String, dynamic> _$ShopPurchaseToJson(ShopPurchase instance) =>
    <String, dynamic>{
      'id': instance.id,
      'item_id': instance.itemId,
      'item_name': instance.itemName,
      'item_icon_url': instance.itemIconUrl,
      'item_type': _$ShopItemTypeEnumMap[instance.itemType]!,
      'price_paid': instance.pricePaid,
      'photon_balance_before': instance.photonBalanceBefore,
      'photon_balance_after': instance.photonBalanceAfter,
      'created_at': instance.createdAt.toIso8601String(),
    };

InventoryItem _$InventoryItemFromJson(Map<String, dynamic> json) =>
    InventoryItem(
      id: json['id'] as String,
      name: json['name'] as String,
      itemType: $enumDecode(_$ShopItemTypeEnumMap, json['item_type']),
      rarity: $enumDecode(_$ItemRarityEnumMap, json['rarity']),
      category: json['category'] as String,
      quantity: (json['quantity'] as num).toInt(),
      isEquipped: json['is_equipped'] as bool,
      iconUrl: json['icon_url'] as String?,
      expiresAt: json['expires_at'] == null
          ? null
          : DateTime.parse(json['expires_at'] as String),
      itemConfig: json['item_config'] as Map<String, dynamic>?,
    );

Map<String, dynamic> _$InventoryItemToJson(InventoryItem instance) =>
    <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'icon_url': instance.iconUrl,
      'item_type': _$ShopItemTypeEnumMap[instance.itemType]!,
      'rarity': _$ItemRarityEnumMap[instance.rarity]!,
      'category': instance.category,
      'quantity': instance.quantity,
      'is_equipped': instance.isEquipped,
      'expires_at': instance.expiresAt?.toIso8601String(),
      'item_config': instance.itemConfig,
    };
