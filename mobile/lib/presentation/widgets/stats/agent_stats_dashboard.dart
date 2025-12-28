import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/data/models/reasoning_step_model.dart';
import 'package:sparkle/presentation/widgets/chat/agent_avatar_switcher.dart';

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
      padding: EdgeInsets.all(DS.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Text(
            'Agent 协作统计',
            style: theme.textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
          SizedBox(height: DS.sm),
          Text(
            '过去 ${statsData['period_days'] ?? 30} 天',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
          SizedBox(height: DS.xl),

          // Overall Stats Cards
          _buildOverallStats(theme, overall),
          SizedBox(height: DS.xl),

          // Usage Pie Chart
          if (byAgent.isNotEmpty) ...[
            Text(
              'Agent 使用分布',
              style: theme.textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            SizedBox(height: DS.lg),
            _buildUsagePieChart(theme, byAgent),
            SizedBox(height: DS.xl),
          ],

          // Top Agents List
          if (byAgent.isNotEmpty) ...[
            Text(
              'Top Agents',
              style: theme.textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            SizedBox(height: DS.lg),
            ...byAgent.take(5).map((agent) => _buildAgentCard(theme, agent)),
          ],
        ],
      ),
    );
  }

  Widget _buildOverallStats(ThemeData theme, Map<String, dynamic> overall) => Row(
      children: [
        Expanded(
          child: _buildStatCard(
            theme,
            title: '总执行次数',
            value: '${overall['total_executions'] ?? 0}',
            icon: Icons.sync_alt,
            color: DS.brandPrimaryConst,
          ),
        ),
        SizedBox(width: DS.md),
        Expanded(
          child: _buildStatCard(
            theme,
            title: '平均耗时',
            value: '${overall['avg_duration_ms'] ?? 0}ms',
            icon: Icons.timer,
            color: DS.brandPrimaryConst,
          ),
        ),
        SizedBox(width: DS.md),
        Expanded(
          child: _buildStatCard(
            theme,
            title: '会话数',
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
  }) => Container(
      padding: EdgeInsets.all(DS.lg),
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
          SizedBox(height: DS.sm),
          Text(
            value,
            style: theme.textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
          SizedBox(height: DS.xs),
          Text(
            title,
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ],
      ),
    );

  Widget _buildUsagePieChart(ThemeData theme, List<dynamic> byAgent) => SizedBox(
      height: 250,
      child: PieChart(
        PieChartData(
          sections: byAgent.take(6).map((agent) {
            final agentType = _parseAgentType(agent['agent_type'] as String);
            final config = AgentConfig.forType(agentType);
            final count = agent['count'] as int;

            return PieChartSectionData(
              value: count.toDouble(),
              title: '${agent['count']}次',
              color: config.color,
              radius: 100,
              titleStyle: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.bold,
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

  Widget _buildAgentCard(ThemeData theme, dynamic agentData) {
    final agentType = _parseAgentType(agentData['agent_type'] as String);
    final config = AgentConfig.forType(agentType);
    final count = agentData['count'] as int;
    final avgDuration = agentData['avg_duration_ms'] as int? ?? 0;
    final successRate = agentData['success_rate'] as num? ?? 100;

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: EdgeInsets.all(DS.lg),
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
          SizedBox(width: DS.lg),

          // Agent Info
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  config.displayName,
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: config.color,
                  ),
                ),
                SizedBox(height: DS.xs),
                Row(
                  children: [
                    Icon(
                      Icons.repeat,
                      size: 14,
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                    SizedBox(width: DS.xs),
                    Text(
                      '$count 次执行',
                      style: theme.textTheme.bodySmall,
                    ),
                    SizedBox(width: DS.lg),
                    Icon(
                      Icons.timer_outlined,
                      size: 14,
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                    SizedBox(width: DS.xs),
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
                fontWeight: FontWeight.bold,
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
      padding: EdgeInsets.all(DS.lg),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '性能趋势',
            style: theme.textTheme.titleLarge?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
          SizedBox(height: DS.lg),
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
                          style: TextStyle(fontSize: 10),
                        ),
                    ),
                  ),
                  leftTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      reservedSize: 40,
                      getTitlesWidget: (value, meta) => Text(
                          '${value.toInt()}ms',
                          style: TextStyle(fontSize: 10),
                        ),
                    ),
                  ),
                  topTitles: const AxisTitles(
                    
                  ),
                  rightTitles: const AxisTitles(
                    
                  ),
                ),
                borderData: FlBorderData(show: true),
                lineBarsData: [
                  LineChartBarData(
                    spots: performanceData
                        .asMap()
                        .entries
                        .map((e) => FlSpot(
                              e.key.toDouble(),
                              (e.value['avg_duration_ms'] as num).toDouble(),
                            ),)
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
