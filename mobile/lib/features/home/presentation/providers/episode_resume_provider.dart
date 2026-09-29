import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/features/home/data/episode_resume_models.dart';
import 'package:sparkle/features/home/presentation/providers/home_growth_provider.dart';
import 'package:sparkle/features/memory/presentation/providers/context_receipt_provider.dart';

/// V4-U01 · 首页接续状态 ——「上次到哪 + 下一步」的唯一派生读面。
///
/// 数据源只接既有权威（B-02 lineage 契约，零新真源）：
/// - **哪次理解**：`contextReceiptProvider`（I06 `GET /experience/context-receipts/latest`
///   读面）。仅当 `phase=ready` 且回执 `selection_role == 'resume_view'`
///   时才可作为接续依据——角色词表（B05 §2）声明这轮回执是为接续视图做的
///   选择；拿 chat_context 等其他角色的回执冒充接续依据 = 归因错置，不做。
/// - **哪个任务**：`homeGrowthStateProvider.nextAction`（/tasks/today 既有
///   选择流，与 cockpit 主行动同一真源）。
/// - **视图本体**：I01 `GET /episode-resume/tasks/{task_id}` 读模型，携带
///   `context_selection://<receipt_id>` ref（scheme 契约：kContextSelectionRefScheme）。
///
/// 状态语义（诚实呈现，每态可失败）：
/// - [EpisodeResumePhase.hidden]：任一门未过（回执未 ready / 角色不符 /
///   无任务 / 视图降级或解析失败 / 网络失败）→ 消费方零渲染。**零假历史**：
///   新用户、读面未开（off/shadow）、已删对象等一律呈现为「无接续上下文」
///   的缺席，不造占位文案；
/// - [EpisodeResumePhase.ready]：视图可用。是否过期由消费方在渲染时刻用
///   [episodeResumeStaleReason] 现判（视图按需计算带 TTL，跨停留时间可能
///   过期——过期只允许说明不确定性，不强行接续）。
@immutable
class EpisodeResumeState {
  const EpisodeResumeState._({required this.phase, this.view, this.taskId});

  const EpisodeResumeState.hidden() : this._(phase: EpisodeResumePhase.hidden);

  const EpisodeResumeState.ready({
    required EpisodeResumeViewData this.view,
    required this.taskId,
  }) : phase = EpisodeResumePhase.ready;

  final EpisodeResumePhase phase;

  /// ready 态的视图投影（hidden 恒 null）。
  final EpisodeResumeViewData? view;

  /// 请求用的任务 id（hidden 态可为 null）。
  final String? taskId;

  /// 渲染时刻判新鲜后、且与 [taskId] 绑定的可接续 pending step 文案。
  ///
  /// 条件全部不满足 → null（主行动不得被过期/错绑视图改写——stale 不接续）。
  String? continueStepFor(String? cockpitTaskId, {required DateTime now}) {
    final view = this.view;
    if (phase != EpisodeResumePhase.ready || view == null) {
      return null;
    }
    if (cockpitTaskId == null || cockpitTaskId.isEmpty || cockpitTaskId != taskId) {
      return null;
    }
    if (episodeResumeStaleReason(view, now: now) != null) {
      return null;
    }
    return view.pendingHumanStep?.description;
  }

  /// ready 且与 cockpit 任务绑定的视图（渲染层入口；过期与否由调用方现判）。
  EpisodeResumeViewData? boundViewFor(String? cockpitTaskId) {
    final view = this.view;
    if (phase != EpisodeResumePhase.ready ||
        view == null ||
        cockpitTaskId == null ||
        cockpitTaskId.isEmpty ||
        cockpitTaskId != taskId) {
      return null;
    }
    return view;
  }
}

enum EpisodeResumePhase { hidden, ready }

/// I01 接续视图共享取数（V4-U06 抽取：U01 派生读面与 W2 bootstrap 共用，
/// 禁平行解析器——同一 `EpisodeResumeViewData.tryParse`，同一 ref scheme 契约）。
///
/// 返回 null = 视图降级（reason_code）或结构损坏（fail-closed）；网络失败原样
/// 上抛，由调用方决定缺席语义（读面降级是缺席，不是错误弹窗）。
Future<EpisodeResumeViewData?> fetchEpisodeResumeView(
  ApiClient apiClient, {
  required String taskId,
  required String receiptId,
}) async {
  final response = await apiClient.get<Map<String, dynamic>>(
    ApiEndpoints.episodeResumeTask(taskId),
    queryParameters: <String, dynamic>{
      'context_receipt_ref': '$kContextSelectionRefScheme://$receiptId',
    },
  );
  final data = response.data;
  Object? viewRaw;
  if (data != null) {
    viewRaw = data['view'];
  }
  final view = viewRaw is Map
      ? EpisodeResumeViewData.tryParse(Map<String, dynamic>.from(viewRaw))
      : null;
  return view;
}

/// 派生 FutureProvider：上游（回执读面 / today 选择流）任一变化即重算；
/// 端点失败一律落 hidden（读面降级是诚实缺席，不是错误弹窗）。
final episodeResumeProvider =
    FutureProvider<EpisodeResumeState>((ref) async {
  final receipt = ref.watch(contextReceiptProvider);
  final growthAsync = ref.watch(homeGrowthStateProvider);

  final task = growthAsync.valueOrNull?.nextAction;
  final receiptView = receipt.phase == ContextReceiptPhase.ready
      ? receipt.view
      : null;
  final taskId = (task == null || task.id.isEmpty) ? null : task.id;
  if (receiptView == null ||
      receiptView.selectionRole != 'resume_view' ||
      receiptView.receiptId.isEmpty ||
      taskId == null) {
    return const EpisodeResumeState.hidden();
  }

  try {
    final view = await fetchEpisodeResumeView(
      ref.read(apiClientProvider),
      taskId: taskId,
      receiptId: receiptView.receiptId,
    );
    if (view == null) {
      // 视图降级（reason_code）或结构损坏 → 无接续上下文，零渲染。
      return const EpisodeResumeState.hidden();
    }
    return EpisodeResumeState.ready(view: view, taskId: taskId);
  } on DioException {
    return const EpisodeResumeState.hidden();
  } catch (_) {
    return const EpisodeResumeState.hidden();
  }
}, dependencies: <ProviderOrFamily>[
  contextReceiptProvider,
  homeGrowthStateProvider,
],);
