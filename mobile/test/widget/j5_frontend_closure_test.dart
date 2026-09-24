import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/features/chat/data/models/expert_catalog_model.dart';
import 'package:sparkle/features/chat/presentation/providers/expert_catalog_provider.dart';
import 'package:sparkle/features/home/data/repositories/omnibar_repository.dart';
import 'package:sparkle/features/home/presentation/providers/intent_prediction_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/unified_omni_bar.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  TestWidgetsFlutterBinding.ensureInitialized();

  group('J5 frontend closure', () {
    testWidgets('dashboard omnibar dispatch lands in chat route',
        (tester) async {
      SharedPreferences.setMockInitialValues({});
      await ViewStorageService.ensureInitialized();
      final router = GoRouter(
        initialLocation: '/',
        routes: [
          GoRoute(
            path: '/',
            builder: (context, state) => const Scaffold(
              body: SafeArea(child: UnifiedOmniBar()),
            ),
          ),
          GoRoute(
            path: '/chat',
            builder: (context, state) => Text(
              'chat:${state.uri.queryParameters['prompt']}:${state.uri.queryParameters['source']}',
            ),
          ),
        ],
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            omniBarRepositoryProvider.overrideWithValue(
              _FakeOmniBarRepository(),
            ),
            multiAgentCatalogProvider.overrideWith(
              (ref) async => MultiAgentCatalog(
                modes: const [],
                experts: const [],
                customExperts: const [],
                customTeams: const [],
                modelOptions: const [],
              ),
            ),
            visiblePredictionsProvider.overrideWith(
              (ref) => const [],
            ),
          ],
          child: MaterialApp.router(
            // wt296：harness 缺 theme → SparkleThemeExtension 未注册，
            // UnifiedOmniBar 构建即断言失败（与 j4 同族修法）。
            theme: AppThemes.lightTheme,
            localizationsDelegates: const [
              ...AppLocalizations.localizationsDelegates,
              GlobalMaterialLocalizations.delegate,
              GlobalWidgetsLocalizations.delegate,
              GlobalCupertinoLocalizations.delegate,
            ],
            supportedLocales: AppLocalizations.supportedLocales,
            locale: const Locale('zh'),
            routerConfig: router,
          ),
        ),
      );

      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      await tester.enterText(find.byType(TextField), '今天要学什么');
      await tester.pump(const Duration(milliseconds: 100));
      await tester.tap(find.byIcon(Icons.arrow_upward_rounded));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));

      expect(find.text('chat:今天要学什么:omnibar'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('mode switch preserves current draft in chat route',
        (tester) async {
      SharedPreferences.setMockInitialValues({});
      await ViewStorageService.ensureInitialized();
      final router = GoRouter(
        initialLocation: '/',
        routes: [
          GoRoute(
            path: '/',
            builder: (context, state) => const Scaffold(
              body: SafeArea(child: UnifiedOmniBar()),
            ),
          ),
          GoRoute(
            path: '/chat',
            builder: (context, state) => Text(
              'chat:${state.uri.queryParameters['prompt']}:${state.uri.queryParameters['chat_mode']}',
            ),
          ),
        ],
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            omniBarRepositoryProvider.overrideWithValue(
              _FakeOmniBarRepository(),
            ),
            multiAgentCatalogProvider.overrideWith(
              (ref) async => MultiAgentCatalog(
                modes: const [],
                experts: const [],
                customExperts: const [],
                customTeams: const [],
                modelOptions: const [],
              ),
            ),
            visiblePredictionsProvider.overrideWith(
              (ref) => const [],
            ),
          ],
          child: MaterialApp.router(
            // wt296：harness 缺 theme → SparkleThemeExtension 未注册，
            // UnifiedOmniBar 构建即断言失败（与 j4 同族修法）。
            theme: AppThemes.lightTheme,
            localizationsDelegates: const [
              ...AppLocalizations.localizationsDelegates,
              GlobalMaterialLocalizations.delegate,
              GlobalWidgetsLocalizations.delegate,
              GlobalCupertinoLocalizations.delegate,
            ],
            supportedLocales: AppLocalizations.supportedLocales,
            locale: const Locale('zh'),
            routerConfig: router,
          ),
        ),
      );

      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      await tester.enterText(find.byType(TextField), '我想学习计算机组成原理');
      await tester.pump(const Duration(milliseconds: 100));
      await tester.tap(find.bySemanticsLabel('切换 Agent 模式'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('学习计划'));
      await tester.pumpAndSettle();

      expect(
        find.text('chat:我想学习计算机组成原理:study_plan'),
        findsOneWidget,
      );
      expect(tester.takeException(), isNull);
    });

    test('chat chrome toggles persist across notifier reload', () async {
      SharedPreferences.setMockInitialValues(<String, Object>{
        kShowChatContextToggleKey: false,
        kShowChatPredictionDockKey: false,
        kShowChatTransparencyCapsuleKey: false,
      });

      final contextToggle = SimpleBoolPreferenceNotifier(
        storageKey: kShowChatContextToggleKey,
        defaultValue: true,
      );
      final predictionDock = SimpleBoolPreferenceNotifier(
        storageKey: kShowChatPredictionDockKey,
        defaultValue: true,
      );
      final transparencyCapsule = SimpleBoolPreferenceNotifier(
        storageKey: kShowChatTransparencyCapsuleKey,
        defaultValue: true,
      );
      addTearDown(contextToggle.dispose);
      addTearDown(predictionDock.dispose);
      addTearDown(transparencyCapsule.dispose);

      await Future<void>.delayed(const Duration(milliseconds: 50));

      expect(contextToggle.state, isFalse);
      expect(predictionDock.state, isFalse);
      expect(transparencyCapsule.state, isFalse);

      await predictionDock.setEnabled(true);

      final reloadedPredictionDock = SimpleBoolPreferenceNotifier(
        storageKey: kShowChatPredictionDockKey,
        defaultValue: true,
      );
      addTearDown(reloadedPredictionDock.dispose);
      await Future<void>.delayed(const Duration(milliseconds: 50));

      expect(reloadedPredictionDock.state, isTrue);
    });

    test('debug local bgm overrides are discoverable', () async {
      // wt296：原断言 `count > 0` 依赖开发者机器上存在 local_audio_overrides
      // （bgm_service 默认根路径是本机绝对路径，CI/他机必然为 0）。改为环境
      // 无关契约：发现 API 可调且两个入口口径一致（enabled ⇔ count>0）。
      final count = await BgmService.localAdaptiveOverrideCount();
      final enabled = await BgmService.hasLocalAdaptiveOverrides();

      expect(count, greaterThanOrEqualTo(0));
      expect(enabled, equals(count > 0));
    });
  });
}

class _FakeOmniBarRepository extends OmniBarRepository {
  _FakeOmniBarRepository() : super(_UnusedApiClient());

  @override
  Future<Map<String, dynamic>> dispatch(String text) async => <String, dynamic>{
        'action_type': 'CHAT',
        'data': <String, dynamic>{
          'initial_message': text,
        },
      };
}

class _UnusedApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
