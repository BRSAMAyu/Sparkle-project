// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'achievement_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

AchievementModel _$AchievementModelFromJson(Map<String, dynamic> json) =>
    AchievementModel(
      id: json['id'] as String,
      name: json['name'] as String,
      type: $enumDecode(_$AchievementTypeEnumMap, json['type']),
      rarity: $enumDecode(_$AchievementRarityEnumMap, json['rarity']),
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
      description: json['description'] as String?,
      iconUrl: json['icon_url'] as String?,
      category: json['category'] as String?,
      isHidden: json['is_hidden'] as bool? ?? false,
      hint: json['hint'] as String?,
      sortOrder: (json['sort_order'] as num?)?.toInt() ?? 0,
      parentId: json['parent_id'] as String?,
      triggerCode: json['trigger_code'] as String?,
      triggerConfig: json['trigger_config'] as Map<String, dynamic>?,
      prerequisites: (json['prerequisites'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
      visualEffectType: $enumDecodeNullable(
              _$VisualEffectTypeEnumMap, json['visual_effect_type']) ??
          VisualEffectType.none,
      visualConfig: json['visual_config'] as Map<String, dynamic>?,
      rewardConfig: (json['reward_config'] as List<dynamic>?)
          ?.map((e) => e as Map<String, dynamic>)
          .toList(),
      totalUnlocked: (json['total_unlocked'] as num?)?.toInt() ?? 0,
    );

Map<String, dynamic> _$AchievementModelToJson(AchievementModel instance) =>
    <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'description': instance.description,
      'icon_url': instance.iconUrl,
      'type': _$AchievementTypeEnumMap[instance.type]!,
      'rarity': _$AchievementRarityEnumMap[instance.rarity]!,
      'category': instance.category,
      'is_hidden': instance.isHidden,
      'hint': instance.hint,
      'sort_order': instance.sortOrder,
      'parent_id': instance.parentId,
      'trigger_code': instance.triggerCode,
      'trigger_config': instance.triggerConfig,
      'prerequisites': instance.prerequisites,
      'visual_effect_type':
          _$VisualEffectTypeEnumMap[instance.visualEffectType]!,
      'visual_config': instance.visualConfig,
      'reward_config': instance.rewardConfig,
      'total_unlocked': instance.totalUnlocked,
      'created_at': instance.createdAt.toIso8601String(),
      'updated_at': instance.updatedAt.toIso8601String(),
    };

const _$AchievementTypeEnumMap = {
  AchievementType.milestone: 'milestone',
  AchievementType.streak: 'streak',
  AchievementType.mastery: 'mastery',
  AchievementType.taskComplete: 'task_complete',
  AchievementType.hidden: 'hidden',
  AchievementType.social: 'social',
  AchievementType.contract: 'contract',
  AchievementType.studyTime: 'study_time',
  AchievementType.nodeExplore: 'node_explore',
};

const _$AchievementRarityEnumMap = {
  AchievementRarity.common: 'common',
  AchievementRarity.rare: 'rare',
  AchievementRarity.epic: 'epic',
  AchievementRarity.legendary: 'legendary',
};

const _$VisualEffectTypeEnumMap = {
  VisualEffectType.none: 'none',
  VisualEffectType.blackHole: 'black_hole',
  VisualEffectType.supernova: 'supernova',
  VisualEffectType.gravityWave: 'gravity_wave',
  VisualEffectType.nebulaTransform: 'nebula_transform',
  VisualEffectType.galaxySkin: 'galaxy_skin',
  VisualEffectType.dualStar: 'dual_star',
};

UserAchievementProgress _$UserAchievementProgressFromJson(
        Map<String, dynamic> json) =>
    UserAchievementProgress(
      achievementId: json['achievement_id'] as String,
      progress: (json['progress'] as num).toDouble(),
      progressValue: (json['progress_value'] as num).toInt(),
      progressTarget: (json['progress_target'] as num).toInt(),
      isPinned: json['is_pinned'] as bool? ?? false,
      shareCount: (json['share_count'] as num?)?.toInt() ?? 0,
      isFirstUnlocker: json['is_first_unlocker'] as bool? ?? false,
      unlockedAt: json['unlockedAt'] == null
          ? null
          : DateTime.parse(json['unlockedAt'] as String),
      lastProgressUpdate: json['last_progress_update'] == null
          ? null
          : DateTime.parse(json['last_progress_update'] as String),
    );

Map<String, dynamic> _$UserAchievementProgressToJson(
        UserAchievementProgress instance) =>
    <String, dynamic>{
      'achievement_id': instance.achievementId,
      'progress': instance.progress,
      'progress_value': instance.progressValue,
      'progress_target': instance.progressTarget,
      'is_pinned': instance.isPinned,
      'share_count': instance.shareCount,
      'is_first_unlocker': instance.isFirstUnlocker,
      'unlockedAt': instance.unlockedAt?.toIso8601String(),
      'last_progress_update': instance.lastProgressUpdate?.toIso8601String(),
    };

AchievementWithProgress _$AchievementWithProgressFromJson(
        Map<String, dynamic> json) =>
    AchievementWithProgress(
      achievement: AchievementModel.fromJson(
          json['achievement'] as Map<String, dynamic>),
      isUnlocked: json['is_unlocked'] as bool,
      progressPercentage: (json['progress_percentage'] as num).toInt(),
      userProgress: json['user_progress'] == null
          ? null
          : UserAchievementProgress.fromJson(
              json['user_progress'] as Map<String, dynamic>),
    );

Map<String, dynamic> _$AchievementWithProgressToJson(
        AchievementWithProgress instance) =>
    <String, dynamic>{
      'achievement': instance.achievement,
      'user_progress': instance.userProgress,
      'is_unlocked': instance.isUnlocked,
      'progress_percentage': instance.progressPercentage,
    };

StreakStats _$StreakStatsFromJson(Map<String, dynamic> json) => StreakStats(
      currentStreak: (json['current_streak'] as num).toInt(),
      maxStreak: (json['max_streak'] as num).toInt(),
      longestStreak: (json['longest_streak'] as num).toInt(),
      lastActivityDate: json['last_activity_date'] == null
          ? null
          : DateTime.parse(json['last_activity_date'] as String),
      freezeCharges: (json['freeze_charges'] as num).toInt(),
      maxFreezeCharges: (json['max_freeze_charges'] as num).toInt(),
      totalCheckinDays: (json['total_checkin_days'] as num).toInt(),
      longestStreakStart: json['longest_streak_start'] == null
          ? null
          : DateTime.parse(json['longest_streak_start'] as String),
      longestStreakEnd: json['longest_streak_end'] == null
          ? null
          : DateTime.parse(json['longest_streak_end'] as String),
    );

Map<String, dynamic> _$StreakStatsToJson(StreakStats instance) =>
    <String, dynamic>{
      'current_streak': instance.currentStreak,
      'max_streak': instance.maxStreak,
      'longest_streak': instance.longestStreak,
      'last_activity_date': instance.lastActivityDate?.toIso8601String(),
      'freeze_charges': instance.freezeCharges,
      'max_freeze_charges': instance.maxFreezeCharges,
      'total_checkin_days': instance.totalCheckinDays,
      'longest_streak_start': instance.longestStreakStart?.toIso8601String(),
      'longest_streak_end': instance.longestStreakEnd?.toIso8601String(),
    };

SparkContract _$SparkContractFromJson(Map<String, dynamic> json) =>
    SparkContract(
      userId: json['user_id'] as String,
      targetStudyMinutes: (json['target_study_minutes'] as num).toInt(),
      targetDays: (json['target_days'] as num).toInt(),
      photonStake: (json['photon_stake'] as num).toInt(),
      status: $enumDecode(_$ContractStatusEnumMap, json['status']),
      startDate: DateTime.parse(json['start_date'] as String),
      endDate: DateTime.parse(json['end_date'] as String),
      currentDays: (json['current_days'] as num).toInt(),
      currentMinutes: (json['current_minutes'] as num).toInt(),
      rewardMultiplier: (json['reward_multiplier'] as num).toDouble(),
      completedAt: json['completedAt'] == null
          ? null
          : DateTime.parse(json['completedAt'] as String),
      failedAt: json['failedAt'] == null
          ? null
          : DateTime.parse(json['failedAt'] as String),
      failureReason: json['failure_reason'] as String?,
    );

Map<String, dynamic> _$SparkContractToJson(SparkContract instance) =>
    <String, dynamic>{
      'user_id': instance.userId,
      'target_study_minutes': instance.targetStudyMinutes,
      'target_days': instance.targetDays,
      'photon_stake': instance.photonStake,
      'status': _$ContractStatusEnumMap[instance.status]!,
      'start_date': instance.startDate.toIso8601String(),
      'end_date': instance.endDate.toIso8601String(),
      'current_days': instance.currentDays,
      'current_minutes': instance.currentMinutes,
      'reward_multiplier': instance.rewardMultiplier,
      'completedAt': instance.completedAt?.toIso8601String(),
      'failedAt': instance.failedAt?.toIso8601String(),
      'failure_reason': instance.failureReason,
    };

const _$ContractStatusEnumMap = {
  ContractStatus.active: 'active',
  ContractStatus.completed: 'completed',
  ContractStatus.failed: 'failed',
  ContractStatus.expired: 'expired',
};

GalaxySkin _$GalaxySkinFromJson(Map<String, dynamic> json) => GalaxySkin(
      id: json['id'] as String,
      name: json['name'] as String,
      rarity: $enumDecode(_$AchievementRarityEnumMap, json['rarity']),
      sortOrder: (json['sort_order'] as num).toInt(),
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
      description: json['description'] as String?,
      previewUrl: json['preview_url'] as String?,
      unlockType: json['unlock_type'] as String?,
      unlockRequirement: json['unlock_requirement'] as Map<String, dynamic>?,
      skinConfig: json['skin_config'] as Map<String, dynamic>?,
      isUnlocked: json['is_unlocked'] as bool? ?? false,
      isEquipped: json['is_equipped'] as bool? ?? false,
      unlockedAt: json['unlocked_at'] == null
          ? null
          : DateTime.parse(json['unlocked_at'] as String),
    );

Map<String, dynamic> _$GalaxySkinToJson(GalaxySkin instance) =>
    <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'description': instance.description,
      'preview_url': instance.previewUrl,
      'unlock_type': instance.unlockType,
      'unlock_requirement': instance.unlockRequirement,
      'skin_config': instance.skinConfig,
      'rarity': _$AchievementRarityEnumMap[instance.rarity]!,
      'sort_order': instance.sortOrder,
      'is_unlocked': instance.isUnlocked,
      'is_equipped': instance.isEquipped,
      'unlocked_at': instance.unlockedAt?.toIso8601String(),
      'created_at': instance.createdAt.toIso8601String(),
      'updated_at': instance.updatedAt.toIso8601String(),
    };

