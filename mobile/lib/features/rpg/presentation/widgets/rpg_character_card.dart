import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/rpg/data/models/rpg_models.dart';
import 'package:sparkle/features/rpg/presentation/providers/rpg_providers.dart';
import 'package:sparkle/features/rpg/presentation/widgets/pixel_character.dart';

/// RPG角色卡片组件 - 实现"Pixel in Glass"设计风格
class RpgCharacterCard extends ConsumerWidget {
  const RpgCharacterCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final character = ref.watch(characterProvider);
    final totalAttributes = ref.watch(totalAttributesProvider);
    
    // 计算HP和XP百分比
    final hpPercentage = (character.currentHp / character.maxHp) * 100;
    final xpPercentage = (character.experience / character.maxExperience) * 100;

    return Container(
      decoration: BoxDecoration(
        borderRadius: DS.borderRadius20,
        color: DS.surfacePrimary,
        boxShadow: DS.shadowLg,
        border: Border.all(
          color: DS.glassBorder,
          width: 1,
        ),
      ),
      padding: const EdgeInsets.all(DS.spacing12),
      child: Column(
        children: [
          // 角色信息行 - 等级和名称
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    character.nickname,
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: DS.fontWeightBold,
                      color: DS.textPrimary,
                    ),
                  ),
                  const SizedBox(height: DS.spacing4),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: DS.spacing8, vertical: DS.spacing4),
                    decoration: BoxDecoration(
                      color: DS.primaryBase,
                      borderRadius: DS.borderRadius12,
                    ),
                    child: Text(
                      '等级 ${character.level}',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ],
              ),
              // 登录天数
              if (character.totalLoginDays != null) ...[
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: DS.spacing8, vertical: DS.spacing4),
                  decoration: BoxDecoration(
                    color: DS.surfaceSecondary,
                    borderRadius: DS.borderRadius12,
                  ),
                  child: Row(
                    children: [
                      Icon(
                        Icons.calendar_today,
                        size: 14,
                        color: DS.textSecondary,
                      ),
                      const SizedBox(width: DS.spacing4),
                      Text(
                        '登录 ${character.totalLoginDays} 天',
                        style: TextStyle(
                          fontSize: 10,
                          color: DS.textSecondary,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
          
          const SizedBox(height: DS.spacing16),
          
          // 像素角色渲染区域
          Container(
            decoration: BoxDecoration(
              color: DS.surfaceSecondary,
              borderRadius: DS.borderRadius16,
              boxShadow: DS.shadowSm,
            ),
            padding: const EdgeInsets.all(DS.spacing16),
            child: PixelCharacter(character: character, size: 60),
          ),
          
          const SizedBox(height: DS.spacing16),
          
          // 状态条 - HP和XP
          Column(
            children: [
              // HP条
              _StatusBar(
                label: '生命值',
                value: character.currentHp,
                maxValue: character.maxHp,
                percentage: hpPercentage,
                color: DS.error,
                icon: Icons.favorite,
              ),
              const SizedBox(height: DS.spacing12),
              // XP条
              _StatusBar(
                label: '经验值',
                value: character.experience,
                maxValue: character.maxExperience,
                percentage: xpPercentage,
                color: DS.primaryBase,
                icon: Icons.star,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

/// 状态条组件
class _StatusBar extends StatelessWidget {
  const _StatusBar({
    required this.label,
    required this.value,
    required this.maxValue,
    required this.percentage,
    required this.color,
    required this.icon,
  });

  final String label;
  final int value;
  final int maxValue;
  final double percentage;
  final Color color;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // 标签和数值
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Row(
              children: [
                Icon(
                  icon,
                  size: 16,
                  color: color,
                ),
                const SizedBox(width: DS.spacing4),
                Text(
                  label,
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: DS.fontWeightMedium,
                    color: DS.textPrimary,
                  ),
                ),
              ],
            ),
            Text(
              '$value / $maxValue',
              style: TextStyle(
                fontSize: 14,
                fontWeight: DS.fontWeightMedium,
                color: DS.textPrimary,
              ),
            ),
          ],
        ),
        
        const SizedBox(height: DS.spacing4),
        
        // 进度条容器
        Container(
          height: 20,
          decoration: BoxDecoration(
            color: DS.surfaceSecondary,
            borderRadius: DS.borderRadius12,
            border: Border.all(
              color: DS.neutral300,
              width: 1,
            ),
          ),
          child: Stack(
            children: [
              // 进度条
              AnimatedContainer(
                duration: const Duration(milliseconds: 300),
                height: double.infinity,
                width: percentage > 0 ? (percentage / 100) * double.infinity : 0,
                decoration: BoxDecoration(
                  color: color,
                  borderRadius: DS.borderRadius12,
                ),
              ),
              // 玻璃效果覆盖
              Container(
                height: double.infinity,
                decoration: BoxDecoration(
                  borderRadius: DS.borderRadius12,
                  color: DS.glassBackground.withValues(alpha: 0.1),
                  border: Border.all(
                    color: Colors.white.withValues(alpha: 0.1),
                    width: 1,
                  ),
                )
              ),
              // 百分比文本
              Center(
                child: Text(
                  '${percentage.toInt()}%',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

/// 货币芯片组件
class _CurrencyChip extends StatelessWidget {
  const _CurrencyChip({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
  });

  final IconData icon;
  final String label;
  final int value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: DS.spacing16, vertical: DS.spacing8),
      decoration: BoxDecoration(
                    borderRadius: DS.borderRadius16,
                    color: DS.surfaceSecondary,
                    border: Border.all(
                      color: color.withValues(alpha: 0.3),
                      width: 1,
                    ),
                  ),
      child: Row(
        children: [
          Icon(
            icon,
            size: 18,
            color: color,
          ),
          const SizedBox(width: DS.spacing4),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: TextStyle(
                  fontSize: 11,
                  color: DS.textSecondary,
                ),
              ),
              Text(
                '$value',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: DS.fontWeightBold,
                  color: DS.textPrimary,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

/// 属性芯片组件
class _AttributeChip extends StatelessWidget {
  const _AttributeChip({required this.attribute});

  final AttributeValue attribute;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(right: DS.spacing8),
      padding: const EdgeInsets.symmetric(horizontal: DS.spacing12, vertical: DS.spacing8),
      decoration: BoxDecoration(
        borderRadius: DS.borderRadius16,
        color: DS.surfaceSecondary,
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            _getAttributeName(attribute.attribute),
            style: TextStyle(
              fontSize: 11,
              color: DS.textSecondary,
            ),
          ),
          Text(
            attribute.value.toString(),
            style: TextStyle(
              fontSize: 16,
              fontWeight: DS.fontWeightBold,
              color: DS.textPrimary,
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
