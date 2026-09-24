# E-01 Cognition Ladder 当前路由映射（ROUTING_MAP v2，接续刷新）

> 任务卡 E-01 重跑（B-05/B-06 已合入后的当前态刷新）｜ worktree `wt316-e01-cog-ladder-map` ｜ base `101c19b9` ｜ 2026-09-22 采样窗口至 09-24
> 性质：现状映射文档（不重建 router，只收敛 current paths）。
> 前版：`v3-output/E-01/ROUTING_MAP.md`（wt6@c3878837，2026-09-19）。本版差异全部来自其后合入的 **E-02（capability lane + memory_class 根修）**、**E-06（batch 车道）**、**E-07（健康三相滞回）**、**B-05/B-05b（capability probe + 智谱 key 轮换）**、**XIAOMI-MODEL / BATCH_LLM_PROVIDER 开关**。v2 只改文档，零代码改动。
> 配套明细：`trace_classification.csv`（132 行 = E-02 合入后 98 条生成调用 + 34 条 default 0/0）；总结见 `REPORT.md`。

---

## 1. 现有路由栈的实际结构（当前 HEAD 读码结论）

聊天主链路每 turn 的路由栈（与 v1 的结构差异以 ► 标注）：

```
gRPC StreamChat (services/agent_grpc_service.py:291)
  ├─ set_request_user_tier(is_pro→pro/free)        agent_grpc_service.py:304（V3-FIX-02，flame_level 永不参与）
  ├─ reasoning_mode = extra_context.reasoning_mode  agent_grpc_service.py:335-337（fast/balanced/deep，缺省 balanced）
  ↓
orchestrator.process_stream (orchestration/orchestrator.py:2150)
  ├─ Step: _route_and_classify (routing_engine.py:2149) → UnifiedIntentRouter.route
  │    ├─ Layer1 explicit   : unified_intent_router.py:237（payload 声明 intent, conf≥0.95）      [L0 零LLM]
  │    ├─ Layer2 rule       : :250（关键词加权, conf≥0.75 即收）                                  [L0 零LLM]
  │    ├─ Layer2.5 fast_path: :269-285（intent=chat ∧ conf≥0.5 ∧ ≤120字 ∧ 非复杂 ∧ 无动作词      [L0 零LLM]
  │    │                     → routing_layer="rule_fast_path"；守卫 _should_skip_llm_assist :555）
  │    └─ Layer3 llm assist : :287→:412-476（router_llm.json_call 5s 超时, 失败降级 "chat"）      [L1 隐藏分类调用]
  ├─ Step: dual_core（认知调制轴，与 ladder 正交）
  │    ├─ belief_state 注入 : routing_engine.py:763-845（services/evidence 融合产物投影 router signals）
  │    ├─ 快捷道            : routing_engine.py:1409-1416（intent=chat ∧ direct → execution_first）
  │    ├─ Aurora 切流投影    : :1431 route_dual_core_via_aurora（cutover shadow/active 状态机）     ► 新
  │    └─ 纯规则打分        : dual_core_router.py:208 route()（情绪/拖延/认知负载/spine/belief）  [L0 零LLM]
  └─ generation_node (agents/standard_workflow.py:1459) —— tier 决策分支按序：
       ├─ E-02 lane 遥测      : :1498-1503 resolve_capability_lane（零 LLM，lane 不改 tier）        ► 新
       ├─ memory_answer 命中  : :1505-1520 近轮回放直答短路 __end__（_resolve_recent_memory_answer :981）[L0 零LLM]
       ├─ deep_analysis 档    : :1536-1545 强制 MAX（F-1；_deep_analysis_generation_tier :141-158）
       ├─ phase_d 强制 tier   : :1546-1553（capability_selection_policy cost_band→preferred_tier，
       │                        经 session_state_mixin.py:292/:385 写入 phase_d_forced_model_tier） ► v1 未单列
       ├─ fast first touch    : :1554-1565 强制 FAST（_should_force_fast_first_touch :248-263）
       ├─ balanced fast path  : :1566-1582 强制 FAST+QUICK_QUERY（:266-292；slim 判据 :2792-2816
       │                        含 E-02 graph_only 不否决记忆轮第二道防线 :2801-2811）              ► 语义修复
       └─ 其余 → llm_router.select_model (core/llm_router.py:1080)
            profile→policy→task_type→reasoning_mode 链（:506-538）→ 复杂度 delta（:1157-1173，
            complexity_analyzer.py:66 纯规则<3ms）→ 免费层钳制（:1175-1189）→ 健康秩+自适应重排
            （:1211-1213，E-07 三相滞回 ModelHealthState :231-336）                            ► 新
```

