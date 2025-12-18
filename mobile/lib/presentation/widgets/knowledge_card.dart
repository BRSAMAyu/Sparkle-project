import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// 知识卡片组件
/// 用于在聊天中显示 AI 生成的知识节点
class KnowledgeCard extends StatelessWidget {
  final Map<String, dynamic> data;

  const KnowledgeCard({
    Key? key,
    required this.data,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final nodeId = data['id'] as String;
    final title = data['title'] as String;
    final summary = data['summary'] as String?;
    final tags = (data['tags'] as List?)?.cast<String>() ?? [];
    final masteryLevel = data['mastery_level'] as int? ?? 0;

    return Card(
      margin: const EdgeInsets.symmetric(vertical: 8),
      elevation: 2,
      child: InkWell(
        onTap: () {
          // 导航到知识星图页面
          context.push('/galaxy');
        },
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(Icons.lightbulb_outline, color: Theme.of(context).colorScheme.primary),
                  const SizedBox(width: 8),
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
                const SizedBox(height: 8),
                Text(
                  summary,
                  style: Theme.of(context).textTheme.bodyMedium,
                  maxLines: 3,
                  overflow: TextOverflow.ellipsis,
                ),
              ],

              if (tags.isNotEmpty) ...[
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8.0,
                  runSpacing: 4.0,
                  children: tags.map((tag) => Chip(
                    label: Text(tag, style: Theme.of(context).textTheme.labelSmall),
                    materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                    visualDensity: VisualDensity.compact,
                  )).toList(),
                ),
              ],
              const SizedBox(height: 12),
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
      color = Colors.green;
      label = '已掌握';
    } else if (masteryLevel >= 50) {
      color = Colors.orange;
      label = '熟练中';
    } else if (masteryLevel > 0) {
      color = Colors.blue;
      label = '初涉';
    } else {
      color = Colors.grey;
      label = '未学习';
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Text(
        label,
        style: TextStyle(color: color, fontSize: 12),
      ),
    );
  }
}