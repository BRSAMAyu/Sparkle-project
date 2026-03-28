# Sparkle × OpenClaw 对齐审查文档 v1.1

> 日期：2026-03-28
> 状态：本轮为增量交付，已形成可回归闭环；未达到 6 个 Phase 全量完工

## 1. 本轮实际交付范围

### Phase 1 已落地

- `mobile/lib/features/task/presentation/widgets/execution_status_indicator.dart`
  - 新增执行状态指示器，覆盖 `DISPATCHED / RUNNING / WAITING_APPROVAL / terminal`
  - 使用独立动画态，切换走 `AnimatedSwitcher`
- `mobile/lib/features/task/presentation/widgets/execution_approval_card.dart`
  - 新增审批预览卡
  - 展示结构化 `parsed_output`、artifact 摘要、工具调用次数、执行时长、信任等级
  - 集成滑动态确认交互与感官反馈
- `mobile/lib/features/task/presentation/widgets/execution_template_card.dart`
  - 新增模板卡片化展示
  - 展示描述、匹配分、模式、环境、推荐标识
- `mobile/lib/features/task/presentation/screens/task_execution_screen.dart`
  - 接入上述 3 个新组件
  - 新增拒绝理由底部弹层 `_RejectReasonSheet`
  - 绑定 handoff / confirm / reject 的 `SensoryFeedbackService`
- `mobile/lib/features/task/data/models/execution_record_model.dart`
  - 透传 `tool_calls_count`

### Phase 2 已落地

- `backend/app/orchestration/orchestrator.py`
  - 新增 `_derive_task_context_for_execution()`
  - 新增 `_detect_execution_suggestion()`
  - 在具备明确委派语义时生成 `execution_suggestion`
- `backend/app/orchestration/response_builder.py`
  - 将 `execution_suggestion` 注入响应 metadata
- `backend/app/orchestration/ux_envelope.py`
  - 新增 `execution_delegate` 展示模式
  - 执行建议场景下切换为委派伴侣框架
- `backend/app/core/agent_profiles.py`
  - 新增 `EXECUTION_ASSISTANT`
- `mobile/lib/features/chat/presentation/providers/chat_provider.dart`
  - 将后端 `execution_suggestion` 映射为聊天流中的 `execution_suggestion` widget
  - 将 `execution_validation` 映射为内联 `execution_summary`
- `mobile/lib/features/chat/presentation/widgets/action_card.dart`
  - 新增执行建议卡样式与双按钮操作
  - 支持“交给 AI 执行 / 查看执行页”
- `mobile/lib/features/chat/presentation/providers/chat_notifier_actions.dart`
  - 支持 `handoff_task`
  - 支持 `open_task_execution`
  - 可直接从聊天流发起执行并导航到执行页

### Phase 3 已落地

- `backend/app/services/execution_learning_service.py`
  - 新增审批速度学习 `handle_approval_speed_signal()`
  - 新增任务类型委派倾向学习 `handle_task_type_delegation_tendency()`
  - 新增质量敏感度学习 `handle_quality_sensitivity()`
  - 新增拒绝情绪/安全顾虑信号 `handle_rejection_sentiment()`
- `backend/app/services/execution_ingestor.py`
  - 在 confirm / reject 路径调用上述学习信号
- `backend/app/services/profile_context_service.py`
  - 新增 `execution_type_preference`
  - 新增 `execution_quality_sensitivity`
  - 新增 `execution_safety_concern`
- `backend/app/orchestration/adaptive_replanner.py`
  - 将新 execution pattern 映射为 replanner 调整参数

### Phase 4 / 6 部分落地

- `backend/app/services/execution_profile_service.py`
  - 新增用户级执行画像聚合
  - 新增全局执行画像聚合
- `backend/app/api/v1/executions.py`
  - 新增 `GET /executions/connection/status`
  - 新增 `GET /executions/profile/summary`
- `backend/app/api/v1/executions_admin.py`
  - 新增 `GET /admin/executions/dashboard`

## 2. 验证结果

### 后端回归

已通过：

