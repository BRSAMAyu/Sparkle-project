import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_button_v2.dart';
import 'package:sparkle/core/state/staged_loading.dart';
import 'package:sparkle/core/state/surface_state.dart';
import 'package:sparkle/core/state/surface_state_injection.dart';
import 'package:sparkle/core/state/surface_state_view.dart';

import '../../shared/i18n_test_helper.dart';

/// U-06 统一状态组件行为测试：每个矩阵相位真实泵入渲染树验证，
/// 失败相位必出现可操作下一步（死胡同守卫），等待相位 >500ms 升格
/// stage feedback（无终结态 spinner）。
void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  Widget shell(Widget child) => ProviderScope(
        child: testMaterialApp(home: Scaffold(body: child)),
      );

  /// 卸载树：让 StagedSurfaceLoader 的 Timer/动画随 dispose 取消，
  /// 避免测试收尾「pending timer」。
  Future<void> unmount(WidgetTester tester) async {
    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pump();
  }

  group('SurfaceStateView 失败族渲染', () {
    for (final phase in SurfaceStateMatrix.failurePhases) {
      testWidgets(
        '${phase.name}: 无回调也必有可操作下一步（死胡同守卫）',
        (tester) async {
          await tester.pumpWidget(
            shell(SurfaceStateView(state: SurfaceState(phase))),
          );
          await tester.pump(const Duration(milliseconds: 700));
          // 至少一个可点动作：失败相位为 SparkleButton；longRunning 为
          // 分阶加载升格后的「返回」退路（同为 TextButton）。
          final hasAction =
              find.byType(SparkleButton).evaluate().isNotEmpty ||
                  find.byType(TextButton).evaluate().isNotEmpty;
          expect(hasAction, isTrue, reason: '${phase.name} 出现死胡同');
          expect(tester.takeException(), isNull);
          await unmount(tester);
        },
      );
    }

    testWidgets('默认下一步含重试的相位：渲染统一「重试」且可触发', (tester) async {
      final retryPhases = SurfaceStateMatrix.failurePhases
          .where(
            (p) => SurfaceStateMatrix.defaultNextSteps(p)
                .contains(SurfaceNextStep.retry),
          )
          .toList();
      expect(retryPhases.length, greaterThanOrEqualTo(5));
      for (final phase in retryPhases) {
        var retried = false;
        await tester.pumpWidget(
          shell(
            SurfaceStateView(
              state: SurfaceState(phase),
              onRetry: () => retried = true,
            ),
          ),
        );
        await tester.pump();
        final retryButton = find.widgetWithText(SparkleButton, '重试');
        expect(retryButton, findsOneWidget, reason: '${phase.name} 未渲染重试');
        await tester.tap(retryButton);
        expect(retried, isTrue, reason: '${phase.name} 重试未触发');
        await unmount(tester);
      }
    });

    testWidgets('自定义 message 优先于默认词典文案', (tester) async {
      await tester.pumpWidget(
        shell(
          SurfaceStateView(
            state: const SurfaceState(
              SurfacePhase.conflict,
              message: '自定义冲突文案',
            ),
            onRefresh: () {},
          ),
        ),
      );
      await tester.pump();
      expect(find.text('自定义冲突文案'), findsOneWidget);
      await unmount(tester);
    });
  });

  group('等待族 stage feedback（500ms 阈值）', () {
    testWidgets(
      'loading 前 500ms 只出骨架无文案；>500ms 升格阶段文案',
      (tester) async {
        await tester.pumpWidget(shell(const StagedSurfaceLoader()));
        await tester.pump(const Duration(milliseconds: 100));
        expect(
          find.text('正在准备…'),
          findsNothing,
          reason: '<500ms 不应出现 stage 文案',
        );

        await tester.pump(const Duration(milliseconds: 500));
        expect(
          find.text('正在准备…'),
          findsOneWidget,
          reason: '>500ms 必须给 stage feedback',
        );

        // 阶段推进：下一阶段文案出现（间隔 2600ms）。
        await tester.pump(const Duration(milliseconds: 2600));
        expect(find.text('正在加载，内容马上就绪'), findsOneWidget);
        await unmount(tester);
      },
    );

    testWidgets('长等待提示（可离开）随后出现', (tester) async {
      await tester.pumpWidget(shell(const StagedSurfaceLoader()));
      await tester.pump(const Duration(milliseconds: 700));
      expect(find.text('仍在处理中——你可以先离开，回来后进度会保留'), findsOneWidget);
      await unmount(tester);
    });

    testWidgets('compact 形态同样在 >500ms 出文案', (tester) async {
      await tester.pumpWidget(
        shell(const StagedSurfaceLoader(compact: true, height: 72)),
      );
      await tester.pump(const Duration(milliseconds: 700));
      expect(find.byType(LinearProgressIndicator), findsOneWidget);
      expect(find.text('正在准备…'), findsOneWidget);
      await unmount(tester);
    });

    testWidgets('提供 onLeave 时长等待渲染「返回」退路', (tester) async {
      await tester.pumpWidget(shell(StagedSurfaceLoader(onLeave: () {})));
      await tester.pump(const Duration(milliseconds: 700));
      expect(find.widgetWithText(TextButton, '返回'), findsOneWidget);
      await unmount(tester);
    });

    testWidgets('注入阶段文案序列按序推进', (tester) async {
      await tester.pumpWidget(
        shell(
          const StagedSurfaceLoader(
            stageMessages: ['阶段A', '阶段B'],
            stageInterval: Duration(milliseconds: 300),
          ),
        ),
      );
      await tester.pump(const Duration(milliseconds: 600));
      expect(find.text('阶段A'), findsOneWidget);
      await tester.pump(const Duration(milliseconds: 300));
      expect(find.text('阶段B'), findsOneWidget);
      await unmount(tester);
    });

    testWidgets('StagedStageHint 500ms 前不可见、之后可见', (tester) async {
      await tester.pumpWidget(shell(const StagedStageHint()));
      await tester.pump(const Duration(milliseconds: 100));
      expect(find.text('正在加载，内容马上就绪'), findsNothing);
      await tester.pump(const Duration(milliseconds: 500));
      expect(find.text('正在加载，内容马上就绪'), findsOneWidget);
      await unmount(tester);
    });
  });

  group('SurfaceStateGate 分派 + 注入拦截', () {
    testWidgets('success → content；empty → emptyBuilder', (tester) async {
      await tester.pumpWidget(
        shell(
          SurfaceStateGate(
            surfaceId: 'community.feed',
            state: const SurfaceState(SurfacePhase.success),
            content: (_) => const Text('CONTENT'),
            emptyBuilder: (_) => const Text('EMPTY'),
          ),
        ),
      );
      await tester.pump();
      expect(find.text('CONTENT'), findsOneWidget);

      await tester.pumpWidget(
        shell(
          SurfaceStateGate(
            surfaceId: 'community.feed',
            state: const SurfaceState(SurfacePhase.empty),
            content: (_) => const Text('CONTENT'),
            emptyBuilder: (_) => const Text('EMPTY'),
          ),
        ),
      );
      await tester.pump();
      expect(find.text('EMPTY'), findsOneWidget);
    });

    testWidgets('empty 无 emptyBuilder → 通用 EmptyState，绝不调 content',
        (tester) async {
      await tester.pumpWidget(
        shell(
          SurfaceStateGate(
            surfaceId: 'community.feed',
            state: const SurfaceState(SurfacePhase.empty),
            content: (_) => const Text('CONTENT'),
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.text('CONTENT'), findsNothing);
    });

    testWidgets('loading → 分阶加载组件', (tester) async {
      await tester.pumpWidget(
        shell(
          SurfaceStateGate(
            surfaceId: 'community.feed',
            state: const SurfaceState(SurfacePhase.loading),
            content: (_) => const Text('CONTENT'),
          ),
        ),
      );
      await tester.pump(const Duration(milliseconds: 700));
      expect(find.text('CONTENT'), findsNothing);
      expect(find.byType(StagedSurfaceLoader), findsOneWidget);
      await unmount(tester);
    });

    testWidgets('debug 注入覆盖真实状态（走同一渲染分支）', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            surfaceStateOverridesProvider.overrideWith(
              (ref) => <String, SurfaceState>{
                'community.feed':
                    const SurfaceState(SurfacePhase.permissionDenied),
              },
            ),
          ],
          child: testMaterialApp(
            home: SurfaceStateGate(
              surfaceId: 'community.feed',
              state: const SurfaceState(SurfacePhase.success),
              content: (_) => const Text('CONTENT'),
              onOpenSettings: () {},
            ),
          ),
        ),
      );
      await tester.pump();
      expect(find.text('CONTENT'), findsNothing, reason: '注入应压过真实 success');
      expect(find.byType(SurfaceStateView), findsOneWidget);
      // permissionDenied 默认下一步 = openSettings（去开启权限）。
      expect(find.text('去开启权限'), findsOneWidget);
      await unmount(tester);
    });

    testWidgets('无注入时直通真实状态', (tester) async {
      await tester.pumpWidget(
        shell(
          SurfaceStateGate(
            surfaceId: 'community.feed',
            state: const SurfaceState(SurfacePhase.success),
            content: (_) => const Text('CONTENT'),
          ),
        ),
      );
      await tester.pump();
      expect(find.text('CONTENT'), findsOneWidget);
    });

    test('注入解析：未知表面返回 null', () {
      final overrides = <String, SurfaceState>{
        'a': const SurfaceState(SurfacePhase.offline),
      };
      expect(resolveInjectedSurfaceState(overrides, 'b'), isNull);
    });

    test('SurfaceStateInjector：inject/clear/clearAll 语义', () {
      var current = const <String, SurfaceState>{};
      current = SurfaceStateInjector.inject(
        current,
        'x',
        SurfaceFailureScenario.conflict,
      );
      expect(current['x']?.phase, SurfacePhase.conflict);
      current = SurfaceStateInjector.clear(current, 'x');
      expect(current.containsKey('x'), isFalse);
      current = SurfaceStateInjector.inject(
        current,
        'x',
        SurfaceFailureScenario.networkError,
      );
      current = SurfaceStateInjector.clearAll(current);
      expect(current, isEmpty);
    });

    test('失败场景目录 ≥12 且与矩阵失败族同源', () {
      expect(
        SurfaceFailureScenario.values.length,
        greaterThanOrEqualTo(12),
      );
      for (final scenario in SurfaceFailureScenario.values) {
        expect(
          SurfaceStateMatrix.isFailure(scenario.phase),
          isTrue,
          reason: '${scenario.name} 应是失败族',
        );
      }
    });
  });
}
