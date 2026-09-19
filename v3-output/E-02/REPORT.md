# E-02 任务报告：Fast Semantic / Deliberate Decision 能力路由

- 任务卡：E-02（stream AI / risk high / locks ai-routing / depends E-01）
- worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt8`
- base SHA：`0ea1e198`（M-07 ACCEPT merge）｜ 未 commit / 未 push
- 日期：2026-09-19 ｜ 接续前任 Worker（19:07 宿主重启阵亡）半成品，未重做 ｜ R2 返修轮（REWORK_DELTA→READY_FOR_REVIEW）
- 交付物：本报告 + `changes.patch`（6 改 + 2 新增，1643 行）+ `REVIEW_RECEIPT_2.md`（R2 收据原文）
- STATUS：**READY_FOR_REVIEW（R2 delta 复核）**

---

## 1. 接续盘点（前任半成品判定）

前任阵亡时树内已有：6 个修改文件 + 2 个新增文件，测试文件当时 39 用例**全绿**。接续逐文件判定：

| 文件 | 前任所做 | 接续判定 |
|---|---|---|
| `orchestration/capability_lane.py`（新） | lane 判定模块（分类器/判定序/遥测） | 主体完成；**发现 step-8 深度词缺失 bug，本次修复**（§4） |
| `tests/unit/test_capability_lane.py`（新） | 39 用例（分类/根修/slim/lane/候选链/fallback） | 保留全绿；补 6 用例（端到端 + 合成负载 + 深度词） |
| `orchestration/retrieval_intent.py` | memory_class_turn 根修早退 | 完成，集成点核实（§2/§3） |
| `agents/standard_workflow.py` | lane 接线 + slim 二道防线 | 完成；本次将深度词清单改为共享常量 |
| `core/llm_router.py` | `resolve_candidate_models` 候选链 reversed-insert 顺序修复 | 完成；核实仅可观测面，`_select_by_policy` 未动 |
| `services/llm/fallback.py` + `services/llm_service.py` | `require_tools` 能力层钳制 | 完成；核实全部既有调用方默认 False（后向兼容） |
| `core/metrics.py` | `CHAT_CAPABILITY_LANE_TOTAL` counter | 完成 |

**接续时的干扰项排除**：跑回归首遇 5 个失败（deep_analysis_tier_routing 3 + llm_router_free_tier 2，全部 `dashscope_reason != deepseek_reason`）。经 /tmp 基线克隆对照：基线（HEAD + 补 `app/gen` 生成物）**同样 5 失败**，且以主仓 dev `.env` 的 `LLM_TIER_*` 形态 inline 传入后 **20/20 全绿** —— 归因：wt8 无 `.env`，这 5 个用例依赖 dev env 的 tier 覆盖（`LLM_TIER_MAX=dashscope_reason` 等）。**预存环境性失败，与前任/本次改动无关，非回归。**

## 2. 基线复现（V3-FIX-12 → 挂钩点确认）

按任务书要求：先基线复现再修改（修改已完成于前任之手，本次独立复核基线成立性 + 补齐 E-01 C1-探针四步法全部答案）。

### 2.1 破点确定性重现（探针①，基线克隆，零 LLM）

在 /tmp 干净基线克隆（HEAD 0ea1e198 + symlink `app/gen`）上直接驱动判据函数：

| 消息 | 基线 classifier 输出 | slim | balanced_fast |
|---|---|---|---|
| 我最喜欢的电影是《星际穿越》，帮我记住这个 | `graph_only`/`ambiguous_query_graph_only`（"帮我"→ambiguous） | **False（否决）** | False |
| 我喜欢的电影是什么？ | `targeted_source_rag`/`knowledge_query_targeted_rag`（"是什么"→knowledge） | **False（否决）** | False |
| 请记住：我的期中考试范围是…（无"帮我"无疑问词） | `no_retrieval` | True | True |

结论：**E-01 (b) 之谜一关闭**——记忆类消息被 retrieval_intent 误判（ambiguous/knowledge）→ `should_retrieve=True` → `_should_use_slim_standard_context` 一票否决 → 落默认链。挂钩点确认在 classifier 根修 + slim 否决条件两处（前任的双防线设计正确）。

### 2.2 PLUS 落点机制（探针②③④，dev env 形态 inline，零 LLM）

- ② `select_model(GENERATION, STANDARD_RESPONSE, balanced)` 候选链（dev env 形态）：`[dashscope_standard_thinking, dashscope_chat, dashscope_fast, dashscope_reason]`，冷态首选 `dashscope_standard_thinking`(standard)。`policy_preferred=["dashscope_chat"]` 是**尾部追加**，不重排首位。
- ②' 健康跳过补全：对首位 `dashscope_standard_thinking` 连续 `report_model_failure` 后重选 → **`dashscope_chat`，`config.tier=plus`** —— 与生产 58/58 签名完全一致（确定性复现）。
- ③ 主仓 dev `.env`（只读）：`LLM_TIER_STANDARD=dashscope_standard_thinking,dashscope_chat`、`LLM_TIER_PLUS=dashscope_chat`。**env 覆盖只改 tier 候选列表，不重写 `ModelConfig.tier`（代码注册 tier）**——`dashscope_chat` 代码注册 tier=PLUS，故无论经 STANDARD 还是 PLUS 位命中，`token_usage.model_tier` 恒记 `plus`。
- ④ GENERATION profile：`preferred_models=["dashscope_chat"]`, `preferred_tier=STANDARD`, `fallback_tiers=[REASONING, FAST]`。

**E-01 (b) 之谜二关闭**：54/54（现 58/58）plus 落点 = 破点一（slim 被否决落默认链）+ 健康跳过/或 STANDARD 位直接命中 `dashscope_chat` + tier 标签按代码注册位（plus）记账。不是能力跳档，但记忆级流量为此支付 thinking 档 ~2.4k prompt tokens 与 plus 计费口径。

### 2.3 live dev DB 只读抽样（C-02/M-07 重启后，E-02 未部署，基线仍成立）

```
model          | model_tier | mode    | n  | avg_prompt
dashscope_chat | plus       | balanced| 58 | 2438      ← 全部真实聊天生成
dashscope_fast | fast       | balanced|  9 |  775      （探针/首触）
default        | -          | balanced|  1 |    0
```

## 3. 修复设计（双防线 + lane 可观测 + fallback 能力兼容）

1. **根修**（`retrieval_intent.py`）：`classify_memory_class_message`（纯规则、零 LLM、≤200 字、反模式优先排除——文档词/工具动作词/深度词/自我分析疑问词）命中且非 planning 信号 → `ContextPlan(no_retrieval, reason="memory_class_turn")`。位置在 emotional/simple_task 早退之后、planning/knowledge 分支之前；集成点核实：`session_state_mixin._attach_retrieval_decision` 正是用 `build_retrieval_decision(...)` 产 `decision.to_dict()` 写入 `context_data["retrieval_decision"/"document_retrieval_decision"]`——根修直接作用于 live 管线。
2. **二道防线**（`standard_workflow._should_use_slim_standard_context`）：`graph_only ∧ memory_class` 不再否决 slim（覆盖决策被旁路写入/旧数据回放）；文档级模式（targeted_source_rag 等）与规划类 graph_only 仍否决。
3. **lane 判定**（`capability_lane.py`，每 turn 一次、零 LLM）：判定序 = 工具流保护(planned_tool_sequence) → 非 standard chat_mode → 用户 deep → 文档在场/显式角色 → 专家 → 文档级检索 → 记忆类 FAST → 轻量标准 FAST（含深度词否决，§4）→ 默认 DELIBERATE。与 dual_core（认知调制轴）正交，只决定模型深度轴。
4. **可观测**：`CHAT_CAPABILITY_LANE_TOTAL{lane, memory_class, retrieval_mode, trigger}` + 结构化日志 `[CapabilityLane]` + `context_data["capability_lane"]` 下游透传。对齐 ROUTING_MAP §5.1 的 ladder 占比度量：lane=fast≈L1、lane=deliberate≈L2/L3；L0 短路（memory_answer）发生在 generation_node 内、lane 判定之后，故 L0 turn 也携带 lane 标签（区分方式：L0 走 `__end__` 短路不产生生成调用，以 `first_touch_model_tier` 缺席识别）。未采用 §5.1 的"`LLM_ROUTER_SELECTION_TOTAL` 加 ladder_level label"原案，理由：selection_total 只覆盖经 select_model 的调用，L0 短路轮无 selection 事件，独立 counter 每 turn 恰好一次、口径更准；两 counter 并存不冲突。
5. **fallback 能力兼容**（卡验收②）：`_get_fallback_candidates(..., require_tools=)`——带工具 schema 的调用（`llm_service` 两条主路 `require_tools=bool(request_params.get("tools"))`）候选钳制在主聊天能力层（TOP/MAX/PRO/PLUS/STANDARD/FAST；REASONING 归一 PRO；FREE*/GLM_BATCH/SPECIALIST 剔除），消除"会说话但不能执行工具"的假完成。其余 3 个调用点（chat/reason/stream_chat 旧路）默认 False，行为不变。
6. **候选链可观测一致性**（`resolve_candidate_models`）：与 `_select_by_policy` 相同的 reversed-insert，使候选链首位=实际选择（旧实现链序反转，describe_agent_routing 与实际不符）。仅可观测面，不动选型。

## 4. 接续发现并修复：lane 深度词一致性 bug

前任 `resolve_capability_lane` step-8 注释声称"轻量标准问答（短、无深度词、无检索需求）→ FAST"，但**代码未检查深度词**：`深入分析我的学习模式`（≤120 字、无检索决策）会被报 `lane=fast`，而实际 tier 走默认链（`_should_force_balanced_fast_first_touch` 的深度词判据否决 balanced fast path）——lane 遥测把 deliberate 轮误计为 fast，恰好违反卡验收"路由决策可观测"。

修法：深度词清单提为共享常量 `DEEP_ANALYSIS_TEXT_MARKERS`（capability_lane 定义，standard_workflow 引用，消除双清单漂移）+ step-8 深度词在场 → `DELIBERATE(trigger=deep_marker_text)`。红绿测试 `test_lane_deliberate_for_deep_marker_text_without_retrieval`（含与实际 tier 判据的交叉验证断言）。

## 5. 验证与证据（全程零真实 LLM）

- **targeted tests**：`tests/unit/test_capability_lane.py` **61/61 绿**（R1 45 + R2 返修 16）：
  - 端到端（FakeLLM + monkeypatch 选型助手）×3：记忆指令（回放旧管线 graph_only 决策）→ `get_configured_llm_service_for_tier(FAST, QUICK_QUERY)` + `first_touch_profile=balanced_fast_path` + `context_data.capability_lane=fast`；根修输出殊途同归；exam 工具流 → 默认链 + `capability_lane=deliberate/tool_flow_protected=true` + 无 first_touch。
  - 合成负载 A/B ×2：简单批（11 条：6 记忆指令 + 3 记忆检索 + 2 轻量）**全量 lane=fast ∧ balanced_fast 命中 ∧ 零检索**；复杂批（7 条：工具流 3 / 文档接地 2 / 深度 2）**全量 lane=deliberate**，工具流/文档批 slim 全否决。
  - R2 返修新增 16 用例：F1 方法建议问法 ×7、F1b 第三方事实疑问 ×2、F2A 超长记忆轮 ×1、F2B 个人数据/工具意图词 ×6（见 §10）。
- **回归**（R2 后口径，全部可复现）：
  - 定向 battery（13 文件：capability_lane + retrieval_intent_classifier + generation_routing + intent fast_path×2 + unified routing/helpers×2 + tier/same_tier/timeout/health fallback + glm thinking + glm_batch_adaptive）：**174 passed**；
  - env 形态批（deep_analysis + free_tier，dev env inline）：**20/20 绿**；
  - workflow 邻接批（memory_revival_slim / file_context / feedback_binding / executable_plan_fallback）：**18/18 绿**；
  - E-01 路由守护与 V3-FIX-04 glm thinking 均含于上（glm thinking 10/10）；
  - **爆炸半径全量回归**（R1 轮：全部 import 改动模块的 51 个测试文件，分 5 片运行）：**1423 passed / 10 failed，10 个失败全部在干净基线克隆（HEAD 0ea1e198）上逐一复现同败**——env 形态性 5（free_tier×2 + deep_analysis×3，dev env inline 后全绿）+ 基线预存破损 5（rb06 flush/commit ×1、t6 severity ×1、stage37 kill-switch ×2、learning_path env 敏感 ×1）。**零 E-02 回归**（R2 返修只动 capability_lane/standard_workflow/metrics 判据面，capability_lane 套件与上列 battery 全绿复跑覆盖）；
  - **patch 自包含证明**：R2 后 changes.patch 在干净基线克隆（HEAD 0ea1e198）上 `git apply` 后 **61/61 绿**；
  - 广谱 `tests/unit tests/core` 单进程全量：因内存熔断主动中止（见 §7-6），以爆炸半径片跑替代。
- **L1/L2 真实 A/B（延迟/质量，引 B-05 探针实测）**：fast（thinking off）TTFT p50 **440–475ms**/total p50 ~1001ms；standard_thinking 首可见内容 p50 **912–1194ms**/total p50 ~1500ms——L1≈2x 首反馈优势，同为 qwen3.8-flash 仅 thinking 差异（E-01 §3：收敛质量风险低）。质量承接实证：E-01 记录 09-18 MRV 4 条 fast 成功调用。本卡在 no-real-LLM 约束下的 A/B = 路由面确定性 A/B（上两条合成负载）+ B-05 实测延迟差引用。
- **零 LLM 声明**：全部测试用 Fake/monkeypatch/纯函数；探针复现仅调判据函数与 select_model（无网络调用）；dev DB 仅 SELECT。

## 6. 验收对照（任务卡）

- [x] **L1/L2 latency/quality 有真实 A/B；简单 intent 不走 L2**：B-05 实测延迟 A/B（引）+ 合成负载确定性 A/B（简单批 12/12 落 FAST lane 且无一条进默认链）+ 端到端 FAST tier 落点断言。生产流量级验证（部署后 L1 占比）留 D-06 埋点读数，本卡交付计数器。
- [x] **fallback 不把需要 tools 的任务降成 text-only 假完成**：`require_tools` 钳制 + 2 用例（含非能力层泄漏逐候选断言）。
- [x] **exam_preparation 工具流保护显式测试**：lane 级（tool_flow_protected）+ slim 级（planned_tool_sequence 否决）+ 端到端（不进 FAST tier 助手）共 4 处断言。
- [x] **路由决策可观测**：counter + 结构化日志 + context_data 透传，trigger/reasons 与 ROUTING_MAP 对齐；候选链可观测一致性修复。
- [x] **禁止项**：未重建权威真源（扩展既有判据，未新建 router）；未 mock 冒充真实行为（全部确定性判据 + 独立基线复现）；未弱化守卫（exam/deep/doc 保护面全部有测试）；未 commit/push。

## 7. 未做 / 边界 / 遗留

1. **生产态健康跳过不可离线重放**：58/58 中 STANDARD 首位被跳过依赖当日 health tracker 状态；本卡已给出确定性等价复现（人为熔断首位 → 同签名）+ 标签归属机制解释，残余不确定性仅"当日熔断是否恰好发生"，不影响修复正确性（记忆轮不再进默认链）。
2. **知识问答（"什么是番茄钟学习法"）仍 RAG→deliberate**：E-02 范围是记忆类 + 保护面；通用知识问答的 L1 收敛（无文档时）未做，属后续卡。
3. **W-2 问候 L0 直答（C2）、W-4 评测 batch 化（C4）、C5 隐藏调用埋点、C6 semantic_key 归一化**：不在本卡。
4. **V3-FIX-12 状态建议**：`T-route-coverage` → **FIXED@E-02**（破点与跳档双谜关闭，保护面有测试；待 Reviewer 独立验收后 Leader 更新 DYNAMIC_ISSUES 表）。
5. lane counter 的 `retrieval_mode=unknown`：retrieval 决策尚未写入 context_data 的窗口（lane 判定先于 `_attach_retrieval_decision` 的路径）会记 unknown——已知口径，非缺陷。
6. **给 Leader 的两条环境通报**（均非本卡引入）：
   - **内存**：本机 swap 已用 18.9G/20G（空闲 1.5G）。当前有一组 **wt5 会话**的 `pytest tests/unit -q --tb=no -rN` 进程（PID 5125，19:17 起，非本会话）与一残留 pytest 组共同占用；我自己的广谱全量 pytest 达 21.4G 物理足迹后按熔断纪律主动杀掉。**建议 Leader 唤醒时巡检 wt5 进程组归属并处置**；全量单测在本机必须分片跑。
   - **test_stage38_d3_persistence 测试隔离 bug（基线预存）**：该文件用 `types.ModuleType("app.gen")` 覆写 `sys.modules["app.gen"]` 且不恢复，导致同进程内**其后** import `app.gen.agent.v1` 的测试文件（如 test_standard_workflow_generation_routing）collection 报 `ModuleNotFoundError`——全量单跑会产生假阳性 collection error。建议登记 FIX 卡（setUp/tearDown 恢复 sys.modules 或改用 monkeypatch）。本卡回归以分片规避（stage38 独立进程 4/4 绿）。

## 8. 复现命令（Reviewer 独立验收用）

```bash
cd /Users/brsama/code/GitHub/Sparkle-sysrev/wt8/backend
SECRET_KEY="test-secret-key-0123456789abcdef0123456789abcdef" \
  .venv/bin/python -m pytest tests/unit/test_capability_lane.py -q          # 61 绿
