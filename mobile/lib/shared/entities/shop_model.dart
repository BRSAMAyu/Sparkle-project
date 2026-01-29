import 'package:json_annotation/json_annotation.dart';

part 'shop_model.g.dart';

/// 商城物品类型
enum ShopItemType {
  @JsonValue('skin')
  skin,
  @JsonValue('title')
  title,
  @JsonValue('consumable')
  consumable,
  @JsonValue('boost')
  boost,
}

/// 物品稀有度
enum ItemRarity {
  @JsonValue('common')
  common,
  @JsonValue('rare')
  rare,
  @JsonValue('epic')
  epic,
  @JsonValue('legendary')
  legendary,
}

// ========== Shop System Models ==========
//
// NOTE: All shop models use snake_case JSON serialization via fieldRename:
// FieldRename.snake to match the backend API contract. This means toJson()
// will emit snake_case JSON (e.g., "item_type", "price_photons") rather than
// camelCase. Ensure any local storage or caching layers handle this correctly.
//
// ==========

/// 消耗品效果类型
enum ConsumableEffectType {
  @JsonValue('exp_boost')
  expBoost,
  @JsonValue('photon_boost')
  photonBoost,
  @JsonValue('streak_freeze')
  streakFreeze,
  @JsonValue('hint_reveal')
  hintReveal,
  @JsonValue('energy_restore')
  energyRestore,
  @JsonValue('custom_avatar')
  customAvatar,
}

// ========== 商城物品实体 ==========

@JsonSerializable(fieldRename: FieldRename.snake)
class ShopItem {

  ShopItem({
    required this.id,
    required this.name,
    this.description,
    required this.itemType,
    required this.category,
    required this.pricePhotons,
    this.originalPrice,
    this.discountPercent,
    required this.isAvailable,
    required this.isLimited,
    this.stockQuantity,
    this.iconUrl,
    required this.rarity,
    this.itemConfig,
    required this.sortOrder,
    required this.hasDiscount,
    required this.isInStock,
    required this.isOwned,
  });

  factory ShopItem.fromJson(Map<String, dynamic> json) =>
      _$ShopItemFromJson(json);
  final String id;
  final String name;
  final String? description;
  final ShopItemType itemType;
  final String category;
  final int pricePhotons;
  final int? originalPrice;
  final int? discountPercent;
  final bool isAvailable;
  final bool isLimited;
  final int? stockQuantity;
  final String? iconUrl;
  final ItemRarity rarity;
  final Map<String, dynamic>? itemConfig;
  final int sortOrder;
  final bool hasDiscount;
  final bool isInStock;
  final bool isOwned;

  Map<String, dynamic> toJson() => _$ShopItemToJson(this);

  /// 获取稀有度颜色（用于UI显示）
  String get rarityColor {
    switch (rarity) {
      case ItemRarity.common:
        return '#9E9E9E'; // 灰色
      case ItemRarity.rare:
        return '#2196F3'; // 蓝色
      case ItemRarity.epic:
        return '#9C27B0'; // 紫色
      case ItemRarity.legendary:
        return '#FF9800'; // 橙色
    }
  }

  /// 获取物品类型显示名称
  String get itemTypeName {
    switch (itemType) {
      case ShopItemType.skin:
        return '皮肤';
      case ShopItemType.title:
        return '称号';
      case ShopItemType.consumable:
        return '消耗品';
      case ShopItemType.boost:
        return '加成';
    }
  }

  ShopItem copyWith({
    String? id,
    String? name,
    String? description,
    ShopItemType? itemType,
    String? category,
    int? pricePhotons,
    int? originalPrice,
    int? discountPercent,
    bool? isAvailable,
    bool? isLimited,
    int? stockQuantity,
    String? iconUrl,
    ItemRarity? rarity,
    Map<String, dynamic>? itemConfig,
    int? sortOrder,
    bool? hasDiscount,
    bool? isInStock,
    bool? isOwned,
  }) => ShopItem(
      id: id ?? this.id,
      name: name ?? this.name,
      description: description ?? this.description,
      itemType: itemType ?? this.itemType,
      category: category ?? this.category,
      pricePhotons: pricePhotons ?? this.pricePhotons,
      originalPrice: originalPrice ?? this.originalPrice,
      discountPercent: discountPercent ?? this.discountPercent,
      isAvailable: isAvailable ?? this.isAvailable,
      isLimited: isLimited ?? this.isLimited,
      stockQuantity: stockQuantity ?? this.stockQuantity,
      iconUrl: iconUrl ?? this.iconUrl,
      rarity: rarity ?? this.rarity,
      itemConfig: itemConfig ?? this.itemConfig,
      sortOrder: sortOrder ?? this.sortOrder,
      hasDiscount: hasDiscount ?? this.hasDiscount,
      isInStock: isInStock ?? this.isInStock,
      isOwned: isOwned ?? this.isOwned,
    );

