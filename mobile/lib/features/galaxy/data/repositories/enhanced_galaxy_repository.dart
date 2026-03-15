import 'package:dio/dio.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/retry_strategy.dart';
import 'package:sparkle/core/services/smart_cache.dart';
import 'package:sparkle/features/knowledge/data/models/knowledge_detail_model.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';

/// 增强的Galaxy仓库Provider
final enhancedGalaxyRepositoryProvider =
    Provider<EnhancedGalaxyRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return EnhancedGalaxyRepository(apiClient);
});

/// 增强的Galaxy仓库 - 带重试机制和智能缓存
class EnhancedGalaxyRepository {
  EnhancedGalaxyRepository(this._apiClient);

  final ApiClient _apiClient;

  // 缓存配置
  final SmartCache<String, GalaxyGraphResponse> _graphCache = SmartCache(
    maxSize: 5,
    maxAge: const Duration(minutes: 10),
  );

  final SmartCache<String, KnowledgeDetailResponse> _detailCache = SmartCache();

  // 断路器
  final CircuitBreakerRetryStrategy _circuitBreaker =
      CircuitBreakerRetryStrategy(
    failureThreshold: 3,
  );

  /// 获取星图数据（带重试和缓存）
  Future<NetworkResult<GalaxyGraphResponse>> getGraph({
    double zoomLevel = 1.0,
    bool forceRefresh = false,
  }) async {
    if (DemoDataService.isDemoMode) {
      return NetworkResult.success(DemoDataService().demoGalaxy);
    }

    final cacheKey = 'graph_$zoomLevel';

    // 检查缓存
    if (!forceRefresh) {
      final cached = _graphCache.get(cacheKey);
      if (cached != null) {
        debugPrint('EnhancedGalaxyRepository: Returning cached graph');
        return NetworkResult.success(cached, isFromCache: true);
      }
    }

    try {
      final response = await _circuitBreaker.execute(
        () async {
          final response = await _apiClient.get<Map<String, dynamic>>(
            ApiEndpoints.galaxyGraph,
            queryParameters: {'zoom_level': zoomLevel},
          );
          final payload = ApiResponseParser.unwrapMap(
            response.data,
            action: 'getGalaxyGraph',
          );
          return GalaxyGraphResponse.fromJson(payload);
        },
        onRetry: (attempt, error, delay) {
          debugPrint(
            'EnhancedGalaxyRepository: Retry attempt $attempt for getGraph',
          );
        },
      );

      // 缓存结果
      _graphCache.set(cacheKey, response);

      return NetworkResult.success(response);
    } on CircuitBreakerOpenException {
      // 断路器打开，尝试返回缓存
      final cached = _graphCache.get(cacheKey);
      if (cached != null) {
        debugPrint(
          'EnhancedGalaxyRepository: Circuit breaker open, returning stale cache',
        );
        return NetworkResult.success(cached, isFromCache: true);
      }
      return NetworkResult.failure(GalaxyError.circuitBreakerOpen());
    } on DioException catch (e) {
      // 网络错误，尝试返回缓存
      final cached = _graphCache.get(cacheKey);
      if (cached != null) {
        debugPrint(
          'EnhancedGalaxyRepository: Network error, returning stale cache',
        );
        return NetworkResult.success(cached, isFromCache: true);
      }
      return NetworkResult.failure(GalaxyError.network(e));
    } catch (e) {
      return NetworkResult.failure(GalaxyError.unknown(e.toString()));
    }
  }

  Future<NetworkResult<GalaxyGraphResponse>> getGraphForViewport({
    required Rect viewport,
  }) async {
    if (DemoDataService.isDemoMode) {
      return NetworkResult.success(DemoDataService().demoGalaxy);
    }

    try {
      final response =
          await RetryStrategy.executeWithRetry<GalaxyGraphResponse>(
        () async {
          final response = await _apiClient.post<Map<String, dynamic>>(
            ApiEndpoints.galaxyViewport,
            data: {
              'min_x': viewport.left,
              'max_x': viewport.right,
              'min_y': viewport.top,
              'max_y': viewport.bottom,
            },
          );
          final payload = ApiResponseParser.unwrapMap(
            response.data ?? const <String, dynamic>{},
            action: 'getGalaxyViewport',
          );
          return GalaxyGraphResponse.fromJson(payload);
        },
        config: const RetryConfig(maxAttempts: 2),
      );

      return NetworkResult.success(response);
    } on DioException catch (e) {
      return NetworkResult.failure(GalaxyError.network(e));
    } catch (e) {
      return NetworkResult.failure(GalaxyError.unknown(e.toString()));
    }
  }

