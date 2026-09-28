# D 线（Data 8 卡）深挖章节 —— V4 交接文档素材（wt776）

> 本文是 `v3/V3-COMPLETE-STATUS-FOR-V4.md` §4「各线深度状态」D 线章节的深挖草稿。
> 证据纪律：只写三源证据（git 主干 SHA / 独立审查 receipt / 运行级实测）支撑的事实；逐条标注出处；无法定位证据的验收项显式标注「未定位到证据」。
> 撰写：wt776（2026-09-28，基线 main@fd4267ef）。方法：卡面（v3/07_tasks/cards/D-0*.md）+ `git log --grep` 逐卡定位 → 主干代码逐文件开文件亲证（event_registry 词表 40 名 sha256 独立复算吻合 / outcome_ledger / understanding_dimensions / intervention_lifecycle / north_star_wvpl / evidence_insight 六服务逐一开读）→ 测试文件逐个计数 → v3-output receipt/审计报告抽读（D-01/02/03/06 目录 + WT651/WT663/WT664/WT669/WT397）→ 台账闭环逐条复核。**未轻信任何台账/报告结论性文字。**

---

## D.0 线级概览

D 线是 V3 的「数据飞轮线」：把交互→决策→执行→outcome 串成可追溯、可审计、不让模型算数字的事件与账本体系。8/8 全部 done（tasks.json@main：D-01~06 由 8d4291aa 核正、D-07/D-08 由 wt759 批量销账 dba6aaf2 按交付+独立增量复证推定；本档 §D.2-D-07/D-08 给出复核结论：**销账成立但两卡均无正式 review receipt**）。

执行形态的显著特点（V4 设计者需要知道）：**D 线是「契约先行、读模型优先」的线**——D-01 冻结事件词表（40 名 sha256 双冻结，本档独立重算吻合）、D-02 纯读模型零 schema 变更（五源聚合不建新表）、D-03 公式冻结进 core 纯函数、D-06 事实 JSON 工厂带 golden 钉死零 LLM。产品代码增量集中在 D-04（mobile 统计接真+清污）和 D-07（insights 证据化重构+假精确面删除）。**D 线是「诚实数据」红线在统计面的执行者**：D-04 催生 FIX-350~354 五项污染清污（两批全修），D-07 催生 FIX-359 删失语义诚实化。

**V4 最须知道的一条（本档新登记 V3-FIX-507）**：数据飞轮的中段——D-05 intervention lifecycle（exposure→response→outcome 关联）——**写路径零生产调用方**。record_exposure/record_response/associate_pending_outcomes 全仓生产面零调用，唯一调用方是测试与评测 harness 引擎；读侧（D-07 两类洞察卡、M-06 经验投影）已接线。即：**飞轮纵向闭环的真实数据流在「干预交付」处断链，D-07/D-08 的洞察与证明是「读侧结构就绪 + 评测 harness 真数据」，不是生产部署会自然产生的数据**。详见 §D.2-D-07/§D.4。

---

## D.1 意图（卡面目标与验收）

八卡共性 Forbidden 条款（卡面原文，全线一致）：不得重建已存在的权威真源；不得用 mock/seed 冒充真实行为；不得只通过静态代码阅读宣称用户体验通过；不得弱化既有安全/幂等/隔离/审计守卫。Worker 只能提交 READY_FOR_REVIEW/PARTIAL/BLOCKED；Reviewer 必须独立执行关键验收。

