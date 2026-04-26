import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/components/atoms/ai_status_capsule.dart';
import 'package:sparkle/core/design/components/atoms/semantic_pill.dart';
import 'package:sparkle/core/design/components/atoms/task_pill.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/shared/entities/task_model.dart';

void main() {
  testWidgets('compact text atoms stay stable with long CJK labels',
      (tester) async {
    tester.view.physicalSize = const Size(320, 640);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      MaterialApp(
        theme: AppThemes.lightTheme,
        darkTheme: AppThemes.darkTheme,
        home: Scaffold(
          body: Center(
            child: SizedBox(
              width: 140,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  SparkleButton.primary(
                    label: '这是一个非常长的按钮标题，需要被安全截断',
                    onPressed: () {},
                    expand: true,
                  ),
                  const SizedBox(height: 12),
                  const TaskPill(
                    type: TaskType.learning,
                    label: '这是一个非常长的任务胶囊标签',
                  ),
                  const SizedBox(height: 12),
                  const SemanticPill(
                    tone: PillTone.brand,
                    label: '这是一个非常长的语义标签胶囊',
                  ),
                  const SizedBox(height: 12),
                  const AiStatusCapsule(
                    label: '这是一个非常长的 AI 状态说明',
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(find.textContaining('这是一个非常长的按钮标题'), findsOneWidget);
    expect(find.textContaining('这是一个非常长的任务胶囊标签'), findsOneWidget);
    expect(find.textContaining('这是一个非常长的语义标签胶囊'), findsOneWidget);
    expect(find.textContaining('这是一个非常长的 AI 状态说明'), findsOneWidget);
  });
}
