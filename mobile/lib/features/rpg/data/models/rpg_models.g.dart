// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'rpg_models.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$AttributeValueImpl _$$AttributeValueImplFromJson(Map<String, dynamic> json) =>
    _$AttributeValueImpl(
      attribute: $enumDecode(_$CharacterAttributeEnumMap, json['attribute']),
      value: (json['value'] as num).toInt(),
    );

Map<String, dynamic> _$$AttributeValueImplToJson(
        _$AttributeValueImpl instance) =>
    <String, dynamic>{
      'attribute': _$CharacterAttributeEnumMap[instance.attribute]!,
      'value': instance.value,
    };

const _$CharacterAttributeEnumMap = {
  CharacterAttribute.strength: 'strength',
  CharacterAttribute.intelligence: 'intelligence',
  CharacterAttribute.agility: 'agility',
  CharacterAttribute.vitality: 'vitality',
  CharacterAttribute.luck: 'luck',
};

_$EquipmentImpl _$$EquipmentImplFromJson(Map<String, dynamic> json) =>
    _$EquipmentImpl(
      id: json['id'] as String,
      name: json['name'] as String,
      type: $enumDecode(_$EquipmentTypeEnumMap, json['type']),
      rarity: $enumDecode(_$RarityEnumMap, json['rarity']),
      attributes: (json['attributes'] as List<dynamic>)
          .map((e) => AttributeValue.fromJson(e as Map<String, dynamic>))
          .toList(),
      description: json['description'] as String?,
      spritePath: json['spritePath'] as String?,
      isUnlocked: json['isUnlocked'] as bool?,
      unlockedAt: json['unlockedAt'] == null
          ? null
          : DateTime.parse(json['unlockedAt'] as String),
      unlockCondition: json['unlockCondition'] as String?,
    );

Map<String, dynamic> _$$EquipmentImplToJson(_$EquipmentImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'type': _$EquipmentTypeEnumMap[instance.type]!,
      'rarity': _$RarityEnumMap[instance.rarity]!,
      'attributes': instance.attributes,
      'description': instance.description,
      'spritePath': instance.spritePath,
      'isUnlocked': instance.isUnlocked,
      'unlockedAt': instance.unlockedAt?.toIso8601String(),
      'unlockCondition': instance.unlockCondition,
    };

const _$EquipmentTypeEnumMap = {
  EquipmentType.hat: 'hat',
  EquipmentType.shirt: 'shirt',
  EquipmentType.pants: 'pants',
  EquipmentType.shoes: 'shoes',
  EquipmentType.weapon: 'weapon',
  EquipmentType.accessory: 'accessory',
};

const _$RarityEnumMap = {
  Rarity.common: 'common',
  Rarity.uncommon: 'uncommon',
  Rarity.rare: 'rare',
  Rarity.epic: 'epic',
  Rarity.legendary: 'legendary',
};

_$CharacterEquipmentImpl _$$CharacterEquipmentImplFromJson(
        Map<String, dynamic> json) =>
    _$CharacterEquipmentImpl(
      hat: json['hat'] as String?,
      shirt: json['shirt'] as String?,
      pants: json['pants'] as String?,
      shoes: json['shoes'] as String?,
      weapon: json['weapon'] as String?,
      accessory: json['accessory'] as String?,
    );

Map<String, dynamic> _$$CharacterEquipmentImplToJson(
        _$CharacterEquipmentImpl instance) =>
    <String, dynamic>{
      'hat': instance.hat,
      'shirt': instance.shirt,
      'pants': instance.pants,
      'shoes': instance.shoes,
      'weapon': instance.weapon,
      'accessory': instance.accessory,
    };

_$CharacterImpl _$$CharacterImplFromJson(Map<String, dynamic> json) =>
    _$CharacterImpl(
      id: json['id'] as String,
      userId: json['userId'] as String,
      nickname: json['nickname'] as String,
      level: (json['level'] as num).toInt(),
      experience: (json['experience'] as num).toInt(),
      maxExperience: (json['maxExperience'] as num).toInt(),
      currentHp: (json['currentHp'] as num).toInt(),
      maxHp: (json['maxHp'] as num).toInt(),
      gold: (json['gold'] as num).toInt(),
      gems: (json['gems'] as num).toInt(),
      baseAttributes: (json['baseAttributes'] as List<dynamic>)
          .map((e) => AttributeValue.fromJson(e as Map<String, dynamic>))
          .toList(),
      equipment: CharacterEquipment.fromJson(
          json['equipment'] as Map<String, dynamic>),
      unlockedEquipment: (json['unlockedEquipment'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
      currentSprite: json['currentSprite'] as String?,
      characterClass: json['characterClass'] as String?,
      totalLoginDays: (json['totalLoginDays'] as num?)?.toInt(),
      lastLogin: json['lastLogin'] == null
          ? null
          : DateTime.parse(json['lastLogin'] as String),
    );

Map<String, dynamic> _$$CharacterImplToJson(_$CharacterImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'userId': instance.userId,
      'nickname': instance.nickname,
      'level': instance.level,
      'experience': instance.experience,
      'maxExperience': instance.maxExperience,
      'currentHp': instance.currentHp,
      'maxHp': instance.maxHp,
      'gold': instance.gold,
      'gems': instance.gems,
      'baseAttributes': instance.baseAttributes,
      'equipment': instance.equipment,
      'unlockedEquipment': instance.unlockedEquipment,
      'currentSprite': instance.currentSprite,
      'characterClass': instance.characterClass,
      'totalLoginDays': instance.totalLoginDays,
      'lastLogin': instance.lastLogin?.toIso8601String(),
    };

_$RpgStateImpl _$$RpgStateImplFromJson(Map<String, dynamic> json) =>
    _$RpgStateImpl(
      character: json['character'] == null
          ? null
          : Character.fromJson(json['character'] as Map<String, dynamic>),
      allEquipment: (json['allEquipment'] as List<dynamic>?)
          ?.map((e) => Equipment.fromJson(e as Map<String, dynamic>))
          .toList(),
      unlockedEquipment: (json['unlockedEquipment'] as List<dynamic>?)
          ?.map((e) => Equipment.fromJson(e as Map<String, dynamic>))
          .toList(),
      isLoading: json['isLoading'] as bool?,
      error: json['error'] as String?,
    );

Map<String, dynamic> _$$RpgStateImplToJson(_$RpgStateImpl instance) =>
    <String, dynamic>{
      'character': instance.character,
      'allEquipment': instance.allEquipment,
      'unlockedEquipment': instance.unlockedEquipment,
      'isLoading': instance.isLoading,
      'error': instance.error,
    };
