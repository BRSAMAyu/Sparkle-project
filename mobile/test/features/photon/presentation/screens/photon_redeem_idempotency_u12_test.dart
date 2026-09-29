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
import 'package:sparkle/l10n/app_localizations.dart';

import '../../../../shared/i18n_test_helper.dart';

/// V4-U12 验收 2「余额/兑换来自真账本，重复兑换幂等」移动端钉。
///
/// - 真账本：余额/成本/时长/基数全部来自服务端快照与兑换终态
///   （PHOTON-STATUS 同源），本地常量只许兜底、绝不覆盖服务端数；
///   成功后余额显示服务端 `balance_after`，不做本地减法。
/// - 幂等：同一逻辑动作全程至多一次 `redeem()` 调用（V4-U12 重入守卫：
///   双击同帧不产生第二确认面/第二次 POST）；成功后月顶封口，动作按钮
///   不再可发（服务端月顶屏障之上的客户端第一道闸）。
void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  testWidgets('账本真值面：余额/成本/时长显示服务端快照数，本地常量不覆盖', (tester) async {
    // 服务端数与展示常量（cost 1500 / days 7）刻意错开，验证 server-first。
    final repo = _CountingRedeemRepository(
      overview: const PhotonRedeemProOverview(
        balance: 4321,
        redeemedThisMonth: false,
        redeemableBase: 4321,
        costPhotons: 1777,
        proDays: 9,
      ),
      result: const PhotonRedeemProResult(status: PhotonRedeemProStatus.error),
    );
    await _pumpRedeemPro(tester, repo);

    expect(
      find.byKey(const ValueKey('photon-redeem-pro-balance-value')),
      findsOneWidget,
    );
    expect(find.text('4321'), findsWidgets);
    expect(
      find.byKey(const ValueKey('photon-redeem-pro-base-value')),
      findsOneWidget,
    );
    // 服务端成本/时长（1777 / 9 天）上屏；展示常量（1500/7）不覆盖。
    expect(find.text('1777'), findsOneWidget);
    expect(find.text('9 天'), findsOneWidget);
    expect(find.text('7 天'), findsNothing);
    expect(find.text('1500'), findsNothing);
    expect(repo.redeemCalls, 0);
  });

  testWidgets('幂等正例：确认一次 → redeem() 恰好一次，余额显示服务端 balance_after',
      (tester) async {
    final repo = _CountingRedeemRepository(
      overview: const PhotonRedeemProOverview(
        balance: 4321,
        redeemedThisMonth: false,
        redeemableBase: 4321,
        costPhotons: 1777,
        proDays: 9,
      ),
      result: const PhotonRedeemProResult(
        status: PhotonRedeemProStatus.ok,
        costPhotons: 1777,
        proDays: 9,
        redeemableBase: 4321,
        balanceAfter: 2544,
      ),
    );
    await _pumpRedeemPro(tester, repo);

    await tester
        .tap(find.byKey(const ValueKey('photon-redeem-pro-action-button')));
    await tester.pumpAndSettle();
    expect(
      find.byKey(const ValueKey('photon-redeem-pro-confirm-button')),
      findsOneWidget,
    );
    await tester.tap(
      find.byKey(const ValueKey('photon-redeem-pro-confirm-button')),
    );
    await tester.pumpAndSettle();

    expect(repo.redeemCalls, 1);
    // 成功终态余额 = 服务端 balance_after（2544），不是本地减法 4321-1777=2544
    // 的巧合能掩盖的其他本地推算路径（这里钉服务端值本身）。
    expect(find.text('2544'), findsOneWidget);
  });

  testWidgets('幂等反例钉：同帧双击动作 → 只开一个确认面，确认后 redeem() 仍只有一次', (tester) async {
    final repo = _CountingRedeemRepository(
      overview: const PhotonRedeemProOverview(
        balance: 4321,
        redeemedThisMonth: false,
        redeemableBase: 4321,
        costPhotons: 1777,
        proDays: 9,
      ),
      result: const PhotonRedeemProResult(
        status: PhotonRedeemProStatus.ok,
        balanceAfter: 2544,
      ),
    );
    await _pumpRedeemPro(tester, repo);

    // 同帧两次触发（无 pump 间隔）。注（一审 C-1 勘误）：本断言实测的是
    // 框架 hit-test 层对同帧第二击的吞没——_actionInFlight 守卫在该路径
    // 从未被执行（一审三组探针实证）；守卫是防御纵深，无独立测试钉，
    // 验收 2 的幂等由服务端月顶屏障独立真证（见后端 photon 套件）。
    await tester
        .tap(find.byKey(const ValueKey('photon-redeem-pro-action-button')));
    await tester.tap(
      find.byKey(const ValueKey('photon-redeem-pro-action-button')),
      warnIfMissed: false,
    );
    await tester.pumpAndSettle();

    expect(
      find.byKey(const ValueKey('photon-redeem-pro-confirm-button')),
      findsOneWidget,
      reason: '双击只允许产生一个确认面对话框',
    );
    await tester.tap(
      find.byKey(const ValueKey('photon-redeem-pro-confirm-button')),
    );
    await tester.pumpAndSettle();

    expect(repo.redeemCalls, 1, reason: '双击不得产生第二次网络兑换');
  });

  testWidgets('重放封口钉：兑换成功后动作按钮禁用（月顶/终态封口），二次触发不可发', (tester) async {
    final repo = _CountingRedeemRepository(
      overview: const PhotonRedeemProOverview(
        balance: 4321,
        redeemedThisMonth: false,
        redeemableBase: 4321,
        costPhotons: 1777,
        proDays: 9,
      ),
      result: const PhotonRedeemProResult(
        status: PhotonRedeemProStatus.ok,
        balanceAfter: 2544,
      ),
    );
    await _pumpRedeemPro(tester, repo);

    await tester
        .tap(find.byKey(const ValueKey('photon-redeem-pro-action-button')));
    await tester.pumpAndSettle();
    await tester.tap(
      find.byKey(const ValueKey('photon-redeem-pro-confirm-button')),
    );
    await tester.pumpAndSettle();

    expect(repo.redeemCalls, 1);
    // 成功后 capped（含 _lastResult.ok）→ 按钮禁用：再点不产生第二次调用。
    final button = tester.widget<SparkleButton>(
      find.byKey(const ValueKey('photon-redeem-pro-action-button')),
    );
    expect(button.disabled, isTrue);
    await tester.tap(
      find.byKey(const ValueKey('photon-redeem-pro-action-button')),
      warnIfMissed: false,
    );
    await tester.pumpAndSettle();
    expect(repo.redeemCalls, 1, reason: '重放路径不得产生第二次兑换调用');
    expect(
      find.byKey(const ValueKey('photon-redeem-pro-confirm-button')),
      findsNothing,
    );
  });

  testWidgets('账本失败面：业务失败映射有界终态文案，异常结构不直出', (tester) async {
    final repo = _CountingRedeemRepository(
      overview: const PhotonRedeemProOverview(
        balance: 10,
        redeemedThisMonth: false,
        redeemableBase: 10,
        costPhotons: 1777,
        proDays: 9,
      ),
      result: const PhotonRedeemProResult(
        status: PhotonRedeemProStatus.insufficientBase,
      ),
    );
    await _pumpRedeemPro(tester, repo);

    // 不足预判诚实呈现（动作前），按钮禁用；基数不足文案直达。
    expect(
      find.text('可兑换基数不足：仅学习所得光子可兑换，转账收入不计入。'),
      findsOneWidget,
    );
    final button = tester.widget<SparkleButton>(
      find.byKey(const ValueKey('photon-redeem-pro-action-button')),
    );
    expect(button.disabled, isTrue);
    expect(repo.redeemCalls, 0);
  });
}

// ========== harness ==========

Future<void> _pumpRedeemPro(
  WidgetTester tester,
  _CountingRedeemRepository repo,
) async {
  final router = GoRouter(
    initialLocation: PhotonRoutes.redeemPro,
    routes: PhotonRoutes.routes,
  );
  tester.view.physicalSize = const Size(390, 1400);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  addTearDown(router.dispose);

  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        photonRedeemProRepositoryProvider.overrideWithValue(repo),
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
  await tester.pump(const Duration(milliseconds: 400));
}

/// 计数型假仓库：只记录 redeem() 调用次数（幂等钉的被测面），读面原样回放
/// 服务端快照。测试注入专用，实现面全走真实 ApiClient/repository。
class _CountingRedeemRepository extends PhotonRedeemProRepository {
  _CountingRedeemRepository({
    required this.overview,
    required this.result,
  }) : super(_UnusedApiClient());

  PhotonRedeemProOverview overview;
  PhotonRedeemProResult result;
  int redeemCalls = 0;

  @override
  Future<PhotonRedeemProOverview> getOverview() async => overview;

  @override
  Future<PhotonRedeemProResult> redeem() async {
    redeemCalls++;
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
