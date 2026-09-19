# E-01 Cognition Ladder 当前路由映射（ROUTING_MAP）

> 任务卡 E-01 交付物 ｜ worktree wt6@c3878837 ｜ 2026-09-19
> 性质：现状映射文档（不重建 router，只收敛 current paths）。数据源：dev DB 只读采样 + 读码。
> 配套明细：`trace_classification.csv`（206 行逐调用分类）；总结见 `REPORT.md`。

---

## 1. 现有路由栈的实际结构（读码结论）

聊天主链路每 turn 的路由栈（`backend/app/orchestration/orchestrator.py` process_stream）：

```
gRPC StreamChat (agent_grpc_service.py:304)
  ├─ set_request_user_tier(is_pro→pro/free)          # V3-FIX-02 独立 entitlement
  ├─ reasoning_mode = extra_context.reasoning_mode   # 客户端传入, 默认 balanced, 合法值 fast/balanced/deep
  ↓
Step10 _route_and_classify → UnifiedIntentRouter.route (core/unified_intent_router.py)
  ├─ Layer1 explicit   : payload 声明 intent, conf=1.0            [L0, 零LLM]
  ├─ Layer2 rule       : 关键词加权匹配, conf≥0.75 即收           [L0, 零LLM]
  ├─ Layer2.5 fast_path: intent=chat ∧ conf≥0.5 ∧ len≤120 ∧ 非复杂 ∧ 无动作词
  │                     → routing_layer="rule_fast_path"          [L0, FT-LAT-2 已接线]
  └─ Layer3 llm assist : 其余情况 router_llm.json_call(5s超时)     [L1, 一次隐藏分类调用]
Step11 dual_core_router.route (orchestration/dual_core_router.py)
  └─ 纯规则打分(情绪/拖延/认知负载/spine/scaffolding/belief) → execution_first|cognitive_first|balanced  [L0, 零LLM]
generation_node (agents/standard_workflow.py:1365)
  ├─ memory_answer 命中 → 直接回放, 生成短路 __end__               [L0 零LLM 直答, "recent_memory" shortcut]
  ├─ deep_analysis 档   → 强制 MAX 层(F-1)                        [L2]
  ├─ fast first touch   → 强制 FAST 层(STANDARD_CHAT_FORCE_FAST_TIER) [L1]
  ├─ balanced fast path → 强制 FAST 层(slim context 判据)          [L1]
  └─ 其余 → llm_router.select_model(agent_profile→policy→task_type→reasoning_mode→complexity→free钳制)
```

tier 落点（`core/llm_router.py`，机制归因按 Review 收据改为两段式）：

**(a) 已证实（读码逐行核对）**：`_preferred_tiers_for_reasoning_mode` 中 balanced 模式仅对 {QUICK_QUERY, SIMPLE_CHAT, ROUTING, RETRIEVAL} 把 FAST 排首位，其余任务类型链为 [STANDARD, FAST, PLUS, PRO]（llm_router.py:387-393）；slim 判据 `_should_use_slim_standard_context` 存在且会被 `planned_tool_sequence` 一票否决（standard_workflow.py:2570），但 `planned_tool_sequence` 全库唯一写入点是 tool_planning_node，**只有 exam_preparation/task_decomposition/skill_building 三种 intent**（standard_workflow.py:3185-3207），不存在记忆类序列——纯记忆指令（≤120字、无深词、无文档）按代码应通过 slim 判据进入 balanced fast path 拿到 FAST 层。

**(b) 未解（观测到的行为与 (a) 推导不符，留探针）**：其一，纯记忆指令实测仍落 plus（01:11:31 req 实测 3144/751），slim 判据链上必有未识别的破点；其二，balanced 链首选应是 STANDARD 档（dashscope_standard_thinking/deepseek_chat）、次选 FAST，**观测到的 dashscope_chat 是链上第 3 位（PLUS 档）**，STANDARD/FAST 候选被整体跳过的原因未解释（候选：模型健康熔断、`LLM_TIER_*` env 覆盖、Agent policy preferred_models 排序、专家角色 profile、reasoning_mode 未按预期传入）。**C1 修复卡必须先跑探针回答 (b) 再定挂钩点**，否则按 (a) 直改（如放开 planned_tool_sequence 排除）对纯记忆消息根本不会命中，还可能破坏考试类消息的真实工具流。

另：complexity_analyzer（纯规则 <3ms）的 delta ±1/±2 是沿 `_FALLBACK_TIER_ORDER` 移动，**可跨档**（TRIVIAL delta=-2 可一次跨两档），但只是改 tier，**不能跳过生成调用本身**。

## 2. 真实 trace 采样结论（dev DB 只读）

