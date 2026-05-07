import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/shop/presentation/providers/shop_provider.dart';
import 'package:sparkle/features/shop/presentation/widgets/purchase_confirmation_dialog.dart';
import 'package:sparkle/features/shop/presentation/widgets/shop_item_card.dart';
import 'package:sparkle/shared/entities/shop_model.dart';

/// Shop Screen
/// 商城界面
class ShopScreen extends ConsumerStatefulWidget {
  const ShopScreen({super.key});

  @override
  ConsumerState<ShopScreen> createState() => _ShopScreenState();
}

class _ShopScreenState extends ConsumerState<ShopScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 6, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(shopItemsProvider);

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        title: Text(context.l10n.shopTitle),
        bottom: TabBar(
          controller: _tabController,
          isScrollable: true,
          tabs: [
            Tab(text: context.l10n.shopCategoryAll),
            Tab(text: context.l10n.shopCategorySkin),
            Tab(text: context.l10n.shopCategoryVisualElement),
            Tab(text: context.l10n.shopCategoryTitle),
            Tab(text: context.l10n.shopCategoryConsumable),
            Tab(text: context.l10n.shopCategoryBoost),
          ],
        ),
      ),
      child: SparkleRefreshIndicator(
        onRefresh: () async {
          unawaited(
              SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
          await ref.read(shopItemsProvider.notifier).refresh();
        },
        child: TabBarView(
          controller: _tabController,
          children: [
            _buildCategoryGrid(null, state),
            _buildCategoryGrid(ShopItemType.skin, state),
            _buildCategoryGrid(ShopItemType.visualElement, state),
            _buildCategoryGrid(ShopItemType.title, state),
            _buildCategoryGrid(ShopItemType.consumable, state),
            _buildCategoryGrid(ShopItemType.boost, state),
          ],
        ),
      ),
    );
  }

  Widget _buildCategoryGrid(
    ShopItemType? type,
    ShopItemsState state,
  ) {
    final items = type == null ? state.items : state.getItemsByType(type);

    if (state.isLoading && items.isEmpty) {
      return const Center(
        child: CircularProgressIndicator(),
      );
    }

    if (items.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.shopping_bag_outlined,
              size: 64,
              color: DS.textTertiary,
            ),
            const SizedBox(height: DS.spacing16),
            Text(
              context.l10n.shopEmpty,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: DS.textSecondary,
                  ),
            ),
            if (state.error != null) ...[
              const SizedBox(height: DS.spacing8),
              Text(
                state.error!,
                style: TextStyle(color: DS.error),
              ),
            ],
          ],
        ),
      );
    }

    return GridView.builder(
      padding: const EdgeInsets.all(DS.spacing16),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        crossAxisSpacing: 16,
        mainAxisSpacing: 16,
        childAspectRatio: 0.75,
      ),
      itemCount: items.length,
      itemBuilder: (context, index) {
        final item = items[index];
        return SparkleStaggerItem(
          index: index,
          child: ShopItemCard(
            item: item,
            onTap: () => _showPurchaseDialog(item),
          ),
        );
      },
    );
  }

  void _showPurchaseDialog(ShopItem item) {
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.sheetOpen));
    showDialog<void>(
      context: context,
      builder: (dialogContext) => PurchaseConfirmationDialog(
        item: item,
        onConfirm: () async {
          final success =
              await ref.read(shopItemsProvider.notifier).purchaseItem(item.id);

          if (!mounted) return;

          if (success) {
            unawaited(
                SensoryFeedbackService.emit(SensoryFeedbackEvent.success));
            Navigator.of(dialogContext).pop();
            AppFeedback.success(
              context,
              context.l10n.shopPurchaseSuccess(item.name),
            );
          } else {
            AppFeedback.error(
              context,
              ref.read(shopItemsProvider).error ??
                  context.l10n.shopPurchaseFailed,
            );
          }
        },
      ),
    );
  }
}
