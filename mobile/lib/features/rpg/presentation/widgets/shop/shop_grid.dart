import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/rpg/data/models/rpg_models.dart';
import 'package:sparkle/features/rpg/presentation/widgets/rpg_equipment_card.dart';

/// RPG商店网格布局组件 - 优化后的纵向卡片布局
class ShopGrid extends StatelessWidget {
  const ShopGrid({
    super.key,
    required this.equipmentList,
    this.onItemTap,
  });

  final List<Equipment> equipmentList;
  final Function(Equipment)? onItemTap;

  @override
  Widget build(BuildContext context) {
    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      padding: const EdgeInsets.all(DS.spacing12),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2, // 每行2个物品
        crossAxisSpacing: 12.0, // 横向间距
        mainAxisSpacing: 12.0, // 纵向间距
        childAspectRatio: 0.65, // 纵向长方形比例，确保能显示所有内容
      ),
      itemCount: equipmentList.length,
      itemBuilder: (context, index) {
        final equipment = equipmentList[index];
        return _ShopItemCard(
          equipment: equipment,
          onTap: () => onItemTap?.call(equipment),
        );
      },
    );
  }
}

/// 商店物品卡片 - 优化布局确保所有内容显示
class _ShopItemCard extends StatelessWidget {
  const _ShopItemCard({
    required this.equipment,
    this.onTap,
  });

  final Equipment equipment;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          borderRadius: DS.borderRadius16,
          color: DS.surfaceSecondary,
          border: Border.all(
            color: DS.glassBorder,
            width: 1,
          ),
          boxShadow: DS.shadowSm,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            // 图片区域 - 占据剩余空间
            Expanded(
              child: Container(
                margin: const EdgeInsets.only(bottom: DS.spacing8),
                child: Stack(
                  alignment: Alignment.center,
                  children: [
                    // 内衬容器
                    Container(
                      width: double.infinity,
                      height: double.infinity,
                      decoration: BoxDecoration(
                        borderRadius: DS.borderRadius12,
                        color: DS.surfaceTertiary,
                      ),
                    ),
                    // 像素画
                    if (equipment.spritePath != null) ...[
                      Image.asset(
                        equipment.spritePath!,
                        width: 80,
                        height: 80,
                        filterQuality: FilterQuality.none,
                        fit: BoxFit.contain,
                      ),
                    ] else ...[
                      // 占位符
                      Container(
                        width: 80,
                        height: 80,
                        decoration: BoxDecoration(
                          borderRadius: DS.borderRadius8,
                          color: DS.neutral300,
                        ),
                        child: Icon(
                          Icons.image_not_supported,
                          color: DS.neutral500,
                          size: 32,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),

            // 固定高度的文字区域
            Container(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // 装备名称
                  Text(
                    equipment.name,
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: DS.fontWeightBold,
                      color: DS.textPrimary,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),

                  // 装备描述
                  if (equipment.description != null) ...[
                    const SizedBox(height: DS.spacing4),
                    Text(
                      equipment.description!,
                      style: TextStyle(
                        fontSize: 12,
                        color: DS.textSecondary,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],

                  // 价格/稀有度
                  const SizedBox(height: DS.spacing8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: DS.spacing8, vertical: DS.spacing2),
                    decoration: BoxDecoration(
                      borderRadius: DS.borderRadius8,
                      color: _getRarityColor(equipment.rarity),
                    ),
                    child: Text(
                      _getRarityName(equipment.rarity),
                      style: const TextStyle(
                        fontSize: 10,
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// 获取稀有度颜色
  Color _getRarityColor(Rarity? rarity) {
    switch (rarity) {
      case Rarity.common: return DS.neutral400;
      case Rarity.uncommon: return DS.success;
      case Rarity.rare: return DS.info;
      case Rarity.epic: return DS.brandPrimary;
      case Rarity.legendary: return DS.warning;
      default: return DS.neutral400;
    }
  }

  /// 获取稀有度名称
  String _getRarityName(Rarity? rarity) {
    switch (rarity) {
      case Rarity.common: return '普通';
      case Rarity.uncommon: return '稀有';
      case Rarity.rare: return '史诗';
      case Rarity.epic: return '传说';
      case Rarity.legendary: return '神话';
      default: return '普通';
    }
  }
}
