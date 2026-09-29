# V4-Q08 预备侦察报告（scout, 2026-09-29, main@ff72096c, 只读+仅本目录写入）

> 用途：Q08「V4发布裁决与可修改设计快照」（PENDING, verification, risk=high, 双审, qa-release 锁, deps=Q02✓/Q03✓/Q04✓/**Q05✗**/**Q07✗**/D06✓/S04✓）派单直接引用。
> 红线声明：本报告为侦察产物非验收证据；未执行 Q08 本体；未改任何既有文件；未动 worktree（只读 `git worktree list`）；引用的台账/CI/fleet 状态均为 2026-09-29 18:00 CST 时点实录，Q08 执行时逐条亲验。

---

## 一、悬置项聚合表（全部已闭卡的挑战/遗留/勘误/豁免 × 台账 OPEN 行）

### A. 等待 Q08 类裁决的设计与口径悬置项（design rulings）

| # | 悬置项 | 来源 | 实录指针 | 裁决 owner 建议 | 对 Q08 的含义 |
|---|--------|------|----------|----------------|---------------|
| A1 | **G01 weather lerp 白基料不令牌化**——C1「登记不修」已由 R1 维持，理由修正（LOW-2）：无语义正确的既有不透明白槽（chatBubbleUserText 在 dusk 为深墨 #17261C，rimLight alpha:1.0 等值混入不成立）；**「待 token 白槽提案（Q08 类）裁决后统一处理」为卡面原文** | V4-G01 limitations §2.2 + review_r1.md 靶4 | v4/evidence/V4-G01/{limitations.md,review_r1.md} | 设计系统 owner + leader（新增不透明白语义槽 = 发布面决策） | Q08 设计层必答题：开白槽 or 维持登记债，二选一落快照 pending 区 |
| A2 | **golden 跨机口径分裂**：G01/G04 系走「比较器容差」（CI53 Linux 0.62%/8227px 超容差=FIX-581 在修，方向为 F579 同型环境感知容差）；G02 系 25 张 golden 走「Linux 跳过+仅签发机（darwin arm64, Flutter 3.41.3）再生」；G03 走「env 门控确定性采集+语义钉，非 matchesGoldenFile 像素基线」（V3-FIX-368 判例）。三种口径并存 | V4-G01/G02/G03 limitations §1 + FIX-581 行 | CI53 run 36546247412；wtF581 在航 | QA/视觉 owner（EVALUATION_PROTOCOL「golden 基线变更需独立签理由」） | Q08 工程层判据必须先统一「golden 纪律」口径，否则四风格完成度矩阵不可比 |
| A3 | **G06 解锁弹窗渐变墨色（美术维度挑战）**——G06 尚未闭账：R1=PASS_WITH_CHALLENGES 带 F-3 HIGH 合并门（DL-SPEC persistentRepeatLoop 4>基线 3），返修 525da0ed 三项全闭，R2 在审；**G06 evidence 未落 main**（弹窗渐变墨色的美术维度挑战在 wtG06，本侦察未入——只读红线不动 worktree） | fleet note 27:30/29:40；wtG06 分支 | v3/.sparkle_v3_fleet_state.json notes | leader + 设计 owner | Q08 输入缺口：G06/G04/G07 三卡闭账前，四风格完成度只有 4/7 |
| A4 | **F05 五面 preview 范围口径**：preview 面=真实表面组件非整屏；入口 flag `enableStylePreview` 编译期 false；l10n 硬编码中文先行（转正时随「preview→发布」决策一并补 arb）；星图 `SectorBackgroundPainter` 不随候选色板全量跟随（页面家族若要跟随需动 galaxy_display_settings_provider 消费链——超卡面） | V4-F05 limitations | v4/evidence/V4-F05/limitations.md §1/已知限制 | 设计 owner + leader（preview 转正=风格拍板的一部分） | 快照 candidate 区需逐面登记「preview 面 ≠ 发布面」的边界，防外推 |
| A5 | **语义钉 vs 像素钉证据层级**：G 卡 golden 大多为「语义钉+确定性 PNG（Ahem 字形）」，真实字形/真机渲染全舰队 DEVICE_UNVERIFIED；V4_DONE 允许「音触只测到调用时注明边界」 | 全 G 卡 + F02/F04/U 系列同先例 | 各卡 limitations §1 | 按 EVALUATION_PROTOCOL 五层口径如实分层，Q08 不新增层级豁免 | 设计层 PASS 只能到 L1/L2 强度，快照须写明「设备面 NOT_RUN 不阻止内部候选」判例边界 |
| A6 | **风格拍板未发生**：TOKENS.proposal.json status=PROPOSED_NOT_APPROVED（四主题 classic/paper_day/dusk/quiet）；CLAIMS_LEDGER「Sparkle采用暖纸像素设计」只允许称候选设计；ROLLOUT「用户未定视觉方向不阻塞内部实现，但默认公开界面不能替团队拍板」 | v4/02_design/TOKENS.proposal.json + CLAIMS_LEDGER.md + 08_release/ROLLOUT_AND_OPERATIONS.md §阶段5 | 文件在库 | **真实人（HUMAN_INBOX 项）**——Q08 只登记不代裁 | DESIGN_PREVIEW_READY 的「风格已明确选择」条件 = 外部门，Q08 产出「待拍板包」而非拍板 |

