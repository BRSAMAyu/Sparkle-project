# Technical Debt Register

日期：2026-03-22

本文件用于替代代码内散落的 `TODO/FIXME`。  
代码中出现的 `TRACKED(TD-xxx)` 均以此为准。

## TD-001 Chat Transport Reliability
- 范围：`websocket_chat_service_v2.dart`
- 内容：待发队列上限、重连期间待发清理、A10 辅助逻辑的最终收口
- 退出条件：待发队列具备容量控制与可观测状态，重连与清理策略统一

## TD-002 Mobile Navigation Follow-Ups
- 范围：通知跳转、学习路径进度跳转、任务详情编辑回流、种子库编辑
- 内容：部分页面仍缺少深链跳转或目标页
- 退出条件：相关按钮全部可导航到真实目标页

## TD-003 Notification And Task Monitor Integration
- 范围：`notification_service.dart`, `task_monitor_screen.dart`, `unified_notification_card.dart`
- 内容：通知 snooze/dismiss API、任务监控刷新/重试链路待接真实后端
- 退出条件：通知控制和任务监控动作完成真实 API 闭环

## TD-004 Focus Context Enrichment
- 范围：`context_service.dart`, `mindfulness_provider.dart`, `focus_mode_provider.dart`
- 内容：语言/领域推断、实际用户 ID 注入、专注状态同步到后端、奖励反馈增强
- 退出条件：上下文推断和状态同步改为真实数据源

## TD-005 Error Book And Cognitive Flow Completion
- 范围：`error_detail_screen.dart`, `error_list_screen.dart`, `capsule_jobs_screen.dart`
- 内容：部分认知/错题导航、重试、编辑、复习页跳转尚未闭环
- 退出条件：错题和胶囊深链动作全部可达

## TD-006 Backend Job And Notification Integration
- 范围：后台任务、日历提醒、群组合并通知、购买成功通知、聊天动作执行
- 内容：部分异步任务和通知仍是保守占位逻辑
- 退出条件：相关后台任务与通知通道全部走真实生产链

## TD-007 Backend Storage And Subscription Gaps
- 范围：MinIO 级联删除、术语表持久化、资源分页 count、订阅配额、资产统计
- 内容：部分存储和订阅能力仍是最小实现
- 退出条件：对象存储、分页统计与订阅配额全部用真实实现替代

## TD-008 Backend Modeling And Analytics Enhancements
- 范围：建议服务、特征提取、统计、记忆限流、grounding validator、conflict resolver
- 内容：部分分析逻辑仍为启发式或保守默认值
- 退出条件：相关逻辑接入真实分析/统计来源

## TD-009 Gateway Protocol Hardening
- 范围：`chat_orchestrator_feedback.go`, `chat_orchestrator_protocol.go`, `chat_orchestrator_responder.go`
- 内容：DB 状态回写、Trace 映射、错误 proto 统一
- 退出条件：协议和追踪上下文完全对齐

## TD-010 Design System And Asset Generation
- 范围：`sparkle_theme_extension.dart`, `achievement_card_generator.dart`, `local_vocabulary_repository.dart`
- 内容：统一圆角/动效 token、实际卡片图片生成、局部仓储实现收口
- 退出条件：设计 token 与生成逻辑全部切到正式实现

## TD-011 DPO/SGW v2 Research Module Disconnected
- 范围：`scripts/sgw_v2/` (42 files), `backend/app/signals/policy_engine.py`
- 内容：DPO policy (`DPOPolicy.select_strategy()`) 是完整的 RL/DPO 实现但零生产接线。`orchestrator.py` 和 `policy_engine.py` 不导入任何 `sgw_v2` 模块。DPO 目前是自洽研究子系统，不参与用户实时对话。
- 影响：无法将 RL 学习到的策略应用到实时对话路由。策略选择完全基于规则表。
- 退出条件：
  1. `policy_engine.py` 导入并调用 `DPOPolicy.select_strategy()` 作为策略候选之一
  2. 通过 kill switch (`aurora:stageN:dpo_mode`) 控制 off→shadow→live
  3. DPO 策略推荐写入 `routing_decision_log` 以供审计
  4. 至少一个端到端测试验证 DPO 策略路径
- 优先级：P2（非上线阻碍，但应在 Era 2 Intelligence Phase 接入）
