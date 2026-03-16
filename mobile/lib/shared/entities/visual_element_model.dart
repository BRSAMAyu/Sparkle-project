import 'package:json_annotation/json_annotation.dart';

part 'visual_element_model.g.dart';

/// 视觉元素类型
enum VisualElementType {
  @JsonValue('background')
  background,
  @JsonValue('particle')
  particle,
  @JsonValue('effect')
  effect,
  @JsonValue('bundle')
  bundle,
}

/// 视觉元素稀有度
enum VisualElementRarity {
  @JsonValue('common')
  common,
  @JsonValue('rare')
  rare,
  @JsonValue('epic')
  epic,
  @JsonValue('legendary')
  legendary,
}

/// 解锁来源
enum VisualElementUnlockSource {
  @JsonValue('system')
  system,
  @JsonValue('achievement')
  achievement,
  @JsonValue('shop')
  shop,
  @JsonValue('event')
  event,
  @JsonValue('season')
  season,
}

// ========== 视觉元素实体 ==========

@JsonSerializable()
class VisualElementModel {
  VisualElementModel({
    required this.id,
    required this.name,
    required this.elementType,
    required this.rarity,
    required this.unlockSource,
    required this.isDefault,
    required this.sortOrder,
    this.description,
    this.previewUrl,
    this.iconUrl,
    this.category,
    this.config = const {},
    this.unlockRequirement,
    this.isUnlocked = false,
    this.unlockedAt,
    this.isEquipped = false,
  });

  factory VisualElementModel.fromJson(Map<String, dynamic> json) =>
      _$VisualElementModelFromJson(json);

  final String id;
  final String name;
  final String? description;
  final VisualElementType elementType;
  final VisualElementRarity rarity;
  final VisualElementUnlockSource unlockSource;
  final bool isDefault;
  final int sortOrder;
  final String? previewUrl;
  final String? iconUrl;
  final String? category;
  final Map<String, dynamic> config;
  final Map<String, dynamic>? unlockRequirement;

  // 用户相关状态
  final bool isUnlocked;
  final DateTime? unlockedAt;
  final bool isEquipped;

  Map<String, dynamic> toJson() => _$VisualElementModelToJson(this);

  /// 获取稀有度对应的颜色
  static int getRarityColor(VisualElementRarity rarity) {
    switch (rarity) {
      case VisualElementRarity.common:
        return 0xFF9E9E9E; // 灰色
      case VisualElementRarity.rare:
        return 0xFF2196F3; // 蓝色
      case VisualElementRarity.epic:
        return 0xFF9C27B0; // 紫色
      case VisualElementRarity.legendary:
        return 0xFFFF9800; // 金色
    }
  }

  /// 复制并更新状态
  VisualElementModel copyWith({
    bool? isUnlocked,
    DateTime? unlockedAt,
    bool? isEquipped,
  }) {
    return VisualElementModel(
      id: id,
      name: name,
      description: description,
      elementType: elementType,
      rarity: rarity,
      unlockSource: unlockSource,
      isDefault: isDefault,
      sortOrder: sortOrder,
      previewUrl: previewUrl,
      iconUrl: iconUrl,
      category: category,
      config: config,
      unlockRequirement: unlockRequirement,
      isUnlocked: isUnlocked ?? this.isUnlocked,
      unlockedAt: unlockedAt ?? this.unlockedAt,
      isEquipped: isEquipped ?? this.isEquipped,
    );
  }
}

// ========== 用户视觉配置 ==========

@JsonSerializable()
class UserVisualConfig {
  UserVisualConfig({
    this.equippedBackground,
    this.equippedParticle,
    this.equippedEffect,
    this.backgroundEquippedAt,
    this.particleEquippedAt,
    this.effectEquippedAt,
  });

  factory UserVisualConfig.fromJson(Map<String, dynamic> json) =>
      _$UserVisualConfigFromJson(json);

  final VisualElementModel? equippedBackground;
  final VisualElementModel? equippedParticle;
  final VisualElementModel? equippedEffect;
  final DateTime? backgroundEquippedAt;
  final DateTime? particleEquippedAt;
  final DateTime? effectEquippedAt;

  Map<String, dynamic> toJson() => _$UserVisualConfigToJson(this);

  /// 检查是否有任何装备
  bool get hasEquipment =>
      equippedBackground != null ||
      equippedParticle != null ||
      equippedEffect != null;
}

// ========== API 响应模型 ==========

@JsonSerializable()
class VisualElementListResponse {
  VisualElementListResponse({
    required this.items,
    required this.total,
  });

  factory VisualElementListResponse.fromJson(Map<String, dynamic> json) =>
      _$VisualElementListResponseFromJson(json);

  final List<VisualElementModel> items;
  final int total;

  Map<String, dynamic> toJson() => _$VisualElementListResponseToJson(this);
}

@JsonSerializable()
class EquipElementResponse {
  EquipElementResponse({
    required this.success,
    required this.message,
    required this.config,
  });

  factory EquipElementResponse.fromJson(Map<String, dynamic> json) =>
      _$EquipElementResponseFromJson(json);

  final bool success;
  final String message;
  final UserVisualConfig config;

  Map<String, dynamic> toJson() => _$EquipElementResponseToJson(this);
}

/// 装备元素响应模型（扩展版）
@JsonSerializable()
class EquipElementResponseExtended {
  EquipElementResponseExtended({
    required this.success,
    required this.message,
    required this.config,
    this.unlockedElements,
  });

  factory EquipElementResponseExtended.fromJson(Map<String, dynamic> json) =>
      _$EquipElementResponseExtendedFromJson(json);

  final bool success;
  final String message;
  final UserVisualConfig config;
  final List<VisualElementModel>? unlockedElements;

  Map<String, dynamic> toJson() => _$EquipElementResponseExtendedToJson(this);
}
