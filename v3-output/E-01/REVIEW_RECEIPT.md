# E-01 REVIEW_RECEIPT（独立 Reviewer）

- Reviewer：E-01 验收 Reviewer（wt6，LIGHT/REVIEW 档）
- 日期：2026-09-19 ｜ 对象：`v3-output/E-01/`（ROUTING_MAP.md、trace_classification.csv、REPORT.md）
- 方法：只读 dev DB（sparkle_db @127.0.0.1:5432，全部 SELECT）独立重算 + wt6 代码逐条对照 + CSV 程序化解析。未改任何代码。

## 1. 逐项复核结论

### 1.1 CSV 完整性 —— 通过
- 206 行、14 列 schema 全一致、无错位；分类计数 necessary 17 / rule_eligible 142 / batch_eligible 30 / wasteful 11 / insufficient_evidence 6，与自报完全一致。
- CSV 覆盖 token_usage 191 行（表现 227 行、采样时 225 行）；未覆盖的 36 行几乎全是重复的 default 0/0 探针（DB 中 default 0/0 实际有 20 条，CSV 收录 10 条）。**CSV 是代表性抽样而非全量**，REPORT"token_usage 225 条全量为主干"的表述偏强，量级结论不受影响。

### 1.2 漂移断言独立重算 —— 方向成立，"漂移"框架不成立（主要修订点）
独立 SQL（token_usage ⋈ chat_sessions ⋈ chat_messages）重算：
- **09-19 真实聊天确实全落 plus+balanced**：54/54 条 chat journey 生成落 dashscope_chat(plus)+balanced；当日唯一的 fast 是 4 条探针（3 条 "What is machine learning" 48-token 探针 + 1 条 round5 注入），1 条 default 0/0 失败。✔
- **~130 条量级成立**：CSV rule_eligible(chat)=130；DB 侧 09-19 plus 会话 54 条中 41 条含记忆指令/检索型消息。✔
- **但"172/225"是日期错标**：172 = 全表两天的 plus+balanced（dashscope_chat 150 + glm_4_7_plus 22，后者是离线队列非真实聊天）；09-19 当日真实聊天 plus 只有 54 条。
- **"09-18 同类由 fast 正常承接→近期漂移"被重算否定**：09-18 当天 MRV 文档问答共 20 次调用，仅 4 次 fast、**15 次 plus、1 次 default**；同日记忆指令会话 30 个 session/45 次调用**全部落 plus**（09-19 为 22/33 plus）。即 plus 承接记忆级流量在 09-18 已是主模式，**这是持续存在的覆盖面缺口，不是两日之间的行为漂移**。Worker 结论里"覆盖面缺口而非回归"一句是对的，但其论据链（拿 4/20 的 fast 记录证明 09-18 正常态）是樱桃采摘。

### 1.3 机制归因审查 —— 第一环证实，第二环证伪一半，最后一环缺失（修复卡依据不扎实）
- ✔ **证实**：balanced 模式下非 {QUICK_QUERY,SIMPLE_CHAT,ROUTING,RETRIEVAL} 的 tier 链首位是 STANDARD 非 FAST（llm_router.py:387-393，逐行一致）。
- ✔ **证实（机制存在）**：`_should_use_slim_standard_context` 确实被 `planned_tool_sequence` 一票否决（standard_workflow.py:2570）；balanced fast path 判据链（:254-296）与文档描述一致；`_should_force_fast_first_touch` 只对 reasoning_mode=fast 生效（:236-251）。
- ✘ **证伪（触发归因）**：`planned_tool_sequence` 全库唯一写入点是 tool_planning_node 的 tool_sequences 字典（standard_workflow.py:3196-3207），**只有 exam_preparation/task_decomposition/skill_building 三种 intent，不存在"记忆工具序列"**。纯记忆指令（"我最喜欢的电影是《星际穿越》，帮我记住这个"，18 字）不匹配任何 _classify_user_intent 关键词、也通过 `_should_disable_tools_for_light_standard_reply`，按代码应过 slim 判据——却仍落 plus（01:11:31 req 实测 3144/751）。只有含考试词+urgency 的记忆消息（"下周三有…考试，帮我记住"）才经 exam_preparation 触发 planned_tool_sequence。
- ✘ **缺失（最后一环）**：即使 balanced 链生效，链是 [STANDARD, FAST, PLUS, PRO]，首选应是 dashscope_standard_thinking/deepseek_chat（STANDARD 档），次选 dashscope_fast——**观测到的 dashscope_chat 是链上第 3 位（PLUS 档）**，文档把 STANDARD 档直接等同 dashscope_chat=plus 是错的。为何 STANDARD/FAST 候选全被跳过（健康熔断？env tier 覆盖？策略 preferred_models 排序？专家角色 profile？）本文档未解释，**C1 修复卡若按现机制描述实施，挂钩点（放开 planned_tool_sequence 排除）对纯记忆消息根本不会命中，还可能破坏考试类消息的真实工具执行**。
- 附带：complexity_analyzer "±1/±2 档内移动、不能跳层"表述有误——TRIVIAL delta=-2 在 _FALLBACK_TIER_ORDER 上可跨档移动。

