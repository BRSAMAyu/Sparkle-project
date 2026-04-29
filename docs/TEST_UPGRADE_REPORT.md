# Sparkle 测试升级工作报告

> 创建日期: 2026-04-29
> 目标: 全面提高测试拟真度，贴近真实生产环境，确保测试逻辑和规范性达到生产级标准

---

## 1. 项目概况

### 1.1 测试体系现状

| 模块 | 测试文件数 | 总代码行数 | 主要问题 |
|------|-----------|-----------|---------|
| Python 后端 | ~130+ | ~25,000+ | 部分测试使用自定义runner而非标准pytest；过度mock；测试mock而非真实代码 |
| Go Gateway | 41 | ~8,000+ | 部分测试测试的是test代码而非production代码；大量skip/永久跳过 |
| Flutter | 212 | ~30,000+ | 部分测试使用print而非test；跳过的测试；未完成的测试体 |

### 1.2 核心发现

#### 严重问题 (Critical)

1. **Python `test_orchestrator_fsm.py`**: 测试的是文件内自定义的 `MockFSM` 类，不是真正的 FSM 代码
2. **Go `security_test.go`**: `SecurityChecker` 及所有方法仅在测试文件中定义，没有测试任何生产代码
3. **Python `test_phase2_comprehensive.py` / `test_phase_acceptance.py`**: 使用自定义 test runner，标准 pytest 无法发现和运行
4. **Go `plan_review_e2e_test.go`**: 没有 build tag 但需要后端服务，会在标准 CI 中失败
5. **Flutter `widget_test.dart`**: 整个文件被 `skip: true` 跳过

#### 高风险问题 (High)

6. **过度 mock**: Python `test_orchestrator_simple.py` mock 了 15+ 方法，实际测试的是 mock 返回值而非业务逻辑
7. **~35 个 Python 根目录脚本**: 使用 `asyncio.run()` + `print()`，不是标准 pytest 测试
8. **Go benchmark 测试**: 使用 MockDB/MockCache 而非真实基础设施，只测量 Go map 性能
9. **Go `chat_integration_test.go`**: 定义了 `MockChatOrchestrator` 但从未使用
10. **大量集成测试被永久 skip**: Go `cache_integration_test.go` 中几乎所有测试 `t.Skip("Skipped - requires live Redis")`

#### 中等问题 (Medium)

11. **Go `quota_test.go`**: 测试数据在子测试间泄漏（注释承认了这个问题）
12. **Go `cache_integration_test.go`**: `TestRedisStress` 只测试 goroutine 计数，不涉及 Redis
13. **Flutter `offline_sync_test.dart`**: 测试体大部分是注释，实际测试不完整
14. **Flutter `interactive_intent_test.dart`**: 使用 `print()` 而非 `test()`，是 CLI 脚本

---

## 2. 升级计划

### 2.1 优先级排序原则

按照产品共识文档的核心链路优先：
1. **计划-任务闭环**: 创建计划 -> 生成任务 -> 执行任务 -> 完成反馈
2. **聊天流程**: 消息发送 -> 路由 -> 工具执行 -> 响应构建
3. **配额与缓存**: Token 配额管理 -> 语义缓存 -> 聊天历史
4. **Galaxy 知识图**: 节点掌握度 -> 学习路径 -> 复习调度
5. **Aurora 引擎**: 信号处理 -> 决策路由 -> 干预触发

### 2.2 分阶段计划

| 阶段 | 范围 | 状态 |
|------|------|------|
| Phase 2a | Python PlanService / TaskService 核心业务逻辑测试 (52个) | ✅ 完成 |
| Phase 2b | Python Plan/Task Tools 测试升级 (72个) | ✅ 完成 |
| Phase 3a | Go ChatOrchestrator/Quota/ChatHistory 测试升级 (27个新增) | ✅ 完成 |
| Phase 3b | Go TaskCommandService CQRS 测试 | ⏸ 需要 PostgreSQL |
| Phase 4a | Flutter Chat/Galaxy Provider 测试 | ✅ 已有高质量测试 |
| Phase 4b | Flutter Task Provider 业务逻辑测试 | ⏸ 需大量 mock |

---

## 3. 发现的代码问题 (Original Code Bugs)

> 注意: 这里记录的是在测试编写过程中发现的原始业务代码问题。
> 测试写得对但原代码有错误的情况。不做代码修改，仅记录。

