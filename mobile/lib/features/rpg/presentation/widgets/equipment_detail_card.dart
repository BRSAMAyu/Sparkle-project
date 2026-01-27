import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/rpg/data/models/rpg_models.dart';

/// 装备详情卡片组件
class EquipmentDetailCard extends StatelessWidget {
  const EquipmentDetailCard({
    super.key,
    required this.equipment,
    this.onEquip,
    this.isEquipped = false,
  });

  final Equipment equipment;
  final VoidCallback? onEquip;
  final bool isEquipped;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(DS.spacing10), // 减小内边距
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: DS.borderRadius16,
        border: Border.all(
          color: isEquipped ? DS.primaryBase : Colors.transparent,
          width: 2,
        ),
        boxShadow: DS.shadowSm,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 装备名称和稀有度
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                equipment.name,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      color: DS.textPrimary,
                      fontWeight: DS.fontWeightBold,
                      fontSize: 15, // 减小字体大小
                    ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: DS.spacing6, vertical: DS.spacing4), // 减小内边距
                decoration: BoxDecoration(
                  color: _getRarityColor(equipment.rarity),
                  borderRadius: DS.borderRadius8,
                ),
                child: Text(
                  _getRarityName(equipment.rarity),
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 11, // 减小字体大小
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),
          
          const SizedBox(height: DS.spacing4), // 减小间距
          
          // 装备类型
          Text(
            _getEquipmentTypeName(equipment.type),
            style: TextStyle(
              color: DS.textSecondary,
              fontSize: 11, // 减小字体大小
            ),
          ),
          
          const SizedBox(height: DS.spacing6), // 减小间距
          
          // 装备描述
          if (equipment.description != null) 
            Text(
              equipment.description!,
              style: TextStyle(
                color: DS.textSecondary,
                fontSize: 11, // 减小字体大小
              ),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          
          const SizedBox(height: DS.spacing8), // 减小间距
          
          // 属性加成
          const Text(
            '属性加成:',
            style: TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 11, // 减小字体大小
            ),
          ),
          
          const SizedBox(height: DS.spacing4), // 减小间距
          
          for (final attr in equipment.attributes)
            Padding(
              padding: const EdgeInsets.only(bottom: DS.spacing4), // 减小间距
              child: Row(
                children: [
                  Text(
                    _getAttributeName(attr.attribute),
                    style: TextStyle(
                      color: DS.textSecondary,
                      fontSize: 11, // 减小字体大小
                    ),
                  ),
                  const Spacer(),
                  Text(
                    '+${attr.value}',
                    style: TextStyle(
                      color: DS.success,
                      fontWeight: FontWeight.bold,
                      fontSize: 11, // 减小字体大小
                    ),
                  ),
                ],
              ),
            ),
          
          const SizedBox(height: DS.spacing8), // 减小间距
          
          // 装备按钮
          if (onEquip != null)
            SizedBox(
              width: double.infinity,
              height: 32, // 减小按钮高度
              child: ElevatedButton(
                onPressed: onEquip,
                style: ElevatedButton.styleFrom(
                  backgroundColor: isEquipped ? DS.neutral400 : DS.primaryBase,
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(
                    borderRadius: DS.borderRadius12,
                  ),
                  textStyle: const TextStyle(
                    fontSize: 13, // 减小字体大小
                  ),
                ),
                child: Text(isEquipped ? '已装备' : '装备'),
              ),
            ),
        ],
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
}
