import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';

class MockApiClient extends Mock implements ApiClient {}

class MockFlutterSecureStorage extends Mock implements FlutterSecureStorage {}

void main() {
  late MockApiClient mockApiClient;
  late MockFlutterSecureStorage mockStorage;
  late AuthRepository repository;

  setUp(() {
    DemoDataService.isDemoMode = false;
    mockApiClient = MockApiClient();
    mockStorage = MockFlutterSecureStorage();
    repository = AuthRepository(mockApiClient, mockStorage);
  });

  tearDown(() {
    DemoDataService.isDemoMode = false;
  });

  test('login stores tokens and returns response', () async {
    when(
      mockApiClient.post<Map<String, dynamic>>(
        ApiEndpoints.login,
        data: anyNamed('data'),
      ),
    ).thenAnswer(
      (_) async => Response(
        requestOptions: RequestOptions(path: ApiEndpoints.login),
        data: {
          'access_token': 'access-token',
          'refresh_token': 'refresh-token',
          'token_type': 'bearer',
          'expires_in': 3600,
        },
      ),
    );
    when(
      mockStorage.write(key: anyNamed('key'), value: anyNamed('value')),
    ).thenAnswer((_) async {});

    final response = await repository.login('user@example.com', 'password');

    expect(response.accessToken, 'access-token');
    verify(mockStorage.write(key: 'accessToken', value: 'access-token'))
        .called(1);
    verify(mockStorage.write(key: 'refreshToken', value: 'refresh-token'))
        .called(1);
  });

  test('refreshToken throws when no refresh token is stored', () async {
    when(mockStorage.read(key: 'refreshToken')).thenAnswer((_) async => null);

    expect(
      () async => repository.refreshToken(),
      throwsA(isA<Exception>()),
    );
  });
}