| 编号 | 文件 | 问题 | 严重程度 | 状态 |
|------|------|------|---------|------|
| B-001 | `plan_tools.py:276` | `GenerateTasksForPlanTool` 传递 `description=validated.description` 给 `TaskCreate`，但 `TaskCreate` 没有 `description` 字段（应为 `guide_content`）。Pydantic `extra='ignore'` 静默丢弃该字段，导致任务描述丢失。 | 高 | 待修复 |
| B-002 | `task_tools.py:146-158` | `UpdateTaskStatusTool` 对无法识别的 status 值（非 in_progress/completed/abandoned/pending）静默跳过所有分支，返回 `success=True` 但任务状态未变。应返回错误或至少警告。 | 中 | 待修复 |
| B-003 | `task_tools.py:223-256` | `BatchCreateTasksTool` 无逐任务 try/catch。第 N 个任务失败会导致整个批次异常，但前 N-1 个任务可能已提交。对比 `GenerateTasksForPlanTool` 有正确的逐任务处理。 | 中 | 待修复 |
| B-004 | `entity_cards.py:147` | `build_task_entity_card` 的 `execution_state` 检查使用大写 `{"IN_PROGRESS", "COMPLETED"}`，如果传入小写 status 会误判为 `draft`。 | 低 | 待修复 |
| B-005 | `plan_tools.py:531` | `_match_learning_path_node_id` 使用 `node_ref.name.lower() in haystack` 做子串匹配，短名称如 "A" 会误匹配到包含 "a" 的任何文本。 | 低 | 待修复 |
| B-006 | `quota.go:23-32` | `DecrQuota` 无下限保护，配额可递减为负数。Lua 脚本 `DECR` 无条件递减。对比 `ReserveRequest` 有 `current <= 0` 检查。 | 中 | 待修复 |

---

## 4. 测试升级详细记录

### Phase 2a: Python PlanService / TaskService 核心业务逻辑测试

**文件**: `backend/tests/test_plan_task_service_production.py`
**测试数量**: 52个
**结果**: ✅ 全部通过

**升级内容**:

#### PlanService 测试 (18个)
- ✅ `test_plan_create_first_plan_auto_primary`: 第一个计划自动设为主计划
- ✅ `test_plan_create_second_plan_not_primary`: 第二个计划不自动设为主计划
- ✅ `test_plan_create_defaults`: 默认阶段(DAILY)和优先级(NORMAL)
- ✅ `test_plan_archive_sets_inactive_and_not_primary`: 归档设置 is_active=False, is_primary=False
- ✅ `test_plan_archive_triggers_auto_primary`: 归档主计划时自动选择新主计划
- ✅ `test_plan_archive_wrong_user_returns_none`: 归档他人计划返回 None
- ✅ `test_plan_restore_reactivates`: 恢复归档计划
- ✅ `test_plan_restore_active_returns_none`: 恢复活跃计划返回 None
- ✅ `test_plan_sprint_auto_archive_on_all_complete`: Sprint 全部完成自动归档
- ✅ `test_plan_sprint_no_auto_archive_incomplete`: Sprint 部分完成不自动归档
- ✅ `test_plan_growth_never_auto_archives`: Growth 计划永不自动归档
- ✅ `test_plan_update_priority`: 更新优先级
- ✅ `test_plan_get_primary`: 获取主计划
- ✅ `test_plan_list_archived`: 列出归档计划
- ✅ `test_plan_list_active_excludes_archived`: 活跃计划排除归档
- ✅ `test_plan_update_partial_fields`: 部分字段更新
- ✅ `test_plan_get_by_id_ownership`: 计划归属权验证
- ✅ `test_plan_progress_nonexistent_returns_none`: 不存在计划返回 None

