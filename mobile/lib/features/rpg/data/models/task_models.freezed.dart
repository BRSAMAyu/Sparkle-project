// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'task_models.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

TaskReward _$TaskRewardFromJson(Map<String, dynamic> json) {
  return _TaskReward.fromJson(json);
}

/// @nodoc
mixin _$TaskReward {
  RewardType get type => throw _privateConstructorUsedError;
  int get value => throw _privateConstructorUsedError;
  String? get equipmentId => throw _privateConstructorUsedError;
  CharacterAttribute? get attributeType => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $TaskRewardCopyWith<TaskReward> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $TaskRewardCopyWith<$Res> {
  factory $TaskRewardCopyWith(
          TaskReward value, $Res Function(TaskReward) then) =
      _$TaskRewardCopyWithImpl<$Res, TaskReward>;
  @useResult
  $Res call(
      {RewardType type,
      int value,
      String? equipmentId,
      CharacterAttribute? attributeType});
}

/// @nodoc
class _$TaskRewardCopyWithImpl<$Res, $Val extends TaskReward>
    implements $TaskRewardCopyWith<$Res> {
  _$TaskRewardCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? type = null,
    Object? value = null,
    Object? equipmentId = freezed,
    Object? attributeType = freezed,
  }) {
    return _then(_value.copyWith(
      type: null == type
          ? _value.type
          : type // ignore: cast_nullable_to_non_nullable
              as RewardType,
      value: null == value
          ? _value.value
          : value // ignore: cast_nullable_to_non_nullable
              as int,
      equipmentId: freezed == equipmentId
          ? _value.equipmentId
          : equipmentId // ignore: cast_nullable_to_non_nullable
              as String?,
      attributeType: freezed == attributeType
          ? _value.attributeType
          : attributeType // ignore: cast_nullable_to_non_nullable
              as CharacterAttribute?,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$TaskRewardImplCopyWith<$Res>
    implements $TaskRewardCopyWith<$Res> {
  factory _$$TaskRewardImplCopyWith(
          _$TaskRewardImpl value, $Res Function(_$TaskRewardImpl) then) =
      __$$TaskRewardImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {RewardType type,
      int value,
      String? equipmentId,
      CharacterAttribute? attributeType});
}

/// @nodoc
class __$$TaskRewardImplCopyWithImpl<$Res>
    extends _$TaskRewardCopyWithImpl<$Res, _$TaskRewardImpl>
    implements _$$TaskRewardImplCopyWith<$Res> {
  __$$TaskRewardImplCopyWithImpl(
      _$TaskRewardImpl _value, $Res Function(_$TaskRewardImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? type = null,
    Object? value = null,
    Object? equipmentId = freezed,
    Object? attributeType = freezed,
  }) {
    return _then(_$TaskRewardImpl(
      type: null == type
          ? _value.type
          : type // ignore: cast_nullable_to_non_nullable
              as RewardType,
      value: null == value
          ? _value.value
          : value // ignore: cast_nullable_to_non_nullable
              as int,
      equipmentId: freezed == equipmentId
          ? _value.equipmentId
          : equipmentId // ignore: cast_nullable_to_non_nullable
              as String?,
      attributeType: freezed == attributeType
          ? _value.attributeType
          : attributeType // ignore: cast_nullable_to_non_nullable
              as CharacterAttribute?,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$TaskRewardImpl implements _TaskReward {
  const _$TaskRewardImpl(
      {required this.type,
      required this.value,
      this.equipmentId,
      this.attributeType});

  factory _$TaskRewardImpl.fromJson(Map<String, dynamic> json) =>
      _$$TaskRewardImplFromJson(json);

  @override
  final RewardType type;
  @override
  final int value;
  @override
  final String? equipmentId;
  @override
  final CharacterAttribute? attributeType;

  @override
  String toString() {
    return 'TaskReward(type: $type, value: $value, equipmentId: $equipmentId, attributeType: $attributeType)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$TaskRewardImpl &&
            (identical(other.type, type) || other.type == type) &&
            (identical(other.value, value) || other.value == value) &&
            (identical(other.equipmentId, equipmentId) ||
                other.equipmentId == equipmentId) &&
            (identical(other.attributeType, attributeType) ||
                other.attributeType == attributeType));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode =>
      Object.hash(runtimeType, type, value, equipmentId, attributeType);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$TaskRewardImplCopyWith<_$TaskRewardImpl> get copyWith =>
      __$$TaskRewardImplCopyWithImpl<_$TaskRewardImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$TaskRewardImplToJson(
      this,
    );
  }
}

abstract class _TaskReward implements TaskReward {
  const factory _TaskReward(
      {required final RewardType type,
      required final int value,
      final String? equipmentId,
      final CharacterAttribute? attributeType}) = _$TaskRewardImpl;

  factory _TaskReward.fromJson(Map<String, dynamic> json) =
      _$TaskRewardImpl.fromJson;

  @override
  RewardType get type;
  @override
  int get value;
  @override
  String? get equipmentId;
  @override
  CharacterAttribute? get attributeType;
  @override
  @JsonKey(ignore: true)
  _$$TaskRewardImplCopyWith<_$TaskRewardImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

Task _$TaskFromJson(Map<String, dynamic> json) {
  return _Task.fromJson(json);
}

/// @nodoc
mixin _$Task {
  String get id => throw _privateConstructorUsedError;
  String get title => throw _privateConstructorUsedError;
  String get description => throw _privateConstructorUsedError;
  TaskType get type => throw _privateConstructorUsedError;
  TaskStatus get status => throw _privateConstructorUsedError;
  List<TaskReward> get rewards => throw _privateConstructorUsedError;
  int get progress => throw _privateConstructorUsedError;
  int get target => throw _privateConstructorUsedError;
  String? get icon => throw _privateConstructorUsedError;
  DateTime? get createdAt => throw _privateConstructorUsedError;
  DateTime? get completedAt => throw _privateConstructorUsedError;
  DateTime? get claimedAt => throw _privateConstructorUsedError;
  int? get loginStreakRequirement => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $TaskCopyWith<Task> get copyWith => throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $TaskCopyWith<$Res> {
  factory $TaskCopyWith(Task value, $Res Function(Task) then) =
      _$TaskCopyWithImpl<$Res, Task>;
  @useResult
  $Res call(
      {String id,
      String title,
      String description,
      TaskType type,
      TaskStatus status,
      List<TaskReward> rewards,
      int progress,
      int target,
      String? icon,
      DateTime? createdAt,
      DateTime? completedAt,
      DateTime? claimedAt,
      int? loginStreakRequirement});
}

/// @nodoc
class _$TaskCopyWithImpl<$Res, $Val extends Task>
    implements $TaskCopyWith<$Res> {
  _$TaskCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? title = null,
    Object? description = null,
    Object? type = null,
    Object? status = null,
    Object? rewards = null,
    Object? progress = null,
    Object? target = null,
    Object? icon = freezed,
    Object? createdAt = freezed,
    Object? completedAt = freezed,
    Object? claimedAt = freezed,
    Object? loginStreakRequirement = freezed,
  }) {
    return _then(_value.copyWith(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      title: null == title
          ? _value.title
          : title // ignore: cast_nullable_to_non_nullable
              as String,
      description: null == description
          ? _value.description
          : description // ignore: cast_nullable_to_non_nullable
              as String,
      type: null == type
          ? _value.type
          : type // ignore: cast_nullable_to_non_nullable
              as TaskType,
      status: null == status
          ? _value.status
          : status // ignore: cast_nullable_to_non_nullable
              as TaskStatus,
      rewards: null == rewards
          ? _value.rewards
          : rewards // ignore: cast_nullable_to_non_nullable
              as List<TaskReward>,
      progress: null == progress
          ? _value.progress
          : progress // ignore: cast_nullable_to_non_nullable
              as int,
      target: null == target
          ? _value.target
          : target // ignore: cast_nullable_to_non_nullable
              as int,
      icon: freezed == icon
          ? _value.icon
          : icon // ignore: cast_nullable_to_non_nullable
              as String?,
      createdAt: freezed == createdAt
          ? _value.createdAt
          : createdAt // ignore: cast_nullable_to_non_nullable
              as DateTime?,
      completedAt: freezed == completedAt
          ? _value.completedAt
          : completedAt // ignore: cast_nullable_to_non_nullable
              as DateTime?,
      claimedAt: freezed == claimedAt
          ? _value.claimedAt
          : claimedAt // ignore: cast_nullable_to_non_nullable
              as DateTime?,
      loginStreakRequirement: freezed == loginStreakRequirement
          ? _value.loginStreakRequirement
          : loginStreakRequirement // ignore: cast_nullable_to_non_nullable
              as int?,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$TaskImplCopyWith<$Res> implements $TaskCopyWith<$Res> {
  factory _$$TaskImplCopyWith(
          _$TaskImpl value, $Res Function(_$TaskImpl) then) =
      __$$TaskImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {String id,
      String title,
      String description,
      TaskType type,
      TaskStatus status,
      List<TaskReward> rewards,
      int progress,
      int target,
      String? icon,
      DateTime? createdAt,
      DateTime? completedAt,
      DateTime? claimedAt,
      int? loginStreakRequirement});
}

/// @nodoc
class __$$TaskImplCopyWithImpl<$Res>
    extends _$TaskCopyWithImpl<$Res, _$TaskImpl>
    implements _$$TaskImplCopyWith<$Res> {
  __$$TaskImplCopyWithImpl(_$TaskImpl _value, $Res Function(_$TaskImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? title = null,
    Object? description = null,
    Object? type = null,
    Object? status = null,
    Object? rewards = null,
    Object? progress = null,
    Object? target = null,
    Object? icon = freezed,
    Object? createdAt = freezed,
    Object? completedAt = freezed,
    Object? claimedAt = freezed,
    Object? loginStreakRequirement = freezed,
  }) {
    return _then(_$TaskImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      title: null == title
          ? _value.title
          : title // ignore: cast_nullable_to_non_nullable
              as String,
      description: null == description
          ? _value.description
          : description // ignore: cast_nullable_to_non_nullable
              as String,
      type: null == type
          ? _value.type
          : type // ignore: cast_nullable_to_non_nullable
              as TaskType,
      status: null == status
          ? _value.status
          : status // ignore: cast_nullable_to_non_nullable
              as TaskStatus,
      rewards: null == rewards
          ? _value._rewards
          : rewards // ignore: cast_nullable_to_non_nullable
              as List<TaskReward>,
      progress: null == progress
          ? _value.progress
          : progress // ignore: cast_nullable_to_non_nullable
              as int,
      target: null == target
          ? _value.target
          : target // ignore: cast_nullable_to_non_nullable
              as int,
      icon: freezed == icon
          ? _value.icon
          : icon // ignore: cast_nullable_to_non_nullable
              as String?,
      createdAt: freezed == createdAt
          ? _value.createdAt
          : createdAt // ignore: cast_nullable_to_non_nullable
              as DateTime?,
      completedAt: freezed == completedAt
          ? _value.completedAt
          : completedAt // ignore: cast_nullable_to_non_nullable
              as DateTime?,
      claimedAt: freezed == claimedAt
          ? _value.claimedAt
          : claimedAt // ignore: cast_nullable_to_non_nullable
              as DateTime?,
      loginStreakRequirement: freezed == loginStreakRequirement
          ? _value.loginStreakRequirement
          : loginStreakRequirement // ignore: cast_nullable_to_non_nullable
              as int?,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$TaskImpl implements _Task {
  const _$TaskImpl(
      {required this.id,
      required this.title,
      required this.description,
      required this.type,
      required this.status,
      required final List<TaskReward> rewards,
      required this.progress,
      required this.target,
      this.icon,
      this.createdAt,
      this.completedAt,
      this.claimedAt,
      this.loginStreakRequirement})
      : _rewards = rewards;

  factory _$TaskImpl.fromJson(Map<String, dynamic> json) =>
      _$$TaskImplFromJson(json);

  @override
  final String id;
  @override
  final String title;
  @override
  final String description;
  @override
  final TaskType type;
  @override
  final TaskStatus status;
  final List<TaskReward> _rewards;
  @override
  List<TaskReward> get rewards {
    if (_rewards is EqualUnmodifiableListView) return _rewards;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_rewards);
  }

  @override
  final int progress;
  @override
  final int target;
  @override
  final String? icon;
  @override
  final DateTime? createdAt;
  @override
  final DateTime? completedAt;
  @override
  final DateTime? claimedAt;
  @override
  final int? loginStreakRequirement;

  @override
  String toString() {
    return 'Task(id: $id, title: $title, description: $description, type: $type, status: $status, rewards: $rewards, progress: $progress, target: $target, icon: $icon, createdAt: $createdAt, completedAt: $completedAt, claimedAt: $claimedAt, loginStreakRequirement: $loginStreakRequirement)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$TaskImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.title, title) || other.title == title) &&
            (identical(other.description, description) ||
                other.description == description) &&
            (identical(other.type, type) || other.type == type) &&
            (identical(other.status, status) || other.status == status) &&
            const DeepCollectionEquality().equals(other._rewards, _rewards) &&
            (identical(other.progress, progress) ||
                other.progress == progress) &&
            (identical(other.target, target) || other.target == target) &&
            (identical(other.icon, icon) || other.icon == icon) &&
            (identical(other.createdAt, createdAt) ||
                other.createdAt == createdAt) &&
            (identical(other.completedAt, completedAt) ||
                other.completedAt == completedAt) &&
            (identical(other.claimedAt, claimedAt) ||
                other.claimedAt == claimedAt) &&
            (identical(other.loginStreakRequirement, loginStreakRequirement) ||
                other.loginStreakRequirement == loginStreakRequirement));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode => Object.hash(
      runtimeType,
      id,
      title,
      description,
      type,
      status,
      const DeepCollectionEquality().hash(_rewards),
      progress,
      target,
      icon,
      createdAt,
      completedAt,
      claimedAt,
      loginStreakRequirement);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$TaskImplCopyWith<_$TaskImpl> get copyWith =>
      __$$TaskImplCopyWithImpl<_$TaskImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$TaskImplToJson(
      this,
    );
  }
}

abstract class _Task implements Task {
  const factory _Task(
      {required final String id,
      required final String title,
      required final String description,
      required final TaskType type,
      required final TaskStatus status,
      required final List<TaskReward> rewards,
      required final int progress,
      required final int target,
      final String? icon,
      final DateTime? createdAt,
      final DateTime? completedAt,
      final DateTime? claimedAt,
      final int? loginStreakRequirement}) = _$TaskImpl;

  factory _Task.fromJson(Map<String, dynamic> json) = _$TaskImpl.fromJson;

  @override
  String get id;
  @override
  String get title;
  @override
  String get description;
  @override
  TaskType get type;
  @override
  TaskStatus get status;
  @override
  List<TaskReward> get rewards;
  @override
  int get progress;
  @override
  int get target;
  @override
  String? get icon;
  @override
  DateTime? get createdAt;
  @override
  DateTime? get completedAt;
  @override
  DateTime? get claimedAt;
  @override
  int? get loginStreakRequirement;
  @override
  @JsonKey(ignore: true)
  _$$TaskImplCopyWith<_$TaskImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

TaskSystemState _$TaskSystemStateFromJson(Map<String, dynamic> json) {
  return _TaskSystemState.fromJson(json);
}

/// @nodoc
mixin _$TaskSystemState {
  List<Task> get dailyTasks => throw _privateConstructorUsedError;
  List<Task> get achievementTasks => throw _privateConstructorUsedError;
  List<Task> get loginStreakTasks => throw _privateConstructorUsedError;
  List<Task> get activityTasks => throw _privateConstructorUsedError;
  bool? get isLoading => throw _privateConstructorUsedError;
  String? get error => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $TaskSystemStateCopyWith<TaskSystemState> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $TaskSystemStateCopyWith<$Res> {
  factory $TaskSystemStateCopyWith(
          TaskSystemState value, $Res Function(TaskSystemState) then) =
      _$TaskSystemStateCopyWithImpl<$Res, TaskSystemState>;
  @useResult
  $Res call(
      {List<Task> dailyTasks,
      List<Task> achievementTasks,
      List<Task> loginStreakTasks,
      List<Task> activityTasks,
      bool? isLoading,
      String? error});
}

/// @nodoc
class _$TaskSystemStateCopyWithImpl<$Res, $Val extends TaskSystemState>
    implements $TaskSystemStateCopyWith<$Res> {
  _$TaskSystemStateCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? dailyTasks = null,
    Object? achievementTasks = null,
    Object? loginStreakTasks = null,
    Object? activityTasks = null,
    Object? isLoading = freezed,
    Object? error = freezed,
  }) {
    return _then(_value.copyWith(
      dailyTasks: null == dailyTasks
          ? _value.dailyTasks
          : dailyTasks // ignore: cast_nullable_to_non_nullable
              as List<Task>,
      achievementTasks: null == achievementTasks
          ? _value.achievementTasks
          : achievementTasks // ignore: cast_nullable_to_non_nullable
              as List<Task>,
      loginStreakTasks: null == loginStreakTasks
          ? _value.loginStreakTasks
          : loginStreakTasks // ignore: cast_nullable_to_non_nullable
              as List<Task>,
      activityTasks: null == activityTasks
          ? _value.activityTasks
          : activityTasks // ignore: cast_nullable_to_non_nullable
              as List<Task>,
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
}

/// @nodoc
abstract class _$$TaskSystemStateImplCopyWith<$Res>
    implements $TaskSystemStateCopyWith<$Res> {
  factory _$$TaskSystemStateImplCopyWith(_$TaskSystemStateImpl value,
          $Res Function(_$TaskSystemStateImpl) then) =
      __$$TaskSystemStateImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {List<Task> dailyTasks,
      List<Task> achievementTasks,
      List<Task> loginStreakTasks,
      List<Task> activityTasks,
      bool? isLoading,
      String? error});
}

/// @nodoc
class __$$TaskSystemStateImplCopyWithImpl<$Res>
    extends _$TaskSystemStateCopyWithImpl<$Res, _$TaskSystemStateImpl>
    implements _$$TaskSystemStateImplCopyWith<$Res> {
  __$$TaskSystemStateImplCopyWithImpl(
      _$TaskSystemStateImpl _value, $Res Function(_$TaskSystemStateImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? dailyTasks = null,
    Object? achievementTasks = null,
    Object? loginStreakTasks = null,
    Object? activityTasks = null,
    Object? isLoading = freezed,
    Object? error = freezed,
  }) {
    return _then(_$TaskSystemStateImpl(
      dailyTasks: null == dailyTasks
          ? _value._dailyTasks
          : dailyTasks // ignore: cast_nullable_to_non_nullable
              as List<Task>,
      achievementTasks: null == achievementTasks
          ? _value._achievementTasks
          : achievementTasks // ignore: cast_nullable_to_non_nullable
              as List<Task>,
      loginStreakTasks: null == loginStreakTasks
          ? _value._loginStreakTasks
          : loginStreakTasks // ignore: cast_nullable_to_non_nullable
              as List<Task>,
      activityTasks: null == activityTasks
          ? _value._activityTasks
          : activityTasks // ignore: cast_nullable_to_non_nullable
              as List<Task>,
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
class _$TaskSystemStateImpl implements _TaskSystemState {
  const _$TaskSystemStateImpl(
      {required final List<Task> dailyTasks,
      required final List<Task> achievementTasks,
      required final List<Task> loginStreakTasks,
      required final List<Task> activityTasks,
      this.isLoading,
      this.error})
      : _dailyTasks = dailyTasks,
        _achievementTasks = achievementTasks,
        _loginStreakTasks = loginStreakTasks,
        _activityTasks = activityTasks;

  factory _$TaskSystemStateImpl.fromJson(Map<String, dynamic> json) =>
      _$$TaskSystemStateImplFromJson(json);

  final List<Task> _dailyTasks;
  @override
  List<Task> get dailyTasks {
    if (_dailyTasks is EqualUnmodifiableListView) return _dailyTasks;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_dailyTasks);
  }

  final List<Task> _achievementTasks;
  @override
  List<Task> get achievementTasks {
    if (_achievementTasks is EqualUnmodifiableListView)
      return _achievementTasks;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_achievementTasks);
  }

  final List<Task> _loginStreakTasks;
  @override
  List<Task> get loginStreakTasks {
    if (_loginStreakTasks is EqualUnmodifiableListView)
      return _loginStreakTasks;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_loginStreakTasks);
  }

  final List<Task> _activityTasks;
  @override
  List<Task> get activityTasks {
    if (_activityTasks is EqualUnmodifiableListView) return _activityTasks;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_activityTasks);
  }

  @override
  final bool? isLoading;
  @override
  final String? error;

  @override
  String toString() {
    return 'TaskSystemState(dailyTasks: $dailyTasks, achievementTasks: $achievementTasks, loginStreakTasks: $loginStreakTasks, activityTasks: $activityTasks, isLoading: $isLoading, error: $error)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$TaskSystemStateImpl &&
            const DeepCollectionEquality()
                .equals(other._dailyTasks, _dailyTasks) &&
            const DeepCollectionEquality()
                .equals(other._achievementTasks, _achievementTasks) &&
            const DeepCollectionEquality()
                .equals(other._loginStreakTasks, _loginStreakTasks) &&
            const DeepCollectionEquality()
                .equals(other._activityTasks, _activityTasks) &&
            (identical(other.isLoading, isLoading) ||
                other.isLoading == isLoading) &&
            (identical(other.error, error) || other.error == error));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode => Object.hash(
      runtimeType,
      const DeepCollectionEquality().hash(_dailyTasks),
      const DeepCollectionEquality().hash(_achievementTasks),
      const DeepCollectionEquality().hash(_loginStreakTasks),
      const DeepCollectionEquality().hash(_activityTasks),
      isLoading,
      error);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$TaskSystemStateImplCopyWith<_$TaskSystemStateImpl> get copyWith =>
      __$$TaskSystemStateImplCopyWithImpl<_$TaskSystemStateImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$TaskSystemStateImplToJson(
      this,
    );
  }
}

abstract class _TaskSystemState implements TaskSystemState {
  const factory _TaskSystemState(
      {required final List<Task> dailyTasks,
      required final List<Task> achievementTasks,
      required final List<Task> loginStreakTasks,
      required final List<Task> activityTasks,
      final bool? isLoading,
      final String? error}) = _$TaskSystemStateImpl;

  factory _TaskSystemState.fromJson(Map<String, dynamic> json) =
      _$TaskSystemStateImpl.fromJson;

  @override
  List<Task> get dailyTasks;
  @override
  List<Task> get achievementTasks;
  @override
  List<Task> get loginStreakTasks;
  @override
  List<Task> get activityTasks;
  @override
  bool? get isLoading;
  @override
  String? get error;
  @override
  @JsonKey(ignore: true)
  _$$TaskSystemStateImplCopyWith<_$TaskSystemStateImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
