# J 线（Journey 8 卡）深挖章节 —— V4 交接文档素材（wt774）

> 本文是 `v3/V3-COMPLETE-STATUS-FOR-V4.md` §4「各线深度状态」J 线章节的深挖草稿。
> 证据纪律：只写三源证据（git 主干 SHA / 独立审查 receipt / 运行级实测）支撑的事实；逐条标注出处；无法定位证据的验收项显式标注「未定位到证据」。
> 撰写：wt774（2026-09-28，基线 main@5307cbb3）。方法：卡面（v3/07_tasks/cards/J-0*.md）+ `git log --grep` 逐卡定位 → 当前主干代码与测试开文件/计数核实 → v3-output REPORT/receipt 抽读（含机会图逐行核对修复标注）→ JOURNEY 七日状态文件（/tmp/northstar_ns001_real_drive_state.json 与 Sparkle-sysrev 备份）读取 → 台账闭环逐条复核。**未轻信任何台账/报告结论性文字。**

---

## J.0 线级概览

J 线是 V3 主张 1（任务卡住→澄清→纠正→重开可见→完成反馈）的用户旅程承载线：实测与机会图（J-01）→ Onboarding 先价值后画像（J-02）→ Today Cockpit 主入口（J-03）→ 首个有意义的行动端到端（J-04）→「我卡住了」统一恢复入口（J-05）→ Hybrid 旗舰旅程（J-06）→ 回访恢复（J-07）→ 完成反思轨迹（J-08）。

**完成度现状（比 v0.3 文档更新一拍）**：7/8 done + **J-02 已独立审查 PARTIAL 不销账**——wt764 交付（`787bc973`）工程面全合格，wt772 独立审查（receipt `588e65c2`，v3-output/WT772-J02-REVIEW/receipt.md 入库）唯一缺口=卡面 Required evidence 明列 integration/simulator 实测（验算不替代、审查方无权豁免），simulator 补证卡排队门后。tasks.json J-02=TODO 与「PARTIAL 不销账」口径一致（规格权威无误）。v0.3 文档「J-02 待审查销账（wt772 在航）」已过时——审查已返。

**两波执行形态**：J-02/J-03/J-07 先后有**两波交付**（wt282→wt764、wt306+wt324、wt303→wt385），复用 J 线章结论时以各卡最新一轮为准。wave-2 五卡（J-04~J-08，09-25~26 密集合入）的 REPORT 均**未入库**（v3-output/WT371-J04 等五目录本地存在、git 零追踪文件）——签收形态与 A/C 线相同（commit message 承载，wt759 判合规、台账零断链指针），作形态残差记录不占 FIX 号。

**七段旅程验证深度总览（V4 最应读的一张表）**：

| 旅程 | 真实驱动证据 | headless/单测证据 | 真模型 |
|---|---|---|---|
| J-01 First 3 Minutes | **macOS 真后端集成测试 5 persona×双路线**（真墙钟+截图序列+j01_timings json，全部入库 v3/09_evidence/j01_first3/） | O10/O11 curl 双向验证 | 否（Legacy 回退路径实测） |
| J-02 Onboarding | 无（simulator 实测=销账缺口） | widget/服务端 4+4；≤3min 为验算非实测 | 否 |
| J-03 Cockpit | **真模拟器三态路径 PASS（wt324，32 截图入库）** | cockpit 9+home 回归+结构测试 | 否（展示面无 LLM） |
| J-04 First Action | HUMAN_INBOX（三端实机+真模型 persona 观感转人工） | backend 8 红绿链+mobile widget 8 真跑（swap 门内） | 推导面走生产 GENERATION/FAST 注入路（测试内判定为规则/脚本 LLM 替身，独立真模型运行记录未定位） |
| J-05 卡住恢复 | **真模拟器 E2E PASS（wt324：stuck→chat→J-05 恢复链）** | backend 9+3+mobile 7 | 否（A-03 引擎 LLM 0 次是设计） |
| J-06 Hybrid 旗舰 | 真实工具链证据（真实 ToolExecutor+真实 document_chunks 检索，零 mock 零预录——但为测试内驱动）；实机转 HUMAN_INBOX | backend 5+12+5+4+mobile 3 | execute/check 走生产 GENERATION/FAST 注入路；独立真模型运行记录未定位到 J-06 名下 |
| J-07 回访恢复 | 无（可控时钟 headless） | backend 12+3+mobile 30 | 否 |
| J-08 完成轨迹 | 无（只读投影 headless） | backend 7+mobile 3 | 否（reflection=用户自报原样回声是设计） |
| JOURNEY day1-6（跨卡主线） | **真用户 ns001 七日真实日界驱动**（门 M1-M4 每日 200 PASS，state 文件+备份在案） | real_drive.py 相位步 | day 探针含 LLM 5 条（全程预算） |

---

## J.1 意图（卡面目标与验收）

八卡共性 Forbidden 条款与 B/C/A 线一致；依赖链 J-01←B-01+B-03+B-04，J-02←J-01+U-01，J-03←J-01+U-01，J-04←J-02+J-03+A-03+X-03，J-05←J-03+A-03+U-01，J-06←J-05+X-07，J-07←J-06+A-07，J-08←J-06+D-02+G-02。

