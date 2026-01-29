import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/shared/entities/shop_model.dart';
import 'package:sparkle/features/photon/presentation/providers/photon_provider.dart';

/// Purchase Confirmation Dialog
/// 购买确认弹窗
class PurchaseConfirmationDialog extends ConsumerStatefulWidget {
  const PurchaseConfirmationDialog({
    super.key,
    required this.item,
    required this.onConfirm,
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

    return AlertDialog(
      title: const Text('确认购买'),
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
                  color: _getRarityColor(widget.item.rarity).withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(
                    color: _getRarityColor(widget.item.rarity),
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
                                color: _getRarityColor(widget.item.rarity),
                              ),
                          ),
                        )
                      : Icon(
                          _getItemTypeIcon(widget.item.itemType),
                          size: 64,
                          color: _getRarityColor(widget.item.rarity),
                        ),
                ),
              ),
            ),

            const SizedBox(height: 24),

            // Item Name
            Text(
              widget.item.name,
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
              textAlign: TextAlign.center,
            ),

            if (widget.item.description != null) ...[
              const SizedBox(height: 8),
              Text(
                widget.item.description!,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Colors.grey[600],
                    ),
                textAlign: TextAlign.center,
              ),
            ],

            const SizedBox(height: 24),

            // Price Breakdown
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.grey[100],
                borderRadius: BorderRadius.circular(12),
              ),
              child: Column(
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text('价格：'),
                      Row(
                        children: [
                          Icon(
                            Icons.flash_on_rounded,
                            size: 18,
                            color: Colors.amber[700],
                          ),
                          const SizedBox(width: 4),
                          Text(
                            '${widget.item.pricePhotons}',
                            style: const TextStyle(
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          if (widget.item.originalPrice != null) ...[
                            const SizedBox(width: 8),
                            Text(
                              '${widget.item.originalPrice}',
                              style: TextStyle(
                                color: Colors.grey[400],
                                decoration: TextDecoration.lineThrough,
                              ),
                            ),
                          ],
                        ],
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text('当前余额：'),
                      Row(
                        children: [
                          Icon(
                            Icons.flash_on_rounded,
                            size: 18,
                            color: Colors.amber[700],
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
                      const Text('购买后余额：',
                          style: TextStyle(fontWeight: FontWeight.bold),),
                      Row(
                        children: [
                          Icon(
                            Icons.flash_on_rounded,
                            size: 18,
                            color: canAfford ? Colors.amber[700] : Colors.red,
                          ),
                          const SizedBox(width: 4),
                          Text(
                            '${currentBalance - widget.item.pricePhotons}',
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              color: canAfford ? Colors.black : Colors.red,
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
                padding: const EdgeInsets.only(top: 16),
                child: Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.red.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.red.withValues(alpha: 0.3)),
                  ),
                  child: Row(
                    children: [
                      const Icon(
                        Icons.error_outline,
                        color: Colors.red,
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          '光子不足',
                          style: TextStyle(
                            color: Colors.red[700],
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
        TextButton(
          onPressed: _isPurchasing ? null : () => Navigator.of(context).pop(),
          child: const Text('取消'),
        ),
        ElevatedButton(
          onPressed: _isPurchasing || !canAfford
              ? null
              : () async {
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
          style: ElevatedButton.styleFrom(
            backgroundColor: _getRarityColor(widget.item.rarity),
            foregroundColor: Colors.white,
          ),
          child: _isPurchasing
              ? const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: Colors.white,
                  ),
                )
              : const Text('确认购买'),
        ),
      ],
    );
  }

  Color _getRarityColor(ItemRarity rarity) {
    switch (rarity) {
      case ItemRarity.common:
        return Colors.grey;
      case ItemRarity.rare:
        return Colors.blue;
      case ItemRarity.epic:
        return Colors.purple;
      case ItemRarity.legendary:
        return Colors.orange;
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
