import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/memory/data/memory_provenance_models.dart';
import 'package:sparkle/features/memory/data/memory_provenance_repository.dart';
import 'package:sparkle/features/memory/presentation/providers/understanding_overview_provider.dart';

/// V4-U03 验收②：并发更改 scope 有版本冲突，不静默覆盖。
///
/// 写前读核对（GET /scope 真实投影 vs 用户所见）+ 后端 409 同面。
/// 每面一正一反，全部可失败。
class _FakeRepository implements MemoryProvenanceRepository {
  _FakeRepository();

  /// GET /scope 返回的服务端当前投影；为抛出函数时模拟核对不可得（断网）。
  Object? serverScope = const {'level': 'global'};
  bool serverPaused = false;
  bool serverEditable = true;

  /// 非空时 GET /scope 直接抛出（核对不可得）。
  DioException? scopeReadError;

  int putCalls = 0;
  int getCalls = 0;
  DioException? putError;

  @override
  Future<ProvenanceListResult> listItems({
    UnderstandingBucket? bucket,
    String? kind,
    int limit = 200,
    int offset = 0,
    bool includeInactive = false,
  }) async =>
      const ProvenanceListResult(
        items: [],
        total: 0,
        hasMore: false,
        scanCapped: false,
      );

  @override
  Future<Map<String, dynamic>> getScope({
    required String kind,
    required String id,
  }) async {
    getCalls++;
    final error = scopeReadError;
    if (error != null) {
      throw error;
    }
    return {
      'schema_version': 'v1',
      'kind': kind,
      'id': id,
      'scope': serverScope ?? const {'level': 'global'},
      'paused': serverPaused,
      'editable': serverEditable,
      'supported_updates': ['pause', 'resume'],
    };
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
    putCalls++;
    final error = putError;
    if (error != null) {
      throw error;
    }
    return {'changed': true, 'memory_epoch': 9};
  }

  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnimplementedError('${invocation.memberName}');
}

ProvenanceMemoryItem _item({
  Map<String, dynamic> scope = const {'level': 'global'},
  String status = 'active',
}) =>
    ProvenanceMemoryItem(
      kind: 'episodic',
      id: 'mem-1',
      ref: 'memory://episodic/mem-1',
      bucket: UnderstandingBucket.told,
      bucketLabel: '你告诉我的',
      content: '我在准备离散数学期末考试',
      status: status,
      scope: scope,
      correctionCount: 0,
      evidenceMissing: false,
      confidenceTier: 'confirmed',
      confidenceTierLabel: '已确认',
      sourceLabel: '你告诉我的',
      sourceKnown: true,
      actions: const ['update', 'revoke', 'view_source', 'pause'],
    );

/// 用「所见 active 条目」驱动一次 pause；返回（错误?）。
Future<Object?> _pause(UnderstandingOverviewNotifier notifier, ProvenanceMemoryItem item) async {
  try {
    await notifier.setPaused(item, paused: true);
    return null;
  } catch (e) {
    return e;
  }
}

/// 容器装配（与既有 U-03 provider 测试同款）：注入 fake repository，
/// 从容器取 notifier（自带 Ref，成功路径的同步链照常工作）。
(UnderstandingOverviewNotifier, ProviderContainer) _harness(
  _FakeRepository repo,
) {
  final container = ProviderContainer(
    overrides: [
      memoryProvenanceRepositoryProvider.overrideWithValue(repo),
    ],
  );
  addTearDown(container.dispose);
  return (container.read(understandingOverviewProvider.notifier), container);
}