| 卡 | Risk/Reviewers | 卡面目标（一句话） | 卡面关键验收 |
|---|---|---|---|
| J-01 First 3 Minutes 实测与机会图 | medium/1 | clean install 真实体验不先改代码，建立时间/困惑/视觉基线与机会图 | 录像/截图/time-to-first-action；第一分钟阻碍可复现；区分 example vs own-goal |
| J-02 Onboarding: Value Before Profile | medium/1 | 重构入口+progressive profiling，先让用户得到 Action；只问改变 first action 的问题 | fresh user ≤3min 到 useful action；seed 不进真实 Memory；注册/游客/升级三端 session 稳定 |
| J-03 Today Cockpit 重新定义主入口 | medium/1 | 首页从聚合仪表盘变成「现在最值得做什么」；识别并移除 competing cards | 5 Persona 第一眼能说出下一步；唯一 primary CTA；所有展示数据有 B-02 lineage |
| J-04 First Meaningful Action 端到端 | medium/1 | Goal capture→Context→Aurora→Proposal→confirm→Task 持久化串通 | GJ01 三端；5 Persona action 不模板化；重开存在；提案生成失败诚实处理 |
| J-05 「我卡住了」旗舰恢复旅程 | medium/1 | Stuck 做成全产品统一恢复入口；最多先问一个高价值问题 | 20 friction scenario ≥18 合理；UI ≤2 轮进 proposal；纠正产生 Memory/evidence candidate |
| J-06 Hybrid Flagship Journey | medium/1 | Agent prep→Human judgment→Agent execute/check→Outcome 可泛化样板 | 端到端真实工具/材料非预录；用户清楚自己必须做哪一步及为何；保留 source/citations/artifacts |
| J-07 Return/Stale Plan/Comeback | medium/1 | 回来能恢复而非面对过期 backlog；1/3/7/14 day test clock；不羞辱式累积 | 回来 ≤2 actions 到 meaningful next step；陈旧建议不复用；comeback rationale 有真实变化依据 |
| J-08 Completion→Reflection→Trajectory | medium/1 | 完成→artifact/outcome→milestone→reflection→experience→Galaxy 价值累积；不只展示分钟/streak | GJ03/GJ05 形成 outcome；Goal 页面/星图一致；Reflection 不凭空推断人格 |

---

## J.2 实际交付逐卡

### J-01 · First 3 Minutes 当前体验实测与机会图

**交付**：合入 `6f20931f`（2026-09-26，产品代码零改动）。测量基建：`mobile/integration_test/first3_measurement_test.dart`（1222 行，真实墙钟计时、每 persona 独立进程=真 clean install、双路线=guest 现实腿+own-goal 注册/登录/向导腿、截图序列+J01_MARK/TEXTDUMP/FINDING 结构化日志+j01_timings_*.json）+ 可复现 runner `scripts/devtools/run_j01_first3_measurement.sh`。证据全部入库 `v3/09_evidence/j01_first3/`（REPORT.md+OPPORTUNITY_MAP.md+PROGRESS.md+**101 张截图+2 份 timings json**，本次 git ls-files 亲证）。实跑：真后端 :8080/:8000，5×own_goal+1×example 全部完成，**头条=own-goal 全链路 245-314s，4/5 persona 超出 3 分钟预算**。

**机会图 11 项（O1-O11）的处置闭环（本次逐行核对修复标注+台账复核）——5 修 6 留**：

| 项 | 处置 | 证据 |
|---|---|---|
| O1 种子假目标无示例标识 | **已修**（选「改」路：保留种子+加标识）FIX-143 FIXED@`62241e59`（wt440，撞号 142→143 顺延有案）——Plan.source="example"+TaskDetail/GoalResponse/dashboard is_example 透传+首屏「示例」badge（红测 3+2） | guest_seed_service.py:2046-2093 亲证 source="example" 写入 |
| O2 guest own-goal 入口被种子堵死 | **未修**——cockpit set-first-goal CTA 仍仅 noGoal 态渲染（today_cockpit_card.dart:215 本次亲证）；J-02 wt764 快车道在 onboarding persona 屏给了另一条 own-goal 表达路径，cockpit 面未动 | 机会图 O2 行无 ✅；FIX 台账 0 行 |
| O3 注册桌面提交无效 | **已修/重定性** @wt436 `8ab9ff65`——拆两层：测量驱动假阳性（textAnySmart 命中 AppBar 标题）+**真实缺陷**（注册屏零键盘提交链，桌面 Enter 零响应）修 textInputAction 链+防重入（红测先行） | 机会图 O3 行内注记 |
| O4 保留域邮箱被拒+报错英文原文 | **未修** | 机会图 O4 行无 ✅；台账 0 行 |
| O5 Example Mode 无用户入口 | **已修** @wt436——登录屏新增「体验一个示例」次级 CTA（authTryExample 双语键，走既有 loginAsGuest 链路） | 机会图 O5 行内注记 |
| O6 splash/登录文案绑定备考 persona | **未修**——app_zh.arb:7200 `splashSubtitle:「期末一周，星火陪你备考…」`+:93 `welcomeSubtitle:「期末备考提分…」` 本次亲证仍在主干 | 机会图 O6 行无 ✅ |
| O7 wipe 后仍自动登录（keychain 残留） | **未修** | 机会图 O7 行无 ✅ |
| O8 首屏无来由 Lv.15 | **部分被旁路闭环**——B-02 审计链 F2（种子伪造统计）→FIX-257 guest 转正清洗（FIXED@2b32d728）+FIX-143 示例标识；纯 guest 首屏等级显示本身未见专项修复 | 机会图 O8 行无 ✅；FIX-257 行交叉引用 J-01 example 标记 |
| O9 注册成功路径不落 Dashboard | 未独立处置（依赖 O3 修后复测） | 机会图 O9 行「与 O3 一并修复后复测」 |
| O10 AI 意图分析网关 404（5/5 persona 静默回退 legacy 表单） | **已修** FIX-140 FIXED@`5aaf2c1a`（wt430）——网关 Goals 组补挂 POST /analyze-intent 代理（红测 404→转发可达） | FIX-140 行 |
| O11 向导终点创建失败（POST 307 不跟随） | **已修** FIX-141 FIXED@`5aaf2c1a`——根因=裸路径 307+dart:io POST 不跟随重定向；createGoal 改引擎规范面 `/goals/`（红测先行） | FIX-141 行 |

