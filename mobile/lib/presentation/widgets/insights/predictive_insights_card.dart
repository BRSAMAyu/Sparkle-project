import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_tokens.dart';

/// 预测洞察卡片 - 显示AI预测的学习建议
///
/// 支持三种类型：
/// - engagement: 活跃度预测
/// - difficulty: 难度预测
/// - risk: 流失风险预警
class PredictiveInsightsCard extends StatelessWidget {

  const PredictiveInsightsCard({
    required this.type,
    required this.data,
    this.onTap,
    super.key,
  });
  final String type;
  final Map<String, dynamic> data;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Padding(
          padding: EdgeInsets.all(DS.lg),
          child: _buildContent(context),
        ),
      ),
    );

  Widget _buildContent(BuildContext context) {
    switch (type) {
      case 'engagement':
        return _buildEngagementCard(context);
      case 'difficulty':
        return _buildDifficultyCard(context);
      case 'risk':
        return _buildRiskCard(context);
      default:
        return Text('Unknown type');
    }
  }

  // 活跃度预测卡片
  Widget _buildEngagementCard(BuildContext context) {
    final nextActiveTime = data['next_active_time'] != null
        ? DateTime.parse(data['next_active_time'] as String)
        : null;
    final confidence = (data['confidence'] ?? 0.0) as double;
    final dropoutRisk = data['dropout_risk'] as String? ?? 'low';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Header
        Row(
          children: [
            Container(
              padding: EdgeInsets.all(DS.sm),
              decoration: BoxDecoration(
                color: DS.brandPrimary.shade50,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(Icons.trending_up, color: DS.brandPrimary.shade600, size: 24),
            ),
            SizedBox(width: DS.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '活跃度预测',
                    style: TextStyle(
                      fontSize: AppDesignTokens.fontSizeBase,
                      fontWeight: AppDesignTokens.fontWeightBold,
                    ),
                  ),
                  Text(
                    'AI 基于学习习惯的预测',
                    style: TextStyle(
                      fontSize: AppDesignTokens.fontSizeXs,
                      color: AppDesignTokens.neutral500,
                    ),
                  ),
                ],
              ),
            ),
            _buildConfidenceBadge(confidence),
          ],
        ),
        SizedBox(height: DS.lg),

        // Next Active Time
        if (nextActiveTime != null) ...[
          Container(
            padding: EdgeInsets.all(DS.md),
            decoration: BoxDecoration(
              color: DS.brandPrimary.shade50,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Row(
              children: [
                Icon(Icons.access_time, color: DS.brandPrimary.shade700, size: 20),
                SizedBox(width: DS.sm),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('预测下次学习时间', style: TextStyle(fontSize: 12)),
                    Text(
                      _formatDateTime(nextActiveTime),
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: DS.brandPrimary.shade700,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          SizedBox(height: DS.md),
        ],

        // Dropout Risk
        _buildRiskIndicator(dropoutRisk),
      ],
    );
  }

  // 难度预测卡片
  Widget _buildDifficultyCard(BuildContext context) {
    final difficultyScore = (data['difficulty_score'] ?? 0.0) as double;
    final estimatedHours = (data['estimated_time_hours'] ?? 0.0) as double;
    final prerequisitesReady = data['prerequisites_ready'] as bool? ?? false;
    final missingCount = (data['missing_prerequisites'] as List?)?.length ?? 0;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Header
        Row(
          children: [
            Container(
              padding: EdgeInsets.all(DS.sm),
              decoration: BoxDecoration(
                color: _getDifficultyColor(difficultyScore).withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(
                Icons.analytics_outlined,
                color: _getDifficultyColor(difficultyScore),
                size: 24,
              ),
            ),
            SizedBox(width: DS.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '难度预测',
                    style: TextStyle(
                      fontSize: AppDesignTokens.fontSizeBase,
                      fontWeight: AppDesignTokens.fontWeightBold,
                    ),
                  ),
                  Text(
                    'AI 基于前置知识的评估',
                    style: TextStyle(
                      fontSize: AppDesignTokens.fontSizeXs,
                      color: AppDesignTokens.neutral500,
                    ),
                  ),
                ],
              ),
            ),
            _buildDifficultyBadge(difficultyScore),
          ],
        ),
        SizedBox(height: DS.lg),

        // Difficulty Bar
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  '预测难度',
                  style: TextStyle(fontSize: AppDesignTokens.fontSizeXs),
                ),
                Text(
                  _getDifficultyLabel(difficultyScore),
                  style: TextStyle(
                    fontSize: AppDesignTokens.fontSizeXs,
                    fontWeight: AppDesignTokens.fontWeightBold,
                    color: _getDifficultyColor(difficultyScore),
                  ),
                ),
              ],
            ),
            SizedBox(height: DS.sm),
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: LinearProgressIndicator(
                value: difficultyScore,
                minHeight: 8,
                backgroundColor: DS.brandPrimary.shade200,
                valueColor: AlwaysStoppedAnimation(_getDifficultyColor(difficultyScore)),
              ),
            ),
          ],
        ),
        SizedBox(height: DS.lg),

        // Estimated Time
        Row(
          children: [
            Icon(Icons.schedule,
              color: AppDesignTokens.neutral500,
              size: AppDesignTokens.iconSizeXs,),
            SizedBox(width: AppDesignTokens.spacing8),
            Text(
              '预计学习时长: ${estimatedHours.toStringAsFixed(1)} 小时',
              style: TextStyle(fontSize: AppDesignTokens.fontSizeSm),
            ),
          ],
        ),
        SizedBox(height: DS.sm),

        // Prerequisites Status
        if (!prerequisitesReady)
          Container(
            padding: EdgeInsets.all(AppDesignTokens.spacing8),
            decoration: BoxDecoration(
              color: AppDesignTokens.warning.withValues(alpha: 0.1),
              borderRadius: AppDesignTokens.borderRadius8,
            ),
            child: Row(
              children: [
                Icon(Icons.warning_amber,
                  color: AppDesignTokens.warning,
                  size: AppDesignTokens.iconSizeXs,),
                SizedBox(width: AppDesignTokens.spacing8),
                Text(
                  '建议先学习 $missingCount 个前置知识',
                  style: TextStyle(
                    fontSize: AppDesignTokens.fontSizeXs,
                    color: AppDesignTokens.warning,
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }

  // 流失风险卡片
  Widget _buildRiskCard(BuildContext context) {
    final riskScore = (data['risk_score'] ?? 0.0) as double;
    final riskLevel = data['risk_level'] as String? ?? 'low';
    final suggestions = data['intervention_suggestions'] as List? ?? [];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Header
        Row(
          children: [
            Container(
              padding: EdgeInsets.all(DS.sm),
              decoration: BoxDecoration(
                color: _getRiskColor(riskLevel).withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(
                Icons.shield_outlined,
                color: _getRiskColor(riskLevel),
                size: 24,
              ),
            ),
            SizedBox(width: DS.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '学习风险评估',
                    style: TextStyle(
                      fontSize: AppDesignTokens.fontSizeBase,
                      fontWeight: AppDesignTokens.fontWeightBold,
                    ),
                  ),
                  Text(
                    'AI 持续关注您的学习状态',
                    style: TextStyle(
                      fontSize: AppDesignTokens.fontSizeXs,
                      color: AppDesignTokens.neutral500,
                    ),
                  ),
                ],
              ),
            ),
            _buildRiskLevelBadge(riskLevel),
          ],
        ),
        SizedBox(height: DS.lg),

        // Risk Score
        Text(
          '风险指数: ${riskScore.toInt()}/100',
          style: TextStyle(
            fontSize: AppDesignTokens.fontSizeSm,
            color: _getRiskColor(riskLevel),
            fontWeight: AppDesignTokens.fontWeightBold,
          ),
        ),
        SizedBox(height: DS.sm),
        ClipRRect(
          borderRadius: BorderRadius.circular(8),
          child: LinearProgressIndicator(
            value: riskScore / 100,
            minHeight: 8,
            backgroundColor: DS.brandPrimary.shade200,
            valueColor: AlwaysStoppedAnimation(_getRiskColor(riskLevel)),
          ),
        ),
        SizedBox(height: DS.lg),

        // Suggestions
        if (suggestions.isNotEmpty) ...[
          Text(
            'AI 建议:',
            style: TextStyle(
              fontSize: AppDesignTokens.fontSizeSm,
              fontWeight: AppDesignTokens.fontWeightBold,
            ),
          ),
          SizedBox(height: AppDesignTokens.spacing8),
          ...suggestions.take(2).map((suggestion) => Padding(
                padding: EdgeInsets.only(bottom: AppDesignTokens.spacing4),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(Icons.lightbulb_outline,
                      color: AppDesignTokens.accent,
                      size: AppDesignTokens.iconSizeXs,),
                    SizedBox(width: AppDesignTokens.spacing8),
                    Expanded(
                      child: Text(
                        suggestion.toString(),
                        style: TextStyle(
                          fontSize: AppDesignTokens.fontSizeXs,
                        ),
                      ),
                    ),
                  ],
                ),
              ),),
        ],
      ],
    );
  }

  // Helper Widgets
  Widget _buildConfidenceBadge(double confidence) => Container(
      padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: confidence > 0.7 ? DS.success.shade50 : DS.brandPrimary.shade50,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            confidence > 0.7 ? Icons.verified : Icons.info_outline,
            size: 12,
            color: confidence > 0.7 ? DS.success.shade700 : DS.brandPrimary.shade700,
          ),
          SizedBox(width: DS.xs),
          Text(
            '${(confidence * 100).toInt()}%',
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.bold,
              color: confidence > 0.7 ? DS.success.shade700 : DS.brandPrimary.shade700,
            ),
          ),
        ],
      ),
    );

  Widget _buildDifficultyBadge(double score) => Container(
      padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: _getDifficultyColor(score).withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        _getDifficultyLabel(score),
        style: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.bold,
          color: _getDifficultyColor(score),
        ),
      ),
    );

  Widget _buildRiskLevelBadge(String level) => Container(
      padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: _getRiskColor(level).withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        _getRiskLevelText(level),
        style: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.bold,
          color: _getRiskColor(level),
        ),
      ),
    );

  Widget _buildRiskIndicator(String risk) => Container(
      padding: EdgeInsets.all(DS.sm),
      decoration: BoxDecoration(
        color: _getRiskColor(risk).withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          Icon(_getRiskIcon(risk), color: _getRiskColor(risk), size: 16),
          SizedBox(width: DS.sm),
          Text(
            '流失风险: ${_getRiskLevelText(risk)}',
            style: TextStyle(fontSize: 12, color: _getRiskColor(risk)),
          ),
        ],
      ),
    );

  // Helper Methods
  String _formatDateTime(DateTime dt) {
    final now = DateTime.now();
    final diff = dt.difference(now);

    if (diff.inHours < 1) {
      return '约 ${diff.inMinutes} 分钟后';
    } else if (diff.inHours < 24) {
      return '今天 ${DateFormat('HH:mm').format(dt)}';
    } else if (diff.inDays == 1) {
      return '明天 ${DateFormat('HH:mm').format(dt)}';
    } else {
      return DateFormat('MM-dd HH:mm').format(dt);
    }
  }

  Color _getDifficultyColor(double score) {
    if (score < 0.3) return DS.success.shade600;
    if (score < 0.6) return DS.brandPrimary.shade600;
    return DS.error.shade600;
  }

  String _getDifficultyLabel(double score) {
    if (score < 0.3) return '简单';
    if (score < 0.6) return '中等';
    return '困难';
  }

  Color _getRiskColor(String level) {
    switch (level) {
      case 'low':
        return DS.success.shade600;
      case 'medium':
        return DS.brandPrimary.shade600;
      case 'high':
        return DS.error.shade600;
      default:
        return DS.brandPrimary.shade600;
    }
  }

  String _getRiskLevelText(String level) {
    switch (level) {
      case 'low':
        return '低风险';
      case 'medium':
        return '中等风险';
      case 'high':
        return '高风险';
      default:
        return '未知';
    }
  }

  IconData _getRiskIcon(String level) {
    switch (level) {
      case 'low':
        return Icons.check_circle;
      case 'medium':
        return Icons.warning_amber;
      case 'high':
        return Icons.error;
      default:
        return Icons.help;
    }
  }
}
