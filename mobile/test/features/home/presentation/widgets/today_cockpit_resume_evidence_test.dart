// V4-U01 · 首页接续证据采集：顶层截图（PNG）+ 语义树 dump。
//
// 常规跑 `flutter test`：本文件仍执行真实渲染断言（接续条 ready / stale
// 两面、唯一 primary CTA），不写文件——保证套件全绿且无副作用。设
// `U01_EVIDENCE_DIR=<abs dir>` 时额外写出：
//   u01_resume_ready_360x800.png / _semantics.txt
//   u01_resume_stale_360x800.png / _semantics.txt
// 证据落盘路径见 v4/evidence/V4-U01/run_manifest.json。
import 'dart:async' show unawaited;
import 'dart:io' as io;
import 'dart:ui' show ImageByteFormat;

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/home/presentation/providers/home_growth_provider.dart';
import 'package:sparkle/features/memory/presentation/providers/context_receipt_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/active_goal_provider.dart';

import '../../../../shared/i18n_test_helper.dart';
import '../../dashboard_test_harness.dart';

class _EvidenceApi implements ApiClient {
  _EvidenceApi(this.response);

  Object? response;

  @override
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async =>
      Response<T>(
        requestOptions: RequestOptions(path: path),
        data: response as T,
      );

  @override
  Stream<SSEEvent> getStream(
    String path, {
    Map<String, dynamic>? queryParameters,
    Map<String, dynamic>? headers,
  }) =>
      const Stream<SSEEvent>.empty();

  @override
  Stream<SSEEvent> postStream(String path, {Object? data}) =>
      const Stream<SSEEvent>.empty();

  @override
  Dio get dio => Dio();

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

Map<String, dynamic> _receiptPayload() => {
      'mode': 'live',
      'schema_version': 'context_selection_receipt.v1',
      'receipt': {
        'schema_version': 'context_selection_receipt.v1',
        'receipt_id': 'csr_U01EVIDENCE',
        'selection_role': 'resume_view',
        'decision_id': null,
        'input_versions': {
          'memory_epoch': 3,
          'selector_version': 'context_pack.v4-i06.v1',
        },
        'candidates': <Map<String, dynamic>>[
          {'ref': 'task://t1', 'status': 'selected', 'reason_code': null, 'note': null},
        ],
        'budget': {'candidate_scan_limit': 12, 'selected_max': 6, 'clarifications_used': 0},
        'why_now': null,
      },
      'source_verification': <Map<String, dynamic>>[],
      'resolved_selected_count': 1,
    };

Map<String, dynamic> _resumeViewPayload({required String expiresAt}) => {
      'view': {
        'schema_version': 'episode_resume_view.v1',
        'goal_ref': 'goal://g-1',
        'task_ref': 'task://t-1',
        'run_ref': null,
        'last_valid_outcome': null,
        'last_confirmed_step': {
          'step_ref': 'subtask://s-1',
          'description': '读完第三章前两节',
          'confirmed_at': '2026-09-28T10:05:00',
          'version_token': 'tok-1',
        },
        'pending_human_step': {
          'description': '做第三章末尾的三道练习题',
          'cognitive_ownership': 'user_led',
          'execution_mode': 'assisted',
        },
        'why_now': null,
        'expires_at': expiresAt,
        'freshness': {
          'context_receipt_ref': 'context_selection://csr_U01EVIDENCE',
          'computed_at': '2026-09-28T12:00:00',
          'memory_epoch_at_compute': 3,
        },
      },
      'reason_code': null,
      'warnings': <String>[],
    };

List<Override> _u01Overrides({required String expiresAt}) => [
      multiGoalOverviewProvider.overrideWith(
        (ref) async => const MultiGoalOverview(
          goals: <ActiveGoalSnapshot>[
            ActiveGoalSnapshot(
              id: 'goal-1',
              title: '期末冲刺：线性代数',
              goalType: 'exam',
              healthScore: 0.7,
              weeklyConflictCount: 0,
            ),
          ],
          selectedGoalId: 'goal-1',
        ),
      ),
      homeGrowthStateProvider.overrideWith(
        (ref) async => const HomeGrowthState(
          planHealth: 0.8,
          tasksTotal: 3,
          tasksCompleted: 0,
          streak: 0,
          activePlan: HomeActivePlanStatus(
            id: 'plan-1',
            name: '期末复习计划',
            healthScore: 0.8,
          ),
          nextAction: HomeGrowthTask(
            id: 't-1',
            title: '第三章：矩阵运算',
            priority: 4,
            isCompleted: false,
          ),
        ),
      ),
      contextReceiptProvider.overrideWith(
        (ref) {
          final notifier = ContextReceiptNotifier(
            _EvidenceApi(_receiptPayload()),
          );
          unawaited(notifier.load());
          return notifier;
        },
      ),
      apiClientProvider.overrideWithValue(
        _EvidenceApi(_resumeViewPayload(expiresAt: expiresAt)),
      ),
    ];

String _dumpSemanticsFromElements(Element rootElement) {
  final buf = StringBuffer();
  void visit(Element el, int depth) {
    final ro = el.renderObject;
    if (ro is RenderParagraph) {
      final text = ro.text.toPlainText();
      if (text.trim().isNotEmpty) {
        final rect = ro.localToGlobal(Offset.zero) & ro.size;
        buf.writeln('${'  ' * depth}- label="$text" isText=true rect=$rect');
      }
    }
    el.visitChildElements((child) => visit(child, depth));
  }

  visit(rootElement, 0);
  return buf.toString();
}

Future<void> _writeEvidence(
  WidgetTester tester,
  GlobalKey repaintKey,
  String basename,
) async {
  final dir = io.Platform.environment['U01_EVIDENCE_DIR'];
  if (dir == null || dir.isEmpty) {
    return;
  }
  final rootElement = tester.binding.rootElement;
  await tester.runAsync(() async {
    final outDir = io.Directory(dir);
    if (!outDir.existsSync()) {
      outDir.createSync(recursive: true);
    }
    // runAsync 内补一帧再截图（shell_evidence_test 同款；根边界需在
    // 实帧管线里落一次 paint，否则 toImage 取到空白层）。
    await tester.pump();
    final boundary = tester.renderObject<RenderRepaintBoundary>(
      find.byKey(repaintKey),
    );
    final image = await boundary.toImage(pixelRatio: 2.0);
    final bytes = await image.toByteData(format: ImageByteFormat.png);
    io.File('${outDir.path}/$basename.png')
        .writeAsBytesSync(bytes!.buffer.asUint8List());
    io.File('${outDir.path}/$basename${'_semantics.txt'}')
        .writeAsStringSync(_dumpSemanticsFromElements(rootElement!));
  });
}

Future<SemanticsHandle> _pumpDashboard(
  WidgetTester tester, {
  required GlobalKey repaintKey,
  required String expiresAt,
}) async {
  tester.view.devicePixelRatio = 2.0;
  tester.view.physicalSize = const Size(360, 800) * 2.0;
  addTearDown(() {
    tester.view.resetDevicePixelRatio();
    tester.view.resetPhysicalSize();
  });
  final semantics = tester.ensureSemantics();
  await initializeDashboardTestEnvironment();
  await tester.pumpWidget(
    RepaintBoundary(
      key: repaintKey,
      // tickerEnabled=true + 足帧 pump：staggered 入场动画需落定，否则
      // 截图停在动画初帧（空白）——harness 文档点名的已知陷阱。
      child: buildDashboardTestHarness(
        size: const Size(360, 800),
        tickerEnabled: true,
        extraOverrides: _u01Overrides(expiresAt: expiresAt),
      ),
    ),
  );
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 200));
  await tester.pump(const Duration(milliseconds: 400));
  await tester.pump(const Duration(milliseconds: 600));
  await tester.pumpAndSettle();
  return semantics;
}

