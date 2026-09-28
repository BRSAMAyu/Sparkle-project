import 'dart:io' as io;
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/agent_run_command_service.dart';
import 'package:sparkle/core/services/agent_run_read_service.dart';
import 'package:sparkle/features/journey/data/models/hybrid_journey_models.dart';
import 'package:sparkle/features/journey/data/repositories/hybrid_journey_repository.dart';
import 'package:sparkle/features/journey/presentation/screens/hybrid_workbench_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';

import '../../shared/i18n_test_helper.dart';
import '../../shared/u02_test_fonts.dart';

/// V4-U04 证据采集：运行工作台顶层截图 + 语义树 + 真实操作（U10 同款）。
///
/// 真实渲染断言**无论是否落盘都执行**；落盘仅在
/// `SPARKLE_U04_EVIDENCE_DIR=<dir>` 会话发生（会话产物不默认入库）。
/// 真实操作序列：恢复旅程 run（同 run 幂等回放，start 零调用）→ 取消
/// 对话框出现且未确认前零命令。
class _FakeRepository implements HybridJourneyRepository {
  _FakeRepository(this.payload);

  final Map<String, dynamic> payload;

  int startCalls = 0;
  final List<String> fetchStateRunIds = <String>[];

  @override
  Future<HybridJourneyPayload> start({
    required String idempotencyKey,
    String? taskId,
  }) async {
    startCalls += 1;
    return HybridJourneyPayload.fromJson(payload);
  }

  @override
  Future<HybridJourneyPayload> submitJudgment({
    required String runId,
    required List<String> selectedRefs,
    required String idempotencyKey,
    String? focusNote,
  }) async =>
      HybridJourneyPayload.fromJson(payload);

  @override
  Future<HybridJourneyPayload> confirmOutcome({
    required String runId,
    required String idempotencyKey,
    String? note,
  }) async =>
      HybridJourneyPayload.fromJson(payload);

  @override
  Future<HybridJourneyPayload?> fetchState({required String runId}) async {
    fetchStateRunIds.add(runId);
    return HybridJourneyPayload.fromJson(payload);
  }
}

class _FakeCommandService implements AgentRunCommandService {
  final List<Map<String, Object?>> completeCalls = <Map<String, Object?>>[];
  final List<Map<String, Object?>> cancelCalls = <Map<String, Object?>>[];

  @override
  Future<Map<String, dynamic>> completeStep(
    String runId,
    String stepId, {
    required String idempotencyKey,
    String action = 'confirm',
    String? note,
  }) async {
    completeCalls.add(<String, Object?>{'run_id': runId, 'step_id': stepId});
    return <String, dynamic>{'step_replay': false, 'run': <String, dynamic>{}};
  }

  @override
  Future<Map<String, dynamic>> cancelRun(
    String runId, {
    String? idempotencyKey,
  }) async {
    cancelCalls.add(<String, Object?>{'run_id': runId});
    return <String, dynamic>{'run': <String, dynamic>{}};
  }
}

AgentRunView _journeyRun() => AgentRunView.fromJson(<String, dynamic>{
      'run_id': 'run-demo-j1',
      'status': 'AWAITING_USER',
      'is_terminal': false,
      'objective': 'Hybrid 旅程：掌握树遍历 —— 材料研判与带引用交付',
      'kind': 'system',
      'trace_id': 'hybrid_journey',
      'task_id': 'task-demo-1',
      'steps': <dynamic>[
        <String, dynamic>{'step_id': 'prep', 'ordinal': 1, 'owner': 'agent', 'completed': true},
        <String, dynamic>{'step_id': 'judgment', 'ordinal': 2, 'owner': 'human', 'completed': true},
        <String, dynamic>{'step_id': 'execute_check', 'ordinal': 3, 'owner': 'agent', 'completed': true},
        <String, dynamic>{'step_id': 'outcome', 'ordinal': 4, 'owner': 'hybrid', 'completed': false},
      ],
      'awaiting_step': <String, dynamic>{
        'step_id': 'outcome',
        'ordinal': 4,
        'owner': 'hybrid',
        'state': 'awaiting',
        'label': '确认交付',
        'prompt': '确认产出后任务才会完成',
        'artifacts': <dynamic>[],
      },
    });

