import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/widgets/graphite_surfaces.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/design/widgets/object_unavailable_surface.dart';
import 'package:sparkle/core/display/lexicon/error_lexicon.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/home/home_routes.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/features/task/presentation/screens/task_execution_screen.dart';
import 'package:sparkle/features/task/utils/task_identity.dart';
import 'package:sparkle/shared/entities/task_model.dart';

/// 执行屏装配签名（测试注入锚点：widget 测试注入桩屏，不泵真实执行屏）。
typedef ExecutionScreenBuilder = Widget Function(
  String? origin,
  String? interventionId,
);

Widget _defaultExecutionScreenBuilder(String? origin, String? interventionId) =>
    TaskExecutionScreen(origin: origin, interventionId: interventionId);

/// U14 · 任务深链闸（卡验收 3：「通知落真实对象，已删对象提示而非空白」）。
///
/// 背景（差量勘察）：`/tasks/:id/execute` 路由此前完全忽略 `:id`——
/// [TaskExecutionScreen] 只渲染 `activeTaskProvider` 的当前快照。通知/推送
/// 深链落到已删任务时：active 为空 → 泛化「无任务」面；active 残留旧快照
/// → **渲染错误的任务**。两条都违反「落真实对象」。
///
/// 本闸在路由层（task_routes.dart，非 RF-06 冲突面）解析 `:id`：
/// 1. active 已是目标 id → 直接透传执行屏（应用内既有路径零差量）；
/// 2. 本地列表缓存命中 → 设 active 后进执行屏（离线/本地任务真实落点）；
/// 3. 服务端 id → 仓储 `getTask` 确证 → 命中进执行屏；404 类确证 →
///    「已删除或不存在」统一面；无法确证（断网/服务异常）→ 可重试的
///    「暂时无法确认」面（绝不凭空宣布「已删除」）；
/// 4. 本地-only id（访客离线任务，无服务端真源）→ 强制刷新本地列表后再查，
///    仍无 → 已删除面。
///
/// 判定一律走 `error_lexicon.dart` 单一 owner（N16：新域禁建私有映射），
/// 本闸只做「类别 → 面」的纯绑定；SCREEN_FAMILIES 要求 404/离线/登录失效
/// 语义互相分开，不全部跳通用错误页。
class TaskExecutionDeepLinkGate extends ConsumerStatefulWidget {
  const TaskExecutionDeepLinkGate({
    required this.taskId,
    this.origin,
    this.interventionId,
    this.missingReplacementRoute = '/tasks',
    @visibleForTesting ExecutionScreenBuilder? screenBuilder,
    super.key,
  }) : _screenBuilder = screenBuilder ?? _defaultExecutionScreenBuilder;

  final String taskId;
  final String? origin;
  final String? interventionId;

  /// 已删/不存在面的列表出口（由 task_routes.dart 传 TaskRoutes.home，
  /// core/feature 路由常量不反向进入本闸默认值之外逻辑）。
  final String missingReplacementRoute;

  final ExecutionScreenBuilder _screenBuilder;

  @override
  ConsumerState<TaskExecutionDeepLinkGate> createState() =>
      _TaskExecutionDeepLinkGateState();
}

class _TaskExecutionDeepLinkGateState
    extends ConsumerState<TaskExecutionDeepLinkGate> {
  _GatePhase _phase = _GatePhase.resolving;
  String? _unreachableMessage;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        unawaited(resolveTarget());
      }
    });
  }

  /// 解析深链目标（@visibleForTesting：测试直接驱动，不走 postFrame 时序）。
  @visibleForTesting
  Future<void> resolveTarget() async {
    // ── 快路径：active 已是目标（应用内既有流已设好），零仓储调用 ──
    final active = ref.read(activeTaskProvider);
    if (active?.id == widget.taskId) {
      _markReady();
      return;
    }

    // ── 本地列表缓存（已装载快照）──
    final cached = _findInLocalLists();
    if (cached != null) {
      _activateAndReady(cached);
      return;
    }

    // ── 本地-only id：无服务端真源，刷新本地列表后再查 ──
    if (isLocalOnlyTaskId(widget.taskId)) {
      try {
        await ref.read(taskListProvider.notifier).loadTasks();
      } catch (_) {
        _markUnreachable(null);
        return;
      }
      final localOnly = _findInLocalLists();
      if (localOnly != null) {
        _activateAndReady(localOnly);
      } else {
        _markMissing();
      }
      return;
    }

    // ── 服务端 id：仓储确证（404 → 已删面；断网/服务异常 → 可重试面）──
    try {
      final task =
          await ref.read(taskRepositoryProvider).getTask(widget.taskId);
      _activateAndReady(task);
    } catch (error) {
      if (!mounted) return;
      final category = categorizeUiError(error);
      switch (category) {
        case UiErrorCategory.notFound:
          _markMissing();
        default:
          // 网络/超时/服务端/未分类：「无法确认」，如实可重试；
          // 不凭空宣布已删除（诚实原则）。
          _markUnreachable(uiErrorMessage(context.l10n, category));
      }
    }
  }

  TaskModel? _findInLocalLists() {
    final state = ref.read(taskListProvider);
    for (final list in <List<TaskModel>>[
      state.tasks,
      state.todayTasks,
      state.recommendedTasks,
    ]) {
      for (final task in list) {
        if (task.id == widget.taskId) {
          return task;
        }
      }
    }
    return null;
  }

  void _activateAndReady(TaskModel task) {
    if (!mounted) return;
    ref.read(activeTaskProvider.notifier).state = task;
    _markReady();
  }

  void _markReady() {
    if (!mounted) return;
    setState(() {
      _phase = _GatePhase.ready;
      _unreachableMessage = null;
    });
  }

  void _markMissing() {
    if (!mounted) return;
    setState(() {
      _phase = _GatePhase.missing;
      _unreachableMessage = null;
    });
  }

  void _markUnreachable(String? message) {
    if (!mounted) return;
    setState(() {
      _phase = _GatePhase.unreachable;
      _unreachableMessage = message;
    });
  }

  @override
  Widget build(BuildContext context) {
    switch (_phase) {
      case _GatePhase.ready:
        return widget._screenBuilder(widget.origin, widget.interventionId);
      case _GatePhase.missing:
        return _GateShell(
          child: ObjectUnavailableSurface(
            kind: ObjectUnavailableKind.missing,
            title: context.l10n.objectUnavailableMissingTitle,
            body: context.l10n.objectUnavailableMissingBody,
            fallbackRoute: HomeRoutes.home,
            primaryLabel: context.l10n.objectUnavailableGoTasks,
            // 用 go 而非 push：失效深链不入返回栈（返回不应回到已删对象）。
            onPrimary: () =>
                GoRouter.of(context).go(widget.missingReplacementRoute),
          ),
        );
      case _GatePhase.unreachable:
        return _GateShell(
          child: ObjectUnavailableSurface(
            kind: ObjectUnavailableKind.offline,
            title: context.l10n.objectUnavailableOfflineTitle,
            body: _unreachableMessage ??
                context.l10n.objectUnavailableOfflineBody,
            fallbackRoute: HomeRoutes.home,
            primaryLabel: context.l10n.retry,
            onPrimary: () {
              setState(() => _phase = _GatePhase.resolving);
              unawaited(resolveTarget());
            },
          ),
        );
      case _GatePhase.resolving:
        // 解析中的真实中间态：轻量加载指示，不造进度、不预渲染任务。
        return _GateShell(
          child: Center(child: LoadingIndicator.circular()),
        );
    }
  }
}

enum _GatePhase { resolving, ready, missing, unreachable }

class _GateShell extends StatelessWidget {
  const _GateShell({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) =>
      GraphiteScaffold(appBar: AppBar(), child: child);
}
