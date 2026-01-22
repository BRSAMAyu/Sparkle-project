import 'package:sparkle/features/rpg/data/models/rpg_models.dart';
import 'package:sparkle/features/rpg/data/models/task_models.dart';

/// 模拟任务数据仓库
class MockTaskRepository {
  /// 获取模拟每日任务
  List<Task> getMockDailyTasks() {
    return [
      Task(
        id: 'daily_1',
        title: '每日登录',
        description: '每天登录应用即可完成',
        type: TaskType.daily,
        status: TaskStatus.pending,
        rewards: [
          TaskReward(
            type: RewardType.experience,
            value: 100,
          ),
        ],
        progress: 0,
        target: 1,
        icon: 'login',
        createdAt: DateTime.now(),
      ),
      Task(
        id: 'daily_2',
        title: '完成1次专注',
        description: '使用专注功能完成1次专注',
        type: TaskType.daily,
        status: TaskStatus.pending,
        rewards: [
          TaskReward(
            type: RewardType.experience,
            value: 150,
          ),
        ],
        progress: 0,
        target: 1,
        icon: 'focus',
        createdAt: DateTime.now(),
      ),
      Task(
        id: 'daily_3',
        title: '学习30分钟',
        description: '累计学习时间达到30分钟',
        type: TaskType.daily,
        status: TaskStatus.pending,
        rewards: [
          TaskReward(
            type: RewardType.experience,
            value: 200,
          ),
        ],
        progress: 0,
        target: 30,
        icon: 'study',
        createdAt: DateTime.now(),
      ),
    ];
  }

  /// 获取模拟成就任务
  List<Task> getMockAchievementTasks() {
    return [
      Task(
        id: 'achievement_1',
        title: '初次登录',
        description: '第一次登录应用',
        type: TaskType.achievement,
        status: TaskStatus.completed,
        rewards: [
          TaskReward(
            type: RewardType.equipment,
            value: 1,
            equipmentId: 'hat_1',
          ),
          TaskReward(
            type: RewardType.experience,
            value: 500,
          ),
        ],
        progress: 1,
        target: 1,
        icon: 'trophy',
        createdAt: DateTime.now(),
        completedAt: DateTime.now().subtract(const Duration(days: 1)),
      ),
      Task(
        id: 'achievement_2',
        title: '连续登录7天',
        description: '连续7天登录应用',
        type: TaskType.achievement,
        status: TaskStatus.pending,
        rewards: [
          TaskReward(
            type: RewardType.equipment,
            value: 1,
            equipmentId: 'weapon_1',
          ),
          TaskReward(
            type: RewardType.experience,
            value: 1000,
          ),
        ],
        progress: 3,
        target: 7,
        icon: 'calendar',
        createdAt: DateTime.now(),
      ),
      Task(
        id: 'achievement_3',
        title: '完成10次专注',
        description: '累计完成10次专注',
        type: TaskType.achievement,
        status: TaskStatus.pending,
        rewards: [
          TaskReward(
            type: RewardType.attribute,
            value: 5,
            attributeType: CharacterAttribute.strength,
          ),
          TaskReward(
            type: RewardType.experience,
            value: 800,
          ),
        ],
        progress: 5,
        target: 10,
        icon: 'target',
        createdAt: DateTime.now(),
      ),
    ];
  }

  /// 获取模拟连续登录任务
  List<Task> getMockLoginStreakTasks() {
    return [
      Task(
        id: 'streak_1',
        title: '连续登录3天',
        description: '连续3天登录应用',
        type: TaskType.loginStreak,
        status: TaskStatus.pending,
        rewards: [
          TaskReward(
            type: RewardType.equipment,
            value: 1,
            equipmentId: 'shirt_1',
          ),
        ],
        progress: 2,
        target: 3,
        icon: 'fire',
        createdAt: DateTime.now(),
        loginStreakRequirement: 3,
      ),
      Task(
        id: 'streak_2',
        title: '连续登录15天',
        description: '连续15天登录应用',
        type: TaskType.loginStreak,
        status: TaskStatus.pending,
        rewards: [
          TaskReward(
            type: RewardType.equipment,
            value: 1,
            equipmentId: 'pants_1',
          ),
          TaskReward(
            type: RewardType.experience,
            value: 2000,
          ),
        ],
        progress: 5,
        target: 15,
        icon: 'diamond',
        createdAt: DateTime.now(),
        loginStreakRequirement: 15,
      ),
    ];
  }

  /// 获取模拟活动任务
  List<Task> getMockActivityTasks() {
    return [
      Task(
        id: 'activity_1',
        title: '新手挑战',
        description: '完成所有新手任务',
        type: TaskType.activity,
        status: TaskStatus.pending,
        rewards: [
          TaskReward(
            type: RewardType.equipment,
            value: 1,
            equipmentId: 'shoes_1',
          ),
          TaskReward(
            type: RewardType.experience,
            value: 1500,
          ),
        ],
        progress: 2,
        target: 3,
        icon: 'star',
        createdAt: DateTime.now(),
      ),
    ];
  }
}

/// 模拟任务仓库实例
final mockTaskRepository = MockTaskRepository();
