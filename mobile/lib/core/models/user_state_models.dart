import 'package:sparkle/core/models/memory_models.dart';

typedef JsonParser<T> = T Function(Map<String, dynamic> json);

class UserStateFieldEnvelope<T> {
  UserStateFieldEnvelope({
    required this.value,
    this.computedAt,
    this.sourceSnapshotIds = const <String>[],
    this.freshnessSeconds = 0,
  });

  factory UserStateFieldEnvelope.fromJson(
    Map<String, dynamic> json,
    JsonParser<T> parser,
  ) {
    final rawValue = json['value'];
    final value = rawValue is Map<String, dynamic>
        ? parser(rawValue)
        : parser(const <String, dynamic>{});
    return UserStateFieldEnvelope<T>(
      value: value,
      computedAt: _parseUserStateDate(json['computed_at']),
      sourceSnapshotIds: (json['source_snapshot_ids'] as List<dynamic>? ?? [])
          .whereType<String>()
          .toList(),
      freshnessSeconds: json['freshness_seconds'] as int? ?? 0,
    );
  }

  final T value;
  final DateTime? computedAt;
  final List<String> sourceSnapshotIds;
  final int freshnessSeconds;
}

class Stage35WorkingMemoryItem {
  Stage35WorkingMemoryItem({
    required this.summary,
    required this.subjectType,
    required this.mentionCount,
    required this.consolidated,
    required this.lastSeenAt,
  });

  factory Stage35WorkingMemoryItem.fromJson(Map<String, dynamic> json) =>
      Stage35WorkingMemoryItem(
        summary: json['summary'] as String? ?? '',
        subjectType: json['subject_type'] as String? ?? 'memory',
        mentionCount: json['mention_count'] as int? ?? 0,
        consolidated: json['consolidated'] as bool? ?? false,
        lastSeenAt: _parseUserStateDate(json['last_seen_at']),
      );

  final String summary;
  final String subjectType;
  final int mentionCount;
  final bool consolidated;
  final DateTime? lastSeenAt;
}

class Stage35WorkingMemorySnapshot {
  Stage35WorkingMemorySnapshot({
    this.activeSessionId,
    this.items = const <Stage35WorkingMemoryItem>[],
  });

  factory Stage35WorkingMemorySnapshot.fromJson(Map<String, dynamic> json) =>
      Stage35WorkingMemorySnapshot(
        activeSessionId: json['active_session_id'] as String?,
        items: (json['items'] as List<dynamic>? ?? [])
            .whereType<Map<String, dynamic>>()
            .map(Stage35WorkingMemoryItem.fromJson)
            .toList(),
      );

  final String? activeSessionId;
  final List<Stage35WorkingMemoryItem> items;
}

class Stage35ActiveSkillItem {
  Stage35ActiveSkillItem({
    required this.skillId,
    required this.name,
    required this.activationMatchScore,
  });

  factory Stage35ActiveSkillItem.fromJson(Map<String, dynamic> json) =>
      Stage35ActiveSkillItem(
        skillId: json['skill_id'] as String? ?? '',
        name: json['name'] as String? ?? '',
        activationMatchScore:
            (json['activation_match_score'] as num?)?.toDouble() ?? 0.0,
      );

  final String skillId;
  final String name;
  final double activationMatchScore;
}

class Stage35ActiveSkillsSummary {
  Stage35ActiveSkillsSummary({this.items = const <Stage35ActiveSkillItem>[]});

  factory Stage35ActiveSkillsSummary.fromJson(Map<String, dynamic> json) =>
      Stage35ActiveSkillsSummary(
        items: (json['items'] as List<dynamic>? ?? [])
            .whereType<Map<String, dynamic>>()
            .map(Stage35ActiveSkillItem.fromJson)
            .toList(),
      );

  final List<Stage35ActiveSkillItem> items;
}

class Stage35AchievementUnlock {
  Stage35AchievementUnlock({
    required this.achievementId,
    required this.name,
    required this.rarity,
    this.unlockedAt,
  });

  factory Stage35AchievementUnlock.fromJson(Map<String, dynamic> json) =>
      Stage35AchievementUnlock(
        achievementId: json['achievement_id'] as String? ?? '',
        name: json['name'] as String? ?? '',
        rarity: json['rarity'] as String? ?? 'common',
        unlockedAt: _parseUserStateDate(json['unlocked_at']),
      );

  final String achievementId;
  final String name;
  final String rarity;
  final DateTime? unlockedAt;
}

class Stage35AchievementProgress {
  Stage35AchievementProgress({
    required this.achievementId,
    required this.name,
    required this.progress,
  });

  factory Stage35AchievementProgress.fromJson(Map<String, dynamic> json) =>
      Stage35AchievementProgress(
        achievementId: json['achievement_id'] as String? ?? '',
        name: json['name'] as String? ?? '',
        progress: (json['progress'] as num?)?.toDouble() ?? 0.0,
      );

  final String achievementId;
  final String name;
  final double progress;
}

class Stage35AchievementSummary {
  Stage35AchievementSummary({
    this.recentUnlocks = const <Stage35AchievementUnlock>[],
    this.inProgressAchievements = const <Stage35AchievementProgress>[],
    this.totalAchievementScore = 0.0,
  });

  factory Stage35AchievementSummary.fromJson(Map<String, dynamic> json) =>
      Stage35AchievementSummary(
        recentUnlocks: (json['recent_unlocks'] as List<dynamic>? ?? [])
            .whereType<Map<String, dynamic>>()
            .map(Stage35AchievementUnlock.fromJson)
            .toList(),
        inProgressAchievements:
            (json['in_progress_achievements'] as List<dynamic>? ?? [])
                .whereType<Map<String, dynamic>>()
                .map(Stage35AchievementProgress.fromJson)
                .toList(),
        totalAchievementScore:
            (json['total_achievement_score'] as num?)?.toDouble() ?? 0.0,
      );

