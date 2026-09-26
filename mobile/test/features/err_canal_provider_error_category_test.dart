import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/display/lexicon/error_lexicon.dart';
import 'package:sparkle/features/plan/data/repositories/plan_repository.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/sprint_actions_provider.dart';
import 'package:sparkle/features/seed_library/data/repositories/seed_library_repository.dart';
import 'package:sparkle/features/seed_library/presentation/marketplace/marketplace_provider.dart';
import 'package:sparkle/features/seed_library/presentation/marketplace/marketplace_repository.dart';
import 'package:sparkle/features/seed_library/presentation/providers/seed_library_provider.dart';
import 'package:sparkle/features/shop/data/repositories/shop_repository.dart';
import 'package:sparkle/features/shop/presentation/providers/shop_provider.dart';
import 'package:sparkle/features/task/data/repositories/subtask_repository.dart';
import 'package:sparkle/features/task/presentation/providers/subtask_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/l10n/app_localizations_zh.dart';
import 'package:sparkle/shared/entities/subtask_model.dart';

/// ERR-CANAL（A-SPEC3 N15 主路径批）验收：
///
/// 五域 provider 的 UI 可达 error 位改存类型化类别（UiErrorCategory），
/// 渲染侧经 error_lexicon owner 出人话。本文件钉两件事：
/// 1. 赋值面——真实 notifier 走异常路径后，`state.error` 是类别值，
///    不再携带 `e.toString()` 原文（`toString()` 产物不回读为文案）；
/// 2. 渲染面——`uiErrorMessage(zh, category)` 产物不含异常痕迹
///    （'Exception:' / 'Instance of'），落进 Text 的是人话。
void main() {
  final zh = AppLocalizationsZh();

  group('N15 赋值面：五域 provider error 位 = UiErrorCategory', () {
    test('subtask: load/add 异常 → error = network 类别', () async {
      final notifier = SubtaskNotifier(_FakeSubtaskRepo(), 'task-1');
      // 构造器自动 loadSubtasks() 也走同款 catch。
      await Future<void>.delayed(Duration.zero);
      expect(notifier.state.error, UiErrorCategory.network);

      await notifier.addSubtask(
        const SubTaskCreate(title: '随便什么标题'),
      );
      expect(notifier.state.error, UiErrorCategory.network);
    });

    test('seed_library: loadLibraries 异常 → error = network 类别', () async {
      final notifier = SeedLibraryListNotifier(_FakeSeedLibraryRepo());
      await notifier.loadLibraries();
      expect(notifier.state.error, UiErrorCategory.network);
    });

    test('seed_library/subscriptions: loadSubscriptions 异常 → 类别', () async {
      final notifier = SubscriptionsNotifier(_FakeSeedLibraryRepo());
      await notifier.loadSubscriptions();
      expect(notifier.state.error, UiErrorCategory.network);
    });

    test('marketplace: 构造器自动 refresh 异常 → error = network 类别',
        () async {
      final notifier = MarketplaceNotifier(_FakeMarketplaceRepo());
      // 构造器 unawaited(refresh())；让事件循环跑完 catch。
      await Future<void>.delayed(Duration.zero);
      await Future<void>.delayed(Duration.zero);
      expect(notifier.state.error, UiErrorCategory.network);
      expect(notifier.state.isLoading, isFalse);
    });

    test('shop: loadPurchaseHistory 异常 → error = network 类别', () async {
      final notifier = PurchaseHistoryNotifier(_FakeShopRepo());
      await notifier.loadPurchaseHistory();
      expect(notifier.state.error, UiErrorCategory.network);
    });

    test('sprint_actions: completeSprint 异常 → error = network 类别',
        () async {
      final container = ProviderContainer(
        overrides: [
          planListProvider.overrideWith(
            _ThrowingPlanNotifier.new,
          ),
        ],
      );
      addTearDown(container.dispose);

      final notifier = container.read(sprintActionsProvider.notifier);
      final ok = await notifier.completeSprint('plan-1');
      expect(ok, isFalse);
      expect(notifier.state.error, UiErrorCategory.network);
    });
  });

  group('N15 渲染面：类别 → 人话，无异常痕迹', () {
    test('uiErrorMessage(zh) 全类别不含 Exception:/Instance of 原文', () {
      for (final category in UiErrorCategory.values) {
        final message = uiErrorMessage(zh, category);
        expect(message, isNot(contains('Exception:')), reason: '$category');
        expect(message, isNot(contains('Instance of')), reason: '$category');
        expect(
          message.contains(category.toString()),
          isFalse,
          reason: '$category 文案不应含枚举 toString 产物',
        );
      }
    });

    testWidgets('渲染产物落进 Text 的是人话（network 类别样本）', (tester) async {
      const category = UiErrorCategory.network;
      await tester.pumpWidget(
        _CategoryProbeText(l10n: zh, category: category),
      );
      // 与 task_detail/subtask_list/shop/simulation 等渲染点同款表达式：
      // Text(uiErrorMessage(l10n, state.error!))。
      final rendered =
          tester.widget<Text>(find.byType(Text)).data ?? '';
      expect(rendered, uiErrorMessage(zh, category));
      expect(rendered, contains('网络'));
      expect(rendered, isNot(contains('Exception:')));
      expect(rendered, isNot(contains('Instance of')));
    });
  });
}

/// 渲染点同款表达式的最小探针（不逐屏重复搭五域脚手架；
/// 各屏接线由既有 widget 测试钉：task_list_screen_test 断言
/// 「服务器出现问题」，simulation/shop provider 测试断言类别直传）。
class _CategoryProbeText extends StatelessWidget {
  const _CategoryProbeText({required this.l10n, required this.category});

  final AppLocalizations l10n;
  final UiErrorCategory category;

  @override
  Widget build(BuildContext context) => MaterialApp(
      home: Scaffold(body: Text(uiErrorMessage(l10n, category))),
    );
}

// ---- 测试脚手架（noSuchMethod 兜底的最小假仓库：
// 任何方法调用即抛网络类异常，命中被测 provider 的 catch） ----

class _FakeSubtaskRepo implements SubtaskRepository {
  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw Exception('SocketException: fake connection refused');
}

class _FakeSeedLibraryRepo implements SeedLibraryRepository {
  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw Exception('SocketException: fake connection refused');
}

class _FakeMarketplaceRepo implements MarketplaceRepository {
  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw Exception('SocketException: fake connection refused');
}

class _FakeShopRepo implements ShopRepository {
  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw Exception('SocketException: fake connection refused');
}

class _ThrowingPlanNotifier extends PlanNotifier {
  _ThrowingPlanNotifier(Ref ref) : super(_FakePlanRepository(), ref);

  @override
  Future<void> archivePlan(String planId) async =>
      throw Exception('SocketException: archive failed');
}

class _FakePlanRepository implements PlanRepository {
  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnimplementedError('not used in this test');
}