### B. 集成链缺口（contract-owner 面，工程层悬置）

| # | 缺口 | 来源 | 状态 |
|---|------|------|------|
| B1 | **ExperienceEventFrame proto 未落**（D01/F03/S03/Q06 全链受制）：mobile 呈现事件现网零流量；Q06 C4 列 9 格 GAP_INTEGRATION；可见性门（present() 无 AppLifecycle 入参）缺位 | V4-D01 limitations #1、V4-F03 #1、V4-Q06 L2、FIX-569 | contract-owner 单独合并位，**至今未派**；Q08 前置清单登记项 |
| B2 | **FIX-569 三 implicit 组件接线小卡**——leader 裁决（2026-09-30）=接线（F03 链低成本样本先行），「新小卡避开 F03/Q05 卡面边界；**Q08 前置清单登记**」 | Q05-prep scout §三-b；FIX-569 行（OPEN, R1 PASS_WITH_CHALLENGES） | 小卡未派；Q08 需决定其是否阻塞工程层结论（建议：不阻塞，入快照 debt 区） |
| B3 | **D02 归因/D03 撤回生产触发方零接线**：RetractionRecomputeService 无 UI/FSM 入口；attribution.py 无生产 import（BJ 豁免+KNOWN_CODE_DEBT_LEDGER P3 #13/#14 双登记，消费卡接线时移除）；FIX-562 已 FIXED@9cb9d961（F-1→FIX-576 OPEN） | V4-D02 #1-2、V4-D03 #1、台账 | 机制面验收成立、生产面待接线——Q08 记「机制在岗、流量为零」口径 |
| B4 | **I02 resolved 正例被 L0 预筛剔除**（M-03 合法性检查为硬规则，放行归 M-03 owner 另卡）；marker tag 词汇无写入方；I05 事件总线监听器与 D03 同批挂接；chat 侧 decision_context 未传（I05 #2） | V4-I02 #1/#3、V4-I05 #2/#3 | VALUE 层 C/D 臂差分只能靠 L2 live 判定（现 BLOCKED）——与 Q02 结论互相锁死 |
| B5 | **U01/FIX-567 resume_view 生产者缺失**：后端唯一回执生产链硬编码 chat_context；W2 bootstrap 方案（U06 scout 已勘路）归 U06 承接 | V4-U01 #2 + U06-prep scout §二 | U06 未闭 → Q05 被门 |
| B6 | **U12 /shop 路由深链可达维持 HIDDEN**（撤路由属 shop 行处置变更需裁决）；U14 登录失效面由路由闸兜底（SCREEN_FAMILIES 第三面取舍） | V4-U12 #7、V4-U14 L4 | leader 口径裁决；不阻塞，入快照 pending 区 |
| B7 | **I09 R1-C1 快路挂点**（retrieval 先于 router，embedding 调用未归零——登记待派）；I10 M6 第二账本未收敛；I07 aurora correct-answer 掌握写点进程级封顶=中期已知债 | V4-I09 R1 追记、V4-I10 #1、V4-I07 #9 | 计量/掌握诚实性边角，入快照 debt 区（ VALUE 层 M04/M05 复测时会再暴露） |
| B8 | **Q04 揭案的 fleet 级运行栈事故**：共享 PG host 侧鉴权自 09-28 损坏（BLOCKED_EXPLICIT）；驻留栈计费进死信/丢失（152 行被吞+恢复 58 行）；MinIO/Redis 凭据跨仓三方漂移——「需 fleet 另派卡修复」在案 | V4-Q04 limitations §2 | **未见派修卡**——LIVE_STACK 层任何复测（含 M04-M06 改善轮、Q07 真实跨进程腿）都被此卡门；Q08 前必须显式处置（修或 BLOCKED 登记） |

