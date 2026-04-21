import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/user/presentation/widgets/srl_phase_badge_card.dart';

void main() {
  testWidgets('srl phase badge hides for unknown phase', (tester) async {
    final parsed = SrlPhaseBadgeCard.fromProfileContext({
      'user_insight_state': {
        'srl_phase': {
          'current_phase': 'UNKNOWN',
        },
      },
    });

    expect(parsed, isNull);
  });

  testWidgets('srl phase badge renders reflection phase copy', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: SrlPhaseBadgeCard(
            phase: 'SELF_REFLECTION',
            helperText: '当前更适合回看阻力、复盘并准备下一轮。',
          ),
        ),
      ),
    );

    expect(find.text('SRL · 复盘中'), findsOneWidget);
    expect(find.text('当前更适合回看阻力、复盘并准备下一轮。'), findsOneWidget);
  });

  test('srl phase parser returns helper text for performance phase', () {
    final parsed = SrlPhaseBadgeCard.fromProfileContext({
      'user_insight_state': {
        'srl_phase': {
          'current_phase': 'PERFORMANCE',
        },
      },
    });

    expect(parsed, isNotNull);
    expect(parsed!['phase'], 'PERFORMANCE');
    expect(parsed['helperText'], contains('执行节奏'));
  });
}