**验证证据**：全部计时真实墙钟可对账；instrumented 步骤逐 pass 标注（诚实声明在 commit+REPORT）；DEFERRED 如实留白（真机复测/O3 人手归因/录屏）。

**残差与引用状态（回答「机会图的结论还被引用吗」）**：①机会图本体是活文档——已修 5 项的修复注记直接写进行内（含 FIX 号与红测证据），被 FIX-140/141/143 三行台账与 FIX-257 行（「按 J-01 example 标记与 GJ02 demo→own 既有裁决保留」）引用；②**留 6 项（O2/O4/O6/O7/O8/O9）零台账跟踪**：无 FIX 行、无承接卡，只活在入库的机会图文档里——它们不是被遗忘的假账（图内如实无 ✅），但也没有任何机制保证 V4 会读到这里；③ wt772 审查把「N49 转 post-RC 独立跨层卡」列了，O 系列未获同等安排。

**一句话用户可见行为**：机会图本身无用户可见行为；它修掉的 5 项=「注册屏 Enter 键生效」「登录屏有体验示例入口」「目标向导能走通创建」「AI 意图分析入口可达」「种子目标带示例标识」。

### J-02 · Onboarding: Value Before Profile

**交付（三波）**：

| 波次 | 主干 SHA | 内容 |
|---|---|---|
| wt282 首波 | `f18f99f4`→`cd154f03`（baseline verified） | 软注册墙+persona 草案续存（8 字段 draft store，debounce+clamp，内容+步双恢复）+首跑具体字幕（N48 zh/en）；GuestConversionCard 盲区由 wt287 补（`2f27dd2a`/`e387f380`） |
| wt764 缺口闭环 | `787bc973`（2026-09-28，READY_FOR_REVIEW） | ①**最小 goal capture 快车道**：persona 屏步 1 目标非空即现 CTA，只提交 {goal_type, goal} 走既有 POST /profile/onboarding——服务端逐字段条件写入故四项偏好零上行；五问零裁减只延后（deferred 草稿步进，重进续答不重填）；失败诚实（SnackBar+重试）。红 0/4→绿 4/4，**红测揪出 400ms 防抖竞态**（迟到存稿以步 0 覆盖 deferred 草稿）就地修。②**namespace 隔离 J-02 级证据**：seed 后 memory_goals/episodic_memories 恒 0 行（结构隔离）+FIX-258 demo 轮跳记忆推断分支钉死（此前零覆盖）。③三端 session 稳定 router 三角钉（游客折回/升级可达/软墙不动）。④**≤3min 为 headless 验算非实测**（≈5 taps+55-70s，口径明示不勾验收框） |
| wt772 独立审查 | `588e65c2`（receipt 入库） | **PARTIAL 不销账**：工程面全合格（独立复跑 19+10+4 绿/变异咬合实证——注释 CTA 空目标守卫→用例 1 红/前人核对 wt282·wt287 均实在/五问零裁减语义核实/Forbidden 四条全过），唯一缺口=卡面 Required evidence 明列 integration/simulator evidence（FIRST_3_MINUTES 清单），验算不替代；notes 计数笔误（8/3/5 实 7/1/4）列更正项 |

**验收兑现度**：「只问改变 first action 的问题」=快车道 ✅（工程面）；「seed 不进真实 Memory」=namespace 隔离测试 ✅（机制属 FIX-257/258/142 既有裁决，本卡只钉不重建）；「三端 session 稳定」=router 钉 ✅；「fresh user ≤3min 到 useful action」=**验算已给、实测缺**（销账前置）；「注册/游客/升级三端 session 稳定」的实机面转 simulator 补证卡（门后排队）。

**一句话用户可见行为**：新用户在 onboarding 第一步写下目标就能拿到第一个行动建议，不必先答完五问问卷；演示种子不会混进自己的记忆。

### J-03 · Today Cockpit 重新定义主入口