  Future<NetworkResult<void>> updateNodePositions(
    Map<String, Offset> positions,
  ) async {
    if (DemoDataService.isDemoMode || positions.isEmpty) {
      return NetworkResult.success(null);
    }

    try {
      await RetryStrategy.executeWithRetry(
        () => _apiClient.post<void>(
          ApiEndpoints.galaxyPositions,
          data: {
            'updates': positions.entries
                .map(
                  (entry) => {
                    'id': entry.key,
                    'x': entry.value.dx,
                    'y': entry.value.dy,
                  },
                )
                .toList(),
          },
        ),
        config: const RetryConfig(maxAttempts: 2),
      );
      return NetworkResult.success(null);
    } on DioException catch (e) {
      return NetworkResult.failure(GalaxyError.network(e));
    } catch (e) {
      return NetworkResult.failure(GalaxyError.unknown(e.toString()));
    }
  }

  Future<NetworkResult<void>> updateNodePosition(
    String nodeId,
    Offset position,
  ) =>
      updateNodePositions(<String, Offset>{nodeId: position});

  /// 激活节点
  Future<NetworkResult<void>> sparkNode(String id) async {
    if (DemoDataService.isDemoMode) {
      return NetworkResult.success(null);
    }

    try {
      await RetryStrategy.executeWithRetry(
        () => _apiClient.post<void>(ApiEndpoints.sparkNode(id)),
      );

      // 清除相关缓存
      _graphCache.clear();

      return NetworkResult.success(null);
    } on DioException catch (e) {
      return NetworkResult.failure(GalaxyError.network(e));
    } catch (e) {
      return NetworkResult.failure(GalaxyError.unknown(e.toString()));
    }
  }

  /// 获取节点详情
  Future<NetworkResult<KnowledgeDetailResponse>> getNodeDetail(
    String nodeId,
  ) async {
    if (DemoDataService.isDemoMode) {
      return NetworkResult.success(DemoDataService().getDemoNodeDetail(nodeId));
    }

    // 检查缓存
    final cached = _detailCache.get(nodeId);
    if (cached != null) {
      return NetworkResult.success(cached, isFromCache: true);
    }

    try {
      final response =
          await RetryStrategy.executeWithRetry<KnowledgeDetailResponse>(
        () async {
          final response = await _apiClient.get<Map<String, dynamic>>(
            ApiEndpoints.galaxyNodeDetail(nodeId),
          );
          final payload = ApiResponseParser.unwrapMap(
            response.data,
            action: 'getGalaxyNodeDetail',
          );
          return KnowledgeDetailResponse.fromJson(payload);
        },
      );

      // 缓存结果
      _detailCache.set(nodeId, response);

      return NetworkResult.success(response);
    } on DioException catch (e) {
      return NetworkResult.failure(GalaxyError.network(e));
    } catch (e) {
      return NetworkResult.failure(GalaxyError.unknown(e.toString()));
    }
  }

  /// 预测下一个节点
  Future<NetworkResult<KnowledgeDetailResponse?>> predictNextNode() async {
    if (DemoDataService.isDemoMode) {
      return NetworkResult.success(null);
    }

    try {
      final response =
          await RetryStrategy.executeWithRetry<KnowledgeDetailResponse?>(
        () async {
          final response = await _apiClient.post<Map<String, dynamic>>(
            ApiEndpoints.galaxyPredictNext,
          );
          if (response.data == null) return null;
          final payload = ApiResponseParser.unwrapMap(
            response.data,
            action: 'predictNextNode',
          );
          return KnowledgeDetailResponse.fromJson(payload);
        },
        config: const RetryConfig(maxAttempts: 2),
      );

      return NetworkResult.success(response);
    } catch (e) {
      // 预测失败不是致命错误
      return NetworkResult.success(null);
    }
  }

  /// 搜索节点
  Future<NetworkResult<List<GalaxySearchResult>>> searchNodes(
    String query,
  ) async {
    if (DemoDataService.isDemoMode) {
      return NetworkResult.success([]);
    }

    try {
      final response =
          await RetryStrategy.executeWithRetry<List<GalaxySearchResult>>(
        () async {
          final response = await _apiClient.post<Map<String, dynamic>>(
            ApiEndpoints.galaxySearch,
            data: {'query': query},
          );
          if (response.data == null) return [];
          final payload = ApiResponseParser.unwrapMap(
            response.data,
            action: 'searchGalaxyNodes',
          );
          return GalaxySearchResponse.fromJson(payload).results;
        },
        config: const RetryConfig(maxAttempts: 2),
      );

      return NetworkResult.success(response);
    } on DioException {
      return NetworkResult.success([]);
    } catch (e) {
      return NetworkResult.success([]);
    }
  }

