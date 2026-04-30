import 'package:dio/dio.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/error_book/data/models/error_record.dart';
import 'package:sparkle/features/error_book/data/models/error_semantic_summary.dart';
import 'package:sparkle/shared/entities/cognitive_analysis.dart';
/// 错题档案 Repository
///
/// 职责：封装所有错题相关的 API 调用
/// 设计原则：
/// - 单一数据源：所有网络请求从这里发起
/// - 异常统一处理：转换 HTTP 异常为业务异常
/// - 可测试性：通过依赖注入 Dio 实例便于 mock
class ErrorBookRepository {
  ErrorBookRepository(this._dio);
  final Dio _dio;
  static const String _basePath = '/errors';

  /// 创建错题
  ///
  /// POST /errors
  /// 请求体：
  /// {
  ///   "question_text": "题目内容",
  ///   "user_answer": "错误答案",
  ///   "correct_answer": "正确答案",
  ///   "subject": "math",
  ///   "chapter": "可选章节"
  /// }
  Future<ErrorRecord> createError({
    required String questionText,
    required String subject,
    String? userAnswer,
    String? correctAnswer,
    String? chapter,
    String? questionImageUrl,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        _basePath,
        data: {
          'question_text': questionText,
          'subject': subject,
          if (userAnswer != null && userAnswer.isNotEmpty)
            'user_answer': userAnswer,
          if (correctAnswer != null && correctAnswer.isNotEmpty)
            'correct_answer': correctAnswer,
          if (chapter != null) 'chapter': chapter,
          if (questionImageUrl != null) 'question_image_url': questionImageUrl,
        },
      );

      return ErrorRecord.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw _handleError(e, zh: '创建错题失败', en: 'Failed to create error record');
    }
  }

  /// 获取错题列表
  ///
  /// GET /errors?subject=math&page=1&page_size=20
  /// 支持的查询参数：
  /// - subject: 科目筛选
  /// - chapter: 章节筛选
  /// - mastery_min/max: 掌握度范围
  /// - need_review: 只看需要复习的
  /// - keyword: 题目关键词搜索
  Future<ErrorListResponse> getErrors({
    String? subject,
    String? chapter,
    String? nodeId,
    bool? needReview,
    String? keyword,
    double? masteryMin,
    double? masteryMax,
    CognitiveDimension? cognitiveDimension,
    int page = 1,
    int pageSize = 20,
  }) async {
    try {
      final queryParams = <String, dynamic>{
        'page': page,
        'page_size': pageSize,
        if (subject != null) 'subject': subject,
        if (chapter != null) 'chapter': chapter,
        if (nodeId != null) 'node_id': nodeId,
        if (needReview != null) 'need_review': needReview,
        if (keyword != null) 'keyword': keyword,
        if (masteryMin != null) 'mastery_min': masteryMin,
        if (masteryMax != null) 'mastery_max': masteryMax,
        if (cognitiveDimension != null)
          'cognitive_dimension': cognitiveDimension.code,
      };

      final response = await _dio.get<Map<String, dynamic>>(
        _basePath,
        queryParameters: queryParams,
      );

      return ErrorListResponse.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw _handleError(e, zh: '获取错题列表失败', en: 'Failed to get error list');
    }
  }

  /// 获取错题详情
  ///
  /// GET /errors/{error_id}
  /// 返回包含 AI 分析和关联知识点的完整信息
  Future<ErrorRecord> getError(String errorId) async {
    try {
      final response =
          await _dio.get<Map<String, dynamic>>('$_basePath/$errorId');
      return ErrorRecord.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw _handleError(e, zh: '获取错题详情失败', en: 'Failed to get error details');
    }
  }

  /// 更新错题
  ///
  /// PATCH /errors/{error_id}
  /// 支持部分更新
  Future<ErrorRecord> updateError(
    String errorId, {
    String? questionText,
    String? userAnswer,
    String? correctAnswer,
    String? subject,
    String? chapter,
    String? questionImageUrl,
  }) async {
    try {
      final data = <String, dynamic>{
        if (questionText != null) 'question_text': questionText,
        if (userAnswer != null) 'user_answer': userAnswer,
        if (correctAnswer != null) 'correct_answer': correctAnswer,
        if (subject != null) 'subject': subject,
        if (chapter != null) 'chapter': chapter,
        if (questionImageUrl != null) 'question_image_url': questionImageUrl,
      };

      final response = await _dio.patch<Map<String, dynamic>>(
        '$_basePath/$errorId',
        data: data,
      );

      return ErrorRecord.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw _handleError(e, zh: '更新错题失败', en: 'Failed to update error record');
    }
  }

  /// 删除错题
  ///
  /// DELETE /errors/{error_id}
  /// 软删除，数据库中标记为已删除但不物理删除
  Future<void> deleteError(String errorId) async {
    try {
      await _dio.delete<void>('$_basePath/$errorId');
    } on DioException catch (e) {
      throw _handleError(e, zh: '删除错题失败', en: 'Failed to delete error record');
    }
  }

  /// 重新分析错题
  ///
  /// POST /errors/{error_id}/analyze
  /// AI 分析是异步的，立即返回确认，实际分析在后台执行
  Future<void> reAnalyzeError(String errorId) async {
    try {
      await _dio.post<void>('$_basePath/$errorId/analyze');
    } on DioException catch (e) {
      throw _handleError(e, zh: '重新分析错题失败', en: 'Failed to re-analyze error');
    }
  }

  /// 提交复习记录
  ///
  /// POST /errors/review
  /// 请求体：
  /// {
  ///   "error_id": "uuid",
  ///   "performance": "remembered",  // remembered/fuzzy/forgotten
  ///   "time_spent_seconds": 120,
  ///   "review_type": "active"
  /// }
  ///
  /// 返回更新后的错题（包含新的掌握度和下次复习时间）
  Future<ErrorRecord> submitReview({
    required String errorId,
    required String performance,
    int? timeSpentSeconds,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '$_basePath/$errorId/review',
        data: {
          'performance': performance,
          if (timeSpentSeconds != null) 'time_spent_seconds': timeSpentSeconds,
        },
      );

      return ErrorRecord.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw _handleError(e, zh: '提交复习记录失败', en: 'Failed to submit review record');
    }
  }

  /// 获取今日待复习列表
  ///
  /// GET /errors/today/review
  /// 返回所有 next_review_at <= 现在 的错题
  Future<ErrorListResponse> getTodayReviewList({
    int page = 1,
    int pageSize = 20,
  }) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '$_basePath/today-review',
        queryParameters: {
          'page': page,
          'page_size': pageSize,
        },
      );

      return ErrorListResponse.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw _handleError(e, zh: '获取今日待复习列表失败', en: 'Failed to get today\'s review list');
    }
  }

  /// 获取统计数据
  ///
  /// GET /errors/stats
  /// 返回：
  /// - 总错题数
  /// - 已掌握数（mastery > 0.8）
  /// - 今日需复习数
  /// - 连续复习天数
  /// - 各科目分布
  Future<ReviewStats> getStats() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>('$_basePath/stats');
      return ReviewStats.fromJson(response.data ?? <String, dynamic>{});
    } on DioException catch (e) {
      throw _handleError(e, zh: '获取统计数据失败', en: 'Failed to get statistics');
    }
  }

  /// 获取错题语义摘要
  ///
  /// GET /errors/{error_id}/semantic
  Future<ErrorSemanticSummary> getSemanticSummary(String errorId) async {
    try {
      final response =
          await _dio.get<Map<String, dynamic>>('$_basePath/$errorId/semantic');
      return ErrorSemanticSummary.fromJson(
        response.data ?? <String, dynamic>{},
      );
    } on DioException catch (e) {
      throw _handleError(e, zh: '获取语义摘要失败', en: 'Failed to get semantic summary');
    }
  }

  /// 统一错误处理
  ///
  /// 将 HTTP 异常转换为用户友好的错误消息
  Exception _handleError(DioException e, {required String zh, required String en}) {
    final isZh = I18nService.instance.isChinese;
    final defaultMessage = isZh ? zh : en;
    if (e.response?.statusCode == 404) {
      return Exception(isZh ? '错题不存在或已删除' : 'Error not found or deleted');
    } else if (e.response?.statusCode == 401) {
      return Exception(isZh ? '未登录或登录已过期' : 'Not logged in or session expired');
    } else if (e.response?.statusCode == 400) {
      final data = e.response?.data;
      final errorDetail =
          data is Map<String, dynamic> ? data['detail'] as String? : null;
      return Exception(errorDetail ?? (isZh ? '请求参数错误' : 'Invalid request parameters'));
    } else if (e.type == DioExceptionType.connectionTimeout ||
        e.type == DioExceptionType.receiveTimeout) {
      return Exception(isZh ? '网络超时，请检查网络连接' : 'Network timeout, please check your connection');
    } else if (e.type == DioExceptionType.unknown) {
      return Exception(isZh ? '网络错误，请检查网络连接' : 'Network error, please check your connection');
    }

    return Exception(defaultMessage);
  }
}
