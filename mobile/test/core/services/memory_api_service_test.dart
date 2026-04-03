import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/core/services/memory_api_service.dart';
import 'package:sparkle/core/network/api_client.dart';

class _TestApiClient implements ApiClient {
  Future<Response<Map<String, dynamic>>> Function(
    String path,
    Map<String, dynamic>? queryParameters,
  )? getHandler;

  Future<Response<Map<String, dynamic>>> Function(
    String path,
    Object? data,
    Map<String, dynamic>? queryParameters,
  )? putHandler;

  @override
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    final handler = getHandler;
    if (handler == null) {
      throw UnimplementedError();
    }
    return await handler(path, queryParameters) as Response<T>;
  }

  @override
  Future<Response<T>> put<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async {
    final handler = putHandler;
    if (handler == null) {
      throw UnimplementedError();
    }
    return await handler(path, data, queryParameters) as Response<T>;
  }

  @override
  Future<Response<T>> post<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) => throw UnimplementedError();

  @override
  Future<Response<T>> patch<T>(String path, {Object? data}) =>
      throw UnimplementedError();

  @override
  Future<Response<T>> delete<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) => throw UnimplementedError();

  @override
  Stream<SSEEvent> getStream(
    String path, {
    Map<String, dynamic>? queryParameters,
    Map<String, dynamic>? headers,
  }) => const Stream<SSEEvent>.empty();

  @override
  Stream<SSEEvent> postStream(String path, {Object? data}) =>
      const Stream<SSEEvent>.empty();

  @override
  Dio get dio => throw UnimplementedError();
}

void main() {
  group('MemoryApiService', () {
    test('falls back to default settings when memory settings request is unauthorized', () async {
      final apiClient = _TestApiClient()
        ..getHandler = (path, queryParameters) async {
          throw DioException(
            requestOptions: RequestOptions(path: path),
            response: Response<Map<String, dynamic>>(
              requestOptions: RequestOptions(path: path),
              statusCode: 401,
              data: <String, dynamic>{'detail': 'Unauthorized'},
            ),
            type: DioExceptionType.badResponse,
          );
        };

      final service = MemoryApiService(apiClient);
      final settings = await service.getMemorySettings();

      expect(settings.enabled, isTrue);
      expect(settings.allowPreferences, isTrue);
      expect(settings.allowGoals, isTrue);
      expect(settings.allowEpisodic, isTrue);
      expect(settings.captureLevel, 'medium');
      expect(settings.blockedPrefKeys, isEmpty);
      expect(settings.blockedSources, isEmpty);
    });

    test('returns submitted settings when update is unauthorized', () async {
      final apiClient = _TestApiClient()
        ..putHandler = (path, data, queryParameters) async {
          throw DioException(
            requestOptions: RequestOptions(path: path),
            response: Response<Map<String, dynamic>>(
              requestOptions: RequestOptions(path: path),
              statusCode: 401,
              data: <String, dynamic>{'detail': 'Unauthorized'},
            ),
            type: DioExceptionType.badResponse,
          );
        };

      final service = MemoryApiService(apiClient);
      final submitted = service.updateMemorySettings(
        MemorySettingsModel(
          enabled: false,
          allowPreferences: true,
          allowGoals: false,
          allowEpisodic: true,
          captureLevel: 'high',
          blockedPrefKeys: const ['response_style'],
          blockedSources: const ['chat'],
        ),
      );

      final resolved = await submitted;
      expect(resolved.enabled, isFalse);
      expect(resolved.captureLevel, 'high');
      expect(resolved.blockedPrefKeys, contains('response_style'));
    });
  });
}
