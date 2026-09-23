import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:logger/logger.dart';
import 'package:sparkle/core/constants/api_constants.dart';
import 'package:sparkle/core/network/api_timeouts.dart';
import 'package:sparkle/core/network/http_client_pinning.dart';
import 'package:sparkle/core/network/token_refresh_coordinator.dart';
import 'package:sparkle/core/services/client_observability_service.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/core/services/device_identity_service.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/plan/presentation/providers/active_goal_provider.dart';

final authInterceptorProvider = Provider(AuthInterceptor.new);
final loggingInterceptorProvider = Provider((ref) => LoggingInterceptor());
final retryInterceptorProvider = Provider.family<RetryInterceptor, Dio>(
  (ref, dio) => RetryInterceptor(dio: dio),
);

class RetryInterceptor extends Interceptor {
  RetryInterceptor({
    required this.dio,
    this.maxRetries = 3,
    this.retryableStatuses = const [502, 503, 504],
  });
  final Dio dio;
  final int maxRetries;
  final List<int> retryableStatuses;

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    if (retryableStatuses.contains(err.response?.statusCode) &&
        _shouldRetry(err)) {
      final retries = err.requestOptions.extra['retries'] as int? ?? 0;
      if (retries < maxRetries) {
        err.requestOptions.extra['retries'] = retries + 1;

        // Exponential backoff
        final delay = Duration(milliseconds: 500 * (1 << retries));
        await Future<void>.delayed(delay);

        try {
          final response = await dio.fetch<dynamic>(err.requestOptions);
          return handler.resolve(response);
        } catch (e) {
          // If retry fails, continue to next error handler
        }
      }
    }
    super.onError(err, handler);
  }

  bool _shouldRetry(DioException err) => err.type != DioExceptionType.cancel;
}

class AuthInterceptor extends Interceptor {
  AuthInterceptor(this._ref, {Dio? retryDioForTesting})
      : _retryDio = retryDioForTesting;
  final Ref _ref;

  // AUTH-DEEP B-1：本地 Completer 单飞已移除——刷新决策统一走全局
  // TokenRefreshCoordinator（与 WS Chat / Community 共享同一单飞口），
  // 拦截器只保留 Dio 拦截职责：401 识别 → 请求刷新 → 用新 token 重放。

  // Lazy-initialized Dio instance for retry (without auth interceptor to avoid recursion)
  Dio? _retryDio;

  /// Get or create a Dio instance configured for retry requests.
  /// This instance has SSL pinning but no AuthInterceptor to avoid infinite recursion.
  Dio _getRetryDio() {
    if (_retryDio == null) {
      _retryDio = Dio(
        BaseOptions(
          baseUrl: ApiConstants.baseUrl,
          // N37 单一事实源：core/network/api_timeouts.dart（数值守恒 10s/30s）。
          connectTimeout: ApiTimeouts.defaultConnectTimeout,
          receiveTimeout: ApiTimeouts.defaultReceiveTimeout,
          contentType: 'application/json',
        ),
      );
      // Configure SSL pinning for secure communication
      configureDioForPinning(_retryDio!, ApiConstants.apiCertSha256);
      // Add only logging and retry interceptors (not auth)
      try {
        _retryDio!.interceptors.add(_ref.read(loggingInterceptorProvider));
      } on StateError {
        // During integration-test teardown the provider container may already
        // be disposed while late network retries are still unwinding.
      }
    }
    return _retryDio!;
  }

  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    try {
      final token = await _ref.read(authRepositoryProvider).getToken();
      final deviceHeaders =
          await _ref.read(deviceIdentityServiceProvider).buildHeaders();
      options.headers.addAll(deviceHeaders);
      if (token != null) {
        options.headers['Authorization'] = 'Bearer $token';
      }
      final currentGoalId = _ref.read(activeGoalHeaderProvider);
      if (currentGoalId != null) {
        options.headers['X-Current-Goal-ID'] = currentGoalId;
      } else {
        options.headers.remove('X-Current-Goal-ID');
      }
    } on StateError {
      // Allow late teardown-time requests to complete without crashing tests.
    }
    super.onRequest(options, handler);
  }

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    final path = err.requestOptions.path;
    final isTelemetryPath = path.contains('/client-telemetry');

    // 🎭 演示模式：仅在特定的演示API路径上忽略401
    // 更严格的条件，避免在真实API上忽略认证错误
    if (DemoDataService.isDemoMode &&
        err.response?.statusCode == 401 &&
        (path.contains('/demo/') || path.contains('/mock/'))) {
      debugPrint('🎭 Demo Mode: Ignoring 401 error for demo path: $path');
      return super.onError(err, handler);
    }

    // Prevent infinite loop: Don't attempt to refresh token if the failed request
    // is itself an auth request (login, register, refresh, etc.)
    if (path.contains('/auth') ||
        path.contains('login') ||
        path.contains('refresh') ||
        isTelemetryPath) {
      return super.onError(err, handler);
    }

    if (err.response?.statusCode == 401) {
      try {
        final authHeader =
            err.requestOptions.headers['Authorization']?.toString();
        final authRepo = _ref.read(authRepositoryProvider);
        final refreshToken = await authRepo.getRefreshToken();
        if (refreshToken == null || refreshToken.isEmpty) {
          // Unauthenticated requests can legitimately receive 401 before login.
          // Do not force a logout loop when the client has no session to refresh.
          return super.onError(err, handler);
        }
        // COMMUNITY-401: a missing Authorization header no longer hard-skips
        // recovery. After any token-state loss, every retry used to go out
        // header-less and 401 forever ("轻触重试" could never recover). When a
        // session exists (refresh token present), attempt one refresh + retry
        // exactly like the with-header path; the no-logout-loop guarantee is
        // kept by the early return above.
        if (authHeader == null || authHeader.isEmpty) {
          debugPrint(
            '🔐 Recovering header-less 401 via token refresh: $path',
          );
        }

        // AUTH-DEEP B-1：并发 401 全部 join 协调器的同一刷新 Future
        // （跨 HTTP/WS/Community 全局单飞），完成后各自带新 token 重放。
        try {
          final newToken = await _ref
              .read(tokenRefreshCoordinatorProvider)
              .refreshOnce(reason: 'http-401');
          // Clone the request and retry using a Dio instance without auth
          // interceptor. This ensures SSL pinning is still used while
          // avoiding infinite recursion.
          err.requestOptions.headers['Authorization'] = 'Bearer $newToken';
          final dio = _getRetryDio();
          final response = await dio.fetch<dynamic>(err.requestOptions);
          return handler.resolve(response);
        } on TokenRefreshException catch (e) {
          // 分级善后：仅会话终局（401/403 被拒、本地凭据已失效）登出；
          // 可重试失败（网络/5xx）保留会话，原 401 放行给业务层
          // （AUTH-DEEP B-3：一次基础设施抖动 ≠ 强登出）。
          if (e.isSessionTerminal) {
            unawaited(
              _ref.read(authRepositoryProvider).logout(
                    keepDemoMode: DemoDataService.isDemoMode,
                  ),
            );
          }
          return super.onError(err, handler);
        }
      } on StateError {
        return super.onError(err, handler);
      } catch (e) {
        return super.onError(err, handler);
      }
    }
    super.onError(err, handler);
  }
}

