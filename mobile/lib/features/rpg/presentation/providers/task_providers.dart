import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/rpg/data/models/task_models.dart';
import 'package:sparkle/features/rpg/data/repositories/mock_task_repository.dart';
import 'package:sparkle/features/rpg/presentation/providers/rpg_providers.dart';

/// 任务系统相关状态管理

/// 模拟任务仓库实例
final mockTaskRepositoryProvider = Provider((ref) => MockTaskRepository());

/// 任务系统状态Provider
final taskSystemProvider = StateNotifierProvider<TaskSystemNotifier, TaskSystemState>((ref) {
  final repository = ref.watch(mockTaskRepositoryProvider);
  return TaskSystemNotifier(
    TaskSystemState(
      dailyTasks: repository.getMockDailyTasks(),
      achievementTasks: repository.getMockAchievementTasks(),
      loginStreakTasks: repository.getMockLoginStreakTasks(),
      activityTasks: repository.getMockActivityTasks(),
      isLoading: false,
    ),
    ref,
  );
});

/// 任务系统状态管理器
class TaskSystemNotifier extends StateNotifier<TaskSystemState> {
  TaskSystemNotifier(super.initialState, this.ref);

  final Ref ref;

  /// 更新任务进度
  void updateTaskProgress(String taskId, int progressDelta) {
    // 更新每日任务
    final updatedDailyTasks = state.dailyTasks.map((task) {
      if (task.id == taskId) {
        final newProgress = task.progress + progressDelta;
        final newStatus = newProgress >= task.target 
            ? TaskStatus.completed 
            : task.status;
        
        return task.copyWith(
          progress: newProgress > task.target ? task.target : newProgress,
          status: newStatus,
          completedAt: newStatus == TaskStatus.completed && task.status != TaskStatus.completed 
              ? DateTime.now() 
              : task.completedAt,
        );
      }
      return task;
    }).toList();

    // 更新成就任务
    final updatedAchievementTasks = state.achievementTasks.map((task) {
      if (task.id == taskId) {
        final newProgress = task.progress + progressDelta;
        final newStatus = newProgress >= task.target 
            ? TaskStatus.completed 
            : task.status;
        
        return task.copyWith(
          progress: newProgress > task.target ? task.target : newProgress,
          status: newStatus,
          completedAt: newStatus == TaskStatus.completed && task.status != TaskStatus.completed 
              ? DateTime.now() 
              : task.completedAt,
        );
      }
      return task;
    }).toList();

    // 更新连续登录任务
    final updatedLoginStreakTasks = state.loginStreakTasks.map((task) {
      if (task.id == taskId) {
        final newProgress = task.progress + progressDelta;
        final newStatus = newProgress >= task.target 
            ? TaskStatus.completed 
            : task.status;
        
        return task.copyWith(
          progress: newProgress > task.target ? task.target : newProgress,
          status: newStatus,
          completedAt: newStatus == TaskStatus.completed && task.status != TaskStatus.completed 
              ? DateTime.now() 
              : task.completedAt,
        );
      }
      return task;
    }).toList();

    // 更新活动任务
    final updatedActivityTasks = state.activityTasks.map((task) {
      if (task.id == taskId) {
        final newProgress = task.progress + progressDelta;
        final newStatus = newProgress >= task.target 
            ? TaskStatus.completed 
            : task.status;
        
        return task.copyWith(
          progress: newProgress > task.target ? task.target : newProgress,
          status: newStatus,
          completedAt: newStatus == TaskStatus.completed && task.status != TaskStatus.completed 
              ? DateTime.now() 
              : task.completedAt,
        );
      }
      return task;
    }).toList();

    state = state.copyWith(
      dailyTasks: updatedDailyTasks,
      achievementTasks: updatedAchievementTasks,
      loginStreakTasks: updatedLoginStreakTasks,
      activityTasks: updatedActivityTasks,
    );
  }

  /// 领取任务奖励
  void claimTaskReward(String taskId) {
    // 查找任务
    Task? task;
    TaskType? taskType;
    
    // 检查每日任务
    final dailyTaskIndex = state.dailyTasks.indexWhere((t) => t.id == taskId);
    if (dailyTaskIndex != -1) {
      task = state.dailyTasks[dailyTaskIndex];
      taskType = TaskType.daily;
    }
    
    // 检查成就任务
    if (task == null) {
      final achievementTaskIndex = state.achievementTasks.indexWhere((t) => t.id == taskId);
      if (achievementTaskIndex != -1) {
        task = state.achievementTasks[achievementTaskIndex];
        taskType = TaskType.achievement;
      }
    }
    
    // 检查连续登录任务
    if (task == null) {
      final loginStreakTaskIndex = state.loginStreakTasks.indexWhere((t) => t.id == taskId);
      if (loginStreakTaskIndex != -1) {
        task = state.loginStreakTasks[loginStreakTaskIndex];
        taskType = TaskType.loginStreak;
      }
    }
    
    // 检查活动任务
    if (task == null) {
      final activityTaskIndex = state.activityTasks.indexWhere((t) => t.id == taskId);
      if (activityTaskIndex != -1) {
        task = state.activityTasks[activityTaskIndex];
        taskType = TaskType.activity;
      }
    }
    
    if (task == null || task.status != TaskStatus.completed) {
      return;
    }
    
    // 处理奖励
    for (final reward in task.rewards) {
      _processReward(reward);
    }
    
    // 更新任务状态为已领取
    _updateTaskStatus(taskId, taskType!, TaskStatus.claimed);
  }

