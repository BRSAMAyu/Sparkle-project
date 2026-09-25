import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_button_v2.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/state/staged_loading.dart';
import 'package:sparkle/core/state/surface_state.dart';
import 'package:sparkle/core/state/surface_state_injection.dart';
import 'package:sparkle/core/state/surface_state_view.dart';
import '../../shared/i18n_test_helper.dart';

/// U-06 核心表面状态矩阵覆盖率测试（验收：核心 surfaces ≥95% covered）。
///
/// 口径：登记表 [gateSurfaceIds] 的每个表面，经 `SurfaceStateGate` 对
/// STATE_MATRIX 全部 22 相位**真实泵入渲染树**逐相驱动；每相判定
/// 「非死胡同渲染」成立即记为覆盖。分阶接缝面（[stagedSeamIds]）由
/// 共享 StagedSurfaceLoader/StagedStageHint 承担 >500ms 升格语义，
/// 以组件行为断言覆盖。
void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  Future<double> driveSurfaceThroughMatrix(
    WidgetTester tester,
    String surfaceId,
  ) async {
    var covered = 0;
    for (final phase in SurfaceStateMatrix.allPhases) {
      await tester.pumpWidget(
        ProviderScope(
          child: testMaterialApp(
            home: Scaffold(
              body: SurfaceStateGate(
                surfaceId: surfaceId,
                state: SurfaceState(phase),
                content: (_) => const Text('SURFACE_CONTENT'),
                emptyBuilder: (_) => const Text('SURFACE_EMPTY'),
                onRetry: () {},
                onRefresh: () {},
                onBack: () {},
                onReauthenticate: () {},
                onOpenSettings: () {},
                onRespond: () {},
                onDismiss: () {},
                onReport: () {},
              ),
            ),
          ),
        ),
      );
      await tester.pump(const Duration(milliseconds: 700));

      var ok = false;
      switch (phase) {
        case SurfacePhase.success:
          ok = find.text('SURFACE_CONTENT').evaluate().isNotEmpty;
        case SurfacePhase.empty:
          ok = find.text('SURFACE_EMPTY').evaluate().isNotEmpty;
        case SurfacePhase.initial:
        case SurfacePhase.loading:
        case SurfacePhase.longRunning:
        case SurfacePhase.executing:
          ok = find.byType(StagedSurfaceLoader).evaluate().isNotEmpty;
        case SurfacePhase.partial:
        case SurfacePhase.offline:
        case SurfacePhase.reconnecting:
          // 非阻断横幅 + 矩阵默认动作（含死胡同守卫兜底）。
          ok = find.byType(SurfaceStateView).evaluate().isNotEmpty &&
              (find.byType(SparkleButton).evaluate().isNotEmpty ||
                  find.byType(TextButton).evaluate().isNotEmpty);
        case SurfacePhase.errorRecoverable:
        case SurfacePhase.errorTerminal:
        case SurfacePhase.permissionDenied:
        case SurfacePhase.authExpired:
        case SurfacePhase.modelUnavailable:
        case SurfacePhase.toolUnavailable:
        case SurfacePhase.awaitingClarification:
        case SurfacePhase.proposalPending:
        case SurfacePhase.awaitingUser:
        case SurfacePhase.conflict:
        case SurfacePhase.unknownOutcome:
        case SurfacePhase.cancelled:
        case SurfacePhase.revoked:
          ok = find.byType(SurfaceStateView).evaluate().isNotEmpty &&
              (find.byType(SparkleButton).evaluate().isNotEmpty ||
                  find.byType(TextButton).evaluate().isNotEmpty);
      }
      if (ok) covered++;
      // 卸载，避免 loader 的周期 Timer 泄漏进下一相位。
      await tester.pumpWidget(const SizedBox.shrink());
      await tester.pump();
    }
    return covered / SurfaceStateMatrix.allPhases.length;
  }

  test('STATE_MATRIX 全集 22 相位 = 覆盖率分母', () {
    expect(SurfaceStateMatrix.allPhases.length, 22);
    expect(coreSurfaceIds, isNotEmpty);
    expect(gateSurfaceIds.length + stagedSeamIds.length, coreSurfaceIds.length);
  });

  for (final surfaceId in gateSurfaceIds) {
    testWidgets('surface "$surfaceId": 矩阵覆盖率 ≥95%', (tester) async {
      final coverage = await driveSurfaceThroughMatrix(tester, surfaceId);
      expect(
        coverage,
        greaterThanOrEqualTo(0.95),
        reason: 'surface $surfaceId 矩阵覆盖率 $coverage < 0.95',
      );
      // 本实现按构造应达 100%——若跌破 1.0 说明闸门分派出现缺口。
      expect(coverage, 1.0, reason: 'surface $surfaceId 存在未覆盖相位');
    });
  }

  testWidgets('分阶接缝组件：等待族 500ms 升格语义（无终结 spinner）',
      (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        child: testMaterialApp(
          home: const Scaffold(
            body: Column(
              children: [
                StagedSurfaceLoader(compact: true, height: 72),
                StagedStageHint(),
              ],
            ),
          ),
        ),
      ),
    );
    await tester.pump(const Duration(milliseconds: 700));
    expect(find.byType(LinearProgressIndicator), findsOneWidget);
    expect(
      find.byType(CircularProgressIndicator),
      findsNothing,
      reason: '统一等待组件不得渲染裸圆形 spinner',
    );
    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pump();
  });

  testWidgets('统一组件等待/失败渲染全程零裸 CircularProgressIndicator',
      (tester) async {
    for (final phase in SurfaceStateMatrix.allPhases) {
      await tester.pumpWidget(
        ProviderScope(
          child: testMaterialApp(
            home: Scaffold(
              body: SurfaceStateView(
                state: SurfaceState(phase),
                onRetry: () {},
              ),
            ),
          ),
        ),
      );
      await tester.pump(const Duration(milliseconds: 700));
      expect(
        find.byType(CircularProgressIndicator),
        findsNothing,
        reason: '${phase.name} 出现裸 spinner（终结态风险形）',
      );
      await tester.pumpWidget(const SizedBox.shrink());
      await tester.pump();
    }
  });

  testWidgets('EmptyState 通用兜底可达（empty 相位的统一空语义）',
      (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        child: testMaterialApp(
          home: Scaffold(
            body: SurfaceStateGate(
              surfaceId: 'coverage.probe',
              state: const SurfaceState(SurfacePhase.empty),
              content: (_) => const Text('X'),
            ),
          ),
        ),
      ),
    );
    await tester.pump();
    expect(find.byType(EmptyState), findsOneWidget);
    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pump();
  });
}