样本口径（按 Review 收据修正）：`token_usage` 全表为全量主干（采样时 225 行、复核时 227 行），CSV 做**代表性收录** 190 条调用——36 条未收录行几乎全是重复的 default 0/0 失败探针（全表 default 0/0 共 20 条，CSV 收 10 条）。逐调用分类结果不变（CSV 已验收）：

| 分类 | 条数 | 占比 | 代表 |
|---|---|---|---|
| necessary_llm | 17 | 8% | 文档接地问答、deep_analysis(MAX) 显式深度分析 |
| rule_eligible | 142 | 69% | 记忆指令确认/记忆检索问答落 plus+balanced（应 L0/L1）|
| batch_eligible | 30 | 15% | deepeval/deepqe 离线评测走 pro/max 直出层、离线队列走 plus |
| wasteful | 11 | 5% | ①"你好"级问候走 plus 全链(~2.1k prompt tokens) ②default 配置 0/0 token 失败调用 |
| insufficient_evidence | 6 | 3% | 非uuid测试车道无消息落库 |

关键发现（详细论据见 CSV rationale 列）：

- **W-1 plus 层对 L0/L1 级流量的持续性覆盖面缺口（主要浪费面，非新近回归）**：09-19 当日真实聊天生成 **54/54 条全部落 dashscope_chat(plus)+balanced**（当日唯一 fast 是 4 条 48-token 探针），其中 41/54 个会话含记忆指令/检索型消息（CSV 中 chat 类 rule_eligible=130 条）。**这不是两日间的行为漂移**：09-18 当天 MRV 文档问答 20 次调用 = 15 plus + 4 fast + 1 default，fast 仅占 1/5；同日记忆指令会话全部落 plus（收据重算 30 session/45 调用；09-19 为 22/33 plus）。即 plus 承接记忆级/检索级流量**自 09-18 起就是主模式**，覆盖面缺口长期存在。09-18 的 4 条 fast MRV 成功记录仅证明 FAST 层有能力承接同类问题，不证明当时常态。
- **W-2 问候直答缺失**：complexity_analyzer 判 TRIVIAL 后只沿 tier 链做 delta 移动（可跨档但不跳过生成），问候语仍走完整生成链（prompt 固定开销 ~2.1k tokens）。首条消息的 intent fast path（FT-LAT-2）只省了 Layer3 分类调用，没省生成层。
- **W-3 失败调用可观测**：`default` 模型 0/0 token 记录（全表 20 条，CSV 收 10 条）= LLMService 初始化失败回退链的痕迹，零价值但计入了调用面（含 1 条"计划执行中断"用户可见错误）。
- **W-4 评测/离线车道未走 batch**：deepeval/deepqe 离线评测 25 条全走 pro/max 直出层（avg completion 2128 tok）；glm_4_7_plus 22 条为离线队列补发（非真实聊天）。与"MiniMax M3/glm_batch 只承接异步分析"的车道约束一致化后可全部迁移。
- **W-5 记忆车道零 LLM（好消息）**：direct_capture(184) 与 inferred_extraction(52) 两条记忆写入车道**均为纯规则**（memory_inferred_write_lane.py 无任何 LLM 调用），无隐藏深模型。但 semantic_key 碎片化（"最喜欢的电影=星际穿越"同一事实存在 **8 种** key 变体；236 条仅 53 个不同摘要）造成重复入库与检索噪声——这是 L0 层的数据质量问题，不是模型问题。
- **W-6 上下文包固定开销**：所有聊天调用 prompt 起步 ~2.1k tokens（"你好"也是 2107）。上下文包对 L0/L1 级 turn 没有瘦身档位与 slim 生成共用判据。
- **观测缺口**：Layer3 intent 分类、sufficiency、HyDE、planning 链（47 个 planning context_pack_runs 的 request_id 全部未回填）都不进 token_usage/billing 队列——隐藏调用量目前不可度量。

## 3. L0–L3 准入判据（基于现状映射，不新建 router）

