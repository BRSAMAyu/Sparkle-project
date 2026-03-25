import 'dart:developer';
// ignore_for_file: unused_field, inference_failure_on_function_invocation

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/shared/entities/task_model.dart';

/// 预测性服务 - 提供API集成和降级策略
class PredictiveService {
  PredictiveService(this._apiClient, this._demoDataService);
  final ApiClient _apiClient;
  final DemoDataService _demoDataService;

  /// 获取学习预测数据
  Future<Map<String, dynamic>> getLearningForecast() async {
    if (DemoDataService.isDemoMode) {
      return _getMockLearningForecast();
    }

    try {
      final response =
          await _apiClient.get<Map<String, dynamic>>('/predictive/engagement');
      return _unwrapPayload(
        response.data,
        action: 'getLearningForecast',
      );
    } catch (e) {
      log('学习预测接口调用失败: $e', name: 'PredictiveService');
      rethrow;
    }
  }

  /// 获取仪表板数据
  Future<Map<String, dynamic>> getDashboardData() async {
    if (DemoDataService.isDemoMode) {
      return _getMockDashboardData();
    }

    try {
      final response =
          await _apiClient.get<Map<String, dynamic>>('/predictive/dashboard');
      return _unwrapPayload(
        response.data,
        action: 'getDashboardData',
      );
    } catch (e) {
      log('预测仪表板接口调用失败: $e', name: 'PredictiveService');
      rethrow;
    }
  }

  /// 获取用户洞察数据
  Future<Map<String, dynamic>> getUserInsights() async {
    if (DemoDataService.isDemoMode) {
      return _getMockUserInsights();
    }

    try {
      final response =
          await _apiClient.get<Map<String, dynamic>>('/insights/user');
      return _unwrapPayload(response.data, action: 'getUserInsights');
    } catch (e) {
      log('用户洞察接口调用失败: $e', name: 'PredictiveService');
      rethrow;
    }
  }

  Map<String, dynamic> _unwrapPayload(
    Map<String, dynamic>? data, {
    required String action,
  }) {
    if (data == null) {
      throw StateError('PredictiveService $action returned null data');
    }

    final payload = data['data'];
    if (payload is Map<String, dynamic>) {
      return payload;
    }

    return data;
  }

  /// 模拟学习预测数据
  Map<String, dynamic> _getMockLearningForecast() {
    final demoTasks = _demoDataService.demoTasks;
    final afternoonTask = demoTasks.firstWhere(
      (task) => task.status == TaskStatus.inProgress,
      orElse: () => demoTasks.first,
    );
    return {
      'predictedMastery': 0.78,
      'confidenceInterval': [0.68, 0.87],
      'nextBestActions': [
        {
          'type': 'review',
          'priority': 'high',
          'description': '先复习《理工课复盘 - 用自己的话讲清楚积分换元》，再口头复述一遍关键步骤',
          'estimatedTime': 25,
        },
        {
          'type': 'practice',
          'priority': 'medium',
          'description': '晚上安排一轮《语言输出 - 口语话题卡 2 轮跟说》，把开口门槛降下来',
          'estimatedTime': 35,
        },
        {
          'type': 'reflect',
          'priority': 'low',
          'description': '在晚间复盘里记录今天学习节奏和分心点',
          'estimatedTime': 15,
        },
      ],
      'riskFactors': [
        {
          'factor': '周末动力下降',
          'severity': 'medium',
          'suggestion': '把周末早晨安排成低门槛复习时段',
        },
        {
          'factor': '连续高强度学习',
          'severity': 'low',
          'suggestion': '每 90 分钟安排一次 10 分钟离屏休息',
        },
      ],
      'timestamp': DateTime.now().toIso8601String(),
      'isMockData': true,
      'focusWindow': {
        'bestTime': '15:00-17:00',
        'reason': '历史上深度学习会话在下午最稳定',
      },
      'activeTask': {
        'id': afternoonTask.id,
        'title': afternoonTask.title,
        'estimatedMinutes': afternoonTask.estimatedMinutes,
      },
    };
  }

  /// 模拟仪表板数据
  Map<String, dynamic> _getMockDashboardData() {
    final dashboard = _demoDataService.demoDashboard;
    final tasks = _demoDataService.demoTasks;
    final focusSessions = _demoDataService.demoFocusSessions;
    final flame = dashboard['flame'] as Map<String, dynamic>;
    final growth = dashboard['growth'] as Map<String, dynamic>;
    return {
      'dailyStats': {
        'tasksCompleted': flame['tasks_completed'],
        'focusTime': flame['today_focus_minutes'],
        'learningProgress': growth['progress'],
      },
      'weeklyTrend': [0.46, 0.49, 0.53, 0.6, 0.66, 0.71, 0.74],
      'upcomingDeadlines': tasks
          .where((task) => task.dueDate != null && task.status != TaskStatus.completed)
          .take(3)
          .map(
            (task) => {
              'title': task.title,
              'dueDate': task.dueDate!.toIso8601String().split('T').first,
              'priority': task.priority >= 3 ? 'high' : 'medium',
            },
          )
          .toList(),
      'recentFocusSessions': focusSessions.take(3).toList(),
      'recommendations': [
        '今天下午最适合推进高认知任务，比如理工复盘或作品集重写',
        '先用 25 分钟清掉一个小任务，再进入深度工作',
        '晚上更适合语言复盘、阅读整理和轻量恢复动作',
      ],
      'isMockData': true,
    };
  }

  /// 模拟用户洞察数据
  Map<String, dynamic> _getMockUserInsights() {
    final behaviorPatterns = _demoDataService.demoBehaviorPatterns;
    final capsules = _demoDataService.demoCuriosityCapsules;
    return {
      'learningPatterns': {
        'bestTime': 'afternoon',
        'preferredSubject': 'multi_domain_growth',
        'averageSessionLength': 58,
        'weekendDrop': 0.35,
      },
      'strengths': [
        '会把不同领域的学习痕迹都留下来',
        '遇到卡点时愿意回到前置知识和更小的下一步',
        '对长期成长型任务有持续投入能力',
      ],
      'areasForImprovement': [
        '周末容易进入低动能状态',
        '有时会把复盘拖到太晚',
        '需要减少任务之间的切换成本',
      ],
      'personalizedTips': [
        '把下午 3 点后的时间留给理工课程、作品集重写和需要判断力的任务',
        '当你开始分心时，先完成一个 15 分钟的低门槛任务',
        '把每周复盘和错题回看固定到周日晚间，形成跨领域闭环',
      ],
      'behaviorPatterns': behaviorPatterns.map((item) => item.toJson()).toList(),
      'curiosityCapsules': capsules.take(3).map((item) => item.toJson()).toList(),
      'isMockData': true,
    };
  }

  /// 检查API可用性
  Future<bool> checkApiAvailability() async {
    try {
      await _apiClient.get('/health');
      return true;
    } catch (e) {
      return false;
    }
  }

  /// 获取服务状态
  Map<String, dynamic> getServiceStatus() => {
        'service': 'PredictiveService',
        'apiAvailable': true, // 简化处理
        'demoMode': DemoDataService.isDemoMode,
        'version': '1.0.0',
      };
}

/// Provider定义
final predictiveServiceProvider = Provider<PredictiveService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  final demoDataService = ref.watch(demoDataServiceProvider);
  return PredictiveService(apiClient, demoDataService);
});