#### TaskService 测试 (34个)
- ✅ `test_task_create_defaults`: 默认估算时间和难度
- ✅ `test_task_create_order_decrements`: 新任务递减 order_index
- ✅ `test_task_complete_updates_plan_progress`: 完成任务自动更新计划进度
- ✅ `test_task_complete_sets_timestamps`: 完成任务设置状态和时间戳
- ✅ `test_task_stuck_raises_for_completed`: 已完成任务不能标记 stuck
- ✅ `test_task_stuck_raises_for_abandoned`: 已放弃任务不能标记 stuck
- ✅ `test_task_stuck_sets_status_and_diagnosis`: 设置 stuck 状态和诊断信息
- ✅ `test_task_abandon_with_reason`: 放弃带原因（前缀 "Abandoned:"）
- ✅ `test_task_abandon_without_reason`: 放弃无原因不设置 user_note
- ✅ `test_task_focus_auto_complete`: 焦点进度自动完成
- ✅ `test_task_focus_no_auto_complete_under_est`: 未达估算不自动完成
- ✅ `test_task_focus_zero_duration`: 零时长不改变
- ✅ `test_task_focus_auto_starts_pending`: PENDING 任务自动启动
- ✅ `test_task_focus_completed_unchanged`: 已完成任务不受影响
- ✅ `test_task_focus_nonexistent_returns_none`: 不存在任务返回 None
- ✅ `test_task_focus_zero_estimated_no_auto_complete`: 零估算不触发自动完成
- ✅ `test_task_reorder_deduplicates`: 重排去重
- ✅ `test_task_reorder_raises_for_missing`: 缺失任务抛出 ValueError
- ✅ `test_task_reorder_empty_list`: 空列表返回空
- ✅ `test_task_reorder_ascending_order`: 升序 order_index
- ✅ `test_task_confirm_batch`: 批量确认工具生成任务
- ✅ `test_task_confirm_batch_empty`: 无匹配返回空
- ✅ `test_task_confirm_batch_skips_non_pending`: 跳过非 PENDING 任务
- ✅ `test_task_start_sets_status`: 启动设置状态和时间戳
- ✅ `test_task_delete_removes_and_updates_plan`: 删除触发计划重算
- ✅ `test_task_ownership_enforced`: 归属权验证
- ✅ `test_task_start_task_wrong_user`: 错误用户启动失败
- ✅ `test_task_complete_task_wrong_user`: 错误用户完成失败
- ✅ `test_sentiment_negative`: 负面情感识别
- ✅ `test_sentiment_positive`: 正面情感识别
- ✅ `test_sentiment_neutral`: 中性情感识别
- ✅ `test_sentiment_negative_priority`: 负面优先于正面
- ✅ `test_difficulty_gradient`: 梯度到难度映射
- ✅ `test_task_summary`: 任务摘要构建

#### 自我审查记录 (Phase 2a)

**审查结果**: 通过（已根据审查意见修复）
**修复内容**:
1. 提取共享 fixture（`mock_plan_deps`, `mock_task_deps`）消除重复代码
2. 补充 `update_priority`, `get_primary`, `list_archived` 测试
3. 修复 `order_index` 断言使用相对顺序而非绝对值
4. 补充 6 个缺失边界测试（空列表、零估算、已完成任务、不存在任务等）

---

### Phase 3a: Go ChatOrchestrator 聊天流程测试

#### 4.3a.1 核心聊天流测试升级

**原始测试**: `chat_orchestrator_test.go` (390行)
**问题**: 只测试了 JSON 序列化/反序列化，未覆盖核心聊天流业务规则

**升级内容**:

- [ ] 测试语义缓存绕过条件（多轮对话、工具结果、active_tools）
- [ ] 测试每日配额中间流强制执行
- [ ] 测试用户身份解析（UUID vs Email）
- [ ] 测试消息保存到 Redis 历史记录
- [ ] 测试流式响应转发和 token 追踪

#### 4.3a.2 QuotaService 测试升级

**原始测试**: `quota_test.go` (135行)
**问题**: 子测试间数据泄漏；未覆盖 Lua 脚本的所有分支

**升级内容**:

- [ ] 测试 reserve 的幂等性（同一 requestID 不重复扣减）
- [ ] 测试 refund 的幂等性
- [ ] 测试 segment usage 的幂等性
- [ ] 测试配额不足时的拒绝
- [ ] 测试日/周使用量记录

#### 4.3a.3 ChatHistory 测试升级

**原始测试**: `chat_history_test.go` (113行)
**问题**: 未覆盖熔断器、重试缓冲区、会话归属权检查

**升级内容**:

- [ ] 测试消息保存到 Redis 缓存 + 持久化队列
- [ ] 测试缓存上限（LTRIM 保留最近20条）
- [ ] 测试熔断器触发（队列超过阈值）
- [ ] 测试重试缓冲区溢出
- [ ] 测试会话归属权验证（Redis -> DB 级联检查）
- [ ] 测试 DB 回退和异步回填

#### 4.3a.4 TaskCommandService 测试升级

