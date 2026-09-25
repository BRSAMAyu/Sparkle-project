import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/features/task/data/repositories/action_proposal_repository.dart';

/// J-04 · First Meaningful Action 数据面（链路六环的移动端入口）.
///
/// 真源对齐（不重建）：
/// - 链路权威在 Python 引擎 `app.services.first_action_service`（Goal 真源 =
///   onboarding memory_goals；mode 权威 = Aurora 分配策略；proposal 生命周期 =
///   X-03 ActionCommandService 统一 command path）。本仓库只做投影查询与命令
///   转发，approve/reject 直接复用 [ActionProposalRepository]（X-03 端点面）。
/// - **诚实失败**：`POST /journey/first-action` 的 503/422 映射为
///   [FirstActionGenerationException]（retryable/reason 结构化）——不把失败
///   吞成空态，更不假装成功。
class FirstActionGoal {
  const FirstActionGoal({
    required this.goalId,
    required this.title,
    this.goalType,
  });

  factory FirstActionGoal.fromJson(Map<String, dynamic> json) =>
      FirstActionGoal(
        goalId: (json['goal_id'] ?? '').toString(),
        title: (json['title'] ?? '').toString(),
        goalType: json['goal_type']?.toString(),
      );

  final String goalId;
  final String title;
  final String? goalType;
}

class FirstActionTaskRef {
  const FirstActionTaskRef({
    required this.id,
    required this.title,
    required this.status,
  });

  factory FirstActionTaskRef.fromJson(Map<String, dynamic> json) =>
      FirstActionTaskRef(
        id: (json['id'] ?? '').toString(),
        title: (json['title'] ?? '').toString(),
        status: (json['status'] ?? '').toString(),
      );

  final String id;
  final String title;
  final String status;
}

/// `/journey/first-action` 的链路状态投影（重开 App 的持久化回放面）.
@immutable
class FirstActionState {
  const FirstActionState({
    this.goal,
    this.proposal = const <String, dynamic>{},
    this.tasks = const <FirstActionTaskRef>[],
  });

  factory FirstActionState.fromJson(Map<String, dynamic> json) =>
      FirstActionState(
        goal: json['goal'] is Map
            ? FirstActionGoal.fromJson(
                Map<String, dynamic>.from(json['goal'] as Map),
              )
            : null,
        proposal: json['proposal'] is Map
            ? Map<String, dynamic>.from(json['proposal'] as Map)
            : const <String, dynamic>{},
        tasks: (json['tasks'] as List? ?? const <dynamic>[])
            .whereType<Map<dynamic, dynamic>>()
            .map(
              (e) => FirstActionTaskRef.fromJson(
                Map<String, dynamic>.from(e),
              ),
            )
            .toList(),
      );

  final FirstActionGoal? goal;

  /// 最新 first-action proposal 的 X-03 投影（PENDING/COMMITTED/REJECTED…）.
  final Map<String, dynamic> proposal;
  final List<FirstActionTaskRef> tasks;

  String? get proposalId =>
      proposal.isEmpty ? null : (proposal['proposal_id'] ?? '').toString();

  String? get proposalStatus =>
      proposal.isEmpty ? null : (proposal['status'] ?? '').toString();

  bool get hasPendingProposal => proposalStatus == 'PENDING';

  bool get hasCommittedProposal => proposalStatus == 'COMMITTED';
}

/// 第一步 step 内容（从 X-03 proposal payload 的 action_plan 块投影）.
@immutable
class FirstActionStep {
  const FirstActionStep({
    required this.title,
    required this.stepDescription,
    required this.outcome,
    required this.evidenceKind,
    required this.executionMode,
    this.estimatedMinutes,
    this.usefulBecause = const <String>[],
  });

  /// X-03 proposal payload → step 投影（task.create_batch 恰一任务）。
  static FirstActionStep? fromProposal(Map<String, dynamic> proposal) {
    final payload = proposal['payload'];
    if (payload is! Map) return null;
    final tasks = payload['tasks'];
    if (tasks is! List || tasks.isEmpty) return null;
    final task = tasks.first;
    if (task is! Map) return null;
    final plan = task['action_plan'];
    if (plan is! Map) return null;
    final step = plan['smallest_useful_step'];
    final evidence = plan['completion_evidence'];
    return FirstActionStep(
      title: (task['title'] ?? '').toString(),
      stepDescription: step is Map
          ? (step['description'] ?? '').toString()
          : '',
      outcome: (plan['desired_outcome'] ?? '').toString(),
      evidenceKind: evidence is List && evidence.isNotEmpty
          ? ((evidence.first as Map)['evidence_kind'] ?? '').toString()
          : '',
      executionMode: (plan['execution_mode'] ?? '').toString(),
      estimatedMinutes: task['estimated_minutes'] is int
          ? task['estimated_minutes'] as int
          : null,
      usefulBecause: step is Map
          ? (step['useful_because'] as List? ?? const [])
              .map((e) => e.toString())
              .toList()
          : const <String>[],
    );
  }

