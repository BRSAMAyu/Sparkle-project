// V4-U02 · recovery sheet「纠正 → 差异确认」证据采集：顶层截图（PNG）+ 语义树 dump。
//
// 常规跑 `flutter test`：本文件仍执行真实渲染断言（分离选择、可读 diff、
// 回执成功面、冲突恢复面、abstain 恒可达），不写文件——保证套件全绿且
// 无副作用。设 `U02_EVIDENCE_DIR=<abs dir>` 时额外写出：
//   u02_scope_choice_360x800.png / _semantics.txt   （约束/偏好分离呈现）
//   u02_diff_review_360x800.png / _semantics.txt    （服务端权威 diff 可读对照）
//   u02_committed_360x800.png / _semantics.txt      （回执到场后的唯一成功面孔）
//   u02_conflict_360x800.png / _semantics.txt       （版本冲突恢复面，零成功视觉）
//   u02_abstain_360x800.png / _semantics.txt        （系统不提案时纠正输入仍在场）
// 证据落盘路径见 v4/evidence/V4-U02/run_manifest.json。
import 'dart:async' show Completer;
import 'dart:io' as io;
import 'dart:ui' show ImageByteFormat;

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:sparkle/core/design/theme/sparkle_theme_extension.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/services/task_notification_id_mapper.dart';
import 'package:sparkle/core/services/task_notification_scheduler.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/features/recovery/data/models/stuck_journey_models.dart';
import 'package:sparkle/features/recovery/data/repositories/stuck_journey_repository.dart';
import 'package:sparkle/features/recovery/presentation/widgets/recovery_calibration_section.dart';
import 'package:sparkle/features/recovery/presentation/widgets/stuck_journey_sheet.dart';
import 'package:sparkle/features/task/data/repositories/action_proposal_repository.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/task_model.dart';
import 'package:sparkle/shared/widgets/action_proposal/proposal_card_models.dart';

// ---------------------------------------------------------------------------
// 自足夹具（与行为契约测试同语义；本文件独立，避免跨测试文件私有依赖）
// ---------------------------------------------------------------------------

class _EvidenceProposalRepository implements ActionProposalRepository {
  Map<String, dynamic> createResponse = _pendingProjection('p1');
  Object? approveResult;
  Completer<Map<String, dynamic>?>? approveGate;

  @override
  Future<Map<String, dynamic>> createAdjustmentProposal({
    required String taskId,
    required Map<String, dynamic> fields,
    required String idempotencyKey,
    String? summary,
  }) async =>
      createResponse;

  @override
  Future<Map<String, dynamic>?> getProposal(String proposalId) async =>
      _pendingProjection(proposalId);

  @override
  Future<Map<String, dynamic>?> approve(
    String proposalId,
    String idempotencyKey,
  ) async {
    final gate = approveGate;
    if (gate != null && !gate.isCompleted) return gate.future;
    final result = approveResult;
    if (result is DioException) throw result;
    return result as Map<String, dynamic>?;
  }

  @override
  Future<Map<String, dynamic>?> cancel(
    String proposalId,
    String idempotencyKey,
  ) async =>
      <String, dynamic>{'proposal': _pendingProjection(proposalId)};

  @override
  Future<List<ActionProposalCardData>> listForSubject(
    String subjectId, {
    String? status,
  }) async =>
      const <ActionProposalCardData>[];

  @override
  Future<Map<String, dynamic>?> reject(
    String proposalId,
    String idempotencyKey, {
    String? reason,
  }) async =>
      null;
}

class _EvidenceApi extends ApiClient {
  _EvidenceApi() : super(_UnusedRef());

  @override
  Future<Response<T>> post<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async =>
      Response<T>(
        requestOptions: RequestOptions(path: path),
        data: <String, dynamic>{'status': 'updated'} as T?,
      );

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _AbstainRepo implements StuckJourneyRepository {
  @override
  Future<StuckJourneyPayload> startJourney({
    required String surface,
    String? goalId,
    String? taskId,
  }) async =>
      StuckJourneyPayload.fromJson(_abstainPayload(surface));

  @override
  Future<StuckJourneyPayload> answerQuestion({
    required String surface,
    required String questionId,
    required String branchKey,
    String? goalId,
    String? taskId,
  }) async =>
      StuckJourneyPayload.fromJson(_abstainPayload(surface));

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
        'journey': _abstainPayload(surface),
      });
}