### C. 台账与 FIXED 行终证条款遗留（v3/06_agent_fleet/DYNAMIC_ISSUES.md @ main@ff72096c）

- **真 OPEN = 58 行**（状态格以 OPEN 开头者；另有「FIXED@…含 OPEN 字样」的翻格变体约 40 行——台账口径噪音，B01 limitation #6 已声明 ±1~2 机器重算差）。V4 期新增 OPEN：FIX-564/565（已裁决摘除，typing_text.dart 已删、棘轮 49→48）/566/568/569/572/575/576/577/580 均标「非阻塞」，**FIX-581 = 唯一 P1**。
- **FIX-579 终证条款**：「下一轮 CI 同位置自然运行：再红则调系数或转测量法基建卡、不再调阈值」——挂 CI 自然轮，未兑现（CI53 红）。
- **FIX-581 终证条款**（在修）：环境感知 golden 容差 + dusk 异常根因定性 + **全部 G 系 golden 比较器一致性一次性审计**——其产出直接是 Q08 工程层输入。
- 老 OPEN 大族：运维族（500/501/502/503/505/509/532/542）、文档族（509/513/514/554）、E-08 销账 C1 义务（545, V4 追踪）、FIX-48 打扰冷却（P01 #3 引用）——Q08 按「已知债不入新裁决」处理，只在快照索引。

### D. 外部门（RELEASE 维度输入，全部 OPEN）

- HUMAN_INBOX（v3/08_operations/HUMAN_INBOX.md）H-001~H-009 全 OPEN：云部署解锁（H-002）、真机/读屏/常驻真 LLM 采集批（H-009 大项）、生产库回填（H-001）、l10n 冻结键文案（H-005）等。
- 原三卡义务未动（V4_DONE「旧工作不重做」）：**O-01（公网/费用/隐私外部门）、Q-07（真实长期验证）、Q-08（原版）**——Q08 卡面验收②明令「未过就不称公网商业上线」。
- 预算门：budget.example.json enabled=false/max_spend=null/price_table_verified=false → M11/M12 L2、M08-M14 联合判定在 L2 缺席（Q02 verdict=FAIL_L1_BLOCKED_L2_NOT_PASS 已固化此结论）。

---

## 二、数据就绪矩阵（Q08 裁决需要什么 × 现状）

