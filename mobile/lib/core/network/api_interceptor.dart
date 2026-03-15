import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:logger/logger.dart';
import 'package:sparkle/core/constants/api_constants.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/core/services/device_identity_service.dart';
import 'package:sparkle/features/auth/auth.dart';

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
  AuthInterceptor(this._ref);
  final Ref _ref;

  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    final token = await _ref.read(authRepositoryProvider).getToken();
    final deviceHeaders =
        await _ref.read(deviceIdentityServiceProvider).buildHeaders();
    options.headers.addAll(deviceHeaders);
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    super.onRequest(options, handler);
  }

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    final path = err.requestOptions.path;

    // 🎭 演示模式：忽略401错误，不尝试刷新token或logout
    // 这样可以让演示模式下的请求失败时不会影响用户体验
    if (DemoDataService.isDemoMode && err.response?.statusCode == 401) {
      debugPrint('🎭 Demo Mode: Ignoring 401 error for $path');
      return super.onError(err, handler);
    }

    // Prevent infinite loop: Don't attempt to refresh token if the failed request
    // is itself an auth request (login, register, refresh, etc.)
    if (path.contains('/auth') ||
        path.contains('login') ||
        path.contains('refresh')) {
      return super.onError(err, handler);
    }

    if (err.response?.statusCode == 401) {
      try {
        final authRepo = _ref.read(authRepositoryProvider);
        final newToken = await authRepo.refreshToken();
        // Clone the request and retry
        // Use a new Dio instance with the same base configuration
        final dio = Dio(BaseOptions(
          baseUrl: ApiConstants.baseUrl,
          connectTimeout: const Duration(seconds: 10),
          receiveTimeout: const Duration(seconds: 30),
        ),);
        err.requestOptions.headers['Authorization'] =
            'Bearer ${newToken.accessToken}';
        final response = await dio.fetch<dynamic>(err.requestOptions);
        return handler.resolve(response);
      } catch (e) {
        // Refresh token failed, logout user
        unawaited(_ref.read(authRepositoryProvider).logout(
              keepDemoMode: DemoDataService.isDemoMode,
            ),);
        return super.onError(err, handler);
      }
    }
    super.onError(err, handler);
  }
}

class LoggingInterceptor extends Interceptor {
  final Logger _logger = Logger(
    printer: PrettyPrinter(
      methodCount: 0,
      errorMethodCount: 5,
      lineLength: 80,
    ),
  );

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    if (kDebugMode) {
      _logger.i('Request: ${options.method} ${options.uri}');
      if (options.data != null) {
        _logger.d('Data: ${options.data}');
      }
    }
    super.onRequest(options, handler);
  }

  @override
  void onResponse(
    Response<dynamic> response,
    ResponseInterceptorHandler handler,
  ) {
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
    if (kDebugMode) {
      _logger.e(
        'Error: ${err.response?.statusCode} ${err.requestOptions.uri}',
        error: err,
      );
    }
    super.onError(err, handler);
  }
}
