# B 线（Baseline 6 卡）深挖章节 —— V4 交接文档素材（wt769）

> 本文是 `v3/V3-COMPLETE-STATUS-FOR-V4.md` §4「各线深度状态」B 线章节的深挖草稿。
> 证据纪律：只写三源证据（git 主干 SHA / 独立审查 receipt / 运行级实测）支撑的事实；逐条标注出处；无法定位证据的验收项显式标注「未定位到证据」。
> 撰写：wt769（2026-09-28，基线 main@b129040c）。方法：卡面（v3/07_tasks/cards/B-0*.md）+ `git log --grep` 逐卡定位 → 当前主干代码存在性逐一开文件核实 → 测试文件计数 → v3-output notes/receipt 抽读 → 台账闭环逐条复核。**未轻信任何台账/报告结论性文字。**

---

## B.0 线级概览

B 线是 V3 的「地基测量线」：在动任何产品卡之前，先把「有哪些功能、数字从哪来、怎么自动化验证、长什么样、AI 真实能力边界在哪、概念映射到哪些实体」六个真相钉死。6/6 全部 done（tasks.json 8d4291aa 核正 + fleet done 名单 + wt759 三源核验报告 v3-output/WT759-RECON/report.md 逐卡 SHA 在案）。

执行形态的显著特点（V4 设计者需要知道）：**6 张卡里 4 张（B-01/B-02/B-05/B-06）是零产品代码改动的审计卡**——交付物是 v3-output 下的机器可读盘点（CSV/JSON）+ 报告 + 独立审查 receipt；只有 B-03（simulator harness）和 B-04（视觉基线 harness）产出可复跑的测试基建代码。B 线的价值不在代码量，而在它后续「生出来」的 FIX 流：B-02 一张卡直接/间接催生 FIX-01/256/257/258/329/330/331，B-06 催生 FIX-259/260/275/276/289/290/291/355(→356)。**B 线是 V3 诚实性红线的第一执行者。**

另一特点：**B 线交付不是一次性的**。B-01 在 09-19（42 feature 生死簿）之后于 09-27 被 wt639 以同一张卡重开为 759 模块四态全量审计；B-03 在 09-19 之后于 09-27 被 wt654 收口为 v2 统一契约；B-04 的 27 张 golden 经历 d7a961da→87b5f432→b8c94477 三轮重锚。V4 若复用这些基线，**以各卡最新一轮为准**。

---

## B.1 意图（卡面目标与验收）

六卡共性 Forbidden 条款（卡面原文，全线一致）：不得重建已存在的权威真源；不得用 mock/seed 冒充真实行为；不得只通过静态代码阅读宣称用户体验通过；不得弱化既有安全/幂等/隔离/审计守卫。Worker 只能提交 READY_FOR_REVIEW/PARTIAL/BLOCKED；Reviewer 必须独立执行关键验收。

| 卡 | Risk/Resource/Reviewers | 卡面目标（一句话） | 卡面关键验收 |
|---|---|---|---|
| B-01 42 模块产品生死簿 | medium/LIGHT/1 | 从当前 HEAD 建真实功能 portfolio，定 CORE/CONTEXTUAL/LABS/HIDDEN/RETIRE，不凭旧文档 | 42 feature 100% 有唯一状态与证据；CORE/CONTEXTUAL 每项映射至少一条 Golden Journey；HIDDEN/RETIRE 用户不可达；产出 MODULE_MATRIX.csv + portfolio.json |
| B-02 数据真实性/Lineage | high/LIGHT/2 | 盘清每个用户可见关键数字的来源，阻止假数据进 V3 | 核心 Journey 数字全有 lineage（标 actual/self_reported/estimated/demo/unknown）；mock 污染有可复现证据；seed/demo namespace 可查询区分；产出 data_truth_inventory.json/csv |
| B-03 Journey Simulator Harness | medium/HEAVY/1 | 把「Agent 真正使用 App」固化成可重复测试基建 | 三平台可重复启动或明确 unsupported 原因；run 产出 build SHA/device/time/截图/日志；失败返回非零（不允许「没找到模拟器=PASS」）；simulator 不绕过 UI |
| B-04 视觉基线 + L2–L5 Review Harness | medium/HEAVY/1 | 建立可比较的真实截图基线，后续 UI 卡以视觉证据闭环 | 核心 9 surfaces × 主要状态有 baseline 且来自真实渲染；每张图有 build SHA/persona/state；产出首轮视觉问题 ledger |
| B-05 模型/Embedding/语音/OCR/成本 Probe | high/MEDIUM/2 | 以当日真实凭据探测 AI 能力，不沿用旧模型清单 | 输出 capability_matrix.json + latency raw samples；LIVE 缺 key/失败不命中 fixture；给 E 系列卡真实 SLO 基线；每实时路径 ≥10 样本 |
| B-06 核心实体映射与重复真源审计 | high/LIGHT/2 | 把 V3 概念映射到现有权威实现，防止 Agent 造第二套系统 | 四分法 State/Memory/Knowledge/Events 可映射到当前实体；Aurora/Agent Runtime/Action 无两个权威 owner；产出 ENTITY_MAP.md/json，后续任务必须引用 |

