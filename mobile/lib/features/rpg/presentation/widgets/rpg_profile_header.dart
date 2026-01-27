import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/rpg/data/models/rpg_models.dart';
import 'package:sparkle/features/rpg/presentation/providers/rpg_providers.dart';
import 'package:sparkle/features/rpg/presentation/widgets/pixel_character.dart';

/// RPG个人资料头部组件 - 左侧头像右侧数据的自适应布局
class RpgProfileHeader extends ConsumerWidget {
  const RpgProfileHeader({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final character = ref.watch(characterProvider);
    
    // 计算HP和XP百分比
    final hpPercentage = (character.currentHp / character.maxHp) * 100;
    final xpPercentage = (character.experience / character.maxExperience) * 100;

    return Container(
      padding: const EdgeInsets.all(DS.spacing16),
      margin: const EdgeInsets.symmetric(horizontal: DS.spacing16),
      decoration: BoxDecoration(
        borderRadius: DS.borderRadius20,
        color: DS.surfaceSecondary,
        border: Border.all(
          color: DS.glassBorder,
          width: 1,
        ),
        boxShadow: DS.shadowSm,
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          // 左侧：80x80的像素头像容器
          Container(
            width: 80,
            height: 80,
            decoration: BoxDecoration(
              borderRadius: DS.borderRadius16,
              color: DS.surfaceTertiary,
            ),
            child: Center(
              child: PixelCharacter(
                character: character,
                size: 64,
              ),
            ),
          ),
          
          // 中间间距
          const SizedBox(width: DS.spacing16),
          
          // 右侧：数据区域（必须使用Expanded防止水平溢出）
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                // 昵称行
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Text(
                        character.nickname,
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: DS.fontWeightBold,
                          color: DS.textPrimary,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    
                    // 等级标签
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: DS.spacing8, vertical: DS.spacing2),
                      decoration: BoxDecoration(
                        borderRadius: DS.borderRadius8,
                        color: DS.primaryBase,
                      ),
                      child: Text(
                        'Lv.${character.level}',
                        style: const TextStyle(
                          fontSize: 12,
                          color: Colors.white,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ],
                ),
                
                const SizedBox(height: DS.spacing12),
                
                // HP进度条
                StatusBar(
                  label: '生命值',
                  value: character.currentHp,
                  maxValue: character.maxHp,
                  percentage: hpPercentage,
                  color: DS.error,
                  icon: Icons.favorite,
                ),
                
                const SizedBox(height: DS.spacing8),
                
                // XP进度条
                StatusBar(
                  label: '经验值',
                  value: character.experience,
                  maxValue: character.maxExperience,
                  percentage: xpPercentage,
                  color: DS.primaryBase,
                  icon: Icons.star,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// 自适应宽度的进度条组件
class StatusBar extends StatelessWidget {
  const StatusBar({
    super.key,
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
                  size: 14,
                  color: color,
                ),
                const SizedBox(width: DS.spacing4),
                Text(
                  label,
                  style: TextStyle(
                    fontSize: 12,
                    color: DS.textSecondary,
                  ),
                ),
              ],
            ),
            Text(
              '$value / $maxValue',
              style: TextStyle(
                fontSize: 12,
                color: DS.textSecondary,
              ),
            ),
          ],
        ),
        
        const SizedBox(height: DS.spacing4),
        
        // 进度条容器（自适应宽度）
        Container(
          height: 12,
          decoration: BoxDecoration(
            borderRadius: DS.borderRadius8,
            color: DS.surfaceTertiary,
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
                width: percentage > 0 ? double.infinity : 0,
                decoration: BoxDecoration(
                  borderRadius: DS.borderRadius8,
                  color: color,
                ),
                // 使用 FractionallySizedBox 来实现百分比宽度
                child: FractionallySizedBox(
                  widthFactor: percentage / 100,
                  child: Container(
                    decoration: BoxDecoration(
                      borderRadius: DS.borderRadius8,
                      color: color,
                    ),
                  ),
                ),
              ),
              // 百分比文本
              Center(
                child: Text(
                  '${percentage.toInt()}%',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 8,
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
