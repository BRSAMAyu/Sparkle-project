# E-02 R2 深层验收收据（DeepAudit 路线）

- 审计员：R2（wt8 独占，DeepAudit）
- 对象：E-02「Fast Semantic / Deliberate Decision 能力路由」交付（8 文件 1315 行，未 commit）
- 基准：wt8 HEAD 0ea1e198 ｜ 主仓参照 cba29db1（03e23023 仅追加 handoff 文档，无代码）
- 方法：全量 diff 审读 + /tmp 基线克隆对照（浅克隆已删）+ 确定性探针（零 LLM）+ 6 组变异（cp /tmp 备份法，全部字节级还原校验）+ 合入预演克隆 apply + dev DB 只读 SELECT
- 复跑环境足迹：全程分片/单文件，未触发熔断；/tmp 三个克隆与备份目录收工即删

## 总 Verdict：REWORK_DELTA（小修后可过，禁止本轮直接 ACCEPT）

根修位置、双防线结构、保护面、fallback 钳制、候选链修复、合入干净度**全部独立验证成立**；但根修分类器判据过宽，把「方法建议类」高频问法劫持进 memory_class_turn，相对基线构成**产品语义级回归**（测试全绿掩盖）。修复面窄（排除词 + 测试），修完补跑即过。

---

## 风险面 1：路由语义正确性（memory_class_turn 判据封闭性）— Verdict: **FAIL（P1）**

### F1（P1，Confirmed defect）：方法建议类问题被劫持为记忆轮次

- **机制**：`_MEMORY_INSTRUCTION_RE = (请)?(帮我)?(记一下|记住|记着|记下来|别忘了|不要忘记)` 两个前缀全部可选，核心动词在**文本任意位置**裸匹配；`_MEMORY_INSTRUCTION_EXCLUDE_RE` 无疑问词/方法词排除。模块 docstring 自己写明「怎么/如何（方法建议）——需要 deliberate」却只在 QUERY 侧排除了此类，INSTRUCTION 侧漏排。
- **证据（确定性探针，wt8 vs 基线克隆 HEAD 0ea1e198）**：

| 消息 | 基线（HEAD） | E-02 修复后 |
|---|---|---|
| 怎么记住英语单词更有效率？ | targeted_source_rag（文档接地） | **memory_class_turn / no_retrieval** + receipt「这是关于你自己的记忆，我直接用已记住的内容回答」 |
| 如何记住复杂的化学公式？ | targeted_source_rag | memory_class_turn / no_retrieval |
| 有什么记住历史年代的好方法 | no_retrieval（无 receipt） | memory_class_turn + 误导性 receipt |
| 我记住了老师讲的重点，接下来该做什么 | no_retrieval | memory_class_turn（过去时陈述句误判指令） |

- **落点链**：no_retrieval → slim 放行 → `_should_force_balanced_fast_first_touch` 命中 → FAST tier + QUICK_QUERY（thinking off）。即：基线走文档 RAG + thinking 档的知识/方法问题，修复后变成**无检索 + 快答档 + 误导 receipt** 的记忆轮。对大学生学习产品，「怎么记住/如何记住/有什么记住…的方法」是核心高频问法族。
- **次级同族（F1b）**：QUERY 侧 `我.{0,24}(是什么…)` 宽窗捕获第三方事实（实测「我们小组定的汇报主题是什么来着」「老师问我这道题的答案是什么」均判 memory_retrieval_query → no_retrieval），记忆系统无此数据，答案质量降级。漏报侧「我的导师姓什么来着」判 None（轻）。
- **为何测试全绿**：45 用例的全部正/负样本均为祈使句/第一人称疑问句设计，无一探针疑问词+记忆动词组合。
- **修法（最小）**：`_MEMORY_INSTRUCTION_EXCLUDE_RE` 增补 `怎么|如何|怎样|方法|技巧|妙招|更快|更高效|更有效`（对齐 QUERY 侧已有的同类排除哲学）+ 补 3–4 条红测（含「怎么记住…」「我记住了…」两形态）。

### 双谜基线复现 — Verdict: **PASS**

