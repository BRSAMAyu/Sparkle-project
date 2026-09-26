import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/errors/failures.dart';

void main() {
  group('AppFailureMapper', () {
    test('maps Dio connection errors to offline failures', () {
      final failure = AppFailureMapper.fromDio(
        DioException(
          requestOptions: RequestOptions(path: '/chat'),
          type: DioExceptionType.connectionError,
          error: 'SocketException: failed host lookup',
        ),
      );

      expect(failure, isA<OfflineFailure>());
      expect(failure.kind, FailureKind.offline);
      expect(failure.errorCode, 'OFFLINE');
      expect(failure.isRetryable, isTrue);
    });

    test('maps auth responses to auth failures', () {
      final failure = AppFailureMapper.fromDio(
        DioException(
          requestOptions: RequestOptions(path: '/me'),
          type: DioExceptionType.badResponse,
          response: Response<Map<String, dynamic>>(
            requestOptions: RequestOptions(path: '/me'),
            statusCode: 401,
            data: const {'detail': 'token expired'},
          ),
        ),
      );

      expect(failure, isA<AuthFailure>());
      expect(failure.kind, FailureKind.auth);
      expect(failure.requiresLogin, isTrue);
      expect(failure.isRetryable, isFalse);
    });

    test('maps validation responses without turning them into server errors',
        () {
      final failure = AppFailureMapper.fromDio(
        DioException(
          requestOptions: RequestOptions(path: '/auth/register'),
          type: DioExceptionType.badResponse,
          response: Response<Map<String, dynamic>>(
            requestOptions: RequestOptions(path: '/auth/register'),
            statusCode: 422,
            data: const {'detail': 'email is invalid'},
          ),
        ),
      );

      expect(failure, isA<ValidationFailure>());
      expect(failure.kind, FailureKind.validation);
      expect(failure.message, 'email is invalid');
      expect(failure.isRetryable, isFalse);
    });

    test('maps server responses to retryable server failures', () {
      final failure = AppFailureMapper.fromDio(
        DioException(
          requestOptions: RequestOptions(path: '/dashboard'),
          type: DioExceptionType.badResponse,
          response: Response<Map<String, dynamic>>(
            requestOptions: RequestOptions(path: '/dashboard'),
            statusCode: 503,
            data: const {'message': 'service unavailable'},
          ),
        ),
      );

      expect(failure, isA<ServerFailure>());
      expect(failure.kind, FailureKind.server);
      expect(failure.isRetryable, isTrue);
    });

    // V3-FIX-17：web 注册「静默假失败」——dio assureDioException 把成功管线
    // 内抛出的非 Dio 异常（解码/泛型 cast/拦截器错误）统一包装为
    // DioExceptionType.unknown（DioException 构造默认 type，故下方不显式传），
    // 旧映射把它一揽子谎报成 NetworkFailure
    // （「网络连接不稳定」）：注册 POST 网关 200 且账号已入库，App 却播
    // 错误音效、误报网络错误并卡死注册页，用户重试必撞「用户名已存在」。
    test('maps unknown with client parse error to parse failure, not network',
        () {
      final failure = AppFailureMapper.fromDio(
        DioException(
          requestOptions: RequestOptions(path: '/auth/register'),
          error: _produceRealTypeError(),
        ),
      );

      expect(failure, isA<UnknownFailure>());
      expect(failure.kind, FailureKind.unknown);
      expect(failure.errorCode, 'PARSE_ERROR');
      // 文案走 fallback，不向用户倾倒技术细节/响应体 dump。
      expect(failure.message, 'Request failed.');
      expect(failure.userMessage, isNot(contains('网络连接不稳定')));
    });

    test(
        'maps unknown with format error to parse failure, not network '
        '(FormatException variant)', () {
      final failure = AppFailureMapper.fromDio(
        DioException(
          requestOptions: RequestOptions(path: '/auth/register'),
          error: const FormatException('Unexpected end of input'),
        ),
      );

      expect(failure, isA<UnknownFailure>());
      expect(failure.errorCode, 'PARSE_ERROR');
    });

    test('maps unknown with a server answer to pipeline failure, not network',
        () {
      final failure = AppFailureMapper.fromDio(
        DioException(
          requestOptions: RequestOptions(path: '/auth/register'),
          error: StateError('pipeline blew up after 200'),
          response: Response<Map<String, dynamic>>(
            requestOptions: RequestOptions(path: '/auth/register'),
            statusCode: 200,
            data: const <String, dynamic>{'ok': true},
          ),
        ),
      );

      expect(failure, isA<UnknownFailure>());
      expect(failure.errorCode, 'PIPELINE_ERROR');
      expect(failure.statusCode, 200);
      expect(failure.userMessage, isNot(contains('网络连接不稳定')));
    });

    test(
        'still maps unknown without response or parse signature to network '
        'failure (true network-layer unknown preserved)', () {
      final failure = AppFailureMapper.fromDio(
        DioException(
          requestOptions: RequestOptions(path: '/chat'),
          error: StateError('boom'),
        ),
      );

      expect(failure, isA<NetworkFailure>());
      expect(failure.errorCode, 'NETWORK_ERROR');
      expect(failure.isRetryable, isTrue);
    });
  });
}

/// 产出真实运行时 [TypeError]（`TypeError` 无法直接构造），
/// 模拟 dio 成功管线内 `assureResponse` 泛型 cast / 模型解码抛出的类型错误。
Object _produceRealTypeError() {
  try {
    final broken = <dynamic>['not-an-int'] as List<int>;
    throw StateError('unreachable: $broken');
  } on TypeError catch (e) {
    return e;
  }
}