void main() {
  test('正（对照面）：服务端状态与所见一致 → 写放行（PUT 恰一次）', () async {
    final repo = _FakeRepository()
      ..serverScope = const {'level': 'global'}
      ..serverPaused = false;
    final (notifier, container) = _harness(repo);
    final item = _item();

    final error = await _pause(notifier, item);

    expect(error, isNull);
    expect(repo.getCalls, 1);
    expect(repo.putCalls, 1);
    expect(container.read(understandingOverviewProvider).conflictItemIds, isEmpty);
    expect(container.read(understandingOverviewProvider).lastEffect?.type, 'pause');
  });

  test('正：并发更改（服务端已 paused）→ 冲突，PUT 零调用（不静默覆盖）', () async {
    final repo = _FakeRepository()
      ..serverScope = const {'level': 'global'}
      ..serverPaused = true; // 别处已暂停——与所见 active 不一致
    final (notifier, container) = _harness(repo);
    final item = _item();

    final error = await _pause(notifier, item);

    expect(error, isA<MemoryScopeConflictError>());
    expect(repo.putCalls, 0, reason: '冲突即停：绝不把别处的更改覆盖掉');
    expect(container.read(understandingOverviewProvider).conflictItemIds, {'mem-1'});
  });

  test('正：并发更改（scope 投影漂移：goal 被绑到别的计划）→ 冲突，PUT 零调用', () async {
    final repo = _FakeRepository()
      ..serverScope = const {'level': 'goal', 'plan_id': 'plan-B'}
      ..serverPaused = false;
    final (notifier, container) = _harness(repo);
    final item = _item(scope: const {'level': 'goal'});

    final error = await _pause(notifier, item);

    expect(error, isA<MemoryScopeConflictError>());
    expect(repo.putCalls, 0);
    expect(container.read(understandingOverviewProvider).conflictItemIds, {'mem-1'});
  });

  test('反（变异守护）：核对不可得（断网）不构成阻塞门——放行真实变更链', () async {
    final repo = _FakeRepository()
      ..scopeReadError = DioException(
        requestOptions: RequestOptions(path: '/x'),
        type: DioExceptionType.connectionError,
      );
    final (notifier, _) = _harness(repo);
    final item = _item();

    final error = await _pause(notifier, item);

    expect(error, isNull);
    expect(repo.putCalls, 1, reason: '核对不到 ≠ 核对通过：交后端行锁+终态 409 兜底');
  });

  test('正：后端 409（终态/并发裁决）→ 同冲突面（conflictItemIds 命中）', () async {
    final repo = _FakeRepository()
      ..serverScope = const {'level': 'global'}
      ..serverPaused = false
      ..putError = DioException(
        requestOptions: RequestOptions(path: '/x'),
        response: Response<Map<String, dynamic>>(
          requestOptions: RequestOptions(path: '/x'),
          statusCode: 409,
          data: {'detail': 'memory is revoked; scope is not editable'},
        ),
      );
    final (notifier, container) = _harness(repo);
    final item = _item();

    final error = await _pause(notifier, item);

    expect(isScopeConflict(error!), isTrue);
    expect(container.read(understandingOverviewProvider).conflictItemIds, {'mem-1'});
  });

  test('正：editable=false（服务端判定不可编辑）→ 冲突，PUT 零调用', () async {
    final repo = _FakeRepository()
      ..serverScope = const {'level': 'global'}
      ..serverPaused = false
      ..serverEditable = false;
    final (notifier, _) = _harness(repo);
    final item = _item();

    final error = await _pause(notifier, item);

    expect(error, isA<MemoryScopeConflictError>());
    expect(repo.putCalls, 0);
  });

  test('isScopeConflict 判定：类型化冲突与 409 命中，普通错误不命中', () {
    expect(
      isScopeConflict(const MemoryScopeConflictError('x')),
      isTrue,
    );
    expect(
      isScopeConflict(
        DioException(
          requestOptions: RequestOptions(path: '/x'),
          response: Response<Map<String, dynamic>>(
            requestOptions: RequestOptions(path: '/x'),
            statusCode: 409,
          ),
        ),
      ),
      isTrue,
    );
    expect(
      isScopeConflict(
        DioException(
          requestOptions: RequestOptions(path: '/x'),
          response: Response<Map<String, dynamic>>(
            requestOptions: RequestOptions(path: '/x'),
            statusCode: 404,
          ),
        ),
      ),
      isFalse,
    );
    expect(isScopeConflict(StateError('boom')), isFalse);
  });
}
