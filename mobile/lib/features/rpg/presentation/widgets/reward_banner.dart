import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

/// 奖励横幅组件 - 显示每日奖励和金币信息
class RewardBanner extends StatelessWidget {
  const RewardBanner({
    super.key,
    required this.onTap,
    required this.gold,
  });

  final VoidCallback onTap;
  final int gold;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        borderRadius: DS.borderRadius16,
        color: DS.glassBackground,
        boxShadow: DS.shadowMd,
        border: Border.all(
          color: DS.glassBorder,
          width: 1,
        ),
      ),
      padding: const EdgeInsets.all(DS.spacing16),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          // 左侧 - 奖励信息
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '每日奖励',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: DS.fontWeightBold,
                    color: DS.textPrimary,
                  ),
                ),
                const SizedBox(height: DS.spacing4),
                Text(
                  '连续登录可获得更多奖励！',
                  style: TextStyle(
                    fontSize: 12,
                    color: DS.textSecondary,
                  ),
                ),
                const SizedBox(height: DS.spacing8),
                // 金币显示
                Row(
                  children: [
                    Icon(
                      Icons.monetization_on,
                      size: 16,
                      color: DS.warning,
                    ),
                    const SizedBox(width: DS.spacing4),
                    Text(
                      '金币: $gold',
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: DS.fontWeightMedium,
                        color: DS.textPrimary,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          
          const SizedBox(width: DS.spacing16),
          
          // 右侧 - 领取按钮
          SizedBox(
            height: 50,
            child: ElevatedButton.icon(
              onPressed: onTap,
              icon: const Icon(Icons.arrow_forward),
              label: const Text('领取'),
              style: ElevatedButton.styleFrom(
                backgroundColor: DS.primaryBase,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(
                  borderRadius: DS.borderRadius12,
                ),
                textStyle: TextStyle(
                  fontSize: 14,
                  fontWeight: DS.fontWeightMedium,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
