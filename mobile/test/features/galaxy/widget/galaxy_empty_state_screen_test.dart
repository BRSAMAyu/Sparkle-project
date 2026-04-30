import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/core/services/retry_strategy.dart';
import 'package:sparkle/features/galaxy/data/models/user_galaxy_contribution.dart';
import 'package:sparkle/features/galaxy/data/repositories/enhanced_galaxy_repository.dart';
import 'package:sparkle/features/galaxy/presentation/screens/galaxy_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';
import '../../../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() async {
    SharedPreferences.setMockInitialValues(<String, Object>{});
    await ViewStorageService.ensureInitialized();
  });

  testWidgets('galaxy screen shows guided empty state for empty graph', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          enhancedGalaxyRepositoryProvider.overrideWithValue(
            _FakeEnhancedGalaxyRepository(),
          ),
        ],
        child: testMaterialApp(
          theme: AppThemes.lightTheme,
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          locale: const Locale('zh'),
          home: const GalaxyScreen(),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 500));

    expect(find.text('星图空空如也'), findsOneWidget);
    expect(find.text('去创建学习任务'), findsOneWidget);
  });

  testWidgets(
      'galaxy screen shows mastery onboarding banner when mastery is zero',
      (WidgetTester tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          enhancedGalaxyRepositoryProvider.overrideWithValue(
            _FakeEnhancedGalaxyRepository(
              graph: GalaxyGraphResponse(
                nodes: <GalaxyNodeModel>[
                  GalaxyNodeModel(
                    id: 'node-1',
                    name: '代数基础',
                    importance: 2,
                    sector: SectorEnum.tech,
                    isUnlocked: true,
                    masteryScore: 0,
                  ),
                ],
                edges: const <GalaxyEdgeModel>[],
                userFlameIntensity: 0,
              ),
            ),
          ),
        ],
        child: testMaterialApp(
          theme: AppThemes.lightTheme,
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          locale: const Locale('zh'),
          home: const GalaxyScreen(),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 500));

    expect(find.text('还没有点亮掌握记录'), findsOneWidget);
    expect(find.text('去学习'), findsOneWidget);
  });
}

class _FakeEnhancedGalaxyRepository extends EnhancedGalaxyRepository {
  _FakeEnhancedGalaxyRepository({
    GalaxyGraphResponse? graph,
  })  : graph = graph ??
            GalaxyGraphResponse(
              nodes: const <GalaxyNodeModel>[],
              edges: const <GalaxyEdgeModel>[],
              userFlameIntensity: 0,
            ),
        super(_NoopApiClient());

  final GalaxyGraphResponse graph;

  @override
  Future<NetworkResult<GalaxyGraphResponse>> getGraph({
    double zoomLevel = 1.0,
    bool forceRefresh = false,
  }) async =>
      NetworkResult.success(graph);

  @override
  Future<NetworkResult<UserGalaxyContribution>> getContributionStats() async =>
      NetworkResult.success(UserGalaxyContribution.empty);

  @override
  Stream<SSEEvent> getGalaxyEventsStream({String? lastEventId}) =>
      const Stream<SSEEvent>.empty();
}

class _NoopApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => null;
}
