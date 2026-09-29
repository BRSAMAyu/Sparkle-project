import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/pixel/pixel_state.dart';
import 'package:sparkle/core/design/widgets/semantic_motion_widgets.dart';
import 'package:sparkle/features/insights/data/models/evidence_insight_card.dart';
import 'package:sparkle/features/insights/presentation/widgets/evidence_insight_card.dart';
import 'package:sparkle/features/recovery/data/models/stuck_journey_models.dart';
import 'package:sparkle/features/recovery/data/repositories/stuck_journey_repository.dart';
import 'package:sparkle/features/recovery/presentation/providers/recovery_calibration_provider.dart';
import 'package:sparkle/features/recovery/presentation/widgets/recovery_calibration_section.dart';
import 'package:sparkle/features/recovery/presentation/widgets/stuck_journey_sheet.dart';
import 'package:sparkle/features/task/data/repositories/action_proposal_repository.dart';
import 'package:sparkle/shared/widgets/action_proposal/proposal_card_models.dart';

import '../../shared/i18n_test_helper.dart';

/// V4-FIX-569 · 三个 S01 implicit 一次性组件的产品接线微测（每接线一正一反）。
///
/// 接线位（F03 R1 低成本样本，Q05 三-b leader 裁决）：
///
/// 1. [SparkleProposalEnter] × 卡住 sheet intervention 提案卡
///    （SCREEN_FAMILIES L7「一个决策问题和提案」）——挂载一次性抬起；
/// 2. [SparkleReceiptSwap] × recovery 校准区 committed 相（全产品唯一
///    成功面孔徽章面）——回执锚定 160ms 替换；同 key 重投不重播、首挂载
///    不播、在途/取消零成功徽章载体；
/// 3. [SparkleEvidenceStamp] × D-07 证据洞察卡类型印章（SCREEN_FAMILIES
///    L16「像素印章标记类型，不给 AI 推断盖认证章」）——160ms 压印入场。
///
/// FIX-565 同族教训：接线必须带覆盖——本文件即覆盖面；摘除任一接线调用，
/// 对应组必红（mutation 自验 ×3 见证据 run_receipt）。
///
/// reduce-motion 两格（Q06 矩阵抽样：卡住家族 + 洞察家族「减少动态」态）
/// 由 P-1 / R-4 / E- 承担：静态分支语义等价（内容完整在场、无动画壳）。

// ---------------------------------------------------------------------------
// fixtures —— stuck journey（P 组）
// ---------------------------------------------------------------------------

/// 只读 journey 仓库：startJourney 返回预置载荷（answer/correct 测内不达）。
class _StaticJourneyRepository implements StuckJourneyRepository {
  _StaticJourneyRepository(this.startPayload);

  final Map<String, dynamic> startPayload;

  @override
  Future<StuckJourneyPayload> startJourney({
    required String surface,
    String? goalId,
    String? taskId,
  }) async =>
      StuckJourneyPayload.fromJson(startPayload);

  @override
  Future<StuckJourneyPayload> answerQuestion({
    required String surface,
    required String questionId,
    required String branchKey,
    String? goalId,
    String? taskId,
  }) async =>
      StuckJourneyPayload.fromJson(startPayload);

  @override
  Future<StuckJourneyCorrectionResult> correct({
    required String surface,
    required String frictionType,
    String? interventionKey,
    String? goalId,
    String? taskId,
    String? reasonText,
  }) async =>
      StuckJourneyCorrectionResult.fromJson(<String, dynamic>{
        'correction_id': 'c-fix569',
        'receipt': <String, dynamic>{},
        'journey': startPayload,
      });
}

Map<String, dynamic> _interventionPayload() => <String, dynamic>{
      'version': 'stuck_journey.v1',
      'surface': 'action',
      'outcome': 'act',
      'friction_type': 'skill',
      'question': null,
      'main_intervention': <String, dynamic>{
        'type': 'practice',
        'nominated': <String>['practice', 'explain'],
        'friction_type': 'skill',
        'uncertain': false,
        'adjusted_by_correction': false,
      },
      'uncertain': false,
      'context': <String, dynamic>{
        'goal': <String, dynamic>{'id': 'g1', 'title': '线代一轮复习'},
        'task': <String, dynamic>{'id': 't1', 'title': '特征值练习'},
        'recent_failures': <String, dynamic>{'count': 3, 'titles': <String>[]},
        'days_since_progress': 6,
      },
      'receipt': <String, dynamic>{},
      'annotations': <String, dynamic>{},
    };

