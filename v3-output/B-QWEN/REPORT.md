# B-QWEN · 主力 Qwen 系列选型研究备忘录（纯研究，零代码）

- Worker：B 纵队模型选型线 ｜ worktree：`Sparkle-sysrev/wt183` ｜ 基线：`a338d989`
- 日期：2026-09-22 ｜ 纪律：纯研究零代码零测试零 LLM 调用；主仓只读；引用 file:line 均在基线 `a338d989` 树内核实
- 交付物：仅本报告（`v3-output/B-QWEN/REPORT.md`，无 patch）
- 诚实性总声明：本文标注三类信息——**【仓库实证】**（引用 file:line 可复核）、**【公开常识】**（Qwen/DashScope 体系的一般性公开知识，未联网核验）、**【推断】**（基于前两类的推理，必须实测才算数）。价格与档位时效以 **dashscope 现价目实测为准**（仓库内最近一次官方页快照是 QWEN-PLAN 2026-09-22，见 `v3-output/QWEN-PLAN/REPORT.md` §2；其中 qwen3.7-plus 非思考价为限时 8 折窗口，存在窗口结束涨价风险）。

---

## 0. TL;DR

1. 现役 Qwen 编队（7 个 LLM 注册位 + 4 个多模态/Embedding 旁支）分层清晰：`qwen3.7-flash`（FAST/批）、`qwen3.8-flash`（STANDARD 甜点）、`qwen3.7-plus`（PLUS 非思考 / PRO 思考一鱼两吃）、`qwen3.8-max`（MAX/TOP 旗舰）。**未注册** `qwen-turbo`（已被 flash 系替代）与独立 `qwen-max` 旧名（仓库用 `qwen3.8-max`）。
2. 四大任务画像的真实分档：聊天生成=STANDARD（qwen3.8-flash 轻思考）+ deep_analysis 显式升 MAX + standard 档首触快响降 FAST；fast-track=FAST（qwen3.7-flash，TTFT 1.26s 战果，**红线不动**）；诊断判卷=聊天内错题诊断走 PRO（qwen3.7-plus 思考）、后台错题分析已归 MiniMax、exam-sprint 判卷是**确定性无 LLM**（对卡面画像的一处诚实修正）；预测 batch=MiniMax M3 现役、qwen3.7-flash 次位。
3. 给出 2 个可测试假设：**假设 A（推荐优先做）**「判卷/诊断结构化面：qwen3.8-flash 思考同价档可替代 qwen3.7-plus 思考档，一致率差 ≤3pp、成本 -79%」；**假设 B（纯评测不切流）**「重上下文聊天生成：qwen3.7-plus 非思考对 qwen3.8-flash 的质量增量是否值 +20% 成本」。两者都只用现有 LLMRouter env 键即可 A/B，全部保留回滚位。

---

## 1. 盘点：LLMRouter tier 体系与 Qwen 系在册配置

### 1.1 tier 体系骨架【仓库实证】

