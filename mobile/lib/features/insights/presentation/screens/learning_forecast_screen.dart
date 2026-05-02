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
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';

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
        _errorMessage = context.l10n.insLoadFailed(e.toString());
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
          title: Text(context.l10n.insForecastTitle, style: TextStyle(color: DS.textPrimary)),
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
                              _errorMessage ?? context.l10n.insForecastEmpty,
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                color: DS.textPrimary,
                                fontSize: 16,
                                fontWeight: DS.fontWeightSemibold,
                              ),
                            ),
                            const SizedBox(height: DS.sm),
                            Text(
                              I18nService.instance.isChinese ? '稍后重试，或者先完成几次学习与专注记录，让预测系统有足够数据可用。' : 'Try again later, or complete a few learning and focus sessions so the prediction system has enough data.',
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
                              label: Text(context.l10n.insReload),
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
                            _buildSectionTitle(context.l10n.insNightReview),
                            const SizedBox(height: DS.md),
                            const NightlyReviewPanel(compact: true),
                            const SizedBox(height: DS.xl),

                            // Engagement Heatmap
                            _buildSectionTitle(context.l10n.insActivityAnalysis),
                            const SizedBox(height: DS.md),
                            EngagementHeatmap(
                              data: _heatmapData,
                              onDayTap: (date) => context.push(
                                '/calendar/day?date=${date.toIso8601String()}',
                              ),
                            ),
                            const SizedBox(height: DS.xl),

                            // Insights Cards
                            _buildSectionTitle(context.l10n.insAiInsights),
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
                    I18nService.instance.isChinese ? 'AI 预测系统' : 'AI Prediction System',
                    style: TextStyle(
                      color: DS.textPrimary,
                      fontSize: 20,
                      fontWeight: DS.fontWeightBold,
                    ),
                  ),
                  const SizedBox(height: DS.xs),
                  Text(
                    I18nService.instance.isChinese ? '基于学习数据的智能分析' : 'Smart analysis based on learning data',
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
          fontWeight: DS.fontWeightBold,
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
                Text(
                  I18nService.instance.isChinese ? '最佳学习时间' : 'Best Learning Time',
                  style: TextStyle(fontSize: 16, fontWeight: DS.fontWeightBold),
                ),
              ],
            ),
            const SizedBox(height: DS.lg),
            Text(
              hasRecommendations
                  ? context.l10n.lfcConfidence(sampleSize, (confidence * 100).round().toString())
                  : (reason.isEmpty ? context.l10n.insNotEnoughData : reason),
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
                      ? (I18nService.instance.isChinese ? '先完成 3 次以上学习或专注记录，系统就会开始给出更个性化的时间窗口。' : 'Complete 3+ learning or focus sessions first, and the system will provide more personalized time windows.')
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
              Text(
                I18nService.instance.isChinese ? '推荐学习时段' : 'Recommended Learning Hours',
                style: TextStyle(fontSize: 14, fontWeight: DS.fontWeightMedium),
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
              Text(
                I18nService.instance.isChinese ? '推荐学习日' : 'Recommended Learning Days',
                style: TextStyle(fontSize: 14, fontWeight: DS.fontWeightMedium),
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
                  Text(
                    I18nService.instance.isChinese ? '学习建议' : 'Learning Tips',
                    style: TextStyle(fontSize: 16, fontWeight: DS.fontWeightBold),
                  ),
                ],
              ),
              const SizedBox(height: DS.md),
              _buildTip(context.l10n.lfcTipMorning),
              _buildTip(I18nService.instance.isChinese ? '周一到周四是您的高产学习日' : 'Mon-Thu are your peak learning days'),
              _buildTip(context.l10n.lfcTipPomodoro),
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
    final zh = I18nService.instance.isChinese;
    final weekdays = zh
        ? ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        : ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    return weekdays[day];
  }
}