/// abstain：无问题无提案（P-2 反例：树中不应有提案入场组件）。
Map<String, dynamic> _abstainPayload() => <String, dynamic>{
      ..._interventionPayload(),
      'outcome': 'abstain',
      'main_intervention': null,
    };

// ---------------------------------------------------------------------------
// fixtures —— recovery calibration（R 组）
// ---------------------------------------------------------------------------

Map<String, dynamic> _pendingProjection(String id) => <String, dynamic>{
      'proposal_id': id,
      'status': 'PENDING',
      'command_type': 'task.update_fields',
      'source': 'task',
      'summary': '仅本次：今天只有十五分钟',
      'diff': <String, dynamic>{
        'before': <String, dynamic>{'estimated_minutes': 40},
        'after': <String, dynamic>{'estimated_minutes': 15},
        'changed_fields': <String>['estimated_minutes'],
      },
    };

Map<String, dynamic> _committedMutationResponse({String receiptId = 'r-569'}) =>
    <String, dynamic>{
      'proposal': <String, dynamic>{
        ..._pendingProjection('p1'),
        'status': 'COMMITTED',
        'receipt': <String, dynamic>{
          'receipt_id': receiptId,
          'status': 'COMMITTED',
          'command_type': 'task.update_fields',
        },
      },
      'applied': true,
      'already_committed': false,
    };

Map<String, dynamic> _cancelledMutationResponse() => <String, dynamic>{
      'proposal': <String, dynamic>{
        ..._pendingProjection('p1'),
        'status': 'CANCELLED',
      },
    };

/// 记录型假仓库（X-03 契约面；create→PENDING / approve→注入回执）。
class _FakeProposalRepository implements ActionProposalRepository {
  Map<String, dynamic> createResponse = _pendingProjection('p1');
  Map<String, dynamic>? approveResult;
  Map<String, dynamic>? cancelResponse = _cancelledMutationResponse();
  Completer<Map<String, dynamic>?>? approveGate;

  final List<String> approveCalls = <String>[];

  @override
  Future<Map<String, dynamic>> createAdjustmentProposal({
    required String taskId,
    required Map<String, dynamic> fields,
    required String idempotencyKey,
    String? summary,
  }) async =>
      createResponse;

  @override
  Future<Map<String, dynamic>?> getProposal(String proposalId) async => null;

  @override
  Future<List<ActionProposalCardData>> listForSubject(
    String subjectId, {
    String? status,
  }) async =>
      const <ActionProposalCardData>[];

  @override
  Future<Map<String, dynamic>?> approve(
    String proposalId,
    String idempotencyKey,
  ) async {
    approveCalls.add(proposalId);
    final gate = approveGate;
    if (gate != null && !gate.isCompleted) return gate.future;
    return approveResult;
  }

  @override
  Future<Map<String, dynamic>?> cancel(
    String proposalId,
    String idempotencyKey,
  ) async =>
      cancelResponse;

  @override
  Future<Map<String, dynamic>?> reject(
    String proposalId,
    String idempotencyKey, {
    String? reason,
  }) async =>
      null;
}

/// 校准区Harness：直接挂 [RecoveryCalibrationSection]（任务锚点 40 分钟基
/// 线），经 container 直驱控制器相机（不经 UI tap，聚焦接线本身）。
Future<ProviderContainer> _pumpCalibrationSection(
  WidgetTester tester,
  _FakeProposalRepository repo, {
  bool disableAnimations = false,
}) async {
  final container = ProviderContainer(
    overrides: [
      actionProposalRepositoryProvider.overrideWithValue(repo),
    ],
  );
  addTearDown(container.dispose);
  const section = RecoveryCalibrationSection(
    request: StuckJourneyRequest(surface: 'test', taskId: 't1'),
    baselineMinutes: 40,
  );
  Widget home = const Scaffold(
    body: SingleChildScrollView(child: section),
  );
  if (disableAnimations) {
    home = MediaQuery(
      data: const MediaQueryData(disableAnimations: true),
      child: home,
    );
  }
  await tester.pumpWidget(
    UncontrolledProviderScope(
      container: container,
      child: testMaterialApp(home: home),
    ),
  );
  await tester.pumpAndSettle();
  return container;
}

