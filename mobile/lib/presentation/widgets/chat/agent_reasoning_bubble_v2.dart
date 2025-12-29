import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/data/models/reasoning_step_model.dart';

/// 🧠 Chain of Thought Visualization Bubble
///
/// 展示AI的思考过程，包括：
/// - 动态Agent图标切换
/// - 可展开的步骤流
/// - 实时状态更新
/// - GraphRAG引用展示
class AgentReasoningBubble extends StatefulWidget {

  const AgentReasoningBubble({
    required this.steps, super.key,
    this.isThinking = false,
    this.totalDurationMs,
  });
  /// 推理步骤列表
  final List<ReasoningStep> steps;

  /// 是否正在思考中（流式更新）
  final bool isThinking;

  /// 总耗时（毫秒）
  final int? totalDurationMs;

  @override
  State<AgentReasoningBubble> createState() => _AgentReasoningBubbleState();
}

class _AgentReasoningBubbleState extends State<AgentReasoningBubble>
    with SingleTickerProviderStateMixin {
  bool _isExpanded = false;
  late AnimationController _animationController;
  late Animation<double> _expandAnimation;

  @override
  void initState() {
    super.initState();

    _animationController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 350),
    );

    _expandAnimation = CurvedAnimation(
      parent: _animationController,
      curve: Curves.easeInOut,
    );
  }

  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }

  void _toggleExpand() {
    setState(() {
      _isExpanded = !_isExpanded;
      if (_isExpanded) {
        _animationController.forward();
      } else {
        _animationController.reverse();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    if (widget.steps.isEmpty) {
      return const SizedBox.shrink();
    }

    final theme = Theme.of(context);
    final activeStep = _getActiveStep();

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8, horizontal: 12),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest.withOpacity(0.3),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: theme.colorScheme.primary.withOpacity(0.2),
          width: 1.5,
        ),
        boxShadow: [
          BoxShadow(
            color: theme.colorScheme.primary.withOpacity(0.1),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header - Always visible
          _buildHeader(theme, activeStep),

          // Expandable Stream
          SizeTransition(
            sizeFactor: _expandAnimation,
            child: _buildStepStream(theme),
          ),
        ],
      ),
    );
  }

  Widget _buildHeader(ThemeData theme, ReasoningStep? activeStep) {
    final isCompleted = !widget.isThinking && widget.steps.every((s) => s.isCompleted);

    return InkWell(
      onTap: _toggleExpand,
      borderRadius: BorderRadius.circular(16),
      child: Padding(
        padding: const EdgeInsets.all(DS.md),
        child: Row(
          children: [
            // Animated Agent Icon
            AnimatedContainer(
              duration: const Duration(milliseconds: 400),
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: _getAgentColor(activeStep?.agent ?? AgentType.orchestrator),
                boxShadow: widget.isThinking
                    ? [
                        BoxShadow(
                          color: _getAgentColor(activeStep?.agent ?? AgentType.orchestrator)
                              .withOpacity(0.4),
                          blurRadius: 8,
                          spreadRadius: 2,
                        ),
                      ]
                    : null,
              ),
              child: AnimatedSwitcher(
                duration: const Duration(milliseconds: 300),
                child: Icon(
                  _getAgentIcon(activeStep?.agent ?? AgentType.orchestrator),
                  color: DS.brandPrimaryConst,
                  size: 18,
                  key: ValueKey(activeStep?.agent ?? AgentType.orchestrator),
                ),
              ),
            ),

            const SizedBox(width: DS.md),

            // Status Text
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _getStatusText(activeStep, isCompleted),
                    style: theme.textTheme.bodyMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                      color: _getStatusColor(activeStep, isCompleted, theme),
                    ),
                  ),
                  if (widget.totalDurationMs != null && isCompleted)
                    Text(
                      '耗时: ${(widget.totalDurationMs! / 1000).toStringAsFixed(1)}s',
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                ],
              ),
            ),

            // Right side: Progress or Expand/Collapse
            if (widget.isThinking && activeStep != null)
              Container(
                width: 20,
                height: 20,
                margin: const EdgeInsets.only(right: 8),
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  valueColor: AlwaysStoppedAnimation(
                    _getAgentColor(activeStep.agent),
                  ),
                ),
              )
            else if (isCompleted)
              Icon(Icons.check_circle, color: DS.success, size: 20)
            else
              AnimatedRotation(
                turns: _isExpanded ? 0.5 : 0,
                duration: const Duration(milliseconds: 300),
                child: Icon(
                  Icons.keyboard_arrow_down,
                  color: theme.colorScheme.primary,
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildStepStream(ThemeData theme) => Container(
      margin: const EdgeInsets.fromLTRB(12, 0, 12, 12),
      padding: const EdgeInsets.all(DS.md),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: theme.colorScheme.outline.withOpacity(0.1),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            children: [
              Icon(
                Icons.psychology,
                size: 16,
                color: theme.colorScheme.primary,
              ),
              const SizedBox(width: 6),
              Text(
                '思考过程',
                style: theme.textTheme.labelLarge?.copyWith(
                  color: theme.colorScheme.primary,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const Spacer(),
              Text(
                '${widget.steps.length} steps',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
            ],
          ),

          const SizedBox(height: DS.md),

          // Steps List
          ...widget.steps.asMap().entries.map((entry) {
            final index = entry.key;
            final step = entry.value;
            final isLast = index == widget.steps.length - 1;

            return _buildStepItem(step, isLast, theme);
          }),
        ],
      ),
    );

  Widget _buildStepItem(ReasoningStep step, bool isLast, ThemeData theme) => Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Status Icon
            Container(
              width: 20,
              height: 20,
              margin: const EdgeInsets.only(top: 2),
              child: _buildStepStatusIcon(step.status),
            ),

            const SizedBox(width: DS.sm),

            // Step Content
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Description
                  Text(
                    step.description,
                    style: theme.textTheme.bodySmall?.copyWith(
                      fontWeight: FontWeight.w500,
                      color: theme.colorScheme.onSurface,
                    ),
                  ),

                  // Tool Output (if any)
                  if (step.toolOutput != null && step.toolOutput!.isNotEmpty)
                    Container(
                      margin: const EdgeInsets.only(top: 6),
                      padding: const EdgeInsets.all(DS.sm),
                      decoration: BoxDecoration(
                        color: DS.brandPrimary87,
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: SelectableText(
                        step.toolOutput!,
                        style: TextStyle(
                          fontFamily: 'monospace',
                          fontSize: 11,
                          color: DS.successAccent,
                          height: 1.4,
                        ),
                      ),
                    ),

                  // Citations (if any)
                  if (step.citations != null && step.citations!.isNotEmpty)
                    Container(
                      margin: const EdgeInsets.only(top: 6),
                      child: Wrap(
                        spacing: 6,
                        runSpacing: 4,
                        children: step.citations!.map((citation) => InkWell(
                            onTap: () => _showCitationDialog(citation),
                            borderRadius: BorderRadius.circular(12),
                            child: Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 8,
                                vertical: 4,
                              ),
                              decoration: BoxDecoration(
                                color: DS.brandPrimary.withOpacity(0.1),
                                borderRadius: BorderRadius.circular(12),
                                border: Border.all(
                                  color: DS.brandPrimary.withOpacity(0.3),
                                ),
                              ),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(
                                    Icons.book,
                                    size: 12,
                                    color: DS.brandPrimaryConst,
                                  ),
                                  const SizedBox(width: DS.xs),
                                  Text(
                                    '引用: $citation',
                                    style: TextStyle(
                                      fontSize: 11,
                                      color: DS.brandPrimaryConst,
                                      fontWeight: FontWeight.w500,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),).toList(),
                      ),
                    ),

                  // Duration
                  if (step.durationMs != null)
                    Container(
                      margin: const EdgeInsets.only(top: 4),
                      child: Text(
                        '${step.durationMs}ms',
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: theme.colorScheme.onSurfaceVariant,
                          fontSize: 10,
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ],
        ),

        // Divider (if not last)
        if (!isLast)
          Container(
            margin: const EdgeInsets.symmetric(vertical: 8),
            height: 1,
            color: theme.colorScheme.outline.withOpacity(0.1),
          ),
      ],
    );

  Widget _buildStepStatusIcon(StepStatus status) {
    switch (status) {
      case StepStatus.completed:
        return Icon(Icons.check_circle, color: DS.success, size: 16);
      case StepStatus.inProgress:
        return SizedBox(
          width: 16,
          height: 16,
          child: CircularProgressIndicator(
            strokeWidth: 2,
            valueColor: AlwaysStoppedAnimation(Colors.amber[600]),
          ),
        );
      case StepStatus.failed:
        return Icon(Icons.error, color: DS.error, size: 16);
      case StepStatus.pending:
        return Icon(Icons.radio_button_unchecked,
            color: DS.brandPrimary400, size: 16,);
    }
  }

  IconData _getAgentIcon(AgentType agent) {
    switch (agent) {
      case AgentType.orchestrator:
        return Icons.psychology; // 🧠 Brain
      case AgentType.math:
        return Icons.functions; // 📐 Math
      case AgentType.code:
        return Icons.code; // 💻 Code
      case AgentType.writing:
        return Icons.edit; // ✍️ Writing
      case AgentType.science:
        return Icons.science; // 🔬 Science
      case AgentType.knowledge:
        return Icons.auto_awesome; // 🌌 Galaxy
      case AgentType.search:
        return Icons.search; // 🔍 Search
      case AgentType.dataAnalysis:
        return Icons.analytics; // 📊 Data Analysis
      case AgentType.translation:
        return Icons.translate; // 🌐 Translation
      case AgentType.image:
        return Icons.image; // 🖼️ Image
      case AgentType.audio:
        return Icons.audiotrack; // 🎵 Audio
      case AgentType.reasoning:
        return Icons.psychology_outlined; // 🤔 Reasoning
    }
  }

  Color _getAgentColor(AgentType agent) {
    switch (agent) {
      case AgentType.orchestrator:
        return const Color(0xFF6366F1); // Indigo
      case AgentType.math:
        return const Color(0xFF0EA5E9); // Sky Blue
      case AgentType.code:
        return const Color(0xFF8B5CF6); // Purple
      case AgentType.writing:
        return const Color(0xFFF59E0B); // Amber
      case AgentType.science:
        return const Color(0xFF10B981); // Emerald
      case AgentType.knowledge:
        return const Color(0xFFEC4899); // Pink
      case AgentType.search:
        return const Color(0xFF3B82F6); // Blue
      case AgentType.dataAnalysis:
        return const Color(0xFF06B6D4); // Cyan
      case AgentType.translation:
        return const Color(0xFF8B5CF6); // Purple (same as code)
      case AgentType.image:
        return const Color(0xFFF97316); // Orange
      case AgentType.audio:
        return const Color(0xFF8B5CF6); // Purple (same as code)
      case AgentType.reasoning:
        return const Color(0xFF6366F1); // Indigo (same as orchestrator)
    }
  }

  String _getStatusText(ReasoningStep? activeStep, bool isCompleted) {
    if (isCompleted) {
      return '✅ 思考完成';
    }
    if (widget.isThinking && activeStep != null) {
      switch (activeStep.agent) {
        case AgentType.orchestrator:
          return '🧠 正在规划...';
        case AgentType.math:
          return '📐 正在计算...';
        case AgentType.code:
          return '💻 正在编码...';
        case AgentType.writing:
          return '✍️ 正在撰写...';
        case AgentType.science:
          return '🔬 正在分析...';
        case AgentType.knowledge:
          return '🌌 正在检索...';
        case AgentType.search:
          return '🔍 正在搜索...';
        case AgentType.dataAnalysis:
          return '📊 正在分析数据...';
        case AgentType.translation:
          return '🌐 正在翻译...';
        case AgentType.image:
          return '🖼️ 正在处理图像...';
        case AgentType.audio:
          return '🎵 正在处理音频...';
        case AgentType.reasoning:
          return '🤔 正在推理...';
      }
    }
    return '准备中...';
  }

  Color _getStatusColor(
      ReasoningStep? activeStep, bool isCompleted, ThemeData theme,) {
    if (isCompleted) return DS.success;
    if (widget.isThinking && activeStep != null) {
      return _getAgentColor(activeStep.agent);
    }
    return theme.colorScheme.onSurfaceVariant;
  }

  ReasoningStep? _getActiveStep() {
    // Find the first in-progress step, or the last completed step
    for (final step in widget.steps) {
      if (step.isInProgress) return step;
    }
    if (widget.steps.isNotEmpty) return widget.steps.last;
    return null;
  }

  void _showCitationDialog(String citation) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
          title: Text('知识引用: $citation'),
          content: const Text(
            '这是一个来自知识星图的节点。\n\n'
            '在实际实现中，这里会显示该知识点的摘要内容，\n'
            '证明AI确实检索了相关知识，而非凭空想象。',
          ),
          actions: [
            SparkleButton.ghost(label: '关闭', onPressed: () => Navigator.pop(context)),
          ],
        ),
    );
  }
}

