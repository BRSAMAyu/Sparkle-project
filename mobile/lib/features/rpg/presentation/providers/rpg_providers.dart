import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/rpg/data/models/rpg_models.dart';
import 'package:sparkle/features/rpg/data/repositories/mock_rpg_repository.dart';

/// RPG成长系统相关状态管理

/// 模拟RPG仓库实例
final mockRpgRepositoryProvider = Provider((ref) => MockRpgRepository());

/// 角色状态Provider
final characterProvider = StateNotifierProvider<CharacterNotifier, Character>((ref) {
  final repository = ref.watch(mockRpgRepositoryProvider);
  return CharacterNotifier(repository.getMockCharacter());
});

/// 装备列表Provider
final equipmentListProvider = Provider((ref) {
  final repository = ref.watch(mockRpgRepositoryProvider);
  return repository.getMockEquipment();
});

/// 解锁的装备Provider
final unlockedEquipmentProvider = Provider<List<Equipment>>((ref) {
  final character = ref.watch(characterProvider);
  final allEquipment = ref.watch(equipmentListProvider);
  
  return allEquipment.where((eq) => character.unlockedEquipment?.contains(eq.id) ?? false).toList();
});

/// 角色状态管理器
class CharacterNotifier extends StateNotifier<Character> {
  CharacterNotifier(super.initialState);

  /// 装备物品
  void equipItem(String equipmentId, EquipmentType type) {
    final updatedEquipment = switch (type) {
      EquipmentType.hat => state.equipment.copyWith(hat: equipmentId),
      EquipmentType.shirt => state.equipment.copyWith(shirt: equipmentId),
      EquipmentType.pants => state.equipment.copyWith(pants: equipmentId),
      EquipmentType.shoes => state.equipment.copyWith(shoes: equipmentId),
      EquipmentType.weapon => state.equipment.copyWith(weapon: equipmentId),
      EquipmentType.accessory => state.equipment.copyWith(accessory: equipmentId),
    };

    state = state.copyWith(equipment: updatedEquipment);
  }

  /// 卸载物品
  void unequipItem(EquipmentType type) {
    final updatedEquipment = switch (type) {
      EquipmentType.hat => state.equipment.copyWith(hat: null),
      EquipmentType.shirt => state.equipment.copyWith(shirt: null),
      EquipmentType.pants => state.equipment.copyWith(pants: null),
      EquipmentType.shoes => state.equipment.copyWith(shoes: null),
      EquipmentType.weapon => state.equipment.copyWith(weapon: null),
      EquipmentType.accessory => state.equipment.copyWith(accessory: null),
    };

    state = state.copyWith(equipment: updatedEquipment);
  }

  /// 解锁装备
  void unlockEquipment(String equipmentId) {
    final currentUnlocked = state.unlockedEquipment ?? [];
    if (!currentUnlocked.contains(equipmentId)) {
      final updatedUnlocked = [...currentUnlocked, equipmentId];
      state = state.copyWith(unlockedEquipment: updatedUnlocked);
    }
  }

  /// 添加经验值
  void addExperience(int amount) {
    const levelUpExp = 1000; // 每级所需经验值
    final newExp = state.experience + amount;
    
    if (newExp >= levelUpExp) {
      // 升级
      final newLevel = state.level + 1;
      final remainingExp = newExp - levelUpExp;
      
      // 升级时增加基础属性
      final updatedAttributes = state.baseAttributes.map((attr) {
        // 每级增加1-2点随机属性
        final increase = 1 + (DateTime.now().millisecond % 2);
        return AttributeValue(
          attribute: attr.attribute,
          value: attr.value + increase,
        );
      }).toList();
      
      state = state.copyWith(
        level: newLevel,
        experience: remainingExp,
        baseAttributes: updatedAttributes,
      );
    } else {
      state = state.copyWith(experience: newExp);
    }
  }

  /// 更新登录天数
  void updateLoginDays() {
    final today = DateTime.now();
    final lastLogin = state.lastLogin;
    
    // 检查是否是新的一天登录
    if (lastLogin == null || 
        today.day != lastLogin.day || 
        today.month != lastLogin.month || 
        today.year != lastLogin.year) {
      
      final newLoginDays = (state.totalLoginDays ?? 0) + 1;
      state = state.copyWith(
        totalLoginDays: newLoginDays,
        lastLogin: today,
      );
      
      // 每日登录奖励经验值
      addExperience(100);
    }
  }
}

/// 当前装备的属性总和Provider
final totalAttributesProvider = Provider<List<AttributeValue>>((ref) {
  final character = ref.watch(characterProvider);
  final allEquipment = ref.watch(equipmentListProvider);
  
  // 获取当前装备的ID列表
  final equippedIds = [
    character.equipment.hat,
    character.equipment.shirt,
    character.equipment.pants,
    character.equipment.shoes,
    character.equipment.weapon,
    character.equipment.accessory,
  ].where((id) => id != null).map((id) => id!).toList();
  
  // 获取当前装备的物品
  final equippedEquipment = allEquipment.where((eq) => equippedIds.contains(eq.id)).toList();
  
  // 合并基础属性和装备属性
  final attributeMap = <CharacterAttribute, int>{};
  
  // 添加基础属性
  for (final attr in character.baseAttributes) {
    attributeMap[attr.attribute] = attr.value;
  }
  
  // 添加装备属性
  for (final equipment in equippedEquipment) {
    for (final attr in equipment.attributes) {
      attributeMap[attr.attribute] = (attributeMap[attr.attribute] ?? 0) + attr.value;
    }
  }
  
  // 转换为AttributeValue列表
  return attributeMap.entries.map((entry) => AttributeValue(
    attribute: entry.key,
    value: entry.value,
  )).toList();
});
