import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/l10n/app_localizations.dart';

import '../../shared/i18n_test_helper.dart';

/// U-01 Step 3：LoadingIndicator owner 扩展参数测试。
///
/// Step 3 为承载 9 surface 的裸 CircularProgressIndicator/LinearProgressIndicator
/// 迁移，对 owner 做了最小扩展：strokeWidth / value / backgroundColor /
/// liveRegion / strokeCap（circular）与 size(minHeight) / borderRadius（linear）。
/// 本套件固定：默认参数与历史行为逐字一致，扩展参数逐项透传到平台控件。
void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  Widget shell(Widget child) => MaterialApp(
        theme: AppThemes.lightTheme,
        darkTheme: AppThemes.darkTheme,
        localizationsDelegates: const [
          ...AppLocalizations.localizationsDelegates,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
        home: Scaffold(body: Center(child: child)),
      );

  testWidgets(
      'circular defaults keep historical rendering (40px / sw 3 / '
      'indeterminate / liveRegion)', (tester) async {
    await tester.pumpWidget(shell(LoadingIndicator.circular()));

    final box = tester.widget<SizedBox>(
      find
          .descendant(
            of: find.byType(LoadingIndicator),
            matching: find.byType(SizedBox),
          )
          .first,
    );
    expect(box.width, 40.0);
    expect(box.height, 40.0);

    final cpi = tester.widget<CircularProgressIndicator>(
      find.byType(CircularProgressIndicator),
    );
    expect(cpi.strokeWidth, 3.0);
    expect(cpi.value, isNull, reason: '默认为不确定态加载');
    expect(
      (cpi.valueColor as AlwaysStoppedAnimation<Color>).value,
      DS.primaryBase,
    );
    expect(cpi.backgroundColor, isNull);

    final semantics = tester.getSemantics(find.byType(LoadingIndicator));
    expect(
      semantics.flagsCollection.isLiveRegion,
      isTrue,
      reason: '默认 liveRegion 与历史行为一致',
    );
    // label 契约 = l10n.commonLoading（locale 无关断言）
    final context = tester.element(find.byType(LoadingIndicator));
    expect(semantics.label, AppLocalizations.of(context)!.commonLoading);
  });

  testWidgets(
      'circular inline params pass through (size/strokeWidth/color/'
      'liveRegion:false)', (tester) async {
    await tester.pumpWidget(
      shell(
        LoadingIndicator.circular(
          size: 12,
          strokeWidth: 2,
          color: DS.warning,
          liveRegion: false,
        ),
      ),
    );

    final box = tester.widget<SizedBox>(
      find
          .descendant(
            of: find.byType(LoadingIndicator),
            matching: find.byType(SizedBox),
          )
          .first,
    );
    expect(box.width, 12.0);
    expect(box.height, 12.0);

    final cpi = tester.widget<CircularProgressIndicator>(
      find.byType(CircularProgressIndicator),
    );
    expect(cpi.strokeWidth, 2.0);
    expect((cpi.valueColor as AlwaysStoppedAnimation<Color>).value, DS.warning);

    final semantics = tester.getSemantics(find.byType(LoadingIndicator));
    expect(
      semantics.flagsCollection.isLiveRegion,
      isFalse,
      reason: '内联在已带语义标签控件内时不应作为 liveRegion 播报',
    );
  });

  testWidgets('determinate ring passes value/backgroundColor/strokeCap',
      (tester) async {
    await tester.pumpWidget(
      shell(
        LoadingIndicator.circular(
          value: 0.42,
          size: 36,
          strokeWidth: 3,
          backgroundColor: DS.surfaceHigh,
          strokeCap: StrokeCap.round,
          liveRegion: false,
        ),
      ),
    );

    final cpi = tester.widget<CircularProgressIndicator>(
      find.byType(CircularProgressIndicator),
    );
    expect(cpi.value, 0.42);
    expect(cpi.backgroundColor, DS.surfaceHigh);
    expect(cpi.strokeCap, StrokeCap.round);
  });

  testWidgets('linear defaults keep historical track color DS.neutral200',
      (tester) async {
    await tester.pumpWidget(shell(LoadingIndicator.linear()));

    final lpi = tester.widget<LinearProgressIndicator>(
      find.byType(LinearProgressIndicator),
    );
    expect(lpi.value, isNull);
    expect(lpi.minHeight, isNull, reason: 'null 走主题默认厚度');
    expect(lpi.backgroundColor, DS.neutral200);
  });

  testWidgets(
      'linear determinate passes value/minHeight/backgroundColor/'
      'borderRadius', (tester) async {
    const radius = BorderRadius.all(Radius.circular(2));
    await tester.pumpWidget(
      shell(
        LoadingIndicator.linear(
          value: 0.25,
          size: 6,
          backgroundColor: DS.surfaceTertiary,
          color: DS.success,
          borderRadius: radius,
          liveRegion: false,
        ),
      ),
    );

    final lpi = tester.widget<LinearProgressIndicator>(
      find.byType(LinearProgressIndicator),
    );
    expect(lpi.value, 0.25);
    expect(lpi.minHeight, 6.0);
    expect(lpi.backgroundColor, DS.surfaceTertiary);
    expect((lpi.valueColor as AlwaysStoppedAnimation<Color>).value, DS.success);
    expect(lpi.borderRadius, radius);
  });

  testWidgets('showText keeps label + text rendering', (tester) async {
    await tester.pumpWidget(
      shell(
        LoadingIndicator.circular(showText: true, loadingText: '生成中'),
      ),
    );

    expect(find.text('生成中'), findsOneWidget);
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    final semantics = tester.getSemantics(find.byType(LoadingIndicator));
    expect(semantics.label, contains('生成中'), reason: '容器 label 与内嵌文本合并播报');
  });
}