---

## B.2 实际交付逐卡

### B-01 · 42 模块产品生死簿与可达性真相

**交付（两波，均零产品代码改动）**

| 波次 | 主干 SHA | 内容 |
|---|---|---|
| 波 1（2026-09-19） | 合入 `1083f4f5`（B-01/B-05 ACCEPT merges） | `v3-output/B-01/`：MODULE_MATRIX.csv（43 行）、portfolio.json（638 行 machine-readable）、REPORT.md、REVIEW_RECEIPT.md（独立 Reviewer verdict **ACCEPT**，含勘误与 GJ 框架说明）、changes.patch（768 行） |
| 波 1 补充 | `012ab490`（09-23 live acceptance PASS）+ `63848706`（CHAT-VISIBLE 修复） | 首轮会话 0→1 的实时验收：WS turns 未建 chat_sessions 头导致首会话不可见的真缺陷修复后过验 |
| 波 2（2026-09-27，wt639） | `15a88876` | 重开为 759 模块四态全量审计（v3-output/WT639-B01/lifecycle.md）：backend services 顶层 410+orchestration 92+子包 20、api/v1 路由组 109、gateway 代理面 84、mobile features 44 → **690 ALIVE / 55 PARTIAL / 12 DEAD / 2 ORPHAN** |

**波 1 关键结论（42/42 全定级，零 UNKNOWN）**：CORE 15｜CONTEXTUAL 18｜LABS 5｜HIDDEN 4（leaderboard/photon/reflection/shop）｜RETIRE 0。leaderboard 判死屏（GoRouter 未注册+全仓 0 引用+快照表 0 行）；shop 形式可达但 shop_items/shop_purchases 0 行（空目录违 D20）；六类表完全零写入。Reviewer 复核发现 shop HIDDEN 判定与 1 条真实入口（streak_details_screen.dart:415）矛盾 → 开 V3-FIX-05。

**波 2 新发现六项不诚实面（V3-FIX-337～342，逐条经人工开文件复核+import 索引机械扫描 502 模块）**：
- FIX-337 /push/interaction 断链（mobile 唯一写方→网关 404→端点零到达）——**FIXED@7e8bc1a7**
- FIX-338 GDPR login_attempt_cleanup beat 条目未入 worker include（宣称执行≠执行）——**FIXED@b3481580**
- FIX-339 guest_cleanup 两任务零 include/零 beat/零入队（孤儿任务）——**FIXED@92e750fb**
- FIX-340 update_similarities 4 任务不可达（协同过滤零写入的机制成因）——**FIXED@ef5fd0c9**
- FIX-341 GraphRAG monitor 翻旗也不可达（flag 双闸+网关无代理组）——按 by-design 收口（面删除+AT 豁免@d5175285+守卫 tests/api/test_graphrag_monitor_face_removed.py+「重建须三件齐上勿单翻旗」警示注记）
- FIX-342 onboarding 交互式引导 4 屏零路由零引用（孤儿屏）——**FIXED@e610853e**