| 卡 | Risk/Resource/Reviewers | 卡面目标（一句话） | 卡面关键验收 |
|---|---|---|---|
| D-01 统一 Event/Evidence Lineage Contract | high/MEDIUM/2 | 把交互/决策/执行/outcome 串到可追溯事件图（复用 outbox，不重建真源） | GJ03 trace 可从 UI action 追到 outcome/state update；事件幂等且跨用户隔离 |
| D-02 Outcome Ledger 与 Evidence Type 正规化 | high/MEDIUM/2 | 建立真实成果账本，让「完成」不等于点击 | completion evidence 无法证明时不伪装 actual；outcome 跨模块可查询且不重复计数 |
| D-03 Understanding 五维内部度量与校准 | medium/MEDIUM/1 | 替代神秘 understanding_depth 百分比，形成可诊断五维指标 | 每维有公式/数据源/边界，缺数据=unknown；纠正与错误使用会合理降维 |
| D-04 真实 Analytics 接线并清除生产 Mock 缓存污染 | high/HEAVY/2 | 修复统计 provider 与 user-visible mock，真实 API 不可用就隐藏 | 生产统计无固定 mock 值；cache 不存 demo fallback；断网显示 last-known-real/unknown+时间 |
| D-05 Intervention→Outcome 分析管线 | medium/MEDIUM/1 | 回答「什么帮助在什么情境有用」，形成 Experience Memory 数据基础 | 同一 intervention 不双计；未观察 outcome 标 censored/unknown；可生成 per-user/per-scope 历史摘要 |
| D-06 WVPL 北极星查询与事实 JSON | medium/MEDIUM/1 | 实现可审计 North Star，不让模型计算数字 | 固定 fixture 确定结果+边界测试；可在 staging 真实跑并追溯 event IDs |
| D-07 Evidence-driven Insights 产品重构 | medium/HEAVY/1 | 把 Insights 从预测仪表盘变成有证据、可行动的 reflection | 每条洞察可点来源，纠正后更新；无数据不生成人格结论；**Simulator 能理解至少 3 条 insight 意义** |
| D-08 数据飞轮纵向证明与 Regression Dashboard | medium/HEAVY/1 | 用多 session 证据证明数据→理解→决策→outcome 闭环 | ≥10 Persona Day0/3/7 模拟；每 persona 至少一条 correction/plan change→可解释 adaptation；无效个性化保留不筛 |

---

## D.2 实际交付逐卡

### D-01 · 统一 Event / Evidence Lineage Contract

**交付（首轮 dual-ACCEPT + 增量复证轮）**

| 波次 | 主干 SHA | 内容 |
|---|---|---|
| 首轮 | `6f488636`（ACCEPT merge，dual-review + rework） | `backend/app/core/event_registry.py`（现 849 行）：封闭事件词表+shared-fields 信封（build_event_metadata：event_id/user_id/schema_version=event.v1/source 封闭枚举/occurred_at/correlation 10 键）+ telemetry 边界（client_telemetry/probe 永非业务真值）；配套 FIX-11（`9b7469c9`，telemetry 入业务真值三链根治）与 FIX-14 follow-up |
| 增量复证（wt663，09-27） | `0495e085` | 现状复核 HOLD：词表 40 名冻结哈希独立重算吻合；写入方 7/7 全走 build_event_metadata 零绕过（新增 4 写入方合规：S-04/D-05/X-03/M-04）；GJ03 全链 7-hop probe 复通；幂等/隔离 43 测试绿；R2 移交项 F2/F6/F7/F8 现状盘点 |

**本档独立复证（main@fd4267ef 亲跑）**：`REGISTERED_EVENT_NAMES` 计数=40（29 live + 10 reserved + 1 observed_unregistered），`sha256("|".join(sorted(names)))` = `3444257e…2e0a0` 与测试字面量 `_FROZEN_VOCABULARY_SHA256` **逐字节吻合**（backend/tests/contract/test_event_registry_contract.py:64）。测试计数：contract 28 + idempotency/isolation 9 = 37 函数（wt663 时点 34+9=43 用例口径，含参数化）。`observed_unregistered` 唯一成员 `task.status_changed` 是诚实设计：dev 库观察到该事件名但仓内无 producer，注册为 observed_unregistered 以保持词表封闭而不假装它有维护者。

**残差**：① R2 移交 F2 真值门 None→eligible=True 的 fail-open 语义保留（FIX-11 选在摄入层 caps+debounce 根治，门语义未改，消费方接入前需重审）；② F6 gateway 第二 envelope 仍在（cqrs/event/types.go Metadata 无 schema_version/correlation 10 键），读侧 read_event_metadata 容忍降级视图不丢行——跨层统一未做；③ F7 outbox 7 天清理 vs lineage 目的张力仍开放（intervention_lifecycle/agent_run 等持久账本已分流，冲突面收敛未关闭）；④ F8 spark 链路业务 commit 与 outbox 写非原子（双 commit 窗口）。

**用户可见行为**：无直接可见面；它是 GJ03「完成任务→掌握度变化」全链可追溯的地基（7-hop probe 全通，HOP4 审计腿 sqlite env-limited 如实标注、PG live 实证在首轮 REPORT §3）。