Map<String, dynamic> _abstainPayload(String surface) => <String, dynamic>{
      'version': 'stuck_journey.v1',
      'surface': surface,
      'outcome': 'act',
      'friction_type': 'skill',
      'question': null,
      'main_intervention': null,
      'uncertain': false,
      'context': <String, dynamic>{
        'goal': <String, dynamic>{'id': 'g1', 'title': '线代一轮复习'},
        'task': <String, dynamic>{'id': 't1', 'title': '特征值练习'},
        'recent_failures': <String, dynamic>{'count': 1, 'titles': <String>[]},
      },
      'receipt': <String, dynamic>{},
      'annotations': <String, dynamic>{},
    };

Map<String, dynamic> _pendingProjection(String id) => <String, dynamic>{
      'proposal_id': id,
      'status': 'PENDING',
      'command_type': 'task.update_fields',
      // X-03 投影回显 source（ProposalSource 词表内值；一审 B-1 后客户端恒发 'task'）。
      'source': 'task',
      'summary': '仅本次：今天只有十五分钟',
      'diff': <String, dynamic>{
        'before': <String, dynamic>{'estimated_minutes': 40},
        'after': <String, dynamic>{'estimated_minutes': 15},
        'changed_fields': <String>['estimated_minutes'],
      },
    };

Map<String, dynamic> _committedEnvelope({String receiptId = 'r-20260929-u02'}) =>
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
    };

class _StaticTasks extends TaskNotifier {
  _StaticTasks() : super(_UnusedTaskRepository(), _UnusedScheduler(), _UnusedRef()) {
    state = TaskListState(tasks: [_anchorTask()], todayTasks: [_anchorTask()]);
  }

  @override
  Future<void> loadTasks({TaskFilter? filter}) async {}

  @override
  Future<void> loadTodayTasks() async {}

  @override
  Future<void> loadRecommendedTasks() async {}

  @override
  Future<void> refreshTasks() async {}
}

TaskModel _anchorTask() => TaskModel(
      id: 't1',
      userId: 'user-1',
      title: '特征值练习',
      type: TaskType.learning,
      tags: const <String>['linear-algebra'],
      estimatedMinutes: 40,
      difficulty: 2,
      energyCost: 2,
      status: TaskStatus.stuck,
      priority: 1,
      createdAt: DateTime(2026, 9),
      updatedAt: DateTime(2026, 9, 20),
    );

class _UnusedTaskRepository extends TaskRepository {
  _UnusedTaskRepository() : super(_EvidenceApi());
}

class _UnusedScheduler extends TaskNotificationScheduler {
  _UnusedScheduler()
      : super(
          NotificationService(_UnusedRef(), autoInitialize: false),
          TaskNotificationIdMapper(),
        );
}

