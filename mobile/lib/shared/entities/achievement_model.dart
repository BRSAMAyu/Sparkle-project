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

/// 连胜日历状态
enum StreakDayStatus {
  @JsonValue('active')
  active,
  @JsonValue('frozen')
  frozen,
  @JsonValue('missed')
  missed,
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
    this.activeFrom,
    this.activeTo,
    this.isLimited = false,
    this.eventTag,
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
  @JsonKey(name: 'active_from')
  final DateTime? activeFrom;
  @JsonKey(name: 'active_to')
  final DateTime? activeTo;
  @JsonKey(name: 'is_limited')
  final bool isLimited;
  @JsonKey(name: 'event_tag')
  final String? eventTag;
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
    DateTime? activeFrom,
    DateTime? activeTo,
    bool? isLimited,
    String? eventTag,
    int? totalUnlocked,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) =>
      AchievementModel(
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
        activeFrom: activeFrom ?? this.activeFrom,
        activeTo: activeTo ?? this.activeTo,
        isLimited: isLimited ?? this.isLimited,
        eventTag: eventTag ?? this.eventTag,
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
    this.contextSnapshot,
    this.contextStory,
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
  @JsonKey(name: 'unlocked_at')
  final DateTime? unlockedAt;
  @JsonKey(name: 'last_progress_update')
  final DateTime? lastProgressUpdate;
  @JsonKey(name: 'context_snapshot')
  final Map<String, dynamic>? contextSnapshot;
  @JsonKey(name: 'context_story')
  final String? contextStory;

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
    Map<String, dynamic>? contextSnapshot,
    String? contextStory,
  }) =>
      UserAchievementProgress(
        achievementId: achievementId ?? this.achievementId,
        progress: progress ?? this.progress,
        progressValue: progressValue ?? this.progressValue,
        progressTarget: progressTarget ?? this.progressTarget,
        isPinned: isPinned ?? this.isPinned,
        shareCount: shareCount ?? this.shareCount,
        isFirstUnlocker: isFirstUnlocker ?? this.isFirstUnlocker,
        unlockedAt: unlockedAt ?? this.unlockedAt,
        lastProgressUpdate: lastProgressUpdate ?? this.lastProgressUpdate,
        contextSnapshot: contextSnapshot ?? this.contextSnapshot,
        contextStory: contextStory ?? this.contextStory,
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
    required this.freezeCharges,
    @JsonKey(name: 'max_freeze_charges') required this.maxFreezeCharges,
    required this.totalCheckinDays,
    this.lastActivityDate,
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

// ========== 连胜日历历史 ==========

@JsonSerializable()
class StreakDayRecord {
  StreakDayRecord({
    required this.day,
    required this.status,
    this.usedFreeze = false,
    this.sourceEvent,
  });

  factory StreakDayRecord.fromJson(Map<String, dynamic> json) =>
      _$StreakDayRecordFromJson(json);

  final DateTime day;
  final StreakDayStatus status;
  @JsonKey(name: 'used_freeze')
  final bool usedFreeze;
  @JsonKey(name: 'source_event')
  final String? sourceEvent;

  Map<String, dynamic> toJson() => _$StreakDayRecordToJson(this);
}

@JsonSerializable()
class StreakHistoryResponse {
  StreakHistoryResponse({required this.days});

  factory StreakHistoryResponse.fromJson(Map<String, dynamic> json) =>
      _$StreakHistoryResponseFromJson(json);

  final List<StreakDayRecord> days;

  Map<String, dynamic> toJson() => _$StreakHistoryResponseToJson(this);
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
  @JsonKey(name: 'completed_at')
  final DateTime? completedAt;
  @JsonKey(name: 'failed_at')
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
    this.createdAt,
    this.updatedAt,
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
  final DateTime? createdAt;
  @JsonKey(name: 'updated_at')
  final DateTime? updatedAt;

  Map<String, dynamic> toJson() => _$GalaxySkinToJson(this);
}

// ========== 称号 ==========

@JsonSerializable()
class UserTitle {
  UserTitle({
    required this.titleId,
    required this.titleName,
    required this.titleDisplay,
    required this.unlockedAt,
    this.sourceAchievementId,
    this.isEquipped = false,
  });

  factory UserTitle.fromJson(Map<String, dynamic> json) =>
      _$UserTitleFromJson(json);

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
    this.lane = 'prestige_lane',
    this.laneLabel = '声望进阶线',
    required this.position,
    required this.isUnlocked,
    this.isHidden = false,
    this.prerequisites = const [],
    this.parentId,
    this.displayState = 'blocked',
    this.isRecommendedTarget = false,
    this.rewardPreview = const [],
    this.progressPercentage = 0,
    this.progressValue = 0,
    this.progressTarget = 1,
    this.unlockHint,
  });

  factory AchievementMapNode.fromJson(Map<String, dynamic> json) =>
      _$AchievementMapNodeFromJson(json);

  final String id;
  final String name;
  final AchievementRarity rarity;
  final String category;
  final String lane;
  @JsonKey(name: 'lane_label')
  final String laneLabel;
  final Map<String, double> position;
  @JsonKey(name: 'is_unlocked')
  final bool isUnlocked;
  @JsonKey(name: 'is_hidden')
  final bool isHidden;
  final List<String> prerequisites;
  @JsonKey(name: 'parent_id')
  final String? parentId;
  @JsonKey(name: 'display_state')
  final String displayState;
  @JsonKey(name: 'is_recommended_target')
  final bool isRecommendedTarget;
  @JsonKey(name: 'reward_preview')
  final List<String> rewardPreview;
  @JsonKey(name: 'progress_percentage')
  final int progressPercentage;
  @JsonKey(name: 'progress_value')
  final int progressValue;
  @JsonKey(name: 'progress_target')
  final int progressTarget;
  @JsonKey(name: 'unlock_hint')
  final String? unlockHint;

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
    this.rewardPreview = const [],
    this.surfacePreview = const [],
    this.gloryLines = const [],
    this.contextSnapshot,
    this.contextStory,
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
  @JsonKey(name: 'reward_preview')
  final List<String> rewardPreview;
  @JsonKey(name: 'surface_preview')
  final List<String> surfacePreview;
  @JsonKey(name: 'glory_lines')
  final List<String> gloryLines;
  @JsonKey(name: 'context_snapshot')
  final Map<String, dynamic>? contextSnapshot;
  @JsonKey(name: 'context_story')
  final String? contextStory;

  Map<String, dynamic> toJson() => _$AchievementUnlockEventToJson(this);
}

