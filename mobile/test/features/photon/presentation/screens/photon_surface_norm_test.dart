import 'dart:async';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_theme_extension.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/photon/data/models/photon_redeem_pro_model.dart';
import 'package:sparkle/features/photon/data/repositories/photon_redeem_pro_repository.dart';
import 'package:sparkle/features/photon/data/repositories/photon_repository.dart';
import 'package:sparkle/features/photon/photon_routes.dart';
import 'package:sparkle/features/photon/presentation/providers/photon_provider.dart';
import 'package:sparkle/features/photon/presentation/providers/photon_redeem_pro_provider.dart';
import 'package:sparkle/features/photon/presentation/screens/transaction_history_screen.dart';
import 'package:sparkle/features/photon/presentation/widgets/transaction_history_list.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/photon_model.dart';

import '../../../../shared/i18n_test_helper.dart';

/// PHOTON 卡（A-SPEC2 top10 v2 #4/#7/#10）验收测试：
/// - #4 流水入口直达：redeem 屏资产卡区次级入口存在且一步可达流水页；
/// - #10 幽灵面处置：transfer 路由撤除 + PhotonBalanceCard 引用清零
///   （grep 钉进测试防回潮），深链落路由兜底而非幽灵屏；
/// - #7 流水页四态：首载骨架贴布局、失败人话三句式（Object 不进 Text）。
void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  group('#4 流水入口直达（A-SPEC2 PH-G1 / N13-①）', () {
    testWidgets('资产卡区「查看光子流水」入口存在，一步可达流水页', (tester) async {
      final photonRepo = _FakePhotonRepository()..historyResult = [];
      await _pumpWithRouter(
        tester,
        redeemRepo: _okRedeemRepo(),
        photonRepo: photonRepo,
      );

      // 入口存在（资产卡区内）。
      final entry = find.byKey(
        const ValueKey('photon-redeem-pro-history-entry'),
      );
      expect(entry, findsOneWidget);
      expect(find.text('查看光子流水'), findsOneWidget);
      expect(find.byType(TransactionHistoryScreen), findsNothing);

      // 一步可达：点击入口直接落到流水页（空数据诚实空态）。
      await tester.tap(entry);
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));

      expect(find.byType(TransactionHistoryScreen), findsOneWidget);
      expect(find.text('暂无交易记录'), findsOneWidget);
    });
  });

  group('#10 幽灵面处置（A-SPEC2 PH-G3 / PH-G2）', () {
    test('路由表：/photon/transfer 已撤，history 与 redeem-pro 仍在', () {
      final paths =
          PhotonRoutes.routes.whereType<GoRoute>().map((r) => r.path).toSet();
      expect(paths.contains('/photon/transfer'), isFalse);
      expect(paths.contains(PhotonRoutes.transactionHistory), isTrue);
      expect(paths.contains(PhotonRoutes.redeemPro), isTrue);
      // PhotonRoutes.transfer 常量本身不复存在（引用即编译错误，天然防回潮）。
    });

    test('引用清零（grep 钉进测试）：PhotonRoutes.transfer / PhotonBalanceCard',
        () {
      final offenders = <String>[];
      _walkDartFiles(Directory('lib')).forEach((file) {
        final source = file.readAsStringSync();
        if (source.contains('PhotonRoutes.transfer') ||
            source.contains('PhotonBalanceCard')) {
          offenders.add(file.path);
        }
      });
      expect(offenders, isEmpty);

      // 死卡文件整删，不留尸体。
      expect(
        File(
          'lib/features/photon/presentation/widgets/photon_balance_card.dart',
        ).existsSync(),
        isFalse,
      );
      // 幽灵屏按裁决保留未删（已登记 KNOWN_CODE_DEBT_LEDGER.md #11）。
      expect(
        File(
          'lib/features/photon/presentation/screens/photon_transfer_screen.dart',
        ).existsSync(),
        isTrue,
      );
    });

    testWidgets('深链 /photon/transfer 落路由兜底，不渲染幽灵屏', (tester) async {
      final router = GoRouter(
        initialLocation: '/photon/transfer',
        routes: PhotonRoutes.routes,
        errorBuilder: (context, state) => const Scaffold(
          key: ValueKey('router-fallback-page'),
          body: SizedBox.shrink(),
        ),
      );
      // router.dispose 由 _pumpRouter 统一登记，勿重复登记（二次 dispose 即崩）。
      await _pumpRouter(tester, router);

      // 兜底页命中；幽灵屏零渲染。
      expect(find.byKey(const ValueKey('router-fallback-page')),
          findsOneWidget,);
    });
  });

  group('#7 流水页四态（A-SPEC2 PH-G4/G5/G6）', () {
    testWidgets('首载骨架贴布局（SparkleListSkeleton），裸 spinner 清零',
        (tester) async {
      final photonRepo = _FakePhotonRepository()..pending = Completer();
      await _pumpList(tester, photonRepo);

      expect(find.byType(SparkleListSkeleton), findsOneWidget);
      expect(find.byType(CircularProgressIndicator), findsNothing);
      photonRepo.pending?.complete([]);
    });

    testWidgets('分页尾为行骨架，非 spinner', (tester) async {
      final photonRepo = _FakePhotonRepository()
        ..historyResult = List.generate(
          20,
          (i) => _tx('tx-$i', DateTime(2026, 9, 20, 10, 0 + i)),
        )
        ..secondPagePending = Completer<List<PhotonTransaction>>();
      await _pumpList(tester, photonRepo);
      await tester.pump(const Duration(milliseconds: 200));

      // 触发分页加载（滚到底部 80% 阈值）。
      await tester.drag(find.byType(ListView).first, const Offset(0, -8000));
      await tester.pump(const Duration(milliseconds: 200));

      expect(find.byType(CircularProgressIndicator), findsNothing);
      expect(find.byType(SparkleCardSkeleton), findsOneWidget);
      photonRepo.secondPagePending?.complete([]);
    });

    testWidgets('失败态：人话三句式 + 重试，异常细节（Object）不出现于任何 Text',
        (tester) async {
      final photonRepo = _FakePhotonRepository()
        ..shouldThrow = Exception('boom-secret-detail');
      await _pumpList(tester, photonRepo);
      await tester.pump(const Duration(milliseconds: 200));

      // 人话模板（发生了什么 + 数据没丢 + 再试指引），有重试钮。
      expect(find.textContaining('光子流水暂时加载不了'), findsOneWidget);
      expect(find.textContaining('你的数据没有丢'), findsOneWidget);
      expect(find.widgetWithText(SparkleButton, '重试'), findsOneWidget);

      // Object 不出现于 Text：异常细节零直出。
      expect(find.textContaining('boom-secret'), findsNothing);
      expect(find.textContaining('Exception'), findsNothing);
      expect(find.byType(CircularProgressIndicator), findsNothing);

      // 重试可用：故障解除后恢复数据面。
      photonRepo
        ..shouldThrow = null
        ..historyResult = [_tx('tx-1', DateTime(2026, 9, 22, 9, 5))];
      await tester.tap(find.widgetWithText(SparkleButton, '重试'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      expect(find.textContaining('光子流水暂时加载不了'), findsNothing);
      expect(find.text('成就奖励'), findsOneWidget);
      expect(find.text('09:05'), findsOneWidget); // 唯一入口 HH:mm 格式
    });

    testWidgets('数据态：日期分组头走唯一入口（今天分组 + HH:mm）', (tester) async {
      final now = DateTime.now();
      final photonRepo = _FakePhotonRepository()
        ..historyResult = [
          _tx('tx-today', now),
          _tx('tx-old', DateTime(2020, 1, 5, 8, 30)),
        ];
      await _pumpList(tester, photonRepo);
      await tester.pump(const Duration(milliseconds: 200));

      expect(find.text('今天'), findsOneWidget); // 相对日分组头（无钟点）
      expect(find.text('1月5日'), findsOneWidget); // ≥7 天落绝对纯日期
      expect(find.textContaining('Exception'), findsNothing);
    });
  });
}

// ========== helpers ==========

PhotonTransaction _tx(String id, DateTime createdAt) => PhotonTransaction(
      id: id,
      transactionType: PhotonTransactionType.grantAchievement,
      amount: 100,
      balanceBefore: 0,
      balanceAfter: 100,
      createdAt: createdAt,
    );

Iterable<File> _walkDartFiles(Directory dir) sync* {
  if (!dir.existsSync()) {
    return;
  }
  for (final entity in dir.listSync(recursive: true)) {
    if (entity is File && entity.path.endsWith('.dart')) {
      yield entity;
    }
  }
}

PhotonRedeemProRepository _okRedeemRepo() => _FakeRedeemRepository(
      overview: const PhotonRedeemProOverview(
        balance: 5200,
        redeemedThisMonth: false,
        redeemableBase: 5200,
        costPhotons: photonRedeemProDisplayCost,
        proDays: 7,
      ),
      result: const PhotonRedeemProResult(status: PhotonRedeemProStatus.error),
    );

Future<void> _pumpRouter(WidgetTester tester, GoRouter router) async {
  tester.view.physicalSize = const Size(390, 1400);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  addTearDown(router.dispose);

  await tester.pumpWidget(
    MaterialApp.router(
      theme: ThemeData.light().copyWith(
        extensions: [SparkleThemeExtension.light()],
      ),
      routerConfig: router,
      locale: const Locale('zh'),
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
    ),
  );
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 400));
}

