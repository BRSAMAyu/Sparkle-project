# GAIN-EVAL：memory/用户画像真实增益消融评测资产

> 2026-09-23 ｜ Worker：wt198（基线 17f4b5df）｜ 交付：`changes.patch` + 本报告
> 用户令（C 线核心）：「memory/星图/向量索引/用户画像必须证明正向增益，发现污染/幻觉/负增益即修」

## 0. 一句话

把「这些能力的增益从未被系统证明过」变成可执行资产：**20 个可判分场景（离散数学冲刺语境）× 真实装配链 A/B 消融双臂 × 确定性优先判分**，`--dry-run` 无 key 跑通装配并硬断言消融接线，live 模式（主会话注 key）产出增益矩阵与红旗清单。**零产品改动、不切任何生产开关**。

## 1. ① 消融面盘点表（能力 × 开关 × 注入点）

装配链口径：`app/api/v1/chat.py:866 get_user_context`（HTTP `/chat` :368、`/chat/stream` :613、task chat :144 三面共用）→ `app/core/context_pack.py:1345 ContextPackBuilder.build`（pack 唯一构建点）→ `app/services/profile_context_service.py:134 get_profile_context`（画像唯一读模型）→ `app/orchestration/prompts.py:861 build_system_prompt`（prompt 唯一渲染器，`agents/graph/nodes/*` 亦复用）。gRPC/gateway transport 面不属本卡；本卡消融的是引擎内上下文装配权威组件，上层链路消费同一 pack/renderer。

| 能力 | 注入点（file:line） | 名义开关 | 实际消融入口 | 判定 |
|---|---|---|---|---|
| **记忆注入**（preferences/goals/episodic 三段） | 召回 `context_pack.py:1402-1404`；预算裁剪 `:1629-1652`；prompt 渲染 `prompts.py:3982 _format_past_session_memory_section`（段落在 prompt **末尾**紧邻 user 消息，`:1657-1662` R2-final(a2) 口径）+ 【学习偏好】`prompts.py:3470-3493` | `ENABLE_CONTEXT_SOURCE_MEMORY`（settings.py:776） | **无**。该开关只控 C-02 manifest 计量（`context_pack.py:2176`，`context_sources.py:766 settings_flag`），**控不了注入**；`ENABLE_MEMORY_USE_SELFCHECK`（settings.py:788，闸门 `context_pack.py:1674`）是反向开关（关掉=记忆**变多**）；`ENABLE_LTM_ROLLOUT/PERCENT`（settings.py:913-914）只控 ranking/conflict（`:1399,:1443`），数据照常召回 | **无消融入口（申报）**；评测杠杆=召回源置空（§3） |
| **用户画像注入**（knowledge_summary 弱项/错误簿/认知画像） | 附加 `chat.py:922-931`；渲染 【知识薄弱点】`prompts.py:3496-3515`、【近期痛点】`:3522-3541`、【画像快照】`:3776-3782`（源 `prompts.py:4475` canonical insight） | 无任何布尔/三态开关 | 评测杠杆=get_profile_context 抛错→生产 fail-soft 分支（`chat.py:930-931` 内层 except，"画像不可用"是**既有生产行为**，无需新代码路径） | **无消融入口（申报）** |
| **全个性化面**（记忆+画像+pack 结构） | `chat.py:887` | `USE_CONTEXT_PACK`（settings.py:758）——**真实总开关**，False 走 legacy 旧上下文路径 | 进程内 settings 置换（臂 E-NOPACK） | 开关在位 ✅ |
| **向量索引/文档检索**（document chunks） | kill-switch 读 `context_pack.py:1313-1329 _resolve_document_context_controls`；服务 `aurora_doc_context_kill_switch_service.py:19-37`（`ENABLE_DOCUMENT_CONTEXT_INJECTION=False` → mode 强制 off） | `ENABLE_DOCUMENT_CONTEXT_INJECTION`（settings.py:814，真实总开关）+ `AURORA_DOC_CONTEXT_MODE`（settings.py:824，分类器**预算档** auto/live/on/skip，非注入开关） | 进程内 settings 置换（探针 D-VEC：off → pack `document_context_controls.enabled=False` 传播验证 ✅）。注：chunk 正文注入走 orchestrator 侧（`agents/standard_workflow.py:1798` galaxy/doc 通道），进程内无端到端 prompt 面 | 开关在位，端到端面**申报留主会话** |
| **星图注入**（galaxy knowledge / stage39 sidecar） | orchestrator 侧 sidecar 装配（`context_builder.py:219 galaxy_inject_mode`；kill-switch `aurora_stage39_kill_switch_service.py:37-43`） | `AURORA_STAGE39_GALAXY_INJECT_MODE`（settings.py:381，off\|shadow\|live，真实三态开关） | 进程内 settings 置换 + kill-switch 读回验证（探针 G-GALAXY：off 读回 off ✅）。注入点在 orchestrator sidecar，进程内无 prompt 装配面 | 开关在位，端到端面**申报留主会话** |
| 相邻面（盘点备查，不做臂） | 语义门控 `ENABLE_CONTEXT_SEMANTIC_GATING`（settings.py:783，闸门 `context_pack.py:1552`，embedding 缺失 fail-soft）；HyDE `ENABLE_HYDE`（:929）；GraphRAG fastpath `ENABLE_GRAPHRAG_FASTPATH`（:924，默认 off）；个性化 ranking `ENABLE_PERSONALIZED_RANKING`（:835）；工作记忆 `AURORA_STAGE19_WORKING_MEMORY_MODE`（:262） | 均为真实开关，但作用是**调制/过滤**召回而非 capability on/off，不构成增益消融臂 | — | 备查 |

