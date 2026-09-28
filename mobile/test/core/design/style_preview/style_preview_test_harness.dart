// V4-F05 · style_preview 测试公共泵制：真实主题管道宿主。
//
// 宿主与 app.dart 同机制：AnimatedBuilder(ThemeManager) → MaterialApp
// （AppThemes.lightTheme 每次重建时经 ThemeManager 单例重估，等价于应用
// 根部 themeManagerProvider → _SparkleAppState rebuild 链）。切档即
// 真实 live re-theme，非测试专用替身。
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/l10n/app_localizations.dart';

/// 状态存活探针（「切主题不重启 run」的反例载体：任一重挂即红）。
class StylePreviewStateProbe extends StatefulWidget {
  const StylePreviewStateProbe({super.key});

  static int mountedCount = 0;

  @override
  State<StylePreviewStateProbe> createState() => StylePreviewStateProbeState();
}

class StylePreviewStateProbeState extends State<StylePreviewStateProbe> {
  int _ticks = 0;
  int get ticks => _ticks;

  @override
  void initState() {
    super.initState();
    StylePreviewStateProbe.mountedCount += 1;
  }

  @override
  Widget build(BuildContext context) => Directionality(
        textDirection: TextDirection.ltr,
        child: Row(
          key: const ValueKey('style-preview-state-probe'),
          children: [
            Text('probe-$_ticks'),
            TextButton(
              key: const ValueKey('style-preview-probe-tick'),
              onPressed: () => setState(() => _ticks += 1),
              child: const Text('tick'),
            ),
          ],
        ),
      );
}

/// 初始化 ThemeManager 单例（测试内幂等）：mock prefs + initialize +
/// 复位 classic（单例跨用例存活，逐用例归位）。
Future<ThemeManager> freshThemeManager({
  Map<String, Object> initialPrefs = const <String, Object>{},
}) async {
  SharedPreferences.setMockInitialValues(initialPrefs);
  final manager = ThemeManager();
  await manager.reset();
  await manager.initialize();
  return manager;
}

/// 真实主题管道宿主（app.dart 同机制）。
Widget buildPreviewHost({
  required Widget body,
  GlobalKey? repaintKey,
}) =>
    AnimatedBuilder(
      animation: ThemeManager(),
      builder: (context, _) {
        final app = MaterialApp(
          debugShowCheckedModeBanner: false,
          theme: AppThemes.lightTheme,
          locale: const Locale('zh'),
          localizationsDelegates: const [
            AppLocalizations.delegate,
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          supportedLocales: AppLocalizations.supportedLocales,
          home: body,
        );
        if (repaintKey != null) {
          return RepaintBoundary(key: repaintKey, child: app);
        }
        return app;
      },
    );

/// 固定时长泵（代替 pumpAndSettle）：preview 面在 runActive 步含真实
/// 骨架 shimmer（无限动画，产品真实行为），pumpAndSettle 永不落定；
/// 两拍 700ms 覆盖主题过渡（280ms）与成功徽章单次动效（≤650ms）。
Future<void> settlePreview(WidgetTester tester) async {
  await tester.pump(const Duration(milliseconds: 200));
  await tester.pump(const Duration(milliseconds: 500));
}

/// 当前挂载主题的像素档（classic/未挂载 = null）。
PixelPreviewProfile? mountedPixelProfile(WidgetTester tester) =>
    tester.widget<Theme>(find.byType(Theme).first)
        .data
        .extension<PixelProfileTheme>()
        ?.profile;

/// 当前挂载主题的 ThemeData。
ThemeData mountedTheme(WidgetTester tester) =>
    tester.widget<Theme>(find.byType(Theme).first).data;
