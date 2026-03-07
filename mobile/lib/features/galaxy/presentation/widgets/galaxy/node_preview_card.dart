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
        constraints: const BoxConstraints(maxWidth: 400),
        child: Material(
          color: Colors.transparent,
          child: Container(
            padding: const EdgeInsets.all(DS.lg),
            decoration: BoxDecoration(
              color: const Color(0xFF111827).withValues(alpha: 0.94),
              borderRadius: BorderRadius.circular(18),
              border: Border.all(
                color: sectorStyle.primaryColor.withValues(alpha: 0.42),
                width: 1.2,
              ),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.28),
                  blurRadius: 28,
                  offset: const Offset(0, 14),
                ),
                BoxShadow(
                  color: sectorStyle.primaryColor.withValues(alpha: 0.12),
                  blurRadius: 16,
                  spreadRadius: 1,
                ),
              ],
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Header
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
                          fontSize: 10,
                          fontWeight: FontWeight.bold,
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

                // Title
                Text(
                  node.name,
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 20,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 8),

                // Description (Placeholder if not available)
                Text(
                  (node.description?.isNotEmpty ?? false)
                      ? node.description!
                      : '探索这个知识点以解锁更多内容。',
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.68),
                    fontSize: 14,
                  ),
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
                              color: Colors.white.withValues(alpha: 0.05),
                              borderRadius: BorderRadius.circular(999),
                              border: Border.all(
                                color: sectorStyle.primaryColor
                                    .withValues(alpha: 0.24),
                              ),
                            ),
                            child: Text(
                              '#$tag',
                              style: TextStyle(
                                color: Colors.white.withValues(alpha: 0.84),
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                        )
                        .toList(),
                  ),
                ],
                const SizedBox(height: 16),

                // Progress Bar
                if (node.isUnlocked) ...[
                  Row(
                    children: [
                      Text(
                        '掌握度',
                        style: TextStyle(
                          color: Colors.white.withValues(alpha: 0.55),
                          fontSize: 12,
                        ),
                      ),
                      const Spacer(),
                      Text(
                        '${node.masteryScore}%',
                        style: TextStyle(
                          color: sectorStyle.primaryColor,
                          fontWeight: FontWeight.bold,
                          fontSize: 12,
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
                  '长按并拖拽星点，可像关系图谱一样重构局部网络。',
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.48),
                    fontSize: 11,
                  ),
                ),
                const SizedBox(height: 14),

                // Action Button
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