- Provider 枚举 7 家：xiaomi/deepseek/zhipu/hunyuan/dashscope/siliconflow/minimax（`backend/app/core/llm_router.py:47-56`）。MiniMax 注释明确「仅 GLM_BATCH 池，永不进主聊天能力层」（:55）。
- ModelTier 枚举 12 层：free / free_fast / free_reasoning（归一 free_fast）/ fast / standard / plus / pro / max / top / reasoning（归一 pro）/ glm_batch / specialist（`backend/app/core/agent_profiles.py:82-95`）。
- 降级链 `_FALLBACK_TIER_ORDER`：TOP→MAX→PRO→PLUS→STANDARD→FAST→FREE_FAST→REASONING→FREE_REASONING→GLM_BATCH→SPECIALIST（`llm_router.py:360-372`；归一规则 :403-409）。
- 能力层排序（免费层钳制用）：TOP=0 … FAST=5，非直出层不参与钳制（`llm_router.py:111-118`）。
- 池条目注册：静态 29 个 + 条件 2 个（`minimax_m3_batch` :885-894、`qwen3_7_flash_batch` :909-918，均 `BATCH_LLM_PROVIDER=minimax` + key-gate）= **key 齐全环境 31 个 model configs**，与任务卡口径一致。
- tier 池映射：代码内默认链（`llm_router.py:924-928, 980-1019`）+ `.env LLM_TIER_*` 全层覆盖（:1024-1050）——**这就是本备忘录所有 A/B 建议的零代码切换面**。
- 思考分档（TTFT-CFG 战果）：`_DASHSCOPE_THINKING_OFF_TIERS = {FAST, STANDARD, PLUS}` 显式注入 `enable_thinking=false`；PRO/MAX/TOP 不注入（provider 默认思考开）；三态函数永不返回 True（`llm_router.py:180-207`，注入点 :1805-1809）。
- batch 车道开关：`batch_llm_provider()` 唯一读取口，`glm`（默认回滚位）/`minimax`（`llm_router.py:65-78`；`settings.py:511`）。
- 免费层钳制：`FREE_TIER_MODEL_CEILING=fast`（`settings.py:730-731`），免费用户能力层高于 fast 一律压到 fast（`llm_router.py:415-504`）；请求级 free/pro 信号由 gRPC 入口按 `users.entitlement` 设置（:84-90）。

### 1.2 Qwen 系在册模型（generation 主力车道）【仓库实证】

| model_key | model_name（settings 默认） | tier | cost/1k (USD) | avg_latency | temp | thinking_mode | 注册位置 |
|---|---|---|---|---|---|---|---|
| `dashscope_fast` | `qwen3.7-flash`（DASHSCOPE_FAST_MODEL） | FAST | 0.0001 | 150ms | 0.7 | —（非思考） | `llm_router.py:759-768` |
| `dashscope_standard_thinking` | `qwen3.8-flash`（DASHSCOPE_STANDARD_MODEL） | STANDARD | 0.00025 | 260ms | 0.7 | enabled（思考不涨价） | `:769-779` |
| `dashscope_chat` | `qwen3.7-plus`（DASHSCOPE_CHAT_MODEL） | PLUS | 0.0003 | 500ms | 0.7 | —（注册语义=非思考，随主链显式关） | `:780-789` |
| `dashscope_reason` | `qwen3.7-plus`（DASHSCOPE_REASON_MODEL，同款开思考） | PRO | 0.0012 | 2000ms | 0.2 | enabled | `:790-800` |
| `qwen3_8_max` | `qwen3.8-max`（DASHSCOPE_MAX_MODEL） | MAX | 0.0034 | 2500ms | 0.3 | enabled | `:802-812` |
| `qwen3_8_max_top` | `qwen3.8-max`（DASHSCOPE_TOP_MODEL） | TOP | 0.0034 | 3500ms | 0.3 | enabled | `:813-823` |
| `qwen3_7_flash_batch` | `qwen3.7-flash`（DASHSCOPE_BATCH_MODEL） | GLM_BATCH | 0.0001 | 300ms | 0.3 | — | `:901-918`（key-gated，仅 BATCH_LLM_PROVIDER=minimax 时注册，池内次位） |

模型名真源：`backend/app/config/settings.py:584-590`；定价注释锚点（北京地域 2026-09 官方页、汇率 7.1）：`llm_router.py:754-758`。思考控制参数 `enable_thinking` 的线上语义见 TTFT-CFG 报告（`v3-output/TTFT-CFG/REPORT.md` §二：修复后组包断言输出——fast/standard/plus 带 `enable_thinking:False`，pro/max/top 不注入）。

### 1.3 Qwen 家族旁支（非聊天 LLM，盘点完整性）【仓库实证】