AgentRunView _genericRun() => AgentRunView.fromJson(<String, dynamic>{
      'run_id': 'run-demo-g1',
      'status': 'AWAITING_USER',
      'is_terminal': false,
      'objective': '比较多份资料，重排后两周计划',
      'kind': 'openclaw',
      'steps': <dynamic>[
        <String, dynamic>{'step_id': 'step-1', 'ordinal': 1, 'owner': 'agent', 'completed': true},
        <String, dynamic>{'step_id': 'step-2', 'ordinal': 2, 'owner': 'human', 'completed': false},
      ],
      'awaiting_step': <String, dynamic>{
        'step_id': 'step-2',
        'ordinal': 2,
        'owner': 'human',
        'state': 'awaiting',
        'label': '补充资料约束',
        'prompt': '这一步需要你',
        'artifacts': <dynamic>[],
      },
    });

Map<String, dynamic> _journeySheetPayload() => <String, dynamic>{
      'version': 'hybrid_journey.v1',
      'run': <String, dynamic>{
        'run_id': 'run-demo-j1',
        'status': 'AWAITING_USER',
        'steps': <dynamic>[
          <String, dynamic>{'step_id': 'prep', 'ordinal': 1, 'owner': 'agent', 'completed': true},
          <String, dynamic>{'step_id': 'judgment', 'ordinal': 2, 'owner': 'human', 'completed': false},
        ],
        'awaiting_step': <String, dynamic>{
          'step_id': 'judgment',
          'ordinal': 2,
          'owner': 'human',
          'state': 'awaiting',
        },
      },
      'goal': <String, dynamic>{'goal_id': 'g1', 'title': '掌握树遍历'},
      'task': <String, dynamic>{'id': 'task-demo-1', 'title': '写综述'},
      'artifacts': <dynamic>[],
      'citations': <dynamic>[],
    };

Future<void> _capture(WidgetTester tester, String outPath) async {
  await tester.runAsync(() async {
    final boundary = tester.renderObject<RenderRepaintBoundary>(
      find.byKey(const Key('u04-evidence-root')),
    );
    final image = await boundary.toImage(pixelRatio: 2.0);
    final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
    io.File(outPath).writeAsBytesSync(bytes!.buffer.asUint8List());
  });
}

String _dumpSemantics(SemanticsNode node, int depth) {
  final buf = StringBuffer()
    ..writeln('${'  ' * depth}- label="${node.getSemanticsData().label}"');
  node.visitChildren((child) {
    buf.write(_dumpSemantics(child, depth + 1));
    return true;
  });
  return buf.toString();
}

/// 按钮可读标签（子树 Text 拼接；读屏按钮朗读的等价面）。
String _buttonLabel(ButtonStyleButton button) {
  final label = button.child;
  if (label is Text) return label.data ?? label.textSpan?.toPlainText() ?? '';
  if (label is Row) {
    return label.children
        .whereType<Text>()
        .map((t) => t.data ?? t.textSpan?.toPlainText() ?? '')
        .where((s) => s.trim().isNotEmpty)
        .join(' ');
  }
  return '(非文本标签)';
}

