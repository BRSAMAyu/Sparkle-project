import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/experience/presentation/providers/experience_provider.dart'
    as experience;
import 'package:sparkle/features/home/presentation/providers/understanding_snapshot_provider.dart';
import 'package:sparkle/features/memory/data/memory_provenance_models.dart';
import 'package:sparkle/features/memory/data/memory_provenance_repository.dart';
import 'package:sparkle/features/memory/presentation/providers/understanding_overview_provider.dart';
import 'package:sparkle/features/user/presentation/providers/persona_view_provider.dart';
import 'package:sparkle/features/user/presentation/providers/profile_context_provider.dart';

/// U-03 provider 级测试：四组分组 + 纠正/删除/scope 后界面与下一次
/// decision 数据源同步（acceptance ②）。
class _FakeProvenanceRepository implements MemoryProvenanceRepository {
  _FakeProvenanceRepository();

  List<ProvenanceMemoryItem> items = [];
  int listCalls = 0;
  String? lastScopeAction;
  String? linkedPlanId;
  String? linkedTaskId;

  @override
  Future<ProvenanceListResult> listItems({
    UnderstandingBucket? bucket,
    String? kind,
    int limit = 200,
    int offset = 0,
    bool includeInactive = false,
  }) async {
    listCalls++;
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
    // episodic supersede 语义：服务端返回新 id 的新条目。
    final old = items.firstWhere((e) => e.id == id);
    final updated = ProvenanceMemoryItem(
      kind: old.kind,
      id: 'new-$id',
      ref: 'memory://$kind/new-$id',
      bucket: old.bucket,
      bucketLabel: old.bucketLabel,
      content: content ?? old.content,
      status: 'active',
      scope: old.scope,
      correctionCount: old.correctionCount + 1,
      evidenceMissing: false,
      confidenceTier: old.confidenceTier,
      confidenceTierLabel: old.confidenceTierLabel,
      sourceLabel: old.sourceLabel,
      sourceKnown: true,
      actions: old.actions,
      updatedAt: DateTime(2026, 9, 22),
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
            status: 'revoked',
            scope: entry.scope,
            correctionCount: entry.correctionCount,
            evidenceMissing: false,
            confidenceTier: entry.confidenceTier,
            confidenceTierLabel: entry.confidenceTierLabel,
            sourceLabel: entry.sourceLabel,
            sourceKnown: true,
            actions: const ['view_source'],
          )
        else
          entry,
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
    lastScopeAction = action;
    linkedPlanId = planId;
    linkedTaskId = taskId;
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
            status: action == 'pause' ? 'archived' : 'active',
            scope: action == 'link_plan'
                ? {'level': 'goal', 'plan_id': planId}
                : action == 'link_task'
                    ? {'level': 'goal', 'task_id': taskId}
                    : entry.scope,
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
    return {
      'changed': true,
      'paused': action == 'pause',
      'memory_epoch': 11,
    };
  }

  @override
  Future<ProvenanceSourceInfo> getSource({
    required String kind,
    required String id,
  }) =>
      throw UnimplementedError();

  @override
  Future<Map<String, dynamic>> getScope({
    required String kind,
    required String id,
  }) =>
      throw UnimplementedError();

  @override
  Future<WhyThisResult> whyThis({
    required String memoryRef,
    int? version,
    String? packId,
    List<String> whyIncluded = const [],
    List<Map<String, Object>> internalOnly = const [],
  }) =>
      throw UnimplementedError();
}

/// 计数型 ApiClient：验证纠正后理解快照与全部个性化读出面被失效重取。
class _CountingSnapshotApiClient implements ApiClient {
  int snapshotGets = 0;
  int profileContextGets = 0;
  int transparentProfileGets = 0;
  int inferredPreferencesGets = 0;

  @override
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    if (path == '/experience/understanding-snapshot') {
      snapshotGets++;
    }
    if (path == '/profile/context') {
      profileContextGets++;
    }
    if (path == '/profile/transparent') {
      transparentProfileGets++;
    }
    if (path == '/profile/inferred-preferences') {
      inferredPreferencesGets++;
    }
    if (path.startsWith('/profile/')) {
      // inferred-preferences 后端返回 list[dict]（profile_transparency.py），
      // 仓库层按 List<dynamic> 解；其余 /profile/* 返回 map。
      final data = path == '/profile/inferred-preferences'
          ? <dynamic>[]
          : <String, dynamic>{};
      return Response<T>(
        requestOptions: RequestOptions(path: path),
        data: data as T,
      );
    }
    return Response<T>(
      requestOptions: RequestOptions(path: path),
      data: <String, dynamic>{
        'claims': <Map<String, dynamic>>[],
        'recently_corrected': <Map<String, dynamic>>[],
        'memory_declarations': <Map<String, dynamic>>[],
        'envelope_style': const <String, String>{
          'current_tone': '',
          'current_verbosity': '',
          'reason_for_style': '',
        },
        'last_update_time': '2026-09-21T08:00:00',
        'total_claims': 0,
        'high_confidence_ratio': 0,
      } as T,
    );
  }

  @override
  Future<Response<T>> post<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) =>
      throw UnimplementedError();

  @override
  Future<Response<T>> put<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) =>
      throw UnimplementedError();

  @override
  Future<Response<T>> patch<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) =>
      throw UnimplementedError();

  @override
  Future<Response<T>> delete<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) =>
      throw UnimplementedError();

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
  Dio get dio => throw UnimplementedError();
}