| 面 | 模型 | 位置 |
|---|---|---|
| Embedding 主力 | `text-embedding-v4`（1024 维） | `settings.py:592` |
| Rerank | `qwen3-rerank` | `settings.py:593` |
| ASR 实时 | `qwen3-asr-flash-realtime` | `settings.py:607` |
| TTS | `qwen3-tts-instruct-flash` | `settings.py:616` |
| 免费兜底（$0） | `siliconflow_free`＝Qwen3.5-4B（FREE / FREE_FAST 链） | `llm_router.py:744-753, 981-989` |

### 1.4 现役 tier 池（首位=实际主力）【仓库实证，`llm_router.py:924-928, 980-1019`；`LLM_PROVIDER=qwen`（`settings.py:418`）经 provider 偏好重排（:931-964）】

| tier | 池（→=降级次序） | 主力 |
|---|---|---|
| FAST | dashscope_fast → deepseek_fast → xiaomi_chat → glm_4_7_flash_no_thinking | **qwen3.7-flash** |
| STANDARD | dashscope_standard_thinking → deepseek_chat → xiaomi_standard_thinking | **qwen3.8-flash** |
| PLUS | dashscope_chat → glm_4_7_plus | **qwen3.7-plus 非思考** |
| PRO/REASONING | dashscope_reason → glm_4_7_pro | **qwen3.7-plus 思考** |
| MAX | qwen3_8_max → deepseek_reason → glm_5_max | **qwen3.8-max** |
| TOP | qwen3_8_max_top → glm_5_1_top | **qwen3.8-max** |
| FREE / FREE_FAST | dashscope_fast → siliconflow_free → glm 免费条目（保留待用） | qwen3.7-flash |
| GLM_BATCH | BATCH_LLM_PROVIDER=minimax：minimax_m3_batch → qwen3_7_flash_batch；=glm：GLM 原链 4 条目 | **MiniMax M3**（测试替换中），qwen3.7-flash 次位 |
| SPECIALIST | zhipu_ocr / siliconflow_ocr / hunyuan_translate / siliconflow_translate | 非 Qwen（另有 qwen3-rerank 独立消费） |

GLM 全系 11 条目「保留配置不启用」，回切零代码（`llm_router.py:614-666` 注释 + `LLM_PROVIDER=zhipu` / `LLM_TIER_*`）。

---

## 2. 任务画像：主力链路真实负载（从调用点归纳）

### 画像 1｜聊天生成（重上下文 + 流式）

**调用链**【仓库实证】：网关 `/ws/chat` → ChatOrchestrator → `standard_workflow.generation_node`（`backend/app/agents/standard_workflow.py:1459`）→ `chat_stream_with_tools`（:1924）→ `LLMService.stream_chat`（`backend/app/services/llm_service.py:1188`）/ `_create_raw_stream`（:910）。全局默认服务就是 GENERATION 角色（`llm_service.py:1905`）。

**分档决策树**（generation_node 内，`standard_workflow.py:1525-1601`）：
1. `chat_mode=deep_analysis` → 强制 **MAX** 层（qwen3.8-max），不被成本带偏好压回 flash；逃生阀 `DEEP_ANALYSIS_FORCE_FAST_TIER` 默认 False（:141-153；`settings.py:725`）。
2. phase_d 强制档（:1543-1550）。
3. standard 档**首触快响**：`STANDARD_CHAT_FORCE_FAST_TIER=True`（`settings.py:721`）+ 任务=STANDARD_RESPONSE + `reasoning_mode=fast` + standard 模式 → 强制 **FAST** 层（:248-262, 1551-1566）。
4. balanced 快路径：reasoning_mode=balanced + slim 上下文 + 消息 ≤120 字符且无深度词 → FAST（:266-291, 1567-1580）。
5. 其余 → profile 策略路由：GENERATION profile `preferred_tier=STANDARD`、preferred_models=[dashscope_chat]（`agent_profiles.py:218-231`）→ 实际选中 `dashscope_standard_thinking`（**qwen3.8-flash 轻思考**）。