UserTitle _$UserTitleFromJson(Map<String, dynamic> json) => UserTitle(
      userId: json['user_id'] as String,
      titleId: json['title_id'] as String,
      titleName: json['title_name'] as String,
      titleDisplay: json['title_display'] as String,
      unlockedAt: DateTime.parse(json['unlocked_at'] as String),
      sourceAchievementId: json['source_achievement_id'] as String?,
      isEquipped: json['is_equipped'] as bool? ?? false,
    );

Map<String, dynamic> _$UserTitleToJson(UserTitle instance) => <String, dynamic>{
      'user_id': instance.userId,
      'title_id': instance.titleId,
      'title_name': instance.titleName,
      'title_display': instance.titleDisplay,
      'source_achievement_id': instance.sourceAchievementId,
      'is_equipped': instance.isEquipped,
      'unlocked_at': instance.unlockedAt.toIso8601String(),
    };

AchievementStats _$AchievementStatsFromJson(Map<String, dynamic> json) =>
    AchievementStats(
      totalAchievements: (json['total_achievements'] as num).toInt(),
      unlockedCount: (json['unlocked_count'] as num).toInt(),
      unlockedPercentage: (json['unlocked_percentage'] as num).toDouble(),
      commonCount: (json['common_count'] as num).toInt(),
      rareCount: (json['rare_count'] as num).toInt(),
      epicCount: (json['epic_count'] as num).toInt(),
      legendaryCount: (json['legendary_count'] as num).toInt(),
      hiddenFound: (json['hidden_found'] as num).toInt(),
      currentStreak: (json['current_streak'] as num).toInt(),
      totalPhotons: (json['total_photons'] as num).toInt(),
    );

