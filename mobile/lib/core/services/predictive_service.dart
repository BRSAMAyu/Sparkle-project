import 'dart:developer';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/demo_data_service.dart';

/// 预测性服务 - 提供API集成和降级策略
class PredictiveService {
  PredictiveService(this._apiClient, this._demoDataService);
  final ApiClient _apiClient;
  final DemoDataService _demoDataService;

  /// 获取学习预测数据
  Future<Map<String, dynamic>> getLearningForecast() async {
    try {
      // 尝试调用真实API
      final response = await _apiClient
          .get<Map<String, dynamic>>('/api/v1/predictive/learning-forecast');
      return response.data ?? _getMockLearningForecast();
    } catch (e) {
      log('API调用失败，使用模拟数据: $e', name: 'PredictiveService');

      // 降级到模拟数据
      return _getMockLearningForecast();
    }
  }

  /// 获取仪表板数据
  Future<Map<String, dynamic>> getDashboardData() async {
    try {
      final response =
          await _apiClient.get<Map<String, dynamic>>('/api/v1/dashboard');
      return response.data ?? _getMockDashboardData();
    } catch (e) {
      log('API调用失败，使用模拟数据: $e', name: 'PredictiveService');

      // 降级到模拟数据
      return _getMockDashboardData();
    }
  }

  /// 获取用户洞察数据
  Future<Map<String, dynamic>> getUserInsights() async {
    try {
      final response =
          await _apiClient.get<Map<String, dynamic>>('/api/v1/insights/user');
      return response.data ?? _getMockUserInsights();
    } catch (e) {
      log('API调用失败，使用模拟数据: $e', name: 'PredictiveService');

      // 降级到模拟数据
      return _getMockUserInsights();
    }
  }

  /// 模拟学习预测数据
  Map<String, dynamic> _getMockLearningForecast() => {
        'predictedMastery': 0.75,
        'confidenceInterval': [0.65, 0.85],
        'nextBestActions': [
          {
            'type': 'review',
            'priority': 'high',
            'description': '复习昨天的学习内容',
            'estimatedTime': 30,
          },
          {
            'type': 'practice',
            'priority': 'medium',
            'description': '完成练习题',
            'estimatedTime': 45,
          },
        ],
        'riskFactors': [
          {
            'factor': '注意力分散',
            'severity': 'medium',
            'suggestion': '尝试专注模式',
          },
        ],
        'timestamp': DateTime.now().toIso8601String(),
        'isMockData': true, // 标记为模拟数据
      };

  /// 模拟仪表板数据
  Map<String, dynamic> _getMockDashboardData() => {
        'dailyStats': {
          'tasksCompleted': 8,
          'focusTime': 120, // 分钟
          'learningProgress': 0.65,
        },
        'weeklyTrend': [0.4, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75],
        'upcomingDeadlines': [
          {
            'title': '数学期末考试',
            'dueDate': '2025-01-15',
            'priority': 'high',
          },
          {
            'title': '项目报告',
            'dueDate': '2025-01-20',
            'priority': 'medium',
          },
        ],
        'recommendations': [
          '今天适合复习数学',
          '建议安排45分钟专注学习',
          '检测到注意力下降趋势',
        ],
        'isMockData': true,
      };

  /// 模拟用户洞察数据
  Map<String, dynamic> _getMockUserInsights() => {
        'learningPatterns': {
          'bestTime': 'morning',
          'preferredSubject': 'mathematics',
          'averageSessionLength': 45,
        },
        'strengths': [
          '逻辑推理能力强',
          '记忆力优秀',
          '专注力持久',
        ],
        'areasForImprovement': [
          '需要提高写作速度',
          '可以尝试更多实践练习',
          '建议增加休息频率',
        ],
        'personalizedTips': [
          '根据你的学习模式，建议早上学习数学',
          '检测到下午注意力下降，建议安排轻松任务',
          '你的最佳学习时长是45分钟，建议设置番茄钟',
        ],
        'isMockData': true,
      };

  /// 检查API可用性
  Future<bool> checkApiAvailability() async {
    try {
      await _apiClient.get('/api/v1/health');
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