/// 多智能体协作可视化组件
///
/// 展示多个智能体的协作过程和结果
class MultiAgentCollaborationBubble extends StatelessWidget {

  const MultiAgentCollaborationBubble({
    required this.contributions, super.key,
    this.summary,
    this.isComplete = false,
  });
  final List<AgentContribution> contributions;
  final String? summary;
  final bool isComplete;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8, horizontal: 12),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            DS.brandPrimary.shade50,
            Colors.purple.shade50,
          ],
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: Colors.purple.shade200,
          width: 1.5,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Container(
            padding: const EdgeInsets.all(DS.md),
            decoration: BoxDecoration(
              color: Colors.purple.shade100.withOpacity(0.5),
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(16),
                topRight: Radius.circular(16),
              ),
            ),
            child: Row(
              children: [
                Icon(
                  Icons.groups,
                  color: Colors.purple.shade700,
                  size: 24,
                ),
                const SizedBox(width: DS.sm),
                Expanded(
                  child: Text(
                    '多专家协作回答',
                    style: theme.textTheme.titleMedium?.copyWith(
                      color: Colors.purple.shade700,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                Chip(
                  label: Text('${contributions.length} 位专家'),
                  backgroundColor: Colors.purple.shade100,
                  labelStyle: TextStyle(
                    color: Colors.purple.shade700,
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                  padding: EdgeInsets.zero,
                  visualDensity: VisualDensity.compact,
                ),
                if (isComplete)
                  Container(
                    margin: const EdgeInsets.only(left: 8),
                    child: Icon(Icons.check_circle,
                        color: DS.success, size: 18,),
                  ),
              ],
            ),
          ),

          // Individual Contributions
          ...contributions.map((contribution) => _buildContributionTile(contribution, theme)),

          // Summary (if provided)
          if (summary != null)
            Container(
              margin: const EdgeInsets.all(DS.md),
              padding: const EdgeInsets.all(DS.md),
              decoration: BoxDecoration(
                color: DS.brandPrimary.withOpacity(0.8),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: Colors.purple.shade200,
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(
                        Icons.summarize,
                        color: Colors.purple.shade700,
                        size: 18,
                      ),
                      const SizedBox(width: 6),
                      Text(
                        '综合建议',
                        style: theme.textTheme.labelLarge?.copyWith(
                          color: Colors.purple.shade700,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: DS.sm),
                  Text(
                    summary!,
                    style: theme.textTheme.bodyMedium,
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildContributionTile(AgentContribution contribution, ThemeData theme) => Container(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      padding: const EdgeInsets.all(DS.md),
      decoration: BoxDecoration(
        color: DS.brandPrimaryConst,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: _getAgentColor(contribution.agentType).withOpacity(0.3),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 28,
                height: 28,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: _getAgentColor(contribution.agentType),
                ),
                child: Icon(
                  _getAgentIcon(contribution.agentType),
                  color: DS.brandPrimaryConst,
                  size: 14,
                ),
              ),
              const SizedBox(width: DS.sm),
              Text(
                contribution.agentName,
                style: theme.textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: _getAgentColor(contribution.agentType),
                ),
              ),
              if (contribution.confidence != null) ...[
                const Spacer(),
                Text(
                  '置信度: ${(contribution.confidence! * 100).toStringAsFixed(0)}%',
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ],
          ),
          const SizedBox(height: DS.sm),
          Text(
            contribution.responseText,
            style: theme.textTheme.bodyMedium,
          ),
          if (contribution.citations != null && contribution.citations!.isNotEmpty)
            Container(
              margin: const EdgeInsets.only(top: 8),
              child: Wrap(
                spacing: 6,
                runSpacing: 4,
                children: contribution.citations!.map((citation) => Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: _getAgentColor(contribution.agentType).withOpacity(0.1),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      '📚 $citation',
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: _getAgentColor(contribution.agentType),
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),).toList(),
              ),
            ),
        ],
      ),
    );

  IconData _getAgentIcon(AgentType agent) {
    switch (agent) {
      case AgentType.orchestrator:
        return Icons.psychology;
      case AgentType.math:
        return Icons.functions;
      case AgentType.code:
        return Icons.code;
      case AgentType.writing:
        return Icons.edit;
      case AgentType.science:
        return Icons.science;
      case AgentType.knowledge:
        return Icons.auto_awesome;
      case AgentType.search:
        return Icons.search;
      case AgentType.dataAnalysis:
        return Icons.analytics;
      case AgentType.translation:
        return Icons.translate;
      case AgentType.image:
        return Icons.image;
      case AgentType.audio:
        return Icons.audiotrack;
      case AgentType.reasoning:
        return Icons.psychology_outlined;
    }
  }

  Color _getAgentColor(AgentType agent) {
    switch (agent) {
      case AgentType.orchestrator:
        return const Color(0xFF6366F1);
      case AgentType.math:
        return const Color(0xFF0EA5E9);
      case AgentType.code:
        return const Color(0xFF8B5CF6);
      case AgentType.writing:
        return const Color(0xFFF59E0B);
      case AgentType.science:
        return const Color(0xFF10B981);
      case AgentType.knowledge:
        return const Color(0xFFEC4899);
      case AgentType.search:
        return const Color(0xFF3B82F6);
      case AgentType.dataAnalysis:
        return const Color(0xFF06B6D4);
      case AgentType.translation:
        return const Color(0xFF8B5CF6);
      case AgentType.image:
        return const Color(0xFFF97316);
      case AgentType.audio:
        return const Color(0xFF8B5CF6);
      case AgentType.reasoning:
        return const Color(0xFF6366F1);
    }
  }
}
