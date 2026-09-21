import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/shared/widgets/action_proposal/proposal_card_models.dart';

/// U-04 · task 侧挂载 Action Proposal 的数据面.
///
/// 真源是 X-03 的统一 command path（网关 `/api/v1/action-proposals` 纯代理 →
/// Python 引擎）；本仓库只做投影查询与命令转发，**不重建** proposal 生命周期、
/// 幂等与授权语义（服务端幂等：X-09；UI 侧防抖在 [ProposalActionGuard]）。
class ActionProposalRepository {
  ActionProposalRepository(this._apiClient);

  final ApiClient _apiClient;

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
  Future<Map<String, dynamic>?> reject(
    String proposalId,
    String idempotencyKey,
  ) =>
      _mutate(ApiEndpoints.actionProposalReject(proposalId), idempotencyKey);

  Future<Map<String, dynamic>?> _mutate(
    String path,
    String idempotencyKey,
  ) async {
    final response = await _apiClient.post<dynamic>(
      path,
      data: <String, dynamic>{'idempotency_key': idempotencyKey},
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