tier/车道基础设施（当前态）：

- **候选链**：`_preferred_tiers_for_reasoning_mode`（llm_router.py:506-538）。balanced FAST 排首位集 = {QUICK_QUERY, SIMPLE_CHAT, ROUTING, RETRIEVAL}（:529-530）——v1 机制段 (b) 之谜二在 E-02 探针②③④关闭（dev env `LLM_TIER_STANDARD=dashscope_standard_thinking,dashscope_chat` + 健康跳过 → `dashscope_chat` 代码注册 tier=plus）。
- **思考控制**：DashScope FAST/STANDARD/PLUS 显式关思考（:191-207）；GLM 车道仅 coding 端点真关思考 + max_tokens 留量（:122-174，B-05b key 轮换后 glm-5.3-flash 接线）。
- **batch 车道**：`BATCH_LLM_PROVIDER` 开关（llm_router.py:65-78，dev=**minimax**）；E-06 异步认知车道 services/batch_worklane.py（:236 force GLM_BATCH + 独立预算/幂等/死信）；glm_batch_service.py:92-109。前台能力层永不感知。► 新
- **证据/认知链（L0 为主）**：`services/evidence/fusion_engine.py`（纯贝叶斯，零 LLM）→ BeliefState → dual_core routing_input（routing_engine.py:763-845）；`MetacognitionHintV1`/`SRLPhaseHint`/`SocialSignalsV1` 由 state_aggregator 注入 dual_core（dual_core_router.py:64-66）。唯一 LLM 点：`conversational_extractor`（chat_signal_collector.py:216-228，见 §4 G-4）。
- **记忆车道**：记忆类轮次检索早退 retrieval_intent.py:400-409（memory_class_turn → no_retrieval，W-1 根修）；context cache 写意图旁路 context_builder.py:177；graph_rag 复用同一词表 graph_rag.py:56。词表真源 = capability_lane.py:203 classify_memory_class_message（指令/检索两族，含 R2-F1/F2 反模式）。

## 2. 真实 trace 采样结论（dev DB 只读，窗口 09-20 13:24 → 09-24）

E-02 ACCEPT merge = 09-19 21:20（690541e3）。以 merge 点为界做前后对照：

**前后对照（同表口径 token_usage 全量）：**

| 窗口 | 真实聊天生成落点 | 记忆类消息落点 | 结论 |
|---|---|---|---|
| 09-18～09-19（合并前，v1 采样） | 54/54 全部 dashscope_chat(**plus**)+balanced | 记忆指令/检索问答全 plus（~2.3-3.1k prompt） | W-1 覆盖面缺口成立 |
| 09-20～09-24（合并后，本卡采样） | uuid 会话 44 条全部 dashscope_**fast**（+balanced） | 记忆类轮次落 FAST（probe 复验 slim=True/balanced_fast=True） | **W-1 行为面已关** |

**E-02 合入后 98 条生成调用按车道分解（CSV 全量 132 行）：**

| 车道 | 条数 | ladder 观测 | 分类 |
|---|---|---|---|
| uuid_chat（真实聊天旅程） | 44 | L1×28、L2/L3 语境×12、L2→L1 错位×4 | necessary_llm 37 + rule_eligible_for_deeper 3 + 早于反指标修复的引用问答 1（记 L2→L1） |
| ns_canary（`ns001-*` 金丝雀巡检） | 46 | L1 | necessary（合成流量，健康探针；建议仪表盘可分离，见 §5 M-6） |
| aurora_modeling（`aurora_modeling_*`） | 8 | L1（旁路生成） | necessary 但无消息对应——隐藏链路样本 |
| default 0/0（初始化/回退痕迹） | 34 | n/a | **wasteful**（canary 19 + uuid 9 + aurora/run 6）——W-3 未关 |

代表性行证据（CSV rationale 列有全量）：