**验证证据**：波 1 方法=GoRouter 注册表+跨 feature 引用分析+gateway 路由枚举（273 条 method+path）+运行中网关未鉴权 curl 探测+psql 只读 248 表 n_live_tup；Reviewer ACCEPT 且修正报告 6 处细节（含「无 GJ 的 9 项实为 7 项」勘误）。波 2 方法=全仓 import 索引（app/tests/tests_e2e/scripts 四域、五种引用形）+每个 DEAD/PARTIAL 判定人工开文件复核（gRPC bootstrap 等索引盲区校正）。

**残差**：① rule-bj 豁免的 9 个 v1 未接线组件（bert_intent_classifier/intent_cache/evaluator 族等），其豁免头指向 KNOWN_CODE_DEBT_LEDGER.md 是 dangling 引用（豁免真实登记面在守卫与接力日志）——audit 判 DEAD，机制在账；② `services/community_context_boundary`（528 行，S-02 群上下文隐私红线单一守卫面）零生产 import——已有 orphan-by-design 豁免登记（docs/aurora/rule_at_exceptions.md:39，移除条件=群 AI prompt/tool 面接入时），**V4 若做群 AI 面必须接线它，否则隐私宣称持续大于保障面**；③ 42-feature 层级的 portfolio.json 是 09-19 时点快照，759 模块级以 wt639 为准。

**一句话用户可见行为**：无直接用户可见行为（审计卡）；它决定了 leaderboard/shop/photon 保持 HIDDEN、长尾维持降级的 V3 事实产品边界。

### B-02 · 数据真实性、Mock 污染与指标 Lineage 基线

**交付（主卡 + B-02X 扩展 + 两轮后续审计，全部有独立审查）**

| 步骤 | 主干 SHA | 内容 |
|---|---|---|
| 主卡交付 | `96004ea5`（READY_FOR_REVIEW） | 22 个用户可见数字全链 lineage（UI→repo/API→DB/event/formula），lineage.csv + data_truth_inventory.json/csv + FINDINGS.md |
| R1 CHANGES 处置 | `51f5acd7` | 独立 REVIEW_RECEIPT：C1 红测未收编、C4 SQL 补 deleted_at、C3 DB 快照漂移标注等全数处置 |
| R2 处置 | `1083f4f5`（C5/C6/P3） | 第二路审查 remediation |
| B-02X 扩展 | `e79eed0e` | 第二路 Reviewer 建议的 9 项数字 lineage 补全 + INV-15（社群 331/331 帖全为 guest/seed 作者）+ 4 处主卡 lineage 失实修正（如「weekly narrative 是 LLM 生成」实为规则模板、「缓存 7d」实为周锚+2d grace） |
| F1 修复 | `4c963ef4`（V3-FIX-01，P0） | 全局排行榜排除 guest/seed cohort——**当前主干核实：leaderboard_service.py:62-65 `EXCLUDED_COHORT_REGISTRATION_SOURCES = ("guest","seed")`，:259/:648/:717/:786 四处过滤在用** |

**两条最高严重度发现（可复现，D20 违例）**：
- **F1** 排行榜 top-50 100% 被游客种子号占据（服务权重公式无 registration_source 过滤；实测复算 guest 50 席、top_score 132.5、email 0 入榜）→ FIX-01 已修（见上）。
- **F2** `IsPro = FlameLevel >= 3` × 游客种子 flame_level=15 ⇒ 所有游客以 is_pro=true 送入 AI 路由（gateway user_context.go:129 + chat_orchestrator_chatflow.go:284 双点）。

**后续审计链（证明 B-02 不是一次性卡）**：
- wt533（`0b928770` 登记）：FIX-256（P4 gen-l10n 格式漂移，**仍 OPEN**）；FIX-257 guest 转正不清洗种子伪造统计——**FIXED@2b32d728**；FIX-258 demo 产出落库与真实产出 schema 层不可区分+mock 喂记忆推断——**修复在主干 `52fbed29`**（ChatMessage.origin 列+记忆推断 demo 轮整轮跳过+迁移 f258_20260925+326 行测试），**但台账行仍标 OPEN**（→ 本次审查登记 V3-FIX-504，见 §B.5）。
- wt624（`b140bb9b` 登记）：FIX-329/330/331（flame 时钟修漏/agent-stats 真空/mock 残轨）——均 **FIXED**（a6b6e19b/773f2055/cb9a1f79）。

