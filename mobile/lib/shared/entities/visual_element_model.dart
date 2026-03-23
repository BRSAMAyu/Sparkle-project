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

  factory VisualElementModel.fromJson(Map<String, dynamic> json) {
    VisualElementType? parseElementType(dynamic raw) {
      final key = raw?.toString();
      return VisualElementType.values
          .where((value) => value.name == key)
          .cast<VisualElementType?>()
          .firstWhere((_) => true, orElse: () => null);
    }

    VisualElementRarity? parseRarity(dynamic raw) {
      final key = raw?.toString();
      return VisualElementRarity.values
          .where((value) => value.name == key)
          .cast<VisualElementRarity?>()
          .firstWhere((_) => true, orElse: () => null);
    }

    VisualElementUnlockSource? parseUnlockSource(dynamic raw) {
      final key = raw?.toString();
      return VisualElementUnlockSource.values
          .where((value) => value.name == key)
          .cast<VisualElementUnlockSource?>()
          .firstWhere((_) => true, orElse: () => null);
    }

    DateTime? parseDate(dynamic value) {
      if (value == null) return null;
      return DateTime.tryParse(value.toString());
    }

    return VisualElementModel(
      id: json['id'] as String,
      name: json['name'] as String,
      description: json['description'] as String?,
      elementType: parseElementType(json['element_type']) ??
          parseElementType(json['elementType']) ??
          VisualElementType.background,
      rarity: parseRarity(json['rarity']) ?? VisualElementRarity.common,
      unlockSource: parseUnlockSource(json['unlock_source']) ??
          parseUnlockSource(json['unlockSource']) ??
          VisualElementUnlockSource.system,
      isDefault: (json['is_default'] ?? json['isDefault'] ?? false) as bool,
      sortOrder: ((json['sort_order'] ?? json['sortOrder'] ?? 0) as num).toInt(),
      previewUrl: json['preview_url'] as String? ?? json['previewUrl'] as String?,
      iconUrl: json['icon_url'] as String? ?? json['iconUrl'] as String?,
      category: json['category'] as String?,
      config: Map<String, dynamic>.from(
        (json['config'] as Map?) ?? const <String, dynamic>{},
      ),
      unlockRequirement: (json['unlock_requirement'] ?? json['unlockRequirement'])
              is Map
          ? Map<String, dynamic>.from(
              (json['unlock_requirement'] ?? json['unlockRequirement']) as Map,
            )
          : null,
      isUnlocked: (json['is_unlocked'] ?? json['isUnlocked'] ?? false) as bool,
      unlockedAt: parseDate(json['unlocked_at'] ?? json['unlockedAt']),
      isEquipped: (json['is_equipped'] ?? json['isEquipped'] ?? false) as bool,
    );
  }

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

  String get displaySlot =>
      config['display_slot']?.toString() ?? elementType.name;

  String? get setId => config['set_id']?.toString();

  int get visibilityWeight =>
      (config['visibility_weight'] as num?)?.toInt() ?? 0;

  String? get prestigeLabel => config['prestige_label']?.toString();

  String? get sourceAchievementId =>
      unlockRequirement?['achievement_id']?.toString() ??
      config['source_achievement_id']?.toString();

  bool get isBundle => elementType == VisualElementType.bundle;

  bool get isPrestigeHighlight => visibilityWeight >= 85;

  Map<String, dynamic> toJson() => <String, dynamic>{
        'id': id,
        'name': name,
        'description': description,
        'element_type': elementType.name,
        'rarity': rarity.name,
        'unlock_source': unlockSource.name,
        'is_default': isDefault,
        'sort_order': sortOrder,
        'preview_url': previewUrl,
        'icon_url': iconUrl,
        'category': category,
        'config': config,
        'unlock_requirement': unlockRequirement,
        'is_unlocked': isUnlocked,
        'unlocked_at': unlockedAt?.toIso8601String(),
        'is_equipped': isEquipped,
      };

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
  }) => VisualElementModel(
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
      UserVisualConfig(
        equippedBackground: (json['equipped_background'] ??
                    json['equippedBackground'])
                is Map<String, dynamic>
            ? VisualElementModel.fromJson(
                (json['equipped_background'] ?? json['equippedBackground'])
                    as Map<String, dynamic>,
              )
            : null,
        equippedParticle:
            (json['equipped_particle'] ?? json['equippedParticle'])
                    is Map<String, dynamic>
                ? VisualElementModel.fromJson(
                    (json['equipped_particle'] ?? json['equippedParticle'])
                        as Map<String, dynamic>,
                  )
                : null,
        equippedEffect: (json['equipped_effect'] ?? json['equippedEffect'])
                is Map<String, dynamic>
            ? VisualElementModel.fromJson(
                (json['equipped_effect'] ?? json['equippedEffect'])
                    as Map<String, dynamic>,
              )
            : null,
        backgroundEquippedAt: DateTime.tryParse(
          (json['background_equipped_at'] ?? json['backgroundEquippedAt'] ?? '')
              .toString(),
        ),
        particleEquippedAt: DateTime.tryParse(
          (json['particle_equipped_at'] ?? json['particleEquippedAt'] ?? '')
              .toString(),
        ),
        effectEquippedAt: DateTime.tryParse(
          (json['effect_equipped_at'] ?? json['effectEquippedAt'] ?? '')
              .toString(),
        ),
      );

  final VisualElementModel? equippedBackground;
  final VisualElementModel? equippedParticle;
  final VisualElementModel? equippedEffect;
  final DateTime? backgroundEquippedAt;
  final DateTime? particleEquippedAt;
  final DateTime? effectEquippedAt;

  Map<String, dynamic> toJson() => <String, dynamic>{
        'equipped_background': equippedBackground?.toJson(),
        'equipped_particle': equippedParticle?.toJson(),
        'equipped_effect': equippedEffect?.toJson(),
        'background_equipped_at': backgroundEquippedAt?.toIso8601String(),
        'particle_equipped_at': particleEquippedAt?.toIso8601String(),
        'effect_equipped_at': effectEquippedAt?.toIso8601String(),
      };

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
      EquipElementResponse(
        success: json['success'] as bool? ?? false,
        message: json['message'] as String? ?? '',
        config: UserVisualConfig.fromJson(
          (json['config'] as Map<String, dynamic>?) ?? const {},
        ),
      );

  final bool success;
  final String message;
  final UserVisualConfig config;

  Map<String, dynamic> toJson() => <String, dynamic>{
        'success': success,
        'message': message,
        'config': config.toJson(),
      };
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
      EquipElementResponseExtended(
        success: json['success'] as bool? ?? false,
        message: json['message'] as String? ?? '',
        config: UserVisualConfig.fromJson(
          (json['config'] as Map<String, dynamic>?) ?? const {},
        ),
        unlockedElements: (json['unlocked_elements'] ??
                    json['unlockedElements'])
                is List<dynamic>
            ? ((json['unlocked_elements'] ?? json['unlockedElements'])
                    as List<dynamic>)
                .whereType<Map<String, dynamic>>()
                .map(VisualElementModel.fromJson)
                .toList()
            : null,
      );

  final bool success;
  final String message;
  final UserVisualConfig config;
  final List<VisualElementModel>? unlockedElements;

  Map<String, dynamic> toJson() => <String, dynamic>{
        'success': success,
        'message': message,
        'config': config.toJson(),
        'unlocked_elements':
            unlockedElements?.map((element) => element.toJson()).toList(),
      };
}