- 谜一：基线克隆实测「帮我记住…」→ graph_only/ambiguous_query_graph_only、「…是什么」→ targeted_source_rag/knowledge_query_targeted_source_rag，与 REPORT §2.1 完全一致。
- 谜二：env 形态下候选链 `[dashscope_standard_thinking, dashscope_chat, dashscope_fast, dashscope_reason]`、首位 config.tier=standard；对 model_key `dashscope_standard_thinking` 连续 report_model_failure 后重选 = **dashscope_chat / config.tier=plus** —— plus 签名确定性复现成立。「人为熔断首位」的代表性残余不确定性（当日熔断是否发生）Worker 已如实声明，且 dev DB 只读复核（30h 窗口）：dashscope_chat/plus/balanced 现 **150 行** avg_prompt 2488（Worker 快照 58 行后量级持续放大），基线仍成立。

## 风险面 2：lane 遥测保真 — Verdict: **PARTIAL FAIL（P2）**

- **同源声明成立**：`DEEP_ANALYSIS_TEXT_MARKERS` 为 import 引用（standard_workflow.py:56 ← capability_lane.py:93），全仓无第三份副本，深度词轴漂移已消。
- **F2（P2，Confirmed defect）：lane=fast 虚高的两个残余形态**（与 Worker 已修的深度词形态同类，REPORT §4「lane 可观测须与实际 tier 判据同源」只在深度词轴闭合）：
  - **形态 A（长度窗分歧）**：`classify_memory_class_message` 上限 200 字、`_should_force_balanced_fast_first_touch` 上限 120 字、lane 记忆分支无长度检查。实测 137 字记忆指令：lane=fast/memory_instruction_fast_lane，实际 fast_tier=False（默认链）。
  - **形态 B（关键词分歧）**：lane 第 8 步 light_standard_reply 不查 `_should_disable_tools_for_light_standard_reply` 的 40+ 个 personal_data/tool 关键词。实测「聊聊我的进度吧」「看看我的知识星图」「根据我的情况给点建议」「查一下我的错题」「我的画像准不准」5/5 全部分歧：lane=fast，实际默认链。
- **影响**：`CHAT_CAPABILITY_LANE_TOTAL` 是 D-06 L1 占比度量的数据源，两形态同向系统性高估 L1。修法：lane 记忆分支补 120 字上限；light_standard_reply 分支复用/共享 `_should_disable_tools_for_light_standard_reply` 判据（或其关键词常量）。

## 风险面 3：熔断/fallback 面 — Verdict: **PASS**

- `require_tools` 语义核实：`_tier_allows_tools` 经 `_normalize_tier_value`（REASONING→PRO、FREE_REASONING→FREE_FAST）后落在 `_CAPABILITY_TIER_RANK`（TOP/MAX/PRO/PLUS/STANDARD/FAST），FREE*/GLM_BATCH/SPECIALIST 剔除——与声明一致。
- 覆盖面核实：三个带工具 schema 的内部调用点（chat_with_tools/continue_with_tool_results/chat_stream_with_tools）全部经 `_create_raw_completion_with_fallback` / `_create_raw_stream_with_fallback` 两个带 `require_tools=bool(request_params.get("tools"))` 的入口；遗留 3 调用点（chat/reason/stream_chat）为纯文本路径，默认 False 不留洞。
- 候选链 reversed-insert 与 `_select_by_policy`（llm_router.py:1153-1163）逐行同构，可观测一致性修复成立；测试断言 candidates[0]==selection.model_key 双场景验证。
- counter 标签词表封闭（trigger ∈ reasons 首位，reasons 为代码内封闭枚举集）。

## 风险面 4：测试语义真实性（变异 6 组）— Verdict: **PASS（含 1 项冗余说明）**