| 级 | 定义 | Entry 判据（现有机制落点） | 出口/退级 | 现状落点 |
|---|---|---|---|---|
| **L0 No-Model** | 确定性逻辑直答/写库，零 LLM | ① 空消息/纯问候/纯确认（complexity=TRIVIAL 或 greeting regex）② memory_answer 命中（近轮回放）③ Layer1 explicit intent + 模板动作（翻译/任务 CRUD 回执）④ 记忆 direct_capture/inferred_extraction 写入 ⑤ plan review 的 `_quick_rule_check` 自动批准 ⑥ dual_core 模式决策（本就零 LLM） | 判据不满足→L1 | 已存在但**不全生效**：问候仍走生成链（W-2）；memory_answer 只覆盖"最近轮原样可答"的窄集 |
| **L1 Fast Semantic** | fast tier 单次轻调用（thinking off） | ① reasoning_mode=fast 且 chat_mode=standard（fast first touch，已实现）② balanced + slim context + ≤120字 + 无深词（balanced fast path，已实现）③ intent∈{QUICK_QUERY, SIMPLE_CHAT, ROUTING, RETRIEVAL}（balanced 模式 FAST 排首位的现状判据，llm_router.py:375-393）④ 记忆指令确认/检索问答（**建议新增**，见收敛项 C1/C2） | 检索/工具需要→L2；用户显式 deep→L2 | 判据已存在，但 balanced 主流量未进入（W-1；破点未定位，见机制段 (b)）|
| **L2 Deliberate** | standard/plus/pro 层，thinking on，多源上下文 | ① intent∈{PLAN, ERROR_DIAGNOSIS} 且 conf≥0.8（execution_mode=langgraph 现判据，unified_intent_router.py:707）② 消息长(>120)/多问句/深度词命中（complexity≥COMPLEX）③ dual_core=cognitive_first 或 very_high_cognitive_load ④ RAG 检索命中/文档接地 ⑤ phase_d 强制 tier | 工具多步编排→L3 | 主力路径；plus 层当前承接了本应 L1 的流量（W-1）|
| **L3 Agent Run** | 多步工具执行/规划编排 | ① planning_workflow（澄清→生成→审查→执行）② execution_engine 工具循环（tool_loop_count 上限已有）③ plan review 触发跨模型复核（conf<0.7 ∨ 高危工具 ∨ >8 tool calls）④ deep_analysis 显式深度档（MAX 层，F-1） | — | 已有；审查前置规则门（quality_gate+feasibility+quick_rule_check）即 L0 gate |

**与 dual_core 的关系**：dual_core_router 的 mode（execution_first/balanced/cognitive_first：`routing_decision_log.decision_type` 实测 155/54/18，含 227 条 context_plan 行不计 mode）是**认知调制**轴，决定 prompt 指令与策略约束，**不直接选 L 级**；L 级由 intent→execution_mode + reasoning_mode→tier 决定。映射为：cognitive_first 倾向 L2（澄清类回复），execution_first 倾向 L0/L1（直推执行），balanced 在 L1/L2。收敛时保持两轴正交，不合并。

**与 tier 的关系**：L0=跳过生成（非 tier）；L1=FAST（dashscope_fast/qwen3.8-flash thinking off）；L2=STANDARD/PLUS/PRO（同模型 thinking on，差异只是 thinking 与计费口径）；L3=编排（内含 L1/L2 调用 + 工具）。由于 qwen3.8-flash 全 tier 同底层模型，**L1→L2 的真实差是 thinking token 与 TTFT，不是模型能力差**——这使"该 L1 的 turn 落 L2"的代价主要是延迟（fast TTFT p50 475ms 基线）而非质量差异，收敛风险低。

## 4. 收敛建议（current paths 内，不重建）

- **C1（对应 W-1，前置探针未跑前不得实施）**：目标是把记忆指令/检索问答级 turn 显式归 L1（FAST tier）。**挂钩点待定**：已证伪"记忆工具序列排除"假设（planned_tool_sequence 只有 exam/task/skill 三种 intent，纯记忆消息按码应过 slim 判据），故不得在该处挂钩；必须先完成下方 C1-探针回答机制段 (b) 的两个未解问题，再定判据挂点，且修复需**显式排除 exam_preparation 工具流路径**（含考试词+urgency 的记忆消息依赖 planned_tool_sequence 走真实工具执行，不能被误伤）。
- **C1-探针（给修复卡的具体方法）**：① 复现跑：向 dev 环境发一条纯记忆指令（如"我最喜欢的电影是《星际穿越》，帮我记住这个"），在 `_should_use_slim_standard_context`、`_should_disable_tools_for_light_standard_reply`、`_resolve_reasoning_mode` 三个判据入口加临时日志，落盘各输入（chat_mode/file_ids/document_context/retrieval_decision/planned_tool_sequence/selected_experts/reasoning_mode 实际值）；② 同一次跑在 `llm_router.select_model` 打印 `LLMSelection.reason` 全文与候选链（`resolve_candidate_models`），确认 target_tier 与最终 model_key 是否一致；③ 静态核查部署 env：`LLM_TIER_STANDARD/LLM_TIER_FAST/LLM_TIER_PLUS` 覆盖与 `LLM_PROVIDER`（llm_router.py:797 `_override_tier_mapping_from_env` 可整体改写候选链）；④ 核查 GENERATION 角色 profile 的 model_policy.preferred_models 是否把 dashscope_chat 排前（agent_profiles.py 注册表）。①②定位 slim 判据破点，③④定位 PLUS 跳档原因。
- **C2（对应 W-2）**：TRIVIAL（问候/确认）走 L0 模板直答或至少强制 FAST+零工具+零检索；上下文包对 TRIVIAL turn 降为空档。
- **C3（对应 W-3）**：default 回退配置从 billing 记录中隔离为 error 事件，不再产生"成功调用"假象。
- **C4（对应 W-4）**：deepeval/deepqe/离线队列全部迁 GLM_BATCH 车道（V3-FIX-04 coding 端点已接线，MiniMax 池并发 8 可用）。
- **C5（观测缺口）**：Layer3 分类、sufficiency、HyDE、planning 链调用补 token_tracker 埋点 + context_pack_runs.request_id 回填（为 D-06/O-02 的度量前置；C1-探针的 ①② 日志可直接升级为 C5 的常驻埋点）。
- **C6（数据质量）**：记忆 semantic_key 归一化（同事实合并 key），非本卡范围，登记给记忆线。

