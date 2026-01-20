import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/user/data/repositories/user_repository.dart';
import 'package:sparkle/shared/entities/user_model.dart';

class MockApiClient extends Mock implements ApiClient {}

void main() {
  late MockApiClient mockApiClient;
  late UserRepository repository;

  setUp(() {
    DemoDataService.isDemoMode = false;
    mockApiClient = MockApiClient();
    repository = UserRepository(mockApiClient);
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

    when(
      mockApiClient.put<Map<String, dynamic>>(
        '/users/me/preferences',
        data: anyNamed('data'),
      ),
    ).thenAnswer(
      (_) async => Response(
        requestOptions: RequestOptions(path: '/users/me/preferences'),
        data: payload,
      ),
    );

    final result = await repository.updateUserPreferences(
      UserPreferences(depthPreference: 0.4, curiosityPreference: 0.7),
    );

    expect(result.id, 'user-1');
    verify(
      mockApiClient.put<Map<String, dynamic>>(
        '/users/me/preferences',
        data: anyNamed('data'),
      ),
    ).called(1);
  });
}