**交付**：合入 `2421a04f`（wt306，2026-09-24，READY_FOR_REVIEW→后续 wt324 实证）。todayCockpitProvider 从 **5 个既有真源**派生四态（判定序 no-goal→stalled→active→fresh，字段级 B-02 lineage、零新权威）；TodayCockpitCard 唯一 primary CTA+why-now/goal-context/I'm-stuck/current-run；**dashboard 净 -810 行**（删 _HomeCommandCenterCard/_CommandCenterContent 等 7 组件），3 张竞争卡移除、6 槽默认折叠（15 槽配置）；与 wt302 StuckRecoveryCard 语义共存（用户主动 vs 系统侦测，合入后双验）；l10n zh/en 28 键。测试：cockpit 9+home 回归+结构 2（本次计数 today_cockpit_card_test.dart 9 函数）。

**模拟器实证（真驱动证据）**：wt324 `a08d20f0`（test(evidence) 卡，32 截图入库 v3-output/WT324-SIMEVIDENCE/）——**J-03 三态路径 PASS（真模拟器）**+collapse-slot 收敛 PASS；同轮猎出 F-4~F-11 十一项缺陷（含 2 BLOCKER：chat 长建议 GlobalKey 崩溃/plan_id 误存 current_goal_id 致 Goal 页 404）全部走 FIX 链闭环（450437c0 收官实录）。

**验收兑现度**：「唯一 primary CTA」✅（结构测试+wt371 J-04 挂载卡不与 cockpit primary 竞争的守卫）；「fresh/no-goal/active/stalled 四态」✅（三态路径真模拟器 PASS）；「所有展示数据有 B-02 lineage」✅（5 真源字段级）；「**5 Persona 第一眼能说出下一步**」——主观用户研究面未做（REPORT.md:81 如实标注 LIGHT 纪律禁模拟器、本报告不宣称；模拟器走查后由 wt324 补了三态可达性，5 persona 主观面仍属未做，如实留白）。

**残差**：JOURNEY day1-6 的 M2 门（today 面 day-N 任务浮现）持续验证 cockpit 活性（见 §J.2-JOURNEY）——这是 J-03 唯一的跨日真驱动证据面。

**一句话用户可见行为**：打开 App 首屏只有一个主行动按钮和「为什么是它」，而不是一墙仪表盘。

### J-04 · First Meaningful Action 端到端

**交付**：合入 `02b82cd2`（wt371，2026-09-25）+轮2 复核修复 `cc84094e`（wt379：study_minutes 容错/edit 事务边界重排——reject 失败 cancel 补偿，旧提案不再先销毁）。`backend/app/services/first_action_service.py`（638 行粘合层）六环串通：Context 环读 onboarding goal 真源（memory_goals）+显式偏好+账本计数→Aurora 环 LLM 推导 Smallest Useful Step（注入面 llm_chat，生产 GENERATION/FAST 同路）经 **X-01 ActionPlanContract 校验**（伪步骤/词表外 evidence 拒绝）→**execution_mode 权威=A-04 decide_allocation**（学习守卫拦 LLM 越权建议 agent→human/hybrid）→Proposal 环走 X-03 create_proposal（source=aurora,trace_id=first_action）→confirm→approve→TaskService.create **单 commit 原子落 V3 列（outcome/evidence/mode 三字段全链真实数据流）**。拒绝/编辑进 feedback（原断点=API 层丢 RejectProposalRequest.reason+service 硬编码归因——红测实锤后修）：reject(user_feedback) 持久进 transition.details+event_outbox（terminal_reason 封闭词表不放宽）。诚实失败：无 goal→422、推导失败→503 {first_action_generation_failed,retryable}、**失败路径零 proposal 落库不假装成功**。API /journey/first-action（POST/GET 回放/POST edit）+网关 /journey 纯代理组（registerREST 通配，本次亲证 J-08 trajectory 同享该组）。mobile：FirstActionRepository+FirstActionCard（重开回放=状态唯一来自 GET，零重生成）。

**红绿链与验证**：test_j04_first_action_chain 8 例在 base `0e4087ec` 全红（模块缺失/拒绝理由被丢/失败假成功）→修后 8 绿；**5 Persona 差异化断言**（五 persona 产出互不相同+prompt 携带各自 goal 原文+mode 经分配策略裁决）；持久化断言=新查询面读回 COMMITTED proposal+receipt+tasks V3 列；幂等=同 key 恰一次；mobile 真跑 8+5+8+12 绿（swap 门内实测）。现值：backend 8+2+2+mobile 8（本次计数）。

**残差（HUMAN_INBOX 转交三项，commit 原文明列）**：①GJ01 三端（Android/Web/macOS 真机）视觉与会话一致性——本机无设备，headless 断言已尽；②真模型（非脚本 LLM）下 5 Persona 实机首帧差异化观感；③503 诚实错误实机重试体验。卡面「GJ01 三端」未以实机闭环，转 HUMAN_INBOX 与 simulator 补证同族。

**一句话用户可见行为**：写下目标后立即收到一个不模板化的「最小有用第一步」提案，可确认/拒绝（带理由）/编辑，拒绝的理由会留在系统里影响后续；失败时明确报错可重试。

### J-05 · 「我卡住了」旗舰恢复旅程

