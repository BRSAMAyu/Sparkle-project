import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_pressable.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/shared/utils/entity_card_payloads.dart';

/// 知识卡片组件
/// 用于在聊天中显示 AI 生成的知识节点
class KnowledgeCard extends StatelessWidget {
  const KnowledgeCard({
    required this.data,
    super.key,
  });
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final entity = EntityCardPayload.fromRaw(data, fallbackType: 'knowledge_node');
    final nodeId = entity.entityId ?? data['id'] as String?;
    final title = entity.title;
    final summary = entity.summary ?? data['summary'] as String?;
    final tags = entity.tags.isNotEmpty
        ? entity.tags
        : (data['tags'] as List?)?.cast<String>() ?? [];
    final masteryLevel =
        (entity.metrics['mastery_level'] as num?)?.toInt() ??
            data['mastery_level'] as int? ??
            0;

    return Card(
      margin: const EdgeInsets.symmetric(vertical: 8),
      elevation: 2,
      child: SparklePressable(
        onTap: () {
          // 导航到知识星图页面，如果有节点ID则聚焦到该节点
          if (entity.detailRoute != null && entity.detailRoute!.isNotEmpty) {
            context.go(entity.detailRoute!);
          } else if (nodeId != null) {
            context.go('/galaxy?nodeId=$nodeId');
          } else {
            context.go('/galaxy');
          }
        },
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: EdgeInsets.all(context.space.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(
                    Icons.lightbulb_outline,
                    color: context.colors.brandPrimary,
                  ),
                  SizedBox(width: context.space.sm),
                  Expanded(
                    child: Text(
                      title,
                      style: context.typo.titleLarge.copyWith(
                        fontWeight: DS.fontWeightBold,
                      ),
                    ),
                  ),
                  _buildMasteryChip(context, masteryLevel),
                ],
              ),
              if (summary != null && summary.isNotEmpty) ...[
                SizedBox(height: context.space.sm),
                Text(
                  summary,
                  style: context.typo.bodyMedium,
                  maxLines: 3,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
              if (tags.isNotEmpty) ...[
                SizedBox(height: context.space.sm),
                Wrap(
                  spacing: 8.0,
                  runSpacing: 4.0,
                  children: tags
                      .map(
                        (tag) => Chip(
                          label: Text(tag, style: context.typo.labelSmall),
                          materialTapTargetSize:
                              MaterialTapTargetSize.shrinkWrap,
                          visualDensity: VisualDensity.compact,
                        ),
                      )
                      .toList(),
                ),
              ],
              SizedBox(height: context.space.md),
              Align(
                alignment: Alignment.bottomRight,
                child: TextButton.icon(
                  onPressed: () {
                    // 导航到知识星图页面
                    context.go('/galaxy');
                  },
                  icon: const Icon(Icons.arrow_forward_ios, size: 16),
                  label: Text(context.l10n.viewDetails),
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
      color = context.colors.semanticSuccess;
      label = context.l10n.knowledgeMasteryLevelMastered;
    } else if (masteryLevel >= 50) {
      color = context.colors.brandPrimary;
      label = context.l10n.knowledgeMasteryLevelPracticing;
    } else if (masteryLevel > 0) {
      color = context.colors.brandPrimary;
      label = context.l10n.knowledgeMasteryLevelBeginner;
    } else {
      color = context.colors.brandPrimary;
      label = context.l10n.knowledgeMasteryLevelUntouched;
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
