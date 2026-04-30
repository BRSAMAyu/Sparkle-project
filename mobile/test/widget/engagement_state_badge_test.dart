import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/models/user_state_models.dart';
import 'package:sparkle/features/user/presentation/widgets/engagement_state_badge.dart';
import '../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  testWidgets('EngagementStateBadge renders engagement chips', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: EngagementStateBadge(
            state: UserStateFieldEnvelope(
              value: Stage35EngagementState(
                lastActiveAt: DateTime(2026, 4, 22, 9, 50),
                sessionCount7d: 6,
                streak: 4,
              ),
            ),
          ),
        ),
      ),
    );

    expect(find.text('参与状态'), findsOneWidget);
    expect(find.text('7日会话 6'), findsOneWidget);
    expect(find.text('连续 4 天'), findsOneWidget);
    expect(find.text('最近 4月22日'), findsOneWidget);
  });
}