**盘点结论**：四个被点名的能力里，只有「全个性化面」（USE_CONTEXT_PACK）、「向量/文档检索」、「星图注入」有真实开关；**「记忆注入」与「用户画像注入」没有消融入口**——按卡纪律（不许为评测加产品开关，除非一行 env）未动产品，以评测杠杆替代（§3），并如实申报。

## 2. ② 场景集构成（`backend/tests/northstar_eval/gain_scenarios.json`）

20 个可判分场景，离散数学冲刺语境（大二学生小陈，期末倒计时 7 天），每场景独立 seed + 独立用户（进程内 SQLite，数据面彼此隔离）：

| 类别 | 数量 | 依赖能力 | 判分法 | 例 |
|---|---|---|---|---|
| memory（记忆依赖） | 8 | episodic 事实 / 记忆偏好 / 记忆目标 | 7 deterministic（expect_groups 命中率+forbidden 罚分）+ 1 llm（例题先行风格） | mem-01 考试日期回忆（答出「下周四」）；mem-05 续接开场自然衔接（CTX-PACK v3 保守放行形状）；mem-03 目标回忆（「数理逻辑 40 题」） |
| profile（画像依赖） | 6 | knowledge_summary 弱项/掌握度/近期变化 | 6 deterministic（弱项点名/优先级） | prof-01 弱项驱动复习建议（点名数理逻辑 35%）；prof-02 今日专项选题（选最弱，选已掌握的集合论 → forbidden 罚分） |
| baseline（基线） | 6 | 无（零种子） | 6 deterministic（知识点要素命中） | base-01 群定义四要素；base-02 等价关系三性质 |

判分构成：19 deterministic + 1 llm（规则不可判的风格类，照 `profile_eval_llm_judge` 先例）。每个 memory/profile 场景带 `probe_terms`（装配探针依赖，见 §3）；每个场景带 `scoring_note`（判分要点申报面）。场景设计与 M-05 Self-ReCheck 的耦合已显式管理：memory 场景 query 与 seed 事实共享显著词元（relevance 词法检查通过），否则臂 A 自身丢记忆（生产真行为，dry-run 探针会把守）。

## 3. ③ 运行器设计（`backend/tests/northstar_eval/gain_ab.py`，照 grade_ab.py 风格）

**臂**（同场景双臂跑，A/B 单变量=上下文）：

| 臂 | 消融实现 | 开关性质 |
|---|---|---|
| A（FULL，对照） | 生产默认装配 | — |
| B-MEM | `MemoryService` 四个召回读方法置空（list_preference_records / **list_preference_history** / list_active_goals / list_recent_episodic）——召回源置空等价"记忆能力关闭" | 评测杠杆（无产品开关，申报） |
| C-PROF | `ProfileContextService.get_profile_context` 抛 `ProfileUnavailable` → 生产 fail-soft 分支不附加 | 评测杠杆（无产品开关，申报） |
| E-NOPACK | `USE_CONTEXT_PACK=False`（legacy 路径）+ 画像消融——全个性化合计增益参照 | **真实总开关** |
| D-VEC / G-GALAXY（探针，不判分） | 真实三态/布尔开关的进程内传播验证 | **真实开关** |