```bash
backend/venv/bin/pytest \
  backend/tests/unit/test_openclaw_phase1.py \
  backend/tests/unit/test_openclaw_phase2.py \
  backend/tests/unit/test_openclaw_phase3.py \
  backend/tests/unit/test_openclaw_phase4.py \
  backend/tests/unit/test_openclaw_admin_api.py -q
```

结果：`31 passed`

新增覆盖点：

- 执行审批速度偏好写回
- 执行质量阈值写回
- 执行画像聚合
- 用户侧 `connection/status`
- 用户侧 `profile/summary`
- 管理侧 `dashboard`

### 静态检查

已通过：

```bash
python3 -m py_compile \
  backend/app/api/v1/executions.py \
  backend/app/api/v1/executions_admin.py \
  backend/app/services/execution_profile_service.py \
  backend/app/services/execution_learning_service.py \
  backend/app/services/execution_ingestor.py \
  backend/app/services/profile_context_service.py \
  backend/app/orchestration/adaptive_replanner.py \
  backend/app/orchestration/orchestrator.py \
  backend/app/orchestration/response_builder.py \
  backend/app/orchestration/ux_envelope.py \
  backend/app/core/agent_profiles.py
```

已通过：

```bash
dart analyze \
  mobile/lib/features/chat/presentation/providers/chat_provider.dart \
  mobile/lib/features/chat/presentation/widgets/action_card.dart \
  mobile/lib/features/task/presentation/screens/task_execution_screen.dart \
  mobile/lib/features/task/presentation/widgets/execution_status_indicator.dart \
  mobile/lib/features/task/presentation/widgets/execution_approval_card.dart \
  mobile/lib/features/task/presentation/widgets/execution_template_card.dart
```

结果：无 warning / error，仅剩原文件中的 info 级 lint。

## 3. 仍未完成的范围

以下内容在本轮没有全量落地，不能按“6 个 Phase 全量完成”验收：

- Phase 2
  - 执行中 streaming milestones 回灌聊天流
  - 失败温柔处理的 error category 文案生成
  - 多 Agent 执行链路在 transparency capsule 的逐步展示
- Phase 3
  - 周期性委派洞察推送
  - cognitive prism 的完整 execution_context 片段建模
- Phase 4
  - mDNS / Bonjour 自动发现
  - 设备配对码 / QR 绑定
  - 远程 relay / NAT 穿透 / 离线队列
  - Sparkle 托管执行沙箱
- Phase 5
  - 结果类型路由器、artifact gallery、执行回放、结果对比
  - classify cache、模板 prompt 精调、结果自验证 prompt
  - 用户执行报告 UI、管理端 dashboard UI
- Phase 5.4
  - execution 文案体系的完整中英文本库
  - 无障碍语义的系统性补齐
- Phase 6
  - 指标采集落表与 A/B 实验框架接线
  - 用户旅程验证自动化

## 4. 推荐审查顺序

1. 任务执行页视觉与审批流
   - `task_execution_screen.dart`
   - `execution_status_indicator.dart`
   - `execution_approval_card.dart`
   - `execution_template_card.dart`
2. 聊天内执行建议与直达 handoff
   - `orchestrator.py`
   - `response_builder.py`
   - `ux_envelope.py`
   - `chat_provider.dart`
   - `action_card.dart`
   - `chat_notifier_actions.dart`
3. 学习闭环与可观测接口
   - `execution_learning_service.py`
   - `execution_ingestor.py`
   - `execution_profile_service.py`
   - `executions.py`
   - `executions_admin.py`

## 5. 结论

本轮已经把 Sparkle × OpenClaw 从“任务页里的独立执行子系统”推进到了“任务页原生执行体验 + 聊天内委派入口 + 执行后学习与画像回流 + 基础可观测 API”的阶段。

但如果按你最初给出的目标定义，这还不是 6 个 Phase 的完整商业级落地，更准确的验收结论应是：

> Phase 1 完成度高；Phase 2/3/4/6 完成关键骨架；Phase 5 大部分仍待实施。