### D-02 · Outcome Ledger 与 Evidence Type 正规化

**交付（首轮 dual-ACCEPT + 三份 receipt + 后续增量）**

| 波次 | 主干 SHA | 内容 |
|---|---|---|
| 首轮 | `e7ef4d32`（ACCEPT merge，dual-review + rework + delta） | `backend/app/core/outcome_ledger.py`（契约）+ `backend/app/services/outcome_ledger_service.py`（现 1119 行读模型服务）：五源聚合（tasks/study_records/focus_sessions/expansion_feedback/behavioral_outcomes）、TruthClass 四值（actual/self_reported/estimated/unknown）+ polarity、证据信任分层（声明不构成证明）、derive_outcome_id 确定性幂等 |
| 盘点增量（wt658） | `87c01313` | 登记 FIX-355：PlanFeedback.decision 四套词汇共存、过滤静默丢弃用户决策（撞号史：wt657 先占 355 登记网关投影族，集成重编号顺延——现役 FIX-355=本项、FIX-356=网关投影） |

**本档代码亲证（服务 docstring+core 词表逐条对读）**：纯读模型零 schema 变更；不重复计数机制=五源 standalone 谓词天然不相交（study_records 的完成回声行只作 pipeline_echo 多源佐证，永不升 actual）；R2 三返修在场（跨流全序带前缀 keyset/证据解析三重门/focus 时间方向单调）；X-08 扩展（ABANDONED 行 NEGATIVE+ACTUAL 进账、agent_run receipt 证据、truth_coverage 只计 POSITIVE）；cohort 边界 exclude_seed_cohort 复用 B-02 FIX-01 词表。测试：contract 30 + service 51 + x08 gj 套件。

**残差**：① FIX-322（两处墙上钟列配 UTC 窗）已 FIXED@188499e2；② 证据原件 v3-output/D-02/ 三份 receipt 在库完好，但 FIX-31 行引用的 **v3-output/D-05/REVIEW_RECEIPT.md 是死指针**（见 §D.5-509）。

**用户可见行为**：无直接可见面；下游消费方=Aurora/Context Compiler（actual 面）、Experience Memory（behavioral 面）、Galaxy（study/focus 面）、North Star（truth_coverage actual 面）——「完成≠点击」是这些面的共同前提。

### D-03 · Understanding 五维内部度量与校准

**交付（首轮 reviewed + 集成 HEAD 复核轮）**

| 波次 | 主干 SHA | 内容 |
|---|---|---|
| 首轮 | `ad5efa35`（feat，reviewed） | `app/core/understanding_dimensions.py`（公式与缺失语义冻结纯函数）+ `backend/app/services/understanding_dimensions_service.py`（现 418 行，每日聚合）+ `understanding_calibration_service.py`（锚点重算对齐+离线校准+漂移检测）+ 迁移 d03_20260920 |
| HEAD 复核（wt664） | `d7a961da` | ad5efa35 后 +1149 提交零回退；62+18+2 测试绿+dev DB 只读聚合复核；双死岛零依赖裁决 |

**本档代码亲证**：五维=coverage/correctness/scope_precision/freshness/utility；数据源全部既有表零新真源（aurora_judgment_records→coverage 用确定性 Stage20 judge 非模型自评、context_pack_runs→correctness 分母、memory_corrections→四维、memory 三表→freshness、chat_messages→coverage 行为锚点）；滚动窗（默认 7 天）+样本量逐维记录、缺就是 unknown；无活动规则=窗口内五类输入全空不落行。celery beat `understanding-dimensions-daily` 已注册（celery_app.py:1260）——**聚合有生产触发方**。测试：contract 25 + migration sqlite 4 + understanding depth 族。

**残差**：① live dev 库 memory_reference/scope 面样本 0 行（服务 docstring 自述）——维度值生产可用性取决于 M 线记忆使用事件的真实流量；② utility 维在 D-08 复证时因 decisive 样本<3 保持 unknown（诚实语义，非缺陷）。

**用户可见行为**：无直接可见面；D-07 的 understanding-dimensions API 与 D-08 的五维迁移证明是它的两个消费出口。

### D-04 · 真实 Analytics 接线并清除生产 Mock 缓存污染

**交付（首轮 dual-reviewed + wt651/wt656 两批清污 + FIX 族）**

