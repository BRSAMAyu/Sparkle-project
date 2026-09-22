import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/community/data/models/shared_error_models.dart';
import 'package:sparkle/features/community/data/models/squad_models.dart';
import 'package:sparkle/features/community/data/repositories/squad_repository.dart';
import 'package:sparkle/features/community/presentation/providers/squad_provider.dart';
import 'package:sparkle/features/community/presentation/widgets/share_error_to_squad_dialog.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../../../../shared/i18n_test_helper.dart';

void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  group('ShareErrorToSquadDialog (D-COMM-5)', () {
    testWidgets('with squads: picking one shares error_id to that squad',
        (tester) async {
      final repository = _FakeShareRepository(
        squads: const [
          SquadListItem(
            id: 'sq-1',
            name: '高数期末互助队',
            memberCount: 3,
            maxMembers: 8,
          ),
          SquadListItem(
            id: 'sq-2',
            name: '英语口语打卡队',
            memberCount: 2,
            maxMembers: 8,
          ),
        ],
      );

      await _pumpDialogHost(tester, repository: repository);

      // 选择第一支小队 → 确认分享。
      await tester.tap(find.byKey(const ValueKey('squad-share-option-sq-1')));
      await tester.pump();
      await tester
          .tap(find.byKey(const ValueKey('squad-share-confirm-button')));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));

      // 动作调 API：只传 error_id + 选定小队（服务端取内容，客户端不可伪造）。
      expect(repository.sharedCalls.length, 1);
      expect(repository.sharedCalls.first.squadId, 'sq-1');
      expect(repository.sharedCalls.first.errorId, 'err-42');
    });

    testWidgets('no squads: honest guidance instead of a fake target',
        (tester) async {
      final repository = _FakeShareRepository();

      await _pumpDialogHost(tester, repository: repository);

      expect(find.textContaining('还没有加入任何小队'), findsOneWidget);
      expect(
        find.byKey(const ValueKey('squad-share-empty-go-squads')),
        findsOneWidget,
      );
      // 无目标时确认钮不可用（未选队）。
      expect(
        tester
            .widget<SparkleButton>(
              find.byKey(const ValueKey('squad-share-confirm-button')),
            )
            .onPressed,
        isNull,
      );
      expect(repository.sharedCalls, isEmpty);
    });

    testWidgets('share failure surfaces honest error message', (tester) async {
      final repository = _FakeShareRepository(
        squads: const [
          SquadListItem(
            id: 'sq-1',
            name: '高数期末互助队',
            memberCount: 3,
            maxMembers: 8,
          ),
        ],
      )..shareFailure = Exception('safety filtered');

      await _pumpDialogHost(tester, repository: repository);

      await tester.tap(find.byKey(const ValueKey('squad-share-option-sq-1')));
      await tester.pump();
      await tester
          .tap(find.byKey(const ValueKey('squad-share-confirm-button')));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));

      expect(
        find.byKey(const ValueKey('squad-share-error-text')),
        findsOneWidget,
      );
      expect(find.textContaining('分享失败'), findsOneWidget);
    });
  });
}

Future<void> _pumpDialogHost(
  WidgetTester tester, {
  required _FakeShareRepository repository,
}) async {
  tester.view.physicalSize = const Size(390, 1200);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  final router = GoRouter(routes: [
    GoRoute(
      path: '/',
      pageBuilder: (context, state) => NoTransitionPage<void>(
        key: state.pageKey,
        child: Scaffold(
          body: Builder(
            builder: (context) => Center(
              child: SparkleButton(
                label: 'open-dialog',
                onPressed: () => showDialog<void>(
                  context: context,
                  builder: (_) =>
                      const ShareErrorToSquadDialog(errorId: 'err-42'),
                ),
              ),
            ),
          ),
        ),
      ),
    ),
    ],
  );
  addTearDown(router.dispose);

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

  await tester.tap(find.text('open-dialog'));
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 600));
}

class _ShareCall {
  const _ShareCall(this.squadId, this.errorId);

  final String squadId;
  final String errorId;
}

class _FakeShareRepository extends SquadRepository {
  _FakeShareRepository({this.squads = const []}) : super(_UnusedApiClient());

  final List<SquadListItem> squads;
  Exception? shareFailure;
  final List<_ShareCall> sharedCalls = <_ShareCall>[];

  @override
  Future<List<SquadListItem>> listMySquads() async => squads;

  @override
  Future<SharedErrorEntry> shareError(String groupId, String errorId) async {
    final failure = shareFailure;
    if (failure != null) {
      throw failure;
    }
    sharedCalls.add(_ShareCall(groupId, errorId));
    return SharedErrorEntry(
      shareId: 'share-new',
      sharerId: 'me',
      sharerName: '我',
      errorId: errorId,
      subjectCode: 'math',
      masteryLevel: 0.5,
      reviewCount: 1,
      createdAt: DateTime.utc(2026, 9, 22),
    );
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
