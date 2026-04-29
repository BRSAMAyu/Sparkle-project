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
| Phase 2b | Python Plan/Task Tools 测试升级 | 待开始 |
| Phase 3a | Go ChatOrchestrator 聊天流程测试 | 待开始 |
| Phase 3b | Go QuotaService 配额管理测试 | 待开始 |
| Phase 3c | Go ChatHistory 聊天历史测试 | 待开始 |
| Phase 3d | Go TaskCommandService CQRS 测试 | 待开始 |
| Phase 4a | Flutter Chat Provider 测试 | 待开始 |
| Phase 4b | Flutter Galaxy Provider 测试 | 待开始 |

---

## 3. 发现的代码问题 (Original Code Bugs)

> 注意: 这里记录的是在测试编写过程中发现的原始业务代码问题。
> 测试写得对但原代码有错误的情况。不做代码修改，仅记录。

| 编号 | 文件 | 问题 | 严重程度 | 状态 |
|------|------|------|---------|------|
| (待发现) | | | | |

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

## 5. Git 提交记录

| 提交 | 日期 | 范围 | 描述 |
|------|------|------|------|
| (待提交) | | | |

---

## 6. 自我审查报告

### Phase 2a 审查

**审查人**: 独立 Code Agent
**日期**: (待审查)
**结果**: (待审查)

### Phase 3a 审查

**审查人**: 独立 Code Agent
**日期**: (待审查)
**结果**: (待审查)

---

*文档持续更新中...*