Map<String, dynamic> _$AchievementStatsToJson(AchievementStats instance) =>
    <String, dynamic>{
      'total_achievements': instance.totalAchievements,
      'unlocked_count': instance.unlockedCount,
      'unlocked_percentage': instance.unlockedPercentage,
      'common_count': instance.commonCount,
      'rare_count': instance.rareCount,
      'epic_count': instance.epicCount,
      'legendary_count': instance.legendaryCount,
      'hidden_found': instance.hiddenFound,
      'current_streak': instance.currentStreak,
      'total_photons': instance.totalPhotons,
    };

AchievementMapNode _$AchievementMapNodeFromJson(Map<String, dynamic> json) =>
    AchievementMapNode(
      id: json['id'] as String,
      name: json['name'] as String,
      rarity: $enumDecode(_$AchievementRarityEnumMap, json['rarity']),
      category: json['category'] as String,
      position: (json['position'] as Map<String, dynamic>).map(
        (k, e) => MapEntry(k, (e as num).toDouble()),
      ),
      isUnlocked: json['is_unlocked'] as bool,
      isHidden: json['is_hidden'] as bool? ?? false,
      prerequisites: (json['prerequisites'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          const [],
      parentId: json['parent_id'] as String?,
    );

Map<String, dynamic> _$AchievementMapNodeToJson(AchievementMapNode instance) =>
    <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'rarity': _$AchievementRarityEnumMap[instance.rarity]!,
      'category': instance.category,
      'position': instance.position,
      'is_unlocked': instance.isUnlocked,
      'is_hidden': instance.isHidden,
      'prerequisites': instance.prerequisites,
      'parent_id': instance.parentId,
    };

AchievementMapData _$AchievementMapDataFromJson(Map<String, dynamic> json) =>
    AchievementMapData(
      nodes: (json['nodes'] as List<dynamic>)
          .map((e) => AchievementMapNode.fromJson(e as Map<String, dynamic>))
          .toList(),
      connections: (json['connections'] as List<dynamic>?)
              ?.map((e) => e as Map<String, dynamic>)
              .toList() ??
          const [],
      categories: (json['categories'] as List<dynamic>?)
              ?.map((e) => e as Map<String, dynamic>)
              .toList() ??
          const [],
    );

Map<String, dynamic> _$AchievementMapDataToJson(AchievementMapData instance) =>
    <String, dynamic>{
      'nodes': instance.nodes,
      'connections': instance.connections,
      'categories': instance.categories,
    };

AchievementUnlockEvent _$AchievementUnlockEventFromJson(
        Map<String, dynamic> json) =>
    AchievementUnlockEvent(
      achievementId: json['achievement_id'] as String,
      name: json['name'] as String,
      rarity: $enumDecode(_$AchievementRarityEnumMap, json['rarity']),
      unlockedAt: DateTime.parse(json['unlocked_at'] as String),
      visualEffect: json['visual_effect'] as Map<String, dynamic>?,
      visualEffectType: $enumDecodeNullable(
          _$VisualEffectTypeEnumMap, json['visual_effect_type']),
      rewards: (json['rewards'] as List<dynamic>?)
          ?.map((e) => e as Map<String, dynamic>)
          .toList(),
      isFirst: json['is_first'] as bool? ?? false,
    );

Map<String, dynamic> _$AchievementUnlockEventToJson(
        AchievementUnlockEvent instance) =>
    <String, dynamic>{
      'achievement_id': instance.achievementId,
      'name': instance.name,
      'rarity': _$AchievementRarityEnumMap[instance.rarity]!,
      'unlocked_at': instance.unlockedAt.toIso8601String(),
      'visual_effect': instance.visualEffect,
      'visual_effect_type':
          _$VisualEffectTypeEnumMap[instance.visualEffectType],
      'rewards': instance.rewards,
      'is_first': instance.isFirst,
    };
