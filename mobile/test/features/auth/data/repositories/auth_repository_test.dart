import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/core/storage/token_storage.dart';
import 'package:sparkle/core/storage/token_storage_web.dart';
import 'package:sparkle/features/auth/data/models/token_model.dart';
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

class InMemoryTokenStorage implements TokenStorage {
  final Map<String, String> _values = <String, String>{};

  @override
  Future<String?> read(String key) async => _values[key];

  @override
  Future<void> write(String key, String value) async {
    _values[key] = value;
  }

  @override
  Future<void> delete(String key) async {
    _values.remove(key);
  }
}

void main() {
  late TestApiClient apiClient;
  late InMemoryTokenStorage storage;
  late AuthRepository repository;

  setUp(() {
    DemoDataService.isDemoMode = false;
    apiClient = TestApiClient();
    storage = InMemoryTokenStorage();
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
    expect(await storage.read('accessToken'), 'access-token');
    expect(await storage.read('refreshToken'), 'refresh-token');
  });

  test('refreshToken throws when no refresh token is stored', () async {
    await expectLater(
      repository.refreshToken(),
      throwsA(isA<Exception>()),
    );
  });

  test('getAccessToken reuses in-memory cache after first read', () async {
    await storage.write('accessToken', 'cached-token');

    expect(await repository.getAccessToken(), 'cached-token');

    await storage.delete('accessToken');

    expect(await repository.getAccessToken(), 'cached-token');
  });

  /// W-1/W-2 验收测试：web 平台（注入 TokenStorageWeb，落 localStorage）
  /// 下 saveTokens 后 read 能取回 —— 修复前 secure storage web 并发写全丢，
  /// getAccessToken 恒为空（web-round1：UI 不跳转、刷新丢会话的根因）。
  test('W-1/W-2: web storage keeps tokens across saveTokens → read', () async {
    SharedPreferences.setMockInitialValues({});
    final webRepository = AuthRepository(apiClient, TokenStorageWeb());

    await webRepository.saveTokens(
      TokenResponse(
        accessToken: 'web-access-token',
        refreshToken: 'web-refresh-token',
        expiresIn: 3600,
      ),
    );

    expect(await webRepository.getAccessToken(), 'web-access-token');
    expect(await webRepository.getRefreshToken(), 'web-refresh-token');
    expect(await webRepository.isLoggedIn(), isTrue);

    await webRepository.clearTokens();
    expect(await webRepository.getAccessToken(), isNull);
    expect(await webRepository.isLoggedIn(), isFalse);
  });
}
