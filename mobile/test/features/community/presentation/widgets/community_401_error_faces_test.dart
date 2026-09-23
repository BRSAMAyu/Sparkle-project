import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/compact_error_card.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/data/repositories/community_repository.dart';
import 'package:sparkle/features/community/presentation/providers/community_provider.dart';
import 'package:sparkle/features/community/presentation/screens/group_discover_screen.dart';
import 'package:sparkle/features/community/presentation/widgets/groups_hub_view.dart';
import 'package:sparkle/l10n/app_localizations.dart';

import '../../../../shared/i18n_test_helper.dart';

/// COMMUNITY-401 secondary regressions:
///   1. the groups tab used to render the raw DioException 401 textbook text
///      (`error.toString()` leak);
///   2. the plaza (社群广场) used to die into a fullscreen ERR-AUTH page —
///      now it degrades to an in-panel face with search + retry alive.
void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  final unauthorized = DioException(
    requestOptions: RequestOptions(path: '/api/v1/community/groups'),
    type: DioExceptionType.badResponse,
    message: 'The request returned a status code of 401',
    response: Response<dynamic>(
      requestOptions: RequestOptions(path: '/api/v1/community/groups'),
      statusCode: 401,
    ),
  );

  testWidgets('groups tab humanizes a 401 error — no raw DioException text',
      (tester) async {
    await _pump(
      tester,
      overrides: [
        myGroupsProvider.overrideWith(
          (ref) => _StubGroupsNotifier(
            AsyncValue.error(unauthorized, StackTrace.current),
          ),
        ),
        groupRecommendationsProvider.overrideWith(
          (ref) => _StubRecommendationsNotifier(const AsyncValue.data([])),
        ),
        groupDiscoverProvider.overrideWith(
          (ref) => _StubDirectoryNotifier(
            AsyncValue.error(unauthorized, StackTrace.current),
          ),
        ),
      ],
      widget: const GroupsHubView(),
    );

    // The raw exception dump must never reach the UI.
    expect(find.textContaining('DioException'), findsNothing);
    expect(find.textContaining('mozilla.org'), findsNothing);
    // Humanized message with the stable field-report code instead.
    expect(find.textContaining('[ERR-AUTH]'), findsOneWidget);
    // A visible tap-to-retry face exists.
    expect(find.byType(CompactErrorCard), findsOneWidget);
  });

  testWidgets('plaza degrades to an in-panel error face, not a fullscreen '
      'error page', (tester) async {
    await _pump(
      tester,
      overrides: [
        groupDiscoverProvider.overrideWith(
          (ref) => _StubDirectoryNotifier(
            AsyncValue.error(unauthorized, StackTrace.current),
          ),
        ),
        recommendationFeedbackPromptsProvider.overrideWith(
          (ref) => _StubPromptsNotifier(const AsyncValue.data([])),
        ),
        recommendationFeedbackInsightsProvider.overrideWith(
          (ref) => _StubInsightsNotifier(const AsyncValue.data([])),
        ),
      ],
      widget: const GroupDiscoverScreen(),
    );

    // No fullscreen error widget anymore.
    expect(find.byType(CustomErrorWidget), findsNothing);
    // The search surface stays usable inside the degraded face.
    expect(find.byType(TextField), findsOneWidget);
    // Tap-to-retry face present, humanized code visible.
    expect(find.byType(CompactErrorCard), findsOneWidget);
    expect(find.textContaining('[ERR-AUTH]'), findsOneWidget);
    expect(find.textContaining('DioException'), findsNothing);
  });
}

Future<void> _pump(
  WidgetTester tester, {
  required List<Override> overrides,
  required Widget widget,
}) async {
  tester.view.physicalSize = const Size(390, 844);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  await tester.pumpWidget(
    ProviderScope(
      overrides: overrides,
      child: MaterialApp(
        theme: AppThemes.lightTheme,
        darkTheme: AppThemes.darkTheme,
        locale: const Locale('zh'),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: Scaffold(body: widget),
      ),
    ),
  );
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 300));
}

// ─── Stubs: never touch the network, just seed the state under test ─────────

class _StubGroupsNotifier extends MyGroupsNotifier {
  _StubGroupsNotifier(AsyncValue<List<GroupListItem>> initialState)
      : super(_UnusedCommunityRepository(), _DirRef()) {
    state = initialState;
  }

  @override
  Future<void> loadGroups() async {}
}

class _StubRecommendationsNotifier extends GroupRecommendationsNotifier {
  _StubRecommendationsNotifier(AsyncValue<List<GroupRecommendationItem>> seed)
      : super(_UnusedCommunityRepository(), source: 'test', limit: 8) {
    state = seed;
  }

  @override
  Future<void> loadRecommendations({int cursor = 0}) async {}
}

class _StubDirectoryNotifier extends GroupDirectoryNotifier {
  _StubDirectoryNotifier(AsyncValue<GroupDirectoryInfo> seed)
      : super(_UnusedCommunityRepository(), _DirRef()) {
    state = seed;
  }

  @override
  GroupDirectorySort get sortBy => GroupDirectorySort.hot;
  @override
  GroupType? get type => null;
  @override
  String get keyword => '';
  @override
  Set<String> get selectedTags => <String>{};

  @override
  Future<void> loadDirectory() async {}
  @override
  Future<void> refresh() => loadDirectory();
  @override
  Future<void> setSortBy(GroupDirectorySort sortBy) async {}
  @override
  Future<void> setKeyword(String keyword) async {}
  @override
  Future<void> setType(GroupType? type) async {}
  @override
  Future<void> toggleTag(String tag) async {}
  @override
  Future<void> clearFilters() async {}
  @override
  Future<void> join(String groupId) async {}
}

class _StubPromptsNotifier extends RecommendationFeedbackPromptsNotifier {
  _StubPromptsNotifier(AsyncValue<List<RecommendationFeedbackPrompt>> seed)
      : super(_UnusedCommunityRepository()) {
    state = seed;
  }

  @override
  Future<void> loadPrompts() async {}
}

class _StubInsightsNotifier extends RecommendationFeedbackInsightsNotifier {
  _StubInsightsNotifier(
    AsyncValue<List<RecommendationFeedbackInsight>> seed,
  )   : super(_UnusedCommunityRepository()) {
    state = seed;
  }

  @override
  Future<void> loadInsights() async {}
}

class _UnusedCommunityRepository implements CommunityRepository {
  // Stubs override every member the tests exercise, so no method here is
  // ever invoked — the concrete constructor (and its ApiClient graph) is
  // deliberately never built.
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

/// Stored but never used: the directory stubs override every member that
/// would touch the ref (join/leave invalidations).
class _DirRef implements Ref {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