| 波次 | 主干 SHA | 内容 |
|---|---|---|
| 首轮 | `5ed3d20d`（feat，dual-reviewed） | 统计 provider 接真实 route/DB、mock 写 Isar 暖缓存清除、demo namespace 隔离；KNOWN_CODE_DEBT_LEDGER #1/#2 统计 mock 债随之销账（`dd7b7486` 注记，原文保留防断链） |
| wt651 审计+首批清污（09-27） | 修复 `c575e6a4`（原 worker 79ad6a90 重提交） | `v3-output/WT651-D04/audit.md`：12 条真轨+4 条受控 demo 轨+**5 条污染点**（登记 345~349，集成撞号重编号 **FIX-350~354**）；首批修 350/351/352 |
| wt656 二批清污 | 修复 `4130f984`+`053bc564` | FIX-353 UserDailyMetric 零写入表被读侧当测量值（改实时真源聚合）+FIX-354 mobile UserAnalyticsEvent Isar 死集合删除 |

**五条污染点终态（本档台账逐行复核，全部 FIXED）**：FIX-350 enhanced_orchestrator 休眠 mock 轨（假知识图谱 50 节点/假掌握度 0.85）删模块+退役守卫@c575e6a4；FIX-351 /stats/overview streak_days 用 flame_level 冒充连续天数——删冒充字段@c575e6a4；FIX-352 /predictive/engagement 硬编码空承诺键——删 4 键@c575e6a4；FIX-353 UserDailyMetric 空表冒充「Total Focus Time: 0 minutes」进 LLM 上下文——读侧改实时聚合@4130f984；FIX-354 Isar 死集合 uae_815——删模型+schema 注册@053bc564。注释号错位（345→350 等）由 FIX-371 收口@7aa46c04。

**受控 demo 轨（非污染，V4 须知）**：4 条门控+自述轨（DEMO_MODE 编译期量/demo_guest_mode_enabled pref 等，WT651-D04 audit.md §三·附1）；后续 V3-FIX-363 社群兜底模板披露化（`6dfe2ad5`）明确引用「D-04 受控轨 #1 门控合法」为同类先例。

**残差**：① B-02 的红测 `mock_statistics_guard_test.dart` 仍不在主干（B 线章已记，本线不重复占号）；② FIX-37（D-04 follow-ups：时区偏差 heatmap 上界排除晨间会话/窗口近似 custom 被忽略等）FIXED@0c1ea188，但其证据指针 v3-output/D-04/REVIEW_RECEIPT_2.md 是死路径（§D.5-509）；③ agent-stats 四端点维持 FIX-330「如实 unavailable」（agent_execution_stats 表零生产写入方）——真零非假零，V4 若接写侧须同步四端点。

**用户可见行为**：统计面不再出现 0.95/4.2 型 mock 固定值与 flame 冒充 streak；断网走 last-known-real/unknown；演示数据仅显式 demo 门控轨可达。

### D-05 · Intervention → Outcome 分析管线

**交付（首轮 R2-reviewed + FIX-31 批清）**

| 波次 | 主干 SHA | 内容 |
|---|---|---|
| 首轮 | `11af43cd`（feat，R2-reviewed） | `app/core/intervention_lifecycle.py`（契约）+ `backend/app/services/intervention_lifecycle_service.py`（现 962 行）+ 迁移 d05_20260919：exposure/response/outcome 关联生命周期、唯一约束幂等（uq_intervention_lifecycle_once + ON CONFLICT DO NOTHING）、漏斗完整性（无 exposure 的响应拒收、shadow/inert 拒绝 exposure）、outcome 白名单双层门（chat reply/sentiment 类两层都拒）、censored 三态分解+Wilson 区间保守关联摘要 |
| 批清（wt662） | `49d81fb2` | FIX-31 六项收口：watermark 全集指纹（公开 watermark() 与摘要内水印构造性相等，M-06 缓存失效面消除）、并发双写显式测试等（P2-1 已由 M-06 e56be400 消费面修复） |