| 输入 | 用途（Q08 判据面） | 状态 | 缺口/动作 |
|------|--------------------|------|-----------|
| 57 张已闭卡 evidence（limitations+review_r1/r2+run_manifest+artifacts_sha256） | 分层完成矩阵的逐卡证据源 | **已备**（本文档 §一 已聚合） | review_receipt.json 多数仍 PENDING（由协调者落 VERDICT 的模式）——Q08 引用以 review_r*.md + tasks.json evidence_verdict 为准，receipt 补登列为债 |
| Q02 结论 | VALUE 层记忆效用（M08-M14） | **已备**：FAIL_L1_BLOCKED_L2_NOT_PASS（R2 PASS_WITH_CHALLENGES_CLOSED）；冻结反例 OPEN_AS_V4_BASELINE | L2 终判永久缺位（无预算）→ VALUE 层按 BLOCKED+FAIL 记录，非 Q08 可解 |
| Q03 结论 | VALUE 层人机护栏 | **已备**：PASS_WITH_FINDINGS_CLOSED（F1 已修闭环）；真人面 NOT_MEASURED_HUMAN | 无 |
| Q04 结论 | VALUE 层延迟/成本（M04-M07） | **已备**：测量成立 PASS_WITH_CHALLENGES；被测系统 **M04/M05/M06 FAIL、M07 PASS** | 改善轮属实现卡职权未派；B8 运行栈事故未修——复测前置 |
| Q05 | DESIGN 层三端页面家族+无障碍 | **阻塞**：heavy，deps 仅剩 U06；U06 等 Q01 模拟器槽（U06-scout 实勘「Q05 起跑以 U06 集成为门」） | 关键路径：Q01闭→U06→Q05 |
| Q06 | 工程/感官层全感官矩阵 | **已备**：PASS_WITH_CHALLENGES（58/58 复跑 exit 0）；C4 列 GAP_INTEGRATION 9 格 | C4 缺口清偿随 B1 接线 |
| Q07 | 工程/韧层 14 日控制钟+跨进程多端 | **阻塞**：high+heavy+双审，deps 含 Q01（在航）与 U06 | 10/4 前闭合存疑（§四 R2） |
| D06 / S04 | GraphRAG 时效 / 资产许可账本 | **已备**：APPROVE / PASS_WITH_CHALLENGES_CLOSED | S04 权利判定是文件名级证据非法律结论（HUMAN_INBOX 候选在案） |
| G 线四风格完成度 | DESIGN 层家族矩阵 | **部分已备**：G01/G02/G03/G05 闭（4/7）；G04 在航、G06 R2 在审、G07 未派 | A3；Q08 快照 candidate 区按「已闭家族」如实计分母 |
| CI 状态 | 工程层「集成 SHA 可失败测试」基面 | **红**：CI53 failure（FIX-581 在修）；本地 main 领先 origin/main 27 commit（银行持仓至 581 合并后一推） | FIX-581 闭+自然轮终证+银行推出 = 工程层判据前提 |
| 守卫基线 | 工程层回归口径 | 已备：各卡单规则 PASS+集成批实录；「全绿」从未在单一检出成立（D02 #5 口径） | Q08 沿用「区分既有失败与新增回归」纪律，全量守卫基线跑一次入 run_manifest |
| 评测协议口径 | VALUE 层判据文本 | **已备**：EVALUATION_PROTOCOL（五层/四臂/M08-M14 联合）+ METRICS.json（M01-M18）+ CLAIMS_LEDGER | 无 |
| 同版本八要素（卡验收③） | 交付包/build/flags/model/价格/schema/资产/证据 | 大体已备：schema=alembic head（Q04 已补 i06 迁移）；资产=S04 账本；flags=ROLLOUT 五旗标 off/shadow/live 各卡已登记；证据=artifacts_sha256 | **build ID**：FIX-558 解封后 Flutter 三构建 exit 0（Q05-scout），Q08 可采真实 build ID；**价格**：B06 price_table_verified=false（价值未核验，只可记「内部估值」） |
| 设计快照素材 | 可修改设计快照 | **已备**：TOKENS.proposal.json（status 不许 agent 改）+ F01 令牌管线 + F05 五面 + G 卡 goldens + 本文 §一.A 待定项清单 | 聚合产出是 Q08 本体工作（§三.2） |

---

## 三、裁决框架提案

### 3.1 分层结构 = V4_DONE 四结论 × 每层独立 PASS/FAIL/NOT_RUN/BLOCKED

