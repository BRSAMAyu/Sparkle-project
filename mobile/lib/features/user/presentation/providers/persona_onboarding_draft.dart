import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// J-02（A-SPEC8B §5 改造 #3 / N50 前半）· persona 引导进度断点续存。
///
/// 背景（A-SPEC8B G7）：persona 5 步引导的 `_currentStep` 与各选择项原为
/// 纯本地 state，中途退出/杀进程后重进从第 0 步重填——对 13-15 决策点的
/// 引导长链是复利性摩擦。本 store 把草稿按 per-user key 落 SharedPreferences
/// （形制对照 settings_provider.dart 的 `kOnboardingCompletedKey_$userId`，
/// 持久化入口同为 `SharedPreferences.getInstance()`），重进时恢复到断点步
/// 与已填内容；跳过/提交成功即清除。
///
/// 边界：仅持久化「未提交的草稿」，不含任何服务端画像写入；userId 为空时
/// 不持久化（引导链由路由守卫保证已认证，此处为防御式降级）。
class PersonaOnboardingDraft {
  const PersonaOnboardingDraft({
    required this.step,
    required this.goalType,
    required this.goalText,
    required this.learningStyle,
    required this.knowledgeLevel,
    required this.studyMinutes,
    required this.depthPreference,
    required this.curiosityPreference,
  });

  factory PersonaOnboardingDraft.fromJson(Map<String, dynamic> json) =>
      PersonaOnboardingDraft(
        step: (json['step'] as num?)?.toInt() ?? 0,
        goalType: json['goal_type'] as String? ?? 'exam',
        goalText: json['goal_text'] as String? ?? '',
        learningStyle: json['learning_style'] as String? ?? 'balanced',
        knowledgeLevel: json['knowledge_level'] as String? ?? 'beginner',
        studyMinutes: (json['study_minutes'] as num?)?.toDouble() ?? 60,
        depthPreference: (json['depth_preference'] as num?)?.toDouble() ?? 0.5,
        curiosityPreference:
            (json['curiosity_preference'] as num?)?.toDouble() ?? 0.5,
      );

  final int step;
  final String goalType;
  final String goalText;
  final String learningStyle;
  final String knowledgeLevel;
  final double studyMinutes;
  final double depthPreference;
  final double curiosityPreference;

  Map<String, dynamic> toJson() => <String, dynamic>{
        'step': step,
        'goal_type': goalType,
        'goal_text': goalText,
        'learning_style': learningStyle,
        'knowledge_level': knowledgeLevel,
        'study_minutes': studyMinutes,
        'depth_preference': depthPreference,
        'curiosity_preference': curiosityPreference,
      };

  /// 屏内恢复时的安全钳位：步数越界（草稿来自旧版本/损坏数据）回落到
  /// 合法区间，滑杆值钳到屏内既有 min/max 范围。
  PersonaOnboardingDraft clamp({
    int maxStep = 4,
    double minStudyMinutes = 10,
    double maxStudyMinutes = 180,
  }) {
    double clampValue(double v, double min, double max) {
      if (v.isNaN || v < min) return min;
      if (v > max) return max;
      return v;
    }

    int clampStep(int v) {
      if (v < 0) return 0;
      if (v > maxStep) return maxStep;
      return v;
    }

    return PersonaOnboardingDraft(
      step: clampStep(step),
      goalType: goalType,
      goalText: goalText,
      learningStyle: learningStyle,
      knowledgeLevel: knowledgeLevel,
      studyMinutes: clampValue(studyMinutes, minStudyMinutes, maxStudyMinutes),
      depthPreference: clampValue(depthPreference, 0, 1),
      curiosityPreference: clampValue(curiosityPreference, 0, 1),
    );
  }
}

class PersonaOnboardingDraftStore {
  PersonaOnboardingDraftStore({SharedPreferences? prefs})
      : _prefsOverride = prefs;

  static const String _keyPrefix = 'onboarding_persona_draft';

  final SharedPreferences? _prefsOverride;

  /// 测试经 SharedPreferences.setMockInitialValues 注入；生产走默认实例
  /// （与 settings_provider 同一形制）。
  Future<SharedPreferences> _resolvePrefs() async {
    final override = _prefsOverride;
    if (override != null) return override;
    return SharedPreferences.getInstance();
  }

  static String keyForUser(String userId) => '${_keyPrefix}_$userId';

  Future<PersonaOnboardingDraft?> load(String userId) async {
    final prefs = await _resolvePrefs();
    final raw = prefs.getString(keyForUser(userId));
    if (raw == null || raw.isEmpty) return null;
    try {
      final decoded = jsonDecode(raw);
      if (decoded is! Map<String, dynamic>) return null;
      return PersonaOnboardingDraft.fromJson(decoded);
    } catch (_) {
      // 草稿损坏即视为无草稿，回到首步（宁可重填，不引导进坏状态）。
      return null;
    }
  }

  Future<void> save(String userId, PersonaOnboardingDraft draft) async {
    final prefs = await _resolvePrefs();
    await prefs.setString(keyForUser(userId), jsonEncode(draft.toJson()));
  }

  Future<void> clear(String userId) async {
    final prefs = await _resolvePrefs();
    await prefs.remove(keyForUser(userId));
  }
}

final personaOnboardingDraftStoreProvider =
    Provider<PersonaOnboardingDraftStore>(
  (ref) => PersonaOnboardingDraftStore(),
);