| 变异 | 内容 | 结果 |
|---|---|---|
| M1 | 去 retrieval_intent memory_class 根修早退 | **3 failed 必红** ✓ |
| M2 | 去 slim 二道防线（恢复一票否决） | **4 failed 必红**（含端到端）✓ |
| M3 | 去 lane 深度词判定 | **2 failed 必红** ✓ |
| M4 | 去 fallback require_tools 钳制（恒 True） | **1 failed 必红**（恰为 require_tools 用例）✓ |
| M5a | 去 slim 层 planned_tool_sequence 否决 | 45 全绿——**非测试造假**：`_should_disable_tools_for_light_standard_reply` 内部同判据双保险，行为仍受保护（F3 记录） |
| M5b | 去 lane 层工具流优先保护 | **3 failed 必红**（lane+端到端+合成批）✓ |

任务书指定 4 组变异（根修/slim/深度词/require_tools）全部必红；exam 保护变异必红。全部还原经 `cmp` 字节级校验，树状态与交付一致。

## 风险面 5：回归归因抽检 — Verdict: **PASS（含 1 项计数勘误）**

- 基线克隆（HEAD 0ea1e198，无补丁）复现抽检 8/10 失败同败：stage37 kill-switch ×2、learning_path ×1、deep_analysis ×3、free_tier ×2（rb06/t6 未抽，Worker 逐一记录在案）。env 形态 inline 后 deep_analysis+free_tier **20/20 绿**——归因成立。
- V3-FIX-04：`test_llm_router_glm_thinking.py` + `test_glm_batch_adaptive.py` wt8 复跑 **10/10 绿** ✓。
- 45/45 复跑绿；定向 battery 复跑全绿（97 listed + 16 unified + 20 env = 133）。
- **F4（P3）**：REPORT §5「147 passed」/§8 注「122 绿」与实际可复现数（97/133）不吻合，疑把 env 批与 unified 两文件混计。绿性成立，计数口径不严，Leader 对账时以 133 为准。

## 风险面 6：合入预演 — Verdict: **PASS**

- 主仓克隆 @ cba29db1：`git apply --3way --check` **exit 0**（6 文件 cleanly，2 新文件 direct apply）；真实 apply 后 **45/45 绿** + 路由守卫 61 绿。
- 四连合入（C-03/M-04/FIX-08/FIX-09，0ea1e198→cba29db1）对 E-02 六个触碰文件**零改动**（仅新增 business_metrics.py，其 `get_or_create_metric` 为独立模块私有 helper，与 `sparkle_chat_capability_lane_total` 无注册冲突）——协调方预警的 llm_router/llm_service 交集实测为空。

## 附带观察（非本卡引入，转 Leader）

- **F5（P3，pre-existing）**：`report_model_failure` docstring 称由 providers.py 调用（传 model_name），而 `_is_model_healthy`/选型跳过按 model_key 查——除 fallback 管理器路径外，providers 上报的健康态在选型侧是死键。影响生产「健康跳过」频率的解读口径，建议登记。
- REPORT §7-6 的 stage38 `sys.modules["app.gen"]` 覆写不恢复问题属实（我方分片复现该文件须独立进程），同意登记 FIX 卡。

## 发现汇总

| # | 级别 | 一句话 | 处置 |
|---|---|---|---|
| F1 | P1 | 「怎么记住/如何记住…」方法建议族被 memory_class_turn 劫持：丢文档 RAG+误 receipt+降快答档（基线对照实锤回归） | Rework 必修 |
| F2 | P2 | lane=fast 虚高两形态（121–200 字记忆轮 / personal-data 关键词轮），污染 D-06 L1 度量 | Rework 修（可与 F1 同批） |
| F3 | P3 | slim 层 planned_tool 否决变异不红系双保险冗余，非测试造假 | 记录 |
| F4 | P3 | battery 计数 147/122 与实际 133 不吻合 | 报告勘误 |
| F5 | P3 | providers 按 model_name 上报健康 vs 选型按 model_key 查（pre-existing） | 转 Leader 登记 |

## 结论

REWORK_DELTA 范围（建议一次小 patch 完成）：F1 排除词族 + 红测 3–4 条；F2 两形态判据统一（lane 记忆分支 120 上限 + light_standard_reply 复用 light-reply 判据）。修后复跑：test_capability_lane.py（应 ≥49）+ 定向 battery + 变异 M1/M3 抽测。其余面（保护/合入/回归归因/FIX-04）已达标，无需返工。
