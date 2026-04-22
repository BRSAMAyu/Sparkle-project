import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/core/models/user_state_models.dart';
import 'package:sparkle/features/user/presentation/widgets/foresight_card.dart';

void main() {
  testWidgets('ForesightCard renders hint and confidence chips', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ForesightCard(
            hint: UserStateFieldEnvelope(
              value: ForesightHintSummaryItem(
                hintText: '你今天后半段更容易被切碎，先把最难的一题压到午前完成。',
                generatedAt: DateTime(2026, 4, 22, 9, 55),
                deviationCount: 2,
                attractorConfidences: [
                  ForesightConfidenceItem(
                    dim: 'execution_stability',
                    confidence: 0.84,
                  ),
                  ForesightConfidenceItem(
                    dim: 'overload_risk',
                    confidence: 0.66,
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );

    expect(find.text('前瞻提示'), findsOneWidget);
    expect(find.text('你今天后半段更容易被切碎，先把最难的一题压到午前完成。'), findsOneWidget);
    expect(find.textContaining('偏离 2 个'), findsOneWidget);
    expect(find.text('执行稳定度 0.84'), findsOneWidget);
    expect(find.text('过载风险 0.66'), findsOneWidget);
  });
}