  /// 处理奖励
  void _processReward(TaskReward reward) {
    switch (reward.type) {
      case RewardType.experience:
        // 增加经验值
        ref.read(characterProvider.notifier).addExperience(reward.value);
        break;
      
      case RewardType.equipment:
        // 解锁装备
        if (reward.equipmentId != null) {
          ref.read(characterProvider.notifier).unlockEquipment(reward.equipmentId!);
        }
        break;
      
      case RewardType.attribute:
        // 增加属性点
        // 这里简化处理，直接增加经验值
        ref.read(characterProvider.notifier).addExperience(reward.value * 100);
        break;
    }
  }

  /// 更新任务状态
  void _updateTaskStatus(String taskId, TaskType taskType, TaskStatus newStatus) {
    switch (taskType) {
      case TaskType.daily:
        final updatedDailyTasks = state.dailyTasks.map((task) {
          if (task.id == taskId) {
            return task.copyWith(
              status: newStatus,
              claimedAt: newStatus == TaskStatus.claimed ? DateTime.now() : task.claimedAt,
            );
          }
          return task;
        }).toList();
        
        state = state.copyWith(dailyTasks: updatedDailyTasks);
        break;
      
      case TaskType.achievement:
        final updatedAchievementTasks = state.achievementTasks.map((task) {
          if (task.id == taskId) {
            return task.copyWith(
              status: newStatus,
              claimedAt: newStatus == TaskStatus.claimed ? DateTime.now() : task.claimedAt,
            );
          }
          return task;
        }).toList();
        
        state = state.copyWith(achievementTasks: updatedAchievementTasks);
        break;
      
      case TaskType.loginStreak:
        final updatedLoginStreakTasks = state.loginStreakTasks.map((task) {
          if (task.id == taskId) {
            return task.copyWith(
              status: newStatus,
              claimedAt: newStatus == TaskStatus.claimed ? DateTime.now() : task.claimedAt,
            );
          }
          return task;
        }).toList();
        
        state = state.copyWith(loginStreakTasks: updatedLoginStreakTasks);
        break;
      
      case TaskType.activity:
        final updatedActivityTasks = state.activityTasks.map((task) {
          if (task.id == taskId) {
            return task.copyWith(
              status: newStatus,
              claimedAt: newStatus == TaskStatus.claimed ? DateTime.now() : task.claimedAt,
            );
          }
          return task;
        }).toList();
        
        state = state.copyWith(activityTasks: updatedActivityTasks);
        break;
    }
  }

  /// 处理登录事件
  void handleLogin() {
    // 更新每日登录任务
    _updateDailyLoginTask();
    
    // 更新连续登录任务
    _updateLoginStreakTasks();
  }

  /// 更新每日登录任务
  void _updateDailyLoginTask() {
    final dailyTasks = state.dailyTasks.map((task) {
      if (task.title == '每日登录' && task.status == TaskStatus.pending) {
        return task.copyWith(
          progress: 1,
          status: TaskStatus.completed,
          completedAt: DateTime.now(),
        );
      }
      return task;
    }).toList();
    
    state = state.copyWith(dailyTasks: dailyTasks);
  }

  /// 更新连续登录任务
  void _updateLoginStreakTasks() {
    // 获取当前连续登录天数
    final loginDays = ref.read(characterProvider).totalLoginDays ?? 0;
    
    // 更新连续登录任务进度
    final updatedLoginStreakTasks = state.loginStreakTasks.map((task) {
      if (task.status == TaskStatus.pending) {
        final newProgress = loginDays;
        final newStatus = newProgress >= task.target 
            ? TaskStatus.completed 
            : task.status;
        
        return task.copyWith(
          progress: newProgress,
          status: newStatus,
          completedAt: newStatus == TaskStatus.completed && task.status != TaskStatus.completed 
              ? DateTime.now() 
              : task.completedAt,
        );
      }
      return task;
    }).toList();
    
    state = state.copyWith(loginStreakTasks: updatedLoginStreakTasks);
    
    // 更新成就任务中的连续登录任务
    final updatedAchievementTasks = state.achievementTasks.map((task) {
      if (task.title.contains('连续登录') && task.status == TaskStatus.pending) {
        final newProgress = loginDays;
        final newStatus = newProgress >= task.target 
            ? TaskStatus.completed 
            : task.status;
        
        return task.copyWith(
          progress: newProgress,
          status: newStatus,
          completedAt: newStatus == TaskStatus.completed && task.status != TaskStatus.completed 
              ? DateTime.now() 
              : task.completedAt,
        );
      }
      return task;
    }).toList();
    
    state = state.copyWith(achievementTasks: updatedAchievementTasks);
  }

  /// 重置每日任务
  void resetDailyTasks() {
    final repository = ref.read(mockTaskRepositoryProvider);
    state = state.copyWith(dailyTasks: repository.getMockDailyTasks());
  }
}
