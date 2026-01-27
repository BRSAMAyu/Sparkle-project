import 'package:sparkle/features/rpg/data/models/rpg_models.dart';

/// 模拟RPG数据仓库
class MockRpgRepository {
  /// 获取模拟角色数据
  Character getMockCharacter() {
    return Character(
      id: 'user_123',
      userId: 'user_123',
      nickname: '学习战士',
      level: 10,
      experience: 1500,
      maxExperience: 2000,
      currentHp: 85,
      maxHp: 100,
      gold: 500,
      gems: 10,
      baseAttributes: [
        AttributeValue(attribute: CharacterAttribute.strength, value: 15),
        AttributeValue(attribute: CharacterAttribute.intelligence, value: 12),
        AttributeValue(attribute: CharacterAttribute.agility, value: 10),
        AttributeValue(attribute: CharacterAttribute.vitality, value: 18),
        AttributeValue(attribute: CharacterAttribute.luck, value: 5),
      ],
      equipment: CharacterEquipment(
        hat: 'hat_1',
        shirt: 'shirt_1',
        pants: 'pants_1',
        shoes: 'shoes_1',
        weapon: 'weapon_1',
        accessory: 'accessory_1',
      ),
      unlockedEquipment: [
        'hat_1', 'shirt_1', 'pants_1', 'shoes_1', 'weapon_1', 'accessory_1',
      ],
      characterClass: '学习战士',
      totalLoginDays: 25,
      lastLogin: DateTime.now().subtract(const Duration(days: 1)),
    );
  }

  /// 获取模拟装备列表
  List<Equipment> getMockEquipment() {
    return [
      Equipment(
        id: 'hat_1',
        name: '智慧帽',
        type: EquipmentType.hat,
        rarity: Rarity.common,
        attributes: [
          AttributeValue(attribute: CharacterAttribute.intelligence, value: 2),
        ],
        description: '增加智力的帽子',
        spritePath: 'assets/character/hat_1.png',
        isUnlocked: true,
        unlockedAt: DateTime.now().subtract(const Duration(days: 5)),
      ),
      Equipment(
        id: 'shirt_1',
        name: '学习衬衫',
        type: EquipmentType.shirt,
        rarity: Rarity.uncommon,
        attributes: [
          AttributeValue(attribute: CharacterAttribute.strength, value: 3),
        ],
        description: '增加力量的衬衫',
        spritePath: 'assets/character/shirt_1.png',
        isUnlocked: true,
        unlockedAt: DateTime.now().subtract(const Duration(days: 10)),
      ),
      Equipment(
        id: 'pants_1',
        name: '敏捷长裤',
        type: EquipmentType.pants,
        rarity: Rarity.common,
        attributes: [
          AttributeValue(attribute: CharacterAttribute.agility, value: 2),
        ],
        description: '增加敏捷的长裤',
        spritePath: 'assets/character/pants_1.png',
        isUnlocked: true,
        unlockedAt: DateTime.now().subtract(const Duration(days: 15)),
      ),
      Equipment(
        id: 'shoes_1',
        name: '活力之靴',
        type: EquipmentType.shoes,
        rarity: Rarity.rare,
        attributes: [
          AttributeValue(attribute: CharacterAttribute.vitality, value: 4),
        ],
        description: '增加活力的靴子',
        spritePath: 'assets/character/shoes_1.png',
        isUnlocked: true,
        unlockedAt: DateTime.now().subtract(const Duration(days: 20)),
      ),
      Equipment(
        id: 'weapon_1',
        name: '知识之剑',
        type: EquipmentType.weapon,
        rarity: Rarity.epic,
        attributes: [
          AttributeValue(attribute: CharacterAttribute.strength, value: 5),
          AttributeValue(attribute: CharacterAttribute.intelligence, value: 3),
        ],
        description: '同时增加力量和智力的剑',
        spritePath: 'assets/character/weapon_1.png',
        isUnlocked: true,
        unlockedAt: DateTime.now().subtract(const Duration(days: 25)),
      ),
      Equipment(
        id: 'accessory_1',
        name: '幸运项链',
        type: EquipmentType.accessory,
        rarity: Rarity.legendary,
        attributes: [
          AttributeValue(attribute: CharacterAttribute.luck, value: 10),
        ],
        description: '大幅增加幸运的项链',
        spritePath: 'assets/character/accessory_1.png',
        isUnlocked: true,
        unlockedAt: DateTime.now().subtract(const Duration(days: 30)),
      ),
    ];
  }
}

/// 模拟RPG仓库实例
final mockRpgRepository = MockRpgRepository();