卡面验收①「设计预览、工程、效用、外部发布四种结论独立」与 V4_DONE「四个结论必须分开」一一对应；终门输出格式（V4_DONE §终门）= 每层 PASS/FAIL/NOT_RUN/BLOCKED + metric IDs + 样本 + 版本 + 证据路径与哈希 + 独立 review + 限制。建议逐层：

| 层 | 判据（PASS 需同时满足） | 证据源 | 当前时点预判（供 Q08 校验，非裁决） |
|----|--------------------------|--------|--------------------------------------|
| L-DESIGN（DESIGN_PREVIEW_READY） | ①四风格全家族 golden/语义钉 CI 可失败且口径统一（A2）；②参考图零冒充（REFERENCE_ONLY 隔离在岗）；③preview flag 关时发布面零差量（classic 零差量钉在岗）；④无 A/B 级遮挡误导（Q05）；⑤风格选择有人的决定记录（A6） | F01/F05/Q05/G01-G07/B04/Q05-prep | FAIL→CONDITIONAL：⑤未发生（注定）、④未跑、G 线 4/7；①②③已达标面可先记 PASS |
| L-ENG（ENGINEERING_VERIFIED） | ①集成 SHA 上 mobile/backend/gateway 测试绿（CI 自然轮）；②全量守卫无新增回归（区分既有失败）；③golden 纪律统一+FIX-581 终证；④原 V3 触达回归（Q07）；⑤音触/设备面按 NOT_RUN 边界如实（V4_DONE 判例） | CI、各卡 test_results、Q06/Q07、FIX-579/581 终证 | BLOCKED-ON-FIX581：CI 红+银行 27 笔未推；Q07 未跑 |
| L-VALUE（VALUE_VERIFIED_IN_TESTS） | M08-M14 联合判定（EVALUATION_PROTOCOL）；M04-M07 延迟成本 | Q02/Q03/Q04/B03/METRICS.json | **FAIL+BLOCKED 如实记录**：M04/M05/M06 实测 FAIL、M11/M12 L2 无预算、冻结反例 OPEN。V4_DONE 明令「结果 FAIL 永久可见；不得删除失败数据凑全绿」——此层结论大概率维持 FAIL，这不是 Q08 的失败而是其正确产出 |
| L-RELEASE（RELEASE_READY） | 外部门关闭：O-01/Q-07/Q-08 原义务+HUMAN_INBOX+风格拍板+价格核验+发布工件同版本（ROLLOUT §发布工件） | HUMAN_INBOX、CLAIMS_LEDGER、ROLLOUT | **BLOCKED（设计使然）**——卡面验收②「未过就不称公网商业上线」就是本层输出的预期形态 |

裁决规则建议：层间不得互相替代（L1 全绿不能替 L3——协议原文）；「完整满足才 VALUE/RELEASE 通过，不因 58 张卡做完就开关全 live」（卡面 work 原文）；每层 FAIL 面附「解阻条件」而非归因修饰。

### 3.2 可修改设计快照产出物形态建议

「可修改」指：快照记录**什么已冻结、什么仍可改、改的程序是什么**，而非冻结设计本身。建议三件套（两件入 evidence，一件提案性文件不落 02_design 以免造第二权威）：

1. **diff_or_evidence_only.md 承载「分层完成矩阵 + 失败/外部条件」**：四层 × 逐判据表，每格 = 结论/证据指针（卡+文件+sha256）/解阻条件。外部条件单独一节（HUMAN_INBOX 映射 + O-01/Q-07/Q-08 原义务状态）。
2. **design_pending_items.json（机器可读待定项快照，落 evidence/V4-Q08/）**：本文 §一.A/B 逐项结构化——`{id, source_card, evidence_ptr, options:[…], ruling_owner, status: PENDING_Q08|RULED|DEBT, rollback_note}`。设计待定项（A1 白槽、A2 golden 口径、A4 preview 转正、B6 shop 路由…）与集成债（B1-B8）分册。这是「可修改设计」的索引权威：后续任何改动先查此表再动码。
3. **可回滚候选表（快照第 3 区 or 独立 rollback_candidates.md）**：沿 ROLLOUT §回滚逐项索引——UI profile 可立即回 classic（F05 判例）；五旗标 pixel.preview/memory.utility_gate/aurora.semantic_selector/experience.feedback_v4/episode.resume_v4 各自 off/shadow/live 现值+回退命令+「撤回与权限永远不能关」红线；P01 回滚开关是紧急全关非行为回退（P01 #10 的坑显式登记）。
4. **TOKENS.proposal.json 本体不动**：status=PROPOSED_NOT_APPROVED 由真实人翻（A6）；Q08 若裁决出「白槽」等令牌演进，产出 `TOKENS.proposal.v2` 草案块附在 pending 表内，不覆写现文件。