  /// 切换收藏状态
  Future<NetworkResult<void>> toggleFavorite(String nodeId) async {
    if (DemoDataService.isDemoMode) {
      return NetworkResult.success(null);
    }

    try {
      await RetryStrategy.executeWithRetry(
        () => _apiClient.post<void>(ApiEndpoints.galaxyNodeFavorite(nodeId)),
      );

      // 清除节点详情缓存
      _detailCache.remove(nodeId);

      return NetworkResult.success(null);
    } on DioException catch (e) {
      return NetworkResult.failure(GalaxyError.network(e));
    } catch (e) {
      return NetworkResult.failure(GalaxyError.unknown(e.toString()));
    }
  }

  /// 暂停/恢复衰减
  Future<NetworkResult<void>> pauseDecay(String nodeId, bool pause) async {
    if (DemoDataService.isDemoMode) {
      return NetworkResult.success(null);
    }

    try {
      await RetryStrategy.executeWithRetry(
        () => _apiClient.post<void>(
          ApiEndpoints.galaxyNodeDecayPause(nodeId),
          data: {'pause': pause},
        ),
      );

      return NetworkResult.success(null);
    } on DioException catch (e) {
      return NetworkResult.failure(GalaxyError.network(e));
    } catch (e) {
      return NetworkResult.failure(GalaxyError.unknown(e.toString()));
    }
  }

  /// 获取事件流
  Stream<SSEEvent> getGalaxyEventsStream({String? lastEventId}) {
    if (DemoDataService.isDemoMode) {
      debugPrint('🌌 Demo mode: returning empty galaxy events stream');
      return const Stream.empty();
    }

    debugPrint('🌌 Connecting to galaxy events stream (SSE)...');
    final headers = <String, dynamic>{};
    if (lastEventId != null) {
      headers['Last-Event-ID'] = lastEventId;
    }

    return _apiClient.getStream(
      ApiEndpoints.galaxyEvents,
      headers: headers,
    );
  }

  /// 清除所有缓存
  void clearCache() {
    _graphCache.clear();
    _detailCache.clear();
  }

  /// 获取断路器状态
  CircuitState get circuitBreakerState => _circuitBreaker.state;

  /// 重置断路器
  void resetCircuitBreaker() {
    _circuitBreaker.reset();
  }

  /// 获取缓存统计
  Map<String, CacheStats> get cacheStats => {
        'graph': _graphCache.stats,
        'detail': _detailCache.stats,
      };
}

/// Galaxy错误类型
class GalaxyError implements Exception {
  GalaxyError._({
    required this.type,
    required this.message,
    this.originalError,
  });

  factory GalaxyError.network(DioException e) {
    final l10n = I18nService.instance.l10n;
    String message;
    switch (e.type) {
      case DioExceptionType.connectionTimeout:
        message = l10n.galaxyErrorConnectionTimeout;
      case DioExceptionType.receiveTimeout:
        message = l10n.galaxyErrorResponseTimeout;
      case DioExceptionType.connectionError:
        message = l10n.galaxyErrorConnectionFailed;
      default:
        message = _extractDetailFromResponse(
          e,
          fallback: l10n.galaxyErrorRequestFailed,
        );
    }
    return GalaxyError._(
      type: GalaxyErrorType.network,
      message: message,
      originalError: e,
    );
  }

  factory GalaxyError.circuitBreakerOpen() => GalaxyError._(
        type: GalaxyErrorType.circuitBreakerOpen,
        message:
            I18nService.instance.l10n.galaxyErrorServiceTemporarilyUnavailable,
      );

  factory GalaxyError.unknown(String message) => GalaxyError._(
        type: GalaxyErrorType.unknown,
        message: message,
      );

  final GalaxyErrorType type;
  final String message;
  final Object? originalError;

  /// 是否可重试
  bool get isRetryable => type == GalaxyErrorType.network;

  /// 是否应该显示错误UI
  bool get shouldShowError => type != GalaxyErrorType.unknown;

  /// 获取用户友好的错误消息
  String get userMessage {
    final l10n = I18nService.instance.l10n;
    switch (type) {
      case GalaxyErrorType.network:
        return message;
      case GalaxyErrorType.circuitBreakerOpen:
        return l10n.galaxyErrorServiceTemporarilyUnavailable;
      case GalaxyErrorType.unknown:
        return l10n.galaxyErrorUnknown;
    }
  }

  @override
  String toString() => 'GalaxyError[$type]: $message';

  static String _extractDetailFromResponse(
    DioException exception, {
    required String fallback,
  }) {
    final data = exception.response?.data;
    if (data is Map<String, dynamic>) {
      final detail = data['detail'];
      if (detail is String && detail.isNotEmpty) {
        return detail;
      }
    }
    return fallback;
  }
}

enum GalaxyErrorType {
  network,
  circuitBreakerOpen,
  unknown,
}
