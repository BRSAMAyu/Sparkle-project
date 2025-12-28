import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:logger/logger.dart';
import 'package:sparkle/data/repositories/auth_repository.dart';

final authInterceptorProvider = Provider(AuthInterceptor.new);
final loggingInterceptorProvider = Provider((ref) => LoggingInterceptor());
final retryInterceptorProvider = Provider.family<RetryInterceptor, Dio>((ref, dio) => RetryInterceptor(dio: dio));

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
  Future<void> onError(DioException err, ErrorInterceptorHandler handler) async {
    if (retryableStatuses.contains(err.response?.statusCode) && 
        _shouldRetry(err)) {
      
      final retries = err.requestOptions.extra['retries'] as int? ?? 0;
      if (retries < maxRetries) {
        err.requestOptions.extra['retries'] = retries + 1;
        
        // Exponential backoff
        final delay = Duration(milliseconds: 500 * (1 << retries));
        await Future.delayed(delay);

        try {
          final response = await dio.fetch(err.requestOptions);
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
  Future<void> onRequest(RequestOptions options, RequestInterceptorHandler handler) async {
    final token = await _ref.read(authRepositoryProvider).getToken();
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    super.onRequest(options, handler);
  }

  @override
  Future<void> onError(DioException err, ErrorInterceptorHandler handler) async {
    final path = err.requestOptions.path;
    // Prevent infinite loop: Don't attempt to refresh token if the failed request
    // is itself an auth request (login, register, refresh, etc.)
    if (path.contains('/auth') || path.contains('login') || path.contains('refresh')) {
      return super.onError(err, handler);
    }

    if (err.response?.statusCode == 401) {
      try {
        final authRepo = _ref.read(authRepositoryProvider);
        final newToken = await authRepo.refreshToken();
        // Clone the request and retry
        final dio = Dio();
        err.requestOptions.headers['Authorization'] = 'Bearer ${newToken.accessToken}';
        final response = await dio.fetch(err.requestOptions);
        return handler.resolve(response);
            } catch (e) {
        // Refresh token failed, logout user
        _ref.read(authRepositoryProvider).logout();
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
  void onResponse(Response response, ResponseInterceptorHandler handler) {
    if (kDebugMode) {
      _logger.i('Response: ${response.statusCode} ${response.requestOptions.uri}');
      if (response.data != null) {
        _logger.d('Response Data: ${response.data}');
      }
    }
    super.onResponse(response, handler);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    if (kDebugMode) {
      _logger.e('Error: ${err.response?.statusCode} ${err.requestOptions.uri}', error: err);
    }
    super.onError(err, handler);
  }
}
