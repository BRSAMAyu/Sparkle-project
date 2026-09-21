// U-01 Step 1 关键屏断言（chat 面 · ActionChip → SemanticPill 迁移）：
// GrowthCard 的行动 pill 语义/可点性保持——继续类动作映射 success tone、
// 「我累了」dismiss 映射 neutral tone、点击仍回调 onAction。
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/components/atoms/semantic_pill.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/chat/presentation/widgets/growth_card.dart';
import 'package:sparkle/l10n/app_localizations.dart';

Future<void> _pumpCard(
  WidgetTester tester,
  ValueChanged<String> onAction,
) async {
  tester.view.physicalSize = const Size(400, 900);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  await tester.pumpWidget(
    MaterialApp(
      theme: AppThemes.lightTheme,
      darkTheme: AppThemes.darkTheme,
      locale: const Locale('zh'),
      localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: AppLocalizations.supportedLocales,
      home: Scaffold(
        body: SingleChildScrollView(
          child: GrowthCard(
            title: '坚持的一周',
            narrative: '你连续 7 天完成了晨间专注。',
            streakDays: 7,
            strategyEffect: '挑战节奏保持不变',
            isMilestone: true,
            actions: const ['继续坚持', '我累了'],
            onAction: onAction,
          ),
        ),
      ),
    ),
  );
  // 动画 400ms + 成就触感事件，多泵几帧到稳定。
  await tester.pump(const Duration(milliseconds: 500));
  await tester.pump(const Duration(milliseconds: 100));
}

void main() {
  testWidgets('GrowthCard 行动 pill：tone 语义映射与点击回调保持', (tester) async {
    final tapped = <String>[];
    await _pumpCard(tester, tapped.add);

    final pills = tester.widgetList<SemanticPill>(
      find.byType(SemanticPill),
    ).toList();
    expect(pills.length, 2);

    // 「继续坚持」→ success tone；「我累了」→ neutral（dismiss）tone。
    final continuePill = pills.singleWhere((p) => p.label == '继续坚持');
    final dismissPill = pills.singleWhere((p) => p.label == '我累了');
    expect(continuePill.tone, PillTone.success);
    expect(dismissPill.tone, PillTone.neutral);

    // 可点性保持：点击继续 pill 回调 onAction。
    await tester.tap(find.text('继续坚持'), warnIfMissed: false);
    await tester.pumpAndSettle();
    expect(tapped, ['继续坚持']);
  });
}
