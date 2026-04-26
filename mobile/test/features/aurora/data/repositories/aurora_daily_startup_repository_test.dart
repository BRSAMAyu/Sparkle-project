import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/aurora/data/repositories/aurora_daily_startup_repository.dart';

class _FakeApiClient implements ApiClient {
  @override
  Dio get dio => throw UnimplementedError();

  @override
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) {
    throw UnimplementedError('Demo test should not call the API');
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  setUp(() {
    DemoDataService.isDemoMode = true;
    DemoDataService().resetDemoState();
  });

  tearDown(() {
    DemoDataService.isDemoMode = false;
    DemoDataService().resetDemoState();
  });

  test('demo daily startup follows selected demo plan instead of TCP copy',
      () async {
    final repository = AuroraDailyStartupRepository(_FakeApiClient());

    final startup = await repository.getDailyStartup(planId: 'plan_growth_2');

    expect(startup.message, contains('语言表达'));
    expect(startup.todayFocus, isNot(contains('TCP')));
    expect(startup.message, isNot(contains('计算机网络')));
    expect(startup.message, isNot(contains('TCP 流量控制')));
  });
}
