import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/utils/theme_utils.dart';
import 'package:sparkle/shared/entities/shop_model.dart';

/// Shop Item Card Widget
/// 商城物品卡片组件
class ShopItemCard extends StatelessWidget {
  const ShopItemCard({
    required this.item,
    required this.onTap,
    super.key,
  });

  final ShopItem item;
  final VoidCallback onTap;

  Color _badgeTextColor(Color background) => ThemeUtils.getContrastSafeText(
        background,
        darkText: DS.textPrimary,
      );

  @override
  Widget build(BuildContext context) => Semantics(
        button: true,
        label: '${item.name}，价格 ${item.pricePhotons} 光子',
        child: GestureDetector(
          onTap: onTap,
          child: DecoratedBox(
            decoration: BoxDecoration(
              color: DS.surfacePrimary,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: _getRarityColor(item.rarity).withValues(alpha: 0.5),
                width: item.isOwned ? 0 : 2,
              ),
              boxShadow: [
                BoxShadow(
                  color: DS.textPrimary.withValues(alpha: 0.05),
                  blurRadius: 8,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Icon Section
                Expanded(
                  child: Stack(
                    children: [
                      // Item Icon
                      Container(
                        width: double.infinity,
                        decoration: BoxDecoration(
                          color: _getRarityColor(item.rarity)
                              .withValues(alpha: 0.1),
                          borderRadius: const BorderRadius.vertical(
                            top: Radius.circular(14),
                          ),
                        ),
                        child: Center(
                          child: item.iconUrl != null
                              ? ClipRRect(
                                  borderRadius: const BorderRadius.vertical(
                                    top: Radius.circular(14),
                                  ),
                                  child: Image.network(
                                    item.iconUrl!,
                                    fit: BoxFit.cover,
                                    errorBuilder:
                                        (context, error, stackTrace) => Icon(
                                      _getItemTypeIcon(item.itemType),
                                      size: 64,
                                      color: _getRarityColor(item.rarity),
                                    ),
                                  ),
                                )
                              : Icon(
                                  _getItemTypeIcon(item.itemType),
                                  size: 64,
                                  color: _getRarityColor(item.rarity),
                                ),
                        ),
                      ),

                      // Owned Badge
                      if (item.isOwned)
                        Positioned(
                          top: 8,
                          left: 8,
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 8,
                              vertical: 4,
                            ),
                            decoration: BoxDecoration(
                              color: DS.success,
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: Text(
                              '已拥有',
                              style: TextStyle(
                                color: _badgeTextColor(DS.success),
                                fontSize: 10,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                        ),

                      // Discount Badge
                      if (item.hasDiscount)
                        Positioned(
                          top: 8,
                          right: 8,
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 8,
                              vertical: 4,
                            ),
                            decoration: BoxDecoration(
                              color: DS.error,
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: Text(
                              '-${item.discountPercent}%',
                              style: TextStyle(
                                color: _badgeTextColor(DS.error),
                                fontSize: 10,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                        ),

                      // Limited Badge
                      if (item.isLimited && item.stockQuantity != null)
                        Positioned(
                          bottom: 8,
                          right: 8,
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 8,
                              vertical: 4,
                            ),
                            decoration: BoxDecoration(
                              color: item.stockQuantity! > 0
                                  ? DS.warning
                                  : DS.neutral500,
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: Text(
                              '限量 ${item.stockQuantity}',
                              style: TextStyle(
                                color: _badgeTextColor(
                                  item.stockQuantity! > 0
                                      ? DS.warning
                                      : DS.neutral500,
                                ),
                                fontSize: 10,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                        ),
                    ],
                  ),
                ),

                // Info Section
                Padding(
                  padding: const EdgeInsets.all(DS.spacing12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Name
                      Text(
                        item.name,
                        style: Theme.of(context).textTheme.titleSmall?.copyWith(
                              fontWeight: FontWeight.bold,
                            ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),

                      const SizedBox(height: 4),

                      // Price
                      Row(
                        children: [
                          Icon(
                            Icons.flash_on_rounded,
                            size: 16,
                            color: DS.warning,
                          ),
                          const SizedBox(width: 4),
                          Text(
                            '${item.pricePhotons}',
                            style: TextStyle(
                              color: DS.warning,
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          if (item.originalPrice != null) ...[
                            const SizedBox(width: DS.spacing8),
                            Text(
                              '${item.originalPrice}',
                              style: TextStyle(
                                color: DS.textTertiary,
                                fontSize: 12,
                                decoration: TextDecoration.lineThrough,
                              ),
                            ),
                          ],
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      );

  Color _getRarityColor(ItemRarity rarity) {
    switch (rarity) {
      case ItemRarity.common:
        return DS.rarityCommon;
      case ItemRarity.rare:
        return DS.rarityRare;
      case ItemRarity.epic:
        return DS.rarityEpic;
      case ItemRarity.legendary:
        return DS.rarityLegendary;
    }
  }

  IconData _getItemTypeIcon(ShopItemType type) {
    switch (type) {
      case ShopItemType.skin:
        return Icons.face_outlined;
      case ShopItemType.title:
        return Icons.military_tech_outlined;
      case ShopItemType.consumable:
        return Icons.inventory_2_outlined;
      case ShopItemType.boost:
        return Icons.trending_up_outlined;
    }
  }
}
