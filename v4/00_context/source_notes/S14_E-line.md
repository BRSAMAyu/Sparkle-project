# E 线（AI 8 卡）深挖章节 —— V4 交接文档素材（wt776）

> 本文是 `v3/V3-COMPLETE-STATUS-FOR-V4.md` §4「各线深度状态」E 线章节的深挖草稿。
> 证据纪律：只写三源证据（git 主干 SHA / 独立审查 receipt / 运行级实测）支撑的事实；逐条标注出处；无法定位证据的验收项显式标注「未定位到证据」。
> 撰写：wt776（2026-09-28，基线 main@fd4267ef）。方法：卡面（v3/07_tasks/cards/E-0*.md）+ `git log --grep` 逐卡定位 → 主干 SHA 祖先核验（16+ 卡相关 commit 全部 --is-ancestor 通过，除 wt755 938e845c 在分支）→ 代码开文件亲证（llm_router.py 1959 行三态熔断/stage_events.py 160 行 canonical 词表/batch_worklane/gateway entitlement 判据）→ 测试文件逐个计数 → receipt/bench 产物抽读（E-01/02/05 目录 + WT372/WT727/WT653）→ 台账闭环逐条复核。**未轻信任何台账/报告结论性文字。**

---

## E.0 线级概览

E 线是 V3 的「AI 能力线」：路由分层（L0-L3 认知阶梯）→ 能力路由（快慢分道）→ 首反馈体验（stage events）→ 模型评测（prompt 收敛）→ embedding 生产化 → batch 降本 → 自适应路由与健康回退 → 集成 bench。7/8 done + E-08 TODO（tasks.json@main 亲证；E-08 交付本体 a1418084 在主干、三笔未闭，见 §E.2-E-08）。

E 线执行形态最重要的特点（V4 设计者必须先读）：**E 线的证据面必须按「真模型 / 规则层 / 结构就绪」三层分开看，混读会高估**——
- **真模型证据**：B-05 探针（59 live samples，09-19 时点）、E-04 收敛轮（qwen3.8-flash 7/15→15/15 + 注入对抗）、E-08 bench（wt372 104 条 + wt406 Q-06 400 条）、JOURNEY day1-6 驱动；
- **规则层/确定性证据**：E-01 全卡（trace 分类+映射文档，零代码）、E-02 的 capability_lane 判定面（FakeLLM/monkeypatch，61 测试）、E-03 机制面（stage 帧三层测试）；
- **结构就绪、生产数据缺位**：E-06 batch lane（生产样本仍近零）、E-08 的 L0 no-model 直答（bench 实锤未生效）。

**E 线的第二特点：它的「done」大量依赖后续 FIX 族的接力校正**——E-02 的 tier 塌缩由 E-08 bench 曝光、wt380 修复；E-03 的 500ms 口径经 wt727 双证裁决→FIX-439→Leader 裁决 b 三段收窄；E-07 的弹性缺陷由 Q-06 波动注入实锤（FIX-77~81 全修）；审计链静默失效由 mypy 批九顺审抓出（FIX-491，wt761 已修但台账未闭——本档 FIX-508）。**E 线的真实状态 = 首轮交付 + Q-06/wt372/wt380/wt755 四波修正的叠加态。**

---

## E.1 意图（卡面目标与验收）

八卡共性 Forbidden 条款（卡面原文，全线一致）：不得重建已存在的权威真源；不得用 mock/seed 冒充真实行为；不得只通过静态代码阅读宣称用户体验通过；不得弱化既有安全/幂等/隔离/审计守卫。

