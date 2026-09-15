import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/shared/entities/task_model.dart';

class TestApiClient implements ApiClient {
  Future<Response<dynamic>> Function(
    String path,
    Map<String, dynamic>? queryParameters,
  )? getHandler;
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

void main() {
  late TestApiClient apiClient;
  late TaskRepository repository;

  setUp(() {
    DemoDataService.isDemoMode = false;
    apiClient = TestApiClient();
    repository = TaskRepository(apiClient);
  });

  tearDown(() {
    DemoDataService.isDemoMode = false;
  });

  test('getTasks returns paginated tasks', () async {
    final task = <String, dynamic>{
      'id': 'task-1',
      'user_id': 'user-1',
      'title': 'Study',
      'type': 'LEARNING',
      'tags': ['tag'],
      'estimated_minutes': 30,
      'difficulty': 2,
      'energy_cost': 1,
      'status': 'PENDING',
      'priority': 1,
      'created_at': '2024-01-01T00:00:00.000Z',
      'updated_at': '2024-01-01T00:00:00.000Z',
    };

    apiClient.getHandler = (path, queryParameters) async {
      expect(path, ApiEndpoints.tasks);
      return Response(
        requestOptions: RequestOptions(path: ApiEndpoints.tasks),
        data: {
          'items': [task],
          'total': 1,
          'page': 1,
          'page_size': 10,
        },
      );
    };

    final result = await repository.getTasks();

    expect(result.items.length, 1);
    expect(result.items.first.id, 'task-1');
  });

  test('getTask unwraps response payload', () async {
    final task = <String, dynamic>{
      'id': 'task-2',
      'user_id': 'user-1',
      'title': 'Review',
      'type': 'LEARNING',
      'tags': ['tag'],
      'estimated_minutes': 20,
      'difficulty': 1,
      'energy_cost': 1,
      'status': 'PENDING',
      'priority': 1,
      'created_at': '2024-01-01T00:00:00.000Z',
      'updated_at': '2024-01-01T00:00:00.000Z',
    };

    apiClient.getHandler = (path, queryParameters) async {
      expect(path, ApiEndpoints.task('task-2'));
      return Response(
        requestOptions: RequestOptions(path: ApiEndpoints.task('task-2')),
        data: {'data': task},
      );
    };

    final result = await repository.getTask('task-2');

    expect(result.id, 'task-2');
  });

  test('createTaskWithNudges parses nudges from wrapped task payloads',
      () async {
    final task = TaskCreate(
      title: 'Sprint prep',
      type: TaskType.learning,
      estimatedMinutes: 30,
      difficulty: 2,
    );

    apiClient.postHandler = (path, data, queryParameters) async {
      expect(path, ApiEndpoints.tasks);
      return Response(
        requestOptions: RequestOptions(path: ApiEndpoints.tasks),
        data: {
          'data': {
            'id': 'task-3',
            'user_id': 'user-1',
            'title': 'Sprint prep',
            'type': 'LEARNING',
            'tags': ['exam'],
            'estimated_minutes': 30,
            'difficulty': 2,
            'energy_cost': 1,
            'status': 'PENDING',
            'priority': 1,
            'created_at': '2024-01-01T00:00:00.000Z',
            'updated_at': '2024-01-01T00:00:00.000Z',
            'nudges': [
              {
                'type': 'time_adjustment',
                'title': '预估偏紧',
                'description': '建议放宽一点时间预算',
                'suggestedValue': 45,
                'patternId': 'optimism-bias',
                'confidence': 0.82,
              },
            ],
          },
        },
      );
    };

    final result = await repository.createTaskWithNudges(task);
    final createdTask = result.task as TaskModel;

    expect(createdTask.id, 'task-3');
    expect(result.nudges, hasLength(1));
    expect(result.nudges.single.message, '建议放宽一点时间预算');
    expect(result.nudges.single.suggestedValue, 45);
    expect(result.nudges.single.patternId, 'optimism-bias');
  });

  test('getTaskGuidance accepts camelCase guidance contracts', () async {
    apiClient.getHandler = (path, queryParameters) async {
      expect(path, '${ApiEndpoints.task('task-1')}/guidance');
      return Response(
        requestOptions: RequestOptions(path: path),
        data: {
          'data': {
            'id': 'guidance-1',
            'taskId': 'task-1',
            'userId': 'user-1',
            'audience': 'ai',
            'content': 'TASK_GUIDANCE_SCAFFOLD v2',
            'generatedBy': 'task_guidance_ai_scaffold',
            'policyVersion': 'stage4.task_guidance.v2',
            'contentFormat': 'plaintext',
            'createdAt': '2024-01-01T00:00:00.000Z',
            'updatedAt': '2024-01-01T00:05:00.000Z',
            'sourceGuidanceId': 'guidance-0',
            'sourceTaskUpdatedAt': '2024-01-01T00:03:00.000Z',
          },
        },
      );
    };

    final result = await repository.getTaskGuidance(
      'task-1',
      audience: TaskGuidanceAudience.ai,
    );

    expect(result, isNotNull);
    expect(result!.taskId, 'task-1');
    expect(result.userId, 'user-1');
    expect(result.audience, TaskGuidanceAudience.ai);
    expect(result.generatedBy, 'task_guidance_ai_scaffold');
    expect(result.policyVersion, 'stage4.task_guidance.v2');
    expect(result.contentFormat, 'plaintext');
    expect(result.sourceGuidanceId, 'guidance-0');
    expect(
      result.sourceTaskUpdatedAt,
      DateTime.parse('2024-01-01T00:03:00.000Z'),
    );
  });
}
