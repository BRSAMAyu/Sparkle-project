import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/home/presentation/providers/understanding_snapshot_provider.dart';
import 'package:sparkle/features/memory/data/memory_provenance_models.dart';
import 'package:sparkle/features/memory/data/memory_provenance_repository.dart';

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

class UnderstandingOverviewNotifier
    extends StateNotifier<UnderstandingOverviewState> {
  UnderstandingOverviewNotifier(this._repository, this._ref)
      : super(const UnderstandingOverviewState());

  final MemoryProvenanceRepository _repository;
  final Ref _ref;

  Future<void> load() async {
    state = state.copyWith(isLoading: true, error: null);
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
    await _runAction(item.id, () async {
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
    await _runAction(item.id, () async {
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
    await _runAction(item.id, () async {
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
        lastEffect: effect,
      );
      await _syncAfterMutation();
    } catch (e) {
      if (mounted) {
        state = state.copyWith(
          pendingActionIds:
              state.pendingActionIds.where((id) => id != itemId).toSet(),
          error: provenanceErrorDetail(e),
        );
      }
      rethrow;
    }
  }

  /// 验收②的同步面：重取列表 + 失效理解快照（home/chat 面板随之刷新）。
  Future<void> _syncAfterMutation() async {
    _ref.invalidate(understandingSnapshotProvider);
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