| 卡 | Risk/Resource/Reviewers | 卡面目标（一句话） | 卡面关键验收 |
|---|---|---|---|
| E-01 Cognition Ladder 当前路由映射 | medium/LIGHT/1 | 现有 DualCore/UnifiedIntent/tiers 映射 L0-L3，找无意义 LLM 调用（不重建 router） | 核心 journey 无隐藏无必要深模型；映射文档+metrics；direct-answer fast path 不退化 |
| E-02 Fast Semantic / Deliberate 能力路由 | high/MEDIUM/2 | 简单交互真正快、复杂决策保留能力 | L1/L2 latency/quality 有真实 A/B；简单 intent 不走 L2；fallback 不把需 tools 任务降成 text-only 假完成 |
| E-03 实时 Stage Events 与首反馈 | medium/HEAVY/1 | 真实阶段事件替代 20s 无反馈，不暴露 chain-of-thought | 深路径 500ms 内真实阶段反馈；stage 与 trace 匹配；不显示 reasoning_content 原文 |
| E-04 Aurora/Action/Memory 专项 Eval 与 Prompt 收敛 | high/MEDIUM/2 | 任务级 eval 选 prompt/examples/tier，不凭主观 | 每域 baseline→candidate 分数/latency/cost；安全相关 input 不用未消毒原文 |
| E-05 Embedding / Hybrid Retrieval 生产接入 | high/MEDIUM/2 | 接活真实 embedding，RAG/Galaxy 语义搜索不靠旧 key | 真实文档 retrieval benchmark；wrong-user=0；无 key 明确关闭功能；不静默随机/zero embedding |
| E-06 Async Batch Cognitive Worklane | medium/MEDIUM/1 | 非实时工作放 MiniMax/glm_batch 降前台成本 | 前台 journey latency 不依赖 batch；stale result 拒绝；batch 老结果不覆盖新 explicit correction |
| E-07 Quality/Latency/Cost 自适应路由+健康回退 | high/MEDIUM/2 | 真实 provider 波动下选最便宜满足质量/延迟能力 | 100+ sample 统计；provider down 仍合法降级/明确 unavailable；无无界重试/成本；付费 entitlement 不绑 flame |
| E-08 AI Stack 集成 Bench | medium/HEAVY/1 | 给最终决策可复跑基准（Quality×TTFT×Cost×Context） | 100+ queries across L0-L3；raw CSV/JSON+dashboard；percentiles 样本≥100；SLO 未达真实报告+dynamic issues |

---

## E.2 实际交付逐卡

### E-01 · Cognition Ladder 当前路由映射

**交付（首轮 ACCEPT + v2 纯文档轮）**

| 波次 | 主干 SHA | 内容 |
|---|---|---|
| 首轮 | `df1b55df`（ACCEPT merge，post-revision） | L0-L3 映射文档+trace 分类（v3-output/E-01/{ROUTING_MAP.md, trace_classification.csv}）+ plus 覆盖缺口发现（W-1：记忆类流量误走 plus 层） |
| v2（wt316，零代码） | `12ba22ec` | 映射 v2+W-1 验证关闭（E-02 根修后 dev DB 44/44 真实会话 FAST，修前 54/54 plus）；**新发现 G-1..G-7 缺口清单**：G-1 sprint phase_d 强制 FAST 抢占 deep-word 否决（7/7 sprint 轮 FAST 含 proof-asking）；G-2 问候无 L0 直答；G-3 0/0 default 记账 34 条；G-4 evidence extractor 默认开且模型未注册；G-5 隐藏调用记账；G-6 batch lane 零样本；G-7 LLM_TIER_PRO 语义 |

**G 缺口后续吸收（本档逐条追溯）**：G-1 修复 `61e78483`（wt319：DEEP_ANALYSIS_TEXT_MARKERS 单源+用户 reasoning_mode=deep 抢占 phase_d FAST 默认，红 2→绿 30，dev DB 真实 trace 探针 7/7——修前两条真实 deep 轮误路由 dashscope_fast）；G-3 计量盲区 → FIX-80 FIXED@a1587328（Q-06 批）；G-7 的 user_tier 死键面 → wt380 `b42e279d` 修复（extra_context.user_tier 双形态死键）；G-2 → **仍未实施**（E08-ISS-L0-TTFT 实锤问候/确认走完整生成链，L0 no-model 直答未生效）；G-6 → batch lane 生产样本仍近零（Q-06 400 样本车道分布 fast263/plus67/max25/standard2，无 batch 车道）；G-4/G-5 → 本档未定位到对应闭环记录（**留档待查**）。

**残差**：卡面验收「existing direct-answer fast path 不退化」在首轮 REPORT 以回归测试面覆盖；映射文档两版（E-01/ 与 WT316-E01/）以 v2 为准。

**用户可见行为**：无直接可见面；它是 E-02/E-06/E-07 的路由事实底图。

### E-02 · Fast Semantic / Deliberate Decision 能力路由

**交付（dual-ACCEPT 三轮 receipt + G-1 修复 + tier 塌缩修复接力）**

| 波次 | 主干 SHA | 内容 |
|---|---|---|
| 首轮 | `690541e3`（ACCEPT merge，dual-review + rework + delta） | capability_lane 判定面：记忆类消息根修（retrieval_intent.py `classify_memory_class_message` 纯规则零 LLM ≤200 字反模式优先）→ ContextPlan(no_retrieval, reason="memory_class_turn")；简单批全落 fast lane 零检索；工具流/文档接地/深度批全落 deliberate 且 slim 全否决；capability_lane 45→61 测试（REVIEW_RECEIPT_3 总 verdict ACCEPT） |
| G-1 修复（wt319） | `61e78483` | deep-signal priority（见 E-01） |
| tier 塌缩修复（wt380） | `b42e279d` | E-08 bench 曝光的 85/85 全落 dashscope_fast 塌缩三因修复（user_tier 双形态死键/显式 deep/pro 免疫 samples 重排/队列边界继承请求 ContextVar）；同 query token_usage.model=dashscope_chat(tier=plus) 双实证、reorder/free_tier_downgrade 双归零、红测 8/8 |

**真模型 vs 规则层证据分层（任务问的核心，REPORT §7/§10 原文级亲证）**：① **L1/L2 延迟 A/B 引 B-05 真模型探针**（fast thinking-off TTFT p50 440-475ms / standard_thinking 首可见内容 p50 912-1194ms——同为 qwen3.8-flash 仅 thinking 开关差异，L1≈2x 首反馈优势）；② **路由面 A/B 是合成负载确定性判定**（FakeLLM+monkeypatch，「零 LLM 声明」REPORT §10 显式）；③ 本卡**未跑自己的真模型 A/B**——卡面「真实 A/B」以「B-05 实测引用+合成负载」双件满足，生产流量级 L1 占比验证明确移交 D-06 埋点读数（计数器已交付）。V4 引用 E-02 延迟数字时必须注 Its 来源是 B-05@09-19 时点。

**残差**：① F5（providers 健康键型接缝）转台账另卡（RECEIPT_3 建议，后续由 E-07/Q-06 族承接）；② REPORT §11 自曝基线预存测试隔离 bug（test_stage38_d3_persistence 污染 sys.modules）未定位到独立 FIX 登记（分片规避）；③ 质量承接仅有 E-01 记录的 09-18 MRV 4 条 fast 成功调用实证——fast lane 的输出质量 A/B 无独立真模型证据。

**用户可见行为**：简单交互（记忆指令/轻量问答）不再进默认深链；sprint 深度词与显式 deep 请求不再被 phase_d 快车道吞掉。

### E-03 · 实时 Stage Events 与首反馈体验

**交付（本体 + 双证裁决链 + L0 分支待集成——E 线最复杂的收口史）**

| 波次 | 主干 SHA | 内容 |
|---|---|---|
| 本体（wt366） | `0e4087ec` | `backend/app/orchestration/stage_events.py`（160 行，本档亲证）：canonical 阶段词表 frozenset（未知 stage raise ValueError）、安全不变式（帧构造无任何入参能携带 reasoning/CoT 原文）、STAGE_TO_LEDGER_STAGE/STAGE_TO_AGENT_STATE 双映射保证「stage 与 trace 匹配」可测、metadata 键 stage_event；接线 orchestrator.py:152/:1471 与 standard_workflow.py；500ms 首帧前置+300ms UI 去抖；红→绿三层留证（backend 16/gateway 全包/flutter 8+55——wt727 HEAD 复验绿） |
| 双证裁决（wt727） | `2bb38b0c` | 机制面正证 × **wt372 真实运行反证**（首阶段帧 L2-free 12/12 全部 0.55-5.24s、L2 p95=5.75s、L3 p95=7.32s、全量 21/103≤500ms；澄清门辅助 LLM 等服务可知前段未覆盖）→ 判部分达成、tasks.json 保持 TODO、残差登记 FIX-439 OPEN（口径 a 服务可知点再前移 / b 字面收窄移交 E-08） |
| Leader 裁决 b | `e85eec52` | 按 work item 2 字面口径（**服务可知后 <500ms**）判达成面双证在案，tasks.json E-03 置 done；端到端前段延迟残差移交 E-08 SLO 族 |
| L0 首帧前移（wt755） | `938e845c`（**分支 agent/node-b/wt755/slo，未集成**） | intake ack 挂请求身份锚定点、守卫链之前；raw.jsonl 逐帧复算修正归因（L2-08 实录 intake@3.0305s→goal_quality@3.0314s=门路径 9ms；**真正的首帧前串行段=StreamChat 前奏+process_stream 守卫链约 6 个串行 await**——校验/幂等 GET/锁 SET/会话态 HSET/run_started persist） |

**本档代码亲证（main@fd4267ef）**：stage_events.py 在位、emit_stage_event/build_stage_frame 两处生产消费方在位、test_stage_events_e03.py 6 测在位；「不显示 reasoning_content」由构造面无入参的结构性保证（非运行时过滤）。

