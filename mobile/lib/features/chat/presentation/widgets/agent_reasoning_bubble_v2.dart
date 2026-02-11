import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/utils/theme_utils.dart';
import 'package:sparkle/features/chat/data/models/reasoning_step_model.dart';

/// 🧠 Chain of Thought Visualization Bubble
///
/// 展示AI的思考过程，包括：
/// - 动态Agent图标切换
/// - 可展开的步骤流
/// - 实时状态更新
/// - GraphRAG引用展示
class AgentReasoningBubble extends StatefulWidget {
  const AgentReasoningBubble({
    required this.steps,
    super.key,
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
    with TickerProviderStateMixin {
  bool _isExpanded = false;
  late AnimationController _animationController;
  late Animation<double> _expandAnimation;
  late AnimationController _shimmerController;
  bool _isShimmerRunning = false;

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

    _shimmerController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    );
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _syncShimmerState();
  }

  @override
  void didUpdateWidget(covariant AgentReasoningBubble oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.isThinking != widget.isThinking) {
      _syncShimmerState();
    }
  }

  void _syncShimmerState() {
    final shouldAnimate = widget.isThinking && !context.reduceMotion;
    if (shouldAnimate == _isShimmerRunning) return;
    _isShimmerRunning = shouldAnimate;
    if (shouldAnimate) {
      unawaited(_shimmerController.repeat());
      return;
    }
    _shimmerController.stop();
    _shimmerController.value = 0;
  }

  @override
  void dispose() {
    _animationController.dispose();
    _shimmerController.dispose();
    super.dispose();
  }

