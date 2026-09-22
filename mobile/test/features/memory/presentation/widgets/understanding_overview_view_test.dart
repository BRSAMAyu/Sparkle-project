import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_button_v2.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/memory/data/memory_provenance_models.dart';
import 'package:sparkle/features/memory/data/memory_provenance_repository.dart';
import 'package:sparkle/features/memory/presentation/providers/understanding_overview_provider.dart';
import 'package:sparkle/features/memory/presentation/widgets/understanding_overview_view.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/shared/entities/task_model.dart';
import 'package:sparkle/shared/models/api_response_model.dart';
import '../../../../shared/i18n_test_helper.dart';

/// U-03 四组理解视图 widget 测试：
/// - 四组分组渲染（bucket_label 用户语言）；
/// - 黑话移除断言（无「条判断 / 高置信百分比」主呈现）；
/// - Why-this receipt 渲染（含 honest-unknown）；
/// - 修改/删除/暂停操作调用真实 repository 契约。
class _FakeProvenanceRepository implements MemoryProvenanceRepository {
  _FakeProvenanceRepository({this.withSource = false});

  final bool withSource;
  List<ProvenanceMemoryItem> items = [];
  String? updatedContent;
  String? revokedId;
  String? pausedId;
  String? lastScopeAction;
  String? linkedTaskId;

  @override
  Future<ProvenanceListResult> listItems({
    UnderstandingBucket? bucket,
    String? kind,
    int limit = 200,
    int offset = 0,
    bool includeInactive = false,
  }) async {
    return ProvenanceListResult(
      items: List.of(items),
      total: items.length,
      hasMore: false,
      scanCapped: false,
    );
  }

  @override
  Future<ProvenanceMemoryItem> updateItem(
    String kind,
    String id, {
    String? content,
    Map<String, Object>? prefValue,
    String? title,
    String? goalStatus,
    String? reason,
  }) async {
    updatedContent = content ?? title;
    final old = items.firstWhere((e) => e.id == id);
    final updated = ProvenanceMemoryItem(
      kind: old.kind,
      id: 'new-$id',
      ref: 'memory://$kind/new-$id',
      bucket: old.bucket,
      bucketLabel: old.bucketLabel,
      content: content ?? title ?? old.content,
      status: 'active',
      scope: old.scope,
      correctionCount: old.correctionCount + 1,
      evidenceMissing: false,
      confidenceTier: old.confidenceTier,
      confidenceTierLabel: old.confidenceTierLabel,
      sourceLabel: old.sourceLabel,
      sourceKnown: true,
      actions: old.actions,
    );
    items = [
      for (final entry in items)
        if (entry.id == id) updated else entry,
    ];
    return updated;
  }

  @override
  Future<Map<String, dynamic>> revokeItem(
    String kind,
    String id, {
    String? reason,
  }) async {
    revokedId = id;
    items = [
      for (final entry in items)
        if (entry.id != id) entry,
    ];
    return {'status': 'revoked', 'revoked': true};
  }

  @override
  Future<Map<String, dynamic>> updateScope(
    String kind,
    String id, {
    required String action,
    String? planId,
    String? taskId,
    String? reason,
  }) async {
    pausedId = action == 'pause' ? id : pausedId;
    lastScopeAction = action;
    linkedTaskId = action == 'link_task' ? taskId : linkedTaskId;
    items = [
      for (final entry in items)
        if (entry.id == id)
          ProvenanceMemoryItem(
            kind: entry.kind,
            id: entry.id,
            ref: entry.ref,
            bucket: entry.bucket,
            bucketLabel: entry.bucketLabel,
            content: entry.content,
            status: action == 'pause' ? 'archived' : entry.status,
            scope: entry.scope,
            correctionCount: entry.correctionCount,
            evidenceMissing: false,
            confidenceTier: entry.confidenceTier,
            confidenceTierLabel: entry.confidenceTierLabel,
            sourceLabel: entry.sourceLabel,
            sourceKnown: true,
            actions: entry.actions,
          )
        else
          entry,
    ];
    return {'changed': true, 'paused': action == 'pause', 'memory_epoch': 3};
  }

  @override
  Future<ProvenanceSourceInfo> getSource({
    required String kind,
    required String id,
  }) async =>
      ProvenanceSourceInfo(
        sourceKnown: true,
        sourceLabel: '你告诉我的',
        evidenceCount: 1,
        evidenceMissing: false,
        correctionCount: 0,
        confidenceTierLabel: '已确认',
        governanceHistory: const [],
        writtenAt: DateTime(2026, 9, 20, 10),
      );

  @override
  Future<Map<String, dynamic>> getScope({
    required String kind,
    required String id,
  }) async =>
      {'scope': {'level': 'global'}, 'paused': false, 'editable': true};

  @override
  Future<WhyThisResult> whyThis({
    required String memoryRef,
    int? version,
    String? packId,
    List<String> whyIncluded = const [],
    List<Map<String, Object>> internalOnly = const [],
  }) async {
    return WhyThisResult(
      kind: 'episodic',
      id: 'a',
      ref: memoryRef,
      content: '我在准备离散数学期末考试',
      statusNow: 'active',
      stillInUse: true,
      paused: false,
      usedAt: DateTime(2026, 9, 21, 8),
      whyIncluded: [
        const WhyReason(reason: 'rank_policy', known: true, label: '按与当轮内容的相关度排序选中'),
        const WhyReason(reason: 'mystery_code', known: false, label: null),
      ],
      internalOnly: const [
        WhyReason(
          reason: 'selfcheck:phatic_query',
          known: true,
          label: '当轮只是问候或确认，不需要引用记忆',
        ),
      ],
      receiptVersion: 'v1',
      receiptVersionKnown: true,
      recentUses: const [],
      source: ProvenanceSourceInfo(
        sourceKnown: false,
        sourceLabel: '',
        evidenceCount: 0,
        evidenceMissing: false,
        correctionCount: 0,
        confidenceTierLabel: '已确认',
        governanceHistory: const [],
      ),
      correctionUpdatePath: '/update',
      correctionRevokePath: '/revoke',
      correctionScopePath: '/scope',
    );
  }
}

ProvenanceMemoryItem _entry({
  required String id,
  required String bucket,
  required String label,
  List<String> actions = const ['update', 'revoke', 'view_source', 'pause'],
}) {
  final bucketEnum = understandingBucketFromName(bucket)!;
  return ProvenanceMemoryItem(
    kind: 'episodic',
    id: id,
    ref: 'memory://episodic/$id',
    bucket: bucketEnum,
    bucketLabel: label,
    content: '内容 $id',
    status: 'active',
    scope: const {'level': 'global'},
    correctionCount: 0,
    evidenceMissing: false,
    confidenceTier: 'confirmed',
    confidenceTierLabel: '已确认',
    sourceLabel: '你告诉我的',
    sourceKnown: true,
    actions: actions,
  );
}

ProvenanceMemoryItem _goalEntry({
  required String id,
  String label = '你告诉我的',
}) {
  final bucketEnum = understandingBucketFromName('told')!;
  return ProvenanceMemoryItem(
    kind: 'goal',
    id: id,
    ref: 'memory://goal/$id',
    bucket: bucketEnum,
    bucketLabel: label,
    content: '目标 $id',
    status: 'active',
    scope: const {'level': 'global'},
    correctionCount: 0,
    evidenceMissing: false,
    confidenceTier: 'confirmed',
    confidenceTierLabel: '已确认',
    sourceLabel: '你告诉我的',
    sourceKnown: true,
    // 服务端契约：active goal 才投影 set_scope（link_plan/link_task 的门）。
    actions: const ['update', 'revoke', 'view_source', 'pause', 'set_scope'],
  );
}

TaskModel _taskModel({
  required String id,
  required String title,
  TaskStatus status = TaskStatus.pending,
}) {
  final now = DateTime.utc(2026, 9, 21);
  return TaskModel(
    id: id,
    userId: 'user-1',
    title: title,
    type: TaskType.learning,
    tags: const [],
    estimatedMinutes: 25,
    difficulty: 2,
    energyCost: 1,
    status: status,
    priority: 1,
    createdAt: now,
    updatedAt: now,
  );
}

