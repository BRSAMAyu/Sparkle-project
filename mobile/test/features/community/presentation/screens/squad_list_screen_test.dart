import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/features/community/community_routes.dart';
import 'package:sparkle/features/community/data/models/squad_models.dart';
import 'package:sparkle/features/community/data/repositories/squad_repository.dart';
import 'package:sparkle/features/community/presentation/providers/squad_provider.dart';
import 'package:sparkle/features/community/presentation/screens/squad_list_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../../../../shared/i18n_test_helper.dart';

void main() {
  setUp(setUpI18nForTesting);
  setUp(() {
    // 日期选择器/ sensory 反馈路径会读 SharedPreferences。
    SharedPreferences.setMockInitialValues({});
  });
  tearDown(tearDownI18n);

  group('SquadListScreen (D-COMM-3)', () {
    testWidgets('data state renders my squads with member count honestly',
        (tester) async {
      await _pumpSquadList(
        tester,
        repository: _FakeSquadRepository(squads: _squads()),
        initialLocation: CommunityRoutes.squads,
      );

      // 必达项①：我的小队列表（真源字段直显）。
      expect(find.text('高数期末互助队'), findsOneWidget);
      expect(find.text('3/8 人'), findsOneWidget);
      expect(find.text('剩 5 天'), findsOneWidget);
      expect(find.text('期末数学一周冲刺'), findsOneWidget);
      // 第二支小队（无目标/无剩余天数行不造假）。
      expect(find.text('英语口语打卡队'), findsOneWidget);
      // 必达项②：创建/加入入口常在（空态也可达）。
      expect(
        find.byKey(const ValueKey('squad-create-entry-button')),
        findsOneWidget,
      );
      expect(
        find.byKey(const ValueKey('squad-join-entry-button')),
        findsOneWidget,
      );
    });

    testWidgets('empty state guides to create, never fakes an error',
        (tester) async {
      await _pumpSquadList(
        tester,
        repository: _FakeSquadRepository(),
        initialLocation: CommunityRoutes.squads,
      );

      // 空态诚实：无小队 ≠ 报错——给组队引导。
      expect(
        find.byKey(const ValueKey('squad-list-empty-state')),
        findsOneWidget,
      );
      expect(find.text('还没有加入冲刺小队'), findsOneWidget);
      expect(find.text('创建我的小队'), findsOneWidget);
      // 不渲染任何队卡。
      expect(find.text('高数期末互助队'), findsNothing);
      // 入口按钮仍在。
      expect(
        find.byKey(const ValueKey('squad-join-entry-button')),
        findsOneWidget,
      );
    });

    testWidgets('repository failure surfaces honest error with retry',
        (tester) async {
      final repository = _FakeSquadRepository.failure(Exception('boom'));

      await _pumpSquadList(
        tester,
        repository: repository,
        initialLocation: CommunityRoutes.squads,
      );

      expect(find.textContaining('加载失败'), findsOneWidget);
      expect(
        find.byKey(const ValueKey('squad-list-retry-button')),
        findsOneWidget,
      );
    });

    testWidgets('route /community/squads is registered and reachable',
        (tester) async {
      final router = GoRouter(
        navigatorKey: navigatorKey,
        initialLocation: '/community/squads',
        routes: CommunityRoutes.routes,
      );

      await _pumpSquadList(
        tester,
        repository: _FakeSquadRepository(squads: _squads()),
        routerOverride: router,
      );

      expect(find.byType(SquadListScreen), findsOneWidget);
      expect(find.text('高数期末互助队'), findsOneWidget);
    });

    testWidgets(
        'create dialog deadline renders through date_formatting single entry (CO-G4/X3)',
        (tester) async {
      await _pumpSquadList(
        tester,
        repository: _FakeSquadRepository(squads: _squads()),
        initialLocation: CommunityRoutes.squads,
      );

      // 打开创建小队对话框，选一个确定可用的日期（initialDate = 今天+7 天，
      // 其「日」号必在当前页且可用——不依赖测试机的具体日期）。
      // 注意：M3 日期选择器内含持续动画件，用定长 pump 驱动，不用
      // pumpAndSettle（假时钟下会无限推进）。
      await tester.tap(find.byKey(const ValueKey('squad-create-entry-button')));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));
      expect(
        find.byKey(const ValueKey('squad-create-name-field')),
        findsOneWidget,
      );

      await tester
          .tap(find.byKey(const ValueKey('squad-create-deadline-button')));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));

      final pickedDay =
          DateTime.now().add(const Duration(days: 7)).day.toString();
      await tester.tap(find.text(pickedDay).last);
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));
      await tester.tap(find.text('确定'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));
      await tester.pump(const Duration(milliseconds: 400));

      // 手工拼接 'y/m/d'（squad_list_screen 原 _formatDate）已废除：
      // 日期一律走 core 的 date_formatting 唯一入口（「9月29日」式）。
      expect(
        find.byWidgetPredicate(
          (widget) =>
              widget is Text &&
              RegExp(r'^\d{1,2}月\d{1,2}日$').hasMatch(widget.data ?? ''),
        ),
        findsOneWidget,
      );
    });
  });
}

List<SquadListItem> _squads() => [
      const SquadListItem(
        id: 'sq-1',
        name: '高数期末互助队',
        sprintGoal: '期末数学一周冲刺',
        daysRemaining: 5,
        memberCount: 3,
        maxMembers: 8,
        myRole: 'owner',
      ),
      const SquadListItem(
        id: 'sq-2',
        name: '英语口语打卡队',
        memberCount: 2,
        maxMembers: 8,
      ),
    ];

Future<void> _pumpSquadList(
  WidgetTester tester, {
  required SquadRepository repository,
  GoRouter? routerOverride,
  String? initialLocation,
}) async {
  tester.view.physicalSize = const Size(390, 1200);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  final router = routerOverride ??
      GoRouter(
        navigatorKey: navigatorKey,
        initialLocation: initialLocation ?? CommunityRoutes.squads,
        routes: CommunityRoutes.routes,
      );
  if (routerOverride == null) {
    addTearDown(router.dispose);
  }

  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        squadRepositoryProvider.overrideWithValue(repository),
      ],
      child: MaterialApp.router(
        theme: AppThemes.lightTheme,
        darkTheme: AppThemes.darkTheme,
        routerConfig: router,
        locale: const Locale('zh'),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
      ),
    ),
  );

  await tester.pump();
  await tester.pump(const Duration(milliseconds: 600));
}

class _FakeSquadRepository extends SquadRepository {
  _FakeSquadRepository({this.squads = const []}) : super(_UnusedApiClient());

  _FakeSquadRepository.failure(this.failure)
      : squads = const [],
        super(_UnusedApiClient());

  final List<SquadListItem> squads;
  Exception? failure;

  @override
  Future<List<SquadListItem>> listMySquads() async {
    final currentFailure = failure;
    if (currentFailure != null) {
      throw currentFailure;
    }
    return squads;
  }
}

class _UnusedApiClient extends ApiClient {
  _UnusedApiClient() : super(_UnusedRef());
}

class _UnusedRef implements Ref {
  @override
  T read<T>(ProviderListenable<T> provider) {
    if (T == Interceptor) {
      return InterceptorsWrapper() as T;
    }
    throw UnimplementedError('Unsupported read for $provider');
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