**交付**：合入 `c4c36ead`（wt374，2026-09-25；前置 wt302 mobile StuckRecoveryCard 已建「系统侦测」面）。后端 /experience/stuck-journey start|answer|correct 三端点——`stuck_journey_service.py`（645 行）**装配层零重建真源**：context 读侧投影 Goal/Task 原样+近期失败计数读 task_stuck_signal_service 既有判据；**单问/主 intervention/差异化选问全交冻结 A-03 引擎（LLM 0 次，缺事实保持 None 不猜）**；单问上限=产品口径经预算声明落引擎 B1 best-guess（uncertain 如实标注）；「不是这个原因」纠正落新表 stuck_journey_corrections（迁移 j05_20260925，sqlite 重放 3/3）进反馈环：**被纠正类型按后验下一位有提名者垫后**（dataclasses.replace 零引擎内改动；无后继回落根分裂问+no_alternative 如实标注，不静默丢弃），纠正 14 天 freshness+20 容量。mobile 三面真实 context 入口（home cockpit CTA surface=home+当前任务 id/goal 详情卡住键/执行屏卡点帮助 sheet）+统一 StuckJourneySheet（≤1 问分支点选即答→主 intervention 中性文案+纠正回执「这类原因会往后放」）+guilt 红线（P-03 词表复用，30 词条零 guilt 零诊断式双语）。FIX-51 修后 main_intervention 恒带 delivery=recommendation 契约（FIXED@28442a5a）。

**验证证据（J 线最硬的一段）**：红测先行 backend 8 例全红→绿（404 面+真实 context 断言+差异化选问+纠正改后续判断）；迁移 3/3；**wt324 真模拟器 E2E PASS：stuck→chat→J-05 恢复链**（32 截图入库）；现值 backend api 9+迁移 3+mobile 3+3+1（本次计数）；JOURNEY 驱动的会话适应探针（day1-6 各日 J5 步，CP-04 S3）持续打同一引擎面。

**验收兑现度**：「最多先问一个高价值问题」✅（单问上限+≤1 问 sheet）；「UI ≤2 轮进入 proposal」=问→答→主 intervention 两轮内结构 ✅（测试断言链）；「20 friction scenario ≥18」由 A-03 fixture 承接（20 场景+hard_family 6，A 线章 §A.2-A-03）；「纠正产生 Memory/evidence candidate」✅（纠正表+反馈环，A-08/D-08 以其为飞轮链起点实证「纠正→后续判断改变」14 条）。

**一句话用户可见行为**：在任何屏幕点「我卡住了」，AI 至多问一个选择题就能给出主建议；选「不是这个原因」后，这类原因下次真的会被排到后面。

### J-06 · Hybrid Flagship Journey：AI 降摩擦但不偷走目标

**交付**：合入 `7bd6ade3`（wt381，2026-09-25）+合并态收口 `97b6eed0`（迁移单头重挂 s04b+schema 重导）+轮2 修复 `3b723e15`（wt392）。后端 /journey/hybrid 四面（start/judgment/outcome-confirm/GET state）——`hybrid_journey_service.py`（1045 行）装配层零重建真源：**run 脊柱=X-05/X-07 四步计划 prep[agent]→judgment[human]→execute_check[agent]→outcome[hybrid]**；prep 走真实注册工具 retrieve_user_material 经 **X-06 ToolExecutor 完整执行链（权限判定+账本行+真实 document_chunks 检索，零 mock 零预录）**；judgment 空选择 422 judgment_required（服务层结构性拒绝代决）+agent 完成 human 步被 X-07 owner 纪律拦截（**卡魂：AI 不替用户 judgment**）；execute/check=LlmChat 注入面起草（生产 GENERATION/FAST）+**C-04 parse_cited_markers 确定性核对（无引用/越集引用 503 诚实失败不落产物，同判断重放可续）**；outcome=用户确认交付经既有 TaskService 完成路径（X-08 capture 随之）+run SUCCEEDED+G-02 既有吸收器实测**点亮恰一次**（同因 receipt duplicate 只补溯源+双面重放幂等）；每段产物落新表 hybrid_journey_artifacts（迁移 j06_20260925，统一 citation 结构指向真实 chunk 行）。mobile 复用统一 Runtime/UI 不另起交接面（HybridJourneySheet=U-04 ownership 词表+ProposalActionGuard 防抖+X-07 AwaitingStepResumeCard，判断面空选择提交键结构性禁用）。

**轮2 猎缺修复（wt391 报告+wt392）**：F1(P1) prep 失败后死 run 钉死（两次内部提交+默认幂等键永 resolve 死 run→修=补偿诚实落 FAILED 终态+attempt-N 新 run）；F2(P1) complete 半确认孤儿（完成戳先于任务内部提交，失败后重试谎报已确认→修=事务重排+全部失败窗口收敛）；F3(P1) 客户端 extra_context.user_tier 自提 pro 车道→修=服务端真源优先升档门（wt380 契约不回退）；F4(P2) galaxy 失效缺口两层齐清。红测先行 8 例（unit 6+api 2）。

**验证证据**：红测 5 例 base `c4c36ead` 全红（含真实数据流 prompt 断言/judgment 不可代决 3 态负测/无引用与越集引用拒绝/G-02 恰一次+重放幂等）→绿；迁移 4/4；邻域 149 绿；现值 backend 5+12+5+4+mobile 3（本次计数）。「端到端真实工具/材料；不是预录」=工具链与检索面真实（**测试内驱动**）；「用户清楚自己必须做哪一步及为何」=judgment 面空选择禁用+四步可见。

