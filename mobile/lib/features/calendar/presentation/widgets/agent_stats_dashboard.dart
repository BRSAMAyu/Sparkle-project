import 'package:fl_chart/fl_chart.dart';
// ignore_for_file: avoid_dynamic_calls

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/chat/data/models/reasoning_step_model.dart';
import 'package:sparkle/features/chat/presentation/widgets/agent_avatar_switcher.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

/// Agent协作统计面板
///
/// 展示用户的Multi-Agent使用情况：
/// - 各Agent使用频率饼图
/// - Top 5最常用Agent卡片
/// - 性能指标趋势图
class AgentStatsDashboard extends StatelessWidget {
  const AgentStatsDashboard({
    required this.statsData,
    super.key,
  });
  final Map<String, dynamic> statsData;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final overall = statsData['overall'] as Map<String, dynamic>? ?? {};
    final byAgent = statsData['by_agent'] as List<dynamic>? ?? [];

    return SingleChildScrollView(
      padding: const EdgeInsets.all(DS.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Text(
            I18nService.instance.isChinese ? 'Agent 协作统计' : 'Agent Collaboration Stats',
            style: theme.textTheme.headlineSmall?.copyWith(
              fontWeight: DS.fontWeightBold,
            ),
          ),
          const SizedBox(height: DS.sm),
          Text(
            I18nService.instance.isChinese
                ? '过去 ${statsData['period_days'] ?? 30} 天'
                : 'Past ${statsData['period_days'] ?? 30} days',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: DS.xl),

          // Overall Stats Cards
          _buildOverallStats(context, theme, overall),
          const SizedBox(height: DS.xl),

          // Usage Pie Chart
          if (byAgent.isNotEmpty) ...[
            Text(
              I18nService.instance.isChinese ? 'Agent 使用分布' : 'Agent Usage Distribution',
              style: theme.textTheme.titleLarge?.copyWith(
                fontWeight: DS.fontWeightBold,
              ),
            ),
            const SizedBox(height: DS.lg),
            _buildUsagePieChart(context, theme, byAgent),
            const SizedBox(height: DS.xl),
          ],

          // Top Agents List
          if (byAgent.isNotEmpty) ...[
            Text(
              I18nService.instance.isChinese ? '常用 Agent' : 'Top Agents',
              style: theme.textTheme.titleLarge?.copyWith(
                fontWeight: DS.fontWeightBold,
              ),
            ),
            const SizedBox(height: DS.lg),
            ...byAgent.take(5).map((agent) => _buildAgentCard(context, theme, agent)),
          ],
        ],
      ),
    );
  }

  Widget _buildOverallStats(BuildContext context, ThemeData theme, Map<String, dynamic> overall) =>
      Row(
        children: [
          Expanded(
            child: _buildStatCard(
              theme,
              title: context.l10n.calTotalExecutions,
              value: '${overall['total_executions'] ?? 0}',
              icon: Icons.sync_alt,
              color: DS.brandPrimaryConst,
            ),
          ),
          const SizedBox(width: DS.md),
          Expanded(
            child: _buildStatCard(
              theme,
              title: context.l10n.calAvgDuration,
              value: '${overall['avg_duration_ms'] ?? 0}ms',
              icon: Icons.timer,
              color: DS.brandPrimaryConst,
            ),
          ),
          const SizedBox(width: DS.md),
          Expanded(
            child: _buildStatCard(
              theme,
              title: context.l10n.calSessionCount,
              value: '${overall['total_sessions'] ?? 0}',
              icon: Icons.chat_bubble_outline,
              color: DS.success,
            ),
          ),
        ],
      );

  Widget _buildStatCard(
    ThemeData theme, {
    required String title,
    required String value,
    required IconData icon,
    required Color color,
  }) =>
      Container(
        padding: const EdgeInsets.all(DS.lg),
        decoration: BoxDecoration(
          color: theme.colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: color.withValues(alpha: 0.3),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: color, size: 24),
            const SizedBox(height: DS.sm),
            Text(
              value,
              style: theme.textTheme.headlineSmall?.copyWith(
                fontWeight: DS.fontWeightBold,
                color: color,
              ),
            ),
            const SizedBox(height: DS.xs),
            Text(
              title,
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
      );

  Widget _buildUsagePieChart(BuildContext context, ThemeData theme, List<dynamic> byAgent) =>
      SizedBox(
        height: 250,
        child: PieChart(
          PieChartData(
            sections: byAgent.take(6).map((agent) {
              final agentType = _parseAgentType(agent['agent_type'] as String);
              final config = AgentConfig.forType(agentType, context);
              final count = agent['count'] as int;

              return PieChartSectionData(
                value: count.toDouble(),
                title: '${agent['count']}x',
                color: config.color,
                radius: 100,
                titleStyle: TextStyle(
                  fontSize: 12,
                  fontWeight: DS.fontWeightBold,
                  color: DS.brandPrimaryConst,
                ),
              );
            }).toList(),
            sectionsSpace: 2,
            centerSpaceRadius: 40,
            borderData: FlBorderData(show: false),
          ),
        ),
      );

  Widget _buildAgentCard(BuildContext context, ThemeData theme, dynamic agentData) {
    final agentType = _parseAgentType(agentData['agent_type'] as String);
    final config = AgentConfig.forType(agentType, context);
    final count = agentData['count'] as int;
    final avgDuration = agentData['avg_duration_ms'] as int? ?? 0;
    final successRate = agentData['success_rate'] as num? ?? 100;

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(DS.lg),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: config.color.withValues(alpha: 0.3),
          width: 1.5,
        ),
        boxShadow: [
          BoxShadow(
            color: config.color.withValues(alpha: 0.1),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        children: [
          // Agent Avatar
          AgentAvatarSwitcher(
            agentType: agentType,
            size: 48,
          ),
          const SizedBox(width: DS.lg),

          // Agent Info
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  config.displayName,
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: DS.fontWeightBold,
                    color: config.color,
                  ),
                ),
                const SizedBox(height: DS.xs),
                Row(
                  children: [
                    Icon(
                      Icons.repeat,
                      size: 14,
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                    const SizedBox(width: DS.xs),
                    Text(
                      I18nService.instance.isChinese ? '$count 次执行' : '$count executions',
                      style: theme.textTheme.bodySmall,
                    ),
                    const SizedBox(width: DS.lg),
                    Icon(
                      Icons.timer_outlined,
                      size: 14,
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                    const SizedBox(width: DS.xs),
                    Text(
                      '${avgDuration}ms',
                      style: theme.textTheme.bodySmall,
                    ),
                  ],
                ),
              ],
            ),
          ),

          // Success Rate Badge
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: _getSuccessRateColor(successRate).withValues(alpha: 0.2),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text(
              '${successRate.toStringAsFixed(0)}%',
              style: TextStyle(
                color: _getSuccessRateColor(successRate),
                fontWeight: DS.fontWeightBold,
                fontSize: 12,
              ),
            ),
          ),
        ],
      ),
    );
  }

  AgentType _parseAgentType(String typeStr) {
    switch (typeStr) {
      case 'orchestrator':
        return AgentType.orchestrator;
      case 'knowledge':
        return AgentType.knowledge;
      case 'math':
        return AgentType.math;
      case 'code':
        return AgentType.code;
      case 'data_analysis':
        return AgentType.dataAnalysis;
      case 'translation':
        return AgentType.translation;
      case 'image':
        return AgentType.image;
      case 'audio':
        return AgentType.audio;
      case 'writing':
        return AgentType.writing;
      case 'reasoning':
        return AgentType.reasoning;
      default:
        return AgentType.orchestrator;
    }
  }

  Color _getSuccessRateColor(num rate) {
    if (rate >= 90) return DS.success;
    if (rate >= 70) return DS.brandPrimary;
    return DS.error;
  }
}

