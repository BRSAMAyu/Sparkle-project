import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';

class MockApiClient extends Mock implements ApiClient {}

void main() {
  late MockApiClient mockApiClient;
  late TaskRepository repository;

  setUp(() {
    DemoDataService.isDemoMode = false;
    mockApiClient = MockApiClient();
    repository = TaskRepository(mockApiClient);
  });

  tearDown(() {
    DemoDataService.isDemoMode = false;
  });

  test('getTasks returns paginated tasks', () async {
    final task = <String, dynamic>{
      'id': 'task-1',
      'user_id': 'user-1',
      'title': 'Study',
      'type': 'learning',
      'tags': ['tag'],
      'estimated_minutes': 30,
      'difficulty': 2,
      'energy_cost': 1,
      'status': 'pending',
      'priority': 1,
      'created_at': '2024-01-01T00:00:00.000Z',
      'updated_at': '2024-01-01T00:00:00.000Z',
    };

    when(
      mockApiClient.get<Map<String, dynamic>>(
        ApiEndpoints.tasks,
        queryParameters: anyNamed('queryParameters'),
      ),
    ).thenAnswer(
      (_) async => Response(
        requestOptions: RequestOptions(path: ApiEndpoints.tasks),
        data: {
          'items': [task],
          'total': 1,
          'page': 1,
          'page_size': 10,
        },
      ),
    );

    final result = await repository.getTasks();

    expect(result.items.length, 1);
    expect(result.items.first.id, 'task-1');
  });

  test('getTask unwraps response payload', () async {
    final task = <String, dynamic>{
      'id': 'task-2',
      'user_id': 'user-1',
      'title': 'Review',
      'type': 'learning',
      'tags': ['tag'],
      'estimated_minutes': 20,
      'difficulty': 1,
      'energy_cost': 1,
      'status': 'pending',
      'priority': 1,
      'created_at': '2024-01-01T00:00:00.000Z',
      'updated_at': '2024-01-01T00:00:00.000Z',
    };

    when(
      mockApiClient.get<Map<String, dynamic>>(ApiEndpoints.task('task-2')),
    ).thenAnswer(
      (_) async => Response(
        requestOptions: RequestOptions(path: ApiEndpoints.task('task-2')),
        data: {'data': task},
      ),
    );

    final result = await repository.getTask('task-2');

    expect(result.id, 'task-2');
  });
}