  void _toggleExpand() {
    if (!mounted) return;
    final reduceMotion = context.reduceMotion;
    setState(() {
      _isExpanded = !_isExpanded;
      if (reduceMotion) {
        _animationController.value = _isExpanded ? 1 : 0;
      } else if (_isExpanded) {
        unawaited(_animationController.forward());
      } else {
        unawaited(_animationController.reverse());
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    if (widget.steps.isEmpty) {
      return const SizedBox.shrink();
    }

    final activeStep = _getActiveStep();

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8, horizontal: 12),
      decoration: BoxDecoration(
        color: context.sparkleColors.surfaceTertiary.withValues(alpha: 0.3),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: context.sparkleColors.brandPrimary.withValues(alpha: 0.2),
          width: 1.5,
        ),
        boxShadow: [
          BoxShadow(
            color: context.sparkleColors.brandPrimary.withValues(alpha: 0.1),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header - Always visible
          _buildHeader(context, activeStep),

          // Expandable Stream
          SizeTransition(
            sizeFactor: context.reduceMotion
                ? AlwaysStoppedAnimation<double>(_isExpanded ? 1 : 0)
                : _expandAnimation,
            child: _buildStepStream(context),
          ),
        ],
      ),
    );
  }

  Widget _buildHeader(BuildContext context, ReasoningStep? activeStep) {
    final isCompleted =
        !widget.isThinking && widget.steps.every((s) => s.isCompleted);
    final reduceMotion = context.reduceMotion;
    final transitionDuration = reduceMotion ? Duration.zero : DS.normal;
    final activeAgentColor =
        _getAgentColor(context, activeStep?.agent ?? AgentType.orchestrator);

    final headerContent = InkWell(
      onTap: _toggleExpand,
      borderRadius: BorderRadius.circular(16),
      child: Padding(
        padding: EdgeInsets.all(context.sparkleSpacing.md),
        child: Row(
          children: [
            // Animated Agent Icon
            AnimatedContainer(
              duration: transitionDuration,
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: activeAgentColor,
                boxShadow: widget.isThinking
                    ? [
                        BoxShadow(
                          color: activeAgentColor.withValues(alpha: 0.4),
                          blurRadius: 8,
                          spreadRadius: 2,
                        ),
                      ]
                    : null,
              ),
              child: AnimatedSwitcher(
                duration: transitionDuration,
                child: Icon(
                  _getAgentIcon(activeStep?.agent ?? AgentType.orchestrator),
                  color: ThemeUtils.getContrastSafeText(
                    activeAgentColor,
                    darkText: context.sparkleColors.textPrimary,
                  ),
                  size: 18,
                  key: ValueKey(activeStep?.agent ?? AgentType.orchestrator),
                ),
              ),
            ),

            SizedBox(width: context.sparkleSpacing.md),

            // Status Text
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _getStatusText(activeStep, isCompleted),
                    style: context.sparkleTypography.bodyMedium.copyWith(
                      fontWeight: FontWeight.w600,
                      color: _getStatusColor(activeStep, isCompleted, context),
                    ),
                  ),
                  if (widget.totalDurationMs != null && isCompleted)
                    Text(
                      '耗时: ${(widget.totalDurationMs! / 1000).toStringAsFixed(1)}s',
                      style: context.sparkleTypography.labelSmall.copyWith(
                        color: context.sparkleColors.textSecondary,
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
                    _getAgentColor(context, activeStep.agent),
                  ),
                ),
              )
            else if (isCompleted)
              Icon(
                Icons.check_circle,
                color: context.sparkleColors.semanticSuccess,
                size: 20,
              )
            else
              AnimatedRotation(
                turns: _isExpanded ? 0.5 : 0,
                duration: transitionDuration,
                child: Icon(
                  Icons.keyboard_arrow_down,
                  color: context.sparkleColors.brandPrimary,
                ),
              ),
          ],
        ),
      ),
    );

    if (!widget.isThinking) {
      return headerContent;
    }

    // Shimmer effect for thinking state
    if (context.reduceMotion) {
      return headerContent;
    }

    return AnimatedBuilder(
      animation: _shimmerController,
      builder: (context, child) => ShaderMask(
        shaderCallback: (bounds) => LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            context.sparkleColors.rimLight,
            context.sparkleColors.rimLight,
            context.sparkleColors.rimLight.withValues(alpha: 0.7),
            context.sparkleColors.rimLight,
            context.sparkleColors.rimLight,
          ],
          stops: [
            0.0,
            (_shimmerController.value - 0.2).clamp(0.0, 1.0),
            _shimmerController.value,
            (_shimmerController.value + 0.2).clamp(0.0, 1.0),
            1.0,
          ],
        ).createShader(bounds),
        child: child,
      ),
      child: headerContent,
    );
  }

  Widget _buildStepStream(BuildContext context) => Container(
        margin: const EdgeInsets.fromLTRB(12, 0, 12, 12),
        padding: EdgeInsets.all(context.sparkleSpacing.md),
        decoration: BoxDecoration(
          color: context.sparkleColors.surfacePrimary,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: context.sparkleColors.neutral200.withValues(alpha: 0.1),
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
                  color: context.sparkleColors.brandPrimary,
                ),
                const SizedBox(width: 6),
                Text(
                  '思考过程',
                  style: context.sparkleTypography.labelLarge.copyWith(
                    color: context.sparkleColors.brandPrimary,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const Spacer(),
                Text(
                  '${widget.steps.length} steps',
                  style: context.sparkleTypography.labelSmall.copyWith(
                    color: context.sparkleColors.textSecondary,
                  ),
                ),
              ],
            ),

            SizedBox(height: context.sparkleSpacing.md),

            // Steps List
            ...widget.steps.asMap().entries.map((entry) {
              final index = entry.key;
              final step = entry.value;
              final isLast = index == widget.steps.length - 1;

              return _buildStepItem(context, step, isLast);
            }),
          ],
        ),
      );

  Widget _buildStepItem(
    BuildContext context,
    ReasoningStep step,
    bool isLast,
  ) =>
      Column(
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
                child: _buildStepStatusIcon(context, step.status),
              ),

              SizedBox(width: context.sparkleSpacing.sm),

              // Step Content
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Description
                    Text(
                      step.description,
                      style: context.sparkleTypography.labelSmall.copyWith(
                        fontWeight: FontWeight.w500,
                        color: context.sparkleColors.textPrimary,
                      ),
                    ),

                    // Tool Output (if any)
                    if (step.toolOutput != null && step.toolOutput!.isNotEmpty)
                      Container(
                        margin: const EdgeInsets.only(top: 6),
                        padding: EdgeInsets.all(context.sparkleSpacing.sm),
                        decoration: BoxDecoration(
                          color: context.sparkleColors.surfaceTertiary,
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: SelectableText(
                          step.toolOutput!,
                          style: TextStyle(
                            fontFamily: 'monospace',
                            fontSize: 11,
                            color: context.sparkleColors.semanticSuccess,
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
                          children: step.citations!
                              .map(
                                (citation) => InkWell(
                                  onTap: () => _showCitationDialog(citation),
                                  borderRadius: BorderRadius.circular(12),
                                  child: Container(
                                    padding: const EdgeInsets.symmetric(
                                      horizontal: 8,
                                      vertical: 4,
                                    ),
                                    decoration: BoxDecoration(
                                      color: context.sparkleColors.brandPrimary
                                          .withValues(alpha: 0.1),
                                      borderRadius: BorderRadius.circular(12),
                                      border: Border.all(
                                        color: context
                                            .sparkleColors.brandPrimary
                                            .withValues(alpha: 0.3),
                                      ),
                                    ),
                                    child: Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        Icon(
                                          Icons.book,
                                          size: 12,
                                          color: context
                                              .sparkleColors.brandPrimary,
                                        ),
                                        const SizedBox(width: 4),
                                        Text(
                                          '引用: $citation',
                                          style: TextStyle(
                                            fontSize: 11,
                                            color: context
                                                .sparkleColors.brandPrimary,
                                            fontWeight: FontWeight.w500,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ),
                              )
                              .toList(),
                        ),
                      ),

                    // Duration
                    if (step.durationMs != null)
                      Container(
                        margin: const EdgeInsets.only(top: 4),
                        child: Text(
                          '${step.durationMs}ms',
                          style: context.sparkleTypography.labelSmall.copyWith(
                            color: context.sparkleColors.textSecondary,
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
              color: context.sparkleColors.neutral200.withValues(alpha: 0.1),
            ),
        ],
      );

  Widget _buildStepStatusIcon(BuildContext context, StepStatus status) {
    switch (status) {
      case StepStatus.completed:
        return Icon(
          Icons.check_circle,
          color: context.sparkleColors.semanticSuccess,
          size: 16,
        );
      case StepStatus.inProgress:
        return const SizedBox(
          width: 16,
          height: 16,
          child: CircularProgressIndicator(
            strokeWidth: 2,
          ),
        );
      case StepStatus.failed:
        return Icon(
          Icons.error,
          color: context.sparkleColors.semanticError,
          size: 16,
        );
      case StepStatus.pending:
        return Icon(
          Icons.radio_button_unchecked,
          color: context.sparkleColors.textDisabled,
          size: 16,
        );
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

  Color _getAgentColor(BuildContext context, AgentType agent) {
    switch (agent) {
      case AgentType.orchestrator:
        return context.sparkleColors.brandPrimary;
      case AgentType.math:
        return context.sparkleColors.semanticInfo;
      case AgentType.code:
        return context.sparkleColors.taskReflection;
      case AgentType.writing:
        return context.sparkleColors.semanticWarning;
      case AgentType.science:
        return context.sparkleColors.semanticSuccess;
      case AgentType.knowledge:
        return context.sparkleColors.planGrowth;
      case AgentType.search:
        return context.sparkleColors.taskLearning;
      case AgentType.dataAnalysis:
        return context.sparkleColors.taskPlanning;
      case AgentType.translation:
        return context.sparkleColors.brandSecondary;
      case AgentType.image:
        return context.sparkleColors.taskTraining;
      case AgentType.audio:
        return context.sparkleColors.taskReflection;
      case AgentType.reasoning:
        return context.sparkleColors.brandPrimary;
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
    ReasoningStep? activeStep,
    bool isCompleted,
    BuildContext context,
  ) {
    if (isCompleted) return context.sparkleColors.semanticSuccess;
    if (widget.isThinking && activeStep != null) {
      return _getAgentColor(context, activeStep.agent);
    }
    return context.sparkleColors.textSecondary;
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
    if (!mounted) return;
    unawaited(
      showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: Text('知识引用: $citation'),
          content: const Text(
            '这是一个来自知识星图的节点。\n\n'
            '在实际实现中，这里会显示该知识点的摘要内容，\n'
            '证明AI确实检索了相关知识，而非凭空想象。',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('关闭'),
            ),
          ],
        ),
      ),
    );
  }
}

/// 多智能体协作可视化组件
///
/// 展示多个智能体的协作过程和结果
class MultiAgentCollaborationBubble extends StatelessWidget {
  const MultiAgentCollaborationBubble({
    required this.contributions,
    super.key,
    this.summary,
    this.isComplete = false,
  });
  final List<AgentContribution> contributions;
  final String? summary;
  final bool isComplete;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final accent = context.sparkleColors.taskReflection;
    final accentSoft = accent.withValues(alpha: 0.08);
    final accentBorder = accent.withValues(alpha: 0.25);

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8, horizontal: 12),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            context.sparkleColors.surfacePrimary,
            accentSoft,
          ],
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: accentBorder,
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
              color: accent.withValues(alpha: 0.12),
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(16),
                topRight: Radius.circular(16),
              ),
            ),
            child: Row(
              children: [
                Icon(
                  Icons.groups,
                  color: accent,
                  size: 24,
                ),
                const SizedBox(width: DS.sm),
                Expanded(
                  child: Text(
                    '多专家协作回答',
                    style: theme.textTheme.titleMedium?.copyWith(
                      color: accent,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                Chip(
                  label: Text('${contributions.length} 位专家'),
                  backgroundColor: accent.withValues(alpha: 0.14),
                  labelStyle: TextStyle(
                    color: accent,
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                  padding: EdgeInsets.zero,
                  visualDensity: VisualDensity.compact,
                ),
                if (isComplete)
                  Container(
                    margin: const EdgeInsets.only(left: 8),
                    child: Icon(
                      Icons.check_circle,
                      color: DS.success,
                      size: 18,
                    ),
                  ),
              ],
            ),
          ),

          // Individual Contributions
          ...contributions.map(
            (contribution) =>
                _buildContributionTile(context, contribution, theme),
          ),

          // Summary (if provided)
          if (summary != null)
            Container(
              margin: const EdgeInsets.all(DS.md),
              padding: const EdgeInsets.all(DS.md),
              decoration: BoxDecoration(
                color: DS.brandPrimary.withValues(alpha: 0.8),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: accentBorder,
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(
                        Icons.summarize,
                        color: accent,
                        size: 18,
                      ),
                      const SizedBox(width: 6),
                      Text(
                        '综合建议',
                        style: theme.textTheme.labelLarge?.copyWith(
                          color: accent,
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

  Widget _buildContributionTile(
    BuildContext context,
    AgentContribution contribution,
    ThemeData theme,
  ) =>
      Container(
        margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        padding: const EdgeInsets.all(DS.md),
        decoration: BoxDecoration(
          color: DS.brandPrimaryConst,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: _getAgentColor(context, contribution.agentType)
                .withValues(alpha: 0.3),
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
                    color: _getAgentColor(context, contribution.agentType),
                  ),
                  child: Icon(
                    _getAgentIcon(contribution.agentType),
                    color: ThemeUtils.getContrastSafeText(
                      _getAgentColor(context, contribution.agentType),
                      darkText: context.sparkleColors.textPrimary,
                    ),
                    size: 14,
                  ),
                ),
                const SizedBox(width: DS.sm),
                Text(
                  contribution.agentName,
                  style: theme.textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: _getAgentColor(context, contribution.agentType),
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
            if (contribution.citations != null &&
                contribution.citations!.isNotEmpty)
              Container(
                margin: const EdgeInsets.only(top: 8),
                child: Wrap(
                  spacing: 6,
                  runSpacing: 4,
                  children: contribution.citations!
                      .map(
                        (citation) => Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 6,
                            vertical: 2,
                          ),
                          decoration: BoxDecoration(
                            color:
                                _getAgentColor(context, contribution.agentType)
                                    .withValues(alpha: 0.1),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Text(
                            '📚 $citation',
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: _getAgentColor(
                                context,
                                contribution.agentType,
                              ),
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ),
                      )
                      .toList(),
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

  Color _getAgentColor(BuildContext context, AgentType agent) {
    switch (agent) {
      case AgentType.orchestrator:
        return context.sparkleColors.brandPrimary;
      case AgentType.math:
        return context.sparkleColors.semanticInfo;
      case AgentType.code:
        return context.sparkleColors.taskReflection;
      case AgentType.writing:
        return context.sparkleColors.semanticWarning;
      case AgentType.science:
        return context.sparkleColors.semanticSuccess;
      case AgentType.knowledge:
        return context.sparkleColors.planGrowth;
      case AgentType.search:
        return context.sparkleColors.taskLearning;
      case AgentType.dataAnalysis:
        return context.sparkleColors.taskPlanning;
      case AgentType.translation:
        return context.sparkleColors.brandSecondary;
      case AgentType.image:
        return context.sparkleColors.taskTraining;
      case AgentType.audio:
        return context.sparkleColors.taskReflection;
      case AgentType.reasoning:
        return context.sparkleColors.brandPrimary;
    }
  }
}
