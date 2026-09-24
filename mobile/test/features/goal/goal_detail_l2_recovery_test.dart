import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/theme/sparkle_theme_extension.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/features/goal/presentation/screens/goal_detail_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';

class _StubApiClient implements ApiClient {
  _StubApiClient(this.goalDetailPayload);

  final Map<String, dynamic> goalDetailPayload;

  @override
  Dio get dio => Dio();

  @override
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    if (path.contains('/experience/goal-detail/')) {
      return Response<T>(
        data: goalDetailPayload as T?,
        requestOptions: RequestOptions(path: path),
      );
    }
    // 与 goal_detail_screen_a6_l10n_test 同款约定：未 stub 的端点走
    // provider 错误路径，对应卡面按设计渲染空态。
    throw UnimplementedError('Not stubbed: $path');
  }

  @override
  Stream<SSEEvent> getStream(
    String path, {
    Map<String, dynamic>? headers,
    Map<String, dynamic>? queryParameters,
  }) =>
      const Stream<SSEEvent>.empty();

  @override
  Stream<SSEEvent> postStream(String path, {Object? data}) =>
      const Stream<SSEEvent>.empty();

  @override
  Future<Response<T>> post<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async {
    throw UnimplementedError('Not stubbed: $path');
  }

  @override
  Future<Response<T>> put<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async {
    throw UnimplementedError('Not stubbed: $path');
  }

  @override
  Future<Response<T>> patch<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async {
    throw UnimplementedError('Not stubbed: $path');
  }

  @override
  Future<Response<T>> delete<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async {
    throw UnimplementedError('Not stubbed: $path');
  }
}

/// U-05 Goal 屏 L2：GOAL.md 屏面契约补全的回归锚点——
/// 1. 「当前里程碑」从 plan health 角标提级为 header 下的独立条；
/// 2. `重新规划` / `我卡住了` 两个恢复入口落位屏面末尾（J-05 统一恢复
///    旅程的 goal 落点 + J-07 计划重校准的直达通道）。
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUpAll(() async {
    SharedPreferences.setMockInitialValues({});
    await ViewStorageService.ensureInitialized();
  });

  testWidgets(
    'milestone strip renders current phase and recovery actions are present',
    (tester) async {
      final stub = _StubApiClient(<String, dynamic>{
        'goal': <String, dynamic>{
          'id': 'g9',
          'title': 'Operating systems final sprint',
          'goal_type': 'exam',
          'status': 'active',
          'target_date': '2099-12-31',
          'mastery': 0.4,
          'progress': 0.5,
          'priority': 'high',
        },
        'minimum_acceptance_criteria': <String, dynamic>{},
        'plan_health': <String, dynamic>{
          'overall': 0.6,
          'phase_health': 0.72,
          'task_completion_rate': 0.5,
        },
        'current_phase': <String, dynamic>{
          'name': '强化冲刺',
          'progress': 0.4,
        },
        'todays_minimal_next_step': <String, dynamic>{},
        'knowledge_bottlenecks': <dynamic>[],
        'accountability_status': <String, dynamic>{},
        'related_sources': <dynamic>[],
      });

      await tester.binding.setSurfaceSize(const Size(800, 2400));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            apiClientProvider.overrideWithValue(stub),
          ],
          child: MaterialApp(
            theme: ThemeData(extensions: [SparkleThemeExtension.light()]),
            locale: const Locale('en'),
            supportedLocales: const [Locale('en'), Locale('zh')],
            localizationsDelegates: const [AppLocalizations.delegate],
            home: const GoalDetailScreen(goalId: 'g9'),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Milestone 提级：独立条存在，标题 + 真实 phase 名 + phaseHealth
      // 百分比（72% 同值也会出现在 plan health 带，故用 findsWidgets）。
      expect(
        find.byKey(const ValueKey('goal-detail-milestone-strip')),
        findsOneWidget,
      );
      expect(find.text('Current milestone'), findsOneWidget);
      expect(find.text('强化冲刺'), findsOneWidget);
      expect(find.text('72%'), findsWidgets);

      // 恢复入口（GOAL.md 收尾两项）。
      expect(
        find.byKey(const ValueKey('goal-detail-replan-action')),
        findsOneWidget,
      );
      expect(
        find.byKey(const ValueKey('goal-detail-stuck-action')),
        findsOneWidget,
      );
      expect(find.text('Replan'), findsOneWidget);
      expect(find.text("I'm stuck"), findsOneWidget);
    },
  );
}