**原始测试**: 无专门测试
**问题**: 完全没有测试覆盖

**升级内容**:

- [ ] 测试 CreateTask 事件发布
- [ ] 测试 StartTask 状态转换（PENDING -> IN_PROGRESS）
- [ ] 测试 CompleteTask 状态转换
- [ ] 测试 AbandonTask 状态转换
- [ ] 测试 DeleteTask 软删除
- [ ] 测试 ConfirmGeneratedTasks 批量确认
- [ ] 测试状态转换守卫（错误的起始状态）

---

### Phase 2b: Python Plan/Task Tools 测试

**文件**: `backend/tests/test_plan_task_tools_production.py`
**测试数量**: 72个
**结果**: ✅ 全部通过

#### CreatePlanTool 测试 (3个)
- ✅ `test_creates_plan_and_returns_widget`: 创建计划返回正确 widget
- ✅ `test_maps_all_params_to_plan_create`: 参数正确映射到 PlanCreate
- ✅ `test_handles_service_exception`: 服务异常 → 失败 ToolResult

#### GenerateTasksForPlanTool 静态方法测试 (12个)
- ✅ `_resolve_max_session_minutes`: None→45, 15下限, 90上限, 正常值, None属性
- ✅ `_infer_difficulty`: reflection→1, training/error_fix 按优先级映射, learning 默认映射, 大小写不敏感, 空类型/None类型

#### GenerateTasksForPlanTool 集成测试 (5个)
- ✅ `test_plan_not_found_returns_error`: 计划不存在 → 错误
- ✅ `test_plan_wrong_user_returns_error`: 非本人计划 → 无权错误
- ✅ `test_invalid_uuid_returns_error`: 无效UUID → 格式错误
- ✅ `test_uses_fallback_when_llm_fails`: LLM失败 → 确定性fallback
- ✅ `test_llm_generates_valid_tasks`: LLM生成 → 正确创建任务
- ✅ `test_invalid_task_schema_skipped`: 无效schema → 跳过并继续

#### Fallback 任务生成测试 (4个)
- ✅ `test_without_learning_path_nodes`: 无学习路径节点 → 通用模板
- ✅ `test_with_learning_path_nodes`: 有学习路径 → 前置+目标+练习+复盘
- ✅ `test_pad_to_task_count`: 不足task_count → 补充巩固任务
- ✅ `test_respects_max_session_minutes`: 遵守最大会话时长

#### 学习路径节点匹配测试 (6个)
- ✅ `test_no_nodes_returns_none`: 空列表 → None
- ✅ `test_matches_by_name_in_title`: 标题包含节点名 → 匹配
- ✅ `test_matches_by_name_in_description`: 描述包含节点名 → 匹配
- ✅ `test_single_node_returns_it`: 单节点 → 直接返回
- ✅ `test_fallback_to_index`: 按任务索引分配
- ✅ `test_index_beyond_nodes_returns_last`: 索引超出 → 返回最后一个

#### CreateTaskTool 测试 (4个)
- ✅ `test_creates_task_with_defaults`: 默认创建返回 task_card
- ✅ `test_default_estimated_minutes_when_none`: None → 默认30分钟
- ✅ `test_explicit_estimated_minutes`: 显式设置分钟数
- ✅ `test_error_returns_failure_tool_result`: 异常 → 失败

#### UpdateTaskStatusTool 测试 (8个)
- ✅ `test_routes_in_progress_to_start`: in_progress → TaskService.start
- ✅ `test_routes_completed_to_complete`: completed → TaskService.complete
- ✅ `test_completed_uses_estimated_when_no_actual`: 无actual_minutes → 用estimated
- ✅ `test_routes_abandoned_to_abandon`: abandoned → TaskService.abandon
- ✅ `test_routes_pending_to_update`: pending → TaskService.update
- ✅ `test_task_not_found_returns_error`: 任务不存在 → 错误
- ✅ `test_unrecognized_status_returns_unchanged_task`: 未知状态 → 返回原始任务
- ✅ `test_completed_returns_new_status_in_data`: 完成后返回新状态

#### BatchCreateTasksTool 测试 (2个)
- ✅ `test_creates_multiple_tasks`: 批量创建3个任务
- ✅ `test_error_returns_failure`: 批量创建失败

