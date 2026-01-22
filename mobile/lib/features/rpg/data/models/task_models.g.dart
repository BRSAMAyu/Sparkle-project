// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'task_models.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$TaskRewardImpl _$$TaskRewardImplFromJson(Map<String, dynamic> json) =>
    _$TaskRewardImpl(
      type: $enumDecode(_$RewardTypeEnumMap, json['type']),
      value: (json['value'] as num).toInt(),
      equipmentId: json['equipmentId'] as String?,
      attributeType: $enumDecodeNullable(
          _$CharacterAttributeEnumMap, json['attributeType']),
    );

Map<String, dynamic> _$$TaskRewardImplToJson(_$TaskRewardImpl instance) =>
    <String, dynamic>{
      'type': _$RewardTypeEnumMap[instance.type]!,
      'value': instance.value,
      'equipmentId': instance.equipmentId,
      'attributeType': _$CharacterAttributeEnumMap[instance.attributeType],
    };

const _$RewardTypeEnumMap = {
  RewardType.experience: 'experience',
  RewardType.equipment: 'equipment',
  RewardType.attribute: 'attribute',
};

const _$CharacterAttributeEnumMap = {
  CharacterAttribute.strength: 'strength',
  CharacterAttribute.intelligence: 'intelligence',
  CharacterAttribute.agility: 'agility',
  CharacterAttribute.vitality: 'vitality',
  CharacterAttribute.luck: 'luck',
};

_$TaskImpl _$$TaskImplFromJson(Map<String, dynamic> json) => _$TaskImpl(
      id: json['id'] as String,
      title: json['title'] as String,
      description: json['description'] as String,
      type: $enumDecode(_$TaskTypeEnumMap, json['type']),
      status: $enumDecode(_$TaskStatusEnumMap, json['status']),
      rewards: (json['rewards'] as List<dynamic>)
          .map((e) => TaskReward.fromJson(e as Map<String, dynamic>))
          .toList(),
      progress: (json['progress'] as num).toInt(),
      target: (json['target'] as num).toInt(),
      icon: json['icon'] as String?,
      createdAt: json['createdAt'] == null
          ? null
          : DateTime.parse(json['createdAt'] as String),
      completedAt: json['completedAt'] == null
          ? null
          : DateTime.parse(json['completedAt'] as String),
      claimedAt: json['claimedAt'] == null
          ? null
          : DateTime.parse(json['claimedAt'] as String),
      loginStreakRequirement: (json['loginStreakRequirement'] as num?)?.toInt(),
    );

Map<String, dynamic> _$$TaskImplToJson(_$TaskImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'title': instance.title,
      'description': instance.description,
      'type': _$TaskTypeEnumMap[instance.type]!,
      'status': _$TaskStatusEnumMap[instance.status]!,
      'rewards': instance.rewards,
      'progress': instance.progress,
      'target': instance.target,
      'icon': instance.icon,
      'createdAt': instance.createdAt?.toIso8601String(),
      'completedAt': instance.completedAt?.toIso8601String(),
      'claimedAt': instance.claimedAt?.toIso8601String(),
      'loginStreakRequirement': instance.loginStreakRequirement,
    };

const _$TaskTypeEnumMap = {
  TaskType.daily: 'daily',
  TaskType.achievement: 'achievement',
  TaskType.loginStreak: 'login_streak',
  TaskType.activity: 'activity',
};

const _$TaskStatusEnumMap = {
  TaskStatus.pending: 'pending',
  TaskStatus.completed: 'completed',
  TaskStatus.claimed: 'claimed',
};

_$TaskSystemStateImpl _$$TaskSystemStateImplFromJson(
        Map<String, dynamic> json) =>
    _$TaskSystemStateImpl(
      dailyTasks: (json['dailyTasks'] as List<dynamic>)
          .map((e) => Task.fromJson(e as Map<String, dynamic>))
          .toList(),
      achievementTasks: (json['achievementTasks'] as List<dynamic>)
          .map((e) => Task.fromJson(e as Map<String, dynamic>))
          .toList(),
      loginStreakTasks: (json['loginStreakTasks'] as List<dynamic>)
          .map((e) => Task.fromJson(e as Map<String, dynamic>))
          .toList(),
      activityTasks: (json['activityTasks'] as List<dynamic>)
          .map((e) => Task.fromJson(e as Map<String, dynamic>))
          .toList(),
      isLoading: json['isLoading'] as bool?,
      error: json['error'] as String?,
    );

Map<String, dynamic> _$$TaskSystemStateImplToJson(
        _$TaskSystemStateImpl instance) =>
    <String, dynamic>{
      'dailyTasks': instance.dailyTasks,
      'achievementTasks': instance.achievementTasks,
      'loginStreakTasks': instance.loginStreakTasks,
      'activityTasks': instance.activityTasks,
      'isLoading': instance.isLoading,
      'error': instance.error,
    };
