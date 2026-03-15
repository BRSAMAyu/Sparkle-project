import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/photon/presentation/providers/photon_provider.dart';
import 'package:sparkle/shared/entities/shop_model.dart';

/// Purchase Confirmation Dialog
/// 购买确认弹窗
class PurchaseConfirmationDialog extends ConsumerStatefulWidget {
  const PurchaseConfirmationDialog({
    required this.item,
    required this.onConfirm,
    super.key,
  });

  final ShopItem item;
  final VoidCallback onConfirm;

  @override
  ConsumerState<PurchaseConfirmationDialog> createState() =>
      _PurchaseConfirmationDialogState();
}

class _PurchaseConfirmationDialogState
    extends ConsumerState<PurchaseConfirmationDialog> {
  bool _isPurchasing = false;

  @override
  Widget build(BuildContext context) {
    final balanceState = ref.watch(photonBalanceProvider);
    final currentBalance = balanceState.balance?.balance ?? 0;
    final canAfford = currentBalance >= widget.item.pricePhotons;
    final rarityColor = _getRarityColor(widget.item.rarity);

    return AlertDialog(
      title: Text(context.l10n.purchaseConfirmTitle),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Item Preview
            Center(
              child: Container(
                width: 120,
                height: 120,
                decoration: BoxDecoration(
                  color: rarityColor.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(
                    color: rarityColor,
                    width: 2,
                  ),
                ),
                child: Center(
                  child: widget.item.iconUrl != null
                      ? ClipRRect(
                          borderRadius: BorderRadius.circular(14),
                          child: Image.network(
                            widget.item.iconUrl!,
                            fit: BoxFit.cover,
                            errorBuilder: (context, error, stackTrace) => Icon(
                              _getItemTypeIcon(widget.item.itemType),
                              size: 64,
                              color: rarityColor,
                            ),
                          ),
                        )
                      : Icon(
                          _getItemTypeIcon(widget.item.itemType),
                          size: 64,
                          color: rarityColor,
                        ),
                ),
              ),
            ),

            const SizedBox(height: DS.lg),

            // Item Name
            Text(
              widget.item.name,
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
              textAlign: TextAlign.center,
            ),

            if (widget.item.description != null) ...[
              const SizedBox(height: DS.sm),
              Text(
                widget.item.description!,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: DS.textSecondary,
                    ),
                textAlign: TextAlign.center,
              ),
            ],

            const SizedBox(height: DS.lg),

            // Price Breakdown
            Container(
              padding: const EdgeInsets.all(DS.spacing16),
              decoration: BoxDecoration(
                color: DS.surfaceTertiary,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Column(
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Expanded(child: Text(context.l10n.shopPriceLabel)),
                      const SizedBox(width: DS.spacing12),
                      Row(
                        children: [
                          Icon(
                            Icons.flash_on_rounded,
                            size: 18,
                            color: DS.warning,
                          ),
                          const SizedBox(width: 4),
                          Text(
                            '${widget.item.pricePhotons}',
                            style: const TextStyle(
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          if (widget.item.originalPrice != null) ...[
                            const SizedBox(width: DS.spacing8),
                            Text(
                              '${widget.item.originalPrice}',
                              style: TextStyle(
                                color: DS.textTertiary,
                                decoration: TextDecoration.lineThrough,
                              ),
                            ),
                          ],
                        ],
                      ),
                    ],
                  ),
                  const SizedBox(height: DS.spacing12),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Expanded(child: Text(context.l10n.shopBalanceLabel)),
                      const SizedBox(width: DS.spacing12),
                      Row(
                        children: [
                          Icon(
                            Icons.flash_on_rounded,
                            size: 18,
                            color: DS.warning,
                          ),
                          const SizedBox(width: 4),
                          Text(
                            '$currentBalance',
                            style: const TextStyle(
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                  const Divider(height: 24),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Expanded(
                        child: Text(
                          context.l10n.shopBalanceAfterPurchase,
                          style: const TextStyle(fontWeight: FontWeight.bold),
                        ),
                      ),
                      const SizedBox(width: DS.spacing12),
                      Row(
                        children: [
                          Icon(
                            Icons.flash_on_rounded,
                            size: 18,
                            color: canAfford ? DS.warning : DS.error,
                          ),
                          const SizedBox(width: 4),
                          Text(
                            '${currentBalance - widget.item.pricePhotons}',
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              color: canAfford ? DS.textPrimary : DS.error,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ],
              ),
            ),

            // Insufficient Funds Warning
            if (!canAfford)
              Padding(
                padding: const EdgeInsets.only(top: DS.md),
                child: Container(
                  padding: const EdgeInsets.all(DS.spacing12),
                  decoration: BoxDecoration(
                    color: DS.error.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: DS.error.withValues(alpha: 0.3)),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        Icons.error_outline,
                        color: DS.error,
                      ),
                      const SizedBox(width: DS.sm),
                      Expanded(
                        child: Text(
                          context.l10n.shopInsufficientPhotons,
                          style: TextStyle(
                            color: DS.error,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
          ],
        ),
      ),
      actions: [
        SparkleButton(
          label: context.l10n.cancel,
          onPressed: _isPurchasing ? () {} : () => Navigator.of(context).pop(),
          variant: ButtonVariant.outline,
          disabled: _isPurchasing,
        ),
        SparkleButton(
          label: context.l10n.shopConfirmPurchase,
          onPressed: () async {
            setState(() {
              _isPurchasing = true;
            });

            widget.onConfirm();

            if (mounted) {
              setState(() {
                _isPurchasing = false;
              });
            }
          },
          loading: _isPurchasing,
          disabled: _isPurchasing || !canAfford,
          icon: const Icon(Icons.shopping_cart_checkout_rounded),
        ),
      ],
    );
  }

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
