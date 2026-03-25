# J1 First Chat -> Task 关单快照

更新时间：2026-03-25
状态：`PASS`

## 目标旅程

`J1 First Chat -> Task`

路径：

1. 打开 AI 对话页
2. 发送消息
3. AI 流式响应
4. AI 生成任务
5. 任务进入任务系统
6. 打开任务详情
7. 查看任务指南

## 已拿到的证据

### 1. 模拟器与 App 可启动

- 当前模拟器截图：
  - [j1_current_2026-03-25.png](/Users/brsama/code/GitHub/Sparkle-project/tmp/acceptance/j1_current_2026-03-25.png)

### 2. 标准多轮对话、历史与 omnibar

- Acceptance 脚本：
  - `backend/scripts/ai_chat_multiturn_acceptance.py`
- 最新结果：
  - `ALL_OK`
- 关键字段：
  - `standard_turn_1_seconds = 4.987`
  - `standard_turn_2_seconds = 5.027`
  - `history_count = 6`
  - `omnibar_action_type = TASK`

结论：

- 标准对话可跑通
- 历史会话可写入并可回读
- `omnibar -> TASK` 可用

### 3. Study Plan 在计划额度已满时仍能落地任务

- 修复文件：
  - [plan_tools.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/tools/plan_tools.py)
- 修复内容：
  - 当 `create_plan` 命中计划额度上限时，不再直接失败
  - 改为进入 `task_only` fallback
  - 直接生成任务卡，并返回可打开 `/tasks/<id>` 的实体卡

结论：

- J1 不再被“计划数量上限 3 个”卡死

### 4. 任务详情与任务指南

- 已通过 API 验证：
  - 生成任务后可打开任务详情
  - `POST /api/v1/tasks/<task_id>/generate-guide` 返回成功
  - 再次读取任务详情后，`guide_content` 已存在

结论：

- `Task -> Detail -> Guide` 主链可用

### 5. 回复反馈链

- 已通过 WebSocket live 验证：
  - 先发标准问题获取 `response_id`
  - 再单独建立反馈连接发送 `response_feedback`
  - 收到：
    - `type = response_feedback_ack`
    - `status = ok`

结论：

- `S0-CHAT-03` 的后端实时反馈链可用

补充单测：

- `mobile/test/unit/websocket_chat_service_v2_test.dart`
  - `Sends response feedback payload`
  - `Parses response_feedback_ack into ActionStatusEvent`
- 最新结果：`All tests passed`

## 附件链闭环结果

### 6. 文件上传、处理、检索与接地回答

本轮把 `upload -> processed -> retrieval -> grounded answer` 跑通了。

修复文件：

- [celery_app.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/core/celery_app.py)
- [document_service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/document_service.py)
- [ingestion_service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/core/ingestion/ingestion_service.py)
- [retrieval_service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/galaxy/retrieval_service.py)
- [standard_workflow.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/agents/standard_workflow.py)
- [agent_grpc_service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/agent_grpc_service.py)

关键修复内容：

1. `.txt/.md` 文件进入文本提取，不再被当成不可处理类型
2. 显式 `file_ids` 在向量阈值未命中时，会走文件范围回退检索
3. 标准对话携带附件时，不再误走 slim context 清空文件上下文
4. 文档结果装配兼容 `page_numbers`，不再因字段名错误把 `document_context` 清空

真实闭环证据：

- 文件 `93b7b24a-d5d3-4aaf-b13c-4cf63091aa78`
  - 状态轨迹：`uploaded -> processed`
  - 对“二分查找”问题的回答已命中文件内知识点
- 唯一文本探针：
  - `session = j1-attach-1774373382`
  - `file_id = fa787bda-8017-450d-9d38-36a5431126fb`
  - 上传内容中的唯一字符串：
    - `cobalt-tulip-731`
    - `amber-mint`
  - 最终回答命中两者
- Agent 日志证据：
  - `Retrieval node assembled 1 document results`
  - `Generation node file grounding ... document_context_chars=251`

## 当前判断

- J1 主链当前已确认：
  - 角色归一化与历史恢复：可用
  - 标准多轮对话：可用
  - 历史恢复：可用
  - 反馈回执：可用
  - 附件上传与接地回答：可用
  - 编辑任务页真实可编辑性：可用
  - 任务详情与任务指南前端展示：可用

### 7. 前端可见层补证结果

新增前端旅程测试：

- `mobile/test/widget/j1_frontend_closure_test.dart`
  - `chat bubble renders malformed markdown stably`
  - `task create screen stays editable on narrow edit mode`
  - `task detail renders guide markdown without exceptions`
- 最新结果：`All tests passed`

本轮前端修复：

- [sparkle_markdown.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/core/widgets/sparkle_markdown.dart)
  - 将 fenced code 从 `flutter_markdown` 主解析中拆出，改为分段渲染
  - 保留代码块复制按钮，同时消除“标题 + 列表 + code fence”触发断言的问题

结论：

- `S0-CHAT-02`：已有真实渲染样本回归
- `S0-TASK-02`：已有窄屏编辑态可编辑与无异常证据
- `S0-TASK-03`：已有任务指南前端展示与代码块渲染证据

## 结论

- `J1 First Chat -> Task` 已完成并可关闭为 `PASS`
- 对应已完成关闭的缺陷：
  - `S0-CHAT-01`
  - `S0-CHAT-02`
  - `S0-CHAT-03`
  - `S0-CHAT-04`
  - `S0-TASK-02`
  - `S0-TASK-03`
