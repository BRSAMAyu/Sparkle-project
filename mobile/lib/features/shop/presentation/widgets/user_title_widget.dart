import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/shop/presentation/providers/title_provider.dart';

/// 用户称号徽章
///
/// 显示用户装备的称号
class UserTitleBadge extends ConsumerWidget {
  const UserTitleBadge({
    super.key,
    this.userId,
    this.equippedTitleId,
    this.style,
  });

  final String? userId;
  final String? equippedTitleId;
  final TextStyle? style;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // 如果没有装备称号，返回空
    if (equippedTitleId == null) {
      return const SizedBox.shrink();
    }

    final titleText = ref.watch(titleTextProvider);
    final displayFormat = ref.watch(titleDisplayFormatProvider);

    if (titleText == null) {
      return const SizedBox.shrink();
    }

    final defaultStyle = TextStyle(
      fontSize: 11,
      fontWeight: FontWeight.w600,
      color: DS.brandPrimary,
    );

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            DS.brandPrimary.withValues(alpha: 0.1),
            DS.brandSecondary.withValues(alpha: 0.1),
          ],
        ),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(
          color: DS.brandPrimary.withValues(alpha: 0.3),
          width: 1,
        ),
      ),
      child: Text(
        titleText,
        style: style ?? defaultStyle,
      ),
    );
  }
}

/// 用户名称与称号组合组件
///
/// 根据称号格式（前缀/后缀）显示名称和称号
class UsernameWithTitle extends ConsumerWidget {
  const UsernameWithTitle({
    super.key,
    required this.username,
    this.userId,
    this.equippedTitleId,
    this.usernameStyle,
    this.titleStyle,
    this.spacing = 4,
  });

  final String username;
  final String? userId;
  final String? equippedTitleId;
  final TextStyle? usernameStyle;
  final TextStyle? titleStyle;
  final double spacing;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // 如果没有装备称号，只显示用户名
    if (equippedTitleId == null) {
      return Text(
        username,
        style: usernameStyle,
      );
    }

    final titleText = ref.watch(titleTextProvider);
    final displayFormat = ref.watch(titleDisplayFormatProvider);

    if (titleText == null) {
      return Text(
        username,
        style: usernameStyle,
      );
    }

    // 根据显示格式排列
    if (displayFormat == 'prefix') {
      // 前缀模式：[称号] 用户名
      return Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          UserTitleBadge(
            equippedTitleId: equippedTitleId,
            style: titleStyle,
          ),
          if (titleText.isNotEmpty) SizedBox(width: spacing),
          Text(
            username,
            style: usernameStyle,
          ),
        ],
      );
    } else {
      // 后缀模式：用户名 [称号]
      return Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            username,
            style: usernameStyle,
          ),
          if (titleText.isNotEmpty) SizedBox(width: spacing),
          UserTitleBadge(
            equippedTitleId: equippedTitleId,
            style: titleStyle,
          ),
        ],
      );
    }
  }
}

/// 称号选择器（用于背包界面）
///
/// 显示用户拥有的称号列表，允许装备
class TitleSelector extends ConsumerWidget {
  const TitleSelector({
    super.key,
    required this.titles,
    this.equippedTitleId,
    this.onEquip,
    this.onUnequip,
  });

  final List<dynamic> titles;
  final String? equippedTitleId;
  final Future<void> Function(String titleId)? onEquip;
  final Future<void> Function()? onUnequip;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (titles.isEmpty) {
      return const Center(
        child: Text('暂无称号'),
      );
    }

    return GridView.builder(
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        childAspectRatio: 3,
        crossAxisSpacing: 8,
        mainAxisSpacing: 8,
      ),
      itemCount: titles.length + 1, // +1 for "unequip" option
      itemBuilder: (context, index) {
        // 第一个选项：卸下称号
        if (index == 0) {
          final isEquipped = equippedTitleId == null;
          return Card(
            elevation: isEquipped ? 2 : 0,
            color: isEquipped ? DS.brandPrimary12 : null,
            child: InkWell(
              onTap: isEquipped ? null : onUnequip,
              child: Center(
                child: Text(
                  '不装备称号',
                  style: TextStyle(
                    color: isEquipped ? DS.brandPrimary : DS.textSecondary,
                    fontWeight: isEquipped ? FontWeight.bold : FontWeight.normal,
                  ),
                ),
              ),
            ),
          );
        }

        // 称号选项
        final title = titles[index - 1] as Map<String, dynamic>;
        final titleId = title['id'] as String;
        final titleName = title['name'] as String;
        final isEquipped = titleId == equippedTitleId;
        final titleConfig = title['item_config'] as Map<String, dynamic>?;
        final titleText = titleConfig?['text'] as String? ?? '';

        return Card(
          elevation: isEquipped ? 2 : 0,
          color: isEquipped ? DS.brandPrimary12 : null,
          child: InkWell(
            onTap: isEquipped ? null : () => onEquip?.call(titleId),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  titleText,
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                    color: isEquipped ? DS.brandPrimary : DS.textPrimary,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  titleName,
                  style: TextStyle(
                    fontSize: 10,
                    color: DS.textSecondary,
                  ),
                ),
                if (isEquipped)
                  Icon(
                    Icons.check_circle,
                    size: 16,
                    color: DS.brandPrimary,
                  ),
              ],
            ),
          ),
        );
      },
    );
  }
}
