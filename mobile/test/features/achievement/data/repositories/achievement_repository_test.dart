import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/achievement/data/repositories/achievement_repository.dart';

class TestApiClient implements ApiClient {
  Future<Response<dynamic>> Function(
    String path,
    Map<String, dynamic>? queryParameters,
  )? getHandler;

  @override
  Dio get dio => throw UnimplementedError();

  @override
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    final handler = getHandler;
    if (handler == null) {
      throw UnimplementedError('No get handler configured');
    }

    final response = await handler(path, queryParameters);
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

void main() {
  late TestApiClient apiClient;
  late AchievementRepository repository;

  setUp(() {
    DemoDataService.isDemoMode = false;
    apiClient = TestApiClient();
    repository = AchievementRepository(apiClient);
  });

  tearDown(() {
    DemoDataService.isDemoMode = false;
  });

  test('getCloseToUnlockAchievements parses nested payload shape', () async {
    apiClient.getHandler = (path, queryParameters) async {
      expect(path, ApiEndpoints.achievementsCloseToUnlock);
      expect(queryParameters?['category'], 'sprint');
      expect(queryParameters?['threshold'], 0.8);

      return Response(
        requestOptions:
            RequestOptions(path: ApiEndpoints.achievementsCloseToUnlock),
        data: {
          'data': [
            {
              'achievement': {
                'id': 'speed_learner',
                'name': '速通大师',
                'description': '24小时内解锁20个新知识点',
                'icon_url': '/icons/achievements/speed_learner.png',
                'type': 'hidden',
                'rarity': 'epic',
                'category': 'hidden',
                'is_hidden': true,
                'hint': '效率至上...',
                'sort_order': 103,
                'parent_id': null,
                'trigger_code': 'SPEED_UNLOCK',
                'trigger_config': {'count': 20, 'hours': 24},
                'prerequisites': null,
                'visual_effect_type': 'supernova',
                'visual_config': {
                  'particle_count': 100,
                  'expansion_speed': 2.0
                },
                'reward_config': [
                  {
                    'type': 'title',
                    'value': 'speed_learner',
                    'display': '速通大师'
                  },
                ],
                'total_unlocked': 0,
                'created_at': '2026-03-10T00:00:00Z',
                'updated_at': '2026-03-10T00:00:00Z',
              },
              'user_progress': {
                'achievement_id': 'speed_learner',
                'progress': 0.8,
                'progress_value': 16,
                'progress_target': 20,
                'is_pinned': false,
                'share_count': 0,
                'is_first_unlocker': false,
                'unlocked_at': null,
                'last_progress_update': null,
              },
              'is_unlocked': false,
              'progress_percentage': 80,
            },
          ],
          'count': 1,
        },
      );
    };

    final result = await repository.getCloseToUnlockAchievements(
      category: 'sprint',
      threshold: 0.8,
    );

    expect(result.length, 1);
    expect(result.first.achievement.id, 'speed_learner');
    expect(result.first.userProgress?.progressValue, 16);
    expect(result.first.progressPercentage, 80);
    expect(result.first.isUnlocked, isFalse);
  });
}
