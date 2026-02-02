import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/shop/data/repositories/shop_repository.dart';
import 'package:sparkle/shared/entities/shop_model.dart';

/// 称号服务
///
/// 管理用户的称号装备和显示
class TitleNotifier extends StateNotifier<Map<String, dynamic>?> {
  TitleNotifier(
    this._shopRepository,
    this._authNotifier,
  ) : super(null) {
    // 监听认证状态变化
    _authNotifier.addListener(_onAuthStateChanged);
    // 初始加载
    _onAuthStateChanged();
  }

  final ShopRepository _shopRepository;
  final AuthNotifier _authNotifier;

  /// 当认证状态变化时，加载用户的称号
  void _onAuthStateChanged() {
    final user = _authNotifier.state.user;
    if (user != null && user.equippedTitle != null) {
      _loadTitle(user.equippedTitle!);
    } else {
      state = null;
    }
  }

  /// 加载称号配置
  Future<void> _loadTitle(String titleId) async {
    try {
      final inventory = await _shopRepository.getInventory();
      final titles = inventory['titles'] ?? [];

      InventoryItem? matchedTitle;
      for (final item in titles) {
        if (item.id == titleId) {
          matchedTitle = item;
          break;
        }
      }

      if (matchedTitle != null) {
        final titleConfig = matchedTitle.itemConfig;
        if (titleConfig != null) {
          state = {
            'id': titleId,
            'name': matchedTitle.name,
            'config': titleConfig,
          };
        }
      }
    } catch (e) {
      // 获取称号配置失败，忽略
      print('Failed to load title: $e');
    }
  }

  /// 装备称号
  Future<bool> equipTitle(String titleId) async {
    try {
      final result = await _shopRepository.equipItem(
        itemType: 'title',
        itemId: titleId,
      );
      if (result['success'] == true) {
        await _loadTitle(titleId);
        return true;
      }
      return false;
    } catch (e) {
      print('Failed to equip title: $e');
      return false;
    }
  }

  /// 卸载称号
  Future<bool> unequipTitle() async {
    try {
      final result = await _shopRepository.equipItem(
        itemType: 'title',
      );
      if (result['success'] == true) {
        state = null;
        return true;
      }
      return false;
    } catch (e) {
      print('Failed to unequip title: $e');
      return false;
    }
  }

  @override
  void dispose() {
    _authNotifier.removeListener(_onAuthStateChanged);
    super.dispose();
  }
}

/// 称号Provider
final titleProvider = StateNotifierProvider<TitleNotifier, Map<String, dynamic>?>((ref) {
  final shopRepository = ref.watch<ShopRepository>(shopRepositoryProvider);
  final authNotifier = ref.watch<AuthNotifier>(authProvider.notifier);

  return TitleNotifier(
    shopRepository,
    authNotifier,
  );
});

/// 当前装备的称号ID
final equippedTitleIdProvider = Provider<String?>((ref) {
  final authState = ref.watch(authProvider);
  return authState.user?.equippedTitle;
});

/// 当前称号显示文本
final titleTextProvider = Provider<String?>((ref) {
  final titleState = ref.watch(titleProvider);
  final config = titleState?['config'] as Map<String, dynamic>?;
  return config?['text'] as String?;
});

/// 当前称号显示格式（prefix/suffix）
final titleDisplayFormatProvider = Provider<String>((ref) {
  final titleState = ref.watch(titleProvider);
  final config = titleState?['config'] as Map<String, dynamic>?;
  return config?['display_format'] as String? ?? 'prefix';
});
