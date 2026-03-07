import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/sector_config.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';

class NodePreviewCard extends StatelessWidget {
  const NodePreviewCard({
    required this.node,
    required this.onClose,
    required this.onTap,
    this.bottomInset = 100,
    super.key,
  });

  final GalaxyNodeModel node;
  final VoidCallback onClose;
  final VoidCallback onTap;
  final double bottomInset;

  @override
  Widget build(BuildContext context) {
    final sectorStyle = SectorConfig.getStyle(node.sector);
    final tags = node.autoTags.take(4).toList();

    return Align(
      alignment: Alignment.bottomCenter,
      child: Container(
        margin: EdgeInsets.only(bottom: bottomInset, left: 20, right: 20),
        width: double.infinity,
        constraints: const BoxConstraints(maxWidth: 460),
        child: GraphiteCardSurface(
          padding: const EdgeInsets.all(20),
          borderColor: sectorStyle.primaryColor.withValues(alpha: 0.24),
          child: Material(
            type: MaterialType.transparency,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 4,
                      ),
                      decoration: BoxDecoration(
                        color: sectorStyle.primaryColor.withValues(alpha: 0.2),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                          color:
                              sectorStyle.primaryColor.withValues(alpha: 0.5),
                        ),
                      ),
                      child: Text(
                        sectorStyle.name,
                        style: TextStyle(
                          color: sectorStyle.primaryColor,
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    const Spacer(),
                    SparkleIconButton(
                      variant: ButtonVariant.ghost,
                      size: 28,
                      icon: Icon(Icons.close, size: 20, color: DS.brandPrimary),
                      onPressed: onClose,
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                Text(
                  node.name,
                  style: DS.titleLarge.copyWith(
                    color: DS.textPrimary,
                    fontSize: 22,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  (node.description?.isNotEmpty ?? false)
                      ? node.description!
                      : '探索这个知识点以解锁更多内容。',
                  style: DS.bodyMedium.copyWith(color: DS.textSecondary),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                if (tags.isNotEmpty) ...[
                  const SizedBox(height: 14),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: tags
                        .map(
                          (tag) => Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 10,
                              vertical: 6,
                            ),
                            decoration: BoxDecoration(
                              color: DS.surfacePanel,
                              borderRadius: BorderRadius.circular(999),
                              border: Border.all(
                                color: sectorStyle.primaryColor.withValues(
                                  alpha: 0.24,
                                ),
                              ),
                            ),
                            child: Text(
                              '#$tag',
                              style: DS.labelSmall.copyWith(
                                color: DS.textPrimary,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                        )
                        .toList(),
                  ),
                ],
                const SizedBox(height: 16),
                if (node.isUnlocked) ...[
                  Row(
                    children: [
                      Text(
                        '掌握度',
                        style: DS.labelSmall.copyWith(color: DS.textSecondary),
                      ),
                      const Spacer(),
                      Text(
                        '${node.masteryScore}%',
                        style: DS.labelLarge.copyWith(
                          color: sectorStyle.primaryColor,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(4),
                    child: LinearProgressIndicator(
                      value: node.masteryScore / 100,
                      backgroundColor:
                          DS.surfaceTertiary.withValues(alpha: 0.5),
                      valueColor: AlwaysStoppedAnimation<Color>(
                        sectorStyle.primaryColor,
                      ),
                      minHeight: 6,
                    ),
                  ),
                  const SizedBox(height: 16),
                ],
                Text(
                  '单击进入知识详情，长按后拖拽可以重构局部关系。',
                  style: DS.labelSmall.copyWith(color: DS.textSecondary),
                ),
                const SizedBox(height: 14),
                SizedBox(
                  width: double.infinity,
                  child: SparkleButton(
                    label: '进入学习',
                    expand: true,
                    onPressed: onTap,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
