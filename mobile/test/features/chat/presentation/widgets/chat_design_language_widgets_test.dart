import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_design_language_widgets.dart';

import '../../../../shared/i18n_test_helper.dart';

void main() {
  setUp(setUpI18nForTesting);

  test('chat, community, and galaxy avoid hard-coded Material shortcuts', () {
    final offenders = <String>[];
    final hardCodedColor =
        RegExp(r'Colors\.(white|black|red|redAccent|orange|amber)');
    for (final dirPath in const [
      'lib/features/chat',
      'lib/features/community',
      'lib/features/galaxy',
    ]) {
      for (final entity in Directory(dirPath).listSync(recursive: true)) {
        if (entity is! File || !entity.path.endsWith('.dart')) continue;
        final content = entity.readAsStringSync();
        if (hardCodedColor.hasMatch(content)) {
          offenders.add(entity.path);
        }
      }
    }

    expect(offenders, isEmpty);
  });

  testWidgets('quick action chip exposes localized semantics and taps',
      (tester) async {
    var tapped = false;

    await tester.pumpWidget(
      testMaterialApp(
        home: Scaffold(
          body: Center(
            child: ChatQuickActionChip(
              icon: Icons.add_task_rounded,
              label: '创建任务',
              subtitle: '把想法拆成下一步',
              color: DS.brandPrimary,
              isNarrow: false,
              onTap: () => tapped = true,
            ),
          ),
        ),
      ),
    );

    expect(
      find.byWidgetPredicate(
        (widget) => widget is Semantics && widget.properties.label == '创建任务',
      ),
      findsOneWidget,
    );

    await tester.tap(find.byType(ChatQuickActionChip));
    await tester.pumpAndSettle();

    expect(tapped, isTrue);
  });

  testWidgets('context toggle keeps compact labels accessible', (tester) async {
    var tapped = false;

    await tester.pumpWidget(
      testMaterialApp(
        home: Scaffold(
          body: Center(
            child: ChatContextToggle(
              isExpanded: false,
              reasoningLabel: '深度',
              modeLabel: '标准',
              planLabel: '期末计划',
              onTap: () => tapped = true,
            ),
          ),
        ),
      ),
    );

    expect(find.text('深度 · 标准 · 期末计划'), findsOneWidget);
    expect(
      find.byWidgetPredicate(
        (widget) =>
            widget is Semantics && widget.properties.label == '深度, 标准, 期末计划',
      ),
      findsOneWidget,
    );

    await tester.tap(find.byType(ChatContextToggle));
    await tester.pumpAndSettle();

    expect(tapped, isTrue);
  });

  testWidgets('daily startup retry banner exposes retry affordance',
      (tester) async {
    var retryCount = 0;

    await tester.pumpWidget(
      testMaterialApp(
        home: Scaffold(
          body: DailyStartupRetryBanner(
            isRetrying: false,
            onRetry: () => retryCount++,
          ),
        ),
      ),
    );

    expect(find.text('加载今日概览中…'), findsOneWidget);
    expect(find.byTooltip('重试今日概览'), findsOneWidget);

    await tester.tap(find.byTooltip('重试今日概览'));
    await tester.pumpAndSettle();

    expect(retryCount, 1);
  });

  testWidgets('chat polish widgets render in dark mode', (tester) async {
    const goldenKey = Key('chat-design-language-dark');

    await tester.pumpWidget(
      testMaterialApp(
        theme: AppThemes.darkTheme,
        home: RepaintBoundary(
          key: goldenKey,
          child: Scaffold(
            body: SizedBox(
              width: 420,
              height: 320,
              child: Padding(
                padding: const EdgeInsets.all(DS.spacing16),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const ChatNewMessagesDivider(),
                    const SizedBox(height: DS.spacing16),
                    ChatContextToggle(
                      isExpanded: true,
                      reasoningLabel: '深度',
                      modeLabel: '标准',
                      planLabel: '期末计划',
                      onTap: () {},
                    ),
                    const SizedBox(height: DS.spacing16),
                    DailyStartupRetryBanner(
                      isRetrying: false,
                      onRetry: () {},
                    ),
                    const SizedBox(height: DS.spacing16),
                    ChatQuickActionChip(
                      icon: Icons.cloud_sync_rounded,
                      label: '交给 OpenClaw',
                      subtitle: '适合跨应用动作',
                      color: DS.info,
                      isNarrow: false,
                      onTap: () {},
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );

    await expectLater(
      find.byKey(goldenKey),
      matchesGoldenFile('goldens/chat_design_language_dark.png'),
    );
  });
}