**残差**：① FIX-439 OPEN（端到端首帧 SLO 残差，E-08 族承接）；② wt755 L0 待门后集成（分支保留，轮#250 台账在案），L1（StreamChat 前奏压缩）/L2（门并行化）/L3（拥塞治理）勘察未实施——wt755 notes 有完整归因，是 V4 首帧优化的现成设计输入；③ 500ms 口径的「服务可知后」字面达成 vs 用户体感（前段静默）之间的差距由 E-08 bench 数字量化（§E.2-E-08）。

**用户可见行为**：深路径等待期出现真实阶段反馈（context/retrieval/decision/tool/waiting 词表）而非 20s 静默；阶段帧不含思维链原文；UI 300ms 去抖防闪烁。

### E-04 · Aurora/Action/Memory 专项模型 Eval 与 Prompt 收敛

**交付（dual-reviewed，E 线真模型证据最厚的一张）**

| 项 | 主干 SHA | 内容 |
|---|---|---|
| 本体 | `58d08c6f`（feat，dual-reviewed） | `backend/tests/ai_face_eval/` 套件（在库，本档亲证）：36 golden case（friction 9/action 10/memory 17）+schema e04-ai-face-eval.v1 冻结；**真模型收敛 7/15→15/15（qwen3.8-flash，预算 60/60 精确，key 零泄漏）**；门禁四类（安全骨架机检/sha256 prompt 白名单——未登记 prompt 变更即红/规则层漂移绊线/逐 case 严格判定），安全维度 floor 恒 1.0 |
| 三真缺陷修复（同卡） | `58d08c6f` 内 | ① Action 注入旁路（task_summary 伪装授权→数据边界段抵抗，intervention_policy.py+joint_decision.py）；② Memory 抽取注入（伪规则→假记忆污染→extractor v2 11/12，llm_extractor_prompt.v2.md）；③ Aurora 联合通道 0/5 零情境幻觉→v2 情境旗标+scenario_summary 零新接口 |
| 溢出发现 | FIX-41（P1）FIXED@`1ae6a9e1` | R2 抓出 M-02 规则层第 4 处漏判+R10 fail-open STORE 语义缺陷（E-04 worker 3 处+R2 第 4 处） |

**证据分层判定**：E-04 的收敛数字（15/15）是**真模型**证据；eval 门禁本身（sha256 白名单/骨架机检）是规则层且常态化在库可复跑。与 M-09（memory_eval 真模型 25 次）并列，是「真模型证据集中在哪些卡」这个 V4 问题的两个主要答案之一。

**残差**：① 收敛轮是 09-20 时点单一模型（qwen3.8-flash）——模型/价格漂移后须重跑（eval 套件在库，复跑路径明确）；② extractor v2 11/12 的 1 例失败未定位到后续收口记录（如实留档）；③ 卡面「每域 baseline→candidate 分数/latency/cost」的 cost 面未在 REPORT 摘要级定位到独立数字（延迟/分数面有）。

**用户可见行为**：无直接可见面；产出是「friction/action/allocation/memory gate 四域的 prompt 与 tier 选择事实」+三处注入防线的实际加固。

### E-05 · Embedding / Hybrid Retrieval 生产接入

**交付（dual-ACCEPT + live 窗口补验闭账）**

| 波次 | 主干 SHA | 内容 |
|---|---|---|
| 首轮 | `fedc6a8e`（ACCEPT merge，dual-review + rework） | 真实 provider 事实更正：运行时实际读 `DASHSCOPE_EMBEDDING_MODEL=qwen3.7-text-embedding-flash`（dim 1024），卡面继承的「EMBEDDING_MODEL=text-embedding-v4」是未被使用的遗留标签——版本串改从 provider 实际参数派生（dashscope/qwen3.7-text-embedding-flash@1024）；**删除 DEMO_MODE 零向量静默回退**（红探针实录「VERDICT: FAIL-CLOSED VIOLATION — silent zero embedding」→修后 EmbeddingNotConfiguredError 明确报错）；迁移 e05_20260919（document_chunks/knowledge_nodes 增 embedding_model/embedding_dim，**存量不回填——来源不可证明宁缺毋假**）；hybrid lexical+vector（CJK bigram+拉丁 ILIKE+RRF+可选 rerank），向量侧失败显式降级词法并标注 retrieval_mode=lexical_only_embedding_disabled；wrong-user=0 红→绿 canary；12 chunk×6 查询三策略 benchmark；语义缓存键加模型版本 |
| live 窗口补验（wt502） | `fd50d2e9` | FIX-16 闭账：四项复核全过+残留就地处置（关停 drain 接线/invalidated_keys 注记/strict filter 维持部署级待拍板）；顺带 FIX-215（celery 向量写入漏 stamp）FIXED@3d05edf8 |
| staging receipt | `v3-output/E-05-staging/REVIEW_RECEIPT_2.md`（在库） | staging 面独立签收在案（E 线唯一有 staging receipt 的卡） |

**本档代码亲证（main@fd4267ef）**：settings.py:683 `EMBEDDING_STRICT_VERSION_FILTER`（过渡期默认 False 容忍 NULL 存量向量，True 后跨模型向量无条件排除）；检索服务版本过滤+deleted_at 谓词在位；G-05（`47898b9f`）对齐 E-05 把 REST /galaxy/search 的 embedding 故障 500 改显式降级。

**残差**：① **FIX-503（wt770 登记）**：FIX-36 修法注记「真模型复验由 E-05 下窗口补」至今无复验产物——库内 stability report 仍是修前 P01-D1 0/5 失败快照（E-05 的 REPORT/RECEIPT 无 real-model/M-09 字样，wt770 grep 实录）；② strict version filter 的部署级拍板仍开放（False=容忍 NULL 过渡态是现状）；③ EMBEDDING_MODEL 遗留标签仍在 settings.py 默认值（:680/:707 均为 text-embedding-v4）——运行时无害但考古易误导（REPORT 已自澄清）。

**用户可见行为**：资料检索/星图语义搜索走真实 embedding+hybrid；无 key 时功能明确关闭或词法降级（带标注），不静默出假结果。

### E-06 · Async Batch Cognitive Worklane

**交付（reviewed + 环境无关修复）**

| 项 | 主干 SHA | 内容 |
|---|---|---|
| 本体 | `f938ba25`（feat，reviewed） | `backend/app/services/batch_worklane.py`（624 行）：reflection/profile-aggregation/analytics 三类 batch 任务路由 GLM_BATCH/MiniMax（**llm_router 路由器级硬钳，provider 池与前台不相交**）；前台保护双层并发隔离+GLM_BATCH 独立预算桶（变异 M3 前台桶污染必红）；幂等双键（结果键+claim 键，R2 独立探针 8 并发同 key 竞争恰 1 完成+7 跳过）；有界重试→死信终态（claim 释放可重调度）；**SLA/explicit-correction 守卫（LLM 执行后 L1 落库前）——batch 老结果不覆盖新 correction 的卡魂在落库前最后一道**；10 个 sparkle_batch_lane_* 指标；R2 PASS（0P1/0P2/4P3；变异 4/4 含 2 自加） |
| 修复 | `f463170d` | no-key 测试环境 router 重建（env-independent） |

**本档代码亲证**：`batch_llm_provider()` 在 llm_router.py:68（路由器级入口）；test_batch_worklane.py 27 测在位。生产消费方：WT651-D04 audit 轨道 6 亲证 predictive long-horizon 走 celery glm_batch——**batch lane 至少有一个生产工作负载接入**，但 Q-06 400 样本 bench 的车道分布（fast263/plus67/max25/standard2）不含 batch 车道，说明 batch 面在聊天主链流量中占比近零（E-01 G-6 的批化建议未扩面）。

**残差**：① batch lane 生产流量近零——降本主张未被真实流量验证；② 卡面「queue/cost metrics」有计数器面（10 指标）但无运行级读数在档。

**用户可见行为**：无直接可见面；前台 journey 延迟与 batch 隔离的结构性保证（预算桶分立）在测试与变异层证明。

### E-07 · Quality/Latency/Cost 自适应路由 + 健康回退

**交付（dual-reviewed + Q-06 波动注入修正族 + FIX-491 审计链修复）**

| 波次 | 主干 SHA | 内容 |
|---|---|---|
| 本体 | `a2327787`（feat，dual-reviewed） | `backend/app/core/llm_router.py`（现 1959 行）ModelHealthState **三态熔断**（healthy→连续 FAILURE_THRESHOLD 失败→unhealthy→冷却到期→probation 恢复观察：1 失败立即回 unhealthy 且冷却翻倍封顶、N 次成功回 healthy；unhealthy 期间在途旧请求成功不解除熔断=滞回）；route reason 留痕（:1584 rich_reason/:1874）；capability-aware fallback |
| Q-06 修正族 | FIX-77/80/81 FIXED@`a1587328`；FIX-78/79 FIXED@`0e44092e`+`3717355e` | 波动注入七场景实锤的修复：全断供 86 连败无快速失败→快速诚实失败；过载 22/30 烧满 150s 无背压→过载背压；SQL 校验器英文词误判拒答/计量盲区 39/400 default/健康双源不同步无复位出口——全收口 |
| 能力宣称真实化 | FIX-333 FIXED@`e71a5df4`（wt642） | 裁决+五族状态机+红→绿（能力宣称与实际调用面一致化） |
| **FIX-491 审计链** | 修复 `1e3b6ebf`（wt761，**本档亲证在主干**） | SLO 自动降级/升级动作的审计事件 publish 双参签名错位恒 TypeError 被 except 吞——**审计从未入 Redis Stream**；修后 publish("slo_auto_response_audit", event.to_dict())+新增 sparkle_slo_auto_response_audit_publish_failures_total 计数器（恒现故障进指标面）；红→绿（TestAuditEventPublishing 2 红→绿）。**台账 491/492/493 三行仍 OPEN——本档登记 V3-FIX-508（见 §E.5）** |
| 付费不绑 flame | V3-FIX-02（D17）在位（本档亲证） | gateway user_context.go:70「entitlement 是唯一权益判据；flame_level 仅为展示层字段，永久禁作权益派生」+chat_orchestrator_chatflow.go:286 注记+回归测试锁（flame=15 无 pro entitlement → is_pro=false） |

**残差**：① 100+ sample 统计由 Q-06 400 样本 bench 承接（4 PASS/2 FAIL/1 NOT_REPORTABLE，见 E-08）；② probation/健康面的运行级复位出口在 FIX-81 收口前缺位、收口后以台账注记为准（未在本档重跑验证）；③ route reason 留痕有代码面（reason 参数）但无运行级审计读数在档——FIX-491 修复后 SLO 审计事件才首次真正入流（无重放补录）。

**用户可见行为**：provider 波动/宕机时合法降级或明确 unavailable（不再重试风暴/无背压拖死）；付费权益与 flame 等级彻底解耦。

### E-08 · AI Stack 集成 Bench —— 当前状态盘点（V4 性能图景专用）

**状态：tasks.json=TODO（wt759 §3.1「交付本体合格，三笔未闭」+本档复核一致）。这是 107 卡里唯一「交付了最大体量真模型数据但未销账」的卡。**

**① 修前数字（wt372 `a1418084`，09-25，引擎@0e4087ec 含 E-03）**——104 真模型 query×L0-L3（guest JWT→gRPC StreamChat，真模型真路由零 mock 失败不重试），raw.csv/raw.jsonl/facts.json/dynamic_issues.json/summary.md 全在 `v3-output/WT372-E08-BENCH/`：

| 层 | n | TTFT p50 | TTFT p95 | 首事件 p95 | total p95 |
|---|---|---|---|---|---|
| L0 | 26 | 1.11s | 2.03s | 0.90s | 65.3s |
| L1 | 26 | 1.95s | 2.95s | 3.06s | 32.9s |
| L2 | 26 | 2.50s | 14.93s | 5.45s | 49.5s |
| L3 | 26 | 7.26s | 113.36s | 7.03s | 113.0s |

SLO 2/6 达标；**最大发现=tier 塌缩**（observed 分布 dashscope_fast 85/85+default 19）；成本 $0.0117 全量（$0.00011/query）；quality 粗筛 65/104。dynamic issues 五项：E08-ISS-L0-TTFT（问候/确认走完整生成链，L0 no-model 直答未生效）、L2-FEEDBACK（免费层 deep 档首事件 p95 4.28s）、L2-TOTAL（49.5s>15s）、L3-ACK（7.03s>1s）、**FALLBACK 计量盲区**（19 条 token_usage.model='default'：12 条 0 token=澄清门/模板直出成本盲区+7 条多代理流计量错挂 default 成本低估）。

**② 已修面（修后证据）**：
- **tier 塌缩→wt380 `b42e279d`**：三因修复（user_tier 双形态死键/显式 deep-pro 免疫 samples 重排/队列边界继承 ContextVar），同 query 构建对照 dashscope_chat(tier=plus) 双实证，红测 5 败转绿——**塌缩已修，但 104 条 bench 的原始数字未在修复后重采**；
- **计量盲区→FIX-80 FIXED@a1587328**（Q-06 批）；
- **L3-ACK 7.03s→Q-06 wt406 `12e89303` 复测转准**：400 真样本分层 bench（L0-L3 每层 n=100）SLO 4 PASS/2 FAIL/1 NOT_REPORTABLE——**L3 ACK 0.06s 由 FAIL 转准**、L1 双达标、tier 账本复活实证（fast263/plus67/max25/standard2 四车道 vs 85/85 塌缩）；**仍 FAIL：L0 no-model 1879ms 与 L2 total 48.2s**；
- **首帧前段→wt755 `938e845c`（分支，待门后集成）**：intake ack 前移+归因修正（门路径仅 9ms，真凶是 StreamChat 前奏+守卫链 6 串行 await）。

**③ 未修面（V4 设计的直接输入）**：L0 no-model 直答（TRIVIAL 跳过生成）未实施；L2 total p95 ~48-49s（思考档总时长）两轮 bench 均超 15s 预算；L2 免费层 deep 档首事件前置静默；wt755 的 L1（StreamChat 前奏压缩）/L2（门并行化）/L3（拥塞治理）勘察未实施。

**④ 复测路径（有 key 环境即可执行）**：wt372 驱动在库可复跑（run_tag/raw.jsonl 口径同构）；Q-06 的 bench/chaos/tier smoke 驱动 5 件在 scripts/devtools（`12e89303` 交付）；E-03 残差闭环要求对 938e845c 集成后重采首帧分布。**V4 决策前应跑的最小集=Q-06 同构 400 样本+wt755 集成后首帧重采。**

**⑤ 销账缺口（wt759 §3.1 原文三项+本档确认）**：① review receipt（卡面 Reviewers:1）未检得独立签收；② wt755 门后未集成；③ E-03 Leader 裁决的残差移交笔（E-08 卡面欠这笔增量闭环）。加上④真模型复测（有 key 环境，V3-COMPLETE-STATUS §3 已列）。

**用户可见行为**：无直接可见面；它决定了「2 秒首反馈」类宣称的诚实边界——全库唯一分层真模型延迟数据出自此卡与 Q-06。

---

## E.3 设计决定与取舍（从提交/审查考古）

1. **映射而非重建路由**（E-01 卡面明令）：现有 DualCore/tiers 收敛映射 L0-L3，缺口以 G 编号留档逐条派修而非推翻 router——后续 wt319/wt380 都是外科修补。取舍：路由债显式化但永不归零（G-2/G-4/G-5 至今开放）。
2. **快慢分道的判定面放在规则层**（E-02）：capability_lane 判定纯函数化+FakeLLM 测试，把「哪个交互走快道」从模型行为变成可断言契约；代价是质量面无真模型 A/B（引 B-05 延迟差替代）。
3. **500ms 口径的字面收窄**（E-03 裁决链）：卡面「第一阶段 feedback <500ms（服务可知后）」的括号注成为裁决 b 的字面依据——诚实性纪律的双刃：机制面真实达成字面口径，用户体感差距（前段静默 5-7s）以数据形式移交 E-08 而非掩盖。V4 定 SLO 应避免这种「服务可知后」式可收窄口径。
4. **eval 门禁把 prompt 当代码管**（E-04）：sha256 白名单使未登记 prompt 变更即红——prompt 收敛成果用基础设施固化而非文档约定；注入防御以真实红测（task_summary 伪装授权/伪规则注入）验收。
5. **fail-closed 取代静默兜底**（E-05）：删 DEMO_MODE 零向量回退是全库「不静默降级」教义在 embedding 面的执行点；「存量不回填宁缺毋假」同判。
6. **batch 隔离做在路由器级而非任务级**（E-06）：provider 池与前台不相交+预算桶分立，把「batch 拖垮前台」从调度问题变成结构不可能；explicit-correction 守卫放在 L1 落库前最后一道。
7. **熔断用滞回而非简单阈值**（E-07）：probation 三态+冷却翻倍+在途成功不解除——每条规则都对应一类真实故障风暴（Q-06 注入面实证在先）。

---

## E.4 残差与 V4 注意点（汇总）

