import 'dart:async';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

/// 重试策略配置
class RetryConfig {
  const RetryConfig({
    this.maxAttempts = 3,
    this.initialDelay = const Duration(milliseconds: 500),
    this.maxDelay = const Duration(seconds: 10),
    this.backoffFactor = 1.5,
    this.retryableErrors = const [
      DioExceptionType.connectionTimeout,
      DioExceptionType.sendTimeout,
      DioExceptionType.receiveTimeout,
      DioExceptionType.connectionError,
    ],
    this.retryableStatusCodes = const [408, 429, 500, 502, 503, 504],
  });

  final int maxAttempts;
  final Duration initialDelay;
  final Duration maxDelay;
  final double backoffFactor;
  final List<DioExceptionType> retryableErrors;
  final List<int> retryableStatusCodes;

  /// 计算第n次重试的延迟
  Duration getDelay(int attempt) {
    if (attempt <= 0) return Duration.zero;

    final delayMs = initialDelay.inMilliseconds * _pow(backoffFactor, attempt - 1);
    return Duration(
      milliseconds: delayMs.toInt().clamp(0, maxDelay.inMilliseconds),
    );
  }

  double _pow(double base, int exponent) {
    var result = 1.0;
    for (var i = 0; i < exponent; i++) {
      result *= base;
    }
    return result;
  }
}

/// 重试策略服务
class RetryStrategy {
  /// 带重试的任务执行
  static Future<T> executeWithRetry<T>(
    Future<T> Function() task, {
    RetryConfig config = const RetryConfig(),
    void Function(int attempt, Object error, Duration nextDelay)? onRetry,
    bool Function(Object error)? shouldRetry,
  }) async {
    var attempt = 1;

    while (true) {
      try {
        return await task();
      } catch (error) {
        // 检查是否应该重试
        if (attempt >= config.maxAttempts) {
          debugPrint('RetryStrategy: Max attempts ($attempt) reached, giving up');
          rethrow;
        }

        final canRetry = shouldRetry?.call(error) ?? _defaultShouldRetry(error, config);
        if (!canRetry) {
          debugPrint('RetryStrategy: Error not retryable: $error');
          rethrow;
        }

        final delay = config.getDelay(attempt);
        debugPrint(
          'RetryStrategy: Attempt $attempt failed, retrying in ${delay.inMilliseconds}ms. '
          'Error: $error',
        );

        onRetry?.call(attempt, error, delay);

        await Future<void>.delayed(delay);
        attempt++;
      }
    }
  }

  /// 默认的重试判断逻辑
  static bool _defaultShouldRetry(Object error, RetryConfig config) {
    if (error is DioException) {
      // 检查错误类型
      if (config.retryableErrors.contains(error.type)) {
        return true;
      }

      // 检查HTTP状态码
      final statusCode = error.response?.statusCode;
      if (statusCode != null && config.retryableStatusCodes.contains(statusCode)) {
        return true;
      }

      return false;
    }

    // 网络错误
    if (error is SocketException) {
      return true;
    }

    // 超时错误
    if (error is TimeoutException) {
      return true;
    }

    return false;
  }
}

/// 带断路器的重试策略
class CircuitBreakerRetryStrategy {
  CircuitBreakerRetryStrategy({
    this.failureThreshold = 5,
    this.resetTimeout = const Duration(seconds: 30),
    this.halfOpenMaxAttempts = 3,
  });

  final int failureThreshold;
  final Duration resetTimeout;
  final int halfOpenMaxAttempts;

  CircuitState _state = CircuitState.closed;
  int _failureCount = 0;
  int _halfOpenAttempts = 0;
  DateTime? _openedAt;

  CircuitState get state => _state;
  int get failureCount => _failureCount;

  /// 执行带断路器保护的请求
  Future<T> execute<T>(
    Future<T> Function() task, {
    RetryConfig config = const RetryConfig(),
    void Function(int attempt, Object error, Duration nextDelay)? onRetry,
  }) async {
    // 检查断路器状态
    if (_state == CircuitState.open) {
      if (_shouldAttemptReset()) {
        _state = CircuitState.halfOpen;
        _halfOpenAttempts = 0;
      } else {
        throw CircuitBreakerOpenException(
          'Circuit breaker is open. Try again after ${resetTimeout.inSeconds}s',
        );
      }
    }

    try {
      final result = await RetryStrategy.executeWithRetry(
        task,
        config: config,
        onRetry: onRetry,
      );

      // 成功时重置计数
      _onSuccess();
      return result;
    } catch (e) {
      _onFailure();
      rethrow;
    }
  }

  bool _shouldAttemptReset() {
    if (_openedAt == null) return true;
    return DateTime.now().difference(_openedAt!) >= resetTimeout;
  }

  void _onSuccess() {
    if (_state == CircuitState.halfOpen) {
      _halfOpenAttempts++;
      if (_halfOpenAttempts >= halfOpenMaxAttempts) {
        // 多次成功，关闭断路器
        _state = CircuitState.closed;
        _failureCount = 0;
      }
    } else {
      _failureCount = 0;
    }
  }

  void _onFailure() {
    _failureCount++;
    _halfOpenAttempts = 0;

    if (_failureCount >= failureThreshold) {
      _state = CircuitState.open;
      _openedAt = DateTime.now();
      debugPrint('CircuitBreaker: Opened due to $failureThreshold consecutive failures');
    }
  }

  /// 手动重置断路器
  void reset() {
    _state = CircuitState.closed;
    _failureCount = 0;
    _halfOpenAttempts = 0;
    _openedAt = null;
  }
}

/// 断路器状态
enum CircuitState {
  closed,   // 正常运行
  open,     // 断开，拒绝请求
  halfOpen, // 半开，尝试恢复
}

/// 断路器打开异常
class CircuitBreakerOpenException implements Exception {
  CircuitBreakerOpenException(this.message);
  final String message;

  @override
  String toString() => 'CircuitBreakerOpenException: $message';
}

/// 网络操作结果包装
class NetworkResult<T> {
  const NetworkResult._({
    this.data,
    this.error,
    this.isFromCache = false,
  });

  factory NetworkResult.success(T data, {bool isFromCache = false}) =>
      NetworkResult._(data: data, isFromCache: isFromCache);

  factory NetworkResult.failure(Object error) =>
      NetworkResult._(error: error);

  final T? data;
  final Object? error;
  final bool isFromCache;

  bool get isSuccess => error == null && data != null;
  bool get isFailure => !isSuccess;

  T? get valueOrNull => data;
  T get value {
    if (data != null) return data as T;
    throw error ?? StateError('No data available');
  }

  R fold<R>({
    required R Function(T data, bool isFromCache) onSuccess,
    required R Function(Object error) onFailure,
  }) {
    if (isSuccess) {
      return onSuccess(data as T, isFromCache);
    }
    return onFailure(error!);
  }
}
