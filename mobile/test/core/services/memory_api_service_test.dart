import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/memory_api_service.dart';

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
  Future<Response<T>> patch<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) =>
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
    test('propagates unauthorized read failures instead of fabricating defaults (R2-01)', () async {
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

      // R2-01（wt296 对齐）：memory_api_service 是薄 API 层——读失败（含 401）
      // 原样传播给调用者，由调用方决定是否以默认值兜底；服务层绝不伪造用户设置。
      await expectLater(service.getMemorySettings(), throwsA(isA<DioException>()));
    });

    test('propagates unauthorized save failures instead of echoing the payload (R2-01)', () async {
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
          allowInferredEpisodic: true,
          captureLevel: 'high',
          blockedPrefKeys: const ['response_style'],
          blockedSources: const ['chat'],
        ),
      );

      // R2-01（wt296 对齐）：保存失败原样传播——回显载荷等于把未落库的设置
      // 假装成保存成功，违反诚实性红线。
      await expectLater(submitted, throwsA(isA<DioException>()));
    });
  });
}
