import 'package:flutter/material.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_button_v2.dart';
import 'package:sparkle/core/design/design_system.dart';

/// 智能体推理气泡组件
///
/// 可展开的推理过程显示，展示AI的思考步骤
class AgentReasoningBubble extends StatefulWidget {
  const AgentReasoningBubble({
    required this.agentName,
    required this.agentType,
    required this.reasoning,
    required this.responseText,
    required this.agentColor,
    super.key,
    this.confidence,
    this.citations,
  });

  /// 智能体名称
  final String agentName;

  /// 智能体类型
  final String agentType;

  /// 推理文本
  final String reasoning;

  /// 响应文本
  final String responseText;

  /// 智能体颜色
  final Color agentColor;

  /// 置信度
  final double? confidence;

  /// 引用资料
  final List<Map<String, dynamic>>? citations;

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
      duration: const Duration(milliseconds: 300),
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

  void _showCitationDetails(BuildContext context, Map<String, dynamic> cite) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text((cite['title'] as String?) ?? '详情'),
        content: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              if (cite['score'] != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8.0),
                  child: Chip(
                    label: Text(
                        '相关度: ${((cite['score'] as num) * 100).toStringAsFixed(0)}%',),
                    backgroundColor: widget.agentColor.withValues(alpha: 0.1),
                    labelStyle:
                        TextStyle(color: widget.agentColor, fontSize: 12),
                  ),
                ),
              Text((cite['content'] as String?) ?? '',
                  style: const TextStyle(fontSize: 14, height: 1.5),),
            ],
          ),
        ),
        actions: [
          SparkleButton.ghost(
              label: '关闭', onPressed: () => Navigator.pop(context),),
        ],
      ),
    );
  }

  Widget _buildCitations(BuildContext context) {
    if (widget.citations == null || widget.citations!.isEmpty)
      return const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 0, 12, 8),
          child: Row(
            children: [
              Icon(Icons.library_books, size: 14, color: widget.agentColor),
              const SizedBox(width: DS.xs),
              Text(
                '引用来源 (${widget.citations!.length})',
                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                      color: widget.agentColor,
                      fontWeight: FontWeight.bold,
                    ),
              ),
            ],
          ),
        ),
        SizedBox(
          height: 100,
          child: ListView.builder(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 12),
            itemCount: widget.citations!.length,
            itemBuilder: (context, index) {
              final cite = widget.citations![index];
              return GestureDetector(
                onTap: () => _showCitationDetails(context, cite),
                child: Container(
                  width: 160,
                  margin: const EdgeInsets.only(right: 8),
                  padding: const EdgeInsets.all(DS.sm),
                  decoration: BoxDecoration(
                    color: DS.brandPrimaryConst,
                    borderRadius: BorderRadius.circular(8),
                    border:
                        Border.all(color: widget.agentColor.withValues(alpha: 0.2)),
                    boxShadow: [
                      BoxShadow(
                        color: DS.brandPrimary.withValues(alpha: 0.03),
                        blurRadius: 4,
                        offset: const Offset(0, 2),
                      ),
                    ],
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        cite['title'] ?? '未知来源',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 12,
                          color: widget.agentColor,
                        ),
                      ),
                      const SizedBox(height: DS.xs),
                      Expanded(
                        child: Text(
                          cite['content'] ?? '',
                          maxLines: 3,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                              fontSize: 10, color: DS.brandPrimary.shade700,),
                        ),
                      ),
                    ],
                  ),
                ),
              );
            },
          ),
        ),
        const SizedBox(height: DS.md),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8, horizontal: 12),
      decoration: BoxDecoration(
        color: widget.agentColor.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: widget.agentColor.withValues(alpha: 0.3),
          width: 1.5,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 头部：智能体信息
          InkWell(
            onTap: _toggleExpand,
            borderRadius: BorderRadius.circular(16),
            child: Padding(
              padding: const EdgeInsets.all(DS.md),
              child: Row(
                children: [
                  // 智能体头像
                  Container(
                    width: 32,
                    height: 32,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: widget.agentColor,
                    ),
                    child: Icon(
                      _getAgentIcon(),
                      color: DS.brandPrimaryConst,
                      size: 18,
                    ),
                  ),

                  const SizedBox(width: DS.md),

                  // 智能体名称和类型
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          widget.agentName,
                          style: theme.textTheme.titleSmall?.copyWith(
                            fontWeight: FontWeight.bold,
                            color: widget.agentColor,
                          ),
                        ),
                        if (widget.confidence != null)
                          Text(
                            '置信度: ${(widget.confidence! * 100).toStringAsFixed(0)}%',
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: theme.colorScheme.onSurfaceVariant,
                            ),
                          ),
                      ],
                    ),
                  ),

                  // 展开/收起图标
                  AnimatedRotation(
                    turns: _isExpanded ? 0.5 : 0,
                    duration: const Duration(milliseconds: 300),
                    child: Icon(
                      Icons.keyboard_arrow_down,
                      color: widget.agentColor,
                    ),
                  ),
                ],
              ),
            ),
          ),

          // 引用资料 (Citations)
          _buildCitations(context),

          // 响应内容（始终显示）
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
            child: Text(
              widget.responseText,
              style: theme.textTheme.bodyMedium,
            ),
          ),

          // 推理过程（可展开）
          SizeTransition(
            sizeFactor: _expandAnimation,
            child: Container(
              margin: const EdgeInsets.fromLTRB(12, 0, 12, 12),
              padding: const EdgeInsets.all(DS.md),
              decoration: BoxDecoration(
                color: widget.agentColor.withValues(alpha: 0.05),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: widget.agentColor.withValues(alpha: 0.2),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(
                        Icons.lightbulb_outline,
                        size: 16,
                        color: widget.agentColor,
                      ),
                      const SizedBox(width: 6),
                      Text(
                        '推理过程',
                        style: theme.textTheme.labelLarge?.copyWith(
                          color: widget.agentColor,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: DS.sm),
                  Text(
                    widget.reasoning,
                    style: theme.textTheme.bodySmall?.copyWith(
                      fontStyle: FontStyle.italic,
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  IconData _getAgentIcon() {
    switch (widget.agentType.toLowerCase()) {
      case 'math':
        return Icons.functions;
      case 'code':
        return Icons.code;
      case 'writing':
        return Icons.edit;
      case 'science':
        return Icons.science;
      default:
        return Icons.smart_toy;
    }
  }
}

/// 多智能体协作气泡
///
/// 显示多个智能体的协作结果
class MultiAgentCollaborationBubble extends StatelessWidget {
  const MultiAgentCollaborationBubble({
    required this.contributions,
    super.key,
    this.summary,
  });

  /// 参与的智能体列表
  final List<AgentContribution> contributions;

  /// 总结文本
  final String? summary;

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
          // 协作标题
          Container(
            padding: const EdgeInsets.all(DS.md),
            decoration: BoxDecoration(
              color: Colors.purple.shade100.withValues(alpha: 0.5),
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
              ],
            ),
          ),

          // 各专家贡献
          ...contributions.map(
            (contribution) => AgentReasoningBubble(
              agentName: contribution.agentName,
              agentType: contribution.agentType,
              reasoning: contribution.reasoning,
              responseText: contribution.responseText,
              agentColor: contribution.agentColor,
              confidence: contribution.confidence,
            ),
          ),

          // 综合总结（如果有）
          if (summary != null)
            Container(
              margin: const EdgeInsets.all(DS.md),
              padding: const EdgeInsets.all(DS.md),
              decoration: BoxDecoration(
                color: DS.brandPrimary.withValues(alpha: 0.8),
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
}

/// 智能体贡献信息
class AgentContribution {
  AgentContribution({
    required this.agentName,
    required this.agentType,
    required this.reasoning,
    required this.responseText,
    required this.agentColor,
    this.confidence,
  });
  final String agentName;
  final String agentType;
  final String reasoning;
  final String responseText;
  final Color agentColor;
  final double? confidence;
}