void main() {
  testWidgets('[evidence] 运行工作台真实渲染并按需落盘（顶层 + 恢复操作）',
      (tester) async {
    tester.view.devicePixelRatio = 2.0;
    tester.view.physicalSize = const Size(750, 1620);
    addTearDown(() {
      tester.view.resetDevicePixelRatio();
      tester.view.resetPhysicalSize();
    });
    setUpI18nForTesting();
    await tester.runAsync(U02TestFonts.load);
    final repository = _FakeRepository(_journeySheetPayload());
    final command = _FakeCommandService();
    final semantics = tester.ensureSemantics();
    final container = ProviderContainer(
      overrides: [
        activeAgentRunsProvider.overrideWith(
          (ref) => Future.value([_journeyRun(), _genericRun()]),
        ),
        agentRunCommandServiceProvider.overrideWithValue(command),
        hybridJourneyRepositoryProvider.overrideWithValue(repository),
      ],
    );
    addTearDown(container.dispose);
    await tester.pumpWidget(
      // RepaintBoundary 包在 MaterialApp 外：捕获面含 Navigator overlay 里的
      // modal sheet 与 dialog（挂在 home 内会截掉它们）。
      RepaintBoundary(
        key: const Key('u04-evidence-root'),
        child: MaterialApp(
          theme: AppThemes.lightTheme,
          locale: const Locale('zh'),
          supportedLocales: AppLocalizations.supportedLocales,
          localizationsDelegates: const [
            AppLocalizations.delegate,
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          home: UncontrolledProviderScope(
            container: container,
            child: const HybridWorkbenchScreen(),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    // 真实渲染断言（无论是否落盘都执行）：两段 run、ownership 词表、
    // 旅程恢复入口与 generic human 步统一确认卡同屏。
    expect(find.byKey(const Key('workbench_run_card_run-demo-j1')), findsOneWidget);
    expect(find.byKey(const Key('workbench_run_card_run-demo-g1')), findsOneWidget);
    expect(find.textContaining('交给 Sparkle'), findsWidgets);
    expect(find.textContaining('我来做'), findsWidgets);
    expect(find.textContaining('带我做'), findsWidgets);
    expect(find.byKey(const Key('workbench_resume_journey_run-demo-j1')), findsOneWidget);
    expect(find.text('确认，继续'), findsOneWidget);
    expect(tester.takeException(), isNull);

    final dir = io.Platform.environment['SPARKLE_U04_EVIDENCE_DIR'];
    if (dir != null && dir.isNotEmpty) {
      final outDir = io.Directory(dir);
      if (!outDir.existsSync()) outDir.createSync(recursive: true);
      await _capture(tester, '$dir/u04_workbench_top.png');

      // 真实操作：恢复旅程 run → 同一段 run 幂等回放（start 零调用）。
      await tester.tap(find.byKey(const Key('workbench_resume_journey_run-demo-j1')));
      await tester.pumpAndSettle();
      expect(repository.fetchStateRunIds, ['run-demo-j1']);
      expect(repository.startCalls, 0);
      expect(find.byKey(const Key('hybrid-journey-ready')), findsOneWidget);
      await _capture(tester, '$dir/u04_workbench_resume_sheet.png');
      // 关闭 sheet：显式 pop modal 路由（确定性，不依赖屏障命中位置）。
      tester.state<NavigatorState>(find.byType(Navigator)).pop();
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('hybrid-journey-ready')), findsNothing);

      // 真实操作：generic run 取消 → 显式确认对话框拦截（未确认零命令）。
      await tester.scrollUntilVisible(
        find.byKey(const Key('workbench_cancel_run_run-demo-g1')),
        200,
        scrollable: find
            .descendant(
              of: find.byKey(const Key('u04-evidence-root')),
              matching: find.byType(Scrollable),
            )
            .first,
      );
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('workbench_cancel_run_run-demo-g1')));
      await tester.pumpAndSettle();
      expect(command.cancelCalls, isEmpty);
      expect(find.textContaining('取消这段运行'), findsOneWidget);
      await _capture(tester, '$dir/u04_workbench_cancel_confirm.png');

      // 语义证据：优先语义树根；不可用时枚举**实际渲染的可读面**——
      // 全部 Text（读屏文本来源）与全部可点按钮（label + 图标语义）。
      final owner = RendererBinding.instance.rootPipelineOwner.semanticsOwner;
      final root = owner?.rootSemanticsNode;
      final buf = StringBuffer();
      if (root != null) {
        buf.write(_dumpSemantics(root, 0));
      } else {
        buf.writeln('(渲染语义根不可用；渲染可读面枚举：Text + 按钮)');
        for (final text in tester.widgetList<Text>(find.byType(Text))) {
          final data = text.data ?? text.textSpan?.toPlainText();
          if (data != null && data.trim().isNotEmpty) {
            buf.writeln('- text "$data"');
          }
        }
        for (final button in tester
            .widgetList<OutlinedButton>(find.byType(OutlinedButton))) {
          buf.writeln('- outlined-button "${_buttonLabel(button)}"');
        }
        for (final button
            in tester.widgetList<TextButton>(find.byType(TextButton))) {
          buf.writeln('- text-button "${_buttonLabel(button)}"');
        }
        for (final button
            in tester.widgetList<FilledButton>(find.byType(FilledButton))) {
          buf.writeln('- filled-button "${_buttonLabel(button)}"');
        }
      }
      io.File(
        '$dir/u04_workbench_semantics.txt',
      ).writeAsStringSync(buf.toString());
    }
    semantics.dispose();
  });
}
