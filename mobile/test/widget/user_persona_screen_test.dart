import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/features/user/data/repositories/user_repository.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';
import 'package:sparkle/features/user/presentation/screens/user_persona_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/user_model.dart';

class _FakeUserRepository implements UserRepository {
  _FakeUserRepository({
    Map<String, dynamic>? transparentProfile,
    Map<String, dynamic>? profileContext,
    List<Map<String, dynamic>>? inferredPreferences,
    List<Map<String, dynamic>>? activePolicies,
    this.inferredPreferencesError,
    this.resetOverrideError,
  })  : _transparentProfile = transparentProfile ??
            <String, dynamic>{
              'layer_1': {
                'preferences': [
                  {
                    'key': 'response_style',
                    'value': 'concise',
                    'metadata': {'level': 'editable', 'reason': 'user choice'},
                  },
                ],
                'goals': [
                  {
                    'id': 'goal_1',
                    'title': '掌握数据结构',
                    'status': 'active',
                    'metadata': {'level': 'editable', 'reason': 'current goal'},
                  },
                ],
              },
              'layer_2': {
                'persona': {
                  'tags': ['deep-thinker'],
                  'capabilities': {'mastery_avg': 0.72},
                },
              },
              'layer_3': {
                'patterns': [
                  {
                    'name': 'Idealistic Scheduling Loop',
                    'metadata': {'level': 'readonly'}
                  },
                ],
                'fragments': [
                  {
                    'content': '喜欢先拆框架再执行',
                    'metadata': {'level': 'readonly'}
                  },
                ],
              },
            },
        _profileContext = profileContext ??
            <String, dynamic>{
              'preferences': {'response_style': 'concise'},
              'preference_version': 12,
              'knowledge_summary': {
                'overall_mastery': 0.81,
                'weak_spots': ['概率论'],
                'recent_mastery_changes': <dynamic>[],
                'active_learning_subjects': ['数据结构'],
              },
              'cognitive_summary': {
                'active_patterns': ['Idealistic Scheduling Loop'],
                'dominant_pattern_type': 'planning',
                'risk_signals': ['task_switching'],
              },
            },
        _inferredPreferences = inferredPreferences ??
            <Map<String, dynamic>>[
              {
                'key': 'social_learning_preference',
                'value': 0.2,
                'source': 'system',
                'adjustable': true,
                'overridden': true,
                'explanation': 'Based on recent collaboration behavior',
              },
            ],
        _activePolicies = activePolicies ??
            <Map<String, dynamic>>[
              {
                'signal': 'pace_control',
                'effect': 'slow_down_and_focus',
                'source_pattern': 'task_switching',
              },
            ];

  final Map<String, dynamic> _transparentProfile;
  final Map<String, dynamic> _profileContext;
  final List<Map<String, dynamic>> _inferredPreferences;
  final List<Map<String, dynamic>> _activePolicies;
  final Object? inferredPreferencesError;
  final Object? resetOverrideError;

  final List<String> resetOverrideCalls = <String>[];

  @override
  Future<Map<String, dynamic>> fetchTransparentProfile() async =>
      _transparentProfile;

  @override
  Future<Map<String, dynamic>> fetchProfileContext() async => _profileContext;

  @override
  Future<List<Map<String, dynamic>>> fetchInferredPreferences() async {
    if (inferredPreferencesError != null) {
      throw inferredPreferencesError!;
    }
    return _inferredPreferences;
  }

  @override
  Future<List<Map<String, dynamic>>> fetchActivePolicies() async =>
      _activePolicies;

  @override
  Future<void> resetInferredOverride(String key) async {
    if (resetOverrideError != null) {
      throw resetOverrideError!;
    }
    resetOverrideCalls.add(key);
  }

  @override
  Future<void> overrideInferredPreference({
    required String key,
    required value,
    String? reason,
  }) async {}