### 3.3 执行顺序建议（Q08 派单时）

1. 先决检查：Q05/Q07 状态 + FIX-581 是否闭合 + 银行是否已推——三者的答案决定 Q08 按「全依赖闭」跑还是 leader 显式降级跑（见 §四 R1/R2）。
2. 开卡即冻结 source_sha（本报告 ff72096c 之后 main 每天前进数十 commit；证据绑定开卡时 SHA + 集成复验条款照 U14 判例预先声明）。
3. 聚合（本文 §一 直接引用，逐条亲验指针非转抄）→ 四层矩阵 → 快照三件套 → test_results.json（矩阵脚本化可复算）→ 双审。
4. 双审靶建议预登记：①VALUE 层 FAIL 措辞是否与 CLAIMS_LEDGER 一致；②L-ENG 是否误把 NOT_RUN 记 PASS；③pending 表是否漏接 G06/G04/G07 的未落库挑战；④同版本八要素逐项 sha 对表。

---

## 四、风险清单（10/4 内部交付前可能爆的雷，按杀伤力排序）

| # | 雷面 | 依据 | 影响/缓解 |
|---|------|------|-----------|
| R1 | **Q05/Q07 赶不上 10/4**：关键链 Q01(在航)→U06→Q05（heavy 三端矩阵）；Q01→Q07（heavy+双审+14 日控制钟模拟+真实跨进程腿）。两卡是 Q08 卡面硬依赖 | tasks.json deps；U06-scout「U06 等 Q01 闭后再占模拟器」 | **Q08 最大风险**。若 10/3 仍未见 Q05/Q07 闭账，需 leader 二选一：①Q08 顺延至 10/5-10/7 缓冲期（挤压提交缓冲）；②显式降级启动（Q05/Q07 记 NOT_RUN，L-DESIGN/L-ENG 对应判据记 BLOCKED 而非 PASS）——降级必须 leader 留痕，不能由 Q08 自行豁免依赖 |
| R2 | **FIX-581 修不彻底**： golden 跨机 0.62% 超容差是架构级（银行 27 笔含 G02×25/G03/G05 50+ golden 连环红）；修法（CI 容差系数）与 G02 的「Linux 跳过」、G03 的「env 门控采集」三种口径若不统一，A2 判据不成立 | FIX-581 行；fleet note 29:00 | 工程层基面不稳+提交快照 SHA 与 CI 状态脱节；缓解=581 修法审计面必须覆盖全 G 系（其终证条款已含） |
| R3 | **VALUE 层 FAIL 的表述风险**：M04/M05/M06 实测 FAIL+M11/M12 BLOCKED 是既成事实；Q08 验收「完整满足才 VALUE 通过」→ 结论必然非全绿。向上汇报若被写成「全绿」即违反 V4_DONE/CLAIMS_LEDGER；反向风险是把工程面一起拖成 FAIL 打击交付叙事 | Q04 test_results；Q02 verdict | 措辞模板预先立好：「内部工程候选成立；效用门 FAIL/未测如实分层；不称公网商业上线」 |
| R4 | **模拟器/设备链全舰队 DEVICE_UNVERIFIED**：Q07 真实跨进程/多端腿无真机；U06/Q01 抢模拟器单槽；磁盘余量紧张（Q06 记 6.7Gi） | Q06 L1；U06-scout §四 | Q07 大概率交付 L1/L2+设备面 NOT_RUN；Q08 判据按「声明平台通过」读，禁借 Q07 冒充真机完成 |
| R5 | **审查槽排不上**：六槽模型（1 协调+4 实现+1 审查）；当前 G06R2/G04R1 在航+Q08 双审需求（risk=high）；Q08 自身也要占 qa-release 锁 | fleet note 29:40 | Q08 实现会话本身轻（无 HEAVY），但双审要预约；建议 leader 在 Q05/Q07 返修波谷插审 |
| R6 | **跨卡合并冲突第三/四例**：G03×G05、G02×G03 已两例 union 解决；G04/G06/G07 与已合并 G 卡同屏面重叠概率高，每例消耗 leader 半会话 | fleet notes 27:30/28:40 | Q08 聚合时以 main 合并态为准逐卡复核（limitations 的跨卡冲突注记已三处） |
| R7 | **B8 运行栈事故无主**：共享 PG 鉴权损坏+计费死信+凭据漂移未派修——任何 LIVE_STACK 复测（M04-M06 改善、Q07 真实腿）都会撞墙 | V4-Q04 §2 | Q08 前要求 leader 显式处置：派修卡或 BLOCKED_EXPLICIT 登记，不留隐式假设 |
| R8 | **review_receipt 账面滞后+台账翻格噪音**：多数 evidence receipt=PENDING 而卡已 done；台账 OPEN 计数有 ±2 机器口径差 | 本文 §二/§一.C | Q08 引用规则写死：以 review_r*.md+tasks.json verdict 为审查完成依据；receipt 补登为债不入裁决 |