**本档代码亲证 + 关键发现（V3-FIX-507，本档新登记）**：读侧接线确认——evidence_insight_service.py:189 与 experience_memory_projector.py:131 真实消费 association_summary；north_star_wvpl_service 经 D-05 lifecycle 取 intervention 面。**但写路径全仓生产面零调用**：`grep -rn "record_exposure\|record_response\|record_outcome_association\|associate_pending_outcomes" backend/ scripts/ tests_e2e/` 的非测试命中仅服务自身；唯一调用方=backend/tests/q04_personal_redteam/engine.py:565、backend/tests/d08_flywheel/engine.py:668、backend/tests/aurora_ablation/engine.py:517（三个评测 harness）+单测。InterventionEventConsumer（交付管线，断点 4）不触 lifecycle。测试计数：service 36 + contract 46 + migration sqlite 3。

**残差**：① **生产写面缺位（见 §D.4 与 §D.5-507）**；② FIX-31 的证据指针 v3-output/D-05/REVIEW_RECEIPT.md 死路径（§D.5-509）；③ outbox 事件只是集成通知（表缺席诚实跳过），自有真源是 intervention_lifecycle_events 表——该表当前生产零写入。

**用户可见行为**：无直接可见面；它是 D-07 两类洞察卡与 M-06 经验记忆的数据供给方——在当前主干形态下，这两类卡在生产部署中将因无数据而整面静默缺席（「无数据不出卡」守卫生效=诚实，但产品承诺面落空）。

### D-06 · WVPL 北极星查询与事实 JSON

**交付（首轮 R2 PASS + 证据包补全轮）**

| 波次 | 主干 SHA | 内容 |
|---|---|---|
| 首轮 | `c90641c0`（feat，R2 PASS） | `app/core/north_star_wvpl.py`（口径 v1 冻结）+ `backend/app/services/north_star_wvpl_service.py`（现 634 行）：确定性 SQL 聚合零 LLM（golden pin 断言守卫）、build_fact(as_of) 幂等逐字节可重复、provenance.source_queries+sample_event_ids 可审计、有界扫描触顶如实 truncated=true；/admin/north-star 只读暴露（router.py:258，superuser） |
| 证据包补全（wt653） | `8a0a868f` | **golden docstring 引用的 v3-output/D-06/REPORT.md 此前从未入库**（承诺证据未 commit 的静默形态）——以集成 HEAD 全新实跑补齐：22+19+4 测全绿、变异 4/4 红绿、OpenAPI 899==899 零漂移；验收 1 完成级判定、**验收 2 运行级四项列清单待升栈补验** |

**本档代码亲证**：与 D-02 谓词一致性策略=只引用 D-02 冻结导出常量不复制字面值（tests 词表一致 pin）；真源消费走 D-02 公开 API 零重复实现。测试：service 16 + api 3 + golden 族。

**残差**：① 验收 2「可在 staging 真实跑」运行级四项待升栈补验（wt653 列清单在案；与 O-01 云凭据解锁同窗口可做）；② REPORT 补全事件本身说明「golden 引用证据未入库」是 V3 的真实失效形态（本档 FIX-509 与之同族）。

**用户可见行为**：无直接可见面（admin 只读端点+事实 JSON 供 LLM 解释消费）；「模型不计算数字」由 golden pin 结构性保证。

### D-07 · Evidence-driven Insights 产品重构

**交付（本体 + 独立会话诚实性增量 + 重编号修复链）**

| 波次 | 主干 SHA | 内容 |
|---|---|---|
| 本体（wt369） | `667001e6` | GET /insights/evidence-cards：五要素卡（fact/interpretation/uncertainty/evidence/implication）×三类洞察——friction pattern 读 D-05 friction_tag 聚合、interventions that helped 读 D-05 association_summary（证据不足切片不发卡）、goal progress 复用 A-07 Goal/Task 读侧双口径；全派生现算、纠正落库后下次读取即更新、零置信百分比零分数族键、无数据不出卡不生成人格结论；mobile 五要素洞察卡+证据深链（decision log·goal ledger 可点）接入洞察总览顶部（learning_insights_overview_screen.dart:96 EvidenceInsightSection 本档亲证）；**假精确面删除**：PredictiveInsightsCard 整体删除（置信度%徽章/精确到时刻预测/风险指数分数条/难度分条），lfcConfidence 改样本观察口径；红测先行（base 5 用例 404 全红+mobile 诚实性测试渲染 90%/72/100 即红） |
| 诚实性增量（wt666） | `b92ae2ec`（原 worker 7a914a2c 重提交） | 删失语义拆分（FIX-359，原登记 357 撞号顺延）：not_yet_observed 只含未到期删失，window_closed/user_churned/unknown 合并进 not_determinable 新行——「不会有可判定结果」不再伪装成「还没到期」；insufficient 哨兵文案「证据不足，暂不下结论」（低报不虚报）。本档亲证：evidence_insight_service.py:209-215 拆分注释与实现在位 |

