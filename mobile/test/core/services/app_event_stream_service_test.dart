import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:dio/dio.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/app_event_stream_service.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';

class _StubApiClient implements ApiClient {
  bool postCalled = false;

  @override
  Dio get dio => Dio();

  @override
  Future<Response<T>> post<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async {
    postCalled = true;
    throw UnimplementedError();
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _StubAuthRepository implements AuthRepository {
  @override
  Future<String?> getAccessToken() async => null;

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  test('ingestEvents skips upload when access token is unavailable', () async {
    final apiClient = _StubApiClient();
    final authRepository = _StubAuthRepository();

    final container = ProviderContainer(
      overrides: [
        apiClientProvider.overrideWithValue(apiClient),
        authRepositoryProvider.overrideWithValue(authRepository),
      ],
    );
    addTearDown(container.dispose);

    final service = container.read(appEventStreamServiceProvider);
    await service.ingestEvents([
      {'event_type': 'demo', 'source': 'test', 'ts_ms': 1},
    ]);

    expect(apiClient.postCalled, isFalse);
  });
}
