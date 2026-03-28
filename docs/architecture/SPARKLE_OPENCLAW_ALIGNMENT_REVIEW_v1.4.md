# Sparkle × OpenClaw 对齐审查文档 v1.4

> 日期：2026-03-28
> 状态：Phase 4 / Phase 5 再次深耕；本地连接闭环、离线排队、配对会话、聊天富结果、结果对比与自验证已落地，远程 relay 基础设施仍不在本轮实现范围内

## 1. 本轮新增完成面

### Phase 4：连接架构

- `mobile/lib/core/services/openclaw_connection_service.dart`
  - 新增离线等待队列持久化
  - 新增 6 位配对码会话模型与过期控制
  - 新增设备配对完成/取消接口
  - 新增排队任务移除/清空能力
- `mobile/lib/features/settings/presentation/screens/openclaw_settings_screen.dart`
  - 设置页接入配对码生成、完成配对、取消配对
  - 新增离线等待队列卡片
  - 支持队列重试、清空队列
  - 保存连接成功后自动尝试重提排队任务
- `mobile/lib/features/task/presentation/providers/task_provider.dart`
  - AI 执行发起前读取连接状态
  - 引擎已配置但离线时，不再直接失败，而是加入等待队列
  - 新增 `drainQueuedAiHandoffs()`，连接恢复后可批量重新提交
- `mobile/lib/features/task/presentation/screens/task_execution_screen.dart`
  - “交给 AI 执行”按钮已受连接状态约束
  - 未连接时显示连接提示卡并跳转设置
  - 已配置但离线时支持“加入等待队列”
- `mobile/lib/features/chat/presentation/providers/chat_notifier_actions.dart`
  - 聊天流发起委派时支持识别“已加入等待队列”场景

### Phase 4：后端健康快照

- `backend/app/adapters/openclaw/client.py`
  - 新增 `health_snapshot()`
  - HTTP 模式返回延迟、消息、能力矩阵
  - WS 模式返回可达性与能力摘要
- `backend/app/services/execution_service.py`
  - `get_health()` 改为返回 richer snapshot
- `backend/app/api/v1/executions.py`
  - `GET /executions/connection/status` 补充 `latency_ms / message / capabilities`

### Phase 5：结果富展示、执行回放、结果对比、结果自验证

- `backend/app/services/execution_result_validator.py`
  - `build_comparison_summary()` 新增：
    - `changed_fields`
    - `highlights`
    - `current_preview`
    - `previous_preview`
  - 新增 `build_self_verification()`
    - 输出 `score / verdict / summary / checklist / recommendations`
- `backend/app/orchestration/validation_engine.py`
  - 聊天侧 `execution_validation` 注入 `self_verification`
- `backend/app/api/v1/executions.py`
  - 执行记录响应新增 `self_verification`
  - 修复 `tool_calls_count` 未透传问题
- `mobile/lib/features/task/data/models/execution_record_model.dart`
  - 增加 `selfVerification`
- `mobile/lib/features/task/presentation/widgets/execution_result_renderer.dart`
  - 图片附件支持全屏预览
  - 其他附件支持底部 sheet 预览元信息、文本片段、复制链接
- `mobile/lib/features/task/presentation/widgets/execution_approval_card.dart`
  - 审批卡新增字段变化视图
  - 新增自验证摘要与 checklist
  - 对比摘要支持 highlights + changed fields
- `mobile/lib/features/chat/presentation/providers/chat_provider.dart`
  - 聊天执行摘要透传 `self_verification`
- `mobile/lib/features/chat/presentation/widgets/action_card.dart`
  - 聊天内联结果卡新增自验证评分、摘要、checklist
  - 对比摘要支持 highlights

## 2. 当前 Phase 4 / 5 的实际完成判断

### Phase 4 已完成的部分

- 本地连接配置
- 连接测试
- 周期健康检查
- 连接状态感知影响执行按钮
- 离线任务入队
- 连接恢复后批量重试
- 设备配对码会话与手动完成配对

### Phase 5 已完成的部分

- 结果内容路由渲染
- 聊天内联富结果
- 审批卡富结果
- 执行回放摘要
- 结果对比摘要与字段变化
- 规则化结果自验证
- artifact 预览
- classify cache 与模板 prompt 优化

## 3. 仍未完成的边界

下面这些不是“没 polish”，而是不同量级的基础设施，因此我不会把它们伪装成已完成：

- Phase 4
  - mDNS / Bonjour 自动发现
  - 真正的二维码绑定链路
  - Sparkle Server 级 relay / NAT 穿透
  - OpenClaw 离线后服务端排队与上线自动执行
  - 跨设备端到端安全通道
- Phase 5
  - PDF/文档前三页真实内容预览
  - step-log 级完整执行回放
  - 同任务多次执行的并排 diff 视图
  - 基于独立 LLM prompt 的结果自检与返工闭环
  - 分级模型策略与成本透明 UI

## 4. 验证结果

### 后端

已通过：

```bash
backend/venv/bin/pytest \
  backend/tests/unit/test_openclaw_phase1.py \
  backend/tests/unit/test_openclaw_phase2.py \
  backend/tests/unit/test_openclaw_phase4.py \
  backend/tests/unit/test_openclaw_admin_api.py -q
```

结果：`28 passed`

已通过：

```bash
python3 -m py_compile \
  backend/app/adapters/openclaw/client.py \
  backend/app/api/v1/executions.py \
  backend/app/orchestration/validation_engine.py \
  backend/app/services/execution_result_validator.py \
  backend/app/services/execution_service.py
```

### Flutter

已通过：

```bash
dart analyze \
  mobile/lib/core/services/openclaw_connection_service.dart \
  mobile/lib/features/settings/presentation/screens/openclaw_settings_screen.dart \
  mobile/lib/features/task/presentation/providers/task_provider.dart \
  mobile/lib/features/task/presentation/screens/task_execution_screen.dart \
  mobile/lib/features/task/presentation/widgets/execution_result_renderer.dart \
  mobile/lib/features/task/presentation/widgets/execution_approval_card.dart \
  mobile/lib/features/chat/presentation/providers/chat_provider.dart \
  mobile/lib/features/chat/presentation/providers/chat_notifier_actions.dart \
  mobile/lib/features/chat/presentation/widgets/action_card.dart \
  mobile/lib/features/task/data/models/execution_record_model.dart
```

结果：无 error，剩余为历史文件上的 info 级 lint。

## 5. 结论

如果以“产品能力是否闭环”为标准，这一轮已经把 Phase 4 的本地连接闭环和 Phase 5 的富结果工作台推进到了可以验收的程度。

如果以“最初商业级远程架构蓝图是否全部建完”为标准，答案仍然是否定的：真正的远程桥接与服务端排队层没有在本轮实现。我选择把这个边界写清楚，而不是把“本地闭环 + 深水区前置骨架”包装成“全部收官”。
