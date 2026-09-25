import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/features/journey/data/models/hybrid_journey_models.dart';

final hybridJourneyRepositoryProvider = Provider<HybridJourneyRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return HybridJourneyRepository(apiClient);
});

/// J-06 · Hybrid 旗舰旅程仓库：消费 /journey/hybrid/*（网关纯代理）。
///
/// 诚实抛错、无 mock fallback（J-05 同纪律）：422 判断/材料缺失、409 状态、
/// 503 起草/check 失败都映射为 [HybridJourneyException]（结构化 error 码），
/// 不把失败吞成空态，更不假装成功。
class HybridJourneyRepository {
  HybridJourneyRepository(this._apiClient);

  final ApiClient _apiClient;

  /// 启动旅程：Agent prep（真实材料检索）→ 轮到用户判断。
  Future<HybridJourneyPayload> start({
    required String idempotencyKey,
    String? taskId,
  }) async {
    try {
      final response = await _apiClient.post<dynamic>(
        ApiEndpoints.journeyHybridStart,
        data: <String, dynamic>{
          'idempotency_key': idempotencyKey,
          if (taskId != null && taskId.isNotEmpty) 'task_id': taskId,
        },
      );
      return HybridJourneyPayload.fromJson(
        ApiResponseParser.unwrapMap(response.data, action: 'startHybridJourney'),
      );
    } on DioException catch (e) {
      throw _toException(e, fallback: 'Failed to start hybrid journey');
    }
  }

  /// 判断段提交（AI 不代决：selectedRefs 为空时服务端 422 judgment_required）。
  Future<HybridJourneyPayload> submitJudgment({
    required String runId,
    required List<String> selectedRefs,
    required String idempotencyKey,
    String? focusNote,
  }) async {
    try {
      final response = await _apiClient.post<dynamic>(
        ApiEndpoints.journeyHybridJudgment(runId),
        data: <String, dynamic>{
          'selected_refs': selectedRefs,
          'idempotency_key': idempotencyKey,
          if (focusNote != null && focusNote.trim().isNotEmpty)
            'focus_note': focusNote.trim(),
        },
      );
      return HybridJourneyPayload.fromJson(
        ApiResponseParser.unwrapMap(response.data, action: 'submitHybridJudgment'),
      );
    } on DioException catch (e) {
      throw _toException(e, fallback: 'Failed to submit judgment');
    }
  }

  /// 确认交付（幂等）：任务完成 + outcome 记录 + run SUCCEEDED。
  Future<HybridJourneyPayload> confirmOutcome({
    required String runId,
    required String idempotencyKey,
    String? note,
  }) async {
    try {
      final response = await _apiClient.post<dynamic>(
        ApiEndpoints.journeyHybridOutcomeConfirm(runId),
        data: <String, dynamic>{
          'idempotency_key': idempotencyKey,
          if (note != null && note.trim().isNotEmpty) 'note': note.trim(),
        },
      );
      return HybridJourneyPayload.fromJson(
        ApiResponseParser.unwrapMap(response.data, action: 'confirmHybridOutcome'),
      );
    } on DioException catch (e) {
      throw _toException(e, fallback: 'Failed to confirm outcome');
    }
  }

  /// 旅程状态读面（重开 App 的持久化回放）。
  Future<HybridJourneyPayload?> fetchState({required String runId}) async {
    try {
      final response = await _apiClient.get<dynamic>(
        ApiEndpoints.journeyHybridState(runId),
      );
      final data = ApiResponseParser.unwrapMap(
        response.data,
        action: 'fetchHybridJourneyState',
      );
      return HybridJourneyPayload.fromJson(data);
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) return null;
      throw _toException(e, fallback: 'Failed to fetch hybrid journey state');
    }
  }

  HybridJourneyException _toException(
    DioException e, {
    required String fallback,
  }) {
    final status = e.response?.statusCode;
    final data = e.response?.data;
    final detail = data is Map ? data['detail'] : null;
    final detailMap = detail is Map
        ? Map<String, dynamic>.from(detail)
        : const <String, dynamic>{};
    return HybridJourneyException(
      error:
          (detailMap['error'] ?? (detail is String ? detail : fallback)).toString(),
      message: (detailMap['message'] ?? fallback).toString(),
      retryable: detailMap['retryable'] == true || status == 503,
      statusCode: status,
    );
  }
}

/// 旅程错误（诚实呈现：判断必做/材料缺失/状态冲突/起草失败可重试）。
@immutable
class HybridJourneyException implements Exception {
  const HybridJourneyException({
    required this.error,
    required this.message,
    this.retryable = false,
    this.statusCode,
  });

  final String error;
  final String message;
  final bool retryable;
  final int? statusCode;

  /// 卡魂错误码：判断段没有用户决定（服务端结构性拒绝代决）。
  bool get judgmentRequired => error == 'judgment_required';
  bool get noMaterials => error == 'no_materials';

  @override
  String toString() => 'HybridJourneyException($error): $message';
}
