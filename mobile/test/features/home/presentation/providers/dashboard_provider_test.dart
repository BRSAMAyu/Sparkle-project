import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/home/data/repositories/dashboard_repository.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';

class _FakeDashboardRepository extends DashboardRepository {
  _FakeDashboardRepository(this._handler) : super(_UnusedApiClient());

  final Future<Map<String, dynamic>> Function() _handler;

  @override
  Future<Map<String, dynamic>> getDashboardStatus() => _handler();
}

class _UnusedApiClient implements ApiClient {
  @override
  Dio get dio => throw UnimplementedError();

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  group('DashboardNotifier', () {
    test('fetchData parses dashboard payload and updates weather state',
        () async {
      final notifier = DashboardNotifier(
        _FakeDashboardRepository(
          () async => {
            'weather': {'type': 'rainy', 'condition': '检测到焦虑'},
            'flame': {
              'level': 4,
              'brightness': 0.75,
              'today_focus_minutes': 45,
            },
            'sprint': {
              'id': 'sprint-1',
              'name': '冲刺计划',
              'progress': 0.6,
              'days_left': 3,
              'total_estimated_hours': 12.5,
            },
            'growth': null,
            'next_actions': [
              {
                'id': 'task-1',
                'title': '复习图论',
                'estimated_minutes': 40,
                'priority': 3,
                'type': 'LEARNING',
              },
            ],
            'cognitive': {
              'status': 'new',
              'weekly_pattern': 'night_owl',
              'pattern_type': 'focus',
              'description': '夜间专注更强',
              'solution_text': '把高强度任务放到晚上',
              'has_new_insight': true,
            },
            'what_changed_card': {
              'headline': '最近真正有变化的是推进质量，不只是更忙了。',
              'summary': '系统注意到你开始在薄弱点上出现真实进展。',
              'highlights': ['系统注意到你开始在薄弱点上出现真实进展。', '最近 7 天连续推进。'],
              'timeframe_label': '最近 7 天',
            },
            'next_move_card': {
              'headline': '下一步先做「复习图论」',
              'summary': '这一步最直接对应当前缺口。',
              'why_now': '因为它最直接对应你现在还没补稳的薄弱点。',
              'reassurance': '如果今天状态不稳，我们也可以把它再拆小。',
              'task_id': 'task-1',
              'estimated_minutes': 40,
              'plan_name': '冲刺计划',
              'days_to_deadline': 3,
            },
          },
        ),
      );
      addTearDown(notifier.dispose);

      await notifier.fetchData();

      expect(notifier.state.error, isNull);
      expect(notifier.state.isLoading, isFalse);
      expect(notifier.state.weather.type, 'rainy');
      expect(notifier.state.weather.condition, '检测到焦虑');
      expect(notifier.state.flame.todayFocusMinutes, 45);
      expect(notifier.state.nextActions, hasLength(1));
      expect(notifier.state.nextActions.first.type, 'LEARNING');
      expect(notifier.state.cognitive.hasNewInsight, isTrue);
      expect(notifier.state.whatChangedCard?.timeframeLabel, '最近 7 天');
      expect(notifier.state.nextMoveCard?.taskId, 'task-1');
    });

    test('fetchData surfaces failures as error state instead of hanging',
        () async {
      final notifier = DashboardNotifier(
        _FakeDashboardRepository(() async {
          throw Exception('dashboard unavailable');
        }),
      );
      addTearDown(notifier.dispose);

      await notifier.fetchData();

      expect(notifier.state.isLoading, isFalse);
      expect(notifier.state.error, contains('dashboard unavailable'));
    });
  });
}