**三类洞察卡的真实数据流判定（本档核心结论，任务问的「真数据 vs 结构就绪」）**：
- **goal progress 卡：有真数据支撑**——读 A-07 Goal/Task 生产表，任何真实用户有目标即出卡。
- **friction pattern 卡与 interventions-that-helped 卡：结构就绪、生产零数据**——供给方是 D-05 lifecycle（写路径零生产调用方，§D.2-D-05/FIX-507），「无数据不出卡」守卫使它们在生产部署中不出卡而非出假卡。
- understanding-depth/understanding-dimensions 面：真数据（celery beat 每日聚合真实生产表，D-03）。

**残差**：① **卡面验收「Simulator 能理解至少 3 条 insight 意义」未定位到证据**（tests_e2e/、journey harness、WT397 产物全扫零命中；wt369 交付的是 backend 5/5+mobile 定向 6/6+smoke 16 的测试面证据）——销账依据=交付本体+wt666 独立增量复证，此验收项按「未定位到证据」如实留档；② FIX-361 置信度百分比族 8 键 6 面（本卡清了 lfcConfidence 后的残余）已由 wt685 定性化收口@53414f8a；③ 无正式 review receipt（独立复核以 wt666 增量形式发生）。

**用户可见行为**：洞察总览顶部出现可点证据深链的五要素卡；预测仪表盘的假精确面（置信度%/风险指数/精确时刻预测）从产品消失。

### D-08 · 数据飞轮纵向证明与 Regression Dashboard

**交付（本体 + 复证轮，双证成立、receipt 明确欠）**

| 波次 | 主干 SHA | 内容 |
|---|---|---|
| 本体（wt397） | `46762b31` | 10/10 persona Day0/Day3/Day7 双臂配对（flywheel vs no_feedback 同世界同探针零反馈）：旅程纠正垫后 14 条链（adjusted_by_correction=True+对照差分成立，含 p05/p10「纠正让类型更对但行动更差」有害适应 4 条）+记忆变安静 10 条链（deny×2+retract 后 Day7 旧偏好 0/10 注入 vs 对照 10/10）+**25 条无效/无效力/有害个性化全部照登**（patch 改序不改局 11/Day3 未变安静 10/有害 4）；理解五维 10/10 从 unknown 迁移到可计算值（correctness 1.0→0.33 真实撤回落账）；评估对象全真实服务面（StuckJourney+FrictionChatWiring+ContextPackBuilder 全漏斗+MemoryService+D-03 五维+Stage20 确定性 judge+D-05 lifecycle+A-05 证据门）；模型 judge 0 次；dashboard 全由 raw 程序化复算（--verify-repro 双跑逐字节一致 exit 0）；产品代码零改动；新测 7/7 契约锁+邻域 264 绿 |
| 复证（wt669） | `41aee60c` | HEAD(0495e085) 全量 --verify-repro 双跑一致；验收 10/10 保持（承载腿从旅程14+记忆10 变为记忆10+旅程4——FIX-50①诚实 no_action 饿死纠正入口的纵向同构实证，不新开号）；五面漂移逐条归因（memory_not_quieter 10→0=FIX-70 真修、ineffective_patch 11→5=FIX-67 诚实化、harmful 4→0 同账）；**「review receipt 仍欠（首轮 READY_FOR_REVIEW 未检得独立签收）」原文在案** |

**产物与复跑路径（V4 直接可用）**：`v3-output/WT397-D08-FLYWHEEL/{dashboard.json, DASHBOARD.md, REPORT.md, raw/{flywheel,no_feedback}.jsonl}` + `scripts/devtools/d08_run_flywheel_eval.py`（--summarize-only 从 raw 复算 / --verify-repro 全量双跑断言）。WT669 复证产物另存 v3-output/WT669-D08-RECHECK/。