## 5. metrics 口径建议（文档级，D-06/O-02 铺垫）

1. **每级调用占比**：`L0_skipped / L1 / L2 / L3` 四级 counter，落点 `LLM_ROUTER_SELECTION_TOTAL` 增加 `ladder_level` label（由 generation_node 的判定分支写入 context_data 一并透传）。目标形态：L0+L1 ≥ 60%（当前 09-19 真实聊天 54/54 全落 plus+balanced，反推 L0≈0、L1≈0）。
2. **隐藏调用比**：`auxiliary_llm_calls / generation_calls`（Layer3+sufficiency+HyDE+review+planning chain / 主生成），当前无数据（C5 前置）。健康线 <0.5。
3. **wasteful 率**：`(default回退调用 + TRIVIAL全链生成) / 总调用`，当前采样值 5%（W-2+W-3 修后应 ≈0）。
4. **每级时延**：按 ladder_level 分组的 TTFT 与 total latency（fast TTFT p50 475ms 为 L1 基线；L2 记录 thinking 占比）。复用 latency_probe.mark 现有埋点。
5. **每级成本**：`token_usage.cost` 按 ladder_level 聚合（需要 C5 埋点补齐后才能算全）；batch 车道单列（MiniMax $0）。
6. **fast path 守护指标**：`rule_fast_path` 命中率（intent 层）与 `first_touch_model_tier=fast` 命中率（生成层），任一跌穿基线即告警——这是"fast path 不退化"的持续度量，不只靠测试。

## 6. fast path 不退化验证（证据清单）

读码链（全部现存且默认开启）：

- intent 层：`_should_skip_llm_assist`（unified_intent_router.py:555）五重守卫（intent=chat、conf≥0.5、≤120字、非复杂、无动作词）→ `routing_layer="rule_fast_path"`。
- 生成层：`_should_force_fast_first_touch`（standard_workflow.py:236，STANDARD_CHAT_FORCE_FAST_TIER 默认 True）→ 强制 `ModelTier.FAST`；`_should_force_balanced_fast_first_touch`（:254）→ FAST+QUICK_QUERY；`_needs_fast_standard_guard`（:222）→ fast 档逃逸到高层时强制 fast rescue 回答。
- L0 直答：`_resolve_recent_memory_answer` → generation 短路 `__end__`，零 LLM。

既有测试（静态证据；worktree 无 venv，按 LIGHT 约束未安装依赖跑 pytest）：

- `backend/tests/unit/test_unified_intent_router_fast_path.py`（2 用例：简单首条消息跳过 LLM assist 且 `llm_calls==[]`）
- `backend/tests/unit/test_unified_intent_router_fast_path_first_message.py`（5 用例：空历史不再强制 LLM、复杂/动作消息仍走 LLM assist）
- `backend/tests/unit/test_standard_workflow_generation_routing.py`（27 用例，含 `test_generation_node_forces_fast_tier_for_standard_chat`、`test_generation_node_forces_fast_tier_for_balanced_light_standard_chat`、`test_generation_node_answers_recent_memory_question_without_llm`）
- `backend/tests/unit/test_deep_analysis_tier_routing.py`（6 用例，F-1 MAX 强制）
- `backend/tests/unit/test_llm_router_free_tier.py`（14 用例，V3-FIX-02 免费层钳制）

合计 54 用例守护 fast path 判据。

DB 侧交叉验证（按收据口径修正）：09-18 MRV 文档问答 20 次调用中 4 条 fast 成功记录，仅证明 **FAST 层有能力承接**该类问题；同日 plus 已占 15/20、记忆指令会话全 plus——即 fast path 判据本身未退化（测试守护完好、能力有实证），但 balanced 主流量**自 09-18 起就未进入**这些判据（W-1 持续性覆盖面缺口），slim 判据链破点与 PLUS 跳档原因待 C1-探针定位。
