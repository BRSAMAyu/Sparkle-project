import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/user/data/repositories/user_repository.dart';
import 'package:sparkle/features/user/presentation/screens/profile_transparent.dart';
import '../../shared/i18n_test_helper.dart';

class _FakeUserRepository implements UserRepository {
  final List<Map<String, dynamic>> controlCalls = <Map<String, dynamic>>[];

  @override
  Future<Map<String, dynamic>> fetchProfileContext() async => <String, dynamic>{
        'knowledge_summary': {
          'overall_mastery': 0.61,
          'active_learning_subjects': ['physics'],
        },
        'cognitive_summary': {
          'active_patterns': ['structured'],
        },
        'user_insight_state': {
          'current_state': {'focus': 'exam prep'},
          'readiness': {'energy': 0.6},
        },
        'user_insight_transparency': {
          'claims': [
            {
              'id': 'achievement_motivation_response',
              'label': 'Achievement motivation response',
              'value': 'progress_praise',
              'family': 'achievement',
              'freshness': 'medium',
              'confidence': 0.82,
              'controls': ['wrong', 'exam_mode_only'],
              'explanation': 'Derived from recent reward response.',
            },
          ],
          'unknowns': [
            {
              'id': 'capacity_hours',
              'description': 'Reliable time-capacity data is still missing.',
            },
          ],
          'calibration': {
            'calibration_posture': 'stable',
          },
          'current_profile': {
            'current_state': {'focus': 'exam prep'},
          },
        },
      };

  @override
  Future<void> submitInsightControl(Map<String, dynamic> payload) async {
    controlCalls.add(payload);
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {

  setUp(setUpI18nForTesting);
  testWidgets(
    'profile transparent screen renders canonical transparency payload and submits control actions',
    (tester) async {
      tester.view.physicalSize = const Size(1200, 2200);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      final repo = _FakeUserRepository();

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            userRepositoryProvider.overrideWithValue(repo),
          ],
          child: testMaterialApp(
            home: ProfileTransparentScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('progress_praise', skipOffstage: false), findsWidgets);
      expect(
          find.textContaining('Calibration posture: stable'), findsOneWidget);
      expect(
        find.textContaining(
          'Reliable time-capacity data is still missing.',
          skipOffstage: false,
        ),
        findsOneWidget,
      );

      final wrongButton = find
          .widgetWithText(
            OutlinedButton,
            '标记不准确',
            skipOffstage: false,
          )
          .first;
      await tester.tap(wrongButton);
      await tester.pumpAndSettle();

      expect(repo.controlCalls, hasLength(1));
      expect(repo.controlCalls.single['target_id'],
          'achievement_motivation_response');
      expect(repo.controlCalls.single['action'], 'wrong');
    },
  );
}
