import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';

class TestApiClient implements ApiClient {
  Future<Response<dynamic>> Function(
    String path,
    Object? data,
    Map<String, dynamic>? queryParameters,
  )? postHandler;

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
  }) async {
    final handler = postHandler;
    if (handler == null) {
      throw UnimplementedError('No post handler configured');
    }
    final response = await handler(path, data, queryParameters);
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
  Future<Response<T>> put<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) {
    throw UnimplementedError();
  }

  @override
  Future<Response<T>> patch<T>(String path, {Object? data}) {
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

class InMemorySecureStorage implements FlutterSecureStorage {
  final Map<String, String> _values = <String, String>{};

  @override
  Future<void> write({
    required String key,
    required String? value,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    AppleOptions? mOptions,
    WindowsOptions? wOptions,
    MacOsOptions? macOsOptions,
  }) async {
    if (value == null) {
      _values.remove(key);
    } else {
      _values[key] = value;
    }
  }

  @override
  Future<String?> read({
    required String key,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    AppleOptions? mOptions,
    WindowsOptions? wOptions,
    MacOsOptions? macOsOptions,
  }) async =>
      _values[key];

  @override
  Future<void> delete({
    required String key,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    AppleOptions? mOptions,
    WindowsOptions? wOptions,
    MacOsOptions? macOsOptions,
  }) async {
    _values.remove(key);
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  late TestApiClient apiClient;
  late InMemorySecureStorage storage;
  late AuthRepository repository;

  setUp(() {
    DemoDataService.isDemoMode = false;
    apiClient = TestApiClient();
    storage = InMemorySecureStorage();
    repository = AuthRepository(apiClient, storage);
  });

  tearDown(() {
    DemoDataService.isDemoMode = false;
  });

  test('login stores tokens and returns response', () async {
    apiClient.postHandler = (path, data, queryParameters) async {
      expect(path, ApiEndpoints.login);
      return Response(
        requestOptions: RequestOptions(path: ApiEndpoints.login),
        data: {
          'token': {
            'access_token': 'access-token',
            'refresh_token': 'refresh-token',
            'token_type': 'bearer',
            'expires_in': 3600,
          },
          'user': {
            'id': 'user-1',
            'username': 'tester',
            'email': 'user@example.com',
            'nickname': 'Tester',
            'avatar_status': 'approved',
            'flame_level': 1,
            'flame_brightness': 0.5,
            'depth_preference': 0.5,
            'curiosity_preference': 0.5,
            'is_active': true,
            'status': 'offline',
            'created_at': '2026-01-01T00:00:00Z',
            'updated_at': '2026-01-01T00:00:00Z',
          },
        },
      );
    };

    final response = await repository.login('user@example.com', 'password');

    expect(response.username, 'tester');
    expect(await storage.read(key: 'accessToken'), 'access-token');
    expect(await storage.read(key: 'refreshToken'), 'refresh-token');
  });

  test('refreshToken throws when no refresh token is stored', () async {
    await expectLater(
      repository.refreshToken(),
      throwsA(isA<Exception>()),
    );
  });
}