/// 相机驱动：输入 → 仅本次 → 生成提案（diffReview）。
Future<void> _driveToDiffReview(
  WidgetTester tester,
  RecoveryCalibrationController notifier,
) async {
  notifier.submitConstraint('今天只有十五分钟');
  await tester.pumpAndSettle(); // → scopeChoice
  notifier.chooseThisTime();
  await tester.pumpAndSettle(); // → adjusting
  await notifier.buildAdjustment();
  await tester.pumpAndSettle(); // → diffReview（PENDING 提案在场）
}

/// 替换壳内在航 Opacity（<1 = 有淡入在播）。
List<double> _inFlightOpacities(WidgetTester tester, Finder swapFinder) =>
    tester
        .widgetList<Opacity>(
          find.descendant(of: swapFinder, matching: find.byType(Opacity)),
        )
        .map((o) => o.opacity)
        .where((v) => v < 1)
        .toList();

// ---------------------------------------------------------------------------
// fixtures —— evidence insight card（E 组）
// ---------------------------------------------------------------------------

Map<String, dynamic> _frictionCardJson() => <String, dynamic>{
      'id': 'friction_pattern:execution_friction',
      'kind': 'friction_pattern',
      'fact': <String, dynamic>{
        'friction_tag': 'execution_friction',
        'exposures': 3,
        'accepted': 1,
        'edited': 0,
        'rejected': 1,
      },
      'interpretation': <String, dynamic>{
        'friction_tag': 'execution_friction',
        'role': 'most_frequent',
      },
      'uncertainty': <String, dynamic>{
        'qualifiers': <String>[
          'counts_only_from_lifecycle_events',
          'small_sample',
        ],
        'samples': 3,
      },
      'evidence': <Map<String, dynamic>>[
        <String, dynamic>{
          'label_key': 'evidence_directive_log',
          'deep_link': '/learning/insights/directives',
          'refs': <String>['aurora_abc'],
        },
      ],
      'implication': <String, dynamic>{
        'action_key': 'review_directives',
        'deep_link': '/learning/insights/directives',
      },
    };

/// 卡住 sheet 主体 Harness（载荷由注入仓库预置；[disableAnimations] 钉
/// reduce-motion 静态分支格）。
Future<void> _pumpStuckSheet(
  WidgetTester tester,
  Map<String, dynamic> payload, {
  bool disableAnimations = false,
}) async {
  const bodyContent = StuckJourneySheetBody(
    request: StuckJourneyRequest(surface: 'action', taskId: 't1'),
  );
  Widget body = const Scaffold(
    body: SingleChildScrollView(child: bodyContent),
  );
  if (disableAnimations) {
    body = MediaQuery(
      data: const MediaQueryData(disableAnimations: true),
      child: body,
    );
  }
  await tester.pumpWidget(
    testMaterialApp(
      home: ProviderScope(
        overrides: [
          stuckJourneyRepositoryProvider
              .overrideWithValue(_StaticJourneyRepository(payload)),
        ],
        child: body,
      ),
    ),
  );
}

