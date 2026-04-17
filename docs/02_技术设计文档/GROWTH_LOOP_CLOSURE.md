# Phase 4 Growth Loop 闭合确认表

## Growth Loop 七环

| 环节 | 核心组件 | 输出 | 下一环输入 |
| --- | --- | --- | --- |
| Sense | `ContextOrchestrator`, `SystemUpdateService`, `ProgressNarrativeService` | 用户画像、偏好、计划约束、群组状态、知识掌握、进步快照 | `SufficiencyChecker`, `GoalQualityEvaluator`, `DualCoreRouter` |
| Clarify | `SufficiencyChecker`, `GoalQualityEvaluator`, `DualCoreRouter` | 信息充分性、目标质量评分、双核心路由决定 | `LangGraphPlanner`, `standard_workflow`, `multi_agent_adapter` |
| Plan | `LangGraphPlanner`, `GroundingValidator` | `ExecutablePlan`、知识未就绪 warning、planning constraints | `ToolExecutor`, 任务创建链路 |
| Execute | `ToolExecutor`, `TaskService`, `CommunitySignalBridge` | 任务执行结果、群组完成事件、知识节点更新 | `TaskFeedbackService`, `BehaviorSignalCollector`, `AchievementEventConsumer` |
| Reflect | `TaskFeedbackService`, `TaskReflectionService`, `BehaviorSignalCollector`, `CognitiveService` | 结构化反馈、反思答案、认知碎片、行为模式更新 | `AdaptiveReplanner`, `CognitivePatternTrigger` |
| Reinforce | `AchievementEngine`, `ProgressNarrativeService`, `SystemUpdateService` | 成就解锁、进步快照、成长回顾高亮 | `UXEnvelopeBuilder`, Flutter growth cards |
| Adapt | `AdaptiveReplanner`, `MemoryService`, `UXEnvelopeBuilder` | 计划约束更新、偏好学习、`AdaptationRecord`、`ux_evolution` | 下一轮 `ContextOrchestrator` 读取的事实与约束 |

## 事件总线审计

| 事件 | 发布者 | 消费者 | 状态 |
| --- | --- | --- | --- |
| `task.completed` | `TaskService` | `TaskEventConsumer`, `AchievementEventConsumer`, `galaxy.event_listener` | 已闭合 |
| `task.abandoned` | `TaskService` | `TaskEventConsumer`, `galaxy.event_listener` | 已闭合 |
| `task.feedback_submitted` | `TaskFeedbackService` | `TaskEventConsumer` | 已闭合 |
| `galaxy.node.updated` | `GalaxyService`, `CommunitySignalBridge` | `GalaxyEventConsumer`, `AchievementEventConsumer` | 已闭合 |
| `achievement.unlocked` | `AchievementEngine` | `SystemUpdateService` / WebSocket 前端提示 | 已闭合 |
| `community.group_task_completed` | `CommunitySignalBridge` | `AchievementEventConsumer` | 已闭合 |
| `behavior.pattern.updated` | `CognitiveService` | `TaskEventConsumer -> BehaviorSignalCollector -> AdaptiveReplanner` | 已闭合 |
| `plan.replanned` | `PlanReviewService`, `AdaptiveReplanner` | `TaskEventConsumer -> BehaviorSignalCollector` | 已闭合 |

## Adapt -> Sense 回流确认

1. `AdaptiveReplanner` 更新 `PlanState.constraints` 和 `facts.adaptive_meta`
2. `MemoryService` 写入偏好学习并通过 `SystemUpdateService` 广播
3. `ChatOrchestrator._hydrate_evolution_context()` 把 adaptation / preference / progress snapshot 注入 `final_state.context_data`
4. 下一轮 `ContextOrchestrator.get_user_context()` 读取：
   - 偏好版本与偏好配置
   - 计划约束
   - 群组状态
   - 知识状态
5. `DualCoreRouter` 和 `LangGraphPlanner` 因此获得已经调整后的上下文

## 场景走查结论

- 高目标学生冲刺：闭合
- 学习受阻调整：闭合
- 群组冲刺协作：闭合
- 长期使用后系统变懂用户：闭合
