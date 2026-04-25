# Reviewer A — E05: Achievement Engine事件消费者完整性
Timestamp: 2026-04-26T12:45:00+08:00
Chain Index: 17

## Chain Flow Summary
用户完成任务/专注/Galaxy节点等行为后，EventBus传递事件到AchievementEventConsumer，consumer调用AchievementEngine.process_event检查成就条件，满足则解锁并发放奖励，通过WebSocket通知前端弹出庆祝弹窗。同时通过EventBus发布achievement.unlocked事件触发认知碎片记录和社区广播。整条链路核心通路通畅，但存在8种事件类型从未被触发、1种EventBus事件无人消费的断裂。

## Critical Issues 🔴

**achievement_engine.py:91-119 (AchievementEvent class)**: 8个事件类型定义了但生产代码从未触发。CONTRACT_COMPLETED、CONTRACT_FAILED、MUTUAL_STUDY、HIDDEN_TRIGGER、SPRINT_STARTED、SPRINT_ABANDONED、DAILY_CHECKIN、WEEKEND_WARRIOR 全部只有定义和case匹配，无任何外部调用者。Expected: 每个定义的事件类型都有对应的生产代码路径触发。Actual: 这8个事件类型的成就永远无法解锁。Evidence: grep `AchievementEvent\.(CONTRACT_COMPLETED|CONTRACT_FAILED|MUTUAL_STUDY|HIDDEN_TRIGGER|SPRINT_STARTED|SPRINT_ABANDONED|DAILY_CHECKIN)` 仅出现在定义处和_get_relevant_achievements的case匹配处，无任何process_event调用。ContractService.check_contract_status (line 2514-2544) 检查契约完成/失败但不调用achievement engine。

**achievement_engine.py:1322-1334 (_publish_achievement_progress)**: `achievement.progress`事件发布到EventBus但完全无消费者。Expected: 用户接近解锁成就时（25%/50%/75%进度），前端能看到进度提示。Actual: 事件写入Redis Streams后无人读取，永远积压。Evidence: grep `achievement\.progress` 在mobile/目录仅匹配到`progressPercentage`属性访问，无WebSocket消息类型`achievement_progress`的handler。在backend/也仅有发布点(achievement_engine.py:1323)和metrics引用，无任何consumer subscribe。

## Major Issues 🟡

**achievement_event_consumer.py:180-230 (_handle_achievement_unlocked)**: 里程碑通知通过NotificationService.create创建（带destination_route和deep_link），路由到`/achievements/milestone/{id}`正确。但`achievement_milestone` WebSocket事件在mobile端仅被`chat_notifier_actions.dart:604`处理为`lastActionStatus: 'milestone_reached'`，显示为chat中的短暂文本提示。Expected: 里程碑进度(25%/50%/75%)有持久可见的提示或toast。Actual: 仅在chat界面显示3秒状态文字，无toast/snackbar，不刷新成就地图。

**event_bus.py:1154-1173 (_process_stream_message)**: 消费者处理失败时直接调用`_move_to_dlq`，完全跳过了`_handle_failed_message`中的重试逻辑。Expected: 失败消息先重试3次再进DLQ。Actual: 任何消费失败（包括临时网络问题）立即进入DLQ，不重试。Evidence: `_requeue_for_retry`方法存在于line 871-909但从未从`_process_stream_message`调用。`_handle_failed_message`(line 911-951)有完整的重试/DLQ决策逻辑但同样未被调用。

## Minor Issues 🟢

None found beyond the above.

## Working Well ✅

- **task.completed EventBus路径**: task_service → EventBus → AchievementEventConsumer._handle_task_completed → process_event → 成就检查 → 解锁 → WebSocket `achievement_unlock` → mobile achievement_unlock_dialog.dart — 完整通畅
- **focus.session.completed路径**: focus_service直接调用process_event(STUDY_MINUTES_ACCUMULATED + NIGHT_STUDY/EARLY_BIRD)，同时EventBus consumer也处理——双路径冗余
- **galaxy.node.updated路径**: EventBus → consumer._handle_node_updated → NODE_UNLOCKED/NODE_MASTERED — 正确区分mastery阈值(0→解锁, 80→掌握)
- **plan.created路径**: 单独的AchievementPlanConsumer (journey consumer) 正确处理PLAN_CREATED事件，包含跨用户payload校验
- **Sprint事件路径**: exam_sprint_review_service和plans.py直接调用process_event(SPRINT_COMPLETED/PERFECT/AHEAD/STREAK)，不经EventBus——合理
- **成就解锁通知**: _notify_unlocks通过WebSocket发送type:`achievement_unlock`，mobile端shell_navigation.dart:145正确捕获并弹出achievement_unlock_dialog
- **里程碑推送**: _maybe_create_milestone_notification创建Notification记录，destination_route为`/achievements/milestone/{id}`，deep_link为`sparkle://milestone/{id}`，mobile端deep_link_service和achievement_routes都有对应路由定义
- **认知碎片记录**: _handle_achievement_unlocked正确调用cognitive_service.create_fragment，成就解锁产生认知系统输入
- **社区广播**: _handle_achievement_unlocked通过CommunitySignalBridge.broadcast_achievement_unlock分享到社区（尊重share_achievements_to_community偏好）
- **Profile信号刷新**: _refresh_achievement_profile_signals分析30天内成就数据，写入推断偏好（peak_hours, pace_style, motivation_response, reward_sensitivity）
- **Session completion幂等**: _reserve_session_completion使用PostgreSQL INSERT ON CONFLICT DO NOTHING防止重复触发
- **After-commit回调**: 解锁后的副作用(缓存清除、EventBus广播、叙事记录)通过SQLAlchemy after_commit hook异步执行，不阻塞主事务

## Files Examined
- backend/app/services/achievement_engine.py
- backend/app/services/achievement_event_consumer.py
- backend/app/core/event_bus.py
- backend/app/consumers/achievement_plan_consumer.py
- backend/app/services/focus_service.py (lines 110-160)
- backend/app/api/v1/tasks.py (line 882)
- backend/app/api/v1/plans.py (lines 1225-1255)
- backend/app/services/galaxy/stats_service.py (lines 165-190)
- backend/app/services/galaxy_service.py (line 1717)
- backend/app/services/exam_sprint_review_service.py (lines 980-1005)
- mobile/lib/features/achievement/presentation/providers/achievement_provider.dart (lines 245-285)
- mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart (lines 875-905)
- mobile/lib/core/navigation/shell_navigation.dart (lines 138-170)
- mobile/lib/features/chat/presentation/providers/chat_notifier_actions.dart (lines 590-615)
- mobile/lib/core/services/push_navigation_service.dart (full)
- mobile/lib/core/services/deep_link_service.dart (full)
- mobile/lib/features/achievement/achievement_routes.dart (full)

## Confidence: High — traced every AchievementEvent type from definition through trigger to consumer, verified EventBus publish/subscribe alignment, verified mobile WebSocket handling and route configuration.
