import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/rpg/data/models/rpg_models.dart';
import 'package:sparkle/features/rpg/presentation/providers/rpg_providers.dart';
import 'package:sparkle/features/rpg/presentation/widgets/equipment_detail_card.dart';
import 'package:sparkle/features/rpg/presentation/widgets/pixel_character.dart';

/// RPG角色页面
class RpgCharacterScreen extends ConsumerWidget {
  const RpgCharacterScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final character = ref.watch(characterProvider);
    final equipmentList = ref.watch(equipmentListProvider);
    final totalAttributes = ref.watch(totalAttributesProvider);
    
    return Scaffold(
      backgroundColor: DS.neutral50,
      appBar: AppBar(
        title: const Text('我的角色'),
        backgroundColor: DS.brandPrimary,
        foregroundColor: Colors.white,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(DS.spacing16),
        child: Column(
          children: [
            // 角色信息卡片
            Container(
              padding: const EdgeInsets.all(DS.spacing24),
              decoration: BoxDecoration(
                color: DS.surfaceSecondary,
                borderRadius: DS.borderRadius16,
                boxShadow: DS.shadowSm,
              ),
              child: Column(
                children: [
                  // 像素角色展示
                  SizedBox(
                    height: 200,
                    child: Center(
                      child: PixelCharacter(
                        character: character,
                        size: 180,
                      ),
                    ),
                  ),
                  
                  const SizedBox(height: DS.spacing24),
                  
                  // 角色基本信息
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                    children: [
                      _StatItem(
                        label: '等级',
                        value: character.level.toString(),
                        color: DS.primaryBase,
                      ),
                      _StatItem(
                        label: '经验',
                        value: character.experience.toString(),
                        color: DS.success,
                      ),
                      _StatItem(
                        label: '登录天数',
                        value: character.totalLoginDays?.toString() ?? '0',
                        color: DS.info,
                      ),
                      _StatItem(
                        label: '职业',
                        value: character.characterClass ?? '无',
                        color: DS.warning,
                      ),
                    ],
                  ),
                ],
              ),
            ),
            
            const SizedBox(height: DS.spacing24),
            
            // 角色属性
            Container(
              padding: const EdgeInsets.all(DS.spacing16),
              decoration: BoxDecoration(
                color: DS.surfaceSecondary,
                borderRadius: DS.borderRadius16,
                boxShadow: DS.shadowSm,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    '角色属性',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  
                  const SizedBox(height: DS.spacing16),
                  
                  GridView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: 2,
                      childAspectRatio: 3,
                      crossAxisSpacing: DS.spacing16,
                      mainAxisSpacing: DS.spacing8,
                    ),
                    itemCount: totalAttributes.length,
                    itemBuilder: (context, index) {
                      final attr = totalAttributes[index];
                      return _AttributeItem(attribute: attr);
                    },
                  ),
                ],
              ),
            ),
            
            const SizedBox(height: DS.spacing24),
            
            // 装备管理
            Container(
              padding: const EdgeInsets.all(DS.spacing16),
              decoration: BoxDecoration(
                color: DS.surfaceSecondary,
                borderRadius: DS.borderRadius16,
                boxShadow: DS.shadowSm,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    '装备管理',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  
                  const SizedBox(height: DS.spacing16),
                  
                  // 装备列表
                  ListView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    itemCount: equipmentList.length,
                    itemBuilder: (context, index) {
                      final equipment = equipmentList[index];
                      final isEquipped = _isEquipped(character, equipment);
                      
                      return Padding(
                        padding: const EdgeInsets.only(bottom: DS.spacing16),
                        child: EquipmentDetailCard(
                          equipment: equipment,
                          isEquipped: isEquipped,
                          onEquip: () {
                            ref.read(characterProvider.notifier).equipItem(
                              equipment.id,
                              equipment.type,
                            );
                          },
                        ),
                      );
                    },
                  ),
                ],
              ),
            ),
            
            const SizedBox(height: DS.spacing24),
            
            // 每日登录奖励按钮
            SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton.icon(
                onPressed: () {
                  ref.read(characterProvider.notifier).updateLoginDays();
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text('每日登录奖励已领取！'),
                      backgroundColor: Colors.green,
                    ),
                  );
                },
                icon: const Icon(Icons.calendar_today),
                label: const Text('领取每日登录奖励'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: DS.brandPrimary,
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(
                    borderRadius: DS.borderRadius12,
                  ),
                  textStyle: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
  
  /// 检查装备是否已装备
  bool _isEquipped(Character character, Equipment equipment) {
    switch (equipment.type) {
      case EquipmentType.hat:
        return character.equipment.hat == equipment.id;
      case EquipmentType.shirt:
        return character.equipment.shirt == equipment.id;
      case EquipmentType.pants:
        return character.equipment.pants == equipment.id;
      case EquipmentType.shoes:
        return character.equipment.shoes == equipment.id;
      case EquipmentType.weapon:
        return character.equipment.weapon == equipment.id;
      case EquipmentType.accessory:
        return character.equipment.accessory == equipment.id;
    }
  }
}

/// 统计项组件
class _StatItem extends StatelessWidget {
  const _StatItem({
    required this.label,
    required this.value,
    required this.color,
  });

  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(
          label,
          style: TextStyle(
            color: DS.textSecondary,
            fontSize: 14,
          ),
        ),
        const SizedBox(height: DS.spacing4),
        Text(
          value,
          style: TextStyle(
            color: color,
            fontSize: 20,
            fontWeight: DS.fontWeightBold,
          ),
        ),
      ],
    );
  }
}

/// 属性项组件
class _AttributeItem extends StatelessWidget {
  const _AttributeItem({required this.attribute});

  final AttributeValue attribute;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(DS.spacing12),
      decoration: BoxDecoration(
        color: DS.surfacePrimary,
        borderRadius: DS.borderRadius8,
        border: Border.all(
          color: DS.neutral300,
          width: 1,
        ),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            _getAttributeName(attribute.attribute),
            style: TextStyle(
              color: DS.textSecondary,
              fontSize: 14,
            ),
          ),
          Text(
            attribute.value.toString(),
            style: TextStyle(
              color: DS.textPrimary,
              fontSize: 16,
              fontWeight: DS.fontWeightBold,
            ),
          ),
        ],
      ),
    );
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
