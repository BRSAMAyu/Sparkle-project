import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/data/models/galaxy_model.dart';
import 'package:sparkle/presentation/widgets/galaxy/sector_config.dart';

class NodePreviewCard extends StatelessWidget {

  const NodePreviewCard({
    required this.node,
    required this.onClose,
    required this.onTap,
    super.key,
  });
  final GalaxyNodeModel node;
  final VoidCallback onClose;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final sectorStyle = SectorConfig.getStyle(node.sector);

    return Align(
      alignment: Alignment.bottomCenter,
      child: Container(
        margin: const EdgeInsets.only(bottom: 100, left: 20, right: 20),
        width: double.infinity,
        constraints: BoxConstraints(maxWidth: 400),
        child: Material(
          color: Colors.transparent,
          child: Container(
            padding: EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: DS.brandSecondary.withValues(alpha: 0.9),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: sectorStyle.primaryColor.withValues(alpha: 0.5),
                width: 1.5,
              ),
              boxShadow: [
                BoxShadow(
                  color: DS.shadowColor.withValues(alpha: 0.5),  // 使用设计系统阴影色
                  blurRadius: 20,
                  offset: const Offset(0, 10),
                ),
                BoxShadow(
                  color: sectorStyle.primaryColor.withValues(alpha: 0.2),
                  blurRadius: 10,
                  spreadRadius: 2,
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
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: sectorStyle.primaryColor.withValues(alpha: 0.2),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: sectorStyle.primaryColor.withValues(alpha: 0.5)),
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
                    Spacer(),
                    IconButton(
                      icon: Icon(Icons.close, size: 20, color: DS.brandPrimary),
                      onPressed: onClose,
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints(),
                    ),
                  ],
                ),
                SizedBox(height: 12),
                
                // Title
                Text(
                  node.name,
                  style: TextStyle(
                    color: DS.brandPrimaryConst,
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),

                // Description (Placeholder if not available)
                Text(
                  (node.description?.isNotEmpty ?? false) 
                    ? node.description! 
                    : '探索这个知识点以解锁更多内容。',
                  style: TextStyle(
                    color: DS.brandPrimary.withValues(alpha: 0.7),
                    fontSize: 14,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 16),

                // Progress Bar
                if (node.isUnlocked) ...[
                  Row(
                    children: [
                      Text(
                        '掌握度',
                        style: TextStyle(
                          color: DS.brandPrimary.withValues(alpha: 0.6),
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
                      backgroundColor: DS.neutral200.withValues(alpha: 0.5),  // 使用设计系统背景色
                      valueColor: AlwaysStoppedAnimation<Color>(sectorStyle.primaryColor),
                      minHeight: 6,
                    ),
                  ),
                  const SizedBox(height: 16),
                ],

                // Action Button
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: onTap,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: sectorStyle.primaryColor,
                      foregroundColor: Colors.white,
                      elevation: 0,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                      padding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                    child: const Text('进入学习'),
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
