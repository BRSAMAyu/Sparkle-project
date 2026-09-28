import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/experience/presentation/providers/experience_provider.dart'
    as experience;
import 'package:sparkle/features/home/presentation/providers/understanding_snapshot_provider.dart';
import 'package:sparkle/features/memory/data/memory_provenance_models.dart';
import 'package:sparkle/features/memory/data/memory_provenance_repository.dart';
import 'package:sparkle/features/user/presentation/providers/persona_view_provider.dart';
import 'package:sparkle/features/user/presentation/providers/profile_context_provider.dart';

/// 「Sparkle 对我的理解」总览状态（U-03 四组视图）。
@immutable
class UnderstandingOverviewState {
  const UnderstandingOverviewState({
    this.isLoading = true,
    this.isLoadingMore = false,
    this.error,
    this.items = const [],
    this.total = 0,
    this.hasMore = false,
    this.scanCapped = false,
    this.pendingActionIds = const {},
    this.conflictItemIds = const {},
    this.lastEffect,
  });

  final bool isLoading;
  final bool isLoadingMore;

  /// 全量失败时的用户语言错误（detail 已提取，可为 null）。
  final String? error;

  /// 当前窗口内条目（服务端按 recency 排序，bucket 已打标）。
  final List<ProvenanceMemoryItem> items;
  final int total;
  final bool hasMore;

  /// 服务端诚实标记：单 kind 扫描达上限，列表可能不完整。
  final bool scanCapped;

  /// 操作进行中的条目 id。
  final Set<String> pendingActionIds;

  /// V4-U03：scope 校准冲突条目 id（写前读核对发现并发更改 / 后端 409）。
  /// 命中条目呈现冲突面（conflict 徽章 + 重新核对），绝不静默覆盖。
  final Set<String> conflictItemIds;

  /// 最近一次成功操作的可见效果（真实后端返回，绝不本地编造）。
  final UnderstandingEffect? lastEffect;

  bool get isEmpty => !isLoading && error == null && items.isEmpty;

  /// 按 bucket 分组（保持服务端 recency 顺序），空组不出现。
  Map<UnderstandingBucket, List<ProvenanceMemoryItem>> get grouped {
    final grouped = <UnderstandingBucket, List<ProvenanceMemoryItem>>{};
    for (final item in items) {
      grouped.putIfAbsent(item.bucket, () => []).add(item);
    }
    return grouped;
  }

  UnderstandingOverviewState copyWith({
    bool? isLoading,
    bool? isLoadingMore,
    Object? error = _sentinel,
    List<ProvenanceMemoryItem>? items,
    int? total,
    bool? hasMore,
    bool? scanCapped,
    Set<String>? pendingActionIds,
    Set<String>? conflictItemIds,
    Object? lastEffect = _sentinel,
  }) =>
      UnderstandingOverviewState(
        isLoading: isLoading ?? this.isLoading,
        isLoadingMore: isLoadingMore ?? this.isLoadingMore,
        error: error == _sentinel ? this.error : error as String?,
        items: items ?? this.items,
        total: total ?? this.total,
        hasMore: hasMore ?? this.hasMore,
        scanCapped: scanCapped ?? this.scanCapped,
        pendingActionIds: pendingActionIds ?? this.pendingActionIds,
        conflictItemIds: conflictItemIds ?? this.conflictItemIds,
        lastEffect: lastEffect == _sentinel
            ? this.lastEffect
            : lastEffect as UnderstandingEffect?,
      );

  static const Object _sentinel = Object();
}

/// 一次成功纠正/删除/scope 操作的 receipt（字段全部来自后端响应）。
@immutable
class UnderstandingEffect {
  const UnderstandingEffect({
    required this.type,
    required this.memoryId,
    this.memoryEpoch,
    this.supersededId,
    this.newItem,
  });

  final String type;
  final String memoryId;
  final int? memoryEpoch;
  final String? supersededId;
  final ProvenanceMemoryItem? newItem;
}