  final List<Stage35AchievementUnlock> recentUnlocks;
  final List<Stage35AchievementProgress> inProgressAchievements;
  final double totalAchievementScore;
}

class Stage35EngagementState {
  Stage35EngagementState({
    this.lastActiveAt,
    this.sessionCount7d = 0,
    this.streak = 0,
  });

  factory Stage35EngagementState.fromJson(Map<String, dynamic> json) =>
      Stage35EngagementState(
        lastActiveAt: _parseUserStateDate(json['last_active_at']),
        sessionCount7d: json['session_count_7d'] as int? ?? 0,
        streak: json['streak'] as int? ?? 0,
      );

  final DateTime? lastActiveAt;
  final int sessionCount7d;
  final int streak;
}

class Stage35MetacognitionDimension {
  Stage35MetacognitionDimension({
    required this.dim,
    required this.sampleSize,
    required this.biasMean,
    required this.trend,
  });

  factory Stage35MetacognitionDimension.fromJson(Map<String, dynamic> json) =>
      Stage35MetacognitionDimension(
        dim: json['dim'] as String? ?? '',
        sampleSize: json['sample_size'] as int? ?? 0,
        biasMean: (json['bias_mean'] as num?)?.toDouble() ?? 0.0,
        trend: json['trend'] as String? ?? 'stable',
      );

  final String dim;
  final int sampleSize;
  final double biasMean;
  final String trend;
}

class Stage35MetacognitionProfile {
  Stage35MetacognitionProfile({
    this.items = const <Stage35MetacognitionDimension>[],
  });

  factory Stage35MetacognitionProfile.fromJson(Map<String, dynamic> json) =>
      Stage35MetacognitionProfile(
        items: (json['items'] as List<dynamic>? ?? [])
            .whereType<Map<String, dynamic>>()
            .map(Stage35MetacognitionDimension.fromJson)
            .toList(),
      );

  final List<Stage35MetacognitionDimension> items;
}

class UserStateV1Model {
  UserStateV1Model({
    this.schemaVersion,
    this.workingMemorySnapshot,
    this.achievementSummary,
    this.activeSkillsSummary,
    this.engagementState,
    this.foresightHint,
    this.metacognitionProfile,
  });

  factory UserStateV1Model.fromJson(Map<String, dynamic> json) =>
      UserStateV1Model(
        schemaVersion: json['schema_version'] as String?,
        workingMemorySnapshot: _parseEnvelope(
          json['working_memory_snapshot'],
          Stage35WorkingMemorySnapshot.fromJson,
        ),
        achievementSummary: _parseEnvelope(
          json['achievement_summary'],
          Stage35AchievementSummary.fromJson,
        ),
        activeSkillsSummary: _parseEnvelope(
          json['active_skills_summary'],
          Stage35ActiveSkillsSummary.fromJson,
        ),
        engagementState: _parseEnvelope(
          json['engagement_state'],
          Stage35EngagementState.fromJson,
        ),
        foresightHint: _parseEnvelope(
          json['foresight_hint'],
          ForesightHintSummaryItem.fromJson,
        ),
        metacognitionProfile: _parseEnvelope(
          json['metacognition_profile'],
          Stage35MetacognitionProfile.fromJson,
        ),
      );

  factory UserStateV1Model.fromProfileContext(
    Map<String, dynamic> profileContext,
  ) {
    final payload = _asMap(profileContext['user_state_v1']);
    final mergedPayload = <String, dynamic>{
      ...payload,
      if (!payload.containsKey('metacognition_profile'))
        'metacognition_profile': profileContext['metacognition_profile'],
    };
    return UserStateV1Model.fromJson(mergedPayload);
  }

  final String? schemaVersion;
  final UserStateFieldEnvelope<Stage35WorkingMemorySnapshot>?
      workingMemorySnapshot;
  final UserStateFieldEnvelope<Stage35AchievementSummary>? achievementSummary;
  final UserStateFieldEnvelope<Stage35ActiveSkillsSummary>? activeSkillsSummary;
  final UserStateFieldEnvelope<Stage35EngagementState>? engagementState;
  final UserStateFieldEnvelope<ForesightHintSummaryItem>? foresightHint;
  final UserStateFieldEnvelope<Stage35MetacognitionProfile>?
      metacognitionProfile;

  bool get hasAnyStage35CardData =>
      (workingMemorySnapshot?.value.items.isNotEmpty ?? false) ||
      (achievementSummary?.value.recentUnlocks.isNotEmpty ?? false) ||
      (achievementSummary?.value.inProgressAchievements.isNotEmpty ?? false) ||
      (activeSkillsSummary?.value.items.isNotEmpty ?? false) ||
      (engagementState?.value.sessionCount7d ?? 0) > 0 ||
      (engagementState?.value.streak ?? 0) > 0 ||
      ((foresightHint?.value.hintText ?? '').isNotEmpty);
}

UserStateFieldEnvelope<T>? _parseEnvelope<T>(
  dynamic raw,
  JsonParser<T> parser,
) {
  final json = _asMap(raw);
  if (json.isEmpty) {
    return null;
  }
  return UserStateFieldEnvelope<T>.fromJson(json, parser);
}

Map<String, dynamic> _asMap(dynamic value) {
  if (value is Map<String, dynamic>) {
    return value;
  }
  if (value is Map) {
    return value.map((key, dynamic item) => MapEntry(key.toString(), item));
  }
  return const <String, dynamic>{};
}

DateTime? _parseUserStateDate(dynamic value) {
  if (value == null) {
    return null;
  }
  if (value is DateTime) {
    return value;
  }
  return DateTime.tryParse(value.toString());
}