/// task-picker 数据源 fake：只覆写 getTasks（picker 唯一消费面）。
class _FakeTaskRepository extends TaskRepository {
  _FakeTaskRepository() : super(_NoopApiClient());

  List<TaskModel> tasks = [];

  @override
  Future<PaginatedResponse<TaskModel>> getTasks({
    Map<String, dynamic>? filters,
    int page = 1,
    int pageSize = 50,
  }) async =>
      PaginatedResponse<TaskModel>(
        items: List.of(tasks),
        total: tasks.length,
        page: page,
        pageSize: pageSize,
      );
}

class _NoopApiClient extends ApiClient {
  _NoopApiClient() : super(_FakeRef());

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _FakeRef implements Ref {
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

Future<void> _pump(
  WidgetTester tester,
  _FakeProvenanceRepository repo, {
  bool embedded = false,
  List<Override> extraOverrides = const [],
}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        memoryProvenanceRepositoryProvider.overrideWithValue(repo),
        ...extraOverrides,
      ],
      child: testMaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: UnderstandingOverviewView(embedded: embedded),
          ),
        ),
      ),
    ),
  );
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 100));
}

void main() {
  setUp(setUpI18nForTesting);

  testWidgets('renders the four bucket groups in user language',
      (tester) async {
    final repo = _FakeProvenanceRepository()
      ..items = [
        _entry(id: 't1', bucket: 'told', label: '你告诉我的'),
        _entry(id: 'o1', bucket: 'observed', label: '我从你的行动中观察到的'),
        _entry(id: 'u1', bucket: 'uncertain', label: '我还不确定的'),
        _entry(id: 'e1', bucket: 'effective', label: '对你有效过的方法'),
      ];
    await _pump(tester, repo);

    expect(find.text('你告诉我的'), findsOneWidget);
    expect(find.text('我从你的行动中观察到的'), findsOneWidget);
    expect(find.text('我还不确定的'), findsOneWidget);
    expect(find.text('对你有效过的方法'), findsOneWidget);
    expect(find.text('内容 t1'), findsOneWidget);
  });

  testWidgets('no jargon counters on the main presentation (copy audit)',
      (tester) async {
    final repo = _FakeProvenanceRepository()
      ..items = [
        _entry(id: 't1', bucket: 'told', label: '你告诉我的'),
      ];
    await _pump(tester, repo);

    // 黑话移除断言：旧「N 条判断 / X% 高置信 / N 条」计数主呈现不得出现。
    expect(find.textContaining('条判断'), findsNothing);
    expect(find.textContaining('高置信'), findsNothing);
    expect(find.text('0 memories'), findsNothing);
    // 来源/层级用用户语言，不出现内部参数。
    expect(find.text('已确认'), findsOneWidget);
    // 范围是 meta 行拼接字段之一。
    expect(find.textContaining('所有场景可用'), findsOneWidget);
  });

  testWidgets('empty state is a plain guided sentence, not a counter',
      (tester) async {
    final repo = _FakeProvenanceRepository()..items = const [];
    await _pump(tester, repo);

    expect(find.text('Sparkle 还不了解你'), findsOneWidget);
    expect(find.textContaining('可以随时纠正'), findsOneWidget);
  });

  testWidgets('edit action calls updateItem with the corrected content',
      (tester) async {
    final repo = _FakeProvenanceRepository()
      ..items = [_entry(id: 'a', bucket: 'told', label: '你告诉我的')];
    await _pump(tester, repo);

    await tester.tap(find.text('修改'));
    await tester.pumpAndSettle();

    final field = tester.widget<TextField>(find.byType(TextField).first);
    field.controller!.text = '纠正后的内容';
    await tester.tap(find.text('确定'));
    await tester.pumpAndSettle();

    expect(repo.updatedContent, '纠正后的内容');
  });

  testWidgets('delete action calls revoke after confirm', (tester) async {
    final repo = _FakeProvenanceRepository()
      ..items = [_entry(id: 'a', bucket: 'told', label: '你告诉我的')];
    await _pump(tester, repo);

    await tester.tap(find.text('删除'));
    await tester.pumpAndSettle();
    // 确认对话框里的「删除」。
    await tester.tap(find.widgetWithText(SparkleButton, '删除').last);
    await tester.pumpAndSettle();

    expect(repo.revokedId, 'a');
  });

  testWidgets('pause action calls updateScope(pause) after confirm',
      (tester) async {
    final repo = _FakeProvenanceRepository()
      ..items = [_entry(id: 'a', bucket: 'told', label: '你告诉我的')];
    await _pump(tester, repo);

    await tester.tap(find.text('暂时不用'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(SparkleButton, '暂时不用').last);
    await tester.pumpAndSettle();

    expect(repo.pausedId, 'a');
  });

  testWidgets('why-this receipt renders translated reasons with honest unknown',
      (tester) async {
    final repo = _FakeProvenanceRepository()
      ..items = [_entry(id: 'a', bucket: 'told', label: '你告诉我的')];
    await _pump(tester, repo);

    await tester.tap(find.text('为什么有这条'));
    await tester.pumpAndSettle();

    expect(find.text('为什么 Sparkle 用了这条'), findsOneWidget);
    expect(find.text('我在准备离散数学期末考试'), findsOneWidget);
    // 已知原因显示服务端翻译。
    expect(find.text('按与当轮内容的相关度排序选中'), findsOneWidget);
    // honest unknown：未知原因码不猜标签。
    expect(find.text('原因说明暂缺'), findsOneWidget);
    expect(find.text('按与当轮内容的相关度排序选中'), findsOneWidget);
    // 未说出原因（internal_only）。
    expect(find.text('当轮只是问候或确认，不需要引用记忆'), findsOneWidget);
    // 来源未知时的诚实标注（与使用时间拼接为同一行）。
    expect(find.textContaining('来源不明'), findsOneWidget);
    // 纠正入口。
    expect(find.text('这不对'), findsOneWidget);
  });

  testWidgets('goal link-task flow: picker renders real tasks and the '
      'picked task id reaches updateScope(link_task)', (tester) async {
    final repo = _FakeProvenanceRepository()
      ..items = [_goalEntry(id: 'g1')];
    final taskRepo = _FakeTaskRepository()
      ..tasks = [
        _taskModel(id: 'task-9', title: '刷完错题本'),
        _taskModel(
          id: 'task-done',
          title: '已完成的任务',
          status: TaskStatus.completed,
        ),
      ];
    await _pump(tester, repo, extraOverrides: [
      taskRepositoryProvider.overrideWithValue(taskRepo),
    ],);

    // 操作条出现「关联任务」（goal + set_scope 门）。
    await tester.tap(find.text('关联任务'));
    await tester.pumpAndSettle();

    // task-picker 渲染真实任务列表。
    expect(find.text('只在某个任务中使用'), findsOneWidget);
    expect(find.text('刷完错题本'), findsOneWidget);
    // 终态任务（已完成）不进候选。
    expect(find.text('已完成的任务'), findsNothing);

    // 选择任务 → pop(task.id) → provider 透传给 updateScope。
    await tester.tap(find.text('刷完错题本'));
    await tester.pumpAndSettle();

    expect(repo.lastScopeAction, 'link_task');
    expect(repo.linkedTaskId, 'task-9');
  });

  testWidgets('task picker shows the honest empty copy when no task exists',
      (tester) async {
    final repo = _FakeProvenanceRepository()
      ..items = [_goalEntry(id: 'g1')];
    final taskRepo = _FakeTaskRepository()..tasks = [];
    await _pump(tester, repo, extraOverrides: [
      taskRepositoryProvider.overrideWithValue(taskRepo),
    ],);

    await tester.tap(find.text('关联任务'));
    await tester.pumpAndSettle();

    expect(find.text('只在某个任务中使用'), findsOneWidget);
    expect(find.text('还没有可选的任务'), findsOneWidget);
  });

  testWidgets('non-goal items do not offer the link-task action',
      (tester) async {
    final repo = _FakeProvenanceRepository()
      ..items = [_entry(id: 'a', bucket: 'told', label: '你告诉我的')];
    await _pump(tester, repo);

    expect(find.text('关联任务'), findsNothing);
    expect(find.text('仅此 Goal'), findsNothing);
  });
}
