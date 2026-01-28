import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/shop/data/repositories/shop_repository.dart';
import 'package:sparkle/shared/entities/shop_model.dart';

/// 消耗品效果状态
class ConsumableEffectState {
  ConsumableEffectState({
    this.expBoostMultiplier = 1.0,
    this.expBoostEndTime,
    this.photonBoostMultiplier = 1.0,
    this.photonBoostEndTime,
    this.streakFreezeCharges = 0,
    this.hintRevealCharges = 0,
    this.customAvatarUnlocked = false,
  });

  final double expBoostMultiplier;
  final DateTime? expBoostEndTime;
  final double photonBoostMultiplier;
  final DateTime? photonBoostEndTime;
  final int streakFreezeCharges;
  final int hintRevealCharges;
  final bool customAvatarUnlocked;

  /// 检查经验加成是否有效
  bool get isExpBoostActive =>
      expBoostMultiplier > 1.0 &&
      (expBoostEndTime == null || DateTime.now().isBefore(expBoostEndTime!));

  /// 检查光子加成是否有效
  bool get isPhotonBoostActive =>
      photonBoostMultiplier > 1.0 &&
      (photonBoostEndTime == null ||
          DateTime.now().isBefore(photonBoostEndTime!));

  /// 检查是否有连击冻结次数
  bool get hasStreakFreeze => streakFreezeCharges > 0;

  /// 检查是否有提示解锁次数
  bool get hasHintReveal => hintRevealCharges > 0;

  ConsumableEffectState copyWith({
    double? expBoostMultiplier,
    DateTime? expBoostEndTime,
    double? photonBoostMultiplier,
    DateTime? photonBoostEndTime,
    int? streakFreezeCharges,
    int? hintRevealCharges,
    bool? customAvatarUnlocked,
  }) =>
      ConsumableEffectState(
        expBoostMultiplier: expBoostMultiplier ?? this.expBoostMultiplier,
        expBoostEndTime: expBoostEndTime ?? this.expBoostEndTime,
        photonBoostMultiplier:
            photonBoostMultiplier ?? this.photonBoostMultiplier,
        photonBoostEndTime:
            photonBoostEndTime ?? this.photonBoostEndTime,
        streakFreezeCharges:
            streakFreezeCharges ?? this.streakFreezeCharges,
        hintRevealCharges: hintRevealCharges ?? this.hintRevealCharges,
        customAvatarUnlocked:
            customAvatarUnlocked ?? this.customAvatarUnlocked,
      );
}

/// 消耗品效果管理器
class ConsumableEffectNotifier extends StateNotifier<ConsumableEffectState> {
  ConsumableEffectNotifier(this._shopRepository)
      : super(ConsumableEffectState()) {
    _loadActiveEffects();
  }

  final ShopRepository _shopRepository;

