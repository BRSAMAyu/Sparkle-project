import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
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
        fallbackMessage: '这次推演没有成功生成，你可以稍后再试。',
      );
    } catch (_) {
      throw const TheaterRepositoryException(
        message: '这次推演没有成功生成，你可以稍后再试。',
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
        fallbackMessage: '这次假设推演没有成功生成，你可以稍后再试。',
      );
    } catch (_) {
      throw const TheaterRepositoryException(
        message: '这次假设推演没有成功生成，你可以稍后再试。',
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
        fallbackMessage: '保存推演快照失败，你可以稍后再试。',
      );
    } catch (_) {
      throw const TheaterRepositoryException(
        message: '保存推演快照失败，你可以稍后再试。',
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
        fallbackMessage: '采纳这条推演路径失败了，你可以稍后再试。',
      );
    } catch (_) {
      throw const TheaterRepositoryException(
        message: '采纳这条推演路径失败了，你可以稍后再试。',
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
        fallbackMessage: '读取这次推演失败了，你可以稍后再试。',
      );
    } catch (_) {
      throw const TheaterRepositoryException(
        message: '读取这次推演失败了，你可以稍后再试。',
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
        fallbackMessage: '记录推演结果失败，你可以稍后再试。',
      );
    } catch (_) {
      throw const TheaterRepositoryException(
        message: '记录推演结果失败，你可以稍后再试。',
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
        fallbackMessage: '读取推演准确度失败，你可以稍后再试。',
      );
    } catch (_) {
      throw const TheaterRepositoryException(
        message: '读取推演准确度失败，你可以稍后再试。',
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
      throw TheaterRepositoryException.fromDio(
        e,
        fallbackMessage: '读取推演校准概览失败，你可以稍后再试。',
      );
    } catch (_) {
      throw const TheaterRepositoryException(
        message: '读取推演校准概览失败，你可以稍后再试。',
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
        fallbackMessage: '将节点同步到知识星图失败，你可以稍后再试。',
      );
    } catch (_) {
      throw const TheaterRepositoryException(
        message: '将节点同步到知识星图失败，你可以稍后再试。',
      );
    }
  }
}
