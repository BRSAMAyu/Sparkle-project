# Reviewer A — E11: 种子库→聊天集成→计划集成链路审查
Timestamp: 2026-04-26T13:30:00+08:00
Chain Index: 11

## Chain Flow Summary
种子库系统通过 `SeedLibraryService` (1878行) 提供完整CRUD、语义搜索、质量评分、few-shot示例提取。集成链路有三条：(1) **聊天集成** — context_builder → prompts → LLM，few-shot示例注入prompt；(2) **计划集成** — planning_workflow 的F19桥接，尝试用seed_library_nodes匹配sprint pack focus；(3) **质量评分** — 混合系统评分与用户评分，但仅用于UI展示。

## Critical Issues 🔴

None found — 三条集成链路均存在且部分工作。

## Major Issues 🟡

**1. `seed.created` / `seed.consumed` 事件无任何消费者 — 事件总线上的孤儿信号**
- `seed_library_service.py:456` 发布 `seed.created`，`seed_library_service.py:1057` 发布 `seed.consumed`
- 全局 grep 确认：仅有 `seed_library_service.py` 引用这两个事件类型，没有任何消费者
- `seed.created` 本应触发：新库质量预评估、官方库审核流程、知识图谱关联
- `seed.consumed` 本应触发：用户使用偏好更新、种子库推荐权重调整、行为信号采集
- 实际效果：种子库的创建和使用行为完全不会影响用户画像或AI推理

**2. 种子库→Sprint Pack桥接代码 (F19) 是死路径 — `seed_library_nodes` 永远为空**
- `planning_workflow.py:1949-1954` 读取 `session.collected.get("seed_library_nodes")`
- 此数据来自 `dashboard.py:588-594`，读取 `user_context_payload.get("seed_library_summary")`
- 但 `context_builder.py` **从未**设置 `seed_library_summary` 或 `node_ids` — 它只设置 `seed_library`（含 `has_seed_library` + `few_shot_examples`）
- `workflow_experience.py:477-480` 同样只设置 `seed_library.few_shot_examples`，无 `node_ids`
- 结果：`matched_seeds` 永远为空列表，output_action 永远不会附上"可使用你的种子库中的..."提示
- 影响：用户订阅了与考试科目相关的种子库，但sprint计划不会引用

**3. 种子库质量评分不影响推荐/搜索排序 — 评分是纯装饰**
- `_blend_quality_score()` (line 149-163) 混合系统评分和用户评分，逻辑合理
- `get_few_shot_examples()` (line 1514-1521) 排序仅用 subscription priority → featured → official → order_index → created_at — **不使用 quality_score**
- `semantic_search_items()` 使用 RRF fusion 排序 — 也不考虑 quality_score
- 结果：高质量种子库和低质量种子库在推荐和搜索中的排序权重相同

## Minor Issues 🟢

**4. 种子库与 Galaxy 知识节点之间无任何关联**
- `SeedLibrary` 和 `SeedItem` 模型中无 `knowledge_node_id` / `galaxy_node_id` 字段
- 种子内容无法按知识点组织，也无法在学习路径中推荐相关种子
- 用户订阅了"计算机网络"种子库，但Galaxy星图中不会显示任何种子关联

**5. mobile 端种子库使用说明纯文本，无实际跳转到聊天验证**
- `seed_library_detail_screen.dart:730-747` 的 `_buildUsageExplanation()` 显示"用于增强AI..."等说明
- 但没有提供"试用效果"按钮让用户验证种子库是否真的在影响AI回答
- 用户无法感知种子库订阅的实际效果

**6. `standard_workflow.py` 的 few-shot 注入受 `seed_library_enabled` 开关控制**
- `standard_workflow.py:1292-1315` 检查 `seed_library_enabled` 才注入示例
- 此开关来自 `grpc_context`，需Go Gateway传递 — 如果前端不传此字段，few-shot注入不会发生
- 但 `context_builder.py:702` 的 `_get_seed_library_context()` 无此开关限制，总是执行
- 两套注入路径的条件不一致

## Working Well ✅

1. **Few-shot → Prompt 注入链路完整** — `context_builder._get_seed_library_context()` → `prompts.py` 渲染 → `{seed_library_section}` 模板变量，最多3个示例以L3背景级别注入
2. **种子库分类设计完善** — fewShot/teachingContent/replyTemplate/custom 四类，各自有明确的AI增强用途说明
3. **质量评分混合算法合理** — `_blend_quality_score()` 使用动态权重 `min(0.85, 0.35 + count*0.1)`，用户评分越多权重越大
4. **订阅机制完整** — 用户可订阅/取消/启用/禁用/设优先级，`last_used_at` 自动更新
5. **语义搜索可用** — RRF fusion + pgvector 向量搜索，支持按类型/学科/标签筛选
6. **社区分享支持种子库** — SharedResource 支持 seed_library 类型，可克隆他人的种子库
7. **Flutter端数据模型丰富** — qualityScore/systemQualityScore/userRatingAvg/currentUserRating 全部映射

## Files Examined
- `backend/app/services/seed_library_service.py` (1878 lines)
- `backend/app/orchestration/context_builder.py` (lines 415-441, 695-750)
- `backend/app/orchestration/prompts.py` (lines 99, 511, 1149-1165, 1276, 1327, 1363, 1440, 1473, 1534)
- `backend/app/orchestration/planning_workflow.py` (lines 1949-1954, 2433)
- `backend/app/agents/standard_workflow.py` (lines 1292-1315)
- `backend/app/agents/workflow_experience.py` (lines 477-480, 545-555)
- `backend/app/aurora/runtime_v1/dashboard.py` (lines 588-594)
- `backend/app/services/llm_service.py` (lines 1495-1524)
- `backend/app/models/seed_content.py` (structure analysis)
- `mobile/lib/features/seed_library/presentation/screens/seed_library_detail_screen.dart` (lines 730-747)
- `mobile/lib/features/seed_library/data/models/seed_library_model.dart` (quality fields)
- `mobile/lib/features/seed_library/presentation/widgets/seed_library_card.dart` (quality display)

## Confidence: High — 三条集成链路（聊天/计划/质量）逐条追踪到终端消费点，grep确认事件消费者缺失和字段未填充。
