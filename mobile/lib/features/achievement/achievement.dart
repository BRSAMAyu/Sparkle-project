/// 成就系统功能导出
library;

// 实体
export '../../shared/entities/achievement_model.dart'
    show
        AchievementMapData,
        AchievementMapNode,
        AchievementModel,
        AchievementRarity,
        AchievementStats,
        AchievementType,
        AchievementUnlockEvent,
        AchievementWithProgress,
        ContractStatus,
        GalaxySkin,
        SparkContract,
        StreakStats,
        UserAchievementProgress,
        UserTitle,
        VisualEffectType;
// 路由
export 'achievement_routes.dart';
// 数据层
export 'data/repositories/achievement_repository.dart'
    hide AchievementListResponse, GalaxySkinListResponse;
// 状态管理
export 'presentation/providers/achievement_provider.dart';
// 页面
export 'presentation/screens/achievement_detail_screen.dart';
export 'presentation/screens/achievement_list_screen.dart';
// 组件
export 'presentation/widgets/achievement_card.dart';
export 'presentation/widgets/achievement_stats_panel.dart';
export 'presentation/widgets/achievement_unlock_dialog.dart';
export 'presentation/widgets/rarity_badge.dart';
export 'presentation/widgets/streak_indicator.dart';