class _UnusedRef implements Ref {
  @override
  T read<T>(ProviderListenable<T> provider) => InterceptorsWrapper() as T;

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

// ---------------------------------------------------------------------------
// 证据泵浦与落盘
// ---------------------------------------------------------------------------

String _dumpSemanticsFromElements(Element rootElement) {
  final buffer = StringBuffer();
  void visit(Element element) {
    final widget = element.widget;
    final semantics = element.renderObject is RenderObject
        ? (element.renderObject as RenderObject).debugSemantics
        : null;
    if (semantics != null && semantics.label.isNotEmpty) {
      buffer.writeln('label: ${semantics.label}');
    }
    if (widget is Text) {
      buffer.writeln('text: ${widget.data ?? widget.textSpan?.toPlainText()}');
    }
    element.visitChildren(visit);
  }

  visit(rootElement);
  return buffer.toString();
}

Future<SemanticsHandle> _pump({
  required WidgetTester tester,
  required _EvidenceProposalRepository proposalRepo,
  required GlobalKey repaintKey,
}) async {
  final semantics = tester.ensureSemantics();
  tester.view.devicePixelRatio = 2.0;
  tester.view.physicalSize = const Size(720, 1600); // 360x800 @2x
  addTearDown(() {
    tester.view.resetDevicePixelRatio();
    tester.view.resetPhysicalSize();
  });
  SharedPreferences.setMockInitialValues({});
  await ViewStorageService.ensureInitialized();

  final container = ProviderContainer(
    overrides: [
      stuckJourneyRepositoryProvider.overrideWithValue(_AbstainRepo()),
      actionProposalRepositoryProvider.overrideWithValue(proposalRepo),
      apiClientProvider.overrideWithValue(_EvidenceApi()),
      taskListProvider.overrideWith((ref) => _StaticTasks()),
    ],
  );
  addTearDown(container.dispose);
  await tester.pumpWidget(
    UncontrolledProviderScope(
      container: container,
      child: RepaintBoundary(
        key: repaintKey,
        child: MaterialApp(
          theme: ThemeData(extensions: [SparkleThemeExtension.light()]),
          locale: const Locale('zh'),
          supportedLocales: const [Locale('en'), Locale('zh')],
          localizationsDelegates: const [
            AppLocalizations.delegate,
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          home: const Scaffold(
            body: SingleChildScrollView(
              child: StuckJourneySheetBody(
                request: StuckJourneyRequest(
                  surface: 'action',
                  taskId: 't1',
                ),
              ),
            ),
          ),
        ),
      ),
    ),
  );
  await tester.pumpAndSettle();
  return semantics;
}

Future<void> _writeEvidence(
  WidgetTester tester,
  GlobalKey repaintKey,
  String basename,
) async {
  final dir = io.Platform.environment['U02_EVIDENCE_DIR'];
  if (dir == null || dir.isEmpty) return;
  final rootElement = tester.binding.rootElement;
  await tester.runAsync(() async {
    final outDir = io.Directory(dir);
    if (!outDir.existsSync()) outDir.createSync(recursive: true);
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

Future<void> _typeAndSubmit(WidgetTester tester, String text) async {
  await tester.enterText(
    find.byKey(const Key('recovery-calibration-input-field')),
    text,
  );
  await tester.ensureVisible(
    find.byKey(const Key('recovery-calibration-submit')),
  );
  await tester.tap(find.byKey(const Key('recovery-calibration-submit')));
  await tester.pumpAndSettle();
}

Future<void> _tap(WidgetTester tester, Finder finder) async {
  await tester.ensureVisible(finder);
  await tester.pumpAndSettle();
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('证据面：分离选择 / 可读 diff / 回执成功面 / 冲突恢复 / abstain',
      (tester) async {
    final repaintKey = GlobalKey();
    final proposalRepo = _EvidenceProposalRepository()
      ..approveResult = _committedEnvelope();
    final semantics = await _pump(
      tester: tester,
      proposalRepo: proposalRepo,
      repaintKey: repaintKey,
    );

    // abstain 恒可达（真实断言，无论是否落盘）。
    expect(find.byType(RecoveryCalibrationSection), findsOneWidget);
    expect(find.text('说一句，就能调整'), findsOneWidget);
    await _writeEvidence(tester, repaintKey, 'u02_abstain_360x800');

    // 分离选择。
    await _typeAndSubmit(tester, '不是不会，今天只有十五分钟');
    expect(find.text('仅本次'), findsOneWidget);
    expect(find.text('保存为偏好'), findsOneWidget);
    await _writeEvidence(tester, repaintKey, 'u02_scope_choice_360x800');

    // 走仅本次 → 服务端权威 diff。
    await _tap(tester, find.text('调整这次行动'));
    await _tap(
      tester,
      find.byKey(const Key('recovery-calibration-create-proposal')),
    );
    expect(find.text('调整前 → 调整后'), findsOneWidget);
    expect(find.text('40 → 15'), findsOneWidget);
    await _writeEvidence(tester, repaintKey, 'u02_diff_review_360x800');

    // 确认 → 回执到场 → 唯一成功面孔。
    await tester.ensureVisible(
      find.byKey(const Key('recovery-calibration-confirm')),
    );
    await tester.tap(find.byKey(const Key('recovery-calibration-confirm')));
    await tester.pumpAndSettle();
    expect(find.textContaining('已按本次约束落账'), findsOneWidget);
    expect(find.textContaining('r-20260929-u02'), findsOneWidget);
    await tester.pump(const Duration(milliseconds: 600));
    await _writeEvidence(tester, repaintKey, 'u02_committed_360x800');

    semantics.dispose();
  });

  testWidgets('证据面：409 版本冲突恢复面（无成功视觉）', (tester) async {
    final repaintKey = GlobalKey();
    final proposalRepo = _EvidenceProposalRepository()
      ..approveResult = DioException(
        requestOptions: RequestOptions(path: '/x'),
        response: Response<void>(
          requestOptions: RequestOptions(path: '/x'),
          statusCode: 409,
        ),
        type: DioExceptionType.badResponse,
      );
    final semantics = await _pump(
      tester: tester,
      proposalRepo: proposalRepo,
      repaintKey: repaintKey,
    );

    await _typeAndSubmit(tester, '今天只有十五分钟');
    await _tap(tester, find.text('调整这次行动'));
    await _tap(
      tester,
      find.byKey(const Key('recovery-calibration-create-proposal')),
    );
    await tester.ensureVisible(
      find.byKey(const Key('recovery-calibration-confirm')),
    );
    await tester.tap(find.byKey(const Key('recovery-calibration-confirm')));
    await tester.pumpAndSettle();

    expect(find.textContaining('任务在这期间有变化'), findsOneWidget);
    expect(find.textContaining('已按本次约束落账'), findsNothing);
    await _writeEvidence(tester, repaintKey, 'u02_conflict_360x800');

    semantics.dispose();
  });
}
