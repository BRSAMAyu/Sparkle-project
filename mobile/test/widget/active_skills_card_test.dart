import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/models/user_state_models.dart';
import 'package:sparkle/features/user/presentation/widgets/active_skills_card.dart';

void main() {
  testWidgets('ActiveSkillsCard renders activated skill chips', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ActiveSkillsCard(
            summary: UserStateFieldEnvelope(
              value: Stage35ActiveSkillsSummary(
                items: [
                  Stage35ActiveSkillItem(
                    skillId: 'chunking',
                    name: '分块推进',
                    activationMatchScore: 0.92,
                  ),
                  Stage35ActiveSkillItem(
                    skillId: 'replan',
                    name: '轻量重排',
                    activationMatchScore: 0.78,
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );

    expect(find.text('当前激活技能'), findsOneWidget);
    expect(find.text('分块推进 92%'), findsOneWidget);
    expect(find.text('轻量重排 78%'), findsOneWidget);
  });
}
