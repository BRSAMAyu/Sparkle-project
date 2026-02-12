import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:sparkle/core/design/design_system.dart';

/// 多智能体协作时间线组件
///
/// 展示多个 AI Agent 协作处理任务的完整流程
class AgentCollaborationTimeline extends StatefulWidget {
  const AgentCollaborationTimeline({
    required this.steps,
    required this.workflowType,
    super.key,
    this.executionTime = 0.0,
  });
  final List<AgentTimelineStep> steps;
  final String workflowType;
  final double executionTime;

  @override
  State<AgentCollaborationTimeline> createState() =>
      _AgentCollaborationTimelineState();
}

class _AgentCollaborationTimelineState extends State<AgentCollaborationTimeline>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: Duration(milliseconds: 500 * widget.steps.length),
    )..forward();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(DS.lg),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              DS.brandPrimary.shade50,
              DS.prismPurple.withValues(alpha: 0.08),
            ],
          ),
          borderRadius: BorderRadius.circular(16),
          boxShadow: [
            BoxShadow(
              color: DS.brandPrimary.withValues(alpha: 0.05),
              blurRadius: 10,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildHeader(),
            const SizedBox(height: DS.lg),
            _buildTimeline(),
          ],
        ),
      );

  Widget _buildHeader() => Row(
        children: [
          Container(
            padding: const EdgeInsets.all(DS.sm),
            decoration: BoxDecoration(
              color: DS.prismPurple.withValues(alpha: 0.14),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Icon(
              Icons.timeline,
              color: DS.prismPurple,
              size: 20,
            ),
          ),
          const SizedBox(width: DS.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '多专家协作时间线',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: DS.prismPurple,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  _getWorkflowDisplayName(),
                  style: TextStyle(
                    fontSize: 12,
                    color: DS.prismPurple.withValues(alpha: 0.82),
                  ),
                ),
              ],
            ),
          ),
          Chip(
            label: Text('${widget.executionTime.toStringAsFixed(1)}s'),
            backgroundColor: DS.success.shade100,
            labelStyle: TextStyle(
              color: DS.success.shade700,
              fontSize: 11,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      );

  Widget _buildTimeline() => Column(
        children: widget.steps.asMap().entries.map((entry) {
          final index = entry.key;
          final step = entry.value;
          final isLast = index == widget.steps.length - 1;

          return AnimatedBuilder(
            animation: _controller,
            builder: (context, child) {
              final progress = (_controller.value * widget.steps.length - index)
                  .clamp(0.0, 1.0);

              return Opacity(
                opacity: progress,
                child: Transform.translate(
                  offset: Offset(0, (1 - progress) * 20),
                  child: child,
                ),
              );
            },
            child: _buildTimelineItem(step, isLast),
          );
        }).toList(),
      );

  Widget _buildTimelineItem(AgentTimelineStep step, bool isLast) => Container(
        margin: EdgeInsets.only(bottom: isLast ? 0 : 16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 时间轴节点
            _buildTimelineNode(step),
            const SizedBox(width: DS.md),
            // 内容卡片
            Expanded(child: _buildStepCard(step)),
          ],
        ),
      );

  Widget _buildTimelineNode(AgentTimelineStep step) => Column(
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: step.agentColor,
              border: Border.all(color: DS.brandPrimaryConst, width: 3),
              boxShadow: [
                BoxShadow(
                  color: step.agentColor.withValues(alpha: 0.4),
                  blurRadius: 8,
                  spreadRadius: 1,
                ),
              ],
            ),
            child: Icon(
              step.agentIcon,
              color: DS.brandPrimaryConst,
              size: 20,
            ),
          ).animate(onPlay: (controller) => controller.repeat()).shimmer(
                duration: 2.seconds,
                color: DS.brandPrimary.withValues(alpha: 0.3),
              ),
          if (!isLast)
            Container(
              width: 2,
              height: 40,
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [
                    step.agentColor,
                    step.agentColor.withValues(alpha: 0.3),
                  ],
                ),
              ),
            ),
        ],
      );

  Widget _buildStepCard(AgentTimelineStep step) => Container(
        padding: const EdgeInsets.all(DS.spacing8 + DS.spacing6),
        decoration: BoxDecoration(
          color: DS.brandPrimaryConst,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: step.agentColor.withValues(alpha: 0.2),
            width: 1.5,
          ),
          boxShadow: [
            BoxShadow(
              color: DS.brandPrimary.withValues(alpha: 0.05),
              blurRadius: 4,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(
                  step.agentName,
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    color: step.agentColor,
                    fontSize: 14,
                  ),
                ),
                const SizedBox(width: DS.sm),
                if (step.timestamp != null)
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: step.agentColor.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      '${step.timestamp!.toStringAsFixed(2)}s',
                      style: TextStyle(
                        fontSize: 10,
                        color: step.agentColor.withValues(alpha: 0.8),
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: DS.sm),
            Text(
              step.action,
              style: TextStyle(
                fontSize: 13,
                color: DS.brandPrimary.shade700,
                height: 1.4,
              ),
            ),
            if (step.outputSummary != null) ...[
              const SizedBox(height: DS.sm),
              _buildExpandableDetails(step),
            ],
          ],
        ),
      );

  Widget _buildExpandableDetails(AgentTimelineStep step) => ExpansionTile(
        tilePadding: EdgeInsets.zero,
        childrenPadding: const EdgeInsets.only(top: 8),
        title: Row(
          children: [
            Icon(
              Icons.visibility_outlined,
              size: 14,
              color: step.agentColor,
            ),
            const SizedBox(width: DS.xs),
            Text(
              '查看详情',
              style: TextStyle(
                fontSize: 12,
                color: step.agentColor,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: step.agentColor.withValues(alpha: 0.05),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color: step.agentColor.withValues(alpha: 0.2),
              ),
            ),
            child: Text(
              step.outputSummary!,
              style: TextStyle(
                fontSize: 12,
                color: DS.brandPrimary.shade700,
                fontStyle: FontStyle.italic,
                height: 1.4,
              ),
            ),
          ),
        ],
      );

  String _getWorkflowDisplayName() {
    switch (widget.workflowType) {
      case 'task_decomposition':
        return '任务分解协作模式';
      case 'progressive_exploration':
        return '渐进式深度探索模式';
      case 'error_diagnosis':
        return '错题诊断循环模式';
      case 'expert_routing':
        return '专家路由模式';
      default:
        return '协作模式';
    }
  }

  bool get isLast => false;
}

