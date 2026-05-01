import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/theater/data/models/theater_models.dart';

final theaterRepositoryProvider = Provider<TheaterRepository>(
  (ref) => TheaterRepository(ref.watch(apiClientProvider)),
);

class TheaterRepositoryException implements Exception {
  const TheaterRepositoryException({
    required this.message,
    this.errorCode,
    this.statusCode,
  });

  factory TheaterRepositoryException.fromDio(
    DioException error, {
    required String fallbackMessage,
  }) {
    final data = error.response?.data;
    Map<String, dynamic>? payload;
    if (data is Map<String, dynamic>) {
      payload = data;
    } else if (data is Map) {
      payload = data.map(
        (key, value) => MapEntry(key.toString(), value),
      );
    }
    final detail = payload?['detail'];
    Map<String, dynamic>? detailMap;
    if (detail is Map<String, dynamic>) {
      detailMap = detail;
    } else if (detail is Map) {
      detailMap = detail.map(
        (key, value) => MapEntry(key.toString(), value),
      );
    }
    final rawMessage = payload?['message']?.toString().trim();
    final message =
        (rawMessage?.isNotEmpty ?? false) ? rawMessage! : fallbackMessage;
    return TheaterRepositoryException(
      message: message,
      errorCode: payload?['error_code']?.toString() ??
          detailMap?['error_code']?.toString(),
      statusCode: error.response?.statusCode,
    );
  }

  final String message;
  final String? errorCode;
  final int? statusCode;

  bool get isTimeout => statusCode == 504 || errorCode == 'THEATER_TIMEOUT';

  @override
  String toString() => message;
}

class TheaterRepository {
  TheaterRepository(this._apiClient);

  final ApiClient _apiClient;

  static String _err(String zh, String en) =>
      I18nService.instance.isChinese ? zh : en;

