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

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() {
    I18nService.instance.updateLocale(const Locale('zh'), AppLocalizationsZh());
  });
  tearDown(I18nService.instance.reset);

  testWidgets('N39 空态必答下一步：诊断空态渲染「开始首次诊断」CTA', (tester) async {
    final router = _buildRouter();

    await tester.pumpWidget(_harness(router));
    await tester.pumpAndSettle();

    expect(find.text('还没有生成真实行为定式'), findsOneWidget);
    expect(find.text('开始首次诊断'), findsOneWidget);
  });

  testWidgets('点击 CTA → 直达聊天路由且诊断 prompt 预填（路由断言）', (tester) async {
    final router = _buildRouter();

    await tester.pumpWidget(_harness(router));
    await tester.pumpAndSettle();

    await tester.tap(find.text('开始首次诊断'));
    await tester.pumpAndSettle();

    expect(router.routeInformationProvider.value.uri.path, '/chat');
    expect(
      router.routeInformationProvider.value.uri.queryParameters['prompt'],
      contains('学习现状诊断'),
    );
    expect(find.textContaining('CHAT_PROMPT_OK'), findsOneWidget);
  });
}

GoRouter _buildRouter() => GoRouter(
      initialLocation: '/cognitive/patterns',
      routes: [
        GoRoute(
          path: '/cognitive/patterns',
          builder: (_, __) => const PatternListScreen(),
        ),
        GoRoute(
          path: '/chat',
          builder: (context, state) {
            final prompt = state.uri.queryParameters['prompt'] ?? '';
            // 断言锚点：prompt 预填已随深链到达 chat 路由
            return Scaffold(
              body: Center(
                child: prompt.contains('学习现状诊断')
                    ? const Text('CHAT_PROMPT_OK')
                    : const Text('CHAT_PROMPT_MISSING'),
              ),
            );
          },
        ),
      ],
    );

Widget _harness(GoRouter router) => ProviderScope(
      overrides: [
        cognitiveProvider.overrideWith((ref) => _EmptyCognitiveNotifier()),
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
    );

/// 空态桩：诚实空库（无 pattern、非 loading），loadPatterns 保持空态不翻动。
class _EmptyCognitiveNotifier extends CognitiveNotifier {
  _EmptyCognitiveNotifier() : super(_FakeCognitiveRepository());

  @override
  Future<void> loadPatterns() async {
    state = const CognitiveState();
  }
}

class _FakeCognitiveRepository implements ICognitiveRepository {
  @override
  Future<CognitiveFragmentModel> createFragment(
    CognitiveFragmentCreate data,
  ) async =>
      throw UnimplementedError('not used in empty-state test');

  @override
  Future<List<CognitiveFragmentModel>> getFragments({
    int? limit,
    int? skip,
  }) async =>
      const [];

  @override
  Future<List<BehaviorPatternModel>> getBehaviorPatterns() async => const [];
}
