import 'package:flutter/material.dart';
import 'package:sparkle/core/design/components/molecules/stepper_indicator.dart';
import 'package:sparkle/core/design/components/organisms/expandable_section.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
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
    this.runLedgerSummary,
    this.currentStepIndex,
    this.showTokenUsageDetails = true,
    this.showAgentCollaboration = true,
    this.showReasoningTimeline = true,
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
  final RunLedgerSummary? runLedgerSummary;
  final int? currentStepIndex;
  final bool showTokenUsageDetails;
  final bool showAgentCollaboration;
  final bool showReasoningTimeline;

  @override
  Widget build(BuildContext context) {
    // 空状态检查
    final hasAnyData = status != null ||
        details != null ||
        totalTokens != null ||
        currentAgentName != null ||
        activeTools.isNotEmpty ||
        dailyTokens != null ||
        transparencyData != null ||
        runLedgerSummary != null;

    if (!hasAnyData) return const SizedBox.shrink();

    return SparkleStaggerItem(
      index: 0,
      offset: 0.035,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: DS.surfacePrimaryElevated,
            borderRadius: DS.borderRadius12,
            boxShadow: DS.shadowSm,
          ),
          child: Column(
            children: [
              _buildHeader(context),
              // 只有在有时间线数据时才显示步骤指示器
              if (showReasoningTimeline &&
                  transparencyData != null &&
                  transparencyData!.steps.isNotEmpty) ...[
                _buildStepper(),
                Divider(height: 1, color: DS.neutral200),
              ],
              _buildCompactInfo(context),
              // 可展开详情区域
              if (activeTools.isNotEmpty ||
                  (showTokenUsageDetails && totalTokens != null) ||
                  (showReasoningTimeline && transparencyData != null))
                _buildExpandableDetails(context),
            ],
          ),
        ),
      ),
    );
  }

  /// 标题栏（带渐变装饰条）
  Widget _buildHeader(BuildContext context) => Stack(
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
                  runLedgerSummary != null
                      ? 'Sparkle AI System'
                      : context.l10n.chatTransparencyTitle,
                  style: TextStyle(
                    fontWeight: DS.fontWeightSemibold,
                    color: DS.textPrimary,
                  ),
                ),
                const Spacer(),
                if (status != null) _statusChip(context, status!),
              ],
            ),
          ),
        ],
      );

  /// 状态徽标
  Widget _statusChip(BuildContext context, String status) {
    Color color;
    String label;
    switch (status.toUpperCase()) {
      case 'THINKING':
        color = DS.primaryBase;
        label = context.l10n.aiStatusThinking;
      case 'GENERATING':
        color = DS.info;
        label = context.l10n.aiStatusGenerating;
      case 'EXECUTING_TOOL':
        color = DS.warning;
        label = context.l10n.aiStatusExecutingTool;
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
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing12,
        vertical: DS.spacing12,
      ),
      child: StepperIndicator(
        steps: transparencyData!.steps,
        currentStepIndex: currentStepIndex ?? 0,
      ),
    );
  }

  /// 紧凑信息行
  Widget _buildCompactInfo(BuildContext context) => Padding(
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
                  _infoIcon(
                    Icons.build_rounded,
                    context.l10n.chatActiveToolsCount(activeTools.length),
                  ),
                ],
              ],
            ),
          ],
        ),
      );

  Widget _infoIcon(IconData icon, String label) => Row(
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

  /// 可展开详情区域（智能展开）
  Widget _buildExpandableDetails(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(
          DS.spacing12,
          0,
          DS.spacing12,
          DS.spacing12,
        ),
        child: Column(
          children: [
            // 工具详情 - 智能展开（有工具时自动展开）
            if (activeTools.isNotEmpty)
              ExpandableSection(
                title: context.l10n.chatActiveTools,
                leading:
                    Icon(Icons.build_rounded, size: 16, color: DS.neutral600),
                smartExpand: true,
                initiallyExpanded: true,
                backgroundColor: DS.surfaceSecondary,
                child: Column(
                  children: activeTools
                      .map(
                        (tool) => Padding(
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
                        ),
                      )
                      .toList(),
                ),
              ),
            // Token 详情 - 智能展开（有数据时自动展开）
            if (showTokenUsageDetails && totalTokens != null)
              ExpandableSection(
                title: context.l10n.chatTokenStats,
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
                    if (promptTokens != null)
                      _statRow(
                        context.l10n.chatPromptTokens,
                        promptTokens.toString(),
                      ),
                    if (completionTokens != null)
                      _statRow(
                        context.l10n.chatCompletionTokens,
                        completionTokens.toString(),
                      ),
                    if (dailyTokens != null && dailyTokenLimit != null)
                      _statRow(
                        context.l10n.chatTokenUsageToday,
                        '$dailyTokens / $dailyTokenLimit',
                      ),
                    if (dailyCostMicroUsd != null)
                      _statRow(
                        context.l10n.chatTokenCostEstimate,
                        _formatCost(dailyCostMicroUsd) ?? '-',
                      ),
                  ],
                ),
              ),
            if (runLedgerSummary != null)
              ExpandableSection(
                title: 'Sparkle Intelligence Control Tower',
                leading: Icon(
                  Icons.auto_awesome_rounded,
                  size: 16,
                  color: DS.neutral600,
                ),
                trailing: Text(
                  runLedgerSummary!.status == 'completed' ? 'Ready' : 'Live',
                  style: TextStyle(
                    fontSize: DS.fontSizeXs,
                    color: DS.neutral600,
                  ),
                ),
                smartExpand: true,
                initiallyExpanded: true,
                backgroundColor: DS.surfaceSecondary,
                child: _buildRunLedgerSummary(),
              ),
            // 步骤详情（完整垂直时间线） - 智能展开
            if (showReasoningTimeline &&
                transparencyData != null &&
                transparencyData!.steps.isNotEmpty)
              ExpandableSection(
                title: context.l10n.chatExecutionSteps,
                leading: Icon(
                  Icons.timeline_rounded,
                  size: 16,
                  color: DS.neutral600,
                ),
                trailing: Text(
                  context.l10n.chatExecutionStepsCount(
                    transparencyData!.steps.length,
                  ),
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

  /// 步骤时间线（使用 StepperIndicator 组件）
  Widget _buildStepTimeline() {
    if (transparencyData == null) return const SizedBox.shrink();
    return StepperIndicator(
      steps: transparencyData!.steps,
      currentStepIndex: currentStepIndex ?? 0,
    );
  }

  Widget _statRow(String label, String value) => Padding(
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

  String? _formatCost(int? microUsd) {
    if (microUsd == null || microUsd <= 0) return null;
    final usd = microUsd / 1000000.0;
    return '\$${usd.toStringAsFixed(4)}';
  }

  Widget _buildRunLedgerSummary() {
    final summary = runLedgerSummary;
    if (summary == null) return const SizedBox.shrink();

    final modelRoles = summary.models
        .map((item) {
          final role = item['role']?.toString() ?? 'unknown';
          final modelKey = item['model_key']?.toString() ?? '';
          final provider = item['provider']?.toString() ?? '';
          if (modelKey.isEmpty) return '';
          return '$role: $modelKey${provider.isNotEmpty ? ' · $provider' : ''}';
        })
        .where((item) => item.isNotEmpty)
        .toList();
    final agentNames = summary.agents
        .map((item) => item['agent_id']?.toString() ?? '')
        .where((item) => item.isNotEmpty)
        .toList();
    final evidenceBits = <String>[];
    final focusMode = summary.evidence['focus_mode']?.toString() ?? '';
    if (focusMode.isNotEmpty) evidenceBits.add('focus: $focusMode');
    final preferences = summary.evidence['preferences'];
    if (preferences is int && preferences > 0) {
      evidenceBits.add('prefs: $preferences');
    }
    final goals = summary.evidence['goals'];
    if (goals is int && goals > 0) {
      evidenceBits.add('goals: $goals');
    }
    final feedbackTargets =
        ((summary.feedback['strategy_effects'] as List<dynamic>?) ?? const [])
            .whereType<Map<String, dynamic>>()
            .map((item) => item['target']?.toString() ?? '')
            .where((item) => item.isNotEmpty)
            .toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _statRow(
          'Execution mode',
          summary.executionMode.isNotEmpty ? summary.executionMode : '-',
        ),
        _statRow('Events tracked', summary.eventCount.toString()),
        if (summary.reviewScore != null)
          _statRow('Review score', summary.reviewScore!.toStringAsFixed(2)),
        if (summary.reflectionCompleted || summary.reflectionDelta > 0)
          _statRow(
            'Reflection uplift',
            '+${summary.reflectionDelta.toStringAsFixed(2)}',
          ),
        if (summary.totalTokens > 0)
          _statRow('Total tokens', summary.totalTokens.toString()),
        if (summary.estimatedCostUsd > 0)
          _statRow(
            'Estimated cost',
            '\$${summary.estimatedCostUsd.toStringAsFixed(4)}',
          ),
        if (showAgentCollaboration && agentNames.isNotEmpty) ...[
          const SizedBox(height: DS.spacing8),
          Text(
            'Agent collaboration',
            style: TextStyle(
              fontSize: DS.fontSizeSm,
              color: DS.textPrimary,
              fontWeight: DS.fontWeightSemibold,
            ),
          ),
          const SizedBox(height: 6),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: agentNames.map(_buildLedgerChip).toList(),
          ),
        ],
        if (modelRoles.isNotEmpty) ...[
          const SizedBox(height: DS.spacing12),
          Text(
            'Model choreography',
            style: TextStyle(
              fontSize: DS.fontSizeSm,
              color: DS.textPrimary,
              fontWeight: DS.fontWeightSemibold,
            ),
          ),
          const SizedBox(height: 6),
          ...modelRoles.map(
            (item) => Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Text(
                item,
                style: TextStyle(
                  fontSize: DS.fontSizeSm,
                  color: DS.textSecondary,
                ),
              ),
            ),
          ),
        ],
        if (evidenceBits.isNotEmpty) ...[
          const SizedBox(height: DS.spacing12),
          Text(
            'Evidence pack',
            style: TextStyle(
              fontSize: DS.fontSizeSm,
              color: DS.textPrimary,
              fontWeight: DS.fontWeightSemibold,
            ),
          ),
          const SizedBox(height: 6),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: evidenceBits.map(_buildLedgerChip).toList(),
          ),
        ],
        if (feedbackTargets.isNotEmpty) ...[
          const SizedBox(height: DS.spacing12),
          Text(
            'Feedback effects',
            style: TextStyle(
              fontSize: DS.fontSizeSm,
              color: DS.textPrimary,
              fontWeight: DS.fontWeightSemibold,
            ),
          ),
          const SizedBox(height: 6),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: feedbackTargets.map(_buildLedgerChip).toList(),
          ),
        ],
      ],
    );
  }

  Widget _buildLedgerChip(String label) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: 4,
        ),
        decoration: BoxDecoration(
          color: DS.surfacePrimaryElevated,
          borderRadius: DS.borderRadius20,
          border: Border.all(color: DS.neutral200),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: DS.fontSizeXs,
            color: DS.textSecondary,
            fontWeight: DS.fontWeightMedium,
          ),
        ),
      );
}
