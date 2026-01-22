// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'rpg_models.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

AttributeValue _$AttributeValueFromJson(Map<String, dynamic> json) {
  return _AttributeValue.fromJson(json);
}

/// @nodoc
mixin _$AttributeValue {
  CharacterAttribute get attribute => throw _privateConstructorUsedError;
  int get value => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $AttributeValueCopyWith<AttributeValue> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $AttributeValueCopyWith<$Res> {
  factory $AttributeValueCopyWith(
          AttributeValue value, $Res Function(AttributeValue) then) =
      _$AttributeValueCopyWithImpl<$Res, AttributeValue>;
  @useResult
  $Res call({CharacterAttribute attribute, int value});
}

/// @nodoc
class _$AttributeValueCopyWithImpl<$Res, $Val extends AttributeValue>
    implements $AttributeValueCopyWith<$Res> {
  _$AttributeValueCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? attribute = null,
    Object? value = null,
  }) {
    return _then(_value.copyWith(
      attribute: null == attribute
          ? _value.attribute
          : attribute // ignore: cast_nullable_to_non_nullable
              as CharacterAttribute,
      value: null == value
          ? _value.value
          : value // ignore: cast_nullable_to_non_nullable
              as int,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$AttributeValueImplCopyWith<$Res>
    implements $AttributeValueCopyWith<$Res> {
  factory _$$AttributeValueImplCopyWith(_$AttributeValueImpl value,
          $Res Function(_$AttributeValueImpl) then) =
      __$$AttributeValueImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({CharacterAttribute attribute, int value});
}

/// @nodoc
class __$$AttributeValueImplCopyWithImpl<$Res>
    extends _$AttributeValueCopyWithImpl<$Res, _$AttributeValueImpl>
    implements _$$AttributeValueImplCopyWith<$Res> {
  __$$AttributeValueImplCopyWithImpl(
      _$AttributeValueImpl _value, $Res Function(_$AttributeValueImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? attribute = null,
    Object? value = null,
  }) {
    return _then(_$AttributeValueImpl(
      attribute: null == attribute
          ? _value.attribute
          : attribute // ignore: cast_nullable_to_non_nullable
              as CharacterAttribute,
      value: null == value
          ? _value.value
          : value // ignore: cast_nullable_to_non_nullable
              as int,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$AttributeValueImpl implements _AttributeValue {
  const _$AttributeValueImpl({required this.attribute, required this.value});

  factory _$AttributeValueImpl.fromJson(Map<String, dynamic> json) =>
      _$$AttributeValueImplFromJson(json);

  @override
  final CharacterAttribute attribute;
  @override
  final int value;

  @override
  String toString() {
    return 'AttributeValue(attribute: $attribute, value: $value)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$AttributeValueImpl &&
            (identical(other.attribute, attribute) ||
                other.attribute == attribute) &&
            (identical(other.value, value) || other.value == value));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode => Object.hash(runtimeType, attribute, value);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$AttributeValueImplCopyWith<_$AttributeValueImpl> get copyWith =>
      __$$AttributeValueImplCopyWithImpl<_$AttributeValueImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$AttributeValueImplToJson(
      this,
    );
  }
}

abstract class _AttributeValue implements AttributeValue {
  const factory _AttributeValue(
      {required final CharacterAttribute attribute,
      required final int value}) = _$AttributeValueImpl;

  factory _AttributeValue.fromJson(Map<String, dynamic> json) =
      _$AttributeValueImpl.fromJson;

  @override
  CharacterAttribute get attribute;
  @override
  int get value;
  @override
  @JsonKey(ignore: true)
  _$$AttributeValueImplCopyWith<_$AttributeValueImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

Equipment _$EquipmentFromJson(Map<String, dynamic> json) {
  return _Equipment.fromJson(json);
}

/// @nodoc
mixin _$Equipment {
  String get id => throw _privateConstructorUsedError;
  String get name => throw _privateConstructorUsedError;
  EquipmentType get type => throw _privateConstructorUsedError;
  Rarity get rarity => throw _privateConstructorUsedError;
  List<AttributeValue> get attributes => throw _privateConstructorUsedError;
  String? get description => throw _privateConstructorUsedError;
  String? get spritePath => throw _privateConstructorUsedError; // 像素图路径
  bool? get isUnlocked => throw _privateConstructorUsedError;
  DateTime? get unlockedAt => throw _privateConstructorUsedError;
  String? get unlockCondition => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $EquipmentCopyWith<Equipment> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $EquipmentCopyWith<$Res> {
  factory $EquipmentCopyWith(Equipment value, $Res Function(Equipment) then) =
      _$EquipmentCopyWithImpl<$Res, Equipment>;
  @useResult
  $Res call(
      {String id,
      String name,
      EquipmentType type,
      Rarity rarity,
      List<AttributeValue> attributes,
      String? description,
      String? spritePath,
      bool? isUnlocked,
      DateTime? unlockedAt,
      String? unlockCondition});
}

/// @nodoc
class _$EquipmentCopyWithImpl<$Res, $Val extends Equipment>
    implements $EquipmentCopyWith<$Res> {
  _$EquipmentCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? name = null,
    Object? type = null,
    Object? rarity = null,
    Object? attributes = null,
    Object? description = freezed,
    Object? spritePath = freezed,
    Object? isUnlocked = freezed,
    Object? unlockedAt = freezed,
    Object? unlockCondition = freezed,
  }) {
    return _then(_value.copyWith(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      name: null == name
          ? _value.name
          : name // ignore: cast_nullable_to_non_nullable
              as String,
      type: null == type
          ? _value.type
          : type // ignore: cast_nullable_to_non_nullable
              as EquipmentType,
      rarity: null == rarity
          ? _value.rarity
          : rarity // ignore: cast_nullable_to_non_nullable
              as Rarity,
      attributes: null == attributes
          ? _value.attributes
          : attributes // ignore: cast_nullable_to_non_nullable
              as List<AttributeValue>,
      description: freezed == description
          ? _value.description
          : description // ignore: cast_nullable_to_non_nullable
              as String?,
      spritePath: freezed == spritePath
          ? _value.spritePath
          : spritePath // ignore: cast_nullable_to_non_nullable
              as String?,
      isUnlocked: freezed == isUnlocked
          ? _value.isUnlocked
          : isUnlocked // ignore: cast_nullable_to_non_nullable
              as bool?,
      unlockedAt: freezed == unlockedAt
          ? _value.unlockedAt
          : unlockedAt // ignore: cast_nullable_to_non_nullable
              as DateTime?,
      unlockCondition: freezed == unlockCondition
          ? _value.unlockCondition
          : unlockCondition // ignore: cast_nullable_to_non_nullable
              as String?,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$EquipmentImplCopyWith<$Res>
    implements $EquipmentCopyWith<$Res> {
  factory _$$EquipmentImplCopyWith(
          _$EquipmentImpl value, $Res Function(_$EquipmentImpl) then) =
      __$$EquipmentImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {String id,
      String name,
      EquipmentType type,
      Rarity rarity,
      List<AttributeValue> attributes,
      String? description,
      String? spritePath,
      bool? isUnlocked,
      DateTime? unlockedAt,
      String? unlockCondition});
}

/// @nodoc
class __$$EquipmentImplCopyWithImpl<$Res>
    extends _$EquipmentCopyWithImpl<$Res, _$EquipmentImpl>
    implements _$$EquipmentImplCopyWith<$Res> {
  __$$EquipmentImplCopyWithImpl(
      _$EquipmentImpl _value, $Res Function(_$EquipmentImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? name = null,
    Object? type = null,
    Object? rarity = null,
    Object? attributes = null,
    Object? description = freezed,
    Object? spritePath = freezed,
    Object? isUnlocked = freezed,
    Object? unlockedAt = freezed,
    Object? unlockCondition = freezed,
  }) {
    return _then(_$EquipmentImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      name: null == name
          ? _value.name
          : name // ignore: cast_nullable_to_non_nullable
              as String,
      type: null == type
          ? _value.type
          : type // ignore: cast_nullable_to_non_nullable
              as EquipmentType,
      rarity: null == rarity
          ? _value.rarity
          : rarity // ignore: cast_nullable_to_non_nullable
              as Rarity,
      attributes: null == attributes
          ? _value._attributes
          : attributes // ignore: cast_nullable_to_non_nullable
              as List<AttributeValue>,
      description: freezed == description
          ? _value.description
          : description // ignore: cast_nullable_to_non_nullable
              as String?,
      spritePath: freezed == spritePath
          ? _value.spritePath
          : spritePath // ignore: cast_nullable_to_non_nullable
              as String?,
      isUnlocked: freezed == isUnlocked
          ? _value.isUnlocked
          : isUnlocked // ignore: cast_nullable_to_non_nullable
              as bool?,
      unlockedAt: freezed == unlockedAt
          ? _value.unlockedAt
          : unlockedAt // ignore: cast_nullable_to_non_nullable
              as DateTime?,
      unlockCondition: freezed == unlockCondition
          ? _value.unlockCondition
          : unlockCondition // ignore: cast_nullable_to_non_nullable
              as String?,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$EquipmentImpl implements _Equipment {
  const _$EquipmentImpl(
      {required this.id,
      required this.name,
      required this.type,
      required this.rarity,
      required final List<AttributeValue> attributes,
      this.description,
      this.spritePath,
      this.isUnlocked,
      this.unlockedAt,
      this.unlockCondition})
      : _attributes = attributes;

  factory _$EquipmentImpl.fromJson(Map<String, dynamic> json) =>
      _$$EquipmentImplFromJson(json);

  @override
  final String id;
  @override
  final String name;
  @override
  final EquipmentType type;
  @override
  final Rarity rarity;
  final List<AttributeValue> _attributes;
  @override
  List<AttributeValue> get attributes {
    if (_attributes is EqualUnmodifiableListView) return _attributes;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_attributes);
  }

  @override
  final String? description;
  @override
  final String? spritePath;
// 像素图路径
  @override
  final bool? isUnlocked;
  @override
  final DateTime? unlockedAt;
  @override
  final String? unlockCondition;

  @override
  String toString() {
    return 'Equipment(id: $id, name: $name, type: $type, rarity: $rarity, attributes: $attributes, description: $description, spritePath: $spritePath, isUnlocked: $isUnlocked, unlockedAt: $unlockedAt, unlockCondition: $unlockCondition)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$EquipmentImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.name, name) || other.name == name) &&
            (identical(other.type, type) || other.type == type) &&
            (identical(other.rarity, rarity) || other.rarity == rarity) &&
            const DeepCollectionEquality()
                .equals(other._attributes, _attributes) &&
            (identical(other.description, description) ||
                other.description == description) &&
            (identical(other.spritePath, spritePath) ||
                other.spritePath == spritePath) &&
            (identical(other.isUnlocked, isUnlocked) ||
                other.isUnlocked == isUnlocked) &&
            (identical(other.unlockedAt, unlockedAt) ||
                other.unlockedAt == unlockedAt) &&
            (identical(other.unlockCondition, unlockCondition) ||
                other.unlockCondition == unlockCondition));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode => Object.hash(
      runtimeType,
      id,
      name,
      type,
      rarity,
      const DeepCollectionEquality().hash(_attributes),
      description,
      spritePath,
      isUnlocked,
      unlockedAt,
      unlockCondition);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$EquipmentImplCopyWith<_$EquipmentImpl> get copyWith =>
      __$$EquipmentImplCopyWithImpl<_$EquipmentImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$EquipmentImplToJson(
      this,
    );
  }
}

abstract class _Equipment implements Equipment {
  const factory _Equipment(
      {required final String id,
      required final String name,
      required final EquipmentType type,
      required final Rarity rarity,
      required final List<AttributeValue> attributes,
      final String? description,
      final String? spritePath,
      final bool? isUnlocked,
      final DateTime? unlockedAt,
      final String? unlockCondition}) = _$EquipmentImpl;

  factory _Equipment.fromJson(Map<String, dynamic> json) =
      _$EquipmentImpl.fromJson;

  @override
  String get id;
  @override
  String get name;
  @override
  EquipmentType get type;
  @override
  Rarity get rarity;
  @override
  List<AttributeValue> get attributes;
  @override
  String? get description;
  @override
  String? get spritePath;
  @override // 像素图路径
  bool? get isUnlocked;
  @override
  DateTime? get unlockedAt;
  @override
  String? get unlockCondition;
  @override
  @JsonKey(ignore: true)
  _$$EquipmentImplCopyWith<_$EquipmentImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

CharacterEquipment _$CharacterEquipmentFromJson(Map<String, dynamic> json) {
  return _CharacterEquipment.fromJson(json);
}

/// @nodoc
mixin _$CharacterEquipment {
  String? get hat => throw _privateConstructorUsedError;
  String? get shirt => throw _privateConstructorUsedError;
  String? get pants => throw _privateConstructorUsedError;
  String? get shoes => throw _privateConstructorUsedError;
  String? get weapon => throw _privateConstructorUsedError;
  String? get accessory => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $CharacterEquipmentCopyWith<CharacterEquipment> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $CharacterEquipmentCopyWith<$Res> {
  factory $CharacterEquipmentCopyWith(
          CharacterEquipment value, $Res Function(CharacterEquipment) then) =
      _$CharacterEquipmentCopyWithImpl<$Res, CharacterEquipment>;
  @useResult
  $Res call(
      {String? hat,
      String? shirt,
      String? pants,
      String? shoes,
      String? weapon,
      String? accessory});
}

/// @nodoc
class _$CharacterEquipmentCopyWithImpl<$Res, $Val extends CharacterEquipment>
    implements $CharacterEquipmentCopyWith<$Res> {
  _$CharacterEquipmentCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? hat = freezed,
    Object? shirt = freezed,
    Object? pants = freezed,
    Object? shoes = freezed,
    Object? weapon = freezed,
    Object? accessory = freezed,
  }) {
    return _then(_value.copyWith(
      hat: freezed == hat
          ? _value.hat
          : hat // ignore: cast_nullable_to_non_nullable
              as String?,
      shirt: freezed == shirt
          ? _value.shirt
          : shirt // ignore: cast_nullable_to_non_nullable
              as String?,
      pants: freezed == pants
          ? _value.pants
          : pants // ignore: cast_nullable_to_non_nullable
              as String?,
      shoes: freezed == shoes
          ? _value.shoes
          : shoes // ignore: cast_nullable_to_non_nullable
              as String?,
      weapon: freezed == weapon
          ? _value.weapon
          : weapon // ignore: cast_nullable_to_non_nullable
              as String?,
      accessory: freezed == accessory
          ? _value.accessory
          : accessory // ignore: cast_nullable_to_non_nullable
              as String?,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$CharacterEquipmentImplCopyWith<$Res>
    implements $CharacterEquipmentCopyWith<$Res> {
  factory _$$CharacterEquipmentImplCopyWith(_$CharacterEquipmentImpl value,
          $Res Function(_$CharacterEquipmentImpl) then) =
      __$$CharacterEquipmentImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {String? hat,
      String? shirt,
      String? pants,
      String? shoes,
      String? weapon,
      String? accessory});
}

/// @nodoc
class __$$CharacterEquipmentImplCopyWithImpl<$Res>
    extends _$CharacterEquipmentCopyWithImpl<$Res, _$CharacterEquipmentImpl>
    implements _$$CharacterEquipmentImplCopyWith<$Res> {
  __$$CharacterEquipmentImplCopyWithImpl(_$CharacterEquipmentImpl _value,
      $Res Function(_$CharacterEquipmentImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? hat = freezed,
    Object? shirt = freezed,
    Object? pants = freezed,
    Object? shoes = freezed,
    Object? weapon = freezed,
    Object? accessory = freezed,
  }) {
    return _then(_$CharacterEquipmentImpl(
      hat: freezed == hat
          ? _value.hat
          : hat // ignore: cast_nullable_to_non_nullable
              as String?,
      shirt: freezed == shirt
          ? _value.shirt
          : shirt // ignore: cast_nullable_to_non_nullable
              as String?,
      pants: freezed == pants
          ? _value.pants
          : pants // ignore: cast_nullable_to_non_nullable
              as String?,
      shoes: freezed == shoes
          ? _value.shoes
          : shoes // ignore: cast_nullable_to_non_nullable
              as String?,
      weapon: freezed == weapon
          ? _value.weapon
          : weapon // ignore: cast_nullable_to_non_nullable
              as String?,
      accessory: freezed == accessory
          ? _value.accessory
          : accessory // ignore: cast_nullable_to_non_nullable
              as String?,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$CharacterEquipmentImpl implements _CharacterEquipment {
  const _$CharacterEquipmentImpl(
      {this.hat,
      this.shirt,
      this.pants,
      this.shoes,
      this.weapon,
      this.accessory});

  factory _$CharacterEquipmentImpl.fromJson(Map<String, dynamic> json) =>
      _$$CharacterEquipmentImplFromJson(json);

  @override
  final String? hat;
  @override
  final String? shirt;
  @override
  final String? pants;
  @override
  final String? shoes;
  @override
  final String? weapon;
  @override
  final String? accessory;

  @override
  String toString() {
    return 'CharacterEquipment(hat: $hat, shirt: $shirt, pants: $pants, shoes: $shoes, weapon: $weapon, accessory: $accessory)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$CharacterEquipmentImpl &&
            (identical(other.hat, hat) || other.hat == hat) &&
            (identical(other.shirt, shirt) || other.shirt == shirt) &&
            (identical(other.pants, pants) || other.pants == pants) &&
            (identical(other.shoes, shoes) || other.shoes == shoes) &&
            (identical(other.weapon, weapon) || other.weapon == weapon) &&
            (identical(other.accessory, accessory) ||
                other.accessory == accessory));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode =>
      Object.hash(runtimeType, hat, shirt, pants, shoes, weapon, accessory);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$CharacterEquipmentImplCopyWith<_$CharacterEquipmentImpl> get copyWith =>
      __$$CharacterEquipmentImplCopyWithImpl<_$CharacterEquipmentImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$CharacterEquipmentImplToJson(
      this,
    );
  }
}

abstract class _CharacterEquipment implements CharacterEquipment {
  const factory _CharacterEquipment(
      {final String? hat,
      final String? shirt,
      final String? pants,
      final String? shoes,
      final String? weapon,
      final String? accessory}) = _$CharacterEquipmentImpl;

  factory _CharacterEquipment.fromJson(Map<String, dynamic> json) =
      _$CharacterEquipmentImpl.fromJson;

  @override
  String? get hat;
  @override
  String? get shirt;
  @override
  String? get pants;
  @override
  String? get shoes;
  @override
  String? get weapon;
  @override
  String? get accessory;
  @override
  @JsonKey(ignore: true)
  _$$CharacterEquipmentImplCopyWith<_$CharacterEquipmentImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

Character _$CharacterFromJson(Map<String, dynamic> json) {
  return _Character.fromJson(json);
}

/// @nodoc
mixin _$Character {
  String get id => throw _privateConstructorUsedError;
  String get userId => throw _privateConstructorUsedError;
  int get level => throw _privateConstructorUsedError;
  int get experience => throw _privateConstructorUsedError;
  List<AttributeValue> get baseAttributes => throw _privateConstructorUsedError;
  CharacterEquipment get equipment => throw _privateConstructorUsedError;
  List<String>? get unlockedEquipment => throw _privateConstructorUsedError;
  String? get currentSprite => throw _privateConstructorUsedError;
  String? get characterClass => throw _privateConstructorUsedError; // 角色职业
  int? get totalLoginDays => throw _privateConstructorUsedError;
  DateTime? get lastLogin => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $CharacterCopyWith<Character> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $CharacterCopyWith<$Res> {
  factory $CharacterCopyWith(Character value, $Res Function(Character) then) =
      _$CharacterCopyWithImpl<$Res, Character>;
  @useResult
  $Res call(
      {String id,
      String userId,
      int level,
      int experience,
      List<AttributeValue> baseAttributes,
      CharacterEquipment equipment,
      List<String>? unlockedEquipment,
      String? currentSprite,
      String? characterClass,
      int? totalLoginDays,
      DateTime? lastLogin});

  $CharacterEquipmentCopyWith<$Res> get equipment;
}

/// @nodoc
class _$CharacterCopyWithImpl<$Res, $Val extends Character>
    implements $CharacterCopyWith<$Res> {
  _$CharacterCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? userId = null,
    Object? level = null,
    Object? experience = null,
    Object? baseAttributes = null,
    Object? equipment = null,
    Object? unlockedEquipment = freezed,
    Object? currentSprite = freezed,
    Object? characterClass = freezed,
    Object? totalLoginDays = freezed,
    Object? lastLogin = freezed,
  }) {
    return _then(_value.copyWith(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      userId: null == userId
          ? _value.userId
          : userId // ignore: cast_nullable_to_non_nullable
              as String,
      level: null == level
          ? _value.level
          : level // ignore: cast_nullable_to_non_nullable
              as int,
      experience: null == experience
          ? _value.experience
          : experience // ignore: cast_nullable_to_non_nullable
              as int,
      baseAttributes: null == baseAttributes
          ? _value.baseAttributes
          : baseAttributes // ignore: cast_nullable_to_non_nullable
              as List<AttributeValue>,
      equipment: null == equipment
          ? _value.equipment
          : equipment // ignore: cast_nullable_to_non_nullable
              as CharacterEquipment,
      unlockedEquipment: freezed == unlockedEquipment
          ? _value.unlockedEquipment
          : unlockedEquipment // ignore: cast_nullable_to_non_nullable
              as List<String>?,
      currentSprite: freezed == currentSprite
          ? _value.currentSprite
          : currentSprite // ignore: cast_nullable_to_non_nullable
              as String?,
      characterClass: freezed == characterClass
          ? _value.characterClass
          : characterClass // ignore: cast_nullable_to_non_nullable
              as String?,
      totalLoginDays: freezed == totalLoginDays
          ? _value.totalLoginDays
          : totalLoginDays // ignore: cast_nullable_to_non_nullable
              as int?,
      lastLogin: freezed == lastLogin
          ? _value.lastLogin
          : lastLogin // ignore: cast_nullable_to_non_nullable
              as DateTime?,
    ) as $Val);
  }

  @override
  @pragma('vm:prefer-inline')
  $CharacterEquipmentCopyWith<$Res> get equipment {
    return $CharacterEquipmentCopyWith<$Res>(_value.equipment, (value) {
      return _then(_value.copyWith(equipment: value) as $Val);
    });
  }
}

/// @nodoc
abstract class _$$CharacterImplCopyWith<$Res>
    implements $CharacterCopyWith<$Res> {
  factory _$$CharacterImplCopyWith(
          _$CharacterImpl value, $Res Function(_$CharacterImpl) then) =
      __$$CharacterImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {String id,
      String userId,
      int level,
      int experience,
      List<AttributeValue> baseAttributes,
      CharacterEquipment equipment,
      List<String>? unlockedEquipment,
      String? currentSprite,
      String? characterClass,
      int? totalLoginDays,
      DateTime? lastLogin});

  @override
  $CharacterEquipmentCopyWith<$Res> get equipment;
}

/// @nodoc
class __$$CharacterImplCopyWithImpl<$Res>
    extends _$CharacterCopyWithImpl<$Res, _$CharacterImpl>
    implements _$$CharacterImplCopyWith<$Res> {
  __$$CharacterImplCopyWithImpl(
      _$CharacterImpl _value, $Res Function(_$CharacterImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? userId = null,
    Object? level = null,
    Object? experience = null,
    Object? baseAttributes = null,
    Object? equipment = null,
    Object? unlockedEquipment = freezed,
    Object? currentSprite = freezed,
    Object? characterClass = freezed,
    Object? totalLoginDays = freezed,
    Object? lastLogin = freezed,
  }) {
    return _then(_$CharacterImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      userId: null == userId
          ? _value.userId
          : userId // ignore: cast_nullable_to_non_nullable
              as String,
      level: null == level
          ? _value.level
          : level // ignore: cast_nullable_to_non_nullable
              as int,
      experience: null == experience
          ? _value.experience
          : experience // ignore: cast_nullable_to_non_nullable
              as int,
      baseAttributes: null == baseAttributes
          ? _value._baseAttributes
          : baseAttributes // ignore: cast_nullable_to_non_nullable
              as List<AttributeValue>,
      equipment: null == equipment
          ? _value.equipment
          : equipment // ignore: cast_nullable_to_non_nullable
              as CharacterEquipment,
      unlockedEquipment: freezed == unlockedEquipment
          ? _value._unlockedEquipment
          : unlockedEquipment // ignore: cast_nullable_to_non_nullable
              as List<String>?,
      currentSprite: freezed == currentSprite
          ? _value.currentSprite
          : currentSprite // ignore: cast_nullable_to_non_nullable
              as String?,
      characterClass: freezed == characterClass
          ? _value.characterClass
          : characterClass // ignore: cast_nullable_to_non_nullable
              as String?,
      totalLoginDays: freezed == totalLoginDays
          ? _value.totalLoginDays
          : totalLoginDays // ignore: cast_nullable_to_non_nullable
              as int?,
      lastLogin: freezed == lastLogin
          ? _value.lastLogin
          : lastLogin // ignore: cast_nullable_to_non_nullable
              as DateTime?,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$CharacterImpl implements _Character {
  const _$CharacterImpl(
      {required this.id,
      required this.userId,
      required this.level,
      required this.experience,
      required final List<AttributeValue> baseAttributes,
      required this.equipment,
      final List<String>? unlockedEquipment,
      this.currentSprite,
      this.characterClass,
      this.totalLoginDays,
      this.lastLogin})
      : _baseAttributes = baseAttributes,
        _unlockedEquipment = unlockedEquipment;

  factory _$CharacterImpl.fromJson(Map<String, dynamic> json) =>
      _$$CharacterImplFromJson(json);

  @override
  final String id;
  @override
  final String userId;
  @override
  final int level;
  @override
  final int experience;
  final List<AttributeValue> _baseAttributes;
  @override
  List<AttributeValue> get baseAttributes {
    if (_baseAttributes is EqualUnmodifiableListView) return _baseAttributes;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_baseAttributes);
  }

  @override
  final CharacterEquipment equipment;
  final List<String>? _unlockedEquipment;
  @override
  List<String>? get unlockedEquipment {
    final value = _unlockedEquipment;
    if (value == null) return null;
    if (_unlockedEquipment is EqualUnmodifiableListView)
      return _unlockedEquipment;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(value);
  }

  @override
  final String? currentSprite;
  @override
  final String? characterClass;
// 角色职业
  @override
  final int? totalLoginDays;
  @override
  final DateTime? lastLogin;

  @override
  String toString() {
    return 'Character(id: $id, userId: $userId, level: $level, experience: $experience, baseAttributes: $baseAttributes, equipment: $equipment, unlockedEquipment: $unlockedEquipment, currentSprite: $currentSprite, characterClass: $characterClass, totalLoginDays: $totalLoginDays, lastLogin: $lastLogin)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$CharacterImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.userId, userId) || other.userId == userId) &&
            (identical(other.level, level) || other.level == level) &&
            (identical(other.experience, experience) ||
                other.experience == experience) &&
            const DeepCollectionEquality()
                .equals(other._baseAttributes, _baseAttributes) &&
            (identical(other.equipment, equipment) ||
                other.equipment == equipment) &&
            const DeepCollectionEquality()
                .equals(other._unlockedEquipment, _unlockedEquipment) &&
            (identical(other.currentSprite, currentSprite) ||
                other.currentSprite == currentSprite) &&
            (identical(other.characterClass, characterClass) ||
                other.characterClass == characterClass) &&
            (identical(other.totalLoginDays, totalLoginDays) ||
                other.totalLoginDays == totalLoginDays) &&
            (identical(other.lastLogin, lastLogin) ||
                other.lastLogin == lastLogin));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode => Object.hash(
      runtimeType,
      id,
      userId,
      level,
      experience,
      const DeepCollectionEquality().hash(_baseAttributes),
      equipment,
      const DeepCollectionEquality().hash(_unlockedEquipment),
      currentSprite,
      characterClass,
      totalLoginDays,
      lastLogin);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$CharacterImplCopyWith<_$CharacterImpl> get copyWith =>
      __$$CharacterImplCopyWithImpl<_$CharacterImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$CharacterImplToJson(
      this,
    );
  }
}

abstract class _Character implements Character {
  const factory _Character(
      {required final String id,
      required final String userId,
      required final int level,
      required final int experience,
      required final List<AttributeValue> baseAttributes,
      required final CharacterEquipment equipment,
      final List<String>? unlockedEquipment,
      final String? currentSprite,
      final String? characterClass,
      final int? totalLoginDays,
      final DateTime? lastLogin}) = _$CharacterImpl;

  factory _Character.fromJson(Map<String, dynamic> json) =
      _$CharacterImpl.fromJson;

  @override
  String get id;
  @override
  String get userId;
  @override
  int get level;
  @override
  int get experience;
  @override
  List<AttributeValue> get baseAttributes;
  @override
  CharacterEquipment get equipment;
  @override
  List<String>? get unlockedEquipment;
  @override
  String? get currentSprite;
  @override
  String? get characterClass;
  @override // 角色职业
  int? get totalLoginDays;
  @override
  DateTime? get lastLogin;
  @override
  @JsonKey(ignore: true)
  _$$CharacterImplCopyWith<_$CharacterImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

RpgState _$RpgStateFromJson(Map<String, dynamic> json) {
  return _RpgState.fromJson(json);
}

/// @nodoc
mixin _$RpgState {
  Character? get character => throw _privateConstructorUsedError;
  List<Equipment>? get allEquipment => throw _privateConstructorUsedError;
  List<Equipment>? get unlockedEquipment => throw _privateConstructorUsedError;
  bool? get isLoading => throw _privateConstructorUsedError;
  String? get error => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $RpgStateCopyWith<RpgState> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $RpgStateCopyWith<$Res> {
  factory $RpgStateCopyWith(RpgState value, $Res Function(RpgState) then) =
      _$RpgStateCopyWithImpl<$Res, RpgState>;
  @useResult
  $Res call(
      {Character? character,
      List<Equipment>? allEquipment,
      List<Equipment>? unlockedEquipment,
      bool? isLoading,
      String? error});

  $CharacterCopyWith<$Res>? get character;
}

/// @nodoc
class _$RpgStateCopyWithImpl<$Res, $Val extends RpgState>
    implements $RpgStateCopyWith<$Res> {
  _$RpgStateCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? character = freezed,
    Object? allEquipment = freezed,
    Object? unlockedEquipment = freezed,
    Object? isLoading = freezed,
    Object? error = freezed,
  }) {
    return _then(_value.copyWith(
      character: freezed == character
          ? _value.character
          : character // ignore: cast_nullable_to_non_nullable
              as Character?,
      allEquipment: freezed == allEquipment
          ? _value.allEquipment
          : allEquipment // ignore: cast_nullable_to_non_nullable
              as List<Equipment>?,
      unlockedEquipment: freezed == unlockedEquipment
          ? _value.unlockedEquipment
          : unlockedEquipment // ignore: cast_nullable_to_non_nullable
              as List<Equipment>?,
      isLoading: freezed == isLoading
          ? _value.isLoading
          : isLoading // ignore: cast_nullable_to_non_nullable
              as bool?,
      error: freezed == error
          ? _value.error
          : error // ignore: cast_nullable_to_non_nullable
              as String?,
    ) as $Val);
  }

  @override
  @pragma('vm:prefer-inline')
  $CharacterCopyWith<$Res>? get character {
    if (_value.character == null) {
      return null;
    }

    return $CharacterCopyWith<$Res>(_value.character!, (value) {
      return _then(_value.copyWith(character: value) as $Val);
    });
  }
}

/// @nodoc
abstract class _$$RpgStateImplCopyWith<$Res>
    implements $RpgStateCopyWith<$Res> {
  factory _$$RpgStateImplCopyWith(
          _$RpgStateImpl value, $Res Function(_$RpgStateImpl) then) =
      __$$RpgStateImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {Character? character,
      List<Equipment>? allEquipment,
      List<Equipment>? unlockedEquipment,
      bool? isLoading,
      String? error});

  @override
  $CharacterCopyWith<$Res>? get character;
}

/// @nodoc
class __$$RpgStateImplCopyWithImpl<$Res>
    extends _$RpgStateCopyWithImpl<$Res, _$RpgStateImpl>
    implements _$$RpgStateImplCopyWith<$Res> {
  __$$RpgStateImplCopyWithImpl(
      _$RpgStateImpl _value, $Res Function(_$RpgStateImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? character = freezed,
    Object? allEquipment = freezed,
    Object? unlockedEquipment = freezed,
    Object? isLoading = freezed,
    Object? error = freezed,
  }) {
    return _then(_$RpgStateImpl(
      character: freezed == character
          ? _value.character
          : character // ignore: cast_nullable_to_non_nullable
              as Character?,
      allEquipment: freezed == allEquipment
          ? _value._allEquipment
          : allEquipment // ignore: cast_nullable_to_non_nullable
              as List<Equipment>?,
      unlockedEquipment: freezed == unlockedEquipment
          ? _value._unlockedEquipment
          : unlockedEquipment // ignore: cast_nullable_to_non_nullable
              as List<Equipment>?,
      isLoading: freezed == isLoading
          ? _value.isLoading
          : isLoading // ignore: cast_nullable_to_non_nullable
              as bool?,
      error: freezed == error
          ? _value.error
          : error // ignore: cast_nullable_to_non_nullable
              as String?,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$RpgStateImpl implements _RpgState {
  const _$RpgStateImpl(
      {this.character,
      final List<Equipment>? allEquipment,
      final List<Equipment>? unlockedEquipment,
      this.isLoading,
      this.error})
      : _allEquipment = allEquipment,
        _unlockedEquipment = unlockedEquipment;

  factory _$RpgStateImpl.fromJson(Map<String, dynamic> json) =>
      _$$RpgStateImplFromJson(json);

  @override
  final Character? character;
  final List<Equipment>? _allEquipment;
  @override
  List<Equipment>? get allEquipment {
    final value = _allEquipment;
    if (value == null) return null;
    if (_allEquipment is EqualUnmodifiableListView) return _allEquipment;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(value);
  }

  final List<Equipment>? _unlockedEquipment;
  @override
  List<Equipment>? get unlockedEquipment {
    final value = _unlockedEquipment;
    if (value == null) return null;
    if (_unlockedEquipment is EqualUnmodifiableListView)
      return _unlockedEquipment;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(value);
  }

  @override
  final bool? isLoading;
  @override
  final String? error;

  @override
  String toString() {
    return 'RpgState(character: $character, allEquipment: $allEquipment, unlockedEquipment: $unlockedEquipment, isLoading: $isLoading, error: $error)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$RpgStateImpl &&
            (identical(other.character, character) ||
                other.character == character) &&
            const DeepCollectionEquality()
                .equals(other._allEquipment, _allEquipment) &&
            const DeepCollectionEquality()
                .equals(other._unlockedEquipment, _unlockedEquipment) &&
            (identical(other.isLoading, isLoading) ||
                other.isLoading == isLoading) &&
            (identical(other.error, error) || other.error == error));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode => Object.hash(
      runtimeType,
      character,
      const DeepCollectionEquality().hash(_allEquipment),
      const DeepCollectionEquality().hash(_unlockedEquipment),
      isLoading,
      error);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$RpgStateImplCopyWith<_$RpgStateImpl> get copyWith =>
      __$$RpgStateImplCopyWithImpl<_$RpgStateImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$RpgStateImplToJson(
      this,
    );
  }
}

abstract class _RpgState implements RpgState {
  const factory _RpgState(
      {final Character? character,
      final List<Equipment>? allEquipment,
      final List<Equipment>? unlockedEquipment,
      final bool? isLoading,
      final String? error}) = _$RpgStateImpl;

  factory _RpgState.fromJson(Map<String, dynamic> json) =
      _$RpgStateImpl.fromJson;

  @override
  Character? get character;
  @override
  List<Equipment>? get allEquipment;
  @override
  List<Equipment>? get unlockedEquipment;
  @override
  bool? get isLoading;
  @override
  String? get error;
  @override
  @JsonKey(ignore: true)
  _$$RpgStateImplCopyWith<_$RpgStateImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