杠杆实现要点（诚实记录两次返工）：
1. 首选的「预算钳 0」杠杆**不干净**：`prompts.py:3784-3810` 的【画像证据摘要】回灌面会在 `active_goals`+`episodic` 皆空时把 `metadata.evidence_summary`（`context_pack.py:1870`，取自**裁剪前** source records）的 goal 标题/偏好值带回 prompt——预算杠杆被该回灌绕过（dry-run 探针抓到，mem-03 B-MEM 泄漏实证）。改为**召回源置空**后全链（pack 三段 / M-05 selfcheck 输入 / conflict resolution / evidence_summary）干净。
2. 只置空 `list_preference_records` 仍不够：conflict resolver 用**全版本链**（`list_preference_history`）做 winner 裁决，偏好会从历史链复活——同样置空。
3. baseline 守卫从「A/B/C 三臂逐字节相同」收敛为「A==B-MEM 逐字节相同（硬断言）」：C-PROF 在零数据用户上仍有结构性差异（生产画像面对零数据用户也注入基础内容，见 §5 红旗 3）——非用户数据污染，差异字符数进证据面。

**判分**：确定性规则优先（expect_groups 逐组命中，组内 OR；forbidden 每命中 −0.5，下限 0）；`kind=llm` 走 `profile_eval_llm_judge` 先例同款（STANDARD 档、严格 JSON `{score,rationale}`、失败诚实 fallback 不重试）。**纯净性红线**：live 臂经 `llm_router.select_model(force_tier=PRO, AgentRole.GENERATION, TaskType.STANDARD_RESPONSE)` 解析后直调 `OpenAICompatibleProvider.chat`，绕过 fallback manager/熔断器；temperature=0.3 两臂同参；失败按场景记 error 不换模型。

**增益判定（冻结门槛，防事后合理化）**：
- 正增益：消融臂在**依赖类场景**均值比 A 低 ≥ +0.15；
- 负增益嫌疑（红旗）：消融臂依赖类均值 ≥ A（能力未证明正向增益）；
- 污染红旗：消融臂 baseline 均值比 A 低 > 0.15（能力关闭伤及无辜）；逐场景「消融后反超 A ≥ 0.5」记幻觉嫌疑（需人审）。

**--dry-run**：无 key 装配自检=消融接线证明——每场景每臂经**真实装配链**产出提示词，硬断言「A 含事实 / B-MEM 不含 / C-PROF 正交保留 / E-NOPACK 全消 / baseline B-MEM 与 A 逐字节相同」+ 双开关探针；任一失败即非零退出（消融没切干净或场景需修，不许进增益判定）。

## 4. 验证结果（全部进程内哑值 `SECRET_KEY`，worktree 无 .env，未调任何真实 LLM）

| 套件 | 结果 |
|---|---|
| 全量 dry-run（20 场景 × 4 臂真实装配链 + D-VEC/G-GALAXY 探针 + 接线硬断言） | **全绿**：`20 场景 × 4 臂真实装配链装配 OK；开关探针 {'D-VEC': True, 'G-GALAXY': True}；消融接线断言全绿` |
| pytest 守卫 `tests/northstar_eval/test_gain_ab.py`（带 --timeout=600） | **5 passed in 8.46s**：包下限/类别构成、judge+probe 完整性、门槛冻结钉、接线断言数学（绿/红两向合成臂）、真实链 dry-run（每类别 1 例 + 探针 + run JSON schema） |
| lint | ruff 全绿 + ruff format(120) 合规（仅本卡两个 .py） |

live 冒烟留主会话（需 DASHSCOPE_API_KEY；命令见模块 docstring：先 `--limit 4` 冒烟再全量，20 场景 × 4 臂预计 ~20-30 分钟串行）。

## 5. 红旗清单（诚实申报；零产品改动，全部留主会话裁决）

