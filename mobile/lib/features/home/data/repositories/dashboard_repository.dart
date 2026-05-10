import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/errors/failures.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/core/services/i18n_service.dart';

final dashboardRepositoryProvider = Provider<DashboardRepository>(
  (ref) => DashboardRepository(ref.read(apiClientProvider)),
);

class DashboardRepository {
  DashboardRepository(this._apiClient);
  final ApiClient _apiClient;

  static const List<String> _growthDashboardKeys = [
    'growth_status',
    'most_important_task',
    'growth_signal',
    'active_plan_progress',
  ];

  Map<String, dynamic> _extractGrowthSnapshot(Map<String, dynamic> payload) {
    final snapshot = <String, dynamic>{};
    for (final key in _growthDashboardKeys) {
      if (payload.containsKey(key)) {
        snapshot[key] = payload[key];
      }
    }
    return snapshot;
  }

  Future<Map<String, dynamic>> getDashboardStatus() async {
    if (DemoDataService.isDemoMode) {
      return DemoDataService().demoDashboard;
    }
    try {
      final response =
          await _apiClient.get<dynamic>(ApiEndpoints.dashboardStatus);
      return ApiResponseParser.unwrapMap(
        response.data,
        action: 'getDashboardStatus',
      );
    } catch (error) {
      throw AppFailureMapper.from(
        error,
        fallbackMessage: 'Could not load dashboard.',
      );
    }
  }

  Future<Map<String, dynamic>> getGrowthDashboard() async {
    if (DemoDataService.isDemoMode) {
      return _extractGrowthSnapshot(DemoDataService().demoDashboard);
    }
    try {
      final response =
          await _apiClient.get<dynamic>(ApiEndpoints.growthDashboard);
      return ApiResponseParser.unwrapMap(
        response.data,
        action: 'getGrowthDashboard',
      );
    } catch (error) {
      throw AppFailureMapper.from(
        error,
        fallbackMessage: 'Could not load growth dashboard.',
      );
    }
  }

  Future<Map<String, dynamic>> getExamSprintDashboard() async {
    if (DemoDataService.isDemoMode) {
      final l10n = I18nService.instance.l10n;
      final today = DateTime.now();
      final tomorrow = today.add(const Duration(days: 1));
      return {
        'active': true,
        'plan_id': 'demo-exam-sprint-plan',
        'plan_name': l10n.dashboardPlanName,
        'subject': l10n.dashboardSubject,
        'days_left': 5,
        'target_mode': 'pass',
        'estimated_score_now': 71.0,
        'baseline_estimated_score': 54.0,
        'pass_probability': 0.76,
        'baseline_pass_probability': 0.42,
        'today_progress': {
          'completed': 2,
          'total': 3,
          'completion_rate': 0.6667,
        },
        'high_freq_coverage': 0.72,
        'high_freq_covered_count': 13,
        'high_freq_total_count': 18,
        'mistake_fix_rate': 0.68,
        'fixed_mistake_count': 17,
        'total_mistake_count': 25,
        'streak_days': 9,
        'high_yield_low_mastery_topics': [
          l10n.dashboardTopicReliableTransport,
          l10n.dashboardTopicTcpCongestion
        ],
        'task_groups': [
          {
            'day_index': 1,
            'date': today.toIso8601String(),
            'is_today': true,
            'completed_count': 2,
            'total_count': 3,
            'tasks': [
              {
                'id': 'demo-sprint-task-1',
                'title': zh
                    ? '闭卷默写 TCP 三次握手与四次挥手'
                    : 'Closed-book: TCP 3-way handshake & 4-way teardown',
                'status': 'COMPLETED',
                'estimated_minutes': 25,
                'is_completed': true,
              },
              {
                'id': 'demo-sprint-task-2',
                'title': zh
                    ? '订正 3 道可靠传输错题'
                    : 'Correct 3 reliable transport mistakes',
                'status': 'COMPLETED',
                'estimated_minutes': 20,
                'is_completed': true,
              },
              {
                'id': 'demo-sprint-task-3',
                'title': zh
                    ? '口述拥塞控制四阶段并自测'
                    : 'Explain 4 congestion control phases & self-test',
                'status': 'PENDING',
                'estimated_minutes': 30,
                'is_completed': false,
              },
            ],
          },
          {
            'day_index': 2,
            'date': tomorrow.toIso8601String(),
            'is_today': false,
            'completed_count': 0,
            'total_count': 2,
            'tasks': [
              {
                'id': 'demo-sprint-task-4',
                'title': zh
                    ? '整理高频考点保底清单'
                    : 'Compile high-frequency exam topic checklist',
                'status': 'PENDING',
                'estimated_minutes': 35,
                'is_completed': false,
              },
              {
                'id': 'demo-sprint-task-5',
                'title': zh
                    ? '做一组路由算法选择题'
                    : 'Complete a set of routing algorithm MCQs',
                'status': 'PENDING',
                'estimated_minutes': 30,
                'is_completed': false,
              },
            ],
          },
        ],
      };
    }
    try {
      final response =
          await _apiClient.get<dynamic>(ApiEndpoints.examSprintDashboard);
      return ApiResponseParser.unwrapMap(
        response.data,
        action: 'getExamSprintDashboard',
      );
    } catch (error) {
      throw AppFailureMapper.from(
        error,
        fallbackMessage: 'Could not load exam sprint dashboard.',
      );
    }
  }

