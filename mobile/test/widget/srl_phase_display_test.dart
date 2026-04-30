import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/user/presentation/widgets/srl_phase_badge_card.dart';

void main() {
  testWidgets('srl phase badge hides for unknown phase', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: _SrlTestHelper(
          profileContext: {
            'user_insight_state': {
              'srl_phase': {
                'current_phase': 'UNKNOWN',
              },
            },
          },
        ),
      ),
    );
    await tester.pump();
    // Should find no SrlPhaseBadgeCard since phase is UNKNOWN
    expect(find.byType(SrlPhaseBadgeCard), findsNothing);
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

  testWidgets('srl phase parser returns helper text for performance phase',
      (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: _SrlParseTestHelper(
          profileContext: {
            'user_insight_state': {
              'srl_phase': {
                'current_phase': 'PERFORMANCE',
              },
            },
          },
        ),
      ),
    );
    await tester.pump();
    // The helper test widget will find the parsed result
    expect(find.byType(_SrlParseResult), findsOneWidget);
    final resultWidget =
        tester.widget<_SrlParseResult>(find.byType(_SrlParseResult));
    expect(resultWidget.result, isNotNull);
    expect(resultWidget.result!['phase'], 'PERFORMANCE');
    expect(resultWidget.result!['helperText'], contains('执行节奏'));
  });
}

class _SrlTestHelper extends StatelessWidget {
  const _SrlTestHelper({required this.profileContext});
  final Map<String, dynamic> profileContext;

  @override
  Widget build(BuildContext context) {
    final parsed =
        SrlPhaseBadgeCard.fromProfileContext(context, profileContext);
    if (parsed == null) return const SizedBox.shrink();
    return SrlPhaseBadgeCard(
      phase: parsed['phase']!,
      helperText: parsed['helperText']!,
    );
  }
}

class _SrlParseTestHelper extends StatelessWidget {
  const _SrlParseTestHelper({required this.profileContext});
  final Map<String, dynamic> profileContext;

  @override
  Widget build(BuildContext context) {
    final result =
        SrlPhaseBadgeCard.fromProfileContext(context, profileContext);
    return _SrlParseResult(result: result);
  }
}

class _SrlParseResult extends StatelessWidget {
  const _SrlParseResult({super.key, required this.result});
  final Map<String, String>? result;

  @override
  Widget build(BuildContext context) => const SizedBox.shrink();
}