**残差**：①execute/check 的 LLM 环走生产注入路，但 **J-06 名下未定位到独立真模型运行记录**（真模型证据面归 E-08 bench 与 JOURNEY 驱动，X 线章同口径）——「真实工具」✅与「真实模型」未混同宣称；②实机端到端走查转 HUMAN_INBOX。

**一句话用户可见行为**：用户发起混合任务后，AI 准备材料（可溯源引用）→**必须由用户做判断步**（AI 代做会被结构性拒绝）→AI 起草并自查引用→用户确认交付，全程四步在一个统一界面里可见。

### J-07 · Return / Stale Plan / Comeback Recovery

**交付（两波）**：

| 波次 | 主干 SHA | 内容 |
|---|---|---|
| wt303 mobile 首波 | `7624ec6a` | **三个真缺陷修复**：过期 sprint 永远挂着「last 24h」模式/Day highlights 前后端双处恒推 Day 1/陈旧建议双重复用——`plan_staleness.dart` 单一权威（3 天阈值+expired/stalled+可测日界）→详情页零羞耻横幅（真实日期）→一键重新校准进既有 PlanUpdate→陈旧建议三重抑制 |
| wt385 后端 | `1c852ed0`（2026-09-25） | `get_comeback_context` 增 reference_time 注入——**1/3/7/14 天全档可控时钟单 fixture 驱动**（1 天静默/3 天 time_passed 接回/7 天窗口耗尽 rescope 推荐/14 天长离诚实呈报），同钟重放 payload 逐字段相等；plan drift/deadline 变化检测+**差异化 rationale 三源封闭词表**（time_passed 恒有/deadline_changed=wt313 last_replan 回执晚于最后真实活动，证据含 previous→new/progress_drifted=窗口进度与任务账本拉开≥PlanProgressService 同源阈值）——「comeback rationale 有真实变化依据」的结构化兑现；Aurora rescope 复用 wt313 勿重建（payload rescope{available,recommended,endpoint}）；**primary_action{within_actions≤2} 量化**（新鲜窗=开任务 1 步/陈旧窗=重校准 2 步）；**陈旧建议不复用=SHIELD-INVAL 缓存穿透负测**（replan 重锚+target_date 编辑双写路径 notify 失效，API 级负测 TTL 窗内必须重估）；顺带修 ComebackContextResponse 静默丢弃 A-07 读侧投影（plan_expired/stale_focus/next_task_overdue_days/goal_state）；mobile rationale/rescope/primary_action 解析+「重新校准计划」单 tap 入口+chat_screen 按路由导航；零 guilt 词表断言双语 |

**验证证据**：红测先行 base `97b6eed0` 服务级 11 例 TypeError+API 级 KeyError+mobile 编译红全红→修后 backend 12+3 绿+邻域 434 绿+mobile 30 绿+plan/chat 邻域 314 绿（本次计数 aurora_comeback_context_test 等在树）；与 A-07 的 3/7/14-day clock 红测互为表里（A 线章 §A.2-A-07）。

**残差**：「回来 ≤2 actions 到 meaningful next step」以 primary_action.within_actions≤2 结构字段+测试兑现；真实用户回访的行为学验证未做（与全线一致转 HUMAN_INBOX 口径）。

**一句话用户可见行为**：离开一周回来，看到的是「计划窗口已结束+这里变了+重新校准（1 tap）」，而不是过期的 backlog 和陈旧建议；重新校准后两步内回到有意义的下一步。

### J-08 · Goal Completion → Reflection → Trajectory

**交付**：合入 `d105aa57`（wt386，2026-09-26）+里程碑 join 修复 `64e6cdff`（wt396 F5）。`backend/app/services/goal_trajectory_service.py`（545 行）**六环只读投影零新真源零新表零新迁移**：action→artifact（=J-06 HybridJourneyArtifact 既有产物行）/outcome（身份=X-08 derive_outcome_id 同一推导，D-02 账本 ledger_verified 真实查询核验——GJ03/GJ05 形成 outcome）/goal milestone（真实任务行终态推导；wt396 修=创建面任务 tags 持久化 goal_milestone:<id> 精确关联替代 created_at 位置 join——修前缺位即后续全部错位一位，且创建失败曾 except:pass 静默吞）/reflection（**TaskFeedback.reflection_payload 用户自报原样回声——不凭空推断人格**，契约锁含 −13 模式扫描负测：模板/连接回应/记忆摘要全零命中）/experience candidate（EpisodicMemory 真实行，M-03 候选契约字段）/Galaxy（经 provenance.read_graph_event_sources 新读投影=**星图 NodeWithStatus._graph_event_sources 同一函数**——两面呈现数据同源的结构性保证）；值叙事=成果/证据/反思计数，**分钟/streak 不入轨迹**。journey.py 新增 GET /journey/trajectory（诚实失败：无活跃目标 422/越权 404；网关经 /journey 通配组可达，本次亲证）。mobile：GoalTrajectoryCard 轨迹卡+星图 NodeDetailSheet 成果证据行——**同一 outcome id 两面同源断言**。

**验证证据**：红测先行 base `911dbeb7` 4 红（ModuleNotFound+ImportError=轨迹面缺失）+3 契约锁 base 即绿如实标注→修后 7/7 绿+邻域 134 绿；mobile 3/3 新测+goal 19 绿+galaxy widget 43/integration 8 绿；OpenAPI +61 纯增量恰 1 新路径。现值 backend 7+mobile 3（本次计数）。

