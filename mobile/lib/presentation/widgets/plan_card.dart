import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// 计划卡片组件
/// 用于在聊天中显示 AI 生成的计划
class PlanCard extends StatelessWidget {
  final Map<String, dynamic> data;

  const PlanCard({
    Key? key,
    required this.data,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final planId = data['id'] as String;
    final title = data['title'] as String;
    final planType = data['type'] as String;
    final description = data['description'] as String?;
    final targetDate = data['target_date'] as String?;
    final mastery = (data['target_mastery'] as num?)?.toDouble();

    return Card(
      margin: const EdgeInsets.symmetric(vertical: 8),
      elevation: 2,
      child: InkWell(
        onTap: () {
          // 根据计划类型导航到相应页面
          if (planType == 'sprint') {
            context.push('/sprint');
          } else if (planType == 'growth') {
            context.push('/growth');
          }
        },
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  _buildTypeIcon(planType),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      title,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  _buildPlanTypeChip(context, planType),
                ],
              ),
              
              if (description != null && description.isNotEmpty) ...[
                const SizedBox(height: 8),
                Text(
                  description,
                  style: Theme.of(context).textTheme.bodyMedium,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ],

              const SizedBox(height: 12),
              Row(
                children: [
                  if (targetDate != null) ...[
                    Icon(Icons.calendar_today, size: 16, color: Theme.of(context).hintColor),
                    const SizedBox(width: 4),
                    Text('目标日期: $targetDate'),
                    const SizedBox(width: 16),
                  ],
                  if (mastery != null) ...[
                    Icon(Icons.grade, size: 16, color: Theme.of(context).hintColor),
                    const SizedBox(width: 4),
                    Text('目标掌握度: ${(mastery * 100).toInt()}%'),
                  ],
                  const Spacer(),
                  TextButton.icon(
                    onPressed: () {
                      // 根据计划类型导航到相应页面
                      if (planType == 'sprint') {
                        context.push('/sprint');
                      } else if (planType == 'growth') {
                        context.push('/growth');
                      }
                    },
                    icon: const Icon(Icons.arrow_forward_ios, size: 16),
                    label: const Text('查看计划'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTypeIcon(String type) {
    IconData icon;
    Color color;
    
    switch (type) {
      case 'sprint':
        icon = Icons.directions_run;
        color = Colors.red;
        break;
      case 'growth':
        icon = Icons.trending_up;
        color = Colors.green;
        break;
      default:
        icon = Icons.assignment;
        color = Colors.grey;
    }
    
    return Container(
      padding: const EdgeInsets.all(6),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Icon(icon, size: 20, color: color),
    );
  }

  Widget _buildPlanTypeChip(BuildContext context, String type) {
    Color color;
    String label;
    
    switch (type) {
      case 'sprint':
        color = Colors.red;
        label = '冲刺计划';
        break;
      case 'growth':
        color = Colors.green;
        label = '成长计划';
        break;
      default:
        color = Colors.grey;
        label = type;
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