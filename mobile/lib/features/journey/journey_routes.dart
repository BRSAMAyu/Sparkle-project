import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/features/journey/presentation/screens/hybrid_workbench_screen.dart';

/// 运行工作台路由（V4-U04，只增不改——不触碰五 Tab 路由合同与既有路由）。
///
/// FIX535 入口面：HybridJourneySheet 此前是孤儿入口（无任何调用点），本路由
/// 把它挂到合法提案/运行面——
/// - 任务面（提案卡旁）经 [HybridJourneyEntrySection] 进入；
/// - OpenClaw hub 概览经「运行工作台」按钮进入（沿用 OpenClaw 路径与 Run ID，
///   不创建第二 Agent 中心，SCREEN_FAMILIES「运行台」红线）；
/// - 跨端/冷启动恢复深链：`run_id` 查询参数直接续跑**同一段** run（幂等读面，
///   不新建 run、不重复生成工件）；带 `task_id` 时启动以该任务为锚
///   （`j06:start:<taskId>`，跨端同键同 run）——一审 F-B 勘误：此前 task_id
///   只生成于 URI、路由侧无人消费（死参数），现由路由消费传入工作台。
class JourneyRoutes {
  static const String workbench = '/journey/workbench';

  static String workbenchUri({String? runId, String? taskId}) {
    final query = <String, String>{
      if (runId != null && runId.isNotEmpty) 'run_id': runId,
      if (taskId != null && taskId.isNotEmpty) 'task_id': taskId,
    };
    if (query.isEmpty) return workbench;
    final encoded = query.entries
        .map((e) => '${e.key}=${Uri.encodeComponent(e.value)}')
        .join('&');
    return '$workbench?$encoded';
  }

  static List<RouteBase> get routes => [
        GoRoute(
          path: workbench,
          name: 'hybridWorkbench',
          pageBuilder: (BuildContext context, GoRouterState state) {
            final query = state.uri.queryParameters;
            return buildSparkleTransitionPage(
              state: state,
              child: HybridWorkbenchScreen(
                initialRunId: query['run_id'],
                initialTaskId: query['task_id'],
              ),
            );
          },
        ),
      ];
}