---

## 五、工作量估计

- **Q08 本体（实现会话）**：约 1 个会话（2-4h agent 时间，零 HEAVY）——聚合聚合已由本侦察预付（§一）；剩余工作=逐指针亲验（~40 分钟）+四层矩阵脚本化复算（~60 分钟）+快照三件套产出（~60 分钟）+五件套证据归档（~30 分钟）。
- **独立审查 ×2**：各 1 个轻会话（0.5-1h）——靶集中在措辞口径与指针抽查，无需复跑产品测试；qa-release 锁无竞争。
- **关键路径不在 Q08 本体，在依赖**：Q01→U06→Q05 与 Q01→Q07 两条 heavy 链合计估 3-5 个实现会话+2-3 个审查会话+模拟器窗口；10/4 前闭全链是进度风险（R1），不是工作量风险。
- **leader 预付决策（建议 Q08 开卡前定）**：①降级启动条款；②B8 处置；③A2 golden 口径统一归 581 还是独立小卡。

---

## 附：本侦察证据基座（全部实查于 main@ff72096c）

- 遍历 63 卡 evidence：V4-*/limitations.md ×57、review_r1.md ×57、review_r2.md ×21（B05/D01/D03/F03/I02/I03/I04/I05/I06/I07/I08/I10/P02/P03/Q02/Q03/S02/U02/U04/U10/U11）。
- 卡库：v4/04_tasks/tasks.json（65 卡，57 done / 8 PENDING：U06/Q01/Q05/Q07/Q08/G04/G06/G07）。
- 台账：v3/06_agent_fleet/DYNAMIC_ISSUES.md 463 行 413 条 FIX 行（真 OPEN 58，P1=FIX-581）。
- 规范：v4/V4_DONE.md、v4/MASTER_DESIGN.md、v4/06_evaluation/{EVALUATION_PROTOCOL.md,METRICS.json,CLAIMS_LEDGER.md,budget.example.json}、v4/08_release/ROLLOUT_AND_OPERATIONS.md、v4/02_design/TOKENS.proposal.json。
- 运行态：v3/.sparkle_v3_fleet_state.json notes（456 条，读至 29:40）；GitHub Actions run 36546247412（CI53 failure）；`git worktree list`（wtF581/wtG04/wtG06/wtQ01 只读清点）；同批侦察 v4/evidence/V4-Q05-prep/、V4-U06-prep/ 交叉引用。
