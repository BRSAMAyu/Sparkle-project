import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';

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
}
