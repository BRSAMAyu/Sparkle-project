import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/user/data/repositories/user_repository.dart';
import 'package:sparkle/shared/entities/user_model.dart';

class TestApiClient implements ApiClient {
  Future<Response<dynamic>> Function(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  })? putHandler;

  @override
  Dio get dio => throw UnimplementedError();

  @override
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) {
    throw UnimplementedError();
  }

  @override
  Future<Response<T>> post<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) {
    throw UnimplementedError();
  }

  @override
  Future<Response<T>> put<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async {
    final handler = putHandler;
    if (handler == null) {
      throw UnimplementedError('No put handler configured');
    }
    final response = await handler(
      path,
      data: data,
      queryParameters: queryParameters,
    );
    return Response<T>(
      data: response.data as T,
      requestOptions: response.requestOptions,
      statusCode: response.statusCode,
      statusMessage: response.statusMessage,
      isRedirect: response.isRedirect,
      redirects: response.redirects,
      extra: response.extra,
      headers: response.headers,
    );
  }

  @override
  Future<Response<T>> patch<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) {
    throw UnimplementedError();
  }

  @override
  Future<Response<T>> delete<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) {
    throw UnimplementedError();
  }

  @override
  Stream<SSEEvent> getStream(
    String path, {
    Map<String, dynamic>? queryParameters,
    Map<String, dynamic>? headers,
  }) {
    throw UnimplementedError();
  }

  @override
  Stream<SSEEvent> postStream(String path, {Object? data}) {
    throw UnimplementedError();
  }
}

void main() {
  late TestApiClient apiClient;
  late UserRepository repository;

  setUp(() {
    DemoDataService.isDemoMode = false;
    apiClient = TestApiClient();
    repository = UserRepository(apiClient);
  });

  tearDown(() {
    DemoDataService.isDemoMode = false;
  });

  test('updateUserPreferences posts data and returns user model', () async {
    final payload = <String, dynamic>{
      'id': 'user-1',
      'username': 'spark',
      'email': 'spark@example.com',
      'flame_level': 1,
      'flame_brightness': 0.6,
      'depth_preference': 0.4,
      'curiosity_preference': 0.7,
      'is_active': true,
      'status': 'offline',
      'created_at': '2024-01-01T00:00:00.000Z',
      'updated_at': '2024-01-02T00:00:00.000Z',
    };

    apiClient.putHandler = (path, {data, queryParameters}) async {
      expect(path, '/users/me/preferences');
      expect(data, <String, dynamic>{
        'learning_depth': 0.4,
        'curiosity_level': 0.7,
      });
      return Response(
        requestOptions: RequestOptions(path: '/users/me/preferences'),
        data: payload,
      );
    };

    final result = await repository.updateUserPreferences(
      UserPreferences(depthPreference: 0.4, curiosityPreference: 0.7),
    );

    expect(result.id, 'user-1');
  });
}
