import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/charts/engagement_heatmap.dart';
import 'package:sparkle/core/services/predictive_service.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/insights/presentation/widgets/predictive_insights_card.dart';
import 'package:sparkle/features/reviews/presentation/widgets/nightly_review_panel.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';

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
  String? _errorMessage;
  Map<String, dynamic>? _dashboardData;
  Map<DateTime, double> _heatmapData = const <DateTime, double>{};

  @override
  void initState() {
    super.initState();
    unawaited(_loadDashboard());
  }

  Future<void> _loadDashboard() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final results = await Future.wait<dynamic>([
        ref.read(predictiveServiceProvider).getDashboardData(),
        ref.read(achievementRepositoryProvider).getStreakHistory(),
      ]);
      final response = results[0] as Map<String, dynamic>;
      final streakDays = results[1] as List<StreakDayRecord>;

      if (mounted) {
        setState(() {
          _dashboardData = response;
          _heatmapData = _buildHeatmapData(streakDays);
          _isLoading = false;
        });
      }
    } catch (e) {
      if (!mounted) {
        return;
      }
      setState(() {
        _isLoading = false;
        _errorMessage = '加载失败: $e';
      });
    }
  }

  Map<DateTime, double> _buildHeatmapData(List<StreakDayRecord> days) {
    if (days.isEmpty) {
      return const <DateTime, double>{};
    }

    return <DateTime, double>{
      for (final record in days)
        DateTime(record.day.year, record.day.month, record.day.day): switch (
            record.status) {
          StreakDayStatus.active => 1.0,
          StreakDayStatus.frozen => 0.55,
          StreakDayStatus.missed => 0.0,
        },
    };
  }

  @override
  Widget build(BuildContext context) => SparklePageScaffold(
        role: SparklePageRole.content,
        appBar: AppBar(
          leading: SparkleIconButton(
            icon: const Icon(Icons.arrow_back),
            onPressed: () => context.pop(),
            variant: ButtonVariant.ghost,
          ),
          backgroundColor: Colors.transparent,
          elevation: 0,
          title: Text('学习预测洞察', style: TextStyle(color: DS.textPrimary)),
          iconTheme: IconThemeData(color: DS.textPrimary),
          actions: [
            SparkleIconButton(
              icon: const Icon(Icons.refresh),
              onPressed: _loadDashboard,
              variant: ButtonVariant.ghost,
            ),
          ],
        ),
        child: _isLoading
            ? const Center(child: CircularProgressIndicator())
            : (_dashboardData == null
                ? ContentConstraint(
                    child: Center(
                      child: Padding(
                        padding: const EdgeInsets.all(DS.xl),
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(
                              Icons.insights_outlined,
                              size: 40,
                              color: DS.textSecondary,
                            ),
                            const SizedBox(height: DS.md),
                            Text(
                              _errorMessage ?? '预测数据暂时还没准备好',
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                color: DS.textPrimary,
                                fontSize: 16,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            const SizedBox(height: DS.sm),
                            Text(
                              '稍后重试，或者先完成几次学习与专注记录，让预测系统有足够数据可用。',
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                color: DS.textSecondary,
                                fontSize: 13,
                              ),
                            ),
                            const SizedBox(height: DS.lg),
                            FilledButton.icon(
                              onPressed: _loadDashboard,
                              icon: const Icon(Icons.refresh),
                              label: const Text('重新加载'),
                            ),
                          ],
                        ),
                      ),
                    ),
                  )
                : ContentConstraint(
                    child: RefreshIndicator(
                      onRefresh: _loadDashboard,
                      child: SingleChildScrollView(
                        physics: const AlwaysScrollableScrollPhysics(),
                        padding: const EdgeInsets.all(DS.lg),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            if (_errorMessage != null) ...[
                              Container(
                                width: double.infinity,
                                padding: const EdgeInsets.all(DS.md),
                                decoration: BoxDecoration(
                                  color: Theme.of(context)
                                      .colorScheme
                                      .errorContainer
                                      .withValues(alpha: 0.7),
                                  borderRadius: BorderRadius.circular(16),
                                ),
                                child: Text(
                                  _errorMessage!,
                                  style: TextStyle(
                                    color: Theme.of(context).colorScheme.error,
                                  ),
                                ),
                              ),
                              const SizedBox(height: DS.lg),
                            ],
                            // Header
                            _buildHeader(),
                            const SizedBox(height: DS.xl),

                            // Nightly Review
                            _buildSectionTitle('夜间复盘'),
                            const SizedBox(height: DS.md),
                            const NightlyReviewPanel(compact: true),
                            const SizedBox(height: DS.xl),

                            // Engagement Heatmap
                            _buildSectionTitle('学习活跃度分析'),
                            const SizedBox(height: DS.md),
                            EngagementHeatmap(
                              data: _heatmapData,
                              onDayTap: (date) => context.push(
                                '/calendar/day?date=${date.toIso8601String()}',
                              ),
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
                  )),
      );

  Widget _buildHeader() => MaterialStyler(
        material: AppMaterials.ceramic(context),
        borderRadius: DS.borderRadius20,
        padding: const EdgeInsets.all(DS.spacing20),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(DS.md),
              decoration: BoxDecoration(
                color: DS.brandPrimary10,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(Icons.auto_graph, color: DS.brandPrimary, size: 30),
            ),
            const SizedBox(width: DS.lg),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'AI 预测系统',
                    style: TextStyle(
                      color: DS.textPrimary,
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: DS.xs),
                  Text(
                    '基于学习数据的智能分析',
                    style: TextStyle(
                      color: DS.textSecondary,
                      fontSize: 14,
                    ),
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
          color: DS.textPrimary,
          fontSize: 18,
          fontWeight: FontWeight.bold,
        ),
      );

  Widget _buildOptimalTimeSection() {
    final optimalTime = _dashboardData?['optimal_time'];
    if (optimalTime == null) return const SizedBox.shrink();
    final optimalTimeMap = Map<String, dynamic>.from(
      optimalTime as Map<String, dynamic>,
    );

    final bestHours = (optimalTimeMap['best_hours'] as List? ?? const [])
        .map((item) => (item as num?)?.toInt() ?? 0)
        .toList(growable: false);
    final bestWeekdays = (optimalTimeMap['best_weekdays'] as List? ?? const [])
        .map((item) => (item as num?)?.toInt() ?? 0)
        .toList(growable: false);
    final reason = optimalTimeMap['reason']?.toString() ?? '';
    final sampleSize = (optimalTimeMap['sample_size'] as num?)?.toInt() ?? 0;
    final confidence = (optimalTimeMap['confidence'] as num?)?.toDouble() ?? 0;
    final dataStatus = optimalTimeMap['data_status']?.toString() ?? 'ok';
    final hasRecommendations = bestHours.isNotEmpty || bestWeekdays.isNotEmpty;

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
                Icon(
                  Icons.wb_sunny_outlined,
                  color: DS.warning,
                  size: 24,
                ),
                const SizedBox(width: DS.md),
                const Text(
                  '最佳学习时间',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: DS.lg),
            Text(
              hasRecommendations
                  ? '基于 $sampleSize 条学习记录，当前推荐置信度 ${(confidence * 100).round()}%。'
                  : (reason.isEmpty ? '还没有足够数据生成稳定推荐。' : reason),
              style: TextStyle(
                color: DS.textSecondary,
                fontSize: 13,
              ),
            ),
            if (!hasRecommendations) ...[
              const SizedBox(height: DS.md),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(DS.md),
                decoration: BoxDecoration(
                  color: DS.brandPrimary.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Text(
                  dataStatus == 'insufficient_data'
                      ? '先完成 3 次以上学习或专注记录，系统就会开始给出更个性化的时间窗口。'
                      : reason,
                  style: TextStyle(
                    color: DS.textSecondary,
                    fontSize: 13,
                    height: 1.4,
                  ),
                ),
              ),
            ],

            // Best Hours
            if (bestHours.isNotEmpty) ...[
              const SizedBox(height: DS.lg),
              const Text(
                '推荐学习时段',
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.w500),
              ),
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
                        padding:
                            const EdgeInsets.symmetric(horizontal: DS.spacing8),
                      ),
                    )
                    .toList(),
              ),
            ],

            // Best Weekdays
            if (bestWeekdays.isNotEmpty) ...[
              const SizedBox(height: DS.lg),
              const Text(
                '推荐学习日',
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.w500),
              ),
              const SizedBox(height: DS.sm),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: bestWeekdays
                    .map(
                      (day) => Chip(
                        label: Text(
                          _getWeekdayName(day),
                          style: const TextStyle(fontSize: 12),
                        ),
                        backgroundColor: DS.success.withValues(alpha: 0.1),
                        padding:
                            const EdgeInsets.symmetric(horizontal: DS.spacing8),
                      ),
                    )
                    .toList(),
              ),
            ],
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
                  Icon(
                    Icons.tips_and_updates,
                    color: DS.prismPurple.shade600,
                    size: 24,
                  ),
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
        padding: const EdgeInsets.only(bottom: DS.spacing8),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(Icons.arrow_right, color: DS.prismPurple.shade600, size: 20),
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
