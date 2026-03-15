import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/tokens_v2/theme_manager.dart';
import 'package:sparkle/core/providers/theme_provider.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/shop/data/repositories/shop_repository.dart';
import 'package:sparkle/features/shop/data/repositories/shop_repository_provider.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';
import 'package:sparkle/shared/entities/shop_model.dart';

/// 皮肤应用服务
///
/// 监听用户登录状态，自动应用装备的皮肤到主题系统
class SkinNotifier extends StateNotifier<Map<String, dynamic>?> {
  SkinNotifier(
    this._themeManager,
    this._shopRepository,
    this._ref,
  ) : super(null) {
    // 监听认证状态变化
    _authStateSubscription = _ref.listen<AuthState>(
      authProvider,
      (previous, next) {
        _onAuthStateChanged(next);
      },
      fireImmediately: true,
    );
  }

  final ThemeManager _themeManager;
  final ShopRepository _shopRepository;
  final Ref _ref;
  String? _currentSkinId;
  String? _currentSkinSource;
  int _skinChangeVersion = 0;
  ProviderSubscription? _authStateSubscription;

  /// 当认证状态变化时，应用用户的装备皮肤
  void _onAuthStateChanged(AuthState authState) {
    _skinChangeVersion += 1;
    final version = _skinChangeVersion;
    final user = authState.user;
    if (user != null) {
      unawaited(
        _applyUserSkin(user.equippedSkin, user.equippedSkinSource, version),
      );
    } else {
      unawaited(_clearAppliedSkin(version));
    }
  }

  /// 应用用户装备的皮肤
  Future<void> _applyUserSkin(
    String? skinId,
    String? source,
    int version,
  ) async {
    if (!mounted || version != _skinChangeVersion) return;
    if (skinId == null || source == null) {
      await _clearAppliedSkin(version);
      return;
    }
    if (skinId == _currentSkinId && source == _currentSkinSource) return;

    try {
      Map<String, dynamic>? skinConfig;

      if (source == 'shop') {
        final inventory = await _shopRepository.getInventory();
        final skins = inventory['skins'] ?? <InventoryItem>[];
        InventoryItem? equippedSkin;
        for (final item in skins) {
          if (item.id == skinId) {
            equippedSkin = item;
            break;
          }
        }
        skinConfig = equippedSkin?.itemConfig;
      } else if (source == 'achievement') {
        final achievementRepository = _ref.read(achievementRepositoryProvider);
        final response = await achievementRepository.getGalaxySkins();
        GalaxySkin? equippedSkin;
        for (final item in response.skins) {
          if (item.id == skinId) {
            equippedSkin = item;
            break;
          }
        }
        skinConfig = equippedSkin?.skinConfig;
      }

      if (skinConfig != null) {
        await _themeManager.equipShopSkin(skinId, skinConfig);
        if (!mounted || version != _skinChangeVersion) return;
        _currentSkinId = skinId;
        _currentSkinSource = source;
        state = {
          'skin_id': skinId,
          'skin_source': source,
          'skin_config': skinConfig,
        };
      }
    } catch (e) {
      if (mounted && version == _skinChangeVersion) {
        debugPrint('Failed to apply skin: $e');
      }
    }
  }

  Future<void> _clearAppliedSkin(int version) async {
    _currentSkinId = null;
    _currentSkinSource = null;
    state = null;

    await _themeManager.unequipSkin();
    if (!mounted || version != _skinChangeVersion) return;
  }

  /// 从商城装备皮肤（购买后调用）
  Future<bool> equipSkinFromShop(String skinId) async {
    try {
      final inventory = await _shopRepository.getInventory();
      final skins = inventory['skins'] ?? <InventoryItem>[];
      InventoryItem? skin;
      for (final item in skins) {
        if (item.id == skinId) {
          skin = item;
          break;
        }
      }

      if (skin != null) {
        final skinConfig = skin.itemConfig;
        if (skinConfig != null) {
          await _themeManager.equipShopSkin(skinId, skinConfig);
          _currentSkinId = skinId;
          _currentSkinSource = 'shop';
          state = {
            'skin_id': skinId,
            'skin_source': 'shop',
            'skin_config': skinConfig,
          };
          return true;
        }
      }
      return false;
    } catch (e) {
      debugPrint('Failed to equip skin: $e');
      return false;
    }
  }

  /// 卸载当前皮肤
  Future<void> unequipSkin() async {
    await _themeManager.unequipSkin();
    _currentSkinId = null;
    _currentSkinSource = null;
    state = null;
  }

  @override
  void dispose() {
    _authStateSubscription?.close();
    super.dispose();
  }
}

/// 皮肤Provider
final skinProvider =
    StateNotifierProvider<SkinNotifier, Map<String, dynamic>?>((ref) {
  final themeManager = ref.watch<ThemeManager>(themeManagerProvider);
  final shopRepository = ref.watch<ShopRepository>(shopRepositoryProvider);

  return SkinNotifier(
    themeManager,
    shopRepository,
    ref,
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
