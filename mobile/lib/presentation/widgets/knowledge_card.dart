import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';

/// 知识卡片组件
/// 用于在聊天中显示 AI 生成的知识节点
class KnowledgeCard extends StatelessWidget {

  const KnowledgeCard({
    required this.data, super.key,
  });
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final nodeId = data['id'] as String?;
    final title = data['title'] as String;
    final summary = data['summary'] as String?;
    final tags = (data['tags'] as List?)?.cast<String>() ?? [];
    final masteryLevel = data['mastery_level'] as int? ?? 0;

    return Card(
      margin: const EdgeInsets.symmetric(vertical: 8),
      elevation: 2,
      child: InkWell(
        onTap: () {
          // 导航到知识星图页面，如果有节点ID则聚焦到该节点
          if (nodeId != null) {
            context.push('/galaxy?nodeId=$nodeId');
          } else {
            context.push('/galaxy');
          }
        },
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: EdgeInsets.all(DS.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(Icons.lightbulb_outline, color: Theme.of(context).colorScheme.primary),
                  SizedBox(width: DS.sm),
                  Expanded(
                    child: Text(
                      title,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  _buildMasteryChip(context, masteryLevel),
                ],
              ),
              
              if (summary != null && summary.isNotEmpty) ...[
                SizedBox(height: DS.sm),
                Text(
                  summary,
                  style: Theme.of(context).textTheme.bodyMedium,
                  maxLines: 3,
                  overflow: TextOverflow.ellipsis,
                ),
              ],

              if (tags.isNotEmpty) ...[
                SizedBox(height: DS.sm),
                Wrap(
                  spacing: 8.0,
                  runSpacing: 4.0,
                  children: tags.map((tag) => Chip(
                    label: Text(tag, style: Theme.of(context).textTheme.labelSmall),
                    materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                    visualDensity: VisualDensity.compact,
                  ),).toList(),
                ),
              ],
              SizedBox(height: DS.md),
              Align(
                alignment: Alignment.bottomRight,
                child: TextButton.icon(
                  onPressed: () {
                    // 导航到知识星图页面
                    context.push('/galaxy');
                  },
                  icon: const Icon(Icons.arrow_forward_ios, size: 16),
                  label: const Text('查看详情'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildMasteryChip(BuildContext context, int masteryLevel) {
    Color color;
    String label;

    if (masteryLevel >= 80) {
      color = DS.success;
      label = '已掌握';
    } else if (masteryLevel >= 50) {
      color = DS.brandPrimary;
      label = '熟练中';
    } else if (masteryLevel > 0) {
      color = DS.brandPrimary;
      label = '初涉';
    } else {
      color = DS.brandPrimary;
      label = '未学习';
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Text(
        label,
        style: TextStyle(color: color, fontSize: 12),
      ),
    );
  }
}