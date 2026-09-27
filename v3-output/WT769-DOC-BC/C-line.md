# C 线（Context 8 卡）深挖章节 —— V4 交接文档素材（wt769）

> 本文是 `v3/V3-COMPLETE-STATUS-FOR-V4.md` §4「各线深度状态」C 线章节的深挖草稿。
> 证据纪律：只写三源证据（git 主干 SHA / 独立审查 receipt / 运行级实测）支撑的事实；逐条标注出处；无法定位证据的验收项显式标注「未定位到证据」。
> 撰写：wt769（2026-09-28，基线 main@b129040c）。方法：卡面（v3/07_tasks/cards/C-0*.md）+ `git log --grep` 逐卡定位 → 当前主干代码存在性与生产消费方逐一开文件核实（grep import/call 面）→ 测试文件逐个计数 → v3-output receipts 抽读 → 台账闭环复核。**未轻信任何台账/报告结论性文字。**

---

## C.0 线级概览

C 线把「模型每次决策看到什么」变成受控工程：契约定死（C-01）→ 来源四分（C-02）→ 合法性前置过滤（C-03）→ 引用正确性（C-04）→ 冲突事实注入（C-05）→ 预算与压缩（C-06）→ 缓存版本正确性（C-07）→ 漏斗可观测与效用消融（C-08）。8/8 全部 done（tasks.json + fleet done + wt759 三源核验报告 v3-output/WT759-RECON/report.md:57-64 逐卡 SHA 在案），交付窗口 2026-09-19～09-21，全部合入主干。