**真实数据流的诚实边界（V4 必读）**：10/10 闭环里的 lifecycle 写入（exposure/response/outcome 关联）由评测 harness 引擎直接驱动（backend/tests/d08_flywheel/engine.py:668），不是产品交付路径产生的——证明的是「服务面在事件到位时会正确联动」，不是「生产流量会自然产生这些事件」（后者归 FIX-507）。数字本身全部真实表取数、零模型 judge、可复算。

**残差**：① 独立审查 receipt 欠（wt669 复证是独立会话双证，非正式 receipt——wt759 标 📌⚠，tasks.json 销账 dba6aaf2 以此为依据之一，本档判定：销账成立、证据形态弱于验收模型要求）；② DEFERRED 三项：经验 spine 纵向面（TTL×可控时钟，归 A-08 权威）/utility outcome 因果联动（D-02 接入 reserved）/>10 persona 扩展；③ >500ms 目标类 SLO 不在本卡（归 E-08）。

**用户可见行为**：无直接可见面；它是 Q-08 final gate 的前置（wt759 依赖序：Q-08 唯一剩余前置=Q-07，上游含 D-08✓）。

---

## D.3 设计决定与取舍（从提交/审查考古）

1. **契约冻结+显式扩词表流程**：D-01 词表 sha256 双冻结进测试字面量，扩词表必须显式 re-freeze（33→36→39→40，每次留 changelog 注释：X-02/M-07/X-05/S-04）；observed_unregistered 状态处理「观察到但无维护者」的名字而不假装封闭。取舍：改词表摩擦大，换来事件域无自由字符串。
2. **读模型优先、零 schema 变更**：D-02/D-06 全部纯读层（聚合既有表、确定性 id、keyset 分页），不建新表不写库——「账本」是逻辑对象不是新存储。取舍：查询层复杂度高（五源谓词/跨流全序），换来了零迁移风险与真源不增殖。
3. **「声明不构成证明」贯穿证据分级**：D-02 的 EvidenceTrustTier（user 断言永不升 actual/pipeline_echo 永不升 actual/focus 覆盖率按比例）、D-06 的零 LLM golden pin、D-07 的无数据不出卡——同一教义在三层各自落地。
4. **假精确面做减法而非加警示**：D-07 直接删 PredictiveInsightsCard 整卡+18 死键收割，而非给假精确数字加免责声明；删失语义拆分（FIX-359）同样是把「不确定」诚实分型而不是统一话术。
5. **发现与修复分离纪律在 D 线的变体**：D-04 的 wt651 只做审计+低风险首批（345~349 登记），第二批 wt656 接力（353/354）——撞号重编号（→350~354）与注释号错位（FIX-371 再修）是这条纪律的集成成本实证。
6. **评测 harness 直接驱动服务面**：D-08（与 A-08/Q-04 同构）不建产品旁路，harness 调真实服务引擎+可控时钟+确定性 judge——代价是「服务面被证明」与「生产流量存在」的分离（本档 FIX-507 即此分离在 D-05 上的显形）。

---

## D.4 残差与 V4 注意点（汇总）

1. **飞轮中段写面缺位（最高优先）**：D-05 lifecycle 生产零写入方（V3-FIX-507，本档登记）。V4 做 Insights/Experience Memory/任何「越用越懂我」功能，第一步是把 record_exposure/record_response 接进干预交付路径（InterventionEventConsumer/notification/P 线交付点）并把 associate_pending_outcomes 挂定时扫描——否则 D-07 两类卡与 M-06 经验投影在生产永远空转。
2. **台账证据指针死链（D/E 线扩展，V3-FIX-509）**：D-04/D-05/D-07/E-03/E-04/E-06/E-07 卡级 REPORT/RECEIPT 从未入库，台账三处死指针（FIX-31/FIX-37/FIX-41）。V4 的记账工具应把「证据路径存在性」做成机器检查（同 FIX-502/504 的教训合并处理）。
3. **两卡证据形态弱于验收模型**：D-07/D-08 无正式 review receipt（前者以 wt666 独立增量、后者以 wt669 独立复证双证成立）；D-07 的 simulator 理解验收未定位到证据。V4 若继承 Insights 面，建议补一份正式独立审查覆盖这两卡。
4. **D-06 staging 运行级四项待升栈**：与 O-01 云凭据同窗口解锁即可补验；golden/fixture 确定性面已完备。
5. **agent-stats「如实 unavailable」态**：真零非假零是对的，但 V4 若接 agent 执行统计写侧，四端点与 agent_execution_stats 表要同步激活，否则继续 unavailable。
6. **受控 demo 轨是合法形态**：D-04 确立的「门控+自述」先例（WT651 附1 + FIX-363 援引）应作为 V4 演示数据面的标准形态，而非 ad-hoc 处理。
7. **D-01 遗留四个 R2 移交项**（F2 fail-open 真值门/F6 gateway 第二 envelope/F7 outbox 清理 vs lineage/F8 双 commit 窗口）——都不是阻塞项，但 V4 做跨层事件面统一时应清点。