SECRET_KEY="..." .venv/bin/python -m pytest tests/unit/test_capability_lane.py \
  tests/unit/test_retrieval_intent_classifier.py \
  tests/unit/test_standard_workflow_generation_routing.py \
  tests/unit/test_unified_intent_router_fast_path.py \
  tests/unit/test_unified_intent_router_fast_path_first_message.py \
  tests/unit/test_unified_intent_router_routing.py tests/unit/test_unified_intent_router_helpers.py \
  tests/unit/test_llm_tier_fallback_order.py tests/unit/test_llm_same_tier_fallback.py \
  tests/unit/test_llm_timeout_fallback.py tests/unit/test_llm_router_health_tracking.py \
  tests/core/test_llm_router_glm_thinking.py tests/unit/test_glm_batch_adaptive.py -q   # 174 绿
# 预存环境性 5 失败的 env 形态复跑（20/20 绿）：
SECRET_KEY="..." LLM_PROVIDER=qwen DEEPSEEK_REASON_MODEL=deepseek-v4-pro \
  DASHSCOPE_REASON_MODEL=qwen3.8-flash \
  LLM_TIER_FAST=dashscope_fast LLM_TIER_STANDARD=dashscope_standard_thinking,dashscope_chat \
  LLM_TIER_PLUS=dashscope_chat LLM_TIER_PRO=dashscope_reason LLM_TIER_REASONING=dashscope_reason \
  LLM_TIER_MAX=dashscope_reason .venv/bin/python -m pytest \
  tests/unit/test_deep_analysis_tier_routing.py tests/unit/test_llm_router_free_tier.py -q