**验证证据**：双 Reviewer（卡面要求 2 份，REVIEW_RECEIPT.md + REVIEW_RECEIPT_2.md 均在 v3-output/B-02/）；DB 结论全部为主仓 psql 只读复算 SQL 原文+结果；复核修订如实标注时点快照漂移（users 219→248 等）。

**残差**：① **红测 `mock_statistics_guard_test.dart` 至今不在主干**——卡面「先写红测」未以文件形式兑现；Reviewer R1 以 C1 抓出（四处引用该文件为钉子），处置方式为如实改表述（机制以代码链路+dart run 探针实证）而非补交文件——这是 B 线唯一的「卡面承诺未以交付物兑现」面，V4 若重做 mock 防线应先补此测；② mock 污染路径（core/statistics 三 repo 的 fetchFromApi 假数据可写 Isar 生产缓存）按卡面「先写红测，不必本卡全部修」留作后续任务映射，修复状态以 FIX 族为准（FIX-329~331 已收三条）；③ 全部 DB 计数为时点快照。

**一句话用户可见行为**：排行榜不再被游客种子号霸榜（FIX-01）；游客转正后不再携带伪造统计（FIX-257）；demo 模式产出在数据层可区分且不再污染记忆（FIX-258）。

### B-03 · 跨端 Journey Simulator Harness 基线

**交付（主卡 + v2 统一化收口）**

| 波次 | 主干 SHA | 内容 |
|---|---|---|
| 主卡（2026-09-19） | 合入 `ee885386`（ACCEPT single-review deep pass） | 三平台 harness + **Android Isar .so 启动即崩高危产品修复**（经真实 UI 截图+logcat 双通道验证）；`v3-output/B-03/{REPORT.md, HARNESS.md, EVIDENCE_INDEX.md, REVIEW_RECEIPT.md}`；harness 演进清单 13 项（`scripts/devtools/journey_harness/`） |
| 附带登记 | `86f3ed6d` → **FIXED@e460f192**（V3-FIX-17） | Web 注册静默假失败（后端 200 建号成功、App 误报网络错误卡死，5 连复现+三层定界锁定 Flutter Web Dart 侧）——B-03 的产品级发现，红测先行修复 |
| v2（2026-09-27，wt654） | `c72a8c45` | 统一化收口：run_manifest 自标识 `sparkle.journey.simulator.run.v1`+simulator-ui/nonui 互斥 lane（防仿真结果冒充真实驱动，FIX-330/333 同族纪律）；persona library 单源（v3/05_metrics_eval/persona_library.json，未知 id 加载期报错）；set_network 统一步（web=CDP/android=飞行模式回读/macos+api 诚实 unsupported）；clock 裁决块；**tests/ 新增 24 用例实跑 24 passed**（loader 10/markers 7/policies 7，含 CLI 失败非零端到端钉） |

**三平台实测状态（09-19，GJ01 最小壳）**：macOS **PASS**（完整访客 journey 12 截图，退出码 0，2m15s）；Web 最小壳 **PASS** / GJ01 全程被上述产品缺陷诚实阻断（即 FIX-17）；Android **PASS 4/4**（含 assert_logcat_absent 崩溃断言——首轮真抓到 IsarError 启动崩）。失败路径全部非零退出码；simulator 不绕过 UI。

**验证证据**：EVIDENCE_INDEX.md 收口（run manifest 带 device/serial/build SHA/截图/日志引用）；REVIEW_RECEIPT 独立签收；v2 的 24 用例为 backend venv 实跑实录（WT654-B03/REPORT.md）。