/// Agent 时间线步骤数据模型
class AgentTimelineStep {
  AgentTimelineStep({
    required this.agentName,
    required this.action,
    required this.agentIcon,
    required this.agentColor,
    this.timestamp,
    this.outputSummary,
  });

  factory AgentTimelineStep.fromJson(Map<String, dynamic> json) =>
      AgentTimelineStep(
        agentName: (json['agent'] as String?) ??
            (json['agent_name'] as String?) ??
            'Agent',
        action: (json['action'] as String?) ?? (json['step'] as String?) ?? '',
        agentIcon: _getAgentIcon(
          (json['agent'] as String?) ??
              (json['agent_name'] as String?) ??
              'Agent',
        ),
        agentColor: _getAgentColor(
          (json['agent'] as String?) ??
              (json['agent_name'] as String?) ??
              'Agent',
        ),
        timestamp: (json['timestamp'] as num?)?.toDouble() ??
            (json['start_time_ms'] is num
                ? (json['start_time_ms'] as num).toDouble() / 1000.0
                : null),
        outputSummary: json['output_summary'] as String? ??
            json['outputSummary'] as String?,
      );
  final String agentName;
  final String action;
  final IconData agentIcon;
  final Color agentColor;
  final double? timestamp; // 相对于开始时间的秒数
  final String? outputSummary;

  static IconData _getAgentIcon(String agentName) {
    final normalized = agentName.toLowerCase();
    if (normalized.contains('studyplanner') ||
        normalized.contains('time_tutor')) {
      return Icons.calendar_today;
    } else if (normalized.contains('problemsolver') ||
        normalized.contains('error_analyst')) {
      return Icons.lightbulb_outline;
    } else if (normalized.contains('math')) {
      return Icons.calculate;
    } else if (normalized.contains('code')) {
      return Icons.code;
    } else if (normalized.contains('writing')) {
      return Icons.edit_note;
    } else if (normalized.contains('science')) {
      return Icons.science_outlined;
    } else if (normalized.contains('galaxy_guide') ||
        normalized.contains('knowledge')) {
      return Icons.auto_awesome;
    } else if (normalized.contains('exam_oracle')) {
      return Icons.quiz;
    } else if (normalized.contains('study_buddy')) {
      return Icons.favorite_border;
    } else if (normalized.contains('search')) {
      return Icons.search;
    } else if (normalized.contains('deep_analyst')) {
      return Icons.psychology_alt;
    } else {
      return Icons.hub_outlined;
    }
  }

  static Color _getAgentColor(String agentName) {
    final normalized = agentName.toLowerCase();
    if (normalized.contains('studyplanner') ||
        normalized.contains('time_tutor')) {
      return DS.success;
    } else if (normalized.contains('problemsolver') ||
        normalized.contains('error_analyst')) {
      return DS.brandPrimary;
    } else if (normalized.contains('math')) {
      return DS.brandPrimary;
    } else if (normalized.contains('code')) {
      return DS.prismPurple;
    } else if (normalized.contains('writing')) {
      return DS.info;
    } else if (normalized.contains('science')) {
      return DS.error;
    } else if (normalized.contains('galaxy_guide')) {
      return DS.infoLight;
    } else if (normalized.contains('exam_oracle')) {
      return DS.warning;
    } else if (normalized.contains('study_buddy')) {
      return DS.capsuleAccent;
    } else if (normalized.contains('search')) {
      return DS.info;
    } else if (normalized.contains('deep_analyst')) {
      return DS.brandSecondary;
    } else {
      return DS.capsuleAccent;
    }
  }
}
