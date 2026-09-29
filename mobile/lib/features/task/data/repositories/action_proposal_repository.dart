import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/shared/widgets/action_proposal/proposal_card_models.dart';

/// X-03 `ActionCommandType` 封闭词表镜像（单一真源：backend
/// `app/core/action_command.py`；同 `ProposalSource`——词表冻结，新增项
/// 是契约变更，客户端不得私开词表外值）。
const List<String> kActionCommandTypeVocabularyMirror = <String>[
  'task.update_status',
  'task.update_fields',
  'task.create_batch',
];

/// X-03 `ProposalSource` 封闭词表镜像（单一真源：backend
/// `app/core/action_command.py`；服务端 create 对词表外值抛
/// `unknown proposal source … (closed vocabulary)` → 路由 400）。
/// 词表冻结：新增项是契约变更，须由 X-03 契约 owner 随服务端冻结测试
/// 一并登记后才可在此同步——客户端不得私开词表外值（一审 B-1 教训）。
const List<String> kProposalSourceVocabularyMirror = <String>[
  'chat',
  'task',
  'aurora',
  'system',
  'api',
];

/// V4-U02「仅本次」调整提案的入口标记（词表内取值；选择理由见
/// [ActionProposalRepository.createAdjustmentProposal] 头注）.
const String _kAdjustmentProposalSource = 'task';

/// U-04 · task 侧挂载 Action Proposal 的数据面.
///
/// 真源是 X-03 的统一 command path（网关 `/api/v1/action-proposals` 纯代理 →
/// Python 引擎）；本仓库只做投影查询与命令转发，**不重建** proposal 生命周期、
/// 幂等与授权语义（服务端幂等：X-09；UI 侧防抖在 [ProposalActionGuard]）。
class ActionProposalRepository {
  ActionProposalRepository(this._apiClient);

  final ApiClient _apiClient;

  /// V4-U02 · recovery sheet 生成「本次约束 → 行动调整」提案.
  ///
  /// 仍走 X-03 统一 command path（`POST /action-proposals`，所有入口共用、
  /// 仅 source 不同）——diff 由服务端 `prepare()` 权威计算后随投影返回，
  /// 客户端只渲染不重算（无第二 diff 权威）。本卡封闭用例：
  /// `task.update_fields`（白名单字段，见后端 TASK_FIELD_WHITELIST）。
  /// 返回**原始投影**（含权威 receipt 本体；回执门解析在消费方 fail-closed
  /// 进行——经卡模型中转会丢 receipt 本体）。
  ///
  /// 一审 B-1 返修：`source` 必须取服务端封闭词表内值
  ///（backend `app/core/action_command.py` `ProposalSource` =
  /// `{chat, task, aurora, system, api}`；词表外服务端 create 即
  /// ValueError → 400，「仅本次」链路端到端不可达）。此处取 `task`——
  /// 本提案产生于任务侧挂载的 recovery 校准面（subject 是任务、命令是
  /// `task.update_fields`），是词表内最准确的入口标记；surface 级溯源
  /// （recovery sheet）由随提案持久进审计的 `summary`（用户纠正原话）
  /// 承载，不私开词表外值。新增入口时同样只能从词表取值。
  Future<Map<String, dynamic>> createAdjustmentProposal({
    required String taskId,
    required Map<String, dynamic> fields,
    required String idempotencyKey,
    String? summary,
  }) async {
    final response = await _apiClient.post<dynamic>(
      ApiEndpoints.actionProposals,
      data: <String, dynamic>{
        'command_type': 'task.update_fields',
        'payload': <String, dynamic>{'task_id': taskId, 'fields': fields},
        'source': _kAdjustmentProposalSource,
        'idempotency_key': idempotencyKey,
        if (summary != null && summary.isNotEmpty) 'summary': summary,
      },
    );
    final data = ApiResponseParser.unwrapMap(
      response.data,
      action: 'createActionProposal',
    );
    return _unwrapProposal(data, action: 'createActionProposal');
  }

