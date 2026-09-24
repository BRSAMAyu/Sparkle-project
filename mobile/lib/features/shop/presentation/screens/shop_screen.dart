import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/display/lexicon/error_lexicon.dart';
import 'package:sparkle/core/errors/user_facing_error.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/photon/photon_routes.dart';
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
        // D-COMM-2：光子兑 Pro 入口（次级位置，不占内容主面积；奖励出口语义，
        // 与商城购买面分开——不放兑换卡进商品网格）。
        actions: [
          // 双源同键（A11Y-BATCH6B，照批 4 漂移修正形制）：Tooltip 之外
          // 显式 semanticLabel——隐藏期 Tooltip 不构成按钮名。
          Tooltip(
            message: context.l10n.photonRedeemProEntryTooltip,
            child: SparkleIconButton(
              variant: ButtonVariant.ghost,
              icon: const Icon(Icons.redeem_rounded),
              semanticLabel: context.l10n.photonRedeemProEntryTooltip,
              onPressed: () =>
                  unawaited(context.push(PhotonRoutes.redeemPro)),
            ),
          ),
        ],
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
        child: LoadingIndicator(),
      );
    }

    // N15/EE-G6（A-SPEC3）：空态与错误态拆为互斥分支——空态不再混排
    // 原始异常红字；错误态走 owner（CustomErrorWidget）+ 人话化文案。
    if (items.isEmpty && state.error != null) {
      return CustomErrorWidget.page(
        context: context,
        message: UserFacingError.from(state.error!),
        onRetry: () =>
            ref.read(shopItemsProvider.notifier).refresh(),
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
                uiErrorMessage(context.l10n, state.error!),
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
            final error = ref.read(shopItemsProvider).error;
            AppFeedback.error(
              context,
              error == null
                  ? context.l10n.shopPurchaseFailed
                  : uiErrorMessage(context.l10n, error),
            );
          }
        },
      ),
    );
  }
}