**残差**：① GJ08 纠错记忆 240s 未落库两连败（API lane）——B-03 报告如实留为诊断线索，**本次未定位到该线索的闭环记录**（V4 可作为记忆管道性能诊断入口）；② Android 构建工具链三坑（JDK 25 被拒/外置卷 gradle 失败/gradle.properties -Xmx8G 事故级配置）——本机环境面已记 HARNESS.md，8G 配置入库调整未见后续提交；③ Web/Android 的 GJ01 全程在 FIX-17 修后未在本卡内重跑（v2 是契约层收口非重测）。

**一句话用户可见行为**：无直接用户可见行为；期间修掉「Android 装上就崩」和「Web 注册谎报网络错误」两个真实用户阻断。

### B-04 · V3 视觉基线截图与 L2–L5 Review Harness

**交付（wt667 重做版为现行基线，三轮重锚）**

| 波次 | 主干 SHA | 内容 |
|---|---|---|
| 初版（09-21） | `55ac467c`（phase 1）+ `fdf8204a`（9/9 verified） | 首轮 harness+onboarding 基线；后因锚点混杂被后续轮重做 |
| wt667 重做（09-26） | `134aff9f` | **9 surfaces × 3 viewport = 27 张真实渲染 golden**（`v3-output/B-04/screenshots/`，routerProvider+matchesGoldenFile 真出图）+ manifest/verify/coverage 三命令链（sha256 事实源）+ GBNF 六元组命名（surface__state__persona__platform__viewport__sha8）+ 首轮视觉问题 ledger（A0/B3/C4+环境限制 2）+ 采集 harness `mobile/test/goldens/b04_visual_baseline/`（431 行 b04_harness.dart）+ states.py 注册表两处裁决修正 |
| 容差修复 | `9ecfa547`（FIX-383 FIXED） | B04TolerantGoldenComparator 容差单位错位 0.5→0.005（分数口径钉死 0.5%） |
| 重锚 | `bb84e122`（wt693，锚 87b5f432）→ `70998cdf`（wt708 全量重采 **27 张单锚 b8c94477**，混锚消解） | 现行基线=单锚态；FIX-395（混锚运行缺陷）FIXED@4b5b351f |
| L-01 闭环 | `bd576cd7`/`68c385f6`（FIX-376 FIXED@e0777bd5+c69f55b7） | ledger 首要 B 级项（home demo 首屏错误文案裸露）真修收口 |

**卡面冲突裁决（消费面亲证，体现「不轻信卡面」纪律）**：卡面 goal 入口 `/goals` 不存在（实为 `/plans`）→ states.py 修正；chat 引用条非 demo 数据自带 → canonical fixture 注入走真实渲染管线（构造期注入被 reload 冲掉曾红，红测留证后改加载后注入）；macOS 批 flutter_tester 无平台字体产生字形伪影 → 登记 B-04-ENV-1，文字审查权威=android 批。

**验证证据**：采集+复验双跑全绿（`--update-goldens` 落 27 张→比对复验 27 绿）；manifest/verify/coverage 命令链 exit 0；首轮无容差 comparator 0.01% 即红（红测先行留证）；12 维 rubric 逐面评分表在案；产品代码零改动。独立审查：REPORT 标 READY_FOR_REVIEW；后续轮 wt694 对 U-02/U-05 联合审查时对 B-04-L-01「未收口」做过独立复核互证（`61239f06`），wt708 重采批 25/27 逐字节相同+2 张差全归因。

**残差**：① V3 Gate V3-7「核心旅程 A/B=0」要求 B 级 3 项（L-02/03/04/05 chat 面四项）在 L2–L5 审查轮清零——L-01 已收口，**chat 面 B 级项清零状态本次未在 ledger 外定位到独立闭环记录**；② FIX-385（同名双定义 provider 普查）**OPEN**；③ golden 锚与内容演进耦合（macOS home 重采差=FIX-376 内容演进），V4 需要一个「内容演进 vs 视觉回归」的裁决约定（wt708 已示范归因式重采）。

**一句话用户可见行为**：无直接用户可见行为；home 首屏「加载失败」裸露（L-01）经它曝光后已修。

### B-05 · 当前模型、Embedding、语音/OCR 与成本能力 Probe

**交付（主卡 PARTIAL → 当日密钥轮换补测收口）**