class LoggingInterceptor extends Interceptor {
  LoggingInterceptor({Logger? logger})
      : _logger = logger ??
            Logger(
              printer: PrettyPrinter(
                methodCount: 0,
                errorMethodCount: 5,
                lineLength: 80,
              ),
            );

  final Logger _logger;

  /// Body fields whose values must never reach logs (M6-14): login /
  /// registration / password-reset requests would otherwise leak plaintext
  /// credentials and tokens into debug output.
  static const Set<String> _sensitiveBodyFields = <String>{
    'password',
    'new_password',
    'old_password',
    'current_password',
    'confirm_password',
    'password_new',
    'password_old',
    'token',
    'access_token',
    'refresh_token',
    'id_token',
    'verification_code',
  };

  /// Returns a log-safe copy of the request body with credential values
  /// masked. Non-map bodies are not loggable in safe form and yield null.
  @visibleForTesting
  static Map<String, dynamic>? sanitizeBodyForLog(dynamic data) {
    if (data is! Map) {
      return null;
    }
    return <String, dynamic>{
      for (final entry in data.entries)
        entry.key.toString():
            _sensitiveBodyFields.contains(entry.key.toString().toLowerCase())
                ? '***'
                : entry.value,
    };
  }

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    options.extra['request_started_at_ms'] =
        DateTime.now().millisecondsSinceEpoch;
    if (kDebugMode) {
      _logger.i('Request: ${options.method} ${options.uri}');
      final sanitized = sanitizeBodyForLog(options.data);
      if (sanitized != null) {
        _logger.d('Data: $sanitized');
      }
    }
    super.onRequest(options, handler);
  }

  @override
  void onResponse(
    Response<dynamic> response,
    ResponseInterceptorHandler handler,
  ) {
    if (response.requestOptions.extra['skip_client_telemetry'] != true) {
      final startedAt =
          response.requestOptions.extra['request_started_at_ms'] as int?;
      final durationMs = startedAt == null
          ? 0
          : DateTime.now().millisecondsSinceEpoch - startedAt;
      unawaited(
        ClientObservabilityService.instance.trackApiRequest(
          path: response.requestOptions.path,
          method: response.requestOptions.method,
          status: 'ok',
          durationMs: durationMs,
          statusCode: response.statusCode,
        ),
      );
    }
    if (kDebugMode) {
      _logger
          .i('Response: ${response.statusCode} ${response.requestOptions.uri}');
      if (response.data != null) {
        _logger.d('Response Data: ${response.data}');
      }
    }
    super.onResponse(response, handler);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    if (err.requestOptions.extra['skip_client_telemetry'] != true) {
      final startedAt =
          err.requestOptions.extra['request_started_at_ms'] as int?;
      final durationMs = startedAt == null
          ? 0
          : DateTime.now().millisecondsSinceEpoch - startedAt;
      unawaited(
        ClientObservabilityService.instance.trackApiRequest(
          path: err.requestOptions.path,
          method: err.requestOptions.method,
          status: 'error',
          durationMs: durationMs,
          statusCode: err.response?.statusCode,
          message: err.message,
        ),
      );
    }
    if (kDebugMode) {
      _logger.e(
        'Error: ${err.response?.statusCode} ${err.requestOptions.uri}',
        error: err,
      );
    }
    super.onError(err, handler);
  }
}
