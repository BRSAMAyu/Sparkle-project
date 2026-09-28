// V4-U04 · FIX535 入口接线真实性（可失败）：
//   `/journey/workbench` 必须注册在**真实 app router** 上——入口「真实可达」
//   不是注释声明。回退 routes.dart 的 `...JourneyRoutes.routes` 注册（stash
//   单行）本测试即红（落在 404 error page），复线复绿——接线级 RED/GREEN 证据。
import 'dart:ffi' as ffi;
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hive_flutter/hive_flutter.dart';
import 'package:isar/isar.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/app/routes.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/offline/models/focus_session_record.dart';
import 'package:sparkle/core/offline/models/offline_chat_message.dart';
import 'package:sparkle/core/offline/models/translation_record.dart';
import 'package:sparkle/core/offline/models/vocab_word.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart'
    show sharedPreferencesProvider;
import 'package:sparkle/features/galaxy/data/repositories/enhanced_galaxy_repository.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/user_brief.dart';
import 'package:sparkle/shared/entities/user_model.dart';

import '../../shared/i18n_test_helper.dart';

void main() {
  setUp(setUpI18nForTesting);
  TestWidgetsFlutterBinding.ensureInitialized();
  late Directory hiveDir;
  late Directory isarDir;
  late Isar isar;

  setUpAll(() async {
    SharedPreferences.setMockInitialValues({});
    final bundledIsarCore = Platform.isMacOS
        ? '${Directory.current.path}/third_party_plugins/isar_flutter_libs/macos/libisar.dylib'
        : Platform.isLinux
            ? '${Directory.current.path}/third_party_plugins/isar_flutter_libs/linux/libisar.so'
            : null;
    await Isar.initializeIsarCore(
      libraries: bundledIsarCore == null
          ? const {}
          : {
              ffi.Abi.current(): bundledIsarCore,
            },
      download: bundledIsarCore == null,
    );
    hiveDir = Directory.systemTemp.createTempSync('sparkle_u04_hive_');
    isarDir = await Directory.systemTemp.createTemp('sparkle_u04_isar_');
    Hive.init(hiveDir.path);
    isar = await Isar.open(
      [
        LocalKnowledgeNodeSchema,
        PendingUpdateSchema,
        LocalCRDTSnapshotSchema,
        OutboxItemSchema,
        TranslationRecordSchema,
        TranslationWordLinkSchema,
        VocabWordSchema,
        VocabReviewSchema,
        FocusSessionRecordSchema,
        CachedStatisticsModelSchema,
        OfflineChatMessageSchema,
      ],
      directory: isarDir.path,
    );
    LocalDatabase().isar = isar;
    await ViewStorageService.ensureInitialized();
  });

  setUp(() {
    DemoDataService.isDemoMode = true;
  });

  tearDown(() {
    DemoDataService.isDemoMode = false;
  });

  testWidgets(
      'app router 注册 /journey/workbench：已认证用户直达运行工作台（FIX535 入口真实可达）',
      (tester) async {
    final container = ProviderContainer(
      overrides: [
        authProvider.overrideWith(
          (ref) => _FakeAuthNotifier(
            AuthState(
              isAuthenticated: true,
              user: _buildUser(),
            ),
          ),
        ),
        sharedPreferencesProvider.overrideWithValue(
          await SharedPreferences.getInstance(),
        ),
        onboardingCompletedProvider.overrideWith(
          (ref) => _FakeOnboardingCompletedNotifier(true, ref),
        ),
        enhancedGalaxyRepositoryProvider.overrideWithValue(
          _TestGalaxyRepository(),
        ),
      ],
    );
    addTearDown(container.dispose);

    final router = container.read(routerProvider);
    addTearDown(router.dispose);

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: MaterialApp.router(
          routerConfig: router,
          theme: AppThemes.lightTheme,
          // 断言 zh 文案（与 setUpI18nForTesting 的 I18nService 口径一致）。
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
    for (var i = 0; i < 8; i++) {
      await tester.pump(const Duration(milliseconds: 100));
    }

    router.go('/journey/workbench');
    for (var i = 0; i < 8; i++) {
      await tester.pump(const Duration(milliseconds: 100));
    }

    // 入口真实可达：落在运行工作台（不是 404 / 未重写）。
    expect(find.byKey(const Key('hybrid_workbench_screen')), findsOneWidget);
    expect(find.text('页面未找到'), findsNothing);
    expect(find.textContaining('运行工作台'), findsWidgets);
  });
}

UserModel _buildUser() => UserModel(
      id: '00000000-0000-0000-0000-000000000042',
      username: 'u04_router_test_user',
      email: 'u04-router@example.com',
      nickname: 'U04 Router Test',
      flameLevel: 1,
      flameBrightness: 0.5,
      depthPreference: 0.5,
      curiosityPreference: 0.5,
      isActive: true,
      status: UserStatus.online,
      createdAt: DateTime(2026),
      updatedAt: DateTime(2026),
    );

class _FakeAuthNotifier extends AuthNotifier {
  _FakeAuthNotifier(AuthState authState)
      : super(_UnusedRef(), _UnusedAuthRepository()) {
    state = authState;
  }

  @override
  Future<void> checkAuthStatus() async {}
}

class _FakeOnboardingCompletedNotifier extends OnboardingCompletedNotifier {
  _FakeOnboardingCompletedNotifier(this._completed, Ref ref) : super(ref);

  final bool _completed;

  @override
  Future<void> syncForUser(UserModel? user) async {
    state = _completed;
  }

  @override
  Future<void> setCompleted(bool value) async {
    state = value;
  }
}

class _UnusedRef implements Ref<Object?> {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _UnusedAuthRepository implements AuthRepository {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _TestGalaxyRepository extends EnhancedGalaxyRepository {
  _TestGalaxyRepository() : super(_UnusedApiClient());

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _UnusedApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