ProvenanceMemoryItem _entry({
  required String id,
  required String bucket,
  String kind = 'episodic',
  String status = 'active',
}) {
  final bucketEnum = understandingBucketFromName(bucket)!;
  return ProvenanceMemoryItem(
    kind: kind,
    id: id,
    ref: 'memory://$kind/$id',
    bucket: bucketEnum,
    bucketLabel: bucketEnum.name,
    content: '内容 $id',
    status: status,
    scope: const {'level': 'global'},
    correctionCount: 0,
    evidenceMissing: false,
    confidenceTier: 'confirmed',
    confidenceTierLabel: '已确认',
    sourceLabel: '你告诉我的',
    sourceKnown: true,
    actions: const ['update', 'revoke', 'view_source', 'pause', 'set_scope'],
  );
}

void main() {
  test('load groups items into the four U-03 buckets in server order', () async {
    final repo = _FakeProvenanceRepository()
      ..items = [
        _entry(id: 't1', bucket: 'told'),
        _entry(id: 'o1', bucket: 'observed'),
        _entry(id: 'u1', bucket: 'uncertain'),
        _entry(id: 'e1', bucket: 'effective'),
      ];
    final container = ProviderContainer(
      overrides: [
        memoryProvenanceRepositoryProvider.overrideWithValue(repo),
      ],
    );
    addTearDown(container.dispose);

    final notifier = container.read(understandingOverviewProvider.notifier);
    await notifier.refresh();
    final state = container.read(understandingOverviewProvider);

    expect(state.grouped.keys.toSet(), {
      UnderstandingBucket.told,
      UnderstandingBucket.observed,
      UnderstandingBucket.uncertain,
      UnderstandingBucket.effective,
    });
    expect(state.grouped[UnderstandingBucket.told]!.single.id, 't1');
    expect(state.isEmpty, isFalse);
  });

  test('updateItem replaces the item and refetches the list', () async {
    final repo = _FakeProvenanceRepository()
      ..items = [_entry(id: 'a', bucket: 'told')];
    final container = ProviderContainer(
      overrides: [
        memoryProvenanceRepositoryProvider.overrideWithValue(repo),
      ],
    );
    addTearDown(container.dispose);
    final notifier = container.read(understandingOverviewProvider.notifier);
    await notifier.refresh();

    final before = repo.listCalls;
    await notifier.updateItem(
          repo.items.single,
          content: '改后的内容',
          reason: 'user_edit',
        );

    final state = container.read(understandingOverviewProvider);
    expect(state.lastEffect?.type, 'update');
    expect(state.lastEffect?.supersededId, 'a');
    expect(state.items.single.id, 'new-a');
    expect(state.items.single.content, '改后的内容');
    expect(repo.listCalls, greaterThan(before));
  });

  test('revokeItem removes the item from the face (server hides terminal)',
      () async {
    final repo = _FakeProvenanceRepository()
      ..items = [_entry(id: 'a', bucket: 'told')];
    // revoke 后服务端列表不再返回该条（include_inactive=false）。
    final container = ProviderContainer(
      overrides: [
        memoryProvenanceRepositoryProvider.overrideWithValue(repo),
      ],
    );
    addTearDown(container.dispose);
    final notifier = container.read(understandingOverviewProvider.notifier);
    await notifier.refresh();
    // 模拟服务端隐藏已删除条目：revoke 同步链会重取列表。
    final itemBeforeRevoke = repo.items.single;
    repo.items = const [];
    await notifier.revokeItem(itemBeforeRevoke);

    final state = container.read(understandingOverviewProvider);
    expect(state.lastEffect?.type, 'revoke');
    expect(state.items, isEmpty);
    expect(state.isEmpty, isTrue);
  });

  test('setPaused flags the item as paused and reports the real epoch',
      () async {
    final repo = _FakeProvenanceRepository()
      ..items = [_entry(id: 'a', bucket: 'observed')];
    final container = ProviderContainer(
      overrides: [
        memoryProvenanceRepositoryProvider.overrideWithValue(repo),
      ],
    );
    addTearDown(container.dispose);
    final notifier = container.read(understandingOverviewProvider.notifier);
    await notifier.refresh();

    await notifier.setPaused(repo.items.single, paused: true);

    final state = container.read(understandingOverviewProvider);
    expect(state.lastEffect?.type, 'pause');
    expect(state.lastEffect?.memoryEpoch, 11);
    expect(state.items.single.isPaused, isTrue);
  });

  test('linkToTask sends the link_task scope action with the picked task id',
      () async {
    final repo = _FakeProvenanceRepository()
      ..items = [_entry(id: 'g1', bucket: 'told', kind: 'goal')];
    final container = ProviderContainer(
      overrides: [
        memoryProvenanceRepositoryProvider.overrideWithValue(repo),
      ],
    );
    addTearDown(container.dispose);
    final notifier = container.read(understandingOverviewProvider.notifier);
    await notifier.refresh();
    final listCallsBefore = repo.listCalls;

    await notifier.linkToTask(repo.items.single, taskId: 'task-9');

    // 契约：PUT scope body 的 action=link_task + task_id 原样透传（归属校验
    // 在后端）。effect 报真实 epoch，且走 _syncAfterMutation 同步链。
    expect(repo.lastScopeAction, 'link_task');
    expect(repo.linkedTaskId, 'task-9');
    final state = container.read(understandingOverviewProvider);
    expect(state.lastEffect?.type, 'link_task');
    expect(state.lastEffect?.memoryEpoch, 11);
    expect(state.items.single.scope, {'level': 'goal', 'task_id': 'task-9'});
    expect(repo.listCalls, greaterThan(listCallsBefore));
  });

  test('correction invalidates understandingSnapshotProvider (acceptance 2)',
      () async {
    final repo = _FakeProvenanceRepository()
      ..items = [_entry(id: 'a', bucket: 'told')];
    final api = _CountingSnapshotApiClient();
    final container = ProviderContainer(
      overrides: [
        memoryProvenanceRepositoryProvider.overrideWithValue(repo),
        apiClientProvider.overrideWithValue(api),
      ],
    );
    addTearDown(container.dispose);

    // 首次读取理解快照（1 次 GET）。
    await container.read(understandingSnapshotProvider.future);
    final getsBefore = api.snapshotGets;

    await container
        .read(understandingOverviewProvider.notifier)
        .updateItem(repo.items.single, content: '纠正', reason: 'user_edit');

    // 纠正后快照被 invalidate；再次读取应触发重新拉取（下一次 decision 面
    // 使用新数据）。
    await container.read(understandingSnapshotProvider.future);
    expect(api.snapshotGets, greaterThan(getsBefore));
  });

  test(
      'M-10: mutation resyncs every current-personalization read surface',
      () async {
    // 诚实性红线（删除后当前个性化正确变化）：mutation 成功后，客户端所有
    // 消费记忆派生数据的读出面都必须失效重取——home/chat 面板、dashboard
    // 理解快照卡、persona 画像与透明档案/推断偏好。任何一个不清缓存都会
    // 把已被删除/纠正的个性化当现状展示。
    final repo = _FakeProvenanceRepository()
      ..items = [_entry(id: 'd1', bucket: 'told')];
    final api = _CountingSnapshotApiClient();
    final container = ProviderContainer(
      overrides: [
        memoryProvenanceRepositoryProvider.overrideWithValue(repo),
        apiClientProvider.overrideWithValue(api),
      ],
    );
    addTearDown(container.dispose);

    // 预热全部五个读出面（home/chat 面板与 dashboard 快照卡共用同一
    // GET 路径，各计 1 次 → snapshotGets=2；profile 三面各 1 次）。
    await container.read(understandingSnapshotProvider.future);
    await container.read(experience.understandingSnapshotProvider.future);
    await container.read(profileContextProvider.future);
    await container.read(transparentProfileProvider.future);
    await container.read(inferredPreferencesProvider.future);
    final snapshotGetsBefore = api.snapshotGets;
    final contextGetsBefore = api.profileContextGets;
    final transparentGetsBefore = api.transparentProfileGets;
    final inferredGetsBefore = api.inferredPreferencesGets;
    expect(snapshotGetsBefore, 2);
    expect(contextGetsBefore, 1);
    expect(transparentGetsBefore, 1);
    expect(inferredGetsBefore, 1);

    await container
        .read(understandingOverviewProvider.notifier)
        .revokeItem(repo.items.single, reason: 'user_deleted');

    // 删除后五个面全部重取（invalidate 后再读 = 重新 GET，计数各 +1 面）。
    await container.read(understandingSnapshotProvider.future);
    await container.read(experience.understandingSnapshotProvider.future);
    await container.read(profileContextProvider.future);
    await container.read(transparentProfileProvider.future);
    await container.read(inferredPreferencesProvider.future);

    expect(api.snapshotGets, snapshotGetsBefore + 2);
    expect(api.profileContextGets, greaterThan(contextGetsBefore));
    expect(api.transparentProfileGets, greaterThan(transparentGetsBefore));
    expect(api.inferredPreferencesGets, greaterThan(inferredGetsBefore));
  });
}