### 1.4 抽样复核（8 行）—— 全部通过
你好/2107+183(wasteful)、MRV default 0/0(wasteful)、星际穿越记忆写入(2780/299 rule_eligible)、记忆检索问答(2162/237 rule_eligible)、09-19 fast 探针 48/104(necessary)、09-18 MRV fast 2563/349 与 2520/511(necessary)、deepeval pro 直出 2383/1179(batch_eligible)——request_id/时间/模型/tier/mode/双 token 与 DB 逐字段一致，分类判据与 rationale 自洽。附：episodic_memories 复核支持 W-5 且比自报更严重——"最喜欢的电影=星际穿越"同一事实存在 **8 种** semantic_key 变体（自报 ≥4）；53 个不同摘要 ✔。

### 1.5 L0-L3 判据表 & fast path 证据 —— 基本通过
- memory_answer 直答短路、fast first touch、rule_fast_path(_should_skip_llm_assist :555/:274)、langgraph conf≥0.8∧{PLAN,ERROR_DIAGNOSIS}、plan review 规则门（quality_gate/feasibility/_quick_rule_check，:499/:1075 conf<0.7/:1082 >8 tools/:1174 高危工具）、deep_analysis 强制 MAX——逐一与代码对上。
- 两处小误：L1 判据集少写了 ROUTING/RETRIEVAL；L2 写入 SPRINT_PLAN 但代码 langgraph 触发集只有 {PLAN, ERROR_DIAGNOSIS}。
- 5 个测试文件全部存在，用例数 2/5/27/6/14=54（自报"40+"✔），三个点名用例逐字存在。
- dual_core 155/54/18：DB 无持久化落点可复算（durable_session_state_snapshots 空、context_pack_runs.budgets 无 mode、event_store 空），推测为日志推导，**未独立证实**（其"正交轴"定性判断与代码一致）。

### 1.6 安全与纪律 —— 通过
- 交付物无密钥/凭据（扫描通过）；wt6 仅新增未跟踪 v3-output/E-01/（未 commit ✔）；主仓零写入 ✔；无进程/模拟器/构建产物遗留；Reviewer 自身 /tmp 探针已清。

## 2. 裁定

**CHANGES**（文档修订，数据与分类无需重做）。required edits：
1. ROUTING_MAP §2 / REPORT W-1：把"172/225"改为准确口径（两日全表 plus+balanced=172，其中 09-19 真实聊天 plus=54；glm 22 条为离线队列）；删除/改写"近期行为漂移"叙事，改为"持续性覆盖面缺口"，并如实给出 09-18 MRV 20 调用中 15 plus/4 fast/1 default、09-18 记忆指令 45 调用全 plus 的对照（这反而加强"缺口非回归"结论）。
2. 机制节：改为两段式——(a) 已证实：balanced tier 链首位非 FAST + slim 判据存在 + exam 词记忆消息经 exam_preparation 触发 planned_tool_sequence；(b) 未决：纯记忆指令落 plus 的真实判据破点与"PLUS 而非 STANDARD/FAST"的选型跳档原因，登记为 C1 前置探针（建议用 C5 埋点或一次带日志的复现跑）。
3. C1 措辞修正：不得按"记忆工具序列排除"挂钩（该序列不存在）；需先回答 (b) 再定挂钩点，并显式排除 exam_preparation 工具流路径。
4. 小修：L1 判据集补 ROUTING/RETRIEVAL；L2 删 SPRINT_PLAN；"complexity 不能跳层"改为"±1/±2 移动且可跨档"；"token_usage 全量"改为"全量主干+代表性收录（36 条重复 0/0 探针未逐行入 CSV）"。

VERDICT: CHANGES