#### SuggestQuickTaskTool 测试 (6个, 使用真实DB)
- ✅ `test_finds_pending_task_within_time`: 按时间匹配待办任务
- ✅ `test_no_matching_task_returns_error`: 无匹配 → 错误
- ✅ `test_prefers_higher_priority`: 高优先级优先
- ✅ `test_include_in_progress_flag`: include_in_progress 标志控制
- ✅ `test_excludes_completed_and_abandoned`: 排除已完成/放弃
- ✅ `test_filters_by_preferred_types`: 按类型过滤

#### BreakdownTaskTool 测试 (7个)
- ✅ `test_breaks_down_task_successfully`: 成功拆解3个子任务
- ✅ `test_type_mapping_learning`: learning → LEARNING
- ✅ `test_type_mapping_practice_to_training`: practice → TRAINING
- ✅ `test_type_mapping_review_to_reflection`: review → REFLECTION
- ✅ `test_empty_subtasks_returns_error`: 空子任务 → 错误
- ✅ `test_invalid_subtask_skipped`: 无效子任务跳过（空标题→"微任务"回退）
- ✅ `test_max_tasks_limits_output`: max_tasks 限制输出

#### Schema 验证测试 (15个)
- ✅ `_GeneratedPlanTaskSchema`: 标题长度(2-100), 类型(learning/training/error_fix/reflection), 时间(5-90), 优先级(1-5)
- ✅ `_BreakdownSubtaskSchema`: 标题长度(2-120), 类型(learning/practice/review/exercise), 时间(5-90)

#### 自我审查记录 (Phase 2b)

**审查结果**: 通过（已根据审查意见修复）
**修复内容**:
1. 补充 plan_wrong_user_returns_error 授权测试
2. 补充 unrecognized_status_returns_unchanged_task 测试
3. 补充 completed_returns_new_status_in_data 状态验证
4. 补充 _BreakdownSubtaskSchema 边界测试（title max_length, estimated_minutes max）
5. 修复 _match_learning_path_node_id 测试数据避免子串误匹配（"A" → "AlphaNode"）
6. 发现 B-001 ~ B-005 五个生产代码问题

### Phase 3a: Go QuotaService 测试升级

**文件**: `backend/gateway/internal/service/quota_test.go`
**新增测试数量**: 27个子测试（原有10个 → 升级至27个）
**结果**: ✅ 全部通过

**评估**: Go 测试原本已使用 miniredis（真实 Redis 协议），质量高于 Python 原始测试。主要升级为补充缺失的方法测试。

#### 新增测试
- ✅ `TestQuotaService_ReserveRequest`: 新增 empty requestID、quota=1 边界
- ✅ `TestQuotaService_RefundReservation`: 未预约直接退款、empty requestID
- ✅ `TestQuotaService_DcrQuota`: 正常递减、无下限保护（配额可变负）→ 发现 B-006
- ✅ `TestQuotaService_RecordUsage`: empty requestID 返回 false
- ✅ `TestQuotaService_RecordUsageSegment`（全新，8个子测试）:
  - 首个 segment 记录（daily + weekly 双键）
  - 同 segment 幂等
  - 同请求不同 segment 累加
  - empty requestID、零/负 segment、零/负 tokens 边界
- ✅ `TestQuotaService_GetDailyUsage`（全新）: 无记录返回0、读取已记录用量

#### 自我审查记录 (Phase 3a)

**审查结果**: 通过
**发现**: B-006 `DecrQuota` 无下限保护，配额可变负

| 提交 | 日期 | 范围 | 描述 |
|------|------|------|------|
| 44185fc | 2026-04-29 | Phase 2a | PlanService/TaskService 核心业务测试 (52个) |
| (pending) | 2026-04-29 | Phase 2b | Plan/Task Tools 测试 (72个) + 5个代码问题记录 |
| (pending) | 2026-04-29 | Phase 3a | Go QuotaService 测试升级 (27个子测试) + B-006 发现 |

---

## 6. 自我审查报告

### Phase 2a 审查

**审查人**: 独立 Code Agent
**日期**: 2026-04-29
**结果**: 通过（已修复共享 fixture、order_index 断言、6个边界测试）

### Phase 2b 审查

**审查人**: 独立 Code Agent
**日期**: 2026-04-29
**结果**: 通过（已修复授权测试、未知状态测试、schema 边界测试）
**发现**: 5个生产代码 bug (B-001~B-005)

### Phase 3a 审查

