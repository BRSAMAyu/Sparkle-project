import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/navigation/cold_start_motion.dart';
import 'package:sparkle/features/splash/presentation/screens/splash_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';

/// N20（A-SPEC4）· splash 两段化 + 400ms 预算的 widget 断言。
///
/// 账目口径：段一 logo（scale+fade，即首帧渐显——原 app 级 _ColdStartFade
/// 320ms 已并入此段）；段二 品牌文+副标题+指示器单段渐显。段二与段一
/// 尾部并行；总时长取 ColdStartMotion.splash（scene 档 400ms）。
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  Widget harness() => MaterialApp(
        theme: AppThemes.lightTheme,
        locale: const Locale('zh'),
        localizationsDelegates: const [
          AppLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
        home: const SplashScreen(),
      );

  /// 段二（品牌文组）的 FadeTransition：标题「Sparkle」的最近渐显祖先。
  FadeTransition brandFadeOf(WidgetTester tester) =>
      tester.widget<FadeTransition>(
        find
            .ancestor(
              of: find.text('Sparkle'),
              matching: find.byType(FadeTransition),
            )
            .first,
      );

  FadeTransition logoFadeOf(WidgetTester tester) =>
      tester.widget<FadeTransition>(
        find
            .ancestor(
              of: find.byIcon(Icons.whatshot_rounded),
              matching: find.byType(FadeTransition),
            )
            .first,
      );

  group('SplashScreen 两段化（N20 / D-3）', () {
    testWidgets('两段结构：标题/副标题/指示器同属一个渐显段，logo 独立成段', (tester) async {
      await tester.pumpWidget(harness());
      await tester.pump();

      expect(find.text('Sparkle'), findsOneWidget);
      expect(find.byType(LoadingIndicator), findsOneWidget);
      expect(tester.takeException(), isNull);

      // 段二唯一性：标题与指示器的最近 FadeTransition 是同一个实例。
      final titleFade = tester.widget<FadeTransition>(
        find
            .ancestor(
              of: find.text('Sparkle'),
              matching: find.byType(FadeTransition),
            )
            .first,
      );
      final indicatorFade = tester.widget<FadeTransition>(
        find
            .ancestor(
              of: find.byType(LoadingIndicator),
              matching: find.byType(FadeTransition),
            )
            .first,
      );
      expect(indicatorFade, same(titleFade));

      // 段一存在：logo 有自己的渐显段（与段二不同实例）。
      expect(logoFadeOf(tester), isNot(brandFadeOf(tester)));
      // logo 段还带 scale（原四段中的 scale 并入段一，未丢）。
      final scaleAncestors = find.ancestor(
        of: find.byIcon(Icons.whatshot_rounded),
        matching: find.byType(ScaleTransition),
      );
      expect(scaleAncestors, findsWidgets);
    });

    testWidgets('动画在 400ms（scene 档）内完成——时间预算断言', (tester) async {
      await tester.pumpWidget(harness());
      await tester.pump(const Duration(milliseconds: 50));

      // 起步段：logo 已开始渐显，段二（0.35 起）尚未开始。
      expect(brandFadeOf(tester).opacity.value, lessThan(0.05));

      // 冷启动总预算内：两段全部到位。
      await tester.pump(ColdStartMotion.splash);
      expect(brandFadeOf(tester).opacity.value, closeTo(1.0, 0.001));
      expect(logoFadeOf(tester).opacity.value, closeTo(1.0, 0.001));
    });

    testWidgets('reduce-motion：splash 动画即时完成，不停留', (tester) async {
      tester.platformDispatcher.accessibilityFeaturesTestValue =
          const FakeAccessibilityFeatures(disableAnimations: true);
      addTearDown(
        tester.platformDispatcher.clearAccessibilityFeaturesTestValue,
      );

      await tester.pumpWidget(harness());
      await tester.pump();

      expect(brandFadeOf(tester).opacity.value, closeTo(1.0, 0.001));
      expect(logoFadeOf(tester).opacity.value, closeTo(1.0, 0.001));
    });
  });
}