**当前主干接线面核实（本次逐一 grep 亲证，这是 C 线区别于纯审计线的核心事实）**：10 个 C 线新增模块全部有生产消费方，且存在跨卡复用网——`decision_context.py`（416 行）被 context_pack/aurora_decision/action_plan/lang_graph_planner 等 10 文件消费；`context_sources.py`（1124 行）被 context_pack/decision_context/context_builder/orchestrator 消费；`context_retrieval_pipeline.py`（745 行）被 graph_rag/galaxy/retrieval_service/business_metrics 消费；`citation_markers.py` 被 knowledge_jit/context_pack/standard_workflow/**hybrid_journey_service**（J-06 旗舰旅程用它做确定性引用核对，无引用/越集引用 503 诚实失败——`7bd6ade3`）消费；`context_cache_key.py` 被 knowledge_jit/context_budget_matrix/context_builder/memory_settings_service 消费；`context_funnel.py` 被 standard_workflow/context_builder/business_metrics 消费（3 处 metadata-only 接线）。**C 线不是 frozen-on-paper 契约，是活的基础设施。**

**测试规模（本次逐文件 `def test_` 计数）**：13 个测试文件合计 **235 个测试函数**——契约面 test_decision_context_contract.py 21、来源面 test_context_sources.py 34 + test_context_source_contract.py 12 + test_context_pack_sources.py 4、检索面 test_context_retrieval_pipeline.py 29 + perf 1 + hard_filter_wiring 7、引用面 test_citation_markers.py 16、冲突面 test_conflict_resolution_context.py 23、预算压缩面 test_c06_context_budget_compaction.py 20、缓存面 test_context_cache_versioning.py 24、漏斗面 test_context_funnel.py 27 + context_eval gate 17。

**审查证据形态说明**：C-01/02/03 有独立 receipt 文件（v3-output/C-01/×2、C-02/×3、C-03/×2）；C-04～C-08 处于「ACCEPT merge 时代」，独立审查结论以提交信息载体记录（dual-review/R2 PASS/reviewed 字样），wt759 三源核验已将此形态判为合规（WT759-RECON report.md:212「R1 卡级签收在 commit 内，52 卡」）。V4 若要求 receipt 文件化，这是要改的执行惯例。

---

## C.1 意图（卡面目标与验收）

八卡共性 Forbidden 条款与 B 线一致（不重建权威真源/不用 mock 冒充/不静态宣称体验/不弱化安全守卫）；Gate V3-2，依赖链 C-01←B-06，C-02←C-01+M-01+D-01，C-03←C-02+M-03，C-04←C-02+E-05，C-05←C-02+M-04，C-06←C-03+C-04，C-07←C-03+M-07，C-08←C-05+06+07。

| 卡 | Risk/Reviewers | 卡面目标（一句话） | 卡面关键验收 |
|---|---|---|---|
| C-01 DecisionContext/ContextPack 契约冻结 | high/2 | 定义 Aurora/Router/Planner 共同消费的最小高信号 Context 契约，字段带 ref/type/scope/version/why_included | Python/Go/Dart 如需消费则 parity guard 过；不存在 parallel UserContextV3 真源 |
| C-02 四分适配层 | medium/1 | Context Builder 明确 State/Memory/Knowledge/Events 来源类别，阻止 profile/RAG/history 混成一段 prose | 每 item source type 正确；同名字段无静默覆盖；trace 可看四类 token/项数 |
| C-03 硬过滤→语义检索 | high/2 | embedding/LLM 前应用 identity/scope/TTL/purpose 硬过滤 | invalid candidate 绝不送 model；1000+ memory synthetic 下稳定 |
| C-04 RAG Placement/Citation/Version | medium/1 | 解决「材料已注入但模型间歇不引用」 | mr4 类案例稳定达阈值（≥20 次统计）；citation faithfulness 过；**不许靠强迫引用无关材料刷指标** |
| C-05 Conflict Resolver 注入与 Clarification | medium/1 | 模型知道哪些事实已裁决、哪些仍不确定；只对会改变 decision 的冲突提问 | 30 冲突场景不出现两个相反偏好同时当真；不必要 clarification 率在 eval 中下降 |
| C-06 Budget/JIT/Compaction | medium/1 | 按 decision utility 分配 token，不沿用单一 6000 机械上限 | 长会话回归不因 compaction 丢 correction/goal state；token 与质量/延迟有对比报告 |
| C-07 缓存版本/Memory Epoch/Policy Version | critical/2 | 缓存不允许继续使用删除/纠正前的信息 | 删除/纠正后 0 stale reuse；跨 user 0 collision；hit metrics 保留且性能不显著退化 |
| C-08 Observability + Decision Utility Eval | medium/1 | 知道「为什么这次模型看了这些」并验证少而对 | ≥50 场景有 utility/latency/token 结果；错误 Context 可追溯 source_ref；不记录敏感正文到日志 |

---

## C.2 实际交付逐卡

### C-01 · DecisionContext / ContextPack 契约冻结

**交付**：合入 `57c87a8e`（ACCEPT dual-review，2026-09-19）。`backend/app/core/decision_context.py`（355 行→现主干 416 行）+ context_pack.py extend（+245 行）+ 契约快照测试 test_decision_context_contract.py（559 行，21 测试）。要点：decision_context.v1 三个 frozen dataclass；ref URI 5 个封闭 scheme；why_included 10 个封闭 code；**extend-only into ContextPack**（optional tail field + kill switch + 双路降级）；signals 从 UserStateV1 指针投影（无平行真源）；**proto 零触碰**（避免三语言再生成的契约面）；sha256 指纹+prompt-surface key 钉定的快照测试。R2-F2 合入时补 emotion_hint/srl_phase 值形状对称冻结。R2 条件项登记 V3-FIX-09（F1 治理模式冒充降级零观测/F3 frozen dataclass 可变 dict 等）——**后续硬化合入 `b2e8fa13`**（FIX-09 单审 ACCEPT）。R2 的 F5（循环 import 债）由 wt364 以 `b5f934ad` 真修收口（台账 C-01 升格条目 CLOSED WITH EVIDENCE，prompts.py:44 顶层 import 下沉+三入口 subprocess 冒烟测试 3/3 红→绿）。

**用户可见行为**：无直接可见行为（契约层）；它让后续所有 C 线卡共享同一 Context 词汇。

**验证证据**：双审 ACCEPT（REVIEW_RECEIPT.md + REVIEW_RECEIPT_2.md 在 v3-output/C-01/）；3 个 aggregator 测试失败经基线复现判定 pre-existing（fleet notes 09-19：「fail identically at pre-C-01 baseline」——非本卡回归的归类有据）。

**残差**：Go/Dart 侧消费面在 V3 期间未出现（proto 零触碰是主动选择），parity guard 验收「如需消费则过」以条件式达成——V4 若网关/端侧要读 ContextPack，需补跨语言 parity。

### C-02 · State/Memory/Knowledge/Events 四分适配层

**交付**：合入 `886a7d42`（ACCEPT dual-review + rework + delta）。`backend/app/orchestration/context_sources.py`（1114 行→现 1124 行）+ context_pack.py +259 行 + context_builder.py +133 行 + orchestrator.py 接线 +19 行。要点：封闭词表四域（State/Memory/Knowledge/Events）+ 4 个独立开关 + token 计数；统一 manifest 形状（frozen keys、单一序列化权威、两条路径钉死）；**W1-W4 接线测试把 delete 与 disable 两类变异全杀**（delta 处 10/10 红）；M-03 权限过滤直接接线（权限继承、不静默吞、无死代码）。三份 receipt（REVIEW_RECEIPT/2/3）。

**用户可见行为**：trace 里能看到四类来源各自的 token/项数；profile 不再与 RAG/history 混装。

**残差**：seed/demo source 标记（卡面 Work 3）在 source adapter 层由 C-02 的 manifest 形状承载，与 B-02 的 origin 列（FIX-258）分属两层——V4 读 trace 时注意两套标记的语义分工。

### C-03 · Context 硬过滤→语义检索 Pipeline

**交付**：合入 `2375694c`（ACCEPT dual-review）。`backend/app/services/context_retrieval_pipeline.py`（738 行→现 745 行）+ graph_rag.py +43 行 + galaxy/retrieval_service.py +52 行 + business_metrics 计量 +11 行。要点：knowledge permission filter 前置到 candidate pool 之前（embedding/LLM/rerank 之前）；M-03-parity reasons 封闭词表；**修掉一个真实隐私泄漏：galaxy hybrid 检索曾把其他用户的个人 chunks 送给远端 rerank**；性能实测 1000+1000 candidates 8.4ms 线性（ratio 断言钉死；perf 探针 scripts/devtools/c03_pipeline_perf_profile.py 146 行随卡入库）。

**用户可见行为**：检索只见合法候选；跨用户材料物理上不再离开候选池前的边界。

**验证证据**：双审（REVIEW_RECEIPT ×2：R2 六变异+R1 零 must-fix）；83 定向测试主干绿；perf 测试 test_context_retrieval_pipeline_perf.py（1 测试，规模断言型）。

**残差**：卡面「1000+ memory synthetic 下仍稳定」以 8.4ms@1000+1000 实测满足；更大规模未测（unknown 未标注上限）。

### C-04 · RAG Placement/Citation/Version 正确性

**交付**：合入 `7a1cd424`（2026-09-20，R2 PASS）。`backend/app/core/citation_markers.py`（217 行→现主干 217 行）+ context_pack.assemble_prompt 与 generation_node 接线 + standard_workflow +11 行 + test_citation_markers.py（306 行，16 测试）。要点：纯函数 `[S#]` 引用锚+use-only-when-cited 指令+确定性答案侧解析（parse_cited_markers）+汉字 bigram faithfulness；**反 gaming 机制封死：不引用不受罚 + 硬引（引用无关材料）必被抓（support_ratio=0）**；BUG-1 哨兵矛盾修复（sentinel block 不再携带 must-cite 声明）。

**验收证据**：fleet notes（v3/.sparkle_v3_fleet_state.json）：「60 runs 独立复算全一致+预算 60/60；变异 5（4 红绿+1 等价分析）；201 passed 复现」——**超过卡面 ≥20 次统计要求**。需要说明：该 A/B 的 60 runs 为评测框架复算一致性口径，**本次未定位到「qwen3.8-flash 真实模型 60 次」的显式运行级记录**；机制在真实模型路径的下游实证由 J-06 提供（`7bd6ade3`：hybrid 旅程 prep 段走生产真实 GENERATION/FAST+C-04 parse_cited_markers 确定性核对，无引用/越集引用 503 诚实失败不落产物，红测先行 5 用例）。

**用户可见行为**：AI 回答里的引用可点击溯源、可机器核对是否真用了材料（J-06 旅程中用户可见「引用-交付」链）。

**残差**：版本/删除/跨用户过滤（卡面 Work 3）由 C-03 的 permission 前置+C-07 的版本信号承载，本卡未重复建设（架构分工而非缺口）；真实模型上的 mr4 稳态统计以 JOURNEY 驱动面证据为主，独立 60 次真模型 A/B 报告未在 v3-output 定位。

### C-05 · Conflict Resolver 注入 Context 与 Clarification

**交付**：合入 `db06260e`（reviewed，R2 PASS 0P1/0P2/5P3）。`backend/app/services/conflict_resolution_context.py`（430 行→现 433 行）+ context_pack.py conflict_resolution 一等字段+74 行 + sufficiency_checker.py 可选参数 +22 行 + test_conflict_resolution_context.py（696 行，23 测试）。要点：stdlib-pure 零 IO/零 LLM 转换；winner 归因 8 条封闭词表+loser「已知分歧」从句（不静默）；消费 M-04 ask_once 权威；ContextPack prompt 面有界投影（满额 6210→796 tokens，7.8x），结构化明细不进 prompt；materiality 确定性——仅未裁决且（UNSAFE∨CJK-bigram 相关）才问，已裁决/SCOPE/无关三路永不问；A-B 缺省一致性 10 案族 IDENTICAL；变异 4/4。

**接线状态（本次亲证，V4 必读）**：注入面**活**——context_pack.py:1524 构建 conflict_resolution_payload、:2084 传入 ContextPack、:1864 metadata 带 resolution_refs。澄清面**边界保持**——SufficiencyChecker.check 支持 conflict_resolution 可选参数且 select_material_clarification 已实现，但**现役调用点 validation_engine.py:361 未传该参数**（本次开文件核实）。这与提交信息如实声明的「WIRING-1 边界保持（validation_engine 单行可接线）」一致：即**冲突驱动的定向澄清是契约就绪、单行接线的状态，不是已激活行为**。

**验收证据**：R2 PASS（fleet notes：「冲突注入 stdlib-pure+有界投影+materiality 确定性」）。**卡面「30 冲突场景」与「不必要 clarification 率在 eval 中下降」两项：本次未定位到 30 场景级 eval 的独立记录**（现证=23 个单测中的 materiality 确定性测试+10 案族一致性），如实标注为证据缺口而非宣称达成。后续红队 wt404（Q-04，`66ab4dbd`）在真实服务面测出 C-05 抑制值过境（FIX-69）/deny 复活（FIX-70），由 wt416 `12ce081b` 红测先行修复（**均 FIXED@12ce081b**，含「prompt_note 零 loser 原文」契约锁与 72h deny 冷却窗）——C-05 的行为正确性最终由红队→修复链闭环。

**用户可见行为**：被纠正的旧偏好不再以原文驻留 prompt（FIX-69 修后）；deny 过的偏好在冷却窗内不再复活。

### C-06 · Context Budget / JIT / Compaction

**交付**：合入 `960bc498`（R2 PASS）。三件套：`backend/app/core/context_budget_matrix.py`（172 行）——entitlement × decision-type 预算矩阵替代单一机械上限（JSON 可覆盖；旧 env 变量降级为 hard-ceiling clamp）；`backend/app/orchestration/conversation_compaction.py`（381 行→现 383 行）——**zero-LLM tier-3 默认压缩，correction/decision/unresolved/action_result/goal_state 有序保留，每次丢弃显式 dropped_key 记账（无静默丢失路径）**；`backend/app/core/knowledge_jit.py`（204 行）——大型 knowledge 只留 references+top chunks+fetch hint（**-36.7% tokens，+18% identity reachability**）。

**验证证据**：20 新测试（test_c06_context_budget_compaction.py 20 测试）；50-turn 5+2+3 probe 保序实录；跨卡回归 C-04/C-07/C-03 47 绿；R2 PASS。

**用户可见行为**：长会话不再因压缩丢掉此前的纠正与目标状态；大文档场景下回答成本显著下降（JIT 拉取）。

**残差**：卡面「token 使用与质量/延迟有对比报告」以 JIT 的 -36.7%/+18% 数字+50-turn probe 满足主体；全象限 budget matrix 的真实模型质量对比（每档 decision-type 的 utility 曲线）未独立成文——C-08 的消融框架是承接面（见 C-08 残差）。

### C-07 · Context Cache 版本/Memory Epoch/Policy Version 正确性

**交付**：合入 `6c197fde`（critical，R2 PASS）。`backend/app/services/context_cache_key.py`（130 行）——4 信号版本解析（object versions/memory_epoch/policy_version/knowledge version），fail-closed，user 前缀复合 key。四面接线：Face A context_builder 进程内缓存版本化+write/correction turn bypass（+87 行）；Face B context_manager 快照钉 memory_epoch 读闸+join M-07 DEL 模板（+57 行）；Face C memory_settings 读闸字段变更→**同事务 epoch bump**+派生缓存 DEL（+45 行）；Face D graph_rag write/correction turn 绕过文本缓存读（+28 行）。

**验收证据**：21 新测试（test_context_cache_versioning.py 24 测试现值）；4/4 验收探针+4/4 独立变异；「删除/纠正后 0 stale reuse」为测试钉死的断言面；发现并登记 FIX-45（baseline push-settings 失败+pin gaps），随后 `d98a70c1` 确认 FIX-45 closed。

**用户可见行为**：删掉/纠正一条记忆后，AI 不会再「记得」旧版本内容（缓存不可能返回删除前的答案）。

**残差**：性能面「hit metrics 保留、不显著退化」以 metrics 计数器保留+测试断言承载，未做独立压测报告（unknown：高并发下的 hit rate 曲线）。

### C-08 · Context Observability + Decision Utility Eval

**交付**：合入 `080a4643`（R2 PASS，CONTEXT stream 收官）。`backend/app/orchestration/context_funnel.py`（688 行→现 700 行）——4 级单调漏斗（count/tokens/reasons，候选→filter→rerank→inject）；source_ref 用 12-bit 不可逆短哈希（PII 红线）；bloat/inert 定位；3 个有界计数器。接线为 3 处 metadata-only（不碰 orchestrator/friction_wiring；失败仅降级）。消融框架 `backend/tests/context_eval/`（schema 188+grading 199+mock_model 222+runner 107+scenarios 234+gate 215 行）——**56 场景 × 4 臂（no memory/no RAG/no outcome/full context）hermetic zero-LLM**，crowd-out 与 harmful-outcome 两个方向被验证，delta 独立逐位复算。

**验收证据**：62 跨回归绿；**零正文泄漏（n-gram 双向扫描）**；错误 Context 可追溯 source_ref；20+ 测试（test_context_funnel.py 27 + gate 17）。超过卡面 ≥50 场景。

**用户可见行为**：无直接可见行为；「为什么这次模型看了这些」从此有机器可答的漏斗账。

**残差（V4 重点）**：消融是 **mock model 上的机制消融**（hermetic zero-LLM 是刻意设计——可在 CI 跑、可逐位复算），它验证的是漏斗机制与 crowd-out 方向，**不是真实模型的效用数字**。「每个 decision-type 的真实 utility 曲线」这一层 V3 期间未做（C-REPORT 战报的链 7「AI 记忆/星图增益」当时也标注「增益尚未证明」）。V4 若要真模型效用评估，context_eval 的 runner/scenarios/grading 骨架可直接复用，换掉 mock_model 即可。

---

## C.3 设计决定与取舍（从提交/审查考古）

1. **C-01 extend-only + proto 零触碰**：不另起 UserContextV3 真源（卡面 Forbidden），DecisionContext 作为 ContextPack 的 optional tail field 接入，带 kill switch 与双路降级；代价是 Go/Dart 侧消费推迟（V4 需补 parity）。契约冻结用 sha256 指纹测试而非文档承诺。
2. **封闭词表优先**：why_included 10 code（C-01）、四域 source type（C-02）、rejection reason 词表（C-03）、winner 归因 8 词表（C-05）——所有「原因」字段一律封闭词表+测试钉死，牺牲表达力换可断言性。
3. **过滤前置于生成前**（C-03）：把 permission/identity 过滤放到 embedding/rerank 之前，顺带修掉真实隐私泄漏（远端 rerank 见到跨用户 chunks）——「先合法再相似」的次序是安全决定，不是性能决定。
4. **反 gaming 内建**（C-04）：卡面明令「不能通过强迫每个回答引用无关材料提高指标」，落地为 support_ratio=0 硬引必抓+不引用不受罚的双向机制，并用变异测试验证机制真的双向生效。
5. **删除可见性**（C-05/C-06）：loser 不静默（「已知分歧」从句）、compaction 每次丢弃 dropped_key 记账——「无静默丢失路径」是 C 线反复出现的验收语言。
6. **fail-closed 缓存**（C-07）：版本信号解析失败即不命中缓存；同事务 epoch bump 保证纠正与失效原子。
7. **可观测的 PII 红线**（C-08）：source_ref 12-bit 不可逆短哈希——可追溯性与不记敏感正文两个验收同时满足的设计点。
8. **诚实边界**：C-05 的 WIRING-1（澄清面单行接线留白）、C-08 的 mock model 消融——两处都在交付时如实声明边界而非宣称完成；V4 接手时这两处是明确的「待激活」而非「已坏」。

---

## C.4 残差与 V4 注意点（汇总）

1. **两个「就绪未激活」面**：① C-05 冲突定向澄清——validation_engine.py:361 单行接线即活，V4 做「少问对问题」时从这里开始；② C-08 真模型效用评估——context_eval 骨架在库，换真模型即用。两者都在交付时如实留白，不是缺陷。
2. **C-04 真模型统计的证据形态**：60-run 复算一致性+J-06 真实旅程核对在案，但独立真模型 mr4 稳态报告未定位——V4 引用「引用正确性」数字时以此口径为准。
3. **跨语言 parity 未发生**：C-01 proto 零触碰，Go/Dart 至今不消费 ContextPack——V4 若把 Context 暴露到端侧/网关侧，parity guard 是第一张卡。
4. **C 线与 M 线的耦合是双向依赖**：C-07 依赖 M-07（memory epoch/DEL 模板）、C-05 消费 M-04（ask_once 权威）、C-02 接 M-03 权限——V4 改记忆系统时必须同步审 C 线四面（cache key/builder/manager/settings）。
5. **审查 receipt 文件化缺口**：C-04～C-08 的独立审查证据在提交信息与 fleet notes 里，无独立 receipt 文件——V4 若沿用「commit 内签收」惯例，应把该形态写进验收模型定义（当前 wt759 已认可，但追溯成本高）。
6. **后续 FIX 证明了红队价值**：FIX-69/70（C-05 行为缺陷）由 Q-04 红队在真实服务面抓出并修复——C 线单测全绿不等于行为全对，V4 应保留红队层。
7. **性能数字的时效**：C-03 的 8.4ms@2000 与 C-06 的 -36.7% 是 09-19/20 时点数据结构上的实测；数据量级变化后需重测（有 perf 探针脚本在库：c03_pipeline_perf_profile.py）。

---

## C.5 本次审查登记

- **零新登记**。本次审查产出的唯一台账级发现（FIX-258 闭账指针丢失）归因于 B-02 审计链，登记为 **V3-FIX-504**（见 B-line.md §B.5 与台账行）。
- C 线复核中确认的「与卡面有距离但已如实声明」项（不构成漂移）：C-05 WIRING-1 边界（commit 明示）、C-08 mock model 消融（报告口径明示）、C-04 真模型统计口径（fleet notes 明示）——三项均已在本文件 §C.2/§C.4 如实标注。
- 号占用核验：C 线相关 FIX 全链状态复核——FIX-09 FIXED（b2e8fa13）、FIX-45 FIXED（d98a70c1）、FIX-69/70 FIXED@12ce081b、C-01 F5 循环 import CLOSED WITH EVIDENCE（b5f934ad）。