/// V4-U03 · scope 校准冲突：写前读核对发现服务端状态与所见不一致
/// （并发更改），或后端 409——绝不静默覆盖，操作就此停止并呈现冲突面。
class MemoryScopeConflictError implements Exception {
  const MemoryScopeConflictError(this.message);
  final String message;

  @override
  String toString() => message;
}
/// 判定一个错误是否 scope 校准冲突（类型化守卫 + 后端 409 同面）。
bool isScopeConflict(Object error) =>
    error is MemoryScopeConflictError ||
    (error is DioException && error.response?.statusCode == 409);

class UnderstandingOverviewNotifier
    extends StateNotifier<UnderstandingOverviewState> {
  UnderstandingOverviewNotifier(this._repository, this._ref)
      : super(const UnderstandingOverviewState());

  final MemoryProvenanceRepository _repository;
  final Ref _ref;

  Future<void> load() async {
    state = state.copyWith(
      isLoading: true,
      error: null,
      conflictItemIds: const <String>{},
    );
    try {
      final result = await _repository.listItems();
      if (!mounted) {
        return;
      }
      state = state.copyWith(
        isLoading: false,
        items: result.items,
        total: result.total,
        hasMore: result.hasMore,
        scanCapped: result.scanCapped,
      );
    } catch (e) {
      if (!mounted) {
        return;
      }
      state = state.copyWith(
        isLoading: false,
        error: provenanceErrorDetail(e),
      );
    }
  }

  Future<void> loadMore() async {
    if (state.isLoadingMore || !state.hasMore) {
      return;
    }
    state = state.copyWith(isLoadingMore: true);
    try {
      final result = await _repository.listItems(
        offset: state.items.length,
      );
      if (!mounted) {
        return;
      }
      final known = state.items.map((e) => e.id).toSet();
      state = state.copyWith(
        isLoadingMore: false,
        items: [
          ...state.items,
          ...result.items.where((e) => !known.contains(e.id)),
        ],
        hasMore: result.hasMore,
        scanCapped: result.scanCapped,
      );
    } catch (_) {
      if (mounted) {
        state = state.copyWith(isLoadingMore: false);
      }
      rethrow;
    }
  }

  Future<void> refresh() async {
    await load();
  }

  /// 修改（纠正）：成功后原地替换为新条目（supersede 返回新 id），
  /// 并让「下一次 decision」面同步（验收②）：
  /// - 后端已 bump memory_epoch + 发 memory.invalidated + DEL derived cache
  ///   （M-07 链，服务端保证下一次 ContextPack/decision 用新内容）；
  /// - 客户端 invalidate understandingSnapshotProvider，home/chat 的
  ///   「Sparkle 懂我」面板立即重取；
  /// - 本列表重取，界面与下一次 decision 使用同一份新数据。
  Future<void> updateItem(
    ProvenanceMemoryItem item, {
    String? content,
    Map<String, Object>? prefValue,
    String? title,
    String? reason,
  }) async {
    await _runAction(item.id, () async {
      final updated = await _repository.updateItem(
        item.kind,
        item.id,
        content: content,
        prefValue: prefValue,
        title: title,
        reason: reason,
      );
      return UnderstandingEffect(
        type: 'update',
        memoryId: item.id,
        supersededId: updated.id == item.id ? null : item.id,
        newItem: updated,
      );
    });
  }

  /// 删除（revoke）。成功后条目从界面移除，同步链同 [updateItem]。
  Future<void> revokeItem(ProvenanceMemoryItem item, {String? reason}) async {
    await _runAction(item.id, () async {
      final result = await _repository.revokeItem(
        item.kind,
        item.id,
        reason: reason,
      );
      // 后端诚实契约：只有真正进入撤销/撤回终态才报 revoked=true。
      if (result['revoked'] != true) {
        throw StateError(result['status']?.toString() ?? 'revoke failed');
      }
      return UnderstandingEffect(type: 'revoke', memoryId: item.id);
    });
  }

  /// 暂时不用（pause）/ 恢复使用（resume）。
  Future<void> setPaused(
    ProvenanceMemoryItem item, {
    required bool paused,
  }) async {
    await _guardedScopeWrite(item.id, () async {
      await _ensureScopeUnchanged(item, expectedPaused: !paused);
      final result = await _repository.updateScope(
        item.kind,
        item.id,
        action: paused ? 'pause' : 'resume',
      );
      return UnderstandingEffect(
        type: paused ? 'pause' : 'resume',
        memoryId: item.id,
        memoryEpoch: (result['memory_epoch'] as num?)?.toInt(),
      );
    });
  }

  /// 仅此 Goal：goal 条目绑定到指定计划（真实 plan_id，归属校验在后端）。
  Future<void> linkToPlan(
    ProvenanceMemoryItem item, {
    required String planId,
  }) async {
    await _guardedScopeWrite(item.id, () async {
      await _ensureScopeUnchanged(item);
      final result = await _repository.updateScope(
        item.kind,
        item.id,
        action: 'link_plan',
        planId: planId,
      );
      return UnderstandingEffect(
        type: 'link_plan',
        memoryId: item.id,
        memoryEpoch: (result['memory_epoch'] as num?)?.toInt(),
      );
    });
  }

  /// 仅此 Goal（任务粒度）：goal 条目绑定到指定任务（真实 task_id，
  /// 归属校验在后端——跨用户/缺失同报 404，客户端不预判）。
  Future<void> linkToTask(
    ProvenanceMemoryItem item, {
    required String taskId,
  }) async {
    await _guardedScopeWrite(item.id, () async {
      await _ensureScopeUnchanged(item);
      final result = await _repository.updateScope(
        item.kind,
        item.id,
        action: 'link_task',
        taskId: taskId,
      );
      return UnderstandingEffect(
        type: 'link_task',
        memoryId: item.id,
        memoryEpoch: (result['memory_epoch'] as num?)?.toInt(),
      );
    });
  }

  /// scope 写统一入口：写前核对与写后回执共用冲突登记位——守卫阶段
  /// （写前核对）与真实变更链阶段（后端 409）的冲突同面呈现。
  Future<void> _guardedScopeWrite(
    String itemId,
    Future<UnderstandingEffect> Function() action,
  ) async {
    try {
      await _runAction(itemId, action);
    } on MemoryScopeConflictError {
      if (mounted) {
        state = state.copyWith(
          conflictItemIds: {...state.conflictItemIds, itemId},
        );
      }
      rethrow;
    }
  }

  /// V4-U03 验收②：scope 写前读核对——服务端当前状态与用户所见不一致
  /// （并发更改）即停，抛 [MemoryScopeConflictError]，**绝不静默覆盖**。
  ///
  /// 核对以 GET /scope 的真实服务端投影为准：paused 位 + scope 投影
  /// （level 与 plan/task 绑定）逐项一致才放行。核对请求本身失败（断网）
  /// 不构成阻塞门：放行到真实变更链，由后端行锁 + 终态 409 兜底（对账
  /// 语义同 F03——核对不到 ≠ 核对通过，失败面照常呈现）。
  Future<void> _ensureScopeUnchanged(
    ProvenanceMemoryItem item, {
    bool? expectedPaused,
  }) async {
    Map<String, dynamic> current;
    try {
      current = await _repository.getScope(kind: item.kind, id: item.id);
    } on MemoryScopeConflictError {
      rethrow;
    } catch (_) {
      return; // 核对不可得：不预判，交给后端真实变更链裁决
    }
    if (current['editable'] == false) {
      throw const MemoryScopeConflictError('memory no longer editable');
    }
    if (expectedPaused != null && (current['paused'] == true) != expectedPaused) {
      throw MemoryScopeConflictError(
          'paused state changed concurrently (${item.id})',);
    }
    final serverScope = current['scope'] is Map
        ? Map<String, dynamic>.from(current['scope'] as Map)
        : const <String, dynamic>{};
    if (!_sameScope(serverScope, item.scope)) {
      throw MemoryScopeConflictError('scope changed concurrently (${item.id})');
    }
  }

  /// scope 投影等价（level 与 plan/task 绑定逐键一致；忽略呈现无关键）。
  static bool _sameScope(Map<String, dynamic> a, Map<String, dynamic> b) {
    if (a['level']?.toString() != b['level']?.toString()) {
      return false;
    }
    for (final key in const ['plan_id', 'task_id']) {
      final av = a[key]?.toString();
      final bv = b[key]?.toString();
      if ((av ?? '') != (bv ?? '')) {
        return false;
      }
    }
    return true;
  }

  /// Why-this receipt（查看来源）。
  Future<WhyThisResult> whyThis(ProvenanceMemoryItem item) =>
      _repository.whyThis(
        memoryRef: item.ref,
        version: item.version,
      );

  Future<void> _runAction(
    String itemId,
    Future<UnderstandingEffect> Function() action,
  ) async {
    state = state.copyWith(
      pendingActionIds: {...state.pendingActionIds, itemId},
      lastEffect: null,
    );
    try {
      final effect = await action();
      if (!mounted) {
        return;
      }
      state = state.copyWith(
        pendingActionIds:
            state.pendingActionIds.where((id) => id != itemId).toSet(),
        conflictItemIds:
            state.conflictItemIds.where((id) => id != itemId).toSet(),
        lastEffect: effect,
      );
      await _syncAfterMutation();
    } catch (e) {
      if (mounted) {
        if (isScopeConflict(e)) {
          // 冲突面（验收②）：登记条目冲突位供内联 conflict 徽章呈现，
          // 不静默覆盖；错误仍上抛由调用方决定是否 toast。
          state = state.copyWith(
            pendingActionIds:
                state.pendingActionIds.where((id) => id != itemId).toSet(),
            conflictItemIds: {...state.conflictItemIds, itemId},
          );
        } else {
          state = state.copyWith(
            pendingActionIds:
                state.pendingActionIds.where((id) => id != itemId).toSet(),
            error: provenanceErrorDetail(e),
          );
        }
      }
      rethrow;
    }
  }

  /// 验收②的同步面：重取列表 + 失效全部「当前个性化」读出面。
  ///
  /// M-10 诚实性红线（删除/修改后当前个性化正确变化）：任何成功 mutation
  /// 都必须让所有消费记忆派生数据的客户端读出面失效重取——它们缓存的是
  /// 旧个性化的快照，不清掉就会向用户展示已被删除/纠正的内容。
  /// 服务端对应保证是 M-07 链（epoch bump + memory.invalidated + derived
  /// cache DEL）；客户端这五个 provider 是各自 surface 的读缓存，语义上
  /// 与服务端 DEL 一一对应：
  /// - understandingSnapshotProvider（home/chat「Sparkle 懂我」面板，U-03）
  /// - experience 理解快照（dashboard UnderstandingSnapshotCard）
  /// - profileContext / transparentProfile / inferredPreferences
  ///   （persona 与透明档案面：「Sparkle 现在怎么看你」）
  Future<void> _syncAfterMutation() async {
    _ref
      ..invalidate(understandingSnapshotProvider)
      ..invalidate(experience.understandingSnapshotProvider)
      ..invalidate(profileContextProvider)
      ..invalidate(transparentProfileProvider)
      ..invalidate(inferredPreferencesProvider);
    try {
      final result = await _repository.listItems();
      if (!mounted) {
        return;
      }
      state = state.copyWith(
        items: result.items,
        total: result.total,
        hasMore: result.hasMore,
        scanCapped: result.scanCapped,
      );
    } catch (_) {
      // 列表重取失败时保留当前状态；错误面由调用方 toast 呈现。
    }
  }
}

final understandingOverviewProvider = StateNotifierProvider<
    UnderstandingOverviewNotifier, UnderstandingOverviewState>(
  (ref) {
    final notifier = UnderstandingOverviewNotifier(
      ref.watch(memoryProvenanceRepositoryProvider),
      ref,
    );
    unawaited(notifier.load());
    return notifier;
  },
);