- 记忆修复实证：09-19 01:11 `我最喜欢的电影…帮我记住` 落 plus/3144 prompt（合并前）；合并后同类消息在判据探针 slim=True、balanced_fast=True、lane=fast（§4 探针表）。
- 错位实证（G-1）：09-22 16:03-16:27 考试冲刺会话 7/7 轮全落 FAST，其中 `帮我系统讲解一下二部图的判定定理，包括充要条件和证明思路`（**证明**=深度词）与 `帮我深入分析…详细对比和例题，要全面`（09-23 04:34）均为 L2 语义落 L1；09-20 16:08 文档引用问答（prompt 13870）落 FAST——早于 21451599（09-20 22:29）反指标修复，该具体洞已补。
- G-3 实证：`default` 0/0 行 request_id 前缀 `run_*`/`aurora_modeling_*`/`req_*` 三族并存（09-23 04:08 等样本）。
- G-4 实证：token_usage 全表无 minimax/glm_batch 行——E-06 batch 车道在 dev 无调用记录（车道未跑或未计账，二者皆为观测缺口）；全表也无 intent Layer3/sufficiency/HyDE/证据抽取行（C5 未关）。

## 3. L0–L3 准入判据（基于当前现状映射，不新建 router）

| 级 | 定义 | Entry 判据（现有机制落点） | 出口/退级 | 当前生效状态 |
|---|---|---|---|---|
| **L0 No-Model** | 确定性逻辑直答/写库，零 LLM | ① 空消息（_should_skip_llm_assist :560 直接 True，仅省 Layer3 不省生成）② memory_answer 命中（standard_workflow.py:981→:1505 短路）③ Layer1 explicit + 模板动作（:237）④ 记忆规则写入两车道（零 LLM）⑤ 记忆类轮次检索早退（retrieval_intent.py:400）⑥ plan review `_quick_rule_check` 自动批准（plan_review_service.py:271/:499）⑦ dual_core 模式决策+快捷道（dual_core_router.py:208；routing_engine.py:1409） | 判据不满足→L1 | 部分生效：②④⑤⑥⑦完好；**问候/确认仍走生成链**（G-2，complexity TRIVIAL delta 只降 tier 不跳过生成，llm_router.py:1157-1173） |
| **L1 Fast Semantic** | FAST tier 单次轻调用（thinking off） | ① fast first touch（:248，reasoning_mode=fast ∧ standard chat ∧ STANDARD_RESPONSE）② balanced fast path（:266，balanced ∧ slim :2792 ∧ ≤120字 ∧ 无深度词）③ intent∈{QUICK_QUERY,SIMPLE_CHAT,ROUTING,RETRIEVAL} 首位 FAST（llm_router.py:529）④ **记忆类轮次**（capability_lane.py:203+349-364 memory_*_fast_lane；retrieval_intent 根修保证 slim 不被否决）► 新 | 文档/工具/深度需要→L2；用户显式 deep→L2 | **主路径已生效**（09-20 起 uuid 聊天 44/44 落 FAST）；E-02 lane 遥测对齐（CHAT_CAPABILITY_LANE_TOTAL，metrics.py:707，lane=fast≈L1） |
| **L2 Deliberate** | standard/plus/pro 层 thinking on，多源上下文/工具 | ① deep_analysis 显式档强制 MAX（:141-158，DEEP_ANALYSIS_FORCE_FAST_TIER 逃生阀默认关）② phase_d 强制 tier（capability_selection_policy.py:46-51 cost_band→tiers，:652 _select_model；经 session_state_mixin.py:292/:385 写回）③ complexity COMPLEX+ delta +1（complexity_analyzer.py:154-161）④ deep mode preferred 链 [PRO,PLUS,STANDARD]（llm_router.py:521-527）⑤ 文档级检索/专家协作/planned_tool_sequence 一票否决 fast（capability_lane.py:296-343；standard_workflow.py:2812） | 工具多步编排→L3 | 判据齐全，但 **phase_d 分支先于深度词否决执行**（:1546 早于 :1566），sprint 低 cost_band 可把深词轮压到 FAST（G-1 错位） |
| **L3 Agent Run** | 多步工具执行/规划编排/跨模型复核 | ① planning_workflow（澄清→生成→审查→执行）+ 考试冲刺 fast track（planning_workflow.py:142/:312-377；orchestrator.py:713/:2920）② tool_execution_node（standard_workflow.py:2316）+ planned_tool_sequence 写入（:3432-3452，仅 exam_preparation/task_decomposition/skill_building 三 intent）③ plan review 跨模型复核门（model_fallback_service.py:414-425 deep/balanced 分级）④ 异步 batch 车道（batch_worklane.py，reflection/aggregation/analytics 三类，GLM_BATCH tier 隔离）► 新 | — | 已有；review 前置规则门即 L0 gate。**batch 车道 dev 无调用记录**（§2），上线后需按 §5 M-5 核对 |