  final String title;
  final String stepDescription;

  /// Action 三字段之一：产出（desired_outcome）.
  final String outcome;

  /// Action 三字段之一：完成证据（completion_evidence[0].evidence_kind）.
  final String evidenceKind;

  /// Action 三字段之一：轮到谁（execution_mode：human/agent/hybrid）.
  final String executionMode;
  final int? estimatedMinutes;
  final List<String> usefulBecause;
}

/// 生成失败的诚实异常（503 aurora 推导失败 / 422 无目标）.
class FirstActionGenerationException implements Exception {
  FirstActionGenerationException({
    required this.error,
    required this.retryable,
    this.statusCode,
  });

  final String error;
  final bool retryable;
  final int? statusCode;

  bool get noGoal => error == 'no_active_goal';
}

class FirstActionRepository {
  FirstActionRepository(this._apiClient, this._proposalRepository);

  final ApiClient _apiClient;
  final ActionProposalRepository _proposalRepository;

  /// 链路状态（重开 App 的持久化回放：goal + proposal + 已建任务）.
  Future<FirstActionState?> fetchState() async {
    try {
      final response = await _apiClient.get<dynamic>(
        ApiEndpoints.journeyFirstAction,
      );
      final data = ApiResponseParser.unwrapMap(
        response.data,
        action: 'fetchFirstActionState',
      );
      return FirstActionState.fromJson(data);
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) return null;
      rethrow;
    }
  }

  /// 生成第一步 proposal（Context→Aurora→X-03 统一 command path）.
  ///
  /// 失败诚实上抛：503（aurora 推导失败，retryable）/ 422（无 active goal）
  /// → [FirstActionGenerationException]；其余网络错误原样上抛。
  Future<FirstActionState> generate({required String idempotencyKey}) async {
    try {
      final response = await _apiClient.post<dynamic>(
        ApiEndpoints.journeyFirstAction,
        data: <String, dynamic>{'idempotency_key': idempotencyKey},
      );
      final data = ApiResponseParser.unwrapMap(
        response.data,
        action: 'generateFirstAction',
      );
      return FirstActionState(
        proposal: data['proposal'] is Map
            ? Map<String, dynamic>.from(data['proposal'] as Map)
            : const <String, dynamic>{},
      );
    } on DioException catch (e) {
      final status = e.response?.statusCode;
      if (status == 503 || status == 422) {
        final detail = e.response?.data;
        final detailMap = detail is Map
            ? (detail['detail'] is Map
                ? Map<String, dynamic>.from(detail['detail'] as Map)
                : const <String, dynamic>{})
            : const <String, dynamic>{};
        throw FirstActionGenerationException(
          error: (detailMap['error'] ??
                  (status == 422 ? 'no_active_goal' : 'first_action_generation_failed'))
              .toString(),
          retryable: detailMap['retryable'] == true || status == 503,
          statusCode: status,
        );
      }
      rethrow;
    }
  }

  /// 确认（幂等：重复 approve 恰一次 commit；重放返回原 receipt）.
  Future<Map<String, dynamic>?> approve(
    String proposalId,
    String idempotencyKey,
  ) =>
      _proposalRepository.approve(proposalId, idempotencyKey);

  /// 拒绝（[reason] 进服务端 feedback 审计——拒绝不静默丢弃）.
  Future<Map<String, dynamic>?> reject(
    String proposalId,
    String idempotencyKey, {
    String? reason,
  }) =>
      _proposalRepository.reject(proposalId, idempotencyKey, reason: reason);

  /// 编辑（拒绝旧提案 + 同链路重提案；编辑 delta 进服务端 feedback 审计）.
  Future<Map<String, dynamic>?> edit(
    String proposalId, {
    required Map<String, dynamic> editedFields,
    required String idempotencyKey, String? reason,
  }) async {
    final response = await _apiClient.post<dynamic>(
      ApiEndpoints.journeyFirstActionEdit(proposalId),
      data: <String, dynamic>{
        'edited_fields': editedFields,
        if (reason != null && reason.trim().isNotEmpty) 'reason': reason.trim(),
        'idempotency_key': idempotencyKey,
      },
    );
    final data = ApiResponseParser.unwrapMap(
      response.data,
      action: 'editFirstAction',
    );
    return data.isEmpty ? null : data;
  }
}

final firstActionRepositoryProvider = Provider<FirstActionRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  final proposalRepository = ref.watch(actionProposalRepositoryProvider);
  return FirstActionRepository(apiClient, proposalRepository);
});

/// 链路状态读面（挂载点自守门：无 goal / 未认证 → null → 卡片零布局影响）.
final firstActionStateProvider = FutureProvider<FirstActionState?>((ref) {
  final repository = ref.watch(firstActionRepositoryProvider);
  return repository.fetchState();
});
