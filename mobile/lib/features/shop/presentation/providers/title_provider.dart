import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/shop/data/repositories/shop_repository.dart';
import 'package:sparkle/features/shop/data/repositories/shop_repository_provider.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';
import 'package:sparkle/shared/entities/shop_model.dart';

/// 称号服务
///
/// 管理用户的称号装备和显示
class TitleNotifier extends StateNotifier<Map<String, dynamic>?> {
  TitleNotifier(
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

  final ShopRepository _shopRepository;
  final Ref _ref;
  String? _currentTitleId;
  String? _currentTitleSource;
  ProviderSubscription? _authStateSubscription;

  /// 当认证状态变化时，加载用户的称号
  void _onAuthStateChanged(AuthState authState) {
    final user = authState.user;
    if (user != null &&
        user.equippedTitle != null &&
        user.equippedTitleSource != null) {
      unawaited(_loadTitle(user.equippedTitle!, user.equippedTitleSource!));
    } else {
      _currentTitleId = null;
      _currentTitleSource = null;
      state = null;
    }
  }

  /// 加载称号配置
  Future<void> _loadTitle(String titleId, String source) async {
    if (_currentTitleId == titleId && _currentTitleSource == source) return;

    try {
      if (source == 'shop') {
        final inventory = await _shopRepository.getInventory();
        if (!mounted) return;
        final titles = inventory['titles'] ?? <InventoryItem>[];
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
            if (!mounted) return;
            _currentTitleId = titleId;
            _currentTitleSource = source;
            state = {
              'id': titleId,
              'name': matchedTitle.name,
              'config': titleConfig,
            };
          }
        }
        return;
      }

      if (source == 'achievement') {
        final achievementRepository = _ref.read(achievementRepositoryProvider);
        final titles = await achievementRepository.getTitles();
        if (!mounted) return;
        UserTitle? matchedTitle;
        for (final item in titles) {
          if (item.titleId == titleId) {
            matchedTitle = item;
            break;
          }
        }
        if (matchedTitle != null) {
          if (!mounted) return;
          _currentTitleId = titleId;
          _currentTitleSource = source;
          state = {
            'id': titleId,
            'name': matchedTitle.titleName,
            'config': {
              'text': matchedTitle.titleDisplay,
              'display_format': 'prefix',
            },
          };
        }
      }
    } catch (e) {
      if (mounted) {
        debugPrint('Failed to load title: $e');
      }
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
        await _loadTitle(titleId, 'shop');
        return true;
      }
      return false;
    } catch (e) {
      debugPrint('Failed to equip title: $e');
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
        _currentTitleId = null;
        _currentTitleSource = null;
        state = null;
        return true;
      }
      return false;
    } catch (e) {
      debugPrint('Failed to unequip title: $e');
      return false;
    }
  }

  @override
  void dispose() {
    _authStateSubscription?.close();
    super.dispose();
  }
}

/// 称号Provider
final titleProvider =
    StateNotifierProvider<TitleNotifier, Map<String, dynamic>?>((ref) {
  final shopRepository = ref.watch<ShopRepository>(shopRepositoryProvider);

  return TitleNotifier(
    shopRepository,
    ref,
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