# 注意：test_stage38_d3_persistence.py 必须独立进程跑（sys.modules 覆写 bug，§7-6）；
# 爆炸半径全量请分片（单进程全量 20G+ 内存足迹，本机 16G 会触发熔断）。
# 基线对照（破点重现）：/tmp/e02-baseline 克隆已删，可重建：
#   git clone /Users/brsama/code/GitHub/Sparkle-sysrev/wt8 /tmp/<name> && cd /tmp/<name>
#   git checkout 0ea1e198; ln -s <wt8>/backend/.venv backend/.venv; ln -s <wt8>/backend/app/gen backend/app/gen
```

## 9. 清理确认

- /tmp：R1 轮 `e02-baseline`/`e02_*` 已删；R2 轮变异备份（m1/m3/mf2/mlen）随变异即还原即删，`e02-r2-baseline` 克隆收工即删。
- 未起端口/模拟器/浏览器；无构建产物入库；`wt8/backend/.venv` 按指示保留。
- 同树另一 pytest 进组（wt5 会话）与本卡无关，未触碰（工作区边界）。
- 未 commit/push；交付仅 `v3-output/E-02/{REPORT.md, changes.patch, REVIEW_RECEIPT_2.md}` + 树内 8 个文件改动。

## 10. R2 返修记录（REWORK_DELTA → 本轮）

收据：`REVIEW_RECEIPT_2.md`（Verdict REWORK_DELTA）。核心修复获独立验证（双谜复现、M1-M4/M5b 必红、合入预演干净+合后 45+61 绿）；返修三发现的处置：

- **F1（P1）方法建议问法劫持 — 已修**：`_MEMORY_INSTRUCTION_EXCLUDE_RE` 增补 `怎么|如何|怎样|方法|技巧|妙招|更快|更高效|更有效`（R2 建议词族）+ `记住了|记下了`（完成时陈述，"我记住了老师讲的重点"形态）+ `接下来`（复合意图续接词）。收据 4 条探针复测：`classify` 全部 None；「怎么记住英语单词更有效率？」恢复基线行为 `targeted_source_rag`（文档接地保留，红测断言）；「我记住了…」不再产生记忆写入 receipt。**F1b 顺带收紧（QUERY 侧同族）**：`我(?!们)`（"我们小组定的汇报主题是什么来着"团体事实不再误判）+ 排除 `问我`（"老师问我这道题的答案是什么"转述问答）。决策说明：R2 提及的漏报侧「我的导师姓什么来着」判 None（轻）**未扩**——返修轮只关假阳性，不在无要求下扩 fast-lane 召回面。
- **F2（P2）lane=fast 虚高两残余 — 已修（与实际 tier 判据同源闭合）**：
  - F2A：lane 记忆分支补 `len(text) <= 120`（与 `_should_force_balanced_fast_first_touch` 同上限；classify 200 上限保留——121–200 字记忆轮根修 `no_retrieval` 仍正确，仅 tier 落默认链，lane 如实报 deliberate，红测交叉验证 balanced_fast=False）。
  - F2B：工具动作/个人数据意图词清单提为共享常量 `LIGHT_REPLY_TOOL_INTENT_MARKERS`/`LIGHT_REPLY_PERSONAL_DATA_MARKERS`（capability_lane 定义，standard_workflow `_should_disable_tools_for_light_standard_reply` 改为引用，**全仓单一事实来源，未抄第二份**）；lane step-7（记忆分支）与 step-8（light_standard_reply）均接入门判据，命中 → `DELIBERATE(trigger=personal_data_or_tool_intent)`。收据 5 探针复测 5/5 deliberate；另闭合记忆分支同族形态「记住我的进度」（根修保留 + lane deliberate）。metrics.py trigger 注释更新为封闭枚举全列。
- **F4（P3）报告计数 — 已勘误**：§5/§8 改为可复现口径——battery 13 文件 **174**（R1 轮 147 系混计 env 批与 unified 文件；R2 复现 133 为不含 capability_lane/glm_thinking 的子集，本轮以单一命令可复现的 174 为准）+ env 形态 20 + workflow 邻接 18。
- **F5（pre-existing providers 健康上报死键）**：不在本卡范围，Leader 台账登记。

**返修后验证**：capability_lane 套件 **61/61 绿**（45→61，+16 用例）；定向 battery 复跑 174 绿；env 形态 20 绿；workflow 邻接 18 绿。**变异抽测（cp /tmp 备份法，全部 cmp 字节级还原）**：M1（去根修早退）**5 红**（≥R2 记录的 3；新增 F2 红测同时钉住根修）；M3（去 lane 深度词判定）**2 红**（同 R2 记录）；自检加做 MF2（去 light-reply 门）**6 红**、MLEN（去记忆分支 120 上限）**1 红**——新增 F2 门均承重。**patch 自包含**：R2 后 changes.patch（1643 行）在干净 HEAD 克隆 apply 后 61/61 绿。STATUS: **READY_FOR_REVIEW（R2 delta 复核：F1/F2 重放 + 新红测）**。