void main() {
  setUp(setUpI18nForTesting);
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('ready 态：接续条 + 收敛主 CTA 如实呈现 + 证据落盘钩子', (tester) async {
    final repaintKey = GlobalKey();
    final semantics = await _pumpDashboard(
      tester,
      repaintKey: repaintKey,
      expiresAt: '2099-01-01T00:00:00',
    );

    // 真实渲染断言（无论是否落盘都执行）。
    expect(find.byKey(const ValueKey('episode-resume-strip')), findsOneWidget);
    expect(find.textContaining('Last time:'), findsOneWidget);
    expect(find.textContaining('Next:'), findsOneWidget);
    // cockpit 卡内唯一 primary CTA（收敛为继续语义；J-03 唯一主行动契约
    // 的卡内口径——整页 lower slots 的次级 primary 属存量基线）。
    final primaries = tester
        .widgetList<SparkleButton>(
          find.descendant(
            of: find.byKey(const ValueKey('today-cockpit-card')),
            matching: find.byType(SparkleButton),
          ),
        )
        .where((b) => b.variant == ButtonVariant.primary)
        .toList();
    expect(primaries, hasLength(1));
    expect(primaries.single.label, 'Continue this step');
    // 首屏验收：主 CTA 不靠滚动即在 360×800 视口内。
    final ctaRect = tester.getRect(
      find.byKey(const ValueKey('today-cockpit-primary-cta')),
    );
    expect(ctaRect.bottom, lessThanOrEqualTo(800));
    expect(tester.takeException(), isNull);

    await _writeEvidence(tester, repaintKey, 'u01_resume_ready_360x800');
    semantics.dispose();
  });

  testWidgets('stale 态：只说明不确定，不接续（过期视图内容零渲染）+ 证据落盘钩子', (tester) async {
    final repaintKey = GlobalKey();
    final semantics = await _pumpDashboard(
      tester,
      repaintKey: repaintKey,
      expiresAt: '2020-01-01T00:00:00',
    );

    expect(
      find.byKey(const ValueKey('episode-resume-stale-line')),
      findsOneWidget,
    );
    expect(find.textContaining('Last time:'), findsNothing);
    expect(find.textContaining('Next:'), findsNothing);
    // 主 CTA 不被 stale 视图改写（卡内口径）。
    final primaries = tester
        .widgetList<SparkleButton>(
          find.descendant(
            of: find.byKey(const ValueKey('today-cockpit-card')),
            matching: find.byType(SparkleButton),
          ),
        )
        .where((b) => b.variant == ButtonVariant.primary)
        .toList();
    expect(primaries, hasLength(1));
    expect(primaries.single.label, 'Start Here');
    expect(tester.takeException(), isNull);

    await _writeEvidence(tester, repaintKey, 'u01_resume_stale_360x800');
    semantics.dispose();
  });
}
