import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

class TransparencyPanel extends StatelessWidget {
  const TransparencyPanel({
    super.key,
    required this.status,
    required this.details,
    required this.promptTokens,
    required this.completionTokens,
    required this.totalTokens,
    required this.currentAgentName,
    required this.activeAgentType,
    required this.activeTools,
    required this.dailyTokens,
    required this.dailyTokenLimit,
    required this.dailyCostMicroUsd,
  });

  final String? status;
  final String? details;
  final int? promptTokens;
  final int? completionTokens;
  final int? totalTokens;
  final String? currentAgentName;
  final String? activeAgentType;
  final List<String> activeTools;
  final int? dailyTokens;
  final int? dailyTokenLimit;
  final int? dailyCostMicroUsd;

  @override
  Widget build(BuildContext context) {
    if (status == null &&
        details == null &&
        totalTokens == null &&
        promptTokens == null &&
        completionTokens == null &&
        currentAgentName == null &&
        activeAgentType == null &&
        activeTools.isEmpty &&
        dailyTokens == null) {
      return const SizedBox.shrink();
    }

    final agentLabel = currentAgentName ?? _mapAgentType(activeAgentType);
    final hasAgent = agentLabel != null && agentLabel.isNotEmpty;
    final costDisplay = _formatCost(dailyCostMicroUsd);

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: DS.surfacePrimaryElevated,
          borderRadius: DS.borderRadius12,
          boxShadow: DS.shadowSm,
        ),
        child: Padding(
          padding: const EdgeInsets.all(DS.spacing12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '透明模式',
                style: TextStyle(
                  fontWeight: DS.fontWeightBold,
                  color: DS.textPrimary,
                ),
              ),
              const SizedBox(height: DS.spacing8),
              if (status != null)
                Text(
                  '状态: $status',
                  style: TextStyle(color: DS.textSecondary),
                ),
              if (details != null && details!.isNotEmpty)
                Text(
                  details!,
                  style: TextStyle(color: DS.textSecondary),
                ),
              if (hasAgent) ...[
                const SizedBox(height: DS.spacing8),
                Text(
                  '当前 Agent: $agentLabel',
                  style: TextStyle(color: DS.textSecondary),
                ),
              ],
              if (activeTools.isNotEmpty) ...[
                const SizedBox(height: DS.spacing8),
                Text(
                  '活跃工具: ${activeTools.join(' · ')}',
                  style: TextStyle(color: DS.textSecondary),
                ),
              ],
              if (totalTokens != null) ...[
                const SizedBox(height: DS.spacing8),
                Text(
                  'Tokens: $totalTokens',
                  style: TextStyle(color: DS.textSecondary),
                ),
                if (promptTokens != null && completionTokens != null)
                  Text(
                    'Prompt $promptTokens · Completion $completionTokens',
                    style: TextStyle(color: DS.neutral600, fontSize: DS.fontSizeSm),
                  ),
              ],
              if (dailyTokens != null && dailyTokenLimit != null) ...[
                const SizedBox(height: DS.spacing8),
                Text(
                  '今日: $dailyTokens / $dailyTokenLimit',
                  style: TextStyle(color: DS.textSecondary),
                ),
                if (costDisplay != null)
                  Text(
                    '成本估算: $costDisplay',
                    style: TextStyle(color: DS.neutral600, fontSize: DS.fontSizeSm),
                  ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  String? _mapAgentType(String? type) {
    switch (type) {
      case 'ORCHESTRATOR':
        return '编排器';
      case 'KNOWLEDGE':
        return '知识专家';
      case 'MATH':
        return '数学专家';
      case 'CODE':
        return '代码专家';
      case 'DATA_ANALYSIS':
        return '数据分析';
      case 'TRANSLATION':
        return '翻译专家';
      case 'IMAGE':
        return '图像专家';
      case 'AUDIO':
        return '音频专家';
      case 'WRITING':
        return '写作专家';
      case 'REASONING':
        return '推理专家';
      default:
        return null;
    }
  }

  String? _formatCost(int? microUsd) {
    if (microUsd == null || microUsd <= 0) {
      return null;
    }
    final usd = microUsd / 1000000.0;
    return '\$${usd.toStringAsFixed(4)}';
  }
}
