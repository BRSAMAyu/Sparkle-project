import 'package:freezed_annotation/freezed_annotation.dart';

part 'rpg_models.freezed.dart';
part 'rpg_models.g.dart';

/// 装备类型
enum EquipmentType {
  @JsonValue('hat')
  hat, // 帽子
  @JsonValue('shirt')
  shirt, // 上衣
  @JsonValue('pants')
  pants, // 裤子
  @JsonValue('shoes')
  shoes, // 鞋子
  @JsonValue('weapon')
  weapon, // 武器
  @JsonValue('accessory')
  accessory, // 饰品
}

/// 装备稀有度
enum Rarity {
  @JsonValue('common')
  common, // 普通
  @JsonValue('uncommon')
  uncommon, // 稀有
  @JsonValue('rare')
  rare, // 史诗
  @JsonValue('epic')
  epic, // 传说
  @JsonValue('legendary')
  legendary, // 神话
}

/// 角色属性
enum CharacterAttribute {
  @JsonValue('strength')
  strength, // 力量
  @JsonValue('intelligence')
  intelligence, // 智力
  @JsonValue('agility')
  agility, // 敏捷
  @JsonValue('vitality')
  vitality, // 活力
  @JsonValue('luck')
  luck, // 幸运
}

/// 属性值
@freezed
class AttributeValue with _$AttributeValue {
  const factory AttributeValue({
    required CharacterAttribute attribute,
    required int value,
  }) = _AttributeValue;

  factory AttributeValue.fromJson(Map<String, dynamic> json) => _$AttributeValueFromJson(json);
}

/// 装备数据模型
@freezed
class Equipment with _$Equipment {
  const factory Equipment({
    required String id,
    required String name,
    required EquipmentType type,
    required Rarity rarity,
    required List<AttributeValue> attributes,
    String? description,
    String? spritePath, // 像素图路径
    bool? isUnlocked,
    DateTime? unlockedAt,
    String? unlockCondition,
  }) = _Equipment;

  factory Equipment.fromJson(Map<String, dynamic> json) => _$EquipmentFromJson(json);
}

/// 角色装备栏
@freezed
class CharacterEquipment with _$CharacterEquipment {
  const factory CharacterEquipment({
    String? hat,
    String? shirt,
    String? pants,
    String? shoes,
    String? weapon,
    String? accessory,
  }) = _CharacterEquipment;

  factory CharacterEquipment.fromJson(Map<String, dynamic> json) => _$CharacterEquipmentFromJson(json);
}

/// 角色数据模型
@freezed
class Character with _$Character {
  const factory Character({
    required String id,
    required String userId,
    required String nickname,
    required int level,
    required int experience,
    required int maxExperience,
    required int currentHp,
    required int maxHp,
    required int gold,
    required int gems,
    required List<AttributeValue> baseAttributes,
    required CharacterEquipment equipment,
    List<String>? unlockedEquipment,
    String? currentSprite,
    String? characterClass, // 角色职业
    int? totalLoginDays,
    DateTime? lastLogin,
  }) = _Character;

  factory Character.fromJson(Map<String, dynamic> json) => _$CharacterFromJson(json);
}

/// RPG成长系统状态
@freezed
class RpgState with _$RpgState {
  const factory RpgState({
    Character? character,
    List<Equipment>? allEquipment,
    List<Equipment>? unlockedEquipment,
    bool? isLoading,
    String? error,
  }) = _RpgState;

  factory RpgState.fromJson(Map<String, dynamic> json) => _$RpgStateFromJson(json);
}
