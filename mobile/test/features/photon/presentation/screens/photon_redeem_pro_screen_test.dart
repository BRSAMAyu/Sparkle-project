import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/photon/data/models/photon_redeem_pro_model.dart';
import 'package:sparkle/features/photon/data/repositories/photon_redeem_pro_repository.dart';
import 'package:sparkle/features/photon/photon_routes.dart';
import 'package:sparkle/features/photon/presentation/providers/photon_redeem_pro_provider.dart';
import 'package:sparkle/features/photon/presentation/screens/photon_redeem_pro_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../../../../shared/i18n_test_helper.dart';

void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  group('PhotonRedeemProResult contract (D-COMM-2 契约钉死)', () {
    test('success envelope parses bounded fields server-first', () {
      final result = PhotonRedeemProResult.fromJson(const {
        'success': true,
        'message': '兑换成功',
        'status': 'ok',
        'data': {
          'user_id': 'u1',
          'cost_photons': 3000,
          'pro_days': 7,
          'redeemable_base': 5200,
          'balance_after': 2200,
          'entitlement': 'pro',
          'entitlement_expires_at': '2026-09-30T00:00:00.000Z',
        },
      });
      expect(result.isOk, isTrue);
      expect(result.costPhotons, 3000);
      expect(result.proDays, 7);
      expect(result.redeemableBase, 5200);
      expect(result.balanceAfter, 2200);
      expect(result.entitlementExpiresAt, isNotNull);
    });

    test('structured error detail maps to bounded status, no guessing', () {
      final requestOptions = RequestOptions(path: '/photons/redeem-pro');
      final result = PhotonRedeemProResult.fromDioError(DioException(
        requestOptions: requestOptions,
        response: Response<Map<String, dynamic>>(
          requestOptions: requestOptions,
          statusCode: 409,
          data: const {
            'detail': {
              'status': 'insufficient_base',
              'message': '可兑换光子不足',
              'cost_photons': 3000,
              'pro_days': 7,
              'redeemable_base': 1200,
            },
          },
        ),
      ),);
      expect(result.status, PhotonRedeemProStatus.insufficientBase);
      expect(result.redeemableBase, 1200);

      // 409 无结构体 body 时不可猜测是基数不足还是月顶——诚实退化为 error。
      final opaque = PhotonRedeemProResult.fromDioError(DioException(
        requestOptions: requestOptions,
        response: Response<String>(
          requestOptions: requestOptions,
          statusCode: 409,
          data: 'conflict',
        ),
      ),);
      expect(opaque.status, PhotonRedeemProStatus.error);
    });
  });

  group('PhotonRedeemProScreen (D-COMM-2)', () {
    testWidgets('redeemable state: two numbers apart, confirm dialog, success '
        'feedback flips card to capped', (tester) async {
      final repository = _FakeRedeemRepository(
        overview: const PhotonRedeemProOverview(
          balance: 5200,
          redeemedThisMonth: false,
        ),
        result: PhotonRedeemProResult(
          status: PhotonRedeemProStatus.ok,
          costPhotons: 3000,
          proDays: 7,
          redeemableBase: 5200,
          balanceAfter: 2200,
          entitlementExpiresAt: DateTime.utc(2026, 9, 30),
        ),
      );
      await _pumpRedeemPro(tester, repository: repository);

      // 必达项①：余额与基数两数分开；基数未揭示前不产数字（诚实展示）。
      expect(find.text('5200'), findsOneWidget);
      expect(find.text('由服务端核算，兑换时揭示'), findsOneWidget);
      expect(find.text('仅合同/首胜/成就等学习所得计入基数，转账收入不计入'),
          findsOneWidget,);

      // 必达项②：三要素 + 可兑按钮。
      expect(find.text('3000'), findsOneWidget);
      expect(find.text('7 天'), findsOneWidget);
      expect(find.text('尚未使用'), findsOneWidget);
      expect(
        tester
            .widget<SparkleButton>(
              find.byKey(const ValueKey('photon-redeem-pro-action-button')),
            )
            .disabled,
        isFalse,
      );

      // 确认对话框（不可逆动作确认面）。
      await tester.tap(
          find.byKey(const ValueKey('photon-redeem-pro-action-button')),);
      await tester.pump();
      expect(find.byType(AlertDialog), findsOneWidget);
      expect(find.text('确认兑换？'), findsOneWidget);
      expect(find.textContaining('3000 光子'), findsOneWidget);
      expect(find.textContaining('不退还'), findsOneWidget);

      // 确认 → 服务端终态 → 成功反馈 + 卡面翻转为已兑换。
      await tester.tap(
          find.byKey(const ValueKey('photon-redeem-pro-confirm-button')),);
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));
      expect(find.textContaining('兑换成功'), findsOneWidget);
      expect(find.text('2200'), findsOneWidget);
      expect(find.text('本月已兑换，下月 1 日起可再兑'), findsOneWidget);
      expect(
        tester
            .widget<SparkleButton>(
              find.byKey(const ValueKey('photon-redeem-pro-action-button')),
            )
            .disabled,
        isTrue,
      );
    });

    testWidgets('insufficient base revealed by server: base number, transfer '
        'note and disabled button', (tester) async {
      final repository = _FakeRedeemRepository(
        overview: const PhotonRedeemProOverview(
          balance: 5200,
          redeemedThisMonth: false,
        ),
        result: const PhotonRedeemProResult(
          status: PhotonRedeemProStatus.insufficientBase,
          costPhotons: 3000,
          proDays: 7,
          redeemableBase: 1200,
        ),
      );
      await _pumpRedeemPro(tester, repository: repository);

      await tester.tap(
          find.byKey(const ValueKey('photon-redeem-pro-action-button')),);
      await tester.pump();
      await tester.tap(
          find.byKey(const ValueKey('photon-redeem-pro-confirm-button')),);
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));

      // 服务端揭示基数 1200 < 余额 5200：诚实区分，差额注明转账来源不可兑。
      expect(find.text('1200'), findsOneWidget);
      expect(find.text('其余 4000 光子来自转账等来源，不计入可兑换基数'),
          findsOneWidget,);
      expect(find.textContaining('可兑换基数不足'), findsWidgets);
      expect(
        tester
            .widget<SparkleButton>(
              find.byKey(const ValueKey('photon-redeem-pro-action-button')),
            )
            .disabled,
        isTrue,
      );
    });

    testWidgets('monthly cap reached: next-month note, button disabled, no '
        'dialog on tap', (tester) async {
      final repository = _FakeRedeemRepository(
        overview: const PhotonRedeemProOverview(
          balance: 5200,
          redeemedThisMonth: true,
        ),
        result: const PhotonRedeemProResult(
          status: PhotonRedeemProStatus.error,
        ),
      );
      await _pumpRedeemPro(tester, repository: repository);

      expect(find.text('本月已兑换，下月 1 日起可再兑'), findsOneWidget);
      final button = tester.widget<SparkleButton>(
        find.byKey(const ValueKey('photon-redeem-pro-action-button')),
      );
      expect(button.disabled, isTrue);

      await tester.tap(
          find.byKey(const ValueKey('photon-redeem-pro-action-button')),);
      await tester.pump();
      expect(find.byType(AlertDialog), findsNothing);
      expect(repository.redeemCallCount, 0);
    });

    testWidgets('balance below cost disables with honest note',
        (tester) async {
      final repository = _FakeRedeemRepository(
        overview: const PhotonRedeemProOverview(
          balance: 500,
          redeemedThisMonth: false,
        ),
        result: const PhotonRedeemProResult(
          status: PhotonRedeemProStatus.error,
        ),
      );
      await _pumpRedeemPro(tester, repository: repository);

      expect(find.text('500'), findsOneWidget);
      expect(find.text('光子余额不足'), findsOneWidget);
      expect(
        tester
            .widget<SparkleButton>(
              find.byKey(const ValueKey('photon-redeem-pro-action-button')),
            )
            .disabled,
        isTrue,
      );
    });

    testWidgets('snapshot failure surfaces honest error with retry',
        (tester) async {
      final repository = _FakeRedeemRepository(
        overview: const PhotonRedeemProOverview(
          balance: 5200,
          redeemedThisMonth: false,
        ),
        result: const PhotonRedeemProResult(
          status: PhotonRedeemProStatus.error,
        ),
      )..failure = Exception('boom');

      await _pumpRedeemPro(tester, repository: repository);

      expect(find.textContaining('光子兑换加载失败'), findsOneWidget);
      expect(
        find.byKey(const ValueKey('photon-redeem-pro-action-card')),
        findsNothing,
      );

      repository.failure = null;
      await tester.tap(
          find.byKey(const ValueKey('photon-redeem-pro-retry-button')),);
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));
      expect(
        find.byKey(const ValueKey('photon-redeem-pro-action-card')),
        findsOneWidget,
      );
    });

    testWidgets('route /photon/redeem-pro is registered and reachable',
        (tester) async {
      final router = GoRouter(
        initialLocation: PhotonRoutes.redeemPro,
        routes: PhotonRoutes.routes,
      );
      await _pumpRedeemPro(
        tester,
        repository: _FakeRedeemRepository(
          overview: const PhotonRedeemProOverview(
            balance: 5200,
            redeemedThisMonth: false,
          ),
          result: const PhotonRedeemProResult(
            status: PhotonRedeemProStatus.error,
          ),
        ),
        routerOverride: router,
      );

      expect(find.byType(PhotonRedeemProScreen), findsOneWidget);
      expect(
        find.byKey(const ValueKey('photon-redeem-pro-action-card')),
        findsOneWidget,
      );
    });
  });
}

Future<void> _pumpRedeemPro(
  WidgetTester tester, {
  _FakeRedeemRepository? repository,
  GoRouter? routerOverride,
}) async {
  tester.view.physicalSize = const Size(390, 1400);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  final router = routerOverride ??
      GoRouter(
        initialLocation: PhotonRoutes.redeemPro,
        routes: PhotonRoutes.routes,
      );
  if (routerOverride == null) {
    addTearDown(router.dispose);
  }

  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        if (repository != null)
          photonRedeemProRepositoryProvider.overrideWithValue(repository),
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

class _FakeRedeemRepository extends PhotonRedeemProRepository {
  _FakeRedeemRepository({
    required this.overview,
    required this.result,
  }) : super(_UnusedApiClient());

  PhotonRedeemProOverview overview;
  PhotonRedeemProResult result;
  Exception? failure;
  int redeemCallCount = 0;

  @override
  Future<PhotonRedeemProOverview> getOverview() async {
    final currentFailure = failure;
    if (currentFailure != null) {
      throw currentFailure;
    }
    return overview;
  }

  @override
  Future<PhotonRedeemProResult> redeem() async {
    redeemCallCount++;
    return result;
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
