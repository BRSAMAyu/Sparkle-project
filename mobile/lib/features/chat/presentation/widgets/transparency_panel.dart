import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:sparkle/core/design/components/molecules/stepper_indicator.dart';
import 'package:sparkle/core/design/components/organisms/expandable_section.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/chat/data/models/chat_stream_events.dart';

/// 透明模式面板 - 显示 AI 处理过程的透明度信息
///
/// 功能包括：
/// - 步骤可视化（垂直时间线）
/// - 状态徽标（思考中/生成中/执行工具）
/// - 智能展开详情（工具、Token、步骤详情）
/// - 耗时显示
class TransparencyPanel extends StatelessWidget {
  const TransparencyPanel({
    super.key,
    // 现有字段
    this.status,
    this.details,
    this.promptTokens,
    this.completionTokens,
    this.totalTokens,
    this.currentAgentName,
    this.activeAgentType,
    this.activeTools = const [],
    this.dailyTokens,
    this.dailyTokenLimit,
    this.dailyCostMicroUsd,
    // 新增字段
    this.transparencyData,
    this.currentStepIndex,
  });

  // 现有字段
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
  // 新增字段
  final TransparencyData? transparencyData;
  final int? currentStepIndex;

  @override
  Widget build(BuildContext context) {
    // 空状态检查
    final hasAnyData = status != null ||
        details != null ||
        totalTokens != null ||
        currentAgentName != null ||
        activeTools.isNotEmpty ||
        dailyTokens != null ||
        transparencyData != null;

    if (!hasAnyData) return const SizedBox.shrink();

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: DS.surfacePrimaryElevated,
          borderRadius: DS.borderRadius12,
          boxShadow: DS.shadowSm,
        ),
        child: Column(
          children: [
            _buildHeader(),
            // 只有在有时间线数据时才显示步骤指示器
            if (transparencyData != null && transparencyData!.steps.isNotEmpty) ...[
              _buildStepper(),
              Divider(height: 1, color: DS.neutral200),
            ],
            _buildCompactInfo(),
            // 可展开详情区域
            if (activeTools.isNotEmpty ||
                totalTokens != null ||
                transparencyData != null)
              _buildExpandableDetails(),
          ],
        ),
      ),
    );
  }

  /// 标题栏（带渐变装饰条）
  Widget _buildHeader() {
    return Stack(
      children: [
        Positioned(
          left: 0,
          top: 0,
          bottom: 0,
          width: 3,
          child: Container(
            decoration: BoxDecoration(
              gradient: DS.primaryGradient,
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(DS.radius12),
                bottomLeft: Radius.circular(DS.radius12),
              ),
            ),
          ),
        ),
        Padding(
          padding: const EdgeInsets.all(DS.spacing12),
          child: Row(
            children: [
              Icon(
                Icons.visibility_rounded,
                size: 18,
                color: DS.primaryBase,
              ),
              const SizedBox(width: DS.spacing8),
              Text(
                '透明模式',
                style: TextStyle(
                  fontWeight: DS.fontWeightSemibold,
                  color: DS.textPrimary,
                ),
              ),
              const Spacer(),
              if (status != null) _statusChip(status!),
            ],
          ),
        ),
      ],
    );
  }

  /// 状态徽标
  Widget _statusChip(String status) {
    Color color;
    String label;
    switch (status.toUpperCase()) {
      case 'THINKING':
        color = DS.primaryBase;
        label = '思考中';
      case 'GENERATING':
        color = DS.info;
        label = '生成中';
      case 'EXECUTING_TOOL':
        color = DS.warning;
        label = '执行工具';
      default:
        color = DS.neutral600;
        label = status;
    }
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing8,
        vertical: 2,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: DS.borderRadius20,
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: DS.fontSizeXs,
          color: color,
          fontWeight: DS.fontWeightSemibold,
        ),
      ),
    );
  }

  /// 步骤指示器（垂直时间线）
  Widget _buildStepper() {
    if (transparencyData == null || transparencyData!.steps.isEmpty) {
      return const SizedBox.shrink();
    }
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: DS.spacing12, vertical: DS.spacing12),
      child: StepperIndicator(
        steps: transparencyData!.steps,
        currentStepIndex: currentStepIndex ?? 0,
      ),
    );
  }

  /// 紧凑信息行
  Widget _buildCompactInfo() {
    return Padding(
      padding: const EdgeInsets.all(DS.spacing12),
      child: Column(
        children: [
          if (details != null && details!.isNotEmpty) ...[
            Text(
              details!,
              style: TextStyle(
                color: DS.textSecondary,
                fontSize: DS.fontSizeSm,
              ),
            ),
            const SizedBox(height: DS.spacing8),
          ],
          Row(
            children: [
              if (currentAgentName != null) ...[
                _infoIcon(Icons.person_rounded, currentAgentName!),
                const SizedBox(width: DS.spacing12),
              ],
              if (totalTokens != null) ...[
                _infoIcon(Icons.token, '$totalTokens'),
                const SizedBox(width: DS.spacing12),
              ],
              if (activeTools.isNotEmpty) ...[
                _infoIcon(Icons.build_rounded, '${activeTools.length} 个工具'),
              ],
            ],
          ),
        ],
      ),
    );
  }

  Widget _infoIcon(IconData icon, String label) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 14, color: DS.neutral500),
        const SizedBox(width: 4),
        Text(
          label,
          style: TextStyle(
            fontSize: DS.fontSizeXs,
            color: DS.neutral600,
          ),
        ),
      ],
    );
  }

  /// 可展开详情区域（智能展开）
  Widget _buildExpandableDetails() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(DS.spacing12, 0, DS.spacing12, DS.spacing12),
      child: Column(
        children: [
          // 工具详情 - 智能展开（有工具时自动展开）
          if (activeTools.isNotEmpty)
            ExpandableSection(
              title: '活跃工具',
              leading: Icon(Icons.build_rounded, size: 16, color: DS.neutral600),
              smartExpand: true,
              initiallyExpanded: true,
              backgroundColor: DS.surfaceSecondary,
              child: Column(
                children: activeTools
                    .map((tool) => Padding(
                          padding: const EdgeInsets.symmetric(vertical: 2),
                          child: Row(
                            children: [
                              Icon(Icons.circle, size: 4, color: DS.neutral400),
                              const SizedBox(width: DS.spacing8),
                              Text(
                                tool,
                                style: TextStyle(
                                  fontSize: DS.fontSizeSm,
                                  color: DS.textSecondary,
                                ),
                              ),
                            ],
                          ),
                        ))
                    .toList(),
              ),
            ),
          // Token 详情 - 智能展开（有数据时自动展开）
          if (totalTokens != null)
            ExpandableSection(
              title: 'Token 统计',
              leading: Icon(Icons.token, size: 16, color: DS.neutral600),
              trailing: Text(
                totalTokens!.toString(),
                style: TextStyle(
                  fontSize: DS.fontSizeXs,
                  color: DS.neutral600,
                ),
              ),
              smartExpand: true,
              initiallyExpanded: true,
              backgroundColor: DS.surfaceSecondary,
              child: Column(
                children: [
                  if (promptTokens != null) _statRow('Prompt Tokens', promptTokens.toString()),
                  if (completionTokens != null) _statRow('Completion Tokens', completionTokens.toString()),
                  if (dailyTokens != null && dailyTokenLimit != null) _statRow('今日使用', '$dailyTokens / $dailyTokenLimit'),
                  if (dailyCostMicroUsd != null) _statRow('成本估算', _formatCost(dailyCostMicroUsd) ?? '-'),
                ],
              ),
            ),
          // 步骤详情（完整垂直时间线） - 智能展开
          if (transparencyData != null && transparencyData!.steps.isNotEmpty)
            ExpandableSection(
              title: '执行步骤',
              leading: Icon(Icons.timeline_rounded, size: 16, color: DS.neutral600),
              trailing: Text(
                '${transparencyData!.steps.length} 个步骤',
                style: TextStyle(
                  fontSize: DS.fontSizeXs,
                  color: DS.neutral600,
                ),
              ),
              smartExpand: true,
              initiallyExpanded: true,
              backgroundColor: DS.surfaceSecondary,
              child: _buildStepTimeline(),
            ),
        ],
      ),
    );
  }

  /// 步骤时间线（使用 StepperIndicator 组件）
  Widget _buildStepTimeline() {
    if (transparencyData == null) return const SizedBox.shrink();
    return StepperIndicator(
      steps: transparencyData!.steps,
      currentStepIndex: currentStepIndex ?? 0,
    );
  }

  Widget _statRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: TextStyle(
              fontSize: DS.fontSizeSm,
              color: DS.textSecondary,
            ),
          ),
          Text(
            value,
            style: TextStyle(
              fontSize: DS.fontSizeSm,
              color: DS.textPrimary,
              fontWeight: DS.fontWeightMedium,
            ),
          ),
        ],
      ),
    );
  }

  String? _formatCost(int? microUsd) {
    if (microUsd == null || microUsd <= 0) return null;
    final usd = microUsd / 1000000.0;
    return '\$${usd.toStringAsFixed(4)}';
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
}