// ========== 成就分享卡 ==========

/// Privacy settings for share card generation
class ShareCardPrivacySettings {
  ShareCardPrivacySettings({
    this.displayName,
    this.showAvatar = false,
    this.showUnlockDate = true,
    this.showProgressStats = true,
    this.showFirstUnlockerBadge = true,
  });

  factory ShareCardPrivacySettings.fromJson(Map<String, dynamic> json) =>
      ShareCardPrivacySettings(
        displayName: json['display_name'] as String?,
        showAvatar: json['show_avatar'] as bool? ?? false,
        showUnlockDate: json['show_unlock_date'] as bool? ?? true,
        showProgressStats: json['show_progress_stats'] as bool? ?? true,
        showFirstUnlockerBadge:
            json['show_first_unlocker_badge'] as bool? ?? true,
      );

  /// Custom display name, null means use default nickname
  final String? displayName;

  /// Whether to show user avatar on card
  final bool showAvatar;

  /// Whether to show unlock date on card
  final bool showUnlockDate;

  /// Whether to show progress statistics on card
  final bool showProgressStats;

  /// Whether to show first unlocker badge if applicable
  final bool showFirstUnlockerBadge;

  String getEffectiveDisplayName(String defaultName) =>
      displayName ?? defaultName;

  Map<String, dynamic> toJson() => <String, dynamic>{
        'display_name': displayName,
        'show_avatar': showAvatar,
        'show_unlock_date': showUnlockDate,
        'show_progress_stats': showProgressStats,
        'show_first_unlocker_badge': showFirstUnlockerBadge,
      };

  ShareCardPrivacySettings copyWith({
    String? displayName,
    bool? showAvatar,
    bool? showUnlockDate,
    bool? showProgressStats,
    bool? showFirstUnlockerBadge,
  }) =>
      ShareCardPrivacySettings(
        displayName: displayName ?? this.displayName,
        showAvatar: showAvatar ?? this.showAvatar,
        showUnlockDate: showUnlockDate ?? this.showUnlockDate,
        showProgressStats: showProgressStats ?? this.showProgressStats,
        showFirstUnlockerBadge:
            showFirstUnlockerBadge ?? this.showFirstUnlockerBadge,
      );

  /// Generate a hash for cache key purposes
  String settingsHash() {
    final parts = [
      displayName ?? '',
      showAvatar.toString(),
      showUnlockDate.toString(),
      showProgressStats.toString(),
      showFirstUnlockerBadge.toString(),
    ];
    return parts.join('_').hashCode.toRadixString(16);
  }
}

/// Share card template information
class ShareTemplateInfo {
  ShareTemplateInfo({
    required this.id,
    required this.name,
    this.description,
    this.previewUrl,
  });

  factory ShareTemplateInfo.fromJson(Map<String, dynamic> json) =>
      ShareTemplateInfo(
        id: json['id'] as String,
        name: json['name'] as String,
        description: json['description'] as String?,
        previewUrl: json['preview_url'] as String?,
      );

  final String id;
  final String name;
  final String? description;
  final String? previewUrl;

  Map<String, dynamic> toJson() => <String, dynamic>{
        'id': id,
        'name': name,
        'description': description,
        'preview_url': previewUrl,
      };
}

class AchievementShareCard {
  AchievementShareCard({
    required this.cardUrl,
    this.mimeType = 'image/png',
    this.width = 0,
    this.height = 0,
    required this.generatedAt,
    this.templateId = 'cosmic',
    this.privacySettings,
    required this.achievement,
  });

  factory AchievementShareCard.fromJson(Map<String, dynamic> json) =>
      AchievementShareCard(
        cardUrl: json['card_url'] as String? ?? '',
        mimeType: json['mime_type'] as String? ?? 'image/png',
        width: (json['width'] as num?)?.toInt() ?? 0,
        height: (json['height'] as num?)?.toInt() ?? 0,
        generatedAt: DateTime.parse(
          json['generated_at'] as String? ?? DateTime.now().toIso8601String(),
        ),
        templateId: json['template_id'] as String? ?? 'cosmic',
        privacySettings: json['privacy_settings'] != null
            ? ShareCardPrivacySettings.fromJson(
                json['privacy_settings'] as Map<String, dynamic>,
              )
            : null,
        achievement: AchievementModel.fromJson(
          json['achievement'] as Map<String, dynamic>? ?? <String, dynamic>{},
        ),
      );

  final String cardUrl;
  final String mimeType;
  final int width;
  final int height;
  final DateTime generatedAt;
  final String templateId;
  final ShareCardPrivacySettings? privacySettings;
  final AchievementModel achievement;

  Map<String, dynamic> toJson() => <String, dynamic>{
        'card_url': cardUrl,
        'mime_type': mimeType,
        'width': width,
        'height': height,
        'generated_at': generatedAt.toIso8601String(),
        'template_id': templateId,
        'privacy_settings': privacySettings?.toJson(),
        'achievement': achievement.toJson(),
      };
}