  /// 按 id 取提案详情（冲突恢复「重新查看」面；返回最新权威投影，原始形态）.
  Future<Map<String, dynamic>?> getProposal(String proposalId) async {
    try {
      final response = await _apiClient.get<dynamic>(
        ApiEndpoints.actionProposal(proposalId),
      );
      final data = ApiResponseParser.unwrapMap(
        response.data,
        action: 'getActionProposal',
      );
      return _unwrapProposal(data, action: 'getActionProposal');
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) return null;
      rethrow;
    }
  }

  /// `ProposalMutationResponse{proposal: …}` → 投影 map（缺失按错误处理，
  /// 不渲染半份）.
  Map<String, dynamic> _unwrapProposal(
    Map<String, dynamic> data, {
    required String action,
  }) {
    final proposal = data['proposal'];
    if (proposal is Map) return Map<String, dynamic>.from(proposal);
    throw StateError('action-proposals $action: proposal projection missing');
  }

  /// 某个 subject（如任务）名下的 proposal 收件箱（可按状态过滤）.
  Future<List<ActionProposalCardData>> listForSubject(
    String subjectId, {
    String? status,
  }) async {
    try {
      final response = await _apiClient.get<dynamic>(
        ApiEndpoints.actionProposals,
        queryParameters: <String, dynamic>{
          'subject_id': subjectId,
          if (status != null) 'status': status,
        },
      );
      final data = ApiResponseParser.unwrapMap(
        response.data,
        action: 'listActionProposals',
      );
      final items = data['items'];
      if (items is! List) return const <ActionProposalCardData>[];
      return items
          .whereType<Map<dynamic, dynamic>>()
          .map((e) => ActionProposalCardData.fromProjection(
                Map<String, dynamic>.from(e),
              ),)
          .toList();
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) {
        return const <ActionProposalCardData>[];
      }
      rethrow;
    }
  }

  /// 确认（幂等：重复 approve 恰一次 commit，重放返回原 receipt）.
  ///
  /// [idempotencyKey] 来自组件的稳定幂等键推导（U-04 UI 面），服务端据此
  /// 保证重复点击不重复 command。
  Future<Map<String, dynamic>?> approve(
    String proposalId,
    String idempotencyKey,
  ) =>
      _mutate(ApiEndpoints.actionProposalApprove(proposalId), idempotencyKey);

  /// 取消（terminal_reason=user_cancelled；终态封闭）。
  Future<Map<String, dynamic>?> cancel(
    String proposalId,
    String idempotencyKey,
  ) =>
      _mutate(ApiEndpoints.actionProposalCancel(proposalId), idempotencyKey);

  /// 拒绝（终态封闭，幂等 no-op）。
  ///
  /// J-04 feedback 面：[reason]（用户"这个不合适"的自由文本）随请求下发，
  /// 服务端持久进 append-only 审计（transition.details + event payload）——
  /// 拒绝理由不再被静默丢弃；省略则行为与旧契约完全一致。
  Future<Map<String, dynamic>?> reject(
    String proposalId,
    String idempotencyKey, {
    String? reason,
  }) =>
      _mutate(
        ApiEndpoints.actionProposalReject(proposalId),
        idempotencyKey,
        body: reason == null || reason.trim().isEmpty
            ? null
            : <String, dynamic>{'reason': reason.trim()},
      );

  Future<Map<String, dynamic>?> _mutate(
    String path,
    String idempotencyKey, {
    Map<String, dynamic>? body,
  }) async {
    final response = await _apiClient.post<dynamic>(
      path,
      data: <String, dynamic>{
        'idempotency_key': idempotencyKey,
        ...?body,
      },
    );
    final data = ApiResponseParser.unwrapMap(
      response.data,
      action: 'mutateActionProposal',
    );
    return data.isEmpty ? null : data;
  }
}

final actionProposalRepositoryProvider = Provider<ActionProposalRepository>((
  ref,
) {
  final apiClient = ref.watch(apiClientProvider);
  return ActionProposalRepository(apiClient);
});

/// 某任务名下待确认的 proposal 卡片数据（task_execution_screen 挂载用）.
final pendingTaskProposalsProvider =
    FutureProvider.family<List<ActionProposalCardData>, String>(
  (ref, taskId) async {
    if (taskId.isEmpty) return const <ActionProposalCardData>[];
    final repository = ref.watch(actionProposalRepositoryProvider);
    return repository.listForSubject(taskId, status: 'PENDING');
  },
);
