import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/app/theme.dart';
import 'package:sparkle/core/models/skill_models.dart';
import 'package:sparkle/core/services/skill_api_service.dart';
import 'package:sparkle/features/user/user_routes.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../shared/i18n_test_helper.dart';

class _FakeSkillApiService implements SkillApiService {
  @override
  Future<SkillItemModel> createSkill(Map<String, dynamic> payload) {
    throw UnimplementedError();
  }

  @override
  Future<void> deleteSkill(String id) async {}

  @override
  Future<SkillDraftModel> extractDraft(Map<String, dynamic> payload) {
    throw UnimplementedError();
  }

  @override
  Future<SkillItemModel> forkSharedSkill(String id) {
    throw UnimplementedError();
  }

  @override
  Future<List<SharedSkillItemModel>> getSharedSkills({
    int page = 1,
    int pageSize = 20,
  }) async =>
      const [];

  @override
  Future<List<SkillItemModel>> getSkills() async => const [];

  @override
  Future<void> recordDraftOutcome(bool accepted) async {}

  @override
  Future<Map<String, dynamic>> shareSkill(String id) {
    throw UnimplementedError();
  }

  @override
  Future<SkillItemModel> toggleSkill(String id, bool active) {
    throw UnimplementedError();
  }

  @override
  Future<SkillItemModel> unshareSkill(String id) {
    throw UnimplementedError();
  }

  @override
  Future<SkillItemModel> updateSkill(String id, Map<String, dynamic> payload) {
    throw UnimplementedError();
  }
}

void main() {

  setUp(setUpI18nForTesting);
  testWidgets('profile can navigate to skill management screen', (
    tester,
  ) async {
    final router = GoRouter(
      initialLocation: '/launcher',
      routes: [
        GoRoute(
          path: '/launcher',
          builder: (context, state) => Scaffold(
            body: Center(
              child: IconButton(
                icon: const Icon(Icons.auto_awesome_motion_rounded),
                onPressed: () => context.push(UserRoutes.skills),
              ),
            ),
          ),
        ),
        ...UserRoutes.routes,
      ],
    );

    final container = ProviderContainer(
      overrides: [
        skillApiServiceProvider.overrideWithValue(_FakeSkillApiService()),
      ],
    );
    addTearDown(container.dispose);

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: MaterialApp.router(
          theme: AppThemes.lightTheme,
          darkTheme: AppThemes.darkTheme,
          routerConfig: router,
          locale: const Locale('zh'),
          localizationsDelegates: const [
            ...AppLocalizations.localizationsDelegates,
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          supportedLocales: AppLocalizations.supportedLocales,
        ),
      ),
    );

    for (var i = 0; i < 10; i++) {
      await tester.pump(const Duration(milliseconds: 100));
    }

    await tester.tap(find.byIcon(Icons.auto_awesome_motion_rounded));
    for (var i = 0; i < 12; i++) {
      await tester.pump(const Duration(milliseconds: 100));
    }

    expect(find.text('我的方式'), findsWidgets);
  });
}
