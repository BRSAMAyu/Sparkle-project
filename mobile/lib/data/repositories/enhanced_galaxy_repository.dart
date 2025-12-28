import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/core/services/retry_strategy.dart';
import 'package:sparkle/core/services/smart_cache.dart';
import 'package:sparkle/data/models/galaxy_model.dart';
import 'package:sparkle/data/models/knowledge_detail_model.dart';

/// 增强的Galaxy仓库Provider
final enhancedGalaxyRepositoryProvider = Provider<EnhancedGalaxyRepository>((ref) {
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

  final SmartCache<String, KnowledgeDetailResponse> _detailCache = SmartCache(
    
  );

  // 断路器
  final CircuitBreakerRetryStrategy _circuitBreaker = CircuitBreakerRetryStrategy(
    failureThreshold: 3,
  );

  // 重试配置
  static const RetryConfig _defaultRetryConfig = RetryConfig(
    
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
          final response = await _apiClient.get(
            ApiEndpoints.galaxyGraph,
            queryParameters: {'zoom_level': zoomLevel},
          );
          return GalaxyGraphResponse.fromJson(response.data);
        },
        onRetry: (attempt, error, delay) {
          debugPrint('EnhancedGalaxyRepository: Retry attempt $attempt for getGraph');
        },
      );

      // 缓存结果
      _graphCache.set(cacheKey, response);

      return NetworkResult.success(response);
    } on CircuitBreakerOpenException catch (e) {
      // 断路器打开，尝试返回缓存
      final cached = _graphCache.get(cacheKey);
      if (cached != null) {
        debugPrint('EnhancedGalaxyRepository: Circuit breaker open, returning stale cache');
        return NetworkResult.success(cached, isFromCache: true);
      }
      return NetworkResult.failure(GalaxyError.circuitBreakerOpen());
    } on DioException catch (e) {
      // 网络错误，尝试返回缓存
      final cached = _graphCache.get(cacheKey);
      if (cached != null) {
        debugPrint('EnhancedGalaxyRepository: Network error, returning stale cache');
        return NetworkResult.success(cached, isFromCache: true);
      }
      return NetworkResult.failure(GalaxyError.network(e));
    } catch (e) {
      return NetworkResult.failure(GalaxyError.unknown(e.toString()));
    }
  }

  /// 激活节点
  Future<NetworkResult<void>> sparkNode(String id) async {
    if (DemoDataService.isDemoMode) {
      return NetworkResult.success(null);
    }

    try {
      await RetryStrategy.executeWithRetry(
        () => _apiClient.post(ApiEndpoints.sparkNode(id)),
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
  Future<NetworkResult<KnowledgeDetailResponse>> getNodeDetail(String nodeId) async {
    if (DemoDataService.isDemoMode) {
      return NetworkResult.success(DemoDataService().getDemoNodeDetail(nodeId));
    }

    // 检查缓存
    final cached = _detailCache.get(nodeId);
    if (cached != null) {
      return NetworkResult.success(cached, isFromCache: true);
    }

    try {
      final response = await RetryStrategy.executeWithRetry(
        () async {
          final response = await _apiClient.get(ApiEndpoints.galaxyNodeDetail(nodeId));
          return KnowledgeDetailResponse.fromJson(response.data);
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
      final response = await RetryStrategy.executeWithRetry(
        () async {
          final response = await _apiClient.post(ApiEndpoints.galaxyPredictNext);
          if (response.data == null) return null;
          return KnowledgeDetailResponse.fromJson(response.data);
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
  Future<NetworkResult<List<GalaxySearchResult>>> searchNodes(String query) async {
    if (DemoDataService.isDemoMode) {
      return NetworkResult.success([]);
    }

    try {
      final response = await RetryStrategy.executeWithRetry(
        () async {
          final response = await _apiClient.post(
            ApiEndpoints.galaxySearch,
            data: {'query': query},
          );
          return GalaxySearchResponse.fromJson(response.data).results;
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
        () => _apiClient.post(ApiEndpoints.galaxyNodeFavorite(nodeId)),
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
        () => _apiClient.post(
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
  Stream<SSEEvent> getGalaxyEventsStream() {
    if (DemoDataService.isDemoMode) {
      return const Stream.empty();
    }
    return _apiClient.getStream(ApiEndpoints.galaxyEvents);
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
    String message;
    switch (e.type) {
      case DioExceptionType.connectionTimeout:
        message = '连接超时，请检查网络';
      case DioExceptionType.receiveTimeout:
        message = '服务器响应超时';
      case DioExceptionType.connectionError:
        message = '网络连接失败';
      default:
        message = e.response?.data?['detail'] ?? '网络请求失败';
    }
    return GalaxyError._(
      type: GalaxyErrorType.network,
      message: message,
      originalError: e,
    );
  }

  factory GalaxyError.circuitBreakerOpen() => GalaxyError._(
        type: GalaxyErrorType.circuitBreakerOpen,
        message: '服务暂时不可用，请稍后重试',
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
    switch (type) {
      case GalaxyErrorType.network:
        return message;
      case GalaxyErrorType.circuitBreakerOpen:
        return '服务暂时不可用，请稍后重试';
      case GalaxyErrorType.unknown:
        return '发生未知错误';
    }
  }

  @override
  String toString() => 'GalaxyError[$type]: $message';
}

enum GalaxyErrorType {
  network,
  circuitBreakerOpen,
  unknown,
}
