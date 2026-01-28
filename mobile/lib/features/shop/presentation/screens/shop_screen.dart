import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/shared/entities/shop_model.dart';
import 'package:sparkle/features/shop/presentation/providers/shop_provider.dart';
import 'package:sparkle/features/shop/presentation/widgets/shop_item_card.dart';
import 'package:sparkle/features/shop/presentation/widgets/purchase_confirmation_dialog.dart';

/// Shop Screen
/// 商城界面
class ShopScreen extends ConsumerStatefulWidget {
  const ShopScreen({Key? key}) : super(key: key);

  @override
  ConsumerState<ShopScreen> createState() => _ShopScreenState();
}

class _ShopScreenState extends ConsumerState<ShopScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 5, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(shopItemsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('光子商城'),
        bottom: TabBar(
          controller: _tabController,
          isScrollable: true,
          tabs: const [
            Tab(text: '全部'),
            Tab(text: '皮肤'),
            Tab(text: '称号'),
            Tab(text: '消耗品'),
            Tab(text: '加成'),
          ],
        ),
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          await ref.read(shopItemsProvider.notifier).refresh();
        },
        child: TabBarView(
          controller: _tabController,
          children: [
            _buildCategoryGrid(null, state),
            _buildCategoryGrid(ShopItemType.skin, state),
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
    final items = type == null
        ? state.items
        : state.getItemsByType(type);

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
              color: Colors.grey[400],
            ),
            const SizedBox(height: 16),
            Text(
              '暂无物品',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: Colors.grey[600],
                  ),
            ),
            if (state.error != null) ...[
              const SizedBox(height: 8),
              Text(
                state.error!,
                style: const TextStyle(color: Colors.red),
              ),
            ],
          ],
        ),
      );
    }

    return GridView.builder(
      padding: const EdgeInsets.all(16),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        crossAxisSpacing: 16,
        mainAxisSpacing: 16,
        childAspectRatio: 0.75,
      ),
      itemCount: items.length,
      itemBuilder: (context, index) {
        final item = items[index];
        return ShopItemCard(
          item: item,
          onTap: () => _showPurchaseDialog(item),
        );
      },
    );
  }

  void _showPurchaseDialog(ShopItem item) {
    showDialog(
      context: context,
      builder: (context) => PurchaseConfirmationDialog(
        item: item,
        onConfirm: () async {
          final success = await ref
              .read(shopItemsProvider.notifier)
              .purchaseItem(item.id);

          if (success && mounted) {
            Navigator.of(context).pop();
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text('成功购买 ${item.name}'),
                backgroundColor: Colors.green,
              ),
            );
          } else if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text(ref.read(shopItemsProvider).error ?? '购买失败'),
                backgroundColor: Colors.red,
              ),
            );
          }
        },
      ),
    );
  }
}
