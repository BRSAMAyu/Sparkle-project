import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/tokens_v2/theme_manager.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/shop/data/repositories/shop_repository.dart';

/// 皮肤应用服务
///
/// 监听用户登录状态，自动应用装备的皮肤到主题系统
class SkinNotifier extends StateNotifier<Map<String, dynamic>?> {
  SkinNotifier(
    this._themeManager,
    this._shopRepository,
    this._authNotifier,
  ) : super(null) {
    // 监听认证状态变化
    _authNotifier.addListener(_onAuthStateChanged);
    // 初始加载
    _onAuthStateChanged();
  }

  final ThemeManager _themeManager;
  final ShopRepository _shopRepository;
  final AuthNotifier _authNotifier;
  String? _currentSkinId;

  /// 当认证状态变化时，应用用户的装备皮肤
  void _onAuthStateChanged() {
    final user = _authNotifier.state.user;
    if (user != null) {
      // 用户已登录，应用装备的皮肤
      _applyUserSkin(user.equippedSkin);
    } else {
      // 用户已登出，移除皮肤
      _themeManager.unequipSkin();
    }
  }

  /// 应用用户装备的皮肤
  Future<void> _applyUserSkin(String? skinId) async {
    if (skinId == null || skinId == _currentSkinId) return;

    try {
      // 从商城获取皮肤配置
      final inventory = await _shopRepository.getInventory();
      final skins = inventory['skins'] as List<dynamic>? ?? [];

      // 查找装备的皮肤
      final equippedSkin = skins.firstWhere(
        (item) => item['id'] == skinId,
        orElse: () => null,
      );

      if (equippedSkin != null) {
        final skinConfig = equippedSkin['item_config'] as Map<String, dynamic>?;
        if (skinConfig != null) {
          await _themeManager.equipShopSkin(skinId, skinConfig);
          _currentSkinId = skinId;
          state = {'skin_id': skinId, 'skin_config': skinConfig};
        }
      }
    } catch (e) {
      // 获取皮肤配置失败，忽略
      print('Failed to apply skin: $e');
    }
  }

  /// 从商城装备皮肤（购买后调用）
  Future<bool> equipSkinFromShop(String skinId) async {
    try {
      final inventory = await _shopRepository.getInventory();
      final skins = inventory['skins'] as List<dynamic>? ?? [];

      final skin = skins.firstWhere(
        (item) => item['id'] == skinId,
        orElse: () => null,
      );

      if (skin != null) {
        final skinConfig = skin['item_config'] as Map<String, dynamic>?;
        if (skinConfig != null) {
          await _themeManager.equipShopSkin(skinId, skinConfig);
          _currentSkinId = skinId;
          state = {'skin_id': skinId, 'skin_config': skinConfig};
          return true;
        }
      }
      return false;
    } catch (e) {
      print('Failed to equip skin: $e');
      return false;
    }
  }

  /// 卸载当前皮肤
  Future<void> unequipSkin() async {
    await _themeManager.unequipSkin();
    _currentSkinId = null;
    state = null;
  }

  @override
  void dispose() {
    _authNotifier.removeListener(_onAuthStateChanged);
    super.dispose();
  }
}

/// 皮肤Provider
final skinProvider = StateNotifierProvider<SkinNotifier, Map<String, dynamic>?>((ref) {
  final themeManager = ref.watch<ThemeManager>(themeManagerProvider);
  final shopRepository = ref.watch<ShopRepository>(shopRepositoryProvider);
  final authNotifier = ref.watch<AuthNotifier>(authProvider.notifier);

  return SkinNotifier(
    themeManager,
    shopRepository,
    authNotifier,
  );
});

/// 当前装备的皮肤ID
final equippedSkinIdProvider = Provider<String?>((ref) {
  final skinState = ref.watch(skinProvider);
  return skinState?['skin_id'] as String?;
});

/// 当前皮肤配置
final skinConfigProvider = Provider<Map<String, dynamic>?>((ref) {
  final skinState = ref.watch(skinProvider);
  return skinState?['skin_config'] as Map<String, dynamic>?;
});
