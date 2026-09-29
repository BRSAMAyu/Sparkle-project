import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/theme/sparkle_theme_extension.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/cognitive/data/models/behavior_pattern_model.dart';
import 'package:sparkle/features/cognitive/data/models/cognitive_fragment_model.dart';
import 'package:sparkle/features/cognitive/data/repositories/i_cognitive_repository.dart';
import 'package:sparkle/features/cognitive/presentation/providers/cognitive_provider.dart';
import 'package:sparkle/features/cognitive/presentation/screens/pattern_list_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/l10n/app_localizations_zh.dart';

/// V4-U13 · 认知定式卡假精确清理守卫（M-10 置信黑话清除同律）。
///
/// 「AI 置信 N%」没有真实定义（无法核对的百分比），从卡面移除；观察档从
/// 真实计数（frequency=出现次数）派生——原始数值与推断拆开：
/// - 正例：frequency 1/2/3+ 分别渲染 单次观察 / 观察到 2 次 / 多次观察到；
/// - 反例钉：整树不出现「置信」字样与无定义百分比徽章。
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() {
    I18nService.instance.updateLocale(
      const Locale('zh'),
      AppLocalizationsZh(),
    );
  });
  tearDown(I18nService.instance.reset);

  BehaviorPatternModel pattern(
    String name,
    int frequency, {
    double confidence = 0.73,
  }) =>
      BehaviorPatternModel(
        id: 'bp-$name',
        userId: 'u1',
        patternName: name,
        patternType: PatternType.cognitive,
        confidenceScore: confidence,
        frequency: frequency,
        isArchived: false,
        createdAt: DateTime(2026, 9, 1),
        updatedAt: DateTime(2026, 9, 20),
      );

  Future<void> pumpPatterns(
    WidgetTester tester,
    List<BehaviorPatternModel> patterns,
  ) async {
    final router = GoRouter(
      initialLocation: '/cognitive/patterns',
      routes: [
        GoRoute(
          path: '/cognitive/patterns',
          builder: (_, __) => const PatternListScreen(),
        ),
        GoRoute(
          path: '/focus',
          builder: (_, __) => const Scaffold(body: Text('FOCUS_OK')),
        ),
      ],
    );
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          cognitiveProvider.overrideWith(
            (ref) => _SeededCognitiveNotifier(patterns),
          ),
        ],
        child: MaterialApp.router(
          routerConfig: router,
          theme: ThemeData.light().copyWith(
            extensions: [SparkleThemeExtension.light()],
          ),
          locale: const Locale('zh'),
          localizationsDelegates: const [
            AppLocalizations.delegate,
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          supportedLocales: AppLocalizations.supportedLocales,
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets('frequency=3 → 「多次观察到（3 次）」，无置信百分比', (tester) async {
    await pumpPatterns(tester, [pattern('计划乐观偏差', 3)]);
    expect(find.text('多次观察到（3 次）'), findsOneWidget);
    expect(find.textContaining('置信'), findsNothing);
  });

  testWidgets('frequency=2 → 「观察到 2 次」；frequency=1 → 「单次观察」',
      (tester) async {
    await pumpPatterns(tester, [
      pattern('计划乐观偏差', 2),
      pattern('专注衰减', 1),
    ]);
    expect(find.text('观察到 2 次'), findsOneWidget);
    expect(find.text('单次观察'), findsOneWidget);
  });

  testWidgets('frequency=0 → 「暂无观察记录」，不编造任何观察', (tester) async {
    await pumpPatterns(tester, [pattern('计划乐观偏差', 0)]);
    expect(find.text('暂无观察记录'), findsOneWidget);
    expect(find.textContaining('观察到'), findsNothing);
  });

  testWidgets('反例钉：confidence 值再高也不得上屏为百分比', (tester) async {
    await pumpPatterns(tester, [
      pattern('计划乐观偏差', 5, confidence: 0.99),
    ]);
    expect(find.textContaining('置信'), findsNothing);
    expect(find.textContaining('%'), findsNothing);
  });
}

/// 预置模式桩：loadPatterns 幂等回落同一真实列表（不翻空态）。
class _SeededCognitiveNotifier extends CognitiveNotifier {
  _SeededCognitiveNotifier(List<BehaviorPatternModel> patterns)
      : _seed = patterns,
        super(_FakeCognitiveRepository());

  final List<BehaviorPatternModel> _seed;

  @override
  Future<void> loadPatterns() async {
    state = CognitiveState(patterns: _seed);
  }
}

class _FakeCognitiveRepository implements ICognitiveRepository {
  @override
  Future<CognitiveFragmentModel> createFragment(
    CognitiveFragmentCreate data,
  ) async =>
      throw UnimplementedError('not used in tier test');

  @override
  Future<List<CognitiveFragmentModel>> getFragments({
    int? limit,
    int? skip,
  }) async =>
      const [];

  @override
  Future<List<BehaviorPatternModel>> getBehaviorPatterns() async => const [];
}
