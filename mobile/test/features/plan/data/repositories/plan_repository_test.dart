import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/data/repositories/plan_repository.dart';

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
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  late TestApiClient apiClient;
  late PlanRepository repository;

  setUp(() {
    DemoDataService.isDemoMode = false;
    DemoDataService().resetDemoState();
    apiClient = TestApiClient();
    repository = PlanRepository(apiClient);
  });

  tearDown(() {
    DemoDataService.isDemoMode = false;
    DemoDataService().resetDemoState();
  });

  test('getPlans parses paginated canonical payload for growth plans', () async {
    apiClient.getHandler = (path, queryParameters) async {
      expect(path, ApiEndpoints.plans);
      expect(queryParameters, {
        'type': 'growth',
        'is_active': true,
      });
      return Response(
        requestOptions: RequestOptions(path: ApiEndpoints.plans),
        data: {
          'data': [
            {
              'id': 'plan-growth-1',
              'user_id': 'user-1',
              'name': '长期计划一',
              'type': 'growth',
              'description': '系统化成长',
              'subject': '系统设计',
              'target_date': '2026-08-01',
              'progress': 0.55,
              'mastery_level': 0.42,
              'daily_available_minutes': 50,
              'total_estimated_hours': 72.0,
              'is_active': true,
              'priority': 'high',
              'is_primary': true,
              'plan_stage': 'review',
              'task_count': 3,
              'completed_task_count': 1,
              'created_at': '2026-03-01T10:00:00Z',
              'updated_at': '2026-03-19T10:00:00Z',
              'source': 'learning_path',
              'source_metadata': {
                'target_node_id': 'node-1',
              },
            },
          ],
          'total': 1,
          'page': 1,
          'page_size': 20,
        },
      );
    };

    final plans = await repository.getPlans(
      type: PlanType.growth,
      isActive: true,
    );

    expect(plans, hasLength(1));
    expect(plans.first.name, '长期计划一');
    expect(plans.first.planStage, PlanStage.review);
    expect(plans.first.isPrimary, isTrue);
    expect(plans.first.source, 'learning_path');
  });

  test('demo mode plan mutations persist and keep growth experience rich', () async {
    DemoDataService.isDemoMode = true;
    final demoService = DemoDataService();

    final baselineGrowthCount = demoService.demoPlans
        .where((plan) => plan.type == PlanType.growth)
        .length;
    final archivedCount = demoService.demoPlans
        .where((plan) => !plan.isActive)
        .length;

    expect(baselineGrowthCount, greaterThanOrEqualTo(3));
    expect(archivedCount, greaterThanOrEqualTo(1));
    expect(
      demoService.demoPlans.any(
        (plan) => plan.type == PlanType.growth && (plan.tasks?.isNotEmpty ?? false),
      ),
      isTrue,
    );

    final created = await repository.createPlan(
      PlanCreate(
        name: 'Demo 新长期计划',
        type: PlanType.growth,
        dailyAvailableMinutes: 40,
        description: '游客新增的长期计划',
        subject: '数据库系统',
      ),
    );

    expect(demoService.demoPlans.any((plan) => plan.id == created.id), isTrue);

    final updated = await repository.updatePlan(
      created.id,
      PlanUpdate(
        name: 'Demo 新长期计划-更新',
        planStage: PlanStage.review,
      ),
    );
    expect(updated.name, 'Demo 新长期计划-更新');
    expect(updated.planStage, PlanStage.review);

    final generatedTasks = await repository.generateTasks(created.id, count: 2);
    expect(generatedTasks, hasLength(2));

    final refreshed = await repository.getPlan(created.id);
    expect(refreshed.tasks, isNotNull);
    expect(refreshed.tasks!, hasLength(2));

    await repository.archivePlan(created.id);
    expect((await repository.getPlan(created.id)).isActive, isFalse);

    await repository.restorePlan(created.id);
    expect((await repository.getPlan(created.id)).isActive, isTrue);
  });
}