**与 dual_core 的关系（v1 结论维持）**：dual_core mode（认知调制轴，execution/balanced/cognitive_first）不选 L 级；本窗口 routing_decision_log 分布 execution_first:balanced:cognitive_first ≈ 87:25:3（09-20→09-24）。两轴正交，不合并。

**与 tier 的关系（v1 结论维持 + B-05 复核）**：L0=跳过生成（非 tier）；L1=FAST；L2=STANDARD/PLUS/PRO；L3=编排。qwen3.8-flash 全 tier 同底层模型（B-05 capability_matrix：fast/standard/reason 实际同模型，仅 thinking 开关差异）→ L1↔L2 的真实差 = thinking token + TTFT，错位的代价主要是延迟与计费口径，不是能力断崖。TOP 层 glm-5.1 仍为死配置（B-05：ZHIPU 401，B-05b 轮换后 coding 端点 glm-5.3-flash 只进 batch/coding 车道）。

## 4. fast path 不退化验证（证据清单）

**探针（当前 HEAD 实跑，零 LLM，dev env inline）：**

| 消息 | lane | trigger | slim | balanced_fast |
|---|---|---|---|---|
| 我最喜欢的电影是《星际穿越》，帮我记住这个 | fast | memory_instruction_fast_lane | True | True |
| 我喜欢的电影是什么？ | fast | memory_query_fast_lane | True | True |
| 你好 | fast | light_standard_reply | True | True |
| 帮我深入分析欧拉回路和哈密顿回路的判定条件差异，给出详细对比和例题，要全面 | deliberate | deep_marker_text | True | False |
| 一句话回答：什么是图的度数？ | fast | light_standard_reply | True | True |

（v1 的 W-1 破点对照：同两条记忆消息在 0ea1e198 基线为 graph_only/targeted_source_rag → slim=False。根修=retrieval_intent.py:400-409 + slim 第二道防线 :2801-2811，实测已翻转。）

**定向测试（worktree 内实跑，非静态断言；命令与数字见 REPORT §测试证据）：**

- `test_capability_lane.py`（61）＋ `test_unified_intent_router_fast_path.py`（2）＋ `test_unified_intent_router_fast_path_first_message.py`（5）＝ **68 passed**
- `test_standard_workflow_generation_routing.py`（27，含 recent_memory 零LLM 直答/balanced 轻量强制 FAST）＋ `test_deep_analysis_tier_routing.py`（6，F-1 MAX 强制）＋ `test_llm_router_free_tier.py`（14，免费层钳制）＋ `test_retrieval_intent_classifier.py`（27，memory_class_turn 早退）＝ **74 passed**
- 合计 **142 passed / 0 failed**（环境性注意：5 个 tier 断言用例依赖 dev env 的 `LLM_TIER_*` inline 注入，worktree 无 .env 属预期，与 E-02 报告 §1 结论一致）。

## 5. metrics 口径（v1 §5 逐项对账 + 增量）

1. 每级调用占比：`CHAT_CAPABILITY_LANE_TOTAL`（metrics.py:707）已落（lane=fast≈L1、deliberate≈L2/L3，trigger 封闭枚举）——**L0 无计数**（memory 直答/rule_fast_path 短路不经过 lane 判定）。缺口 M-1：ladder_level 统一 counter 仍缺（v1 建议，未实施）。
2. 隐藏调用比：无数据。C5 未关——Layer3/sufficiency/HyDE/planning/aurora_modeling/evidence extractor 都不进 token_usage；本卡新增实证：`aurora_modeling_*` 车道 8 条有 token 消耗、无消息对应（CSV）。
3. wasteful 率：default 0/0 行在合并后窗口 34/132（25.8%口径含 canary；纯 uuid 聊天口径 9/53）——W-3/G-3 修后应≈0。
4. 每级时延：未复核（LIGHT 卡不做压测）；B-05 SLO 基线（fast TTFT p50 440ms）为 L1 参照。
5. batch 车道成本单列：BATCH_LANE_* 指标族已在 batch_worklane.py 引入；dev 无调用记录（G-6），上线后首个样本需核对 CostCategory.GLM_BATCH 独立桶。
6. M-6（新）：canary（`ns001-*`）调用建议在 metrics/request 侧打 `traffic_class=canary` 标签——当前金丝雀与真实用户流量在 token_usage 无法区分，污染 L1 占比与 wasteful 率分母（本窗口 46/98=47% 为金丝雀）。

## 6. 缺口与错位清单（当前态，按影响排序；映射卡不改码，挂钩点供修复卡引用）