**残差**：「避免只展示分钟/streak」以投影值叙事结构性兑现；「Goal 页面/星图一致」以同源函数+双面同 id 断言兑现；轨迹的长期价值感知（用户是否真觉得「看到了成长」）属用户研究面未做。

**一句话用户可见行为**：目标完成后，Goal 页和星图节点上都能看到「从想法到成果」的证据轨迹（做了什么/产出了什么/反思了什么），而不是一句「连续打卡 N 天」。

### JOURNEY day1-6 与 J 线卡的对应（比赛主线证据链）

**运行形态**：真用户 ns001（northstar_jrn_5a140173，run NS001-JOURNEY2-20260922-211514）七日真实驱动。**日界机制是真实的**——「进入 Day N」唯一途径=真实时钟跨日使 _plan_current_day 增长（JOURNEY-DRIVER 报告 §1.1 逐文件考证：date.today() 内联散布约 20 文件、无时钟 seam；方案 a/b 因违反诚实红线否决，选 c=真实跨日）。驱动器 backend/tests/northstar_eval/real_drive.py。

**状态文件硬证据（本次直接读取）**：/tmp/northstar_ns001_real_drive_state.json + 备份 Sparkle-sysrev/.journey_ns001_state_backup.json——day1_run_date=09-22、day2=09-23、day3=09-24、day4=09-25、day5=09-26（task 125cda75「Day 5·检索攻克-欧拉图与哈密顿图等3个点」自然浮现，08:18 门 PASS）、day6=09-27（task 60557135）全部 done=True；day7_done 未置（门=09-28 08:00，在本文档状态快照之后）。fleet notes 逐日门记录与 state 一致。

**day6 门的示范性插曲（诚实红线运行样本）**：08:00 首跑 M2 语义停（零候选 TODO 任务）→按纪律停、留证、不硬造→30 分钟定根因（day:6 任务 PENDING 在库而 /tasks/today 空=plan.created_at 钟名语义）→FIX-314 当日紧急卡 wt602 修复→live 库迁移→栈刷新→**门前自验恰浮 Day 6 任务**→08:26 重跑 M1-M4 全 200 PASS（6/7）。后续 wt615 曾翻案该修法的前提（FIX-326），wt618 终审裁决收敛到 sprint_day_math.py 单一权威并把「day7 today=09-28→current=7」做成常驻钉测试——时钟战役 314/318/319/320/322/323/326/327 全闭账。

**day7 终门预备**：手册 runday7.md（193 行，wt746 `13376533` 入库 v3-output/WT746-REHEARSAL/）+独立安全核验 GO（wt751，v3-output/WT751-RUNDAY7-CHECK/verdicts.md：kill 面恰 3 PID 定靶/STATE 仅只读/gate_day7.py 字节分毫不差/alembic AST 定谳单头 wt598_20260927/回退零不可逆——七项全 PASS，0 BLOCKER）。

**与 J 线卡的对应关系（V4 诚实口径）**：day 门 M1-M4=登录→**today 面浮当日任务（J-03 cockpit 面）**→start→complete。day1-3 相位另含晨间面板读取/复习队列提交/会话适应探针（CP-04 S3，打 A-03/wiring 面）/星图结算（G 线）。**JOURNEY 验证的是「真实日界的计划-任务-完成闭环」，即 J-03 面+任务生命周期+计划日推进；J-04/J-05/J-06/J-07/J-08 五段旅程不在七日门循环内**——它们的证据是各自卡的红绿链+wt324 真模拟器 E2E（J-03/J-05）。V4 引用「七日真实驱动」时应表述为日循环闭环证据，不得扩展为「七段旅程全部真用户走查」。

---

## J.3 设计决定与取舍（从提交/审查考古）

1. **J-01 「先实测后动刀」与「地图即交付」**：卡面 Forbidden「不先改代码」被严格执行（产品代码零改动），产出直接可执行的修复清单而非泛泛 UX 报告——5/11 项在两周内经 FIX-140/141/143+wt436 闭环，其余 6 项如实留在图上。取舍：机会图是文档不是台账，未修项没有追踪机制（§J.4-2）。
2. **J-02 「验算不冒充实测」**：wt764 把 ≤3min 明示为 headless 验算、不勾验收框、实测留 Reviewer——审查方据此判 PARTIAL 而非放行。这是「无设备时交付阻塞证据，不伪造通过」红线在旅程卡上的正面样本：**销账缺口被诚实保留，补证卡排队而非降标准**。
3. **J-03 「组合而非新建」**：四态全部从 5 个既有真源派生（B-02 lineage 字段级），dashboard -810 行是「删」的交付——把首页从信息架构问题变成排序问题的解法。
4. **J-04/J-06 「装配层零重建真源」**：两个旗舰服务都不拥有任何权威数据——Context 读 memory_goals、执行权读 A-04、提案走 X-03、run 脊柱用 X-05/X-07、引用核对用 C-04、outcome 用 X-08/D-02。J 线的代码量几乎全是装配与诚实失败路径；卡魂（AI 不偷走目标）落在 X-07 owner 纪律的**结构性拒绝**（422/代做拦截）而非提示词。
5. **J-05 「引擎冻结复用」**：旅程面不复制摩擦逻辑，全部选问/干预交冻结 A-03 引擎（LLM 0 次），纠正反馈用 dataclasses.replace 零引擎内改动垫后——修复面只有一张新表；两面守卫差异后来以 delivery=recommendation 契约声明化（FIX-51）而非静默。
6. **J-06 「真实分层宣称」**：交付时把「真实工具链+真实检索」与「真实模型」分开表述——工具/材料/引用核对全真实，LLM 环走生产注入路但独立真模型运行记录不宣称。诚实边界写在交付里，V4 引用时不应混同。
7. **J-07 「可控时钟+真实依据」**：1/3/7/14 全档单 fixture 驱动替代真实等待；rationale 三源封闭词表（time_passed/deadline_changed/progress_drifted）保证「为什么重新校准」永远有真实变化依据——防的是「AI 编造关心」。
8. **J-08 「回声而非推断」**：reflection=用户自报原样回声+13 模式扫描负测（人格结论/连接回应/记忆摘要全零命中）；轨迹=计数叙事+同源投影。「展示成长」与「编造成长」的边界用结构守住。