  /// 加载当前生效的效果
  Future<void> _loadActiveEffects() async {
    try {
      final inventory = await _shopRepository.getInventory();
      final consumables =
          inventory['consumables'] as List<dynamic>? ?? [];
      final boosts = inventory['boosts'] as List<dynamic>? ?? [];

      double expMultiplier = 1.0;
      DateTime? expEndTime;
      double photonMultiplier = 1.0;
      DateTime? photonEndTime;
      int streakCharges = 0;
      int hintCharges = 0;
      bool customAvatar = false;

      // 检查所有消耗品
      for (final item in [...consumables, ...boosts]) {
        final consumable = item as Map<String, dynamic>;
        final quantity = consumable['quantity'] as int? ?? 0;
        if (quantity <= 0) continue;

        final effectType = consumable['effect_type'] as String?;
        final config = consumable['item_config'] as Map<String, dynamic>?;

        if (effectType == null || config == null) continue;

        switch (effectType) {
          case 'exp_boost':
            final multiplier = config['multiplier'] as double? ?? 1.0;
            final duration = config['duration_hours'] as int? ?? 0;
            if (multiplier > expMultiplier) {
              expMultiplier = multiplier;
              // 假设从购买时间开始计算
              final createdAt = consumable['created_at'] as String?;
              if (createdAt != null && duration > 0) {
                expEndTime = DateTime.parse(createdAt).add(
                  Duration(hours: duration),
                );
              }
            }
            break;

          case 'photon_boost':
            final multiplier = config['multiplier'] as double? ?? 1.0;
            if (multiplier > photonMultiplier) {
              photonMultiplier = multiplier;
              final duration = config['duration_hours'] as int? ?? 0;
              final createdAt = consumable['created_at'] as String?;
              if (createdAt != null && duration > 0) {
                photonEndTime = DateTime.parse(createdAt).add(
                  Duration(hours: duration),
                );
              }
            }
            break;

          case 'streak_freeze':
            streakCharges += quantity;
            break;

          case 'hint_reveal':
            hintCharges += quantity;
            break;

          case 'custom_avatar':
            if (config['permanent'] == true) {
              customAvatar = true;
            }
            break;
        }
      }

      state = ConsumableEffectState(
        expBoostMultiplier: expMultiplier,
        expBoostEndTime: expEndTime,
        photonBoostMultiplier: photonMultiplier,
        photonBoostEndTime: photonEndTime,
        streakFreezeCharges: streakCharges,
        hintRevealCharges: hintCharges,
        customAvatarUnlocked: customAvatar,
      );
    } catch (e) {
      print('Failed to load consumable effects: $e');
    }
  }

  /// 使用消耗品
  Future<Map<String, dynamic>> useConsumable(String consumableId) async {
    try {
      final result = await _shopRepository.useConsumable(consumableId);

      if (result['success'] == true) {
        // 重新加载效果状态
        await _loadActiveEffects();
      }

      return result;
    } catch (e) {
      return {
        'success': false,
        'error': e.toString(),
      };
    }
  }

  /// 获取当前经验倍率
  double getExpMultiplier() {
    return state.isExpBoostActive ? state.expBoostMultiplier : 1.0;
  }

  /// 获取当前光子倍率
  double getPhotonMultiplier() {
    return state.isPhotonBoostActive ? state.photonBoostMultiplier : 1.0;
  }

  /// 使用连击冻结
  bool useStreakFreeze() {
    if (!state.hasStreakFreeze) return false;

    state = state.copyWith(
      streakFreezeCharges: state.streakFreezeCharges - 1,
    );
    return true;
  }

  /// 使用提示解锁
  bool useHintReveal() {
    if (!state.hasHintReveal) return false;

    state = state.copyWith(
      hintRevealCharges: state.hintRevealCharges - 1,
    );
    return true;
  }

  /// 刷新效果状态
  Future<void> refresh() async {
    await _loadActiveEffects();
  }
}

/// 消耗品效果Provider
final consumableEffectProvider =
    StateNotifierProvider<ConsumableEffectNotifier, ConsumableEffectState>((ref) {
  final shopRepository = ref.watch(shopRepositoryProvider);
  return ConsumableEffectNotifier(shopRepository);
});

/// 当前经验倍率Provider
final expMultiplierProvider = Provider<double>((ref) {
  final effectState = ref.watch(consumableEffectProvider);
  return effectState.isExpBoostActive
      ? effectState.expBoostMultiplier
      : 1.0;
});

/// 当前光子倍率Provider
final photonMultiplierProvider = Provider<double>((ref) {
  final effectState = ref.watch(consumableEffectProvider);
  return effectState.isPhotonBoostActive
      ? effectState.photonBoostMultiplier
      : 1.0;
});

/// 经验加成剩余时间Provider
final expBoostTimeLeftProvider = Provider<Duration?>((ref) {
  final effectState = ref.watch(consumableEffectProvider);
  final endTime = effectState.expBoostEndTime;
  if (endTime == null) return null;

  final now = DateTime.now();
  if (now.isAfter(endTime)) return null;

  return endTime.difference(now);
});