Future<void> _pumpWithRouter(
  WidgetTester tester, {
  required PhotonRedeemProRepository redeemRepo,
  required PhotonRepository photonRepo,
}) async {
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
        photonRedeemProRepositoryProvider.overrideWithValue(redeemRepo),
        photonRepositoryProvider.overrideWithValue(photonRepo),
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

Future<void> _pumpList(
  WidgetTester tester,
  _FakePhotonRepository photonRepo,
) async {
  tester.view
    ..physicalSize = const Size(390, 1400)
    ..devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        photonRepositoryProvider.overrideWithValue(photonRepo),
      ],
      child: MaterialApp(
        theme: AppThemes.lightTheme,
        locale: const Locale('zh'),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: const Scaffold(
          body: ContentConstraint(
            child: TransactionHistoryList(),
          ),
        ),
      ),
    ),
  );
  await tester.pump();
}

class _FakePhotonRepository implements PhotonRepository {
  List<PhotonTransaction> historyResult = [];
  Exception? shouldThrow;
  Completer<List<PhotonTransaction>>? pending;
  Completer<List<PhotonTransaction>>? secondPagePending;
  int historyCalls = 0;

  @override
  Future<List<PhotonTransaction>> getTransactionHistory({
    String? transactionType,
    int limit = 50,
    int offset = 0,
  }) async {
    historyCalls++;
    final throwed = shouldThrow;
    if (throwed != null) {
      throw throwed;
    }
    if (offset > 0) {
      final gate = secondPagePending;
      if (gate != null) {
        return gate.future;
      }
      return [];
    }
    final gate = pending;
    if (gate != null) {
      return gate.future;
    }
    return historyResult;
  }

  @override
  Future<PhotonBalance> getBalance() async => PhotonBalance(
        userId: 'u1',
        balance: 0,
        updatedAt: DateTime(2026, 9, 22),
      );

  @override
  Future<TransactionSummary> getTransactionSummary({int days = 30}) async =>
      TransactionSummary(
        totalIncome: 0,
        totalExpense: 0,
        netChange: 0,
        transactionCount: 0,
        byType: const {},
      );

  @override
  Future<Map<String, dynamic>> transferPhotons({
    required String recipientId,
    required int amount,
    String? message,
  }) =>
      throw UnimplementedError();
}

class _FakeRedeemRepository extends PhotonRedeemProRepository {
  _FakeRedeemRepository({
    required this.overview,
    required this.result,
  }) : super(_UnusedApiClient());

  PhotonRedeemProOverview overview;
  PhotonRedeemProResult result;

  @override
  Future<PhotonRedeemProOverview> getOverview() async => overview;

  @override
  Future<PhotonRedeemProResult> redeem() async => result;
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