  Future<Map<String, dynamic>> getPredictiveDashboard() async {
    if (DemoDataService.isDemoMode) {
      final zh = I18nService.instance.isChinese;
      return {
        'engagement_forecast': {
          'forecast_type': 'engagement',
          'trend': 'slightly_up',
          'confidence': 0.76,
          'summary': zh
              ? '未来 24 小时内保持较高活跃度的概率较大，但晚间会有轻微回落。'
              : 'High engagement likely in the next 24 hours, with a slight dip in the evening.',
          'signals': [
            zh
                ? '最近三次专注会话都发生在下午'
                : 'Last 3 focus sessions were all in the afternoon',
            zh
                ? '错题本和星图节点的回看频率在上升'
                : 'Error book & galaxy node review frequency is rising',
            zh
                ? '周末动能略低于工作日'
                : 'Weekend momentum is slightly lower than weekdays',
          ],
        },
        'dropout_risk': {
          'risk_level': 'low_to_medium',
          'confidence': 0.34,
          'summary': zh
              ? '当前没有明显流失风险，但如果连续两天没有专注记录，风险会抬升。'
              : 'No significant dropout risk now, but it will rise if you skip two consecutive days of focus.',
          'factors': [
            zh ? '近期任务较多' : 'Many recent tasks',
            zh ? '存在少量未完成任务' : 'Some incomplete tasks remain',
            zh ? '晚间学习容易被打断' : 'Evening study sessions are easily interrupted',
          ],
        },
        'optimal_time': {
          'best_hours': [15, 16, 17, 20],
          'best_weekdays': ['monday', 'tuesday', 'wednesday', 'thursday'],
          'summary': zh
              ? '下午 3 点到 5 点是你最稳定的学习窗口，晚上适合做收尾与复盘。'
              : '3–5 PM is your most stable study window; evenings are best for wrap-ups and reviews.',
        },
        'next_intent_forecast': {
          'schema_version': 'prediction.v1',
          'prediction_id': 'demo-prediction-next-intent',
          'horizon': 'long_horizon',
          'title': zh
              ? '系统预测你接下来会继续推进最关键任务'
              : 'Prediction: you\'ll continue pushing your most critical task',
          'summary': zh
              ? '根据最近 24 小时的节奏，先推进当前重点任务最合适。'
              : 'Based on the last 24 hours, tackling your current priority task makes the most sense.',
          'confidence': 0.72,
          'predicted_action_type': 'resume_priority_task',
          'predicted_window': 'next_2h',
          'reasons': [
            zh ? '最近24小时持续活跃' : 'Active in the last 24 hours',
            zh ? '当前仍有重点待办' : 'Priority tasks still pending'
          ],
          'suggested_prompt': zh
              ? '帮我继续推进今天最关键的任务'
              : 'Help me continue today\'s most critical task',
          'prediction_source': 'rules',
          'prediction_tier': 'rules',
          'fallback_used': true,
          'explanations': {
            'recent_24h': [zh ? '最近24小时持续活跃' : 'Active in the last 24 hours'],
            'recent_7d': [
              zh ? '过去7天保持稳定推进' : 'Steady progress over the past 7 days'
            ],
            'profile': [
              zh
                  ? '你更容易承接已有重点任务'
                  : 'You tend to pick up existing priority tasks'
            ],
            'plan': [zh ? '当前仍有重点待办' : 'Priority tasks still pending'],
            'focus': [
              zh
                  ? '先推进一个25分钟小段更自然'
                  : 'A 25-minute focused block feels natural first'
            ],
          },
          'recommended_actions': [
            {
              'id': 'demo-prediction-next-intent:primary',
              'label': zh ? '继续重点任务' : 'Continue Priority Task',
              'action_type': 'resume_priority_task',
              'target_route': '/chat',
              'suggested_prompt': zh
                  ? '帮我继续推进今天最关键的任务'
                  : 'Help me continue today\'s most critical task',
              'resource_type': 'chat',
              'resource_id': null,
              'surface': 'dashboard',
            },
            {
              'id': 'demo-prediction-next-intent:secondary',
              'label': zh ? '先做 25 分钟' : 'Start a 25-min Focus',
              'action_type': 'start_pomodoro',
              'target_route': '/focus',
              'suggested_prompt': zh
                  ? '先帮我把今天最重要的任务拆成 25 分钟专注块'
                  : 'Break today\'s most important task into 25-minute focus blocks',
              'resource_type': 'focus',
              'resource_id': null,
              'surface': 'dashboard',
            },
          ],
          'tracking': {
            'candidate_id': 'demo-prediction-next-intent',
            'action_type': 'resume_priority_task',
            'surface': 'dashboard',
          },
          'generated_at': DateTime.now().toIso8601String(),
        },
      };
    }
    try {
      final response =
          await _apiClient.get<dynamic>(ApiEndpoints.predictiveDashboard);
      return ApiResponseParser.unwrapMap(
        response.data,
        action: 'getPredictiveDashboard',
      );
    } catch (error) {
      throw AppFailureMapper.from(
        error,
        fallbackMessage: 'Could not load predictive dashboard.',
      );
    }
  }
}