| 步骤 | 主干 SHA | 内容 |
|---|---|---|
| 主卡（09-19） | `55a067bd` | **59 live samples**（latency_samples.csv 逐次原始样本）；capability_matrix.json/csv；**ZHIPU_API_KEY 失效为 blocking finding**（coding+标准双端点 chat/OCR 全 401 code 1000→glm_batch 池实际只剩 minimax、TOP 层死配置）→ 如实 PARTIAL，401 原样记录不命中 fixture |
| 密钥轮换补测（同日，随 `1083f4f5` 收编） | probe1-8 raw_zhipu + capability_matrix_zhipu.csv（16 行）+ SUPPLEMENT_KEY_ROTATED.md | 新 key 全链路可用：glm-5.3-flash 双端点 16/16 200、并发 4 路 8/8；glm-ocr 主路 200；glm-asr-2512 中文转写逐字正确；引擎侧 9 个 zhipu registry lane 真实调用全健康（0 个 4xx/5xx）→ glm 车道可转正式备用 |

**核心实测结论（全部真实凭据无 fixture）**：
- qwen3.8-flash fast=standard=reason **同一模型**，差异仅 `enable_thinking` 请求级开关（双向生效）；fast TTFT p50 474.7ms/p95 623.7ms、总 p50 1063.5ms；reason 总 p50 1718.8ms；JSON 模式 3/3 合法。
- MiniMax-M3 流式 200，12 并发一波 12/12 全 200 零 429。
- Embedding qwen3.7-text-embedding-flash dim=1024（=EMBEDDING_DIM），single p50 128ms；TTS→ASR round-trip 逐字正确；**qwen3.8-flash 原生视觉可用**（OCR 可路由主模型）。
- **路由成本表与真实计费矛盾**：config 币种未标注、不分输入/输出/reasoning，reason=5×standard 与同模型同价实测矛盾——「路由成本表需按真实计费维度重建」。
- SLO 输入：fast 档可满足 L1（first meaningful feedback p50≤2.5s）且余量大；**L2 <500ms 不可由模型 TTFT 保证**（thinking 首 chunk ~423ms 仅是事件流）——这条直接塑造了 E 线「服务可知后 <500ms」口径（V3-COMPLETE-STATUS §4-E 线）。

**验证证据**：COMPLETION_RECEIPT.md + REVIEW_RECEIPT.md；SAMPLES_SANITIZED.md 脱敏样本；raw/ 逐次探针落盘（凭据不出进程）；后续 wt321 商业化设计（`8e563e8d`）直接引用 B-05 实测成本（¥0.8/2.7 per M tok、batch lane ≈0 margin、100k daily cap）做 unit economics。

**残差**：① rerank/翻译/json_schema strict/MiniMax 服务端真实并发上限=unknown（卡面允许，如实保持）；② 成本表重建**未见后续卡承接**（本次 grep 未见对应 FIX 或交付）；③ 全部数字为 2026-09-19 时点——V4 设计时的模型/价格/行为已漂移（如 glm 车道当时仅剩 5.3-flash 双模型、思考不可关），**复用前须重跑 probe_zhipu_lanes_b05b.py 同构脚本**（scripts/devtools/probe_zhipu_lanes_b05b.py 在主干，117 行）。

**一句话用户可见行为**：无直接用户可见行为；它决定了 V3 的模型选型事实（fast 档快、TOP 层一度是死配置、OCR 走主模型）。

### B-06 · V3 核心实体映射与重复真源审计

**交付（基线 + 两轮深化）**

