// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'visual_element_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

VisualElementModel _$VisualElementModelFromJson(Map<String, dynamic> json) =>
    VisualElementModel(
      id: json['id'] as String,
      name: json['name'] as String,
      elementType: $enumDecode(_$VisualElementTypeEnumMap, json['elementType']),
      rarity: $enumDecode(_$VisualElementRarityEnumMap, json['rarity']),
      unlockSource:
          $enumDecode(_$VisualElementUnlockSourceEnumMap, json['unlockSource']),
      isDefault: json['isDefault'] as bool,
      sortOrder: (json['sortOrder'] as num).toInt(),
      description: json['description'] as String?,
      previewUrl: json['previewUrl'] as String?,
      iconUrl: json['iconUrl'] as String?,
      category: json['category'] as String?,
      config: json['config'] as Map<String, dynamic>? ?? const {},
      unlockRequirement: json['unlockRequirement'] as Map<String, dynamic>?,
      isUnlocked: json['isUnlocked'] as bool? ?? false,
      unlockedAt: json['unlockedAt'] == null
          ? null
          : DateTime.parse(json['unlockedAt'] as String),
      isEquipped: json['isEquipped'] as bool? ?? false,
    );

Map<String, dynamic> _$VisualElementModelToJson(VisualElementModel instance) =>
    <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'description': instance.description,
      'elementType': _$VisualElementTypeEnumMap[instance.elementType]!,
      'rarity': _$VisualElementRarityEnumMap[instance.rarity]!,
      'unlockSource':
          _$VisualElementUnlockSourceEnumMap[instance.unlockSource]!,
      'isDefault': instance.isDefault,
      'sortOrder': instance.sortOrder,
      'previewUrl': instance.previewUrl,
      'iconUrl': instance.iconUrl,
      'category': instance.category,
      'config': instance.config,
      'unlockRequirement': instance.unlockRequirement,
      'isUnlocked': instance.isUnlocked,
      'unlockedAt': instance.unlockedAt?.toIso8601String(),
      'isEquipped': instance.isEquipped,
    };

const _$VisualElementTypeEnumMap = {
  VisualElementType.background: 'background',
  VisualElementType.particle: 'particle',
  VisualElementType.effect: 'effect',
  VisualElementType.bundle: 'bundle',
};

const _$VisualElementRarityEnumMap = {
  VisualElementRarity.common: 'common',
  VisualElementRarity.rare: 'rare',
  VisualElementRarity.epic: 'epic',
  VisualElementRarity.legendary: 'legendary',
};

const _$VisualElementUnlockSourceEnumMap = {
  VisualElementUnlockSource.system: 'system',
  VisualElementUnlockSource.achievement: 'achievement',
  VisualElementUnlockSource.shop: 'shop',
  VisualElementUnlockSource.event: 'event',
  VisualElementUnlockSource.season: 'season',
};

UserVisualConfig _$UserVisualConfigFromJson(Map<String, dynamic> json) =>
    UserVisualConfig(
      equippedBackground: json['equippedBackground'] == null
          ? null
          : VisualElementModel.fromJson(
              json['equippedBackground'] as Map<String, dynamic>),
      equippedParticle: json['equippedParticle'] == null
          ? null
          : VisualElementModel.fromJson(
              json['equippedParticle'] as Map<String, dynamic>),
      equippedEffect: json['equippedEffect'] == null
          ? null
          : VisualElementModel.fromJson(
              json['equippedEffect'] as Map<String, dynamic>),
      backgroundEquippedAt: json['backgroundEquippedAt'] == null
          ? null
          : DateTime.parse(json['backgroundEquippedAt'] as String),
      particleEquippedAt: json['particleEquippedAt'] == null
          ? null
          : DateTime.parse(json['particleEquippedAt'] as String),
      effectEquippedAt: json['effectEquippedAt'] == null
          ? null
          : DateTime.parse(json['effectEquippedAt'] as String),
    );

Map<String, dynamic> _$UserVisualConfigToJson(UserVisualConfig instance) =>
    <String, dynamic>{
      'equippedBackground': instance.equippedBackground,
      'equippedParticle': instance.equippedParticle,
      'equippedEffect': instance.equippedEffect,
      'backgroundEquippedAt': instance.backgroundEquippedAt?.toIso8601String(),
      'particleEquippedAt': instance.particleEquippedAt?.toIso8601String(),
      'effectEquippedAt': instance.effectEquippedAt?.toIso8601String(),
    };

VisualElementListResponse _$VisualElementListResponseFromJson(
        Map<String, dynamic> json) =>
    VisualElementListResponse(
      items: (json['items'] as List<dynamic>)
          .map((e) => VisualElementModel.fromJson(e as Map<String, dynamic>))
          .toList(),
      total: (json['total'] as num).toInt(),
    );

Map<String, dynamic> _$VisualElementListResponseToJson(
        VisualElementListResponse instance) =>
    <String, dynamic>{
      'items': instance.items,
      'total': instance.total,
    };

EquipElementResponse _$EquipElementResponseFromJson(
        Map<String, dynamic> json) =>
    EquipElementResponse(
      success: json['success'] as bool,
      message: json['message'] as String,
      config: UserVisualConfig.fromJson(json['config'] as Map<String, dynamic>),
    );

Map<String, dynamic> _$EquipElementResponseToJson(
        EquipElementResponse instance) =>
    <String, dynamic>{
      'success': instance.success,
      'message': instance.message,
      'config': instance.config,
    };

EquipElementResponseExtended _$EquipElementResponseExtendedFromJson(
        Map<String, dynamic> json) =>
    EquipElementResponseExtended(
      success: json['success'] as bool,
      message: json['message'] as String,
      config: UserVisualConfig.fromJson(json['config'] as Map<String, dynamic>),
      unlockedElements: (json['unlockedElements'] as List<dynamic>?)
          ?.map((e) => VisualElementModel.fromJson(e as Map<String, dynamic>))
          .toList(),
    );

Map<String, dynamic> _$EquipElementResponseExtendedToJson(
        EquipElementResponseExtended instance) =>
    <String, dynamic>{
      'success': instance.success,
      'message': instance.message,
      'config': instance.config,
      'unlockedElements': instance.unlockedElements,
    };