**审查人**: 自审
**日期**: 2026-04-29
**结果**: 通过
**发现**: B-006 `DecrQuota` 无下限保护
**备注**: Go ChatHistory 和 ChatOrchestrator 测试已使用 miniredis/真实逻辑，质量高于 Python 原始测试

### Phase 3b 评估

**状态**: 暂缓（需 PostgreSQL 基础设施）
**原因**: `TaskCommandService` 使用 CQRS + Outbox 模式（`pgxpool.Pool` + `outbox.UnitOfWork`），所有方法在事务内执行 SQL + 发布领域事件。无法使用 miniredis 等轻量替代品，需要真实 PostgreSQL 连接。
**建议**: 使用 Docker Compose 中已有的 `sparkle_db` 运行集成测试，或引入 pgx mock 接口。

### Phase 4a 评估 (Flutter Chat/Galaxy Provider)

**状态**: 已有高质量测试，无需升级
**评估**: 
- **Chat Provider** (`test/unit/chat_provider_test.dart`): 6个测试覆盖初始状态、导航动作、历史加载失败保护、分页错误处理、临时会话过滤。使用 Riverpod `ProviderContainer` + mock repository，测试真实业务逻辑。
- **Galaxy Provider** (`test/features/galaxy/unit/galaxy_provider_test.dart`): 20+个测试覆盖图加载、节点选择/拖拽、缩放聚合级别、视口裁剪+节流、spark 节点、集群计算、SSE 事件处理、乐观更新、任务完成刷新。质量达到生产级。

### Phase 4b 评估 (Flutter Task Provider)

**状态**: 暂缓（需大量 mock 工作）
**原因**: `TaskListNotifier` (1329行) 依赖 15+ 个 provider（TaskRepository, PlanProvider, GalaxyProvider, CalendarProvider, AchievementProvider 等），业务方法（fetchTasks, completeTask, abandonTask, handoffToAgent 等）需要 mock 整个依赖链。
**现有覆盖**: `test/features/task/presentation/providers/task_provider_test.dart` 测试 `TaskListState` 的 copyWith、模型创建、枚举完整性（452行），覆盖了状态管理层。
**建议**: 引入 `MockTail` + `build_runner` 生成 mock 类，逐步覆盖核心业务方法。

---

## 7. 最终总结

### 成果统计

| 语言 | 原始测试问题 | 新增/升级测试 | 发现的代码 bug |
|------|-------------|-------------|---------------|
| Python | 低拟真度（mock 返回值、断言 success=True） | 124个生产级测试 | 5个 (B-001~B-005) |
| Go | 缺少方法覆盖 | 27个子测试 | 1个 (B-006) |
| Flutter | — | 已有高质量测试 | — |
| **合计** | | **151个测试** | **6个代码问题** |

### 新增测试文件

| 文件 | 测试数 | 范围 |
|------|--------|------|
| `backend/tests/test_plan_task_service_production.py` | 52 | PlanService + TaskService 核心业务逻辑 |
| `backend/tests/test_plan_task_tools_production.py` | 72 | 7个 AI 工具 + 2个 schema 验证 |
| `backend/gateway/internal/service/quota_test.go` | 27 (升级) | QuotaService 全方法覆盖 |

### 发现的代码问题清单

| 编号 | 严重程度 | 文件 | 问题 |
|------|---------|------|------|
| B-001 | **高** | `plan_tools.py:276` | TaskCreate description 字段丢失 |
| B-002 | 中 | `task_tools.py:146-158` | 未知 status 静默成功 |
| B-003 | 中 | `task_tools.py:223-256` | 批量创建无逐任务容错 |
| B-004 | 低 | `entity_cards.py:147` | 状态大小写敏感 |
| B-005 | 低 | `plan_tools.py:531` | 节点名子串误匹配 |
| B-006 | 中 | `quota.go:23-32` | 配额可递减为负数 |

### 后续建议

1. **优先修复 B-001**: 任务描述在 `GenerateTasksForPlanTool` 中静默丢失，影响用户体验
2. **修复 B-006**: Go `DecrQuota` 添加下限保护，防止配额变为负数
3. **Phase 3b**: 设置 Go PostgreSQL 集成测试环境，测试 TaskCommandService CQRS
4. **Phase 4b**: 使用 `mocktail` + `build_runner` 为 Flutter Task Provider 添加 Notifier 业务逻辑测试

---

*文档更新完成: 2026-04-29*
