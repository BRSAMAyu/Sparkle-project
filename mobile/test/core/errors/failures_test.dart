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
  });
}