/// Agent性能趋势图
class AgentPerformanceChart extends StatelessWidget {
  const AgentPerformanceChart({
    required this.performanceData,
    super.key,
  });
  final List<Map<String, dynamic>> performanceData;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      padding: const EdgeInsets.all(DS.lg),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            I18nService.instance.isChinese ? '性能趋势' : 'Performance Trends',
            style: theme.textTheme.titleLarge?.copyWith(
              fontWeight: DS.fontWeightBold,
            ),
          ),
          const SizedBox(height: DS.lg),
          SizedBox(
            height: 200,
            child: LineChart(
              LineChartData(
                titlesData: FlTitlesData(
                  bottomTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      reservedSize: 30,
                      getTitlesWidget: (value, meta) => Text(
                        value.toInt().toString(),
                        style: const TextStyle(fontSize: 10),
                      ),
                    ),
                  ),
                  leftTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      reservedSize: 40,
                      getTitlesWidget: (value, meta) => Text(
                        '${value.toInt()}ms',
                        style: const TextStyle(fontSize: 10),
                      ),
                    ),
                  ),
                  topTitles: const AxisTitles(),
                  rightTitles: const AxisTitles(),
                ),
                borderData: FlBorderData(show: true),
                lineBarsData: [
                  LineChartBarData(
                    spots: performanceData
                        .asMap()
                        .entries
                        .map(
                          (e) => FlSpot(
                            e.key.toDouble(),
                            (e.value['avg_duration_ms'] as num).toDouble(),
                          ),
                        )
                        .toList(),
                    isCurved: true,
                    color: DS.brandPrimaryConst,
                    barWidth: 3,
                    dotData: const FlDotData(show: false),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
