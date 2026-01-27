import 'package:json_annotation/json_annotation.dart';

part 'achievement_model.g.dart';

/// 成就稀有度
enum AchievementRarity {
  @JsonValue('common')
  common,
  @JsonValue('rare')
  rare,
  @JsonValue('epic')
  epic,
  @JsonValue('legendary')
  legendary,
}

/// 成就类型
enum AchievementType {
  @JsonValue('milestone')
  milestone,
  @JsonValue('streak')
  streak,
  @JsonValue('mastery')
  mastery,
  @JsonValue('task_complete')
  taskComplete,
  @JsonValue('hidden')
  hidden,
  @JsonValue('social')
  social,
  @JsonValue('contract')
  contract,
  @JsonValue('study_time')
  studyTime,
  @JsonValue('node_explore')
  nodeExplore,
  @JsonValue('sprint')
  sprint,
}

/// 视觉特效类型
enum VisualEffectType {
  @JsonValue('none')
  none,
  @JsonValue('black_hole')
  blackHole,
  @JsonValue('supernova')
  supernova,
  @JsonValue('gravity_wave')
  gravityWave,
  @JsonValue('nebula_transform')
  nebulaTransform,
  @JsonValue('galaxy_skin')
  galaxySkin,
  @JsonValue('dual_star')
  dualStar,
}

/// 契约状态
enum ContractStatus {
  @JsonValue('active')
  active,
  @JsonValue('completed')
  completed,
  @JsonValue('failed')
  failed,
  @JsonValue('expired')
  expired,
}

// ========== 成就实体 ==========

@JsonSerializable()
class AchievementModel {
  AchievementModel({
    required this.id,
    required this.name,
    required this.type,
    required this.rarity,
    required this.createdAt,
    required this.updatedAt,
    this.description,
    this.iconUrl,
    this.category,
    this.isHidden = false,
    this.hint,
    this.sortOrder = 0,
    this.parentId,
    this.triggerCode,
    this.triggerConfig,
    this.prerequisites,
    this.visualEffectType = VisualEffectType.none,
    this.visualConfig,
    this.rewardConfig,
    this.totalUnlocked = 0,
  });

  factory AchievementModel.fromJson(Map<String, dynamic> json) =>
      _$AchievementModelFromJson(json);

  final String id;
  final String name;
  final String? description;
  @JsonKey(name: 'icon_url')
  final String? iconUrl;
  final AchievementType type;
  final AchievementRarity rarity;
  final String? category;
  @JsonKey(name: 'is_hidden')
  final bool isHidden;
  final String? hint;
  @JsonKey(name: 'sort_order')
  final int sortOrder;
  @JsonKey(name: 'parent_id')
  final String? parentId;
  @JsonKey(name: 'trigger_code')
  final String? triggerCode;
  @JsonKey(name: 'trigger_config')
  final Map<String, dynamic>? triggerConfig;
  final List<String>? prerequisites;
  @JsonKey(name: 'visual_effect_type')
  final VisualEffectType visualEffectType;
  @JsonKey(name: 'visual_config')
  final Map<String, dynamic>? visualConfig;
  @JsonKey(name: 'reward_config')
  final List<Map<String, dynamic>>? rewardConfig;
  @JsonKey(name: 'total_unlocked')
  final int totalUnlocked;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;
  @JsonKey(name: 'updated_at')
  final DateTime updatedAt;

  Map<String, dynamic> toJson() => _$AchievementModelToJson(this);