| 波次 | 主干 SHA | 内容 |
|---|---|---|
| 基线（09-19） | `faaae378`（READY_FOR_REVIEW）→ `0cbfd777`（双审 remediation → DONE） | ENTITY_MAP.md + entity_map.csv（24 概念 × 8 列）：四分法全量映射、Aurora/Runtime/Action 单一 owner 确认、**8 组重复真源 D-\***（D-PREF/D-CTX/D-INT/D-STATE/D-TASK/D-CONF/D-OUTBOX/D-ENTITLE，每组给权威真源+应收敛方+迁移路径）、V2.5 飞轮资产 8 项标注复用地基；REVIEW_RECEIPT ×2（卡面要求 2 份） |
| wt574 审计（09-25/27） | `c4b33b6a`+`13bd8d81` | A3/B7/C4 分级：FIX-289 GroupType 第三副本缺 official→search/directory 500（**FIXED@63806c2f**）；FIX-290 focus streak 双真源双时钟打架（服务端下发被 mobile 本地覆盖）——**OPEN 待裁决**（修法涉「哪侧权威」产品裁决）；FIX-291 guard 只扫 app/models 的 StrEnum、models 外 6+ 族未入管——**OPEN 待派** |
| wt657 round-1（09-25） | `f4789f98` | 补齐基线未竟验收：四分法/十二概念映射 ENTITY_MAP（md+json，`v3-output/WT657-B06/`）；确认验收 2（runtime_v1 AuroraDecision 同名异面属观测非分裂）；登记 gateway 任务 CQRS 投影族零读面双投影器 V3-FIX-355（撞号顺延 356，**FIXED@9770f636 裁决 b 退役**） |

**基线的关键判定（V4 最应读）**：V3 四分法与 Aurora/Runtime/Action **全部存在唯一权威 owner，无需新造系统**——Aurora owner=backend/app/aurora/、run truth=execution_intents、Action 分配协议=ExecutionIntent（execution_mode+TrustLevel 扩展而非新建分配服务）。真正的 no-authority 缺口只有两个：**Experience Memory 聚合体、Trajectory/Golden Journey 读模型**。全部 8 组重复真源应走「迁移/收敛」而非重写。

**后续收敛证据（B-06 发现→真修的闭环样本）**：FIX-259 streakdaystatus 枚举断链（**FIXED@cd4624fb**，四层修复后 ENUM-PARITY 豁免删除 `d79354e9`）；FIX-260 AchievementType wire 对齐钉（**FIXED@b2fe866c**）；FIX-275 entitlement Python/Go 受控双实现跨语言等价测试（**FIXED@312a32c3**，共享向量单源 38+9 例）；FIX-276 CARD-DUAL-WRITE 守卫停用债（**FIXED**，考古→修实现+复活）。

**验证证据**：psql 只读 236 表核对；R2 复核修订 C4 如实标注 db_table_live 时点漂移并重跑关键 0 值双路复核；后续卡片（C-01 卡面 Must read 即 `00_context/ENTITY_MAP.md`）实际引用该图——「后续任务必须引用」验收以 C-01 卡面依赖关系兑现。

**残差**：① FIX-290/291 双 OPEN（见上，都是「需要产品裁决/独立工程量」而非机械修）；② card_protocol 目标形态 0 行 mid-flight（KNOWN_CODE_DEBT_LEDGER #4/#6）——`cards`/`task_occurrences` 建表 0 行，今日真值仍是 `tasks`/`subtasks`；③ **cognitive_ownership（D13 必需字段）在 B-06 时点全仓 0 命中，现已在主干落地**（app/core/action_plan.py:251 `cognitive_ownership: CognitiveOwnership`，X 线契约族承接）——B-06 报告的这条缺口已过期，V4 读旧图时注意；④ 权威映射有两个版本（v3-output/B-06/ENTITY_MAP.md 基线版 + v3-output/WT657-B06/ENTITY_MAP.md round-1 版），`v3/00_context/ENTITY_MAP.md` 只是「要找什么」的契约模板而非映射本体——V4 应以 WT657 round-1 版为最全口径，并注意权威件在 v3-output 不在 docs 树。

**一句话用户可见行为**：无直接用户可见行为；它防住了「第二套系统」（V4 设计者应把 §B.2-B-06 基线判定当作直接输入）。

---

## B.3 设计决定与取舍（从提交/审查考古）