| # | 类型 | 描述 | 挂钩点（file:line） | 证据 |
|---|---|---|---|---|
| G-1 | **错位** | phase_d 强制 tier（cost_band=low→[FAST,STANDARD]）在分支序上先于 balanced fast path 的深度词否决，sprint 会话内深词轮（系统讲解/证明/深入分析/全面）落 L1 thinking-off | generation_node 分支序 standard_workflow.py:1546-1582（phase_d 在 :1546，深度词否决只在 :1566 分支内）；tier 偏好表 capability_selection_policy.py:46-51 | 09-22 16:03-16:27 sprint 7/7 轮 FAST 含"证明思路"轮；09-23 04:34"深入分析…详细对比"FAST（CSV） |
| G-2 | 缺口（W-2 沿袭） | TRIVIAL 问候/确认仍走完整生成链（L0 直答缺失）；context 包对 TRIVIAL 无空档 | 生成入口 standard_workflow.py:1505 前无 greeting 模板分支；complexity_analyzer.py:85-92（TRIVIAL 判定已有） | 探针"你好"=light_standard_reply（仍生成）；v1 W-2 未关 |
| G-3 | 缺口（W-3 沿袭） | default 配置 0/0 token 调用仍计账（34 条/合并后窗口），request_id 前缀 run_*/aurora_modeling_*/req_* 三族 | llm_router.py:842 default ModelConfig；:1118/:1217/:1450/:1514/:1789 兜底点 | CSV 34 行 wasteful |
| G-4 | 缺口+死配置 | 证据链每 turn 隐藏 LLM 抽取默认开启（SPARKLE_LLM_EXTRACTOR_ENABLED=True，config/settings.py:947）且模型 `claude-haiku-4-5`（:965）不在 provider 注册表（llm_router.py:47-55 无 anthropic；B-05 matrix 无 anthropic 凭据）→ 每 turn 必败调用后静默规则回退，且不计 token_usage | chat_signal_collector.py:216-228；conversational_extractor.extract（fallback=extract_rule_based）；orchestrator.py:3842 finalize 后台任务 | 读码 + settings 默认值 + B-05 matrix；建议：关默认/换注册模型/落 token_tracker（C5 同族） |
| G-5 | 观测缺口（C5 沿袭） | 隐藏调用（Layer3/sufficiency/HyDE/planning/aurora_modeling/evidence extractor）不进 token_usage；context_pack_runs.request_id 回填仍未实施（本窗口 planning intent 17 run 无 usage 对照） | 同 v1 C5 建议；lane counter（Prometheus）无 DB 持久化，dev 无每日 lane 分布可查 | §2/§5；aurora_modeling 8 条 CSV 行 |
| G-6 | 观测缺口 | E-06 batch 车道合并后 dev 零调用记录——无法证真"异步分析已走 batch"（W-4 的收口验证缺样本） | batch_worklane.py 调度入口；BATCH_LANE_DISPATCH_TOTAL | token_usage 全表无 minimax/glm_batch |
| G-7 | 配置错位 | dev `LLM_TIER_PRO=dashscope_standard_thinking,glm_4_7_pro`：PRO 层实际是 standard 档模型，token_usage tier 记账与能力语义错位（B-05②③已证 tier 标签按代码注册位）；TOP 层 glm_5.1 死配置仍注册 | llm_router.py:_override_tier_mapping_from_env :1048；:842 起 default/TOP 注册 | dev .env 只读核查 + B-05 probe |

## 7. 收敛项状态对账（v1 C1-C6 → 当前）

- **C1（记忆级流量归 L1）**：✅ 由 E-02 收口（classifier 根修 + slim 二道防线 + lane 遥测），行为面 09-20 起实证关闭。
- **C1-探针**：✅ E-02 §2 完成（破点= retrieval_intent 误判 graph_only/targeted_source_rag；PLUS 跳档=env tier 覆盖 + 健康跳过 + 代码注册 tier 记账）。
- **C2（TRIVIAL L0 直答）**：❌ 未实施（G-2）。
- **C3（default 隔离为 error 事件）**：❌ 未实施（G-3）。
- **C4（评测/离线迁 batch）**：◐ 机制已备（E-06 batch_worklane + BATCH_LLM_PROVIDER=minimax），dev 无样本（G-6）；deepeval/deepqe 直出层迁移未见专卡收口。
- **C5（隐藏调用埋点）**：❌ 未实施（G-5），新增 aurora_modeling 与 evidence extractor 两个具体落点。
- **C6（记忆 semantic_key 归一）**：非本卡范围，仍登记记忆线。