  Future<TheaterPrediction> generatePrediction({
    required String topic,
    String? targetNodeId,
    int horizonDays = 14,
    String? simulationSessionId,
  }) async {
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.theaterGeneratePrediction,
        data: {
          'topic': topic,
          if (targetNodeId != null && targetNodeId.isNotEmpty)
            'target_node_id': targetNodeId,
          'horizon_days': horizonDays,
          if (simulationSessionId != null && simulationSessionId.isNotEmpty)
            'simulation_session_id': simulationSessionId,
        },
      );
      return TheaterPrediction.fromJson(response.data ?? const {});
    } on DioException catch (e) {
      throw TheaterRepositoryException.fromDio(
        e,
        fallbackMessage: _err('这次推演没有成功生成，你可以稍后再试。', 'Prediction generation failed. Please try again later.'),
      );
    } catch (_) {
      throw TheaterRepositoryException(
        message: _err('这次推演没有成功生成，你可以稍后再试。', 'Prediction generation failed. Please try again later.'),
      );
    }
  }

  Future<TheaterWhatIfResult> simulateWhatIf({
    required String predictionId,
    required String routeId,
    required List<String> skipNodeIds,
  }) async {
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.theaterWhatIf,
        data: {
          'prediction_id': predictionId,
          'route_id': routeId,
          if (skipNodeIds.isNotEmpty) 'skip_node_id': skipNodeIds.first,
          'skip_node_ids': skipNodeIds,
        },
      );
      return TheaterWhatIfResult.fromJson(response.data ?? const {});
    } on DioException catch (e) {
      throw TheaterRepositoryException.fromDio(
        e,
        fallbackMessage: _err('这次假设推演没有成功生成，你可以稍后再试。', 'What-if simulation failed. Please try again later.'),
      );
    } catch (_) {
      throw TheaterRepositoryException(
        message: _err('这次假设推演没有成功生成，你可以稍后再试。', 'What-if simulation failed. Please try again later.'),
      );
    }
  }

  Future<TheaterSnapshot> saveSnapshot({
    required String predictionId,
    required String routeId,
    String? note,
  }) async {
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.theaterSnapshots,
        data: {
          'prediction_id': predictionId,
          'route_id': routeId,
          if (note != null && note.isNotEmpty) 'note': note,
        },
      );
      return TheaterSnapshot.fromJson(response.data ?? const {});
    } on DioException catch (e) {
      throw TheaterRepositoryException.fromDio(
        e,
        fallbackMessage: _err('保存推演快照失败，你可以稍后再试。', 'Failed to save snapshot. Please try again later.'),
      );
    } catch (_) {
      throw TheaterRepositoryException(
        message: _err('保存推演快照失败，你可以稍后再试。', 'Failed to save snapshot. Please try again later.'),
      );
    }
  }

  Future<TheaterAdoptionResult> adoptRoute({
    required String predictionId,
    required String routeId,
    String? sourceChatSessionId,
  }) async {
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.theaterAdopt(predictionId),
        data: {
          'prediction_id': predictionId,
          'route_id': routeId,
          if (sourceChatSessionId != null && sourceChatSessionId.isNotEmpty)
            'source_chat_session_id': sourceChatSessionId,
        },
      );
      return TheaterAdoptionResult.fromJson(response.data ?? const {});
    } on DioException catch (e) {
      throw TheaterRepositoryException.fromDio(
        e,
        fallbackMessage: _err('采纳这条推演路径失败了，你可以稍后再试。', 'Failed to adopt this route. Please try again later.'),
      );
    } catch (_) {
      throw TheaterRepositoryException(
        message: _err('采纳这条推演路径失败了，你可以稍后再试。', 'Failed to adopt this route. Please try again later.'),
      );
    }
  }

  Future<TheaterPrediction> getPredictionById(String predictionId) async {
    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.theaterPrediction(predictionId),
      );
      return TheaterPrediction.fromJson(response.data ?? const {});
    } on DioException catch (e) {
      throw TheaterRepositoryException.fromDio(
        e,
        fallbackMessage: _err('读取这次推演失败了，你可以稍后再试。', 'Failed to load prediction. Please try again later.'),
      );
    } catch (_) {
      throw TheaterRepositoryException(
        message: _err('读取这次推演失败了，你可以稍后再试。', 'Failed to load prediction. Please try again later.'),
      );
    }
  }

  Future<TheaterAccuracySummary> recordActuals({
    required String predictionId,
    double? actualCompletionRate,
    double? actualMastery,
  }) async {
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.theaterActuals(predictionId),
        data: {
          if (actualCompletionRate != null)
            'actual_completion_rate': actualCompletionRate,
          if (actualMastery != null) 'actual_mastery': actualMastery,
        },
      );
      return TheaterAccuracySummary.fromJson(response.data ?? const {});
    } on DioException catch (e) {
      throw TheaterRepositoryException.fromDio(
        e,
        fallbackMessage: _err('记录推演结果失败，你可以稍后再试。', 'Failed to record results. Please try again later.'),
      );
    } catch (_) {
      throw TheaterRepositoryException(
        message: _err('记录推演结果失败，你可以稍后再试。', 'Failed to record results. Please try again later.'),
      );
    }
  }

  Future<TheaterAccuracySummary?> getAccuracy(String predictionId) async {
    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.theaterAccuracy(predictionId),
      );
      final data = response.data;
      if (data == null || data.isEmpty) {
        return null;
      }
      return TheaterAccuracySummary.fromJson(data);
    } on DioException catch (e) {
      throw TheaterRepositoryException.fromDio(
        e,
        fallbackMessage: _err('读取推演准确度失败，你可以稍后再试。', 'Failed to load accuracy. Please try again later.'),
      );
    } catch (_) {
      throw TheaterRepositoryException(
        message: _err('读取推演准确度失败，你可以稍后再试。', 'Failed to load accuracy. Please try again later.'),
      );
    }
  }

  Future<TheaterAccuracyOverview> getAccuracyOverview() async {
    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.theaterAccuracyOverview,
      );
      return TheaterAccuracyOverview.fromJson(response.data ?? const {});
    } on DioException catch (e) {
      final statusCode = e.response?.statusCode;
      if (statusCode == 404 || statusCode == 405) {
        return const TheaterAccuracyOverview(
          sampleCount: 0,
          avgAccuracyScore: 0,
          completionBiasMean: 0,
          masteryBiasMean: 0,
          completionMae: 0,
          masteryMae: 0,
          confidenceScore: 0,
          dataStatus: 'cold_start',
          trend: 'insufficient_data',
        );
      }
      throw TheaterRepositoryException.fromDio(
        e,
        fallbackMessage: _err('读取推演校准概览失败，你可以稍后再试。', 'Failed to load calibration overview. Please try again later.'),
      );
    } catch (_) {
      throw TheaterRepositoryException(
        message: _err('读取推演校准概览失败，你可以稍后再试。', 'Failed to load calibration overview. Please try again later.'),
      );
    }
  }

  Future<TheaterNodePromotionResult> promoteNodeToGalaxy({
    required String predictionId,
    required String theaterNodeId,
  }) async {
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.theaterPromoteNode(predictionId),
        data: {
          'theater_node_id': theaterNodeId,
        },
      );
      return TheaterNodePromotionResult.fromJson(response.data ?? const {});
    } on DioException catch (e) {
      throw TheaterRepositoryException.fromDio(
        e,
        fallbackMessage: _err('将节点同步到知识星图失败，你可以稍后再试。', 'Failed to sync node to Galaxy. Please try again later.'),
      );
    } catch (_) {
      throw TheaterRepositoryException(
        message: _err('将节点同步到知识星图失败，你可以稍后再试。', 'Failed to sync node to Galaxy. Please try again later.'),
      );
    }
  }
}