**负载特征**【仓库实证】：上下文预算按 entitlement×决策类型 6000–11000 token（`backend/app/core/context_budget_matrix.py:46-60`）；slim 标准问答 episodic top-3 ≈500 token（`standard_workflow.py:100-102`）；流式、reasoning 进度帧 3s 节流（TTFT-PROBE §4.2）、[S#] 溯源标记（:1258 附近）。

**时延/质量/成本要求**：TTFT 是第一指标——C 线压缩轮战果「fast-track 链 1.26s、通用链 enable_thinking=false 分档 1-2s」（任务卡口径；FLEET-BRIEF 四线现状「TTFT 1-2s」）。历史教训：qwen3 混合模型默认思考时 reasoning 13-43s、首块其实 356ms 就到（`v3-output/TTFT-PROBE/REPORT.md` 簇 B：M2=42.9s、M6=33.4s 等）。质量要求：教学人格一致、结构化可读、溯源可查；成本约束见 O-07 预算（free 150k tok/$0.5 每 run，`v3-output/QWEN-PLAN/REPORT.md` §1.3）。

### 画像 2｜fast-track（轻问答）——**红线，不动**

**调用点**【仓库实证】：
- FAST 层首位 `dashscope_fast`（`llm_router.py:924`）；FREE_FAST 层也 Qwen 置首（:984-989）；免费用户钳制天花板=FAST（`settings.py:730-731`）。
- 前置质量门钉 FAST 车道：`check_sufficiency`（`backend/app/orchestration/sufficiency_checker.py:20-35`，探针实测原 STANDARD 思考档单次 3.2-19.2s）与 `check_goal_quality`（`backend/app/orchestration/goal_quality_evaluator.py:19,78,100-105`，5s 预算封顶）。
- 轻问答 agent 全在 FREE_FAST/FAST：ROUTER（意图 JSON 路由，`agent_profiles.py:252-282`）、RETRIEVAL（:234-249）、STUDY_BUDDY（:599-626）、SEARCH_AGENT（:508-527）。
- 生成侧首触快响（画像 1 第 3/4 条）同样落 FAST。

**要求**：TTFT 1.26s 是 B/C 两线共同战果（簇 B 根因修复=显式 `enable_thinking=false` + FAST 置首 + 首触快响），**任何选型建议不得触碰 FAST 层首位、思考分档参数与首触快响开关**。质量面：路由 JSON 稳定性 > 小模型（QWEN-PLAN 把 FREE_FAST 从 GLM-4B 升 qwen3.7-flash 的论证，§3）。

### 画像 3｜诊断判卷（结构化输出）

调用点分三个子面【仓库实证】：

1. **聊天内错题诊断**（同步、用户直面、流式）：`chat_mode=error_diagnosis` → `TaskType.ERROR_DIAGNOSIS`（`standard_workflow.py:216-224`）→ deep 档链 PRO→PLUS→STANDARD（`llm_router.py:522-523, 531-532`）→ ERROR_ANALYST profile `preferred_models=[dashscope_reason, dashscope_chat]`（`agent_profiles.py:399-427`，输出契约四段结构①错误类型②根因③正确解法④变式题）→ **PRO 层 qwen3.7-plus 思考档**。rescue 路径同样 PRO（`standard_workflow.py:767-773, 784-789`）。REVIEWER 审查专家同层（`agent_profiles.py:558-580`，低温 0.2、structured_output=True）。
2. **后台错题批量分析**（异步、非直面）：`error_book_service._run_llm_analysis`（`backend/app/services/error_book_service.py:661-735`）——`response_format=json_object` + MiniMax 直连车道优先（BATCH_LLM_PROVIDER 裁决）、主 LLM 兜底、规则兜底兜全链。**已归 MiniMax，不属于 Qwen 选型面**。
3. **exam-sprint 诊断判卷**：`exam_sprint_diagnostic_service.py:660` 注释明示「静态模板 + **确定性判卷（无 LLM、无预算面）**」（:1053-1098 grading_payload 服务端持有）。**诚实修正：这个「判卷」面不消耗任何 LLM，不存在模型选型问题**；若未来引入 LLM 判卷（如主观题/后测增益 CP-07），它属于画像 3 的第 1 子面（PRO 档结构化），假设 A 直接适用。
4. 结构化解析容错是真源：`_parse_json_payload` 的 `<think>` 剥离 + json 块提取（`llm_service.py:1150-1172`）——意味着即使模型输出带思维链/围栏，系统有统一兜底，但**解析成功率仍是档位选择的硬指标**。另有现成 LLM 判卷基础设施：`profile_eval_llm_judge.a_judge` 钉 STANDARD 层评分（`backend/app/services/profile_eval_llm_judge.py:109-117`）——假设 B 的 LLM judge 交叉可直接复用。

**要求**：结构化一致率（JSON 可解析、枚举值合法、字段完整）> 时延（用户直面子面秒级可接受、后台无感）> 成本（PRO 档 $0.0012/1k 是非旗舰中最贵车道）。profile_eval LLM judge（`profile_eval_llm_judge.py:109-117`）钉 STANDARD 层做评分，是现成的「LLM 判卷」基础设施参照。

### 画像 4｜预测 batch（已归 MiniMax，本卡不动）

【仓库实证】长时程预测 `generate_long_horizon_prediction` 显式投 `queue="glm_batch"`（`backend/app/services/predictive_service.py:1955-1969`，`_schedule_long_horizon_refresh` 内 dispatch 覆盖）；链解析 `_select_long_horizon_model_chain`（:1509）随 router 注册面走；celery 路由表 5 个 batch 任务（`backend/app/core/celery_app.py:121-145`）；minimax 车道锁死（注册即唯一默认、不健康也不偷切、失败走 celery 退避重试，`backend/app/services/glm_batch_service.py:43-79`）；并发硬上限 8（`settings.py:502`）。实测：M3 简单任务 1.4-3.3s、`<think>` 内联、HTTP 200 + `base_resp.status_code=1004` 错误形状（`v3-output/MM-M3/REPORT.md` §4）。**Qwen 在此车道仅为次位回退**（`qwen3_7_flash_batch`，`llm_router.py:1005-1017`），MiniMax 测试替换期内不建议动排序；DashScope Batch API 半价是后续成本优化项（`llm_router.py:904-906` 注释已预留）。

---

## 3. 候选与权衡：画像 × 候选矩阵

### 3.1 候选清单与情报等级

| 候选 | 状态 | 情报等级 |
|---|---|---|
| qwen3.7-flash | 在册（FAST/FREE_FAST/GLM_BATCH） | 【仓库实证】价格 0.2-0.8 元/M（≤32K 阶梯）、思考同价、1M 上下文（`v3-output/QWEN-PLAN/REPORT.md` §2，2026-09-22 官方页快照） |
| qwen3.8-flash | 在册（STANDARD） | 【仓库实证】0.8/2.7 元/M、**思考不涨价（flash 系独有）**、缓存折扣 |
| qwen3.7-plus（非思考/思考） | 在册（PLUS/PRO 一鱼两吃） | 【仓库实证】非思考 ~2/2 元/M（限时 8 折）、思考 8/8（=4×非思考）；**8 折窗口结束会涨价**【推断风险】 |
| qwen3.8-max | 在册（MAX/TOP） | 【仓库实证】12/36 元/M、思考同价、1M 上下文 |
| qwen-turbo | **未注册** | 【仓库实证不选】QWEN-PLAN §2：0.3/0.6 元/M、128K、已被 flash 系替代 |
| qwen3.5-plus / 3.5-flash（上一代） | 未注册 | 【仓库实证】保留为快照可选，无动因 |
| dashscope Batch API / 上下文缓存折扣 | 未启用 | 【公开常识】Batch 半价、缓存命中折扣可显著降 batch/重上下文成本；【仓库实证】Batch 半价已列为后续优化项（`llm_router.py:905`） |

### 3.2 矩阵（●强适配 ○可测 △不推荐 ✗排除）

| 画像 ＼ 候选 | qwen3.7-flash | qwen3.8-flash | qwen3.7-plus 非思考 | qwen3.7-plus 思考 | qwen3.8-max |
|---|---|---|---|---|---|
| 聊天生成（重上下文+流式，现役 STANDARD） | ○ 仅首触快响已用 | **● 现役**（思考同价=甜点最优解，QWEN-PLAN §3 论证） | ○ 假设 B 验证位（质量上限更高、无思考税、+20% 成本） | ✗ 流式思考税 13-43s 已被 TTFT-CFG 逐出直出层 | ✗ 旗舰做通用聊天 = 27× 成本无对应质量需求 |
| fast-track（轻问答，现役 FAST） | **● 现役，红线不动** | ✗ TTFT 战果不许冒险 | ✗ 同上 | ✗ | ✗ |
| 诊断判卷·聊天直面（现役 PRO 思考） | △ 轻量题可、难题根因定位能力存疑【推断】 | **○ 假设 A 首选**（思考同价、成本 -79%、代际更新可追平一致率【推断】） | ○ 次选（非思考结构化稳定性好但推理深度弱于思考档【公开常识】） | **● 现役** | △ 疑难杂症单点升级位，成本 2.8×，无现役动因 |
| 诊断判卷·后台批量 | ○（已注册为 batch 次位） | ○ 若假设 A 证真可同时覆盖 | △ | △ 后台无时延压力但成本高 | ✗ |
| 预测 batch（现役 MiniMax） | **○ 次位回退（现状即正确）** | △ 成本 2.5× 于 3.7-flash 无收益 | ✗ | ✗ | ✗ 免费 M3 面前无意义 |

### 3.3 权衡要点（诚实标注）

- **flash 系「思考同价」是 Qwen 档位体系里对 Sparkle 最有价值的特性**【仓库实证注释+公开常识】：其他系（GLM 标准、qwen3.7-plus）思考都溢价（GLM 实测思考吃 completion 预算 84-88%，`llm_router.py:122-174`；qwen3.7-plus 思考=4×，QWEN-PLAN §2），qwen3.8-flash 思考不加价——这使「轻思考」可以下沉到甜点层，也正是现役 STANDARD 选它的理由。
- **思考质量 > 非思考质量、但时延/预算税重**是【公开常识】级的一般规律；**具体到「错题诊断判卷一致率 qwen3.8-flash 思考 vs qwen3.7-plus 思考差多少」，没有任何实测数据，纯【推断】**——这正是假设 A 要买的答案。
- **代际风险**【推断】：3.8 代 flash 对 3.7 代 plus 的「以小博大」能否成立，取决于 dashscope 代际迭代策略，无法离线判断；测试成本低（env 一行 + 固定判卷集），值得买答案。
- **价格时效**：全部价格快照于 2026-09-22 官方页（QWEN-PLAN §2）；qwen3.7-plus 非思考 8 折为限时窗口【仓库实证注明】；**落地前一律以 dashscope 现价目实测复核**，若价格面翻转（如 plus 大降价），假设 A 的成本论证需重算。
- **1M 上下文全系标配**【仓库实证】：Sparkle 最深 run 的窗口需求（pro 600k token 预算内）全系覆盖，上下文长度不构成分档判据。

---

## 4. 建议：2 个可测试假设 + A/B 验证方案

> 公共前提：所有切换只用现有 LLMRouter 配置面（`.env` 的 `LLM_TIER_*` / `DASHSCOPE_*_MODEL` + 重启引擎——LLMRouter 是进程启动快照注册，改 settings 必须重启），**零代码**；每条假设都先声明回滚位。

### 假设 A（优先做）：判卷/诊断结构化面——qwen3.8-flash 思考同价档可替代 qwen3.7-plus 思考档

**假设陈述**：在错题诊断/判卷类结构化任务上，`qwen3.8-flash`（思考同价，blended $0.00025/1k）与现役 `dashscope_reason`（qwen3.7-plus 思考，$0.0012/1k）的判卷一致率差 ≤3 个百分点、JSON 解析成功率差 ≤2pp，而单次成本 **-79%**、时延显著更低。

**改动面（B 组=现役不动，A 组）**：`.env` 加一行
```
LLM_TIER_PRO=dashscope_standard_thinking,glm_4_7_pro
```
即 PRO 池首位换成 qwen3.8-flash（`_override_tier_mapping_from_env`，`llm_router.py:1024-1050`）。**不动** `dashscope_reason` 条目本身、不动 fast-track、不动 deep_analysis 聊天档（走 MAX，`standard_workflow.py:141-153`）。

**影响面盘点（A/B 期间被切换的消费者）**【仓库实证】：error_diagnosis 聊天模式（`standard_workflow.py:216-224` + ERROR_ANALYST/PROBLEM_SOLVER/EXAM_ORACLE/DEEP_ANALYST/REVIEWER/SCIENCE_AGENT 的 PRO 层策略，`agent_profiles.py:323,373-397,399-427,446-460,558-580,654-678`）+ reasoning_mode=deep 链（`llm_router.py:522-523,531-532`）。

**A/B 方案**：
1. 固定判卷集 ≥100 题（覆盖错题四类型：知识性/理解性/计算性/粗心 + 附加根系定位难度分层），每题带人工标注错误类型与根因要点；同集在 B 组（现役）与 A 组各跑一遍（生产路径或 `select_specific_model` 直呼等价面）。
2. 指标：①错误类型分类一致率（vs 人工标注）；②结构化完整率（四段①-④齐备 + JSON 可解析率，消费 `_parse_json_payload` 同口径）；③根因定位有效抽评（双盲人工 1-5 分）；④单次均成本与 P50/P95 时延。
3. 判定：①差 ≤3pp 且 ②差 ≤2pp → 采纳 A 组（省 79%）；任一超限 → 回滚，并把「qwen3.8-max 做 PRO 单点升级位」记为后续观察项。
4. 度量面现成：`LLM_ROUTER_SELECTION_TOTAL` / `LLM_ROUTER_ESTIMATED_COST_PER_1K` / routing_audit（`llm_router.py:1516-1552`）按 model_key/tier 分桶，A/B 期天然可分。

**回滚位**：删除该 env 行（或改回）→ 重启 → 逐位恢复现役链；`dashscope_reason` 注册全程未动，降级链上它仍在 MAX 链外随时可用。
**预期指标**：成本 $0.0012→$0.00025/1k（-79%）；P95 时延从思考档（秒级，QWEN-PLAN §3 计 2000ms 均值锚）降至 flash 档（260ms 锚，实际带思考取中）；质量面以判卷集实测为准（**不预设通过**）。

### 假设 B（纯评测，不切流）：重上下文聊天生成——qwen3.7-plus 非思考对 qwen3.8-flash 的质量增量是否值 +20% 成本

**假设陈述（可证伪双向）**：正向——qwen3.7-plus 非思考（现 PLUS 档）在重上下文教学生成的正确率/幻觉率/结构可读性上显著优于 qwen3.8-flash 轻思考，增量值 +20% 成本，可作为付费用户升档差异化位；反向——增量不显著，维持 qwen3.8-flash 现役，且 PLUS 档存在收敛到 flash 系的省钱空间。

**方案（影子评测，零现网变更）**：
1. 固定 50 条重上下文 prompt（真实会话脱敏采样：多轮 + 长 RAG 注入 + deep_analysis 各占 ~1/3），`dashscope_standard_thinking` 与 `dashscope_chat` 各生成一遍。
2. 评：双盲人工评（正确性/教学可用性/幻觉 1-5 分）+ `profile_eval_llm_judge` 基础设施做 LLM judge 交叉（`profile_eval_llm_judge.py`，judge 本身钉 STANDARD 层）；同时记录 TTFT 与 completion 时延（plus 非思考应无思考税，验证 TTFT 不劣化）。
3. 判定：正向显著（配对检验 p<0.05 或人工评均值差 >0.3）→ 另立产品卡评估「付费 STANDARD 升 PLUS」（涉及 entitlement/免费钳制面，**不在本卡**）；反向 → 记录结论，PLUS 档维持现状（它还承担降级链位，不动）。

**回滚位**：纯评测无现网变更；若后续任何切流，`LLM_TIER_STANDARD`/`LLM_TIER_PLUS` 一行回切。
**预期指标**：成本差 +20%（$0.00025 vs $0.0003/1k）；TTFT 差应在噪声内（两者都是 `enable_thinking=false` 直出层，`llm_router.py:191-193`）——**若 plus 档实测出现思考税（模型未按参数关思考），立即记为 dashscope 参数面缺陷并上报，不进入切流评估**。

### 明确不建议的事项（负面清单）

- **不动 fast-track 现役配置**：FAST 池首位、`enable_thinking=false` 分档、`STANDARD_CHAT_FORCE_FAST_TIER`、前置质量门 FAST 化——TTFT 1.26s 战果一条都不碰（任务卡红线）。
- **不动 batch 车道排序**：MiniMax M3 现役测试替换期内，`qwen3_7_flash_batch` 维持次位；Batch API 半价优化另立卡。
- **不注册 qwen-turbo**：已被 flash 系替代（QWEN-PLAN §2），注册无收益。
- **不动免费钳制 ceiling=fast**：假设 A 的 PRO 池换键对免费用户无感（免费请求根本到不了 PRO 层，`llm_router.py:433-445` 钳制在前）。

---

## 5. 风险与时效性登记

| 风险 | 等级 | 缓解 |
|---|---|---|
| 价格/档位快照过期（2026-09-22 官方页，QWEN-PLAN §2） | 中 | 落地前以 dashscope 现价目实测复核；成本论证全部可由 `cost_per_1k` 锚点一键重算（`llm_router.py:754-823`） |
| qwen3.7-plus 限时 8 折窗口结束 → PLUS/PRO 现役成本上升 | 中 | 若发生，假设 A 的成本优势进一步放大（现役基准变贵）；无回滚负担 |
| 「思考同价 flash 能否追平 plus 思考一致率」无实测先例 | 高（对假设 A） | 判卷集 A/B 是买答案的全部成本；判据（≤3pp）事先钉死防事后合理化 |
| PRO 池换键影响面广（7 个 profile + deep 链） | 中 | env 一行回滚；A/B 期监控 `LLM_ROUTER_SELECTION_TOTAL` 与用户面投诉；deep_analysis 聊天档走 MAX 不受影响 |
| DashScope `enable_thinking` 参数面对 3.8-flash 的实际行为 | 低 | TTFT-CFG 已有 wire 级断言覆盖（`v3-output/TTFT-CFG/REPORT.md` §三裁决 1），A/B 复用同款 httpx.MockTransport 校验即可 |
| 本备忘录未联网，Qwen 档位体系表述依赖仓库快照+公开常识 | 声明 | 全文已按【仓库实证】/【公开常识】/【推断】三级标注 |

---

## 收工申报

- 交付物仅 `v3-output/B-QWEN/REPORT.md`；零代码/零测试/零 LLM 调用/零 commit；主仓只读。
- 无 tmp 产物（研究全程直读仓库，无探针/无克隆基线）；无进程/模拟器/浏览器残留。
- 引用核对说明：所有 file:line 在基线 `a338d989` 树内用 grep/sed 核实；任务卡口径数字（31 configs、TTFT 1.26s、1-2s、MiniMax 测试替换中）分别与 `llm_router.py:883-918`（29+2 条目）、FLEET-BRIEF/CP 线战果口径对上。
