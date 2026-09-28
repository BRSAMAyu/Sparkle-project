import 'package:dio/dio.dart';
import 'package:sparkle/features/learning/data/learning_journey_models.dart';

/// V4-U10 · 旅程 Repository —— /learning-journey 契约的唯一移动端出口。
///
/// 职责（对齐 error_book_repository 纪律）：单一数据源、异常统一转业务异常、
/// Dio 注入可测。**不做**本地答案缓存——检验判分面永远走网络权威，不落盘。
class LearningJourneyRepository {
  LearningJourneyRepository(this._dio);

  final Dio _dio;

  static const String _basePath = '/learning-journey/tasks';

  /// GET /learning-journey/tasks/{taskId}
  Future<LearningJourneyView> getJourney({
    required String goalTaskId,
  }) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>('$_basePath/$goalTaskId');
      final body = response.data ?? const <String, dynamic>{};
      return LearningJourneyView.fromJson(
        body['view'] as Map<String, dynamic>? ?? const <String, dynamic>{},
        warnings: (body['warnings'] as List<dynamic>? ?? const [])
            .whereType<String>()
            .toList(growable: false),
      );
    } on DioException catch (error) {
      throw _fromDio(error, 'learningJourneyLoadFailed');
    }
  }

  /// POST /learning-journey/tasks/{taskId}/check/enter
  /// 用户显式选择「检验」；证据不支持 → holdReason 非空，不出题。
  Future<CheckEnterResult> enterCheck({required String goalTaskId}) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>('$_basePath/$goalTaskId/check/enter');
      final view = response.data?['view'] as Map<String, dynamic>? ?? const <String, dynamic>{};
      return CheckEnterResult(
        available: view['check_available'] as bool? ?? false,
        question: LearningCheckQuestion.sanitize(view),
        holdReason: view['hold_reason'] as String?,
      );
    } on DioException catch (error) {
      throw _fromDio(error, 'learningCheckEnterFailed');
    }
  }

  /// POST /learning-journey/tasks/{taskId}/check/submit
  /// 判分面（零答案材料——答案留在服务端 guide_json 权威）。
  Future<LearningCheckVerdict> submitCheck({
    required String goalTaskId,
    required String answer,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '$_basePath/$goalTaskId/check/submit',
        data: <String, String>{'answer': answer},
      );
      final view = response.data?['view'] as Map<String, dynamic>? ?? const <String, dynamic>{};
      return LearningCheckVerdict.fromJson(view);
    } on DioException catch (error) {
      throw _fromDio(error, 'learningCheckSubmitFailed');
    }
  }

  LearningJourneyRepositoryException _fromDio(DioException error, String fallback) {
    final status = error.response?.statusCode;
    if (status == 404) {
      return const LearningJourneyRepositoryException('learningJourneyTargetMissing', 404);
    }
    return LearningJourneyRepositoryException(fallback, status);
  }
}

/// 检验入口结果（放行出题 / 类型化暂缓）。
class CheckEnterResult {
  const CheckEnterResult({
    required this.available,
    required this.question,
    this.holdReason,
  });

  final bool available;
  final LearningCheckQuestion question;
  final String? holdReason;
}

class LearningJourneyRepositoryException implements Exception {
  const LearningJourneyRepositoryException(this.message, this.statusCode);

  final String message;
  final int? statusCode;

  @override
  String toString() => 'LearningJourneyRepositoryException($statusCode, $message)';
}