void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  // ═══ P 组：SparkleProposalEnter × 卡住 sheet intervention 提案卡 ═══

  group('P 提案出现接线（卡住 sheet intervention 卡）', () {
    testWidgets('P+ 挂载一次性抬起入场：80ms 在航（淡入在播），落定完全可见',
        (tester) async {
      await _pumpStuckSheet(tester, _interventionPayload());
      // 载荷就绪 → ready pane 挂载，入场动画起步（t≈0）。
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 80));

      final enterFinder = find.byType(SparkleProposalEnter);
      expect(enterFinder, findsOneWidget);
      // 动画壳在场（非 reduce-motion 路径）。
      expect(
        find.descendant(
          of: enterFinder,
          matching: find.byType(TweenAnimationBuilder<double>),
        ),
        findsOneWidget,
      );
      // 200ms 预算在航：80ms 处淡入进行中（0 < opacity < 1）。
      final mid = _inFlightOpacities(tester, enterFinder);
      expect(mid, isNotEmpty, reason: '80ms 处提案入场淡入应仍在航');
      // 动画不截留内容：提案卡文本已在语义树（读屏不等动画）。
      expect(find.text('用一个练习把方法跑一遍'), findsOneWidget);

      await tester.pumpAndSettle();
      // 落定：完全不透明（纸面抬起落定），壳仍在树（不残留调度帧由 S01 钉）。
      final settled = tester
          .widgetList<Opacity>(
            find.descendant(
              of: enterFinder,
              matching: find.byType(Opacity),
            ),
          )
          .map((o) => o.opacity);
      expect(settled, isNotEmpty);
      expect(settled.every((v) => v == 1.0), isTrue);
    });

    testWidgets('P- reduce-motion：静态分支直落终态，不装动画壳（Q06 卡住家族'
        '「减少动态」格）', (tester) async {
      await _pumpStuckSheet(
        tester,
        _interventionPayload(),
        disableAnimations: true,
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      final enterFinder = find.byType(SparkleProposalEnter);
      expect(enterFinder, findsOneWidget);
      // 静态分支：无动画壳、无透明度中间态（信息等价、零在航）。
      expect(
        find.descendant(
          of: enterFinder,
          matching: find.byType(TweenAnimationBuilder<double>),
        ),
        findsNothing,
      );
      expect(_inFlightOpacities(tester, enterFinder), isEmpty);
      // 提案完整可见（等价信息不丢失）。
      expect(find.text('用一个练习把方法跑一遍'), findsOneWidget);
    });

    testWidgets('P- 反（取消/无提案）：abstain 载荷树中无提案入场组件',
        (tester) async {
      await _pumpStuckSheet(tester, _abstainPayload());
      await tester.pumpAndSettle();
      // 无提案（main_intervention == null）→ 入场组件结构性缺席，不出装饰位。
      expect(find.byType(SparkleProposalEnter), findsNothing);
    });
  });

  // ═══ R 组：SparkleReceiptSwap × recovery 校准区 committed 相 ═══

  group('R 回执替换接线（校准区成功面孔）', () {
    testWidgets('R+ 确认→回执到场：一次 160ms 淡入替换（在航可测），壳包裹'
        '成功徽章', (tester) async {
      final repo = _FakeProposalRepository()
        ..approveResult = _committedMutationResponse();
      final container = await _pumpCalibrationSection(tester, repo);
      const args = RecoveryCalibrationArgs(taskId: 't1', baselineMinutes: 40);
      final notifier = container.read(recoveryCalibrationProvider(args).notifier);

      // 输入相首挂载：替换壳在场但零动画（首挂载直落终态）。
      final swapFinder = find.byType(SparkleReceiptSwap);
      expect(swapFinder, findsOneWidget);
      expect(
        find.descendant(
          of: swapFinder,
          matching: find.byType(TweenAnimationBuilder<double>),
        ),
        findsNothing,
      );

      await _driveToDiffReview(tester, notifier);
      // 提案相（无回执）：仍零在航、零成功徽章。
      expect(_inFlightOpacities(tester, swapFinder), isEmpty);
      expect(find.byType(PixelSuccessBadge), findsNothing);

      await notifier.confirmAdjustment(); // 回执 r-569 到场 → key 变化
      await tester.pump(); // 替换代际推进 → 动画起步
      await tester.pump(const Duration(milliseconds: 60));
      // 160ms 预算在航：60ms 处淡入进行中。
      expect(
        _inFlightOpacities(tester, swapFinder),
        isNotEmpty,
        reason: '回执到场 60ms 处替换淡入应仍在航',
      );

      await tester.pumpAndSettle();
      // 落定：成功面孔 + 回执号可见；160ms 替换壳是成功徽章的祖先
      //（mutation：摘壳 → 本断言必红）。
      expect(find.byType(PixelSuccessBadge), findsOneWidget);
      expect(find.textContaining('回执 r-569'), findsOneWidget);
      final shells = tester.widgetList<TweenAnimationBuilder<double>>(
        find.ancestor(
          of: find.byType(PixelSuccessBadge),
          matching: find.byType(TweenAnimationBuilder<double>),
        ),
      );
      expect(
        shells.any((s) => s.duration == const Duration(milliseconds: 160)),
        isTrue,
        reason: '回执替换壳（receiptReplace 160ms）应包裹成功面孔',
      );
    });

    testWidgets('R- 同回执重建不重播（重投/重放语义在产品面成立）', (tester) async {
      final repo = _FakeProposalRepository()
        ..approveResult = _committedMutationResponse();
      final container = await _pumpCalibrationSection(tester, repo);
      const args = RecoveryCalibrationArgs(taskId: 't1', baselineMinutes: 40);
      final notifier = container.read(recoveryCalibrationProvider(args).notifier);

      await _driveToDiffReview(tester, notifier);
      await notifier.confirmAdjustment();
      await tester.pumpAndSettle(); // 替换播完落定

      // 同配置新实例重建（didUpdateWidget 同 key）→ 不重播：40ms 处（若重播
      // 必在航）零透明度中间态。容器不变 → 元素原地更新（非重挂载）。
      const replaySection = RecoveryCalibrationSection(
        request: StuckJourneyRequest(surface: 'test', taskId: 't1'),
        baselineMinutes: 40,
      );
      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: testMaterialApp(
            home: const Scaffold(
              body: SingleChildScrollView(child: replaySection),
            ),
          ),
        ),
      );
      await tester.pump(const Duration(milliseconds: 40));
      expect(
        _inFlightOpacities(tester, find.byType(SparkleReceiptSwap)),
        isEmpty,
        reason: '同 key 重投不得重播替换',
      );
      // 文本状态仍恢复：committed 相内容仍在场。
      expect(find.byType(PixelSuccessBadge), findsOneWidget);
      expect(find.textContaining('回执 r-569'), findsOneWidget);
    });

    testWidgets('R- 反（门拒）：回执到场之前（在途相）零成功徽章零替换动画',
        (tester) async {
      final gate = Completer<Map<String, dynamic>?>();
      final repo = _FakeProposalRepository()..approveGate = gate;
      final container = await _pumpCalibrationSection(tester, repo);
      const args = RecoveryCalibrationArgs(taskId: 't1', baselineMinutes: 40);
      final notifier = container.read(recoveryCalibrationProvider(args).notifier);

      await _driveToDiffReview(tester, notifier);
      // 确认在途（approve 挂起）——不 await；在途相有 loading 指示器
      //（永不 settle），用定长 pump（既有回执门测试同款口径）。
      unawaited(notifier.confirmAdjustment());
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      // 门拒时序钉：在途相零成功面孔、零在航替换。
      expect(find.byType(PixelSuccessBadge), findsNothing);
      expect(find.textContaining('已按本次约束落账'), findsNothing);
      expect(
        _inFlightOpacities(tester, find.byType(SparkleReceiptSwap)),
        isEmpty,
      );

      // 回执到场 → 才有替换与成功面孔（R+ 同一门，此处只钉时序反例）。
      gate.complete(_committedMutationResponse(receiptId: 'r-late'));
      await tester.pumpAndSettle();
      expect(find.byType(PixelSuccessBadge), findsOneWidget);
    });

    testWidgets('R- 反（取消）：取消提案 → 回到输入相，零成功徽章零回执',
        (tester) async {
      final repo = _FakeProposalRepository();
      final container = await _pumpCalibrationSection(tester, repo);
      const args = RecoveryCalibrationArgs(taskId: 't1', baselineMinutes: 40);
      final notifier = container.read(recoveryCalibrationProvider(args).notifier);

      await _driveToDiffReview(tester, notifier);
      await notifier.cancelAdjustment();
      await tester.pumpAndSettle();

      // 取消即回输入相：无成功徽章载体、无 committed 文案、无回执号。
      expect(find.byType(PixelSuccessBadge), findsNothing);
      expect(find.textContaining('已按本次约束落账'), findsNothing);
      expect(find.textContaining('回执 r-'), findsNothing);
      // 输入相原样在场（取消回到原任务语义）。
      expect(
        find.byKey(const Key('recovery-calibration-input-field')),
        findsOneWidget,
      );
    });

    testWidgets('R- reduce-motion：回执到场即时完成，无动画壳（Q06 卡住家族'
        '「减少动态」格）', (tester) async {
      final repo = _FakeProposalRepository()
        ..approveResult = _committedMutationResponse();
      final container = await _pumpCalibrationSection(
        tester,
        repo,
        disableAnimations: true,
      );
      const args = RecoveryCalibrationArgs(taskId: 't1', baselineMinutes: 40);
      final notifier = container.read(recoveryCalibrationProvider(args).notifier);

      await _driveToDiffReview(tester, notifier);
      await notifier.confirmAdjustment();
      await tester.pump(); // 状态相重建
      await tester.pump(const Duration(milliseconds: 40));

      // 静态分支：即时替换完成——零在航透明度、committed 内容完整在场。
      expect(
        _inFlightOpacities(tester, find.byType(SparkleReceiptSwap)),
        isEmpty,
      );
      expect(find.byType(PixelSuccessBadge), findsOneWidget);
      expect(find.textContaining('回执 r-569'), findsOneWidget);
    });
  });

  // ═══ E 组：SparkleEvidenceStamp × 证据洞察卡类型印章 ═══

  group('E 证据印章接线（D-07 证据洞察卡类型印）', () {
    testWidgets('E+ 压印入场：60ms 在航（scale >1.00 <1.12 淡入在播），落定'
        '全尺寸；文字只标类型不认证', (tester) async {
      final card = EvidenceInsightCardData.fromJson(_frictionCardJson());
      await tester.pumpWidget(
        testMaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(child: EvidenceInsightCardWidget(card: card)),
          ),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 60));

      final stampFinder = find.byType(SparkleEvidenceStamp);
      expect(stampFinder, findsOneWidget);
      // 160ms 预算在航：scale ∈ (1.00, 1.12) 压印进行中。
      final scales = tester
          .widgetList<Transform>(
            find.descendant(of: stampFinder, matching: find.byType(Transform)),
          )
          .map((t) => t.transform.getMaxScaleOnAxis())
          .where((s) => s > 1.0 && s < 1.12);
      expect(scales, isNotEmpty, reason: '60ms 处压印应仍在航（1.12→1.00）');
      expect(
        _inFlightOpacities(tester, stampFinder),
        isNotEmpty,
        reason: '60ms 处印章淡入应仍在航',
      );

      await tester.pumpAndSettle();
      // 落定：类型印章文本在场（封闭 kind 词表；无「已掌握/认证」措辞）。
      expect(find.text('阻力模式'), findsOneWidget);
      expect(find.textContaining('已掌握'), findsNothing);
      expect(find.textContaining('认证'), findsNothing);
      expect(
        find.descendant(
          of: stampFinder,
          matching: find.byType(TweenAnimationBuilder<double>),
        ),
        findsOneWidget,
      );
    });

    testWidgets('E- reduce-motion：静态分支直落全尺寸，无动画壳（Q06 洞察家族'
        '「减少动态」格）', (tester) async {
      final card = EvidenceInsightCardData.fromJson(_frictionCardJson());
      await tester.pumpWidget(
        testMaterialApp(
          home: MediaQuery(
            data: const MediaQueryData(disableAnimations: true),
            child: Scaffold(
              body: SingleChildScrollView(
                child: EvidenceInsightCardWidget(card: card),
              ),
            ),
          ),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      final stampFinder = find.byType(SparkleEvidenceStamp);
      expect(stampFinder, findsOneWidget);
      expect(
        find.descendant(
          of: stampFinder,
          matching: find.byType(TweenAnimationBuilder<double>),
        ),
        findsNothing,
      );
      expect(_inFlightOpacities(tester, stampFinder), isEmpty);
      // 类型印章完整在场（等价信息不丢失）。
      expect(find.text('阻力模式'), findsOneWidget);
    });
  });
}