1. **审计卡零产品码 + 机器可读交付**：B-01/02/05/06 全部零产品代码改动（changes.patch 只含 v3-output），盘点一律 CSV/JSON 双格式（人读+机读），DB 只读 SELECT、curl 只读探测。取舍：牺牲「顺手修」的速度，换「发现与修复分离」——每个发现进台账走独立 FIX，修与不修由验收模型裁决。这条纪律在 B-02 的 F1（发现→FIX-01 三天后独立修）上跑通了。
2. **「未知的保持 unknown」**：B-01 的 UNKNOWN 状态、B-05 的 rerank/翻译 unknown、B-04 的运行级待验清单——卡面「未知项不猜」被严格执行，代价是留下一批显式 unknown 面而非伪完备矩阵。
3. **B-03 修 harness 而非重建**：13 项修复全在前员骨架上演进；v2 再补 schema 互斥契约（simulator run 自标识+lane 互斥），把「仿真结果冒充真实驱动」这类诚实性风险在格式层封死。取舍：v1 阶段先跑通三端留证，契约统一推迟到 v2。
4. **B-04 把视觉基线放进 flutter test golden 而非模拟器截图**：换取 CI 可复跑+manifest sha256 机器验证链；代价是 flutter_tester 无平台字体（ENV-1 伪影，文字审查权威让渡给 android 批）与「无真机批次」（报告 §6 运行级待验清单如实留白）。
5. **B-05 的 401 即数据**：缺 key/失败不命中 fixture 是卡面 Forbidden，zhipu 全 lane 401 被如实记为 unavailable 并以 PARTIAL 收编，随后靠用户轮换密钥当日补测转全量——「阻塞证据不伪造通过」的样本路径。
6. **B-06 的「迁移而非重写」教义**：8 组重复真源逐一给权威方与收敛路径而不立即动手；这条教义后来被 C-01（extend-only into ContextPack）继承并成为 V3 全线反「第二真源」的锚。

---

## B.4 残差与 V4 注意点（汇总）

1. **B-02 红测缺位**：mock 写 Isar 生产缓存的防线测试从未入库（§B.2-B-02 残差①）。V4 做数据真实性应先补钉子再谈防线。
2. **台账指针会腐烂**：FIX-258 行闭账丢失（V3-FIX-504，本次登记）证明「集成即纠指」依赖人工且 rebuild 会回退闭账；V4 的记账工具应把 FIXED@ 指针的主干可达性做成机器检查。
3. **B-05 能力矩阵时效性**：模型面/价格/密钥状态全部是 09-19 时点；成本表重建未承接。V4 任何 AI 能力设计前重跑 probe。
4. **三个 OPEN 的产品裁决**：FIX-256（gen-l10n 格式漂移）、FIX-290（focus streak 哪侧权威）、FIX-385（同名双定义 provider）——都不是机械修，V4 排期时应作为设计议题而非 bug。
5. **群 AI 面的隐私接线义务**：community_context_boundary（orphan-by-design 豁免在案）是 V4 群 AI 功能的既定守卫面，接入即移除豁免。
6. **孤儿面常态存在**：wt639 证明「有代码≠可达≠有写入方」（12 DEAD+2 ORPHAN@09-27）；V4 应把 wt639 的四问判据（入口可达/下游消费/测试在测/宣称 vs 实现）做成周期性审计而非一次性卡。
7. **no-authority 两缺口**：Experience Memory 聚合体与 Trajectory/Golden Journey 读模型至今无权威存储——V4 若做「越用越懂我」的_experience_层，这是起点而非新增面。

---

## B.5 本次审查登记

- **V3-FIX-504**（本次新登记，台账行已入本 worktree commit）：V3-FIX-258 行闭账指针丢失——行尾双 OPEN 零 FIXED@，而修复本体（52fbed29）在主干完整在案。证据链与修法方向见台账行；B-02 残差节已同步注记。方向性说明：这是台账**低估**完成度的漂移（与假 DONE 反向），危害在误导后来者重做已修的面。
- 复核过但**不构成新发现**的两项：B-02 红测未收编（Reviewer R1 已抓、receipt 已如实处置，属已登记残差）；community_context_boundary 零接线（orphan-by-design 豁免在 rule_at_exceptions.md:39 在案，属已知设计态）。
- 号占用核验：499=wt767（plan_review total_days，OPEN 在账）、500/501=wt765（09-28 轮#259 登记）均被占用，故取 502（grep 全仓零命中后占用）。
