# E-01 任务报告：Cognition Ladder 当前路由映射

- 任务卡：E-01（stream AI / risk medium / resource LIGHT / gate 前置基线）
- worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt6` @ c3878837
- 日期：2026-09-19 ｜ 禁 commit/push（未 commit）
- 交付物：
  - `v3-output/E-01/ROUTING_MAP.md` — 路由栈现状 + L0–L3 准入判据表 + 收敛建议 C1–C6 + metrics 口径
  - `v3-output/E-01/trace_classification.csv` — 206 行逐调用分类明细
  - 本报告

## 做了什么

1. **真实 trace 采样（只读 dev DB）**：以 `token_usage` 全表为全量主干（采样时 225 行、复核时 227 行；重复的 default 0/0 失败探针未逐行收录——全表 20 条收 10 条，属代表性收录），join `chat_messages` 还原触发消息，覆盖 113 个真实聊天 journey（190 条调用入 CSV），外加记忆写入车道（236 条 episodic_memories 抽样 12）、规划 journey（context_pack_runs intent=planning 共 47 run，链路静态分类）、审查链（plan_review_service 读码）、离线/评测/探针车道。逐调用按 必要/可规则/可batch/浪费 四类打标，每行附 rationale。
2. **逐调用分类结果**：necessary_llm 17 ｜ rule_eligible 142 ｜ batch_eligible 30 ｜ wasteful 11 ｜ insufficient_evidence 6（明细见 CSV）。
3. **L0–L3 判据表**：完全基于现有 UnifiedIntentRouter 三层级联 + dual_core_router 规则打分 + standard_workflow fast path 判据 + llm_router tier 链映射，未新建路由概念；明确 dual_core（认知调制轴）与 ladder（模型深度轴）正交。
4. **fast path 不退化**：读码证明三层判据（intent rule_fast_path / fast first touch / balanced fast path / recent_memory 零LLM直答）均现存且默认开启；既有测试 5 个文件共 54 用例作为守护（worktree 无 venv，按 LIGHT 约束未装依赖跑 pytest，以静态断言清单为证）；DB 侧 09-18 的 4 条 fast MRV 记录证明 FAST 层有能力承接该类问题（判据未退化），但同日 plus 已是主模式——问题是 balanced 主流量持续未进入判据（W-1 覆盖面缺口），破点待 C1-探针。

## 关键发现（wasteful 面按影响排序）

1. **W-1 plus 层对 L0/L1 级流量的持续性覆盖面缺口（主要浪费面，非新近回归）**：09-19 真实聊天生成 **54/54 条全部落 plus+balanced**（"172"为两日全表 plus+balanced 口径，其中 22 条 glm_4_7_plus 是离线队列、非真实聊天），其中 ~130 条（41/54 会话）为记忆指令/检索问答级。**非两日间行为漂移**：09-18 当天 MRV 文档问答 20 次调用 = 15 plus + 4 fast + 1 default，同日记忆指令会话全部落 plus（30 session/45 调用）——plus 承接记忆级流量自 09-18 起就是主模式。09-18 的 4 条 fast 记录仅证明 FAST 层有能力承接，不证明当时常态。
2. **W-2 问候直答缺失**：TRIVIAL 消息仍走完整生成链（prompt 固定 ~2.1k tokens 开销），complexity delta 只沿 tier 链移动（可跨档）但不跳过生成调用。
3. **W-3 失败调用计账**：`default` 配置 0/0 token 调用（全表 20 条，CSV 收 10）产生零价值调用记录（LLMService 初始化失败回退）。
4. **W-4 评测/离线车道未 batch 化**：deepeval/deepqe 25 条走 pro/max 直出层；glm_4_7_plus 22 条离线队列走 plus。可整体迁 GLM_BATCH/MiniMax 车道。
5. **好消息**：记忆写入两车道均纯规则零 LLM（无隐藏深模型）；审查/规划链有 L0 规则前置门（quick_rule_check/quality_gate）；semantic_key 碎片化比初报更严重——"最喜欢的电影=星际穿越"同一事实存在 **8 种** key 变体（236 条仅 53 个不同摘要），归 C6/记忆线。
6. **观测缺口**：intent Layer3、sufficiency、HyDE、planning 链调用不进 token_usage；47 个 planning run 的 request_id 未回填——隐藏调用量目前不可度量（C5 建议）。
7. **机制归因两段式（R2 修订）**：已证实——balanced 模式仅 {QUICK_QUERY,SIMPLE_CHAT,ROUTING,RETRIEVAL} FAST 排首位（llm_router.py:387-393）；planned_tool_sequence 唯一写入点是 exam/task/skill 三种 intent（standard_workflow.py:3185-3207），**无记忆序列**，纯记忆消息按码应过 slim 判据。未解——纯记忆消息实测仍落 plus 的判据破点，以及 balanced 链 [STANDARD,FAST,PLUS,PRO] 中 STANDARD/FAST 被跳过、直接落第 3 位 PLUS 的选型跳档原因；已列为 C1-探针（判据入口临时日志 + select_model reason 全文 + env tier 覆盖核查 + GENERATION profile preferred_models 核查），修复卡必须先探针后定挂钩点，并显式保护 exam_preparation 工具流路径。

## L0–L3 判据要点

- L0：TRIVIAL 问候/确认、recent_memory 回放、显式 intent 模板动作、记忆规则写入、计划规则审查门——判据已存在但 L0 覆盖不全（问候/记忆确认仍走生成）。
- L1：fast first touch + balanced fast path 现有判据；balanced FAST-first 判据集 = {QUICK_QUERY, SIMPLE_CHAT, ROUTING, RETRIEVAL}；建议把记忆指令/检索问答显式归入（C1，挂钩点待 C1-探针）。
- L2：intent∈{PLAN, ERROR_DIAGNOSIS}∧conf≥0.8（langgraph 触发集，不含 SPRINT_PLAN）、复杂度 COMPLEX+、cognitive_first/高认知负载、RAG 命中。
- L3：planning_workflow 编排、工具循环、跨模型复核（conf<0.7/高危工具/>8 calls）、deep_analysis 显式 MAX（F-1）。
- 因 qwen3.8-flash 全 tier 同底层模型，L1→L2 真实差 = thinking token + TTFT（fast p50 475ms 基线），收敛风险低。

## R2 修订记录（响应 REVIEW_RECEIPT CHANGES）

- 修订 1（口径）：W-1"172/225"改为准确口径——172 为两日全表 plus+balanced（含 22 条 glm 离线队列）；09-19 真实聊天 plus=54（54/54 全 plus+balanced 属实）。REPORT/ROUTING_MAP 同步；采样口径改述为"全量主干+代表性收录"（default 0/0 全表 20 条收 10）。
- 修订 2（定性）：删除"近期行为漂移/回归"叙事，改为"持续性覆盖面缺口"；如实补入 09-18 MRV 20 调用=15 plus/4 fast/1 default、09-18 记忆指令会话全 plus（30/45）对照（Worker 已独立复核确认）。
- 修订 3（机制两段式）：已证实（balanced FAST-first 集合 + slim 判据存在 + exam 词消息经 exam_preparation 触发 planned_tool_sequence）与未解（纯记忆消息判据破点、PLUS 跳档原因）分开陈述；新增 C1-探针具体方法（判据入口日志复现跑 + select_model reason/候选链打印 + env tier 覆盖核查 + GENERATION profile 核查）；C1 明确不得按"记忆工具序列排除"挂钩，须显式排除 exam_preparation 工具流路径；complexity 表述改"±1/±2 可跨档"。
- 修订 4（判据表小修）：L1 补 ROUTING/RETRIEVAL；L2 删 SPRINT_PLAN（langgraph 触发集仅 {PLAN, ERROR_DIAGNOSIS}）；dual_core 计数标注来源表 routing_decision_log.decision_type；测试用例数精确为 54；W-5 semantic_key 变体数修正为 8。
- CSV 未改动（Reviewer 已验收通过）。

## 未做 / 边界

- 未跑 pytest（worktree 无 venv；LIGHT 约束 + 磁盘纪律，选择静态证据路线）。
- 未改任何代码（任务卡为映射+收敛文档，收敛项 C1–C6 留给后续 FIX 卡）。
- dev DB 中 09-19 样本高度集中于记忆验收场景（V3 验收回放），占比数字反映验收流量结构，上线结构需 D-06 埋点后重测。

## 清理确认

- /tmp 修订工作副本与首轮采样 dump 已删；未创建任何仓库外持久文件；无进程/模拟器/构建产物遗留；未 commit/push。
- changes.patch（R2 文档修订 diff）归档于本目录 `changes.patch`。