---

## D.5 本次审查登记

- **V3-FIX-507**（P2，本次新登记）：D-05 intervention lifecycle 写路径零生产调用方——record_exposure/record_response/record_outcome_association/associate_pending_outcomes 全仓生产面零调用（唯一非测试调用方=d08_flywheel/q04_personal_redteam/aurora_ablation 三个评测 harness 引擎）；读侧（D-07 evidence_insight_service 两类卡+M-06 ExperienceMemoryProjector 经验投影+north_star_wvpl intervention 面）全部已接线且诚实守卫生效（无数据不出卡）——生产部署中干预漏斗数据面静默缺席。危害定性：不是不诚实（守卫使空面不出假卡），是**产品结构就绪与生产数据流的断裂**被测试全绿掩盖；D-08 的飞轮闭环证明是 harness 驱动，不能外推为生产流量事实。修法方向：交付面（InterventionEventConsumer 标记 delivered 处/Aurora decision 执行点）调 record_exposure+record_response，D-02 ledger 增量扫描定时任务调 associate_pending_outcomes。
- **V3-FIX-508**（P2，本次新登记，归 E 线章详述——wt761 批三行台账未闭）：V3-FIX-491/492/493 三行行尾状态格 OPEN 零 FIXED@，而修复本体 wt761 `1e3b6ebf`（2026-09-28 01:35）已在主干（merge-base --is-ancestor 判祖先）：491 auto_degrade 审计 publish 双参签名+sparkle_slo_auto_response_audit_publish_failures_total 计数器、492 plan_review daily_hours None 守卫、493 event_registry docstring 契约段改写。与 V3-FIX-504（FIX-258 行闭账丢失）同族第三例——本次成因是「集成合入后未回写台账」而非行重建回退。V3-COMPLETE-STATUS-FOR-V4.md §5「491/493 收口」表述与台账互相矛盾，以代码为准。修法：三行置 FIXED@1e3b6ebf。
- **V3-FIX-509**（P3，本次新登记）：D/E 线卡级证据断链（V3-FIX-502 同型扩展）——v3-output/D-04、D-05、D-07、E-03、E-04、E-06、E-07 七目录从未入库（git log --all --diff-filter=A 全零命中）；台账死指针三处：FIX-31→v3-output/D-05/REVIEW_RECEIPT.md、FIX-37→v3-output/D-04/REVIEW_RECEIPT_2.md、**FIX-41(P1)**→v3-output/E-04/REVIEW_RECEIPT_2.md。wt759 以 commit message 签收字样（dual-reviewed/R2 PASS/reviewed）核验故销账结论不受影响；两个修复本体（FIX-37@0c1ea188、FIX-41@1ae6a9e1）均真实在主干。修法三选一同 502（回收原件/批量注记纠指/按台账行重建最小 receipt）。
- 复核过但**不构成新发现**的三项：D-08 receipt 欠（wt669 自报+wt759 📌⚠ 在案，属已知残差非新发现）；D-07 simulator 验收无证据（按「未定位到证据」留档于本章 §D.2-D-07 残差①，与 D-08 receipt 同属证据形态弱面，不另占号）；FIX-345~349 撞号重编号与注释错位（FIX-371 已收口@7aa46c04）。
- 号占用核验：507 起占用前 grep 复核——主仓 v3/ v3-output/ docs/ backend/ `V3-FIX-50[5-9]`/`V3-FIX-51[0-2]` 零命中；499~504 已占用（499=wt767、500/501=wt765、502/503=wt770、504=wt769）；505/506 为在航兄弟会话（wt774-AJ/wt775-UPSG）预留段，本档顺延取 507/508/509。