  AchievementModel copyWith({
    String? id,
    String? name,
    String? description,
    String? iconUrl,
    AchievementType? type,
    AchievementRarity? rarity,
    String? category,
    bool? isHidden,
    String? hint,
    int? sortOrder,
    String? parentId,
    String? triggerCode,
    Map<String, dynamic>? triggerConfig,
    List<String>? prerequisites,
    VisualEffectType? visualEffectType,
    Map<String, dynamic>? visualConfig,
    List<Map<String, dynamic>>? rewardConfig,
    int? totalUnlocked,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) => AchievementModel(
      id: id ?? this.id,
      name: name ?? this.name,
      description: description ?? this.description,
      iconUrl: iconUrl ?? this.iconUrl,
      type: type ?? this.type,
      rarity: rarity ?? this.rarity,
      category: category ?? this.category,
      isHidden: isHidden ?? this.isHidden,
      hint: hint ?? this.hint,
      sortOrder: sortOrder ?? this.sortOrder,
      parentId: parentId ?? this.parentId,
      triggerCode: triggerCode ?? this.triggerCode,
      triggerConfig: triggerConfig ?? this.triggerConfig,
      prerequisites: prerequisites ?? this.prerequisites,
      visualEffectType: visualEffectType ?? this.visualEffectType,
      visualConfig: visualConfig ?? this.visualConfig,
      rewardConfig: rewardConfig ?? this.rewardConfig,
      totalUnlocked: totalUnlocked ?? this.totalUnlocked,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
}

// ========== 用户成就进度 ==========

@JsonSerializable()
class UserAchievementProgress {
  UserAchievementProgress({
    required this.achievementId,
    required this.progress,
    required this.progressValue,
    required this.progressTarget,
    this.isPinned = false,
    this.shareCount = 0,
    this.isFirstUnlocker = false,
    this.unlockedAt,
    this.lastProgressUpdate,
  });

  factory UserAchievementProgress.fromJson(Map<String, dynamic> json) =>
      _$UserAchievementProgressFromJson(json);

  @JsonKey(name: 'achievement_id')
  final String achievementId;
  final double progress;
  @JsonKey(name: 'progress_value')
  final int progressValue;
  @JsonKey(name: 'progress_target')
  final int progressTarget;
  @JsonKey(name: 'is_pinned')
  final bool isPinned;
  @JsonKey(name: 'share_count')
  final int shareCount;
  @JsonKey(name: 'is_first_unlocker')
  final bool isFirstUnlocker;
  final DateTime? unlockedAt;
  @JsonKey(name: 'last_progress_update')
  final DateTime? lastProgressUpdate;

  Map<String, dynamic> toJson() => _$UserAchievementProgressToJson(this);

  UserAchievementProgress copyWith({
    String? achievementId,
    double? progress,
    int? progressValue,
    int? progressTarget,
    bool? isPinned,
    int? shareCount,
    bool? isFirstUnlocker,
    DateTime? unlockedAt,
    DateTime? lastProgressUpdate,
  }) => UserAchievementProgress(
      achievementId: achievementId ?? this.achievementId,
      progress: progress ?? this.progress,
      progressValue: progressValue ?? this.progressValue,
      progressTarget: progressTarget ?? this.progressTarget,
      isPinned: isPinned ?? this.isPinned,
      shareCount: shareCount ?? this.shareCount,
      isFirstUnlocker: isFirstUnlocker ?? this.isFirstUnlocker,
      unlockedAt: unlockedAt ?? this.unlockedAt,
      lastProgressUpdate: lastProgressUpdate ?? this.lastProgressUpdate,
    );
}

// ========== 成就与进度组合 ==========

@JsonSerializable()
class AchievementWithProgress {
  AchievementWithProgress({
    required this.achievement,
    required this.isUnlocked,
    required this.progressPercentage,
    this.userProgress,
  });

  factory AchievementWithProgress.fromJson(Map<String, dynamic> json) =>
      _$AchievementWithProgressFromJson(json);

  final AchievementModel achievement;
  @JsonKey(name: 'user_progress')
  final UserAchievementProgress? userProgress;
  @JsonKey(name: 'is_unlocked')
  final bool isUnlocked;
  @JsonKey(name: 'progress_percentage')
  final int progressPercentage;

  Map<String, dynamic> toJson() => _$AchievementWithProgressToJson(this);
}

// ========== 连胜统计 ==========

@JsonSerializable()
class StreakStats {
  StreakStats({
    required this.currentStreak,
    required this.maxStreak,
    required this.longestStreak,
    required this.freezeCharges, @JsonKey(name: 'max_freeze_charges') required this.maxFreezeCharges, required this.totalCheckinDays, this.lastActivityDate,
    this.longestStreakStart,
    this.longestStreakEnd,
  });

  factory StreakStats.fromJson(Map<String, dynamic> json) =>
      _$StreakStatsFromJson(json);

  @JsonKey(name: 'current_streak')
  final int currentStreak;
  @JsonKey(name: 'max_streak')
  final int maxStreak;
  @JsonKey(name: 'longest_streak')
  final int longestStreak;
  @JsonKey(name: 'last_activity_date')
  final DateTime? lastActivityDate;
  @JsonKey(name: 'freeze_charges')
  final int freezeCharges;
  @JsonKey(name: 'max_freeze_charges')
  final int maxFreezeCharges;
  @JsonKey(name: 'total_checkin_days')
  final int totalCheckinDays;
  @JsonKey(name: 'longest_streak_start')
  final DateTime? longestStreakStart;
  @JsonKey(name: 'longest_streak_end')
  final DateTime? longestStreakEnd;

  Map<String, dynamic> toJson() => _$StreakStatsToJson(this);

  bool get isActiveToday {
    if (lastActivityDate == null) return false;
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final activityDay = DateTime(
      lastActivityDate!.year,
      lastActivityDate!.month,
      lastActivityDate!.day,
    );
    return activityDay.isAtSameMomentAs(today);
  }
}

// ========== 契约 ==========

@JsonSerializable()
class SparkContract {
  SparkContract({
    required this.userId,
    required this.targetStudyMinutes,
    required this.targetDays,
    required this.photonStake,
    required this.status,
    required this.startDate,
    required this.endDate,
    required this.currentDays,
    required this.currentMinutes,
    required this.rewardMultiplier,
    this.completedAt,
    this.failedAt,
    this.failureReason,
  });

  factory SparkContract.fromJson(Map<String, dynamic> json) =>
      _$SparkContractFromJson(json);

  @JsonKey(name: 'user_id')
  final String userId;
  @JsonKey(name: 'target_study_minutes')
  final int targetStudyMinutes;
  @JsonKey(name: 'target_days')
  final int targetDays;
  @JsonKey(name: 'photon_stake')
  final int photonStake;
  final ContractStatus status;
  @JsonKey(name: 'start_date')
  final DateTime startDate;
  @JsonKey(name: 'end_date')
  final DateTime endDate;
  @JsonKey(name: 'current_days')
  final int currentDays;
  @JsonKey(name: 'current_minutes')
  final int currentMinutes;
  @JsonKey(name: 'reward_multiplier')
  final double rewardMultiplier;
  final DateTime? completedAt;
  final DateTime? failedAt;
  @JsonKey(name: 'failure_reason')
  final String? failureReason;

  Map<String, dynamic> toJson() => _$SparkContractToJson(this);

  double get progressPercent {
    if (targetDays == 0) return 0;
    return (currentDays / targetDays).clamp(0.0, 1.0);
  }

  bool get isCompletedToday => currentMinutes >= targetStudyMinutes;
}

// ========== 星系皮肤 ==========

@JsonSerializable()
class GalaxySkin {
  GalaxySkin({
    required this.id,
    required this.name,
    required this.rarity,
    required this.sortOrder,
    required this.createdAt,
    required this.updatedAt,
    this.description,
    this.previewUrl,
    this.unlockType,
    this.unlockRequirement,
    this.skinConfig,
    this.isUnlocked = false,
    this.isEquipped = false,
    this.unlockedAt,
  });

  factory GalaxySkin.fromJson(Map<String, dynamic> json) =>
      _$GalaxySkinFromJson(json);

  final String id;
  final String name;
  final String? description;
  @JsonKey(name: 'preview_url')
  final String? previewUrl;
  @JsonKey(name: 'unlock_type')
  final String? unlockType;
  @JsonKey(name: 'unlock_requirement')
  final Map<String, dynamic>? unlockRequirement;
  @JsonKey(name: 'skin_config')
  final Map<String, dynamic>? skinConfig;
  final AchievementRarity rarity;
  @JsonKey(name: 'sort_order')
  final int sortOrder;
  @JsonKey(name: 'is_unlocked')
  final bool isUnlocked;
  @JsonKey(name: 'is_equipped')
  final bool isEquipped;
  @JsonKey(name: 'unlocked_at')
  final DateTime? unlockedAt;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;
  @JsonKey(name: 'updated_at')
  final DateTime updatedAt;

  Map<String, dynamic> toJson() => _$GalaxySkinToJson(this);
}

// ========== 称号 ==========

@JsonSerializable()
class UserTitle {
  UserTitle({
    required this.userId,
    required this.titleId,
    required this.titleName,
    required this.titleDisplay,
    required this.unlockedAt,
    this.sourceAchievementId,
    this.isEquipped = false,
  });

  factory UserTitle.fromJson(Map<String, dynamic> json) =>
      _$UserTitleFromJson(json);

  @JsonKey(name: 'user_id')
  final String userId;
  @JsonKey(name: 'title_id')
  final String titleId;
  @JsonKey(name: 'title_name')
  final String titleName;
  @JsonKey(name: 'title_display')
  final String titleDisplay;
  @JsonKey(name: 'source_achievement_id')
  final String? sourceAchievementId;
  @JsonKey(name: 'is_equipped')
  final bool isEquipped;
  @JsonKey(name: 'unlocked_at')
  final DateTime unlockedAt;

  Map<String, dynamic> toJson() => _$UserTitleToJson(this);
}

// ========== 成就统计 ==========

@JsonSerializable()
class AchievementStats {
  AchievementStats({
    required this.totalAchievements,
    required this.unlockedCount,
    required this.unlockedPercentage,
    required this.commonCount,
    required this.rareCount,
    required this.epicCount,
    required this.legendaryCount,
    required this.hiddenFound,
    required this.currentStreak,
    required this.totalPhotons,
  });

  factory AchievementStats.fromJson(Map<String, dynamic> json) =>
      _$AchievementStatsFromJson(json);

  @JsonKey(name: 'total_achievements')
  final int totalAchievements;
  @JsonKey(name: 'unlocked_count')
  final int unlockedCount;
  @JsonKey(name: 'unlocked_percentage')
  final double unlockedPercentage;
  @JsonKey(name: 'common_count')
  final int commonCount;
  @JsonKey(name: 'rare_count')
  final int rareCount;
  @JsonKey(name: 'epic_count')
  final int epicCount;
  @JsonKey(name: 'legendary_count')
  final int legendaryCount;
  @JsonKey(name: 'hidden_found')
  final int hiddenFound;
  @JsonKey(name: 'current_streak')
  final int currentStreak;
  @JsonKey(name: 'total_photons')
  final int totalPhotons;

  Map<String, dynamic> toJson() => _$AchievementStatsToJson(this);
}

// ========== 成就地图节点 ==========

@JsonSerializable()
class AchievementMapNode {
  AchievementMapNode({
    required this.id,
    required this.name,
    required this.rarity,
    required this.category,
    required this.position,
    required this.isUnlocked,
    this.isHidden = false,
    this.prerequisites = const [],
    this.parentId,
  });

  factory AchievementMapNode.fromJson(Map<String, dynamic> json) =>
      _$AchievementMapNodeFromJson(json);

  final String id;
  final String name;
  final AchievementRarity rarity;
  final String category;
  final Map<String, double> position;
  @JsonKey(name: 'is_unlocked')
  final bool isUnlocked;
  @JsonKey(name: 'is_hidden')
  final bool isHidden;
  final List<String> prerequisites;
  @JsonKey(name: 'parent_id')
  final String? parentId;

  Map<String, dynamic> toJson() => _$AchievementMapNodeToJson(this);
}

// ========== 成就地图响应 ==========

@JsonSerializable()
class AchievementMapData {
  AchievementMapData({
    required this.nodes,
    this.connections = const [],
    this.categories = const [],
  });

  factory AchievementMapData.fromJson(Map<String, dynamic> json) =>
      _$AchievementMapDataFromJson(json);

  final List<AchievementMapNode> nodes;
  final List<Map<String, dynamic>> connections;
  final List<Map<String, dynamic>> categories;

  Map<String, dynamic> toJson() => _$AchievementMapDataToJson(this);
}

// ========== 成就解锁事件 ==========

@JsonSerializable()
class AchievementUnlockEvent {
  AchievementUnlockEvent({
    required this.achievementId,
    required this.name,
    required this.rarity,
    required this.unlockedAt,
    this.visualEffect,
    this.visualEffectType,
    this.rewards,
    this.isFirst = false,
  });

  factory AchievementUnlockEvent.fromJson(Map<String, dynamic> json) =>
      _$AchievementUnlockEventFromJson(json);

  @JsonKey(name: 'achievement_id')
  final String achievementId;
  final String name;
  final AchievementRarity rarity;
  @JsonKey(name: 'unlocked_at')
  final DateTime unlockedAt;
  @JsonKey(name: 'visual_effect')
  final Map<String, dynamic>? visualEffect;
  @JsonKey(name: 'visual_effect_type')
  final VisualEffectType? visualEffectType;
  final List<Map<String, dynamic>>? rewards;
  @JsonKey(name: 'is_first')
  final bool isFirst;

  Map<String, dynamic> toJson() => _$AchievementUnlockEventToJson(this);
}