  @override
  Future<void> rollbackTransparentPreference(String prefKey) async {}

  @override
  Future<void> submitOnboarding(Map<String, dynamic> payload) async {}

  @override
  Future<void> submitProfileCorrection(Map<String, dynamic> payload) async {}

  @override
  Future<List<Map<String, dynamic>>> fetchSystemUpdates(
          {int limit = 50, int offset = 0}) async =>
      <Map<String, dynamic>>[];

  @override
  Future<void> updateTransparentPreference(
      {required String prefKey, required value}) async {}

  @override
  Future<void> updateGoal(
      {required String goalId, String? title, String? status}) async {}

  @override
  Future<Map<String, dynamic>> fetchUserSettings() async => <String, dynamic>{};

  @override
  Future<void> updateUserSettings(Map<String, dynamic> payload) async {}

  @override
  Future<UserModel> updateUserPreferences(UserPreferences preferences) {
    throw UnimplementedError();
  }

  @override
  Future<UserModel> updatePushPreferences(PushPreferences prefs) {
    throw UnimplementedError();
  }

  @override
  Future<UserModel> updateSchedulePreferences(
      Map<String, dynamic> scheduleData) {
    throw UnimplementedError();
  }
}

Widget _buildTestApp(_FakeUserRepository repository) {
  return ProviderScope(
    overrides: [
      userRepositoryProvider.overrideWithValue(repository),
    ],
    child: MaterialApp(
      home: const UserPersonaScreen(),
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      locale: const Locale('zh'),
    ),
  );
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues(<String, Object>{
      kOnboardingCompletedKey: true,
    });
  });

  testWidgets(
      'persona screen renders context snapshot and inferred preferences',
      (WidgetTester tester) async {
    final repository = _FakeUserRepository();

    await tester.pumpWidget(_buildTestApp(repository));
    await tester.pumpAndSettle();

    expect(find.text('Context Snapshot'), findsOneWidget);
    expect(find.textContaining('Preference Version: 12'), findsOneWidget);
    expect(
        find.textContaining('Knowledge Summary: mastery=0.81'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.text('Inferred Preferences'),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.pumpAndSettle();
    expect(find.text('Inferred Preferences'), findsOneWidget);
    expect(
        find.textContaining('social_learning_preference: 0.2'), findsOneWidget);
    expect(find.text('Reset'), findsOneWidget);
  });

  testWidgets(
      'persona screen shows section error instead of silent empty state',
      (WidgetTester tester) async {
    final repository = _FakeUserRepository(
      inferredPreferencesError: Exception('inferred fetch failed'),
    );

    await tester.pumpWidget(_buildTestApp(repository));
    await tester.pumpAndSettle();

    await tester.scrollUntilVisible(
      find.text('Inferred Preferences'),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.pumpAndSettle();
    expect(find.text('Inferred Preferences'), findsOneWidget);
    expect(find.textContaining('加载失败：inferred fetch failed'), findsOneWidget);
    expect(find.text('重试'), findsWidgets);
  });

  testWidgets('reset override triggers repository and shows success feedback',
      (WidgetTester tester) async {
    final repository = _FakeUserRepository();

    await tester.pumpWidget(_buildTestApp(repository));
    await tester.pumpAndSettle();

    await tester.scrollUntilVisible(
      find.text('Reset'),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('Reset'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(
        repository.resetOverrideCalls, <String>['social_learning_preference']);
    expect(find.text('已恢复系统推断值'), findsOneWidget);
  });

  testWidgets('reset override failure shows error feedback',
      (WidgetTester tester) async {
    final repository = _FakeUserRepository(
      resetOverrideError: Exception('reset failed'),
    );

    await tester.pumpWidget(_buildTestApp(repository));
    await tester.pumpAndSettle();

    await tester.scrollUntilVisible(
      find.text('Reset'),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('Reset'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('恢复失败：reset failed'), findsOneWidget);
  });
}