---

## J.4 残差与 V4 注意点（汇总）

1. **J-02 是全 V3 唯一的非 done 卡，且差距是证据而非工程**：simulator 实测补证卡排队门后——V4 开工第一周若做 onboarding 相关任何事，应先收这张补证（复用 B-03 v2 harness 的 macOS lane 即可，成本低）。
2. **J-01 机会图 6 项零追踪**（O2 guest own-goal 入口/O4 域邮箱文案/O6 备考绑定文案/O7 keychain 自动登录/O8 无据等级/O9 注册落点）——全部在入库的 OPPORTUNITY_MAP.md 有证据行，但无 FIX 行无承接卡；O6 文案本次亲证仍在主干（app_zh.arb:7200/:93）。**V4 做「面向比赛的多 persona 叙事」时，O6（splash 写死备考）与 O2 是最直接影响演示观感的两颗钉子**；O8 已被 B-02→FIX-257/143 链部分旁路闭环。
3. **七段旅程的真实验证深度不均**（§J.0 表）：有真驱动证据的只有 J-01（macOS 集成测试）、J-03/J-05（wt324 真模拟器）与 JOURNEY 日循环（J-03 面）；J-04/J-06 的「真实」是工具链层；三端实机走查全线转 HUMAN_INBOX。V4 的验收模型应把「旅程级真机证据」列为独立验收轴，而非沿用「headless 断言已尽」。
4. **JOURNEY 七日门的证据边界**：day1-6 全绿+day7 手册与安全核验 GO 在案，但 day7_done 在本文档状态快照时点未置——并入 v0.4 时应核对 day7 最终结果再落笔「7/7」。门循环验证的是日界闭环，不含五段旗舰旅程（§J.2-JOURNEY 末段口径）。
5. **J-06 的 503 诚实失败路径与死 run 修复**（wt392 F1/F2）值得 V4 作为「长旅程可恢复性」的设计输入：prep 失败补偿 FAILED 终态+attempt-N 新 run+半确认事务重排——可恢复 Run 在旅程面的落地样本。
6. **J 线核心测试面**：backend 约 70 测试函数（J-02 4+J-04 12+J-05 12+J-06 26+J-07 15+J-08 7，本次逐文件计数）+mobile 约 47（cockpit 9/first_action 8/hybrid 3/stuck 7/onboarding 8/comeback 族/trajectory 3 等）；J-06 另有 run steps 面 17。
7. **审查 receipt 文件化缺口（形态残差）**：wave-2 五卡（J-04~J-08）REPORT 未入库、签收在 commit message（wt759 判合规、台账零断链指针）；J-02 是例外正样本（wt772 receipt 77 行入库）。V4 若要求文件化按 FIX-502 三选一同构处理。

---

## J.5 本次审查登记

- **零新登记**。候选发现逐一判定：①J-01 六项未处置——机会图内如实留白（无假 ✅）、无台账指针指向不存在文件，属「诚实留白缺追踪」而非假账，作 §J.4-2 残差显式登记入章；②J-02 审查已返（PARTIAL）而 v0.3 文档写「wt772 在航」——文档时点滞后，本文件 §J.0 已给终态，随章并入即修正；③wave-2 五卡 REPORT 未入库——wt759 已裁决的 commit 内签收形态且台账零断链指针（区别于 FIX-502），按 A/C 线先例作形态残差。
- 号占用核验：505 起空闲（grep 全仓 v3/ v3-output/ docs/ backend/ `V3-FIX-50[5-9]`/`V3-FIX-5[1-9][0-9]` 零命中；499=wt767、500/501=wt765、502/503=wt770、504=wt769 已占用）。
- J 线相关 FIX 全链状态复核：FIX-59 FIXED@28442a5a｜FIX-140/141 FIXED@5aaf2c1a｜FIX-143 FIXED@62241e59｜FIX-257 FIXED@2b32d728（J-01 O8 旁路链）｜F-4~F-11（wt324 发现族）全部含测试证据收官（450437c0）｜FIX-314 时钟族 314/318/319/320/322/323/326/327 全闭账（wt618 终审 sprint_day_math.py 单一权威）。