  @override
  String toString() => 'ShopItem(id: $id, name: $name, type: $itemType, price: $pricePhotons, isOwned: $isOwned)';
}

// ========== 购买记录实体 ==========

@JsonSerializable(fieldRename: FieldRename.snake)
class ShopPurchase {

  ShopPurchase({
    required this.id,
    required this.itemId,
    required this.itemName,
    this.itemIconUrl,
    required this.itemType,
    required this.pricePaid,
    required this.photonBalanceBefore,
    required this.photonBalanceAfter,
    required this.createdAt,
  });

  factory ShopPurchase.fromJson(Map<String, dynamic> json) =>
      _$ShopPurchaseFromJson(json);
  final String id;
  final String itemId;
  final String itemName;
  final String? itemIconUrl;
  final ShopItemType itemType;
  final int pricePaid;
  final int photonBalanceBefore;
  final int photonBalanceAfter;
  final DateTime createdAt;

  Map<String, dynamic> toJson() => _$ShopPurchaseToJson(this);

  ShopPurchase copyWith({
    String? id,
    String? itemId,
    String? itemName,
    String? itemIconUrl,
    ShopItemType? itemType,
    int? pricePaid,
    int? photonBalanceBefore,
    int? photonBalanceAfter,
    DateTime? createdAt,
  }) => ShopPurchase(
      id: id ?? this.id,
      itemId: itemId ?? this.itemId,
      itemName: itemName ?? this.itemName,
      itemIconUrl: itemIconUrl ?? this.itemIconUrl,
      itemType: itemType ?? this.itemType,
      pricePaid: pricePaid ?? this.pricePaid,
      photonBalanceBefore: photonBalanceBefore ?? this.photonBalanceBefore,
      photonBalanceAfter: photonBalanceAfter ?? this.photonBalanceAfter,
      createdAt: createdAt ?? this.createdAt,
    );

  @override
  String toString() => 'ShopPurchase(id: $id, itemId: $itemId, itemName: $itemName, pricePaid: $pricePaid)';
}

// ========== 用户物品实体（背包） ==========

@JsonSerializable(fieldRename: FieldRename.snake)
class InventoryItem {

  InventoryItem({
    required this.id,
    required this.name,
    this.iconUrl,
    required this.itemType,
    required this.rarity,
    required this.category,
    required this.quantity,
    required this.isEquipped,
    this.expiresAt,
    this.itemConfig,
  });

  factory InventoryItem.fromJson(Map<String, dynamic> json) =>
      _$InventoryItemFromJson(json);
  final String id;
  final String name;
  final String? iconUrl;
  final ShopItemType itemType;
  final ItemRarity rarity;
  final String category;
  final int quantity;
  final bool isEquipped;
  final DateTime? expiresAt;
  final Map<String, dynamic>? itemConfig;

  Map<String, dynamic> toJson() => _$InventoryItemToJson(this);

  /// 是否已过期
  bool get isExpired {
    if (expiresAt == null) return false;
    return DateTime.now().isAfter(expiresAt!);
  }

  /// 是否有效（未过期且有库存）
  bool get isValid => !isExpired && quantity > 0;

  InventoryItem copyWith({
    String? id,
    String? name,
    String? iconUrl,
    ShopItemType? itemType,
    ItemRarity? rarity,
    String? category,
    int? quantity,
    bool? isEquipped,
    DateTime? expiresAt,
    Map<String, dynamic>? itemConfig,
  }) => InventoryItem(
      id: id ?? this.id,
      name: name ?? this.name,
      iconUrl: iconUrl ?? this.iconUrl,
      itemType: itemType ?? this.itemType,
      rarity: rarity ?? this.rarity,
      category: category ?? this.category,
      quantity: quantity ?? this.quantity,
      isEquipped: isEquipped ?? this.isEquipped,
      expiresAt: expiresAt ?? this.expiresAt,
      itemConfig: itemConfig ?? this.itemConfig,
    );

  @override
  String toString() => 'InventoryItem(id: $id, name: $name, type: $itemType, quantity: $quantity, isEquipped: $isEquipped)';
}
