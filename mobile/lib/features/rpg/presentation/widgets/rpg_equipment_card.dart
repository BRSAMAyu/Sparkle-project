import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/rpg/data/models/rpg_models.dart';

/// 现代复古风格装备卡片组件 - 结合毛玻璃效果与像素画
class RpgEquipmentCard extends StatelessWidget {
  const RpgEquipmentCard({
    super.key,
    required this.equipment,
    this.onTap,
    this.isEquipped = false,
  });

  final Equipment equipment;
  final VoidCallback? onTap;
  final bool isEquipped;

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
            color: isEquipped ? DS.primaryBase : DS.glassBorder,
            width: isEquipped ? 2 : 1,
          ),
          boxShadow: DS.shadowSm,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            // 像素画展示区域
            Container(
              margin: const EdgeInsets.only(bottom: DS.spacing8),
              child: Stack(
                alignment: Alignment.center,
                children: [
                  // 内衬容器 - 深色背景衬托像素画
                  Container(
                    width: 80,
                    height: 80,
                    decoration: BoxDecoration(
                      borderRadius: DS.borderRadius12,
                      color: DS.surfaceTertiary,
                    ),
                  ),
                  // 像素画
                  if (equipment.spritePath != null) ...[
                    Image.asset(
                      equipment.spritePath!,
                      width: 64,
                      height: 64,
                      filterQuality: FilterQuality.none, // 确保像素画清晰
                      fit: BoxFit.contain,
                    ),
                  ] else ...[
                    // 占位符
                    Container(
                      width: 64,
                      height: 64,
                      decoration: BoxDecoration(
                        borderRadius: DS.borderRadius8,
                        color: DS.neutral300,
                      ),
                      child: Icon(
                        Icons.image_not_supported,
                        color: DS.neutral500,
                      ),
                    ),
                  ],
                ],
              ),
            ),

            // 装备名称
            Text(
              equipment.name,
              style: TextStyle(
                fontSize: 14,
                fontWeight: DS.fontWeightBold,
                color: DS.textPrimary,
              ),
              textAlign: TextAlign.center,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),

            // 装备类型
            Text(
              _getEquipmentTypeName(equipment.type),
              style: TextStyle(
                fontSize: 11,
                color: DS.textSecondary,
              ),
              textAlign: TextAlign.center,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),

            const SizedBox(height: DS.spacing8),

            // 装备属性
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  for (final attr in equipment.attributes.take(2)) // 最多显示2个属性
                    Padding(
                      padding: const EdgeInsets.only(bottom: DS.spacing4),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            _getAttributeName(attr.attribute),
                            style: TextStyle(
                              fontSize: 11,
                              color: DS.textSecondary,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                          Text(
                            '+${attr.value}',
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: DS.fontWeightBold,
                              color: DS.success,
                            ),
                          ),
                        ],
                      ),
                    ),
                ],
              ),
            ),

            // 稀有度指示器
            if (equipment.rarity != null) ...[
              const SizedBox(height: DS.spacing8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: DS.spacing8, vertical: DS.spacing2),
                decoration: BoxDecoration(
                  borderRadius: DS.borderRadius8,
                  color: _getRarityColor(equipment.rarity!),
                ),
                child: Text(
                  _getRarityName(equipment.rarity!),
                  style: const TextStyle(
                    fontSize: 10,
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  /// 获取装备类型名称
  String _getEquipmentTypeName(EquipmentType type) {
    switch (type) {
      case EquipmentType.hat: return '帽子';
      case EquipmentType.shirt: return '上衣';
      case EquipmentType.pants: return '裤子';
      case EquipmentType.shoes: return '鞋子';
      case EquipmentType.weapon: return '武器';
      case EquipmentType.accessory: return '饰品';
    }
  }

  /// 获取属性名称
  String _getAttributeName(CharacterAttribute attribute) {
    switch (attribute) {
      case CharacterAttribute.strength: return '力量';
      case CharacterAttribute.intelligence: return '智力';
      case CharacterAttribute.agility: return '敏捷';
      case CharacterAttribute.vitality: return '活力';
      case CharacterAttribute.luck: return '幸运';
    }
  }

  /// 获取稀有度颜色
  Color _getRarityColor(Rarity rarity) {
    switch (rarity) {
      case Rarity.common: return DS.neutral400;
      case Rarity.uncommon: return DS.success;
      case Rarity.rare: return DS.info;
      case Rarity.epic: return DS.brandPrimary;
      case Rarity.legendary: return DS.warning;
    }
  }

  /// 获取稀有度名称
  String _getRarityName(Rarity rarity) {
    switch (rarity) {
      case Rarity.common: return '普通';
      case Rarity.uncommon: return '稀有';
      case Rarity.rare: return '史诗';
      case Rarity.epic: return '传说';
      case Rarity.legendary: return '神话';
    }
  }
}
