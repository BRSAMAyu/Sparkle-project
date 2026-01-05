import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/predictive_service.dart';
import 'package:sparkle/presentation/widgets/charts/engagement_heatmap.dart';
import 'package:sparkle/presentation/widgets/insights/predictive_insights_card.dart';

/// 学习预测洞察屏幕 - 展示AI预测的学习趋势
///
/// 包含：
/// - 活跃度预测
/// - 最佳学习时间
/// - 流失风险评估
/// - 活跃度热力图（GitHub风格）
class LearningForecastScreen extends ConsumerStatefulWidget {
  const LearningForecastScreen({super.key});

  @override
  ConsumerState<LearningForecastScreen> createState() =>
      _LearningForecastScreenState();
}

class _LearningForecastScreenState
    extends ConsumerState<LearningForecastScreen> {
  bool _isLoading = true;
  Map<String, dynamic>? _dashboardData;

  @override
  void initState() {
    super.initState();
    _loadDashboard();
  }

  Future<void> _loadDashboard() async {
    setState(() => _isLoading = true);

    try {
      // API Integration: Fetch dashboard data with fallback to mock
      // See: lib/core/services/predictive_service.dart
      final response =
          await ref.read(predictiveServiceProvider).getDashboardData();

      if (mounted) {
        setState(() {
          _dashboardData = response;
          _isLoading = false;
        });
      }
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('加载失败: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: DS.deepSpaceStart,
        appBar: AppBar(
          backgroundColor: Colors.transparent,
          elevation: 0,
          title: Text('学习预测洞察', style: TextStyle(color: DS.brandPrimary)),
          iconTheme: IconThemeData(color: DS.brandPrimary),
          actions: [
            IconButton(
              icon: const Icon(Icons.refresh),
              onPressed: _loadDashboard,
            ),
          ],
        ),
        body: _isLoading
            ? const Center(child: CircularProgressIndicator())
            : RefreshIndicator(
                onRefresh: _loadDashboard,
                child: SingleChildScrollView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  padding: const EdgeInsets.all(DS.lg),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Header
                      _buildHeader(),
                      const SizedBox(height: DS.xl),

                      // Engagement Heatmap
                      _buildSectionTitle('学习活跃度分析'),
                      const SizedBox(height: DS.md),
                      const EngagementHeatmap(
                        data: <DateTime,
                            double>{}, // API Integration: Pass actual heatmap data
                      ),
                      const SizedBox(height: DS.xl),

                      // Insights Cards
                      _buildSectionTitle('AI 洞察'),
                      const SizedBox(height: DS.md),

                      // Engagement Forecast
                      PredictiveInsightsCard(
                        type: 'engagement',
                        data: (_dashboardData?['engagement_forecast']
                                as Map<String, dynamic>?) ??
                            {},
                      ),
                      const SizedBox(height: DS.lg),

                      // Risk Assessment
                      PredictiveInsightsCard(
                        type: 'risk',
                        data: (_dashboardData?['dropout_risk']
                                as Map<String, dynamic>?) ??
                            {},
                      ),
                      const SizedBox(height: DS.xl),

                      // Optimal Time Recommendation
                      _buildOptimalTimeSection(),
                      const SizedBox(height: DS.xl),

                      // Learning Tips
                      _buildLearningTips(),
                    ],
                  ),
                ),
              ),
      );

  Widget _buildHeader() => Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [
              DS.brandPrimary,
              DS.brandSecondary,
            ],
          ),
          borderRadius: BorderRadius.circular(16),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(DS.md),
              decoration: BoxDecoration(
                color: DS.brandPrimary.withValues(alpha: 0.2),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(Icons.auto_graph, color: DS.brandPrimary, size: 32),
            ),
            const SizedBox(width: DS.lg),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'AI 预测系统',
                    style: TextStyle(
                      color: DS.brandPrimary,
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: DS.xs),
                  Text(
                    '基于学习数据的智能分析',
                    style: TextStyle(
                        color: DS.brandPrimary.withValues(alpha: 0.7),
                        fontSize: 14,),
                  ),
                ],
              ),
            ),
          ],
        ),
      );

  Widget _buildSectionTitle(String title) => Text(
        title,
        style: TextStyle(
          color: DS.brandPrimary,
          fontSize: 18,
          fontWeight: FontWeight.bold,
        ),
      );

  Widget _buildOptimalTimeSection() {
    final optimalTime = _dashboardData?['optimal_time'];
    if (optimalTime == null) return const SizedBox.shrink();

    final bestHours = optimalTime['best_hours'] as List? ?? [];
    final bestWeekdays = optimalTime['best_weekdays'] as List? ?? [];

    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(DS.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.wb_sunny_outlined,
                    color: Colors.amber.shade700, size: 24,),
                const SizedBox(width: DS.md),
                const Text(
                  '最佳学习时间',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: DS.lg),

            // Best Hours
            const Text('推荐学习时段',
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.w500),),
            const SizedBox(height: DS.sm),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: bestHours
                  .map(
                    (hour) => Chip(
                      label: Text(
                        '$hour:00-${hour + 1}:00',
                        style: const TextStyle(fontSize: 12),
                      ),
                      backgroundColor: DS.brandPrimary.withValues(alpha: 0.1),
                      padding: const EdgeInsets.symmetric(horizontal: 8),
                    ),
                  )
                  .toList(),
            ),
            const SizedBox(height: DS.lg),

            // Best Weekdays
            const Text('推荐学习日',
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.w500),),
            const SizedBox(height: DS.sm),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: bestWeekdays
                  .map(
                    (day) => Chip(
                      label: Text(
                        _getWeekdayName(day as int),
                        style: const TextStyle(fontSize: 12),
                      ),
                      backgroundColor: DS.success.withValues(alpha: 0.1),
                      padding: const EdgeInsets.symmetric(horizontal: 8),
                    ),
                  )
                  .toList(),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLearningTips() => Card(
        elevation: 2,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        child: Padding(
          padding: const EdgeInsets.all(DS.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(Icons.tips_and_updates,
                      color: Colors.purple.shade600, size: 24,),
                  const SizedBox(width: DS.md),
                  const Text(
                    '学习建议',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                ],
              ),
              const SizedBox(height: DS.md),
              _buildTip('根据历史数据，您在早上9点学习效果最佳'),
              _buildTip('周一到周四是您的高产学习日'),
              _buildTip('建议每次学习 30-45 分钟，然后休息 5-10 分钟'),
            ],
          ),
        ),
      );

  Widget _buildTip(String text) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(Icons.arrow_right, color: Colors.purple.shade600, size: 20),
            const SizedBox(width: DS.sm),
            Expanded(
              child: Text(text, style: const TextStyle(fontSize: 14)),
            ),
          ],
        ),
      );

  String _getWeekdayName(int day) {
    const weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
    return weekdays[day];
  }
}
