import 'package:freezed_annotation/freezed_annotation.dart';
import 'package:sparkle/features/rpg/data/models/rpg_models.dart';

part 'task_models.freezed.dart';
part 'task_models.g.dart';

/// 任务类型
enum TaskType {
  @JsonValue('daily')
  daily, // 每日任务
  
  @JsonValue('achievement')
  achievement, // 成就任务
  
  @JsonValue('login_streak')
  loginStreak, // 连续登录任务
  
  @JsonValue('activity')
  activity, // 活动任务
}

/// 任务状态
enum TaskStatus {
  @JsonValue('pending')
  pending, // 待完成
  
  @JsonValue('completed')
  completed, // 已完成
  
  @JsonValue('claimed')
  claimed, // 已领取奖励
}

/// 任务奖励类型
enum RewardType {
  @JsonValue('experience')
  experience, // 经验值
  
  @JsonValue('equipment')
  equipment, // 装备
  
  @JsonValue('attribute')
  attribute, // 属性点
}

/// 任务奖励
@freezed
class TaskReward with _$TaskReward {
  const factory TaskReward({
    required RewardType type,
    required int value,
    String? equipmentId,
    CharacterAttribute? attributeType,
  }) = _TaskReward;

  factory TaskReward.fromJson(Map<String, dynamic> json) => _$TaskRewardFromJson(json);
}

/// 任务数据模型
@freezed
class Task with _$Task {
  const factory Task({
    required String id,
    required String title,
    required String description,
    required TaskType type,
    required TaskStatus status,
    required List<TaskReward> rewards,
    required int progress,
    required int target,
    String? icon,
    DateTime? createdAt,
    DateTime? completedAt,
    DateTime? claimedAt,
    int? loginStreakRequirement,
  }) = _Task;

  factory Task.fromJson(Map<String, dynamic> json) => _$TaskFromJson(json);
}

/// 任务系统状态
@freezed
class TaskSystemState with _$TaskSystemState {
  const factory TaskSystemState({
    required List<Task> dailyTasks,
    required List<Task> achievementTasks,
    required List<Task> loginStreakTasks,
    required List<Task> activityTasks,
    bool? isLoading,
    String? error,
  }) = _TaskSystemState;

  factory TaskSystemState.fromJson(Map<String, dynamic> json) => _$TaskSystemStateFromJson(json);
}