1. **性能图景的唯一可信口径**：修前=wt372 104 条（§E.2-E-08①表）；已修=tier 塌缩（wt380）+计量盲区（FIX-80）+L3-ACK（Q-06 复测 0.06s）；仍坏=L0 直答缺位/L2 total ~48s/免费层前置静默；复测=Q-06 同构 bench+wt755 集成后首帧重采。**任何 V4 SLO 设计请以这张叠加态表为起点，不要引用「2 秒」类旧宣称。**
2. **E-08 销账四件事**（receipt/wt755 集成/E-03 残差闭环/真模型复测）全部就绪待条件（门后集成窗口+key 环境），是 107 卡销账成本最低的一张。
3. **E-01 G 缺口清单是现成的 V4 待办**：G-2（L0 直答）/G-4（evidence extractor 默认开且模型未注册）/G-5（隐藏调用记账）未闭环——G-4 兼具成本与审计双面风险，建议 V4 优先清点。
4. **E-02 的延迟证据是借来的**：引用前核对 B-05 时点（09-19）；fast lane 质量面无独立真模型 A/B，V4 若把更多流量压到 fast 档应先补质量 eval。
5. **真模型证据重跑义务**：E-04 收敛轮与 M-09 stability report 都是单模型时点快照（FIX-503 已登记 M-09 面的复验欠账）；E 线的 eval 套件全部在库可复跑，V4 排期应把「模型漂移后重跑」当作例行而非一次性。
6. **FIX-491/492/493 台账未闭**（本档 FIX-508）：代码已在主干，V4 动 SLO 审计/plan_review/event_registry 文档前先按 §E.5-508 纠指，避免重做已修面。
7. **batch lane 的降本主张未被真实流量验证**（E-06）：接入面只有 predictive long-horizon 一处；V4 若做成本优化应先扩 batch 工作负载再谈收益。
8. **卡级证据目录缺口**（E-03/E-04/E-06/E-07 无 v3-output 目录，本档 FIX-509）：wt759 以 commit message 签收字样核验故结论不受影响，但 V4 沿用「receipt 必须入库」纪律时应把这批卡的原件回收或注记纠指。

---

## E.5 本次审查登记

- **V3-FIX-507**（P2，本次新登记，主登记在 D 线章 §D.5——D-05 lifecycle 写路径零生产调用方；对 E 线的含义：D-07 两类洞察卡与 M-06 经验投影的供给断链使「数据飞轮」在 E-08 的 Quality 维度上缺少真实个性化流量，E-08 复测时 quality 粗筛数字的解释需注此边界）。
- **V3-FIX-508**（P2，本次新登记，E 线章主登记）：V3-FIX-491/492/493 三行台账 OPEN vs 修复本体已在主干——wt761 `1e3b6ebf`（2026-09-28 01:35:54，merge-base --is-ancestor 亲证祖先）修复 491 auto_degrade 审计 publish 双参签名（含 sparkle_slo_auto_response_audit_publish_failures_total 计数器，TestAuditEventPublishing 红→绿实录在 commit message）+492 plan_review daily_hours None 守卫+493 event_registry docstring 契约段；三行行尾状态格至今 OPEN 零 FIXED@（本档 sed 逐行亲证）。可证伪判据：对三行 grep -o "FIXED@" 计数=0；git log -S "V3-FIX-491" -- backend/app/api/internal/auto_degrade.py 唯一命中 1e3b6ebf。与 V3-FIX-504（FIX-258 行闭账丢失）同族第三例，成因=集成合入后未回写台账（504 是行重建回退）。V3-COMPLETE-STATUS-FOR-V4.md §5「491/493 收口」表述与台账矛盾，以代码为准。修法：三行置 FIXED@1e3b6ebf；ledger 工具加 FIXED@ 主干可达性抽检（与 504 的修法建议合并）。
- **V3-FIX-509**（P3，本次新登记，D 线章 §D.5 主登记——七目录从未入库+三处台账死指针，E 线涉及 E-03/E-04/E-06/E-04→FIX-41(P1) 死指针；详见 D-line.md §D.5）。
- 复核过但**不构成新发现**的四项：E-08 receipt 欠+wt755 未集成+E-03 移交笔（wt759 §3.1 已登记在案，本档 §E.2-E-08⑤ 复述不占号）；E-04 extractor v2 11/12 的 1 例（属 eval 数字如实照登非不诚实面）；E-02 §11 测试隔离 bug（REPORT 自曝、分片规避，未定位到独立 FIX 但属 test-infra 债非产品缺陷）；E-05 EMBEDDING_MODEL 遗留标签（REPORT 已自澄清，运行时无害）。
- 号占用核验：507/508/509 占用前 grep 复核——主仓 v3/ v3-output/ docs/ backend/ `V3-FIX-50[5-9]`/`V3-FIX-51[0-2]` 零命中；499~504 已占用（499=wt767、500/501=wt765、502/503=wt770、504=wt769）；505/506 为在航兄弟会话（wt774-AJ/wt775-UPSG）预留段，本档顺延取 507/508/509（与 D-line.md 同批登记，三号两章共用）。