1. **记忆/画像无消融入口**（§1 判定列）：建议后续卡补 `ENABLE_CONTEXT_PACK_MEMORY`（一行 env + `context_pack.py:1402-1404` 召回处一个 gate，即可让本运行器的 B-MEM 杠杆退休为真开关）；画像同理（`chat.py:922` 一行 gate）。
2. **`ENABLE_CONTEXT_SOURCE_*` 名不副实**：四分开关（settings.py:775-778）只控 C-02 manifest 计量（`context_pack.py:2162-2212`），不控注入——运维视角会误以为关掉即切断注入。建议改名（`*_MANIFEST`）或补真闸门。
3. **零数据用户被注入捏造状态（幻觉嫌疑，直接命中用户令「发现污染/幻觉即修」）**：全新用户（零错题、零画像）的 prompt 含【画像快照】`痛点: Recent error pressure remains elevated.`（英文模板行，`prompts.py:3776-3782` ← canonical insight inline snapshot）+【近期痛点】`累计错题 0`。空数据应诚实空态（FLEET-BRIEF 四.4 口径），建议空数据时 inline snapshot `available=false`。
4. **【画像证据摘要】正文回灌**（`prompts.py:3784-3810`）：`active_goals`+`episodic` 皆空时把 `metadata.evidence_summary`（裁剪前 source records，`context_pack.py:1870-1899`）的 goal 标题/偏好值+分数带进 prompt——预算裁剪与 M-05「降档条目正文不回灌」语义在**预算维度**有缺口（M-05 注释明确「无正文回灌」，此处违背）。本运行器靠召回源置空绕开，但生产普通轮次仍受影响。
5. **画像面跨通道注入 goals**（`prompts.py:4479-4484`）：canonical insight 的 goals 可回填 `active_goals`——画像与记忆边界在 prompt 面有交叉（C-PROF 消融同样切掉，不影响本卡判定，申报备查）。
6. **legacy 路径存量 bug**：`chat.py:1014` `not Plan.is_completed`——`Plan` 模型无该属性，`USE_CONTEXT_PACK=False` 时 context 组装中途 AttributeError 被外层 `except`（:1047）静默吞掉、后续段落（plans/knowledge_stats）丢失。总开关实际处于「半坏」状态。
7. **galaxy/文档 chunk 的端到端 prompt 面**：开关已验真在位且传播（探针 PASS），但注入点在 orchestrator 侧，进程内无法给「关掉星图后答案变差/不变差」的证据——该项的真实 LLM 增益冒烟留主会话（gRPC/WS 链路冒烟同批）。

## 6. ④ 冲突面声明

| 邻卡 | 面域 | 与本卡交叠 | 判定 |
|---|---|---|---|
| wt195 | mobile/ | 无接触（本卡零 mobile 文件） | 无冲突 |
| wt196 | orchestration/ + northstar 测试 | **同目录**（`backend/tests/northstar_eval/`）：wt196 若改 `runner.py/grading.py/metrics.py/feature_tour.py` 等存量文件，与本卡**无同文件交叠**（本卡只新增 `gain_scenarios.json`、`gain_ab.py`、`test_gain_ab.py` 三文件）；`__init__.py` 共享但本卡未改它。若 wt196 也在该目录新增文件，合入时仅需注意 patch 无同名 | 低风险，无同文件冲突 |
| wt197 | docker-compose*/deploy | 无接触 | 无冲突 |
| 存量产品代码 | `backend/app/**` | **零改动**（diff 可证） | 无冲突 |

## 7. ⑤ 诚实申报汇总 + 收工核查

- 无法消融（无入口）的能力：**记忆注入、用户画像注入**——评测杠杆替代并如实标注（`_meta.ablation_entry_disclosure` 落进每次 run JSON）；
- 进程内无端到端证据面：**星图注入、文档 chunk 注入**——开关探针已证传播，真 LLM 冒烟留主会话（§5.7）；
- 真实 LLM 全量增益矩阵：**未跑**（worktree 无 key，纪律禁调真 LLM）——门槛与判分已冻结，主会话注 key 即可出结果；
- [x] 修改仅在本 worktree（wt198）；主仓只读未动；零凭据（api_key 仅以布尔在场进证据）；
- [x] 未 commit / 未 push；交付物 = 本报告 + `v3-output/GAIN-EVAL/changes.patch`（3 个新文件：场景包/运行器/守卫测试）；
- [x] /tmp 探针产物已清（`/tmp/gain_probe_out.txt`、`/tmp/gain_runs/`）；worktree 内 dry-run 运行产物（`v3-output/GAIN-EVAL/runs/`）不入 patch、已清；
- [x] 无模拟器/浏览器/Gradle/独立端口进程（全 LIGHT 任务）；未宽扫测试（只跑本卡守卫文件，带 --timeout）；
- [x] `app/gen/` 为 gitignore 内本地构建产物（`make proto-gen` 生成，测试必需），不入 patch。
