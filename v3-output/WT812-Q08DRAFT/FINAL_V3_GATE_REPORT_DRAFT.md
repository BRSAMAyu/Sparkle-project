# FINAL_V3_GATE_REPORT_DRAFT.md —— 非公网 gate 裁决草案（wt812，Q-08 双审前）

> ## ⚠️ 双审前的主会话裁决草案（非终判）
> **本文件是 Q-08 正式裁决的草案底稿，不是终判。** 所有 PASS/FAIL/BLOCKED 字样均为「草案裁决」，效力止于：给主会话与双 reviewer 提供可证伪判据齐备的裁决底稿。FINAL 状态在 ①待拍板项（§2）落定 ②双 reviewer 独立签收（卡面 Reviewers: 2）之前一律为 **DRAFT**（骨架 §2.4 规则 7）。本草案不改 DoD 原文、不改台账、不改 tasks.json、不碰运行栈、不 push。
> Worker: wt812 ｜ 分支 `agent/wt812/q08draft`（worktree wt812）｜ 基线 main@`5c288841`（2026-09-28，含轮#314 后 FIX-554 登记）｜ 上游骨架=[WT804-Q08SKELETON/FINAL_V3_GATE_REPORT.md](../WT804-Q08SKELETON/FINAL_V3_GATE_REPORT.md)
> 覆盖范围：**不依赖 O-01 公网面的 10 个 gate**（V3-0..V3-6、V3-8、V3-9、V3-10）；V3-7 双口径中口径A（API 级+模拟器/桌面通道）预填、**口径B（真机）BLOCKED 段留空标「待 O-01」**（阻塞归因注记按证据如实拆分，见 §1.V3-7）。
> 弹药引用：[WT806-V32MEMO/memo.md](../WT806-V32MEMO/memo.md)（预裁②）｜[WT808-Q08PREJUDGE](../WT808-Q08PREJUDGE/report.md) memo-3/4/6（预裁③④⑥）｜[B-01/MODULE_MATRIX.csv](../B-01/MODULE_MATRIX.csv)+[WT790-B01DELTA](../WT790-B01DELTA/delta_report.md)（预裁①）｜[WT801-E08FINAL/report.md](../WT801-E08FINAL/report.md)+[WT803-E08REV/receipt.md](../WT803-E08REV/receipt.md)（E-08）｜[WT802-J02-RETEST/REPORT.md](../WT802-J02-RETEST/REPORT.md)（J-02）｜[DYNAMIC_ISSUES.md](../../v3/06_agent_fleet/DYNAMIC_ISSUES.md)（台账）。
> 诚实纪律：证据链断的地方如实写断（本次新增断裂 1 处=§1.V3-0 W12-01）；本会话未亲证的判据逐条标注「未亲证，引用来源」。

---

## 0. 草案时点快照与增量事实（vs 骨架 @054b8c9b → 本草案 @5c288841）

| 项 | 骨架时点 | **本草案时点（亲证）** | 出处 |
|---|---|---|---|
| tasks.json | done=104 / TODO=3 | **不变：done=104 / TODO=3**（O-01/Q-07/Q-08） | `v3/07_tasks/tasks.json` 机器口径实测 |
| CI | 四绿（23/25/27/29） | **五绿 gh 逐条实核（23/25/27/29-rerun/30）＋第 6 绿（31）与 CI 32 在跑系主会话引述（协调分支 state 口径，本 worktree 不可 gh 实核）**；CI 29 attempt1 真红=FIX-547（已修，wt807 分支@`45336b1b` 在途未并主干，v0.9 §6 如实标注） | [V3-COMPLETE-STATUS-FOR-V4.md §6](../../v3/V3-COMPLETE-STATUS-FOR-V4.md)（v0.9）、轮#312-#314 |
| mypy | 55 零漂移 | **双口径：本地棘轮 55 ／ CI 基线按首绿实测对齐 77**（差异披露在 v0.9 §6/§9， greens 27/29r/30 连过门） | 同上 |
| 台账 | 45 OPEN（P2×5） | **46 OPEN（P2×5：168/439/505/542/545；P3×33、P4×8）——机器口径实测（行尾状态格 `^OPEN` 正则）；原计 47/P2×6 系 FIX-547 陈旧 OPEN 重复行误计（同 ID FIXED@3bf967ac 在册，wt816 一审 C2 勘误 2026-09-28 已正）。P1 维持 0** | [DYNAMIC_ISSUES.md](../../v3/06_agent_fleet/DYNAMIC_ISSUES.md)（431 行）@5c288841 |
| E-08 | 复测已补 4P/2F | 不变；独立审查 **APPROVE-closure**（条件 C1=追踪义务落账——已落 FIX-545 行，台账 L417 亲证） | [WT803-E08REV/receipt.md](../WT803-E08REV/receipt.md) §1/§6 |
| J-02 | 全量 6/6 | 不变（A1a 99.8-102.2s×6、FirstActionCard 6/6、纯 UI 注册 6/6） | [WT802-J02-RETEST/REPORT.md](../WT802-J02-RETEST/REPORT.md) |
| 预裁 | ①已裁 ②在航 ③④⑤待 | ①已裁@`cf8d6c16`（**但入册存在缺口，见 §1.V3-0 W12-01**）②③④⑥备忘齐（wt806/wt808）；⑤仍待 | git log 亲证 |
| **新发现** | — | **W12-01：B-01Δ 入册缺口——权威矩阵 F20/F26 两行未改写＋portfolio.json 内容未同步（详见 §1.V3-0）** | 本草案 `git show cf8d6c16` 亲证 |

---

## 1. 逐 gate 裁决草案（三件套：裁决＋可证伪判据＋证据链接）

> 值域遵骨架 §2.4：PASS / FAIL / BLOCKED / NOT_RUN；「PASS-with-notes」=PASS 附必须随 FINAL 报告入册的注记；「FAIL-派V4」=FAIL 附 V4 工作项定义。

### Gate V3-0 — Truth

- **草案裁决：FAIL（可翻案，修复=机械合并）**。理由不是五态结构缺失，而是**权威矩阵这个「唯一真源」当前与已裁决结论自相矛盾**——在以 Truth 命名的 gate 上，artifact 与裁决注的漂移本身就是 gate 条款违反。
- **W12-01（本草案新发现，证据链断裂点，全部亲证）**：
  - 入册 commit `cf8d6c16`（"B-01Δ 入册——权威矩阵 42→43（F20/F26 重定/…）"）实际 diff：`MODULE_MATRIX.csv` 只删 F24 行＋追加 F43/F44 两行（3 行变更），**F20/F26 两行原样未动**——现 CSV 中 F20/F26 仍为 `HIDDEN`、`source_sha=a2d8a10c`（Δ 前旧基线），且 F20 的 v3_surface 格仍载「死屏建议 RETIRE」，与 [WT790-B01DELTA/delta_report.md](../WT790-B01DELTA/delta_report.md) 明文「RETIRE 倾向建议撤销」及 Δ 判定 `CONTEXTUAL` 直接矛盾（Δ 权威记录=[WT790-B01DELTA/MODULE_MATRIX_DELTA.csv](../WT790-B01DELTA/MODULE_MATRIX_DELTA.csv) 五行 F20/F24/F26/F43/F44@`27bd05e5`）。
  - `portfolio.json` 同 commit 仅追加顶层 `feature_count:43`＋`b01_delta_merge` 元数据块，**features 数组内容零同步**：onboarding 仍在册且标 CORE、leaderboard/photon 仍 HIDDEN、无 journey/recovery 条目——metadata 与内容自相矛盾。轮#313「portfolio.json 同步」表述与 artifact 实况不符。
  - DoD V3-0 决议注（`cf8d6c16`，[V3_DEFINITION_OF_DONE.md](../../v3/V3_DEFINITION_OF_DONE.md) L6）宣称「F20/F26 重定 CONTEXTUAL；唯一真源=MODULE_MATRIX.csv」——**决议注与被指为真源的 CSV 在 2/43 行上互相矛盾**。
  - 连带：台账 FIX-533 闭账注记「B-01Δ 入册完成」（`ea861e02`）在 artifact 层面不成立（FIX-508 族「账面 FIXED vs 产物事实」同型）。
- **可证伪判据**：①`awk -F',' '$1=="F20"||$1=="F26"{print $4}' v3-output/B-01/MODULE_MATRIX.csv` 现输出 `HIDDEN/HIDDEN`（Δ 判定应为 `CONTEXTUAL/CONTEXTUAL`）——实测复现；②`python3 -c "import json;print([f for f in json.load(open('v3-output/B-01/portfolio.json'))['features'] ...])"` 中 onboarding 仍在、journey/recovery 缺席——实测复现；③修复后同两判据翻转＋43 行逐行 `source_sha` 可溯。
- **翻案路径（机械、零代码，半小时级）**：按 DELTA CSV 把 F20/F26 两行改写为 CONTEXTUAL@`27bd05e5`（含 reachability_evidence/v3_surface 同步 delta_report §项1/项2）；由合并后 CSV 重建 portfolio.json features 数组（保留 b01_delta_merge 块）；FIX-533 行加注或重开走协调方渠道。**修复后 V3-0 草案翻 PASS-with-notes**（注记=钉时点审计，见下）。
- **其余条款面（不受 W12-01 影响，证据在位）**：feature 拓扑亲证 43 目录与册载可恢复 1:1（Δ 审计口径）；本草案追加实测：`27bd05e5..5c288841` 共 95 commit 中 mobile/lib 仅 6 文件变更（151+/50-，全是 FIX-539/540/800 tokens 族），**feature 目录拓扑零漂移**（`git ls-tree` 差集为空，亲证）——支撑「钉时点注记」而非全量重跑（见 §2-拍板7）；mock/seed 隔离（FIX-258）、能力宣称真实化（FIX-333）台账 FIXED 在案；无用户可达半成品入口由矩阵 reachability 列承载。
- **证据链接**：[B-01/MODULE_MATRIX.csv](../B-01/MODULE_MATRIX.csv)（含缺口）、[WT790-B01DELTA/MODULE_MATRIX_DELTA.csv](../WT790-B01DELTA/MODULE_MATRIX_DELTA.csv)、[WT790-B01DELTA/delta_report.md](../WT790-B01DELTA/delta_report.md)、[B-01/REVIEW_RECEIPT.md](../B-01/REVIEW_RECEIPT.md)（42/42 EXACT MATCH 系初始口径）、DoD 决议注@`cf8d6c16`（本 worktree 亲证为 HEAD 祖先）。

### Gate V3-1 — First Meaningful Value

- **草案裁决：PASS-with-notes**。
- **可证伪判据与证据**：
  - 「≤3 分钟 meaningful action proposal」：J-02 全量秒表 **6/6 ≤180s（98,767-102,170ms（一审 C3 勘误：原误 99,767），另有迭代跑 51,347ms 佐证带宽下限）**、FirstActionCard 6/6、纯 UI 注册 6/6 无 bounce——run_id `j02retest_macos_20260928_101701_wt802`，[WT802-J02-RETEST/REPORT.md](../WT802-J02-RETEST/REPORT.md) §0/§1 delta 表。判据=verdict.json leg_r_runs 全 in_budget；复现=同 harness 重跑。**引用口径注记：这是 J-01/J-02 秒表面（macOS desktop 真应用通道），非统计分母口径，随报告注明。**
  - 首屏无内部名词＋A/B 清零：[WT401-Q03-VISUAL/rubric_scores.md](../WT401-Q03-VISUAL/rubric_scores.md) 核心 13 屏 A/B=0（渲染形态=flutter_tester 390×844@2x 单档，引用时保留此限定）。
  - demo 不冒充用户历史：FIX-143 FIXED@`62241e59`（`is_example` 全链透传＋「示例」badge）；J-02 A1b 种子隔离活栈复证（guest_03a6e396305e：memory_goals=0、episodic 3 行全归属自身 uid）。
  - 无 P0/P1 阻断：J-02 四件闭环（FIX-539/540/543 端到端实证）；JOURNEY ns001 day1-7 门 7/7 PASS（轮#289，升栈 0-7 步全绿为基座）。
- **必须随报告入册的注记（如实带上）**：①R9 确认面文案缺口——后端 approve 200＋status=COMMITTED＋DB tasks=1 ×6，但 60s 窗内 UI 无「已创建」面（WT792 已知缺口原样，6/6 如实留证不阻塞）；②FIX-541 落点分歧族——注册/升级后落「我的」tab，驱动以真人路径恢复，软墙 resume 卡 6/6 达成（541 家族扩展实证在档）；③A2c upgrade 的 UI dashboard 面受同族落点影响（后端翻转语义活栈实证，UI 面未全通）；④真机/三端实机走查段未采集（随 V3-7 双口径，不在此 gate 重复计）。
- **证据链接**：同上四处＋[WT792-J02-SIM](../WT792-J02-SIM)（首跑降级口径对照）。

### Gate V3-2 — Stuck → Useful Action

- **草案裁决：PASS-with-notes（条件裁决）**——条件=**S4 采口径A**（§2-拍板2）。若主会话裁口径B，则本 gate 翻 **FAIL/BLOCKED（需新证据卡）**，两分支不可含糊（[WT806-V32MEMO/memo.md](../WT806-V32MEMO/memo.md) §③）。
- **六子项裁决草案（依据 wt806 memo，映射=原文 4 bullet 拆 6 子项）**：
  - **S1（20 场景集合存在且代表性有依据）：PASS**。载体=`backend/tests/aurora/fixtures/friction_diagnosis_scenarios.json`（scenarios=20＋hard_family=6＋persona×5＋sha256 四指纹双钉，亲证存在）；全库唯一与原文数量语义精确对应载体（wt806 grep 全库确认）。
  - **S2（≥18/20 运行判定）：PASS（规则层口径）**。`backend/tests/unit/test_a03_friction_diagnosis.py` 对生产模块 `diagnose_friction` 直跑断言 ≥18＋hard_family 全过；wt806 在其 HEAD 实跑 112 passed（**本会话未重跑，引用其记录**）。注记：gate 原文未规定模型口径；真模型面现有证据仅 E-04 intervention face 5 golden cases 15/15（`58d08c6f` dual-reviewed）；**20 场景全量真模型复验无记录——如实带注记，是否要求复验随 §2-拍板2 一并显式裁**。
  - **S3（intervention 与真实原因一致）：PASS**。同 rubric 三重匹配（outcome 精确＋friction_in 归因集＋nomination_first_in）＋burnout/skill 错分类代价面，112 passed 内。
  - **S4（输出五要素）：条件 PASS（口径A）/ FAIL（口径B）**。4/5 要素有类型化契约（`backend/app/core/action_plan.py`：outcome/smallest step/完成证据/人机模式；X-01 合入 `43942d23`）；**缺口=why-now 无 task 级契约字段位（X-01 REPORT §6.7 自证）**；Aurora 侧主动建议路径已有 why_now（`backend/app/signals/aurora_core_session.py:59`、`orchestration/plan_quality_contract.py:211`）。口径A=「输出=intervention/proposal 输出」→ PASS＋task 级缺位登记 V4 卡；口径B=「输出=ActionPlan/task 级」→ FAIL/BLOCKED。
  - **S5（防无限缩小任务）：PASS（契约层口径）**。`action_plan.py:204`「伪步骤不合法」（useful_because 空集拒绝）＋六判据封闭词表＋词表外拒绝；系统级拆分深度 eval 全库未找到——登记增强项不阻塞。
  - **S6（高风险/信息不足 clarify/abstain）：PASS**。`backend/app/core/aurora_decision.py:324,331,170`（clarify 必带问句/abstain inert）＋A-02 inert 地板＋A-03 One Best Question 预算＋E-04 A1 真模型 case＋X-10 high-risk auto=0（77 场景）；wt806 实跑 193 passed（引用其记录）。
- **诚实注记**：tasks.json J-05 标 done 但其 REPORT 不含 20-scenario 评测证据——本 gate 主证据在 A-03 测试面，读证据以 wt806 memo §② 指针为准（wt806 §⑤ 原文）。
- **证据链接**：上述文件路径全部经本会话 `ls`/开文件亲证存在；测试判定数字引 wt806 memo（其 §⑤ 声明本地 sqlite/零 LLM 实跑）。

### Gate V3-3 — Human–AI Collaboration

- **草案裁决：PASS**。
- **可证伪判据与证据**：
  - 分配评测 ≥90% 符合 rubric：X-10 77 场景 **allocation 100%（28/28）达标、false success=0、`real_llm_calls=0` 判定器强制断言**（[X-10/REPORT.md](../X-10/REPORT.md) §0/§2＋[results.json](../X-10/results.json) 891 条 checks 全留痕＋7 组变异红证防判定器失明）；rubric 统计锚=X 线章 77/77＋85 场景盲评（[WT770-DOC-MX/X-line.md](../WT770-DOC-MX/X-line.md)）。**引用纪律：X-10 系零 LLM 口径，引用时按 memo-4 §5 标注 `real_llm_calls=0` 为显式设计，不与真模型口径混写。**
  - 高风险不可逆 autonomous execution=0：同 X-10（high-risk auto=0，不变式覆盖 5 场景＋high_risk×4 需审批）。
  - 人形成能力/判断的步骤不被替代：cognitive ownership 契约（`action_plan.py` user_core/shared/delegated 正交）＋P-04 低风险 auto-execute 五条件门 fail-closed@`cffd4034`。
  - Hybrid handoff 可恢复：GJ14 run 恢复 admin 门＋resume PASS 面（[WT394-Q02-GOLDEN/summary.json](../WT394-Q02-GOLDEN/summary.json)）；X-07 双 resume 幂等（`v3-output/X-10` 同族判定器钉死）。
- **证据链接**：同上。无待拍板项。

### Gate V3-4 — Personalization That Helps

- **草案裁决：FAIL（NOT_REMEASURED 形态，如实交付）——是否补跑翻案随 §2-拍板3（预裁⑤）**。
- **可证伪判据与证据**：
  - **修前 dashboard 快照（现值口径）**：[WT404-Q04-REDTEAM/dashboard.json](../WT404-Q04-REDTEAM/dashboard.json)（`git_sha=46762b31`、100 records、20 blind pairs，本会话程序化读数亲证）——fleet 级 **precision=0.0（目标 0.95）、valid_uses=0/10、gates 全 false、acceptance="FAIL"**；over-personalization 41.67%（p01/p02 per-persona `overpersonalization_rate=0.4167` 实测）；paired uplift=0.0pp。同报告四路隐私/隔离面 PASS（敏感零泄漏/删除撤回零复活/跨用户零串号/无关历史零上 prompt）。
  - **修复与锁（修后无全量重跑）**：FIX-67 FIXED@`7244efb2`、FIX-68/69/70 FIXED@`12ce081b`；q04 两锁翻转＋双失明锁 `backend/tests/q04_personal_redteam/test_q04_redteam_final.py`（亲证存在，套件在 445 实跑绿内）。**锁级证据不能替代 dashboard 级复测——这是 FAIL 判定与「按锁级判 PASS」选项的区别线。**
  - **必须如实带上的反证分量（wt816 一审 C1 勘误后口径）**：uplift 0.0pp（Q-04 dashboard 级）为个性化净贡献未证的主要反证；A-08 消融（[WT393-A08-ABLATION/summary.json](../WT393-A08-ABLATION/summary.json)）journey 面**方向实为正贡献**——full 臂 stuck_accuracy=0.65 > no_memory 臂 0.55（净 +0.10）、utility full=-16.2 > no_memory=-21.4（净 +5.2，WT393 REPORT 原文「方向达成（含反例）」）——原草案此处方向写反（一审 CHALLENGED C1，2026-09-28 已正）。两证据不同向，不构成「双独立同向证据」；FAIL 判定依据=dashboard precision 0.0+修后无 dashboard 级复测（NOT_REMEASURED 形态），此两条不因 A-08 方向勘误而变。DoD 原文「达不到必须报告真实结果而非改口径」。
- **FAIL-派V4 内容（若不补跑）**：V4 工作项=q04 六路红队全量复测（驱动在库，约半窗），产出修后 dashboard 级复测＋uplift 重估；复测前任何 PASS 表述均不成立。
- **证据链接**：同上。

### Gate V3-5 — Data Flywheel

- **草案裁决：PASS-with-notes（机制口径，采预裁⑥丙案为草案基线；随 §2-拍板5）**。
- **可证伪判据（memo-6 §4 三判据，本会话执行状态如实标注）**：
  - **C1（修复在主干）**：`git merge-base --is-ancestor 8e503cd8 HEAD` → **本会话亲证成立**（8e503cd8 是 5c288841 祖先）。
  - **C2（f507 双套 14 测绿）**：**本会话未重跑**——引用 wt797 修后绿 14（5+9）与 wt806 基线实跑记录；路径勘误：memo-6 引 `backend/tests/test_f507_*.py`，**实际路径=`backend/tests/services/test_f507_readface_dataflow.py`＋`test_f507_lifecycle_wiring.py`**（本会话 find 亲证），正式执行复核时按此路径。
  - **C3（运行栈≥`cdc547be`）**：`cdc547be` 为 HEAD 祖先（亲证）；活栈含接线由 wt801 notes 头部亲证（09:55:27 滚启，栈=主干 `cdc547be`）；Q-08 正式执行时点需复核当次滚启状态。
- **条款级映射**：条款1（连接性）=PASS 机制口径＋运行级注记三行（507 FIXED@`8e503cd8` 三写面接线／滚启激活@轮#299／**运行级生产写入截至本草案时点未采样——本会话无 DB 访问，P1 读探针未执行**）；条款2（五维）=D-08 十 persona 五维全部迁移（[WT397-D08-FLYWHEEL/REPORT.md](../WT397-D08-FLYWHEEL/REPORT.md) §1）；条款3（不显示未校准百分比）=校准恒等回退链（`52dab3af`）；条款4（过去什么有效＋相关/因果区分）=D-08 双臂配对 10/10＋25 条无效照登（台账不粉饰面）。
- **P1 判读纪律（引用 memo-6 §4）**：exposed≥1 且下游≥1→注记升级为实测；仅 exposed→「写入在证、下游待流量」；全 0→**不构成断链反证**（激活后流量形态无 friction 干预型）；若期间实际发生过「我卡住了」型会话仍零行→升级 P2 定向探针（派实现 worker，半小时级）。
- **证据链接**：[WT797-F507/notes.md](../WT797-F507/notes.md)（修复全录＋「D-08 lifecycle 写入系 harness 直接驱动，非生产流量」自证）、台账 FIX-507 行（L392 区 FIXED@`8e503cd8`）、[WT801-E08FINAL/notes.md](../WT801-E08FINAL/notes.md) §4（507 解释性注记不可反用为运行级证据——memo-6 §2.5 原文）。

### Gate V3-6 — Trustworthy Agent Runtime

- **草案裁决：PASS-with-notes**（两项低成本补证未齐——作为 FINAL 前补齐项而非阻断项，随 §3 checklist）。
- **可证伪判据与证据**：
  - 三零硬门（false success=0 / cross-user access=0 / duplicate side effect=0）：X-09 18 failure_kind 四归因分类器 162 组合×100 次零偏差＋SIGKILL 真杀进程 e2e＋UNKNOWN_OUTCOME 禁自动重试（dual-reviewed `0c0e08ef`）；测试在库亲证：`backend/tests/unit/test_x09_failure_recovery.py`＋`test_failure_semantics.py`。跨逻辑重试 duplicate 通道已由 FIX-335 轨道 A＋wt699 意图稳定键闭合（台账 L334 亲证 FIXED@`b06969d3`，红→绿 8/8＋护栏 53 passed）。
  - 「100 run ≥99 terminal」批量统计锚：**未定位到证据（维持骨架结论；本会话复查 v3-output 无 X-09 独立产物目录——X-09 证据面在测试库＋卡双审记录）**。X-09 卡面验收为「20+ chaos cases」，与 DoD 的 100-run 批量统计不是同一口径——如实注明。补证路径=从 X-05/09 测试面提取或按同形制补跑（低成本项）。
  - 恢复三态（app 重开/WS 重连/worker restart）：FIX-461（PEL 重放）/469（幂等闸）/487（清理接线）全 FIXED；GJ14 resume 面（V3-3 同锚）。
  - cancel/timeout/retry/unknown 语义：test_failure_semantics.py＋UNKNOWN_OUTCOME 面。
  - tool call 五件套：X-06 账本面（run_id/permission/idempotency/result/latency；调用级 cost 缺口=FIX-336 复验披露，已由 335-A/wt699 收口主通道）。
  - trace 脊柱：O-02＋FIX-491 审计链修复；**运行级 trace 重建证据缺一口**——`scripts/devtools/trace_timeline.py` 亲证在库，跑真 GJ 即补（低成本项）。
  - 进程韧性：FIX-530 已修（P1 清零）；残差 FIX-542 P2 OPEN（网关守护第二例＋CWD 相对路径，ops 家族合并处置）——随注记。
- **证据链接**：同上。

### Gate V3-7 — Experience Quality（双口径；口径B 段按任务书留空）

- **草案裁决（口径A：API 级＋headless 渲染器/桌面集成通道）：PASS 候选（预填）**。
  - 核心旅程 A/B=0：Q-03 核心 13 屏 A/B=0、long-tail 85 屏 A=0（107 屏真渲染逐屏程序化探针；[WT401-Q03-VISUAL/rubric_scores.md](../WT401-Q03-VISUAL/rubric_scores.md)；**渲染形态限定=flutter_tester 390×844@2x 单档，引用时不得写成「Android 端已渲染验证」**——memo-4 §4 边界注①）。
  - 核心金旅程语义面：Q-02 首轮 20 GJ 真栈真 LLM 13 PASS/6 FAIL/1 RESTRICTED（GJ19 remote 如实 RESTRICTED）＋FIX-53/54/55/56 修复链＋WT400 局部复验（[WT400-F53 summary.json](../WT400-FIX53-REVERIFY/summary.json)：6 GJ 3 PASS、GJ04/GJ09 翻 PASS、GJ08 轮间波动 5/6 在档）；**修后无全 20 GJ 重跑（预裁⑤，§2-拍板3）**。
  - 九类状态完整：U 线 L2 双审 APPROVE（U-06 九态、U-07/U-08 面）；U-09 headless 契约 C1-C7 全绿＋C7 几何近似＋静态审计补偿（web VM 不可翻转的如实披露）。
  - macOS 真应用级：J-02 6/6（真窗口 desktop 集成通道，三端中唯一「真应用」级证据）。
  - 视觉回归基线：**U-09 matrix 设施为就绪清单非已建基线（FIX-376/395 换锚链在案）——DoD「视觉回归有基线截图与 diff」条款在口径A 内只能记 PARTIAL 注记，不随 PASS 计**。
- **草案裁决（口径B：Android/Web/macOS 真机/实机段）：＿＿＿＿（留空，待 O-01——按任务书指令本段不预填）**。
  - 精确归因注记（如实拆分两类解锁条件，避免混写）：**设备段（45 张三端矩阵/真机 FPS/TalkBack·VoiceOver·NVDA 走查/文字级权威批）阻塞原因是设备与浏览器权限（V3-FIX-511＋H-009 十子项），与公网部署无关，O-01 部署后仍不可补——只能采集解锁或走 H-009-7 明文豁免记账通道**；**远程段（GJ19 remote fresh-device/Q-02 D 段/V3-9 远程验证）阻塞原因是 O-01 凭据（H-002），TCC 已解锁 09-28、AK 轮转在途（v0.9 §3），部署后即可补**。
  - 可证伪解除判据（引用 memo-4 §4-3）：H-009 批次采集完成＋`visual_baseline.py manifest/verify/diff` 链跑通＋DIFF_REPORT 核心行无新增 A/B → 口径B 翻 PASS 候选；或 fleet owner 显式豁免记账 → 口径B 维持 BLOCKED 标注但 FINAL 不再被其阻塞。禁止形态：无豁免记账而标 NOT_RUN 或 PASS。
- **证据链接**：[U-09/REPORT.md](../U-09/REPORT.md)、[HUMAN_INBOX](../../v3/08_operations/HUMAN_INBOX.md) H-009/H-002、[WT783-HUMANINBOX/notes.md](../WT783-HUMANINBOX/notes.md)。

### Gate V3-8 — Performance & Cost

- **草案裁决：FAIL（条款级：L0 一项）→ 派V4；随草案同批产出 SLO 修订决议 R1（L2 项原口径 FAIL 事实保留、按 R1 判 PASS）；tier 账本判「存在但有计量盲区」**（采 memo-3 §5 A+B 复合分治为草案基线，随 §2-拍板4）。
- **七条款逐项草案裁决（实测三轮同构口径：wt372 修前/WT406/wt801 修后，harness `_pct` 线性插值，wt803 全量复算逐数吻合）**：
  | # | 条款 | 草案裁决 | 实测（wt801 终测 n=26/层） | 判据 |
  |---|---|---|---|---|
  | 1 | 本地确定性 p95≤300ms | 口径外参考注记（不本轮修订） | 未入 bench 操作化；旁证：网关纯透传 0.02-0.35s、ContextPackBuilder p50 7ms/1000 行 | 引 WT406 §3＋wt801 summary |
  | 2 | L0 no-model p95≤500ms | **FAIL（终判，不修订）→ 派V4** | **1781ms**（p50 1.08s；四轮同带 2.03/1.88/1.78s） | R2：同 harness n≥26 下 L0 TTFT p95≤500ms；定性=功能缺位（TRIVIAL 不跳过生成链），非环境非口径（memo-3 §3.1） |
  | 3/4 | L1 p50≤2.5s / p95≤5s | **PASS / PASS** | 1.656s / 2.596s | facts.json slo_results 同源 |
  | 5 | L2 阶段反馈≤500ms | **PASS（修后翻转）** | **42ms**（修前 4282ms） | 同上 |
  | 6 | L2 最终 p95≤15s | **原口径 FAIL 事实保留＋修订口径 R1 下 PASS** | **65.4s**（较修前 49.5s 上行） | **R1=L2 deep 档 total p95 ≤75s**（65.356×1.15）；重校准触发=provider 价表/主力模型切换或路由 tier 策略变更；**硬伴随门不随 R1 放宽：L2 阶段反馈≤500ms（现 42ms）＋UI 隐藏调用冻结>2s=0 条（现 ack max 400ms）**；修订依据=tier 塌缩修复时间线＋`qwen3_8_max` TTFT p50 64.91s＋L0/L1 同向改善排除系统性退化＋「叠加态对照非单变量归因」边界（wt801 report §5/§9）；已获 wt803 APPROVE-closure 背书＋轮#307 销账「深档 trade-off 入 V4 输入」落账 |
  | 7 | L3 ACK≤1s | **PASS（修后翻转）** | **0.054s**（修前 7.03s） | 同上 |
  | — | UI 隐藏调用冻结>2s | **PASS（判据 R4）** | intake ack 104/104 ≤500ms（max 400ms）＋keyless 24/24 ≤55.6ms＋J-02 F5 6/6 | R4：新会话首事件 p95≤500ms 且无>2s 无反馈窗 |
  | — | tier 账本 | **存在但有计量盲区（注记 FAIL 倾向，不阻塞 gate）** | 账本存在（fast68/plus12/max5/standard1 分布＋lane token/cost/TTFT/quality 表）；**盲区：7/104=6.7% 多代理流计量错挂计 $0（L3-06/08/15/18/21/23/26 同 qid 修前修后持续）** | R3：错挂行占比≤5% 为可信阈值，现 6.7% 超标——FIX-545 P2 OPEN 承接（台账 L417，wt803 C1 义务已落账） |
- **FINAL 汇总口径（待拍板4b）**：建议 gate 级判定按条款计数如实呈现——即便 R1 采纳使 L2 翻 PASS，**V3-8 仍带 L0 一项 FAIL 分量，gate 级=FAIL**；改善项（L3-ACK/L2 阶段反馈/首帧 45.1× 中位改善）如实入册。
- **证据链接**：[WT801-E08FINAL/report.md](../WT801-E08FINAL/report.md) §4/§5、[facts.json](../WT801-E08FINAL/facts.json)、[dynamic_issues.json](../WT801-E08FINAL/dynamic_issues.json)、[WT803-E08REV/receipt.md](../WT803-E08REV/receipt.md) §3.2/§4、[WT406-Q06-PERF/REPORT.md](../WT406-Q06-PERF/REPORT.md) §3、[WT372-E08-BENCH](../WT372-E08-BENCH)（修前基线）。

### Gate V3-9 — Commercial Launch Engineering

- **草案裁决：机制/本地面 PASS-with-notes；远程部署段 BLOCKED（待 O-01，H-002）**。
- **条款级草案裁决**：
  - 解耦（flame/gameification 与 entitlement）：O-04 双侧判官——PASS。
  - 观测面（quota/成本/降级/kill switch/rollback 可观测）：O-06 `backend/app/api/internal/ops_release.py`（亲证存在：`GET /release-manifest` model/config/migration 清单＋release 五旗冻结键集＋64 能力快照）＋O-07 预算/背压/超预算 UX——PASS（机制面）。
  - 导出/删除/Memory 控制：data_export/memory export/ai-usage export 端点在库＋M-07 删除级联红→绿——PASS（机制面）。
  - backup/restore 演练：[WT773-O05](../WT773-O05/notes.md) 一次性容器栈演练——恢复后 GJ03 11/11、run query/transitions 通过、无已删 memory 复活（INV-5/7＋墓碑复活负证被红测抓住）；**GJ08 4/6 如实披露**（两个 real_llm 步 HTTP 200 但空文本=演练环境无 LLM_API_KEY demo mode，不伪造）。脚本残差：FIX-505 P2 OPEN（redis-stack 持久化错位）、FIX-532 P3 OPEN（残余四项，①②已修@`d434dcd0`）——随注记。
  - HTTPS 远程可部署／移动/Web 远端 endpoint／密钥只在服务端：**整段 BLOCKED——O-01 未执行（H-002；TCC 已解锁 09-28、RAM 会话在博仁 profile、AK 轮转在途，截至 v0.9 凭据未产出）**。工程准备面：compose.prod＋deploy 六脚本在库（v0.9 §3「工程面准备度其实很高」原样引用）。
  - RC 一键 smoke＋rollback runbook：**仅在本地行使一次**（ops_rollback_smoke 真栈面本机；staging 级从未发生——v0.9 §4 三层分开看原样引用）；RUNBOOK_DEMO.md 与 RUNBOOK_LLM_HEALTH_RESET.md 先例在库。远程行使随 O-01。
  - release-manifest git SHA 缺口：按 runbook §4.3 选 (b) 带外记录集成 SHA＋manifest 注记（正式执行第 1 步执行；(a) build-time 注入属 O-01 部署面）。
- **证据链接**：同上＋[WT788-POSTGATE/runbook.md](../WT788-POSTGATE/runbook.md) §4.3。

### Gate V3-10 — North Star Measurement

- **草案裁决：PASS-with-notes（本地演示形态口径）**。
- **可证伪判据与证据**：
  - 定义→实现全链在库（亲证存在）：`backend/app/core/north_star_wvpl.py`（词表判据，排除 chat/send/task-click 当闭环——DoD 禁令的代码化）＋`cost_wvpl_metrics.py`＋cost_wvpl_worker（loops=0 不伪造）。
  - 七日闭环实证：JOURNEY ns001 **day7 终门 PASS（轮#289 08:19，M1d6-M4d6 全 200，七日 7/7 收官）**；升栈 0-7 步全绿为基座（轮#288）。
  - **证据收编状态（如实写断）**：全证据在 `/tmp/ns001_journey_out/evidence/steps/`＋`/tmp/day7_gate_run.log`＋备份 `/Users/brsama/code/GitHub/Sparkle-sysrev/.journey_ns001_state_backup.json`——**本会话亲证三处均在盘但均非库内**；收编入库是 FINAL 前必做项（/tmp 易失），随 §3 checklist。
  - 报告口径注记：生产分母=ns001 单用户七日；「active users 分母/WVPL users/loops/user/outcome 类型/H-A-H」六伴生指标中分母面在无公网部署下只有演示语义——如实标注，不冒充统计显著口径。
- **证据链接**：fleet state 轮#288/#289（`v3/.sparkle_v3_fleet_state.json` 本 worktree 亲证原文）＋上述代码路径。

---

## 2. 待主会话拍板清单（按影响排序；每项给倾向＋理由）

| # | 拍板项 | 选项 | **本草案倾向＋理由** |
|---|---|---|---|
| 1 | **W12-01：B-01Δ 入册缺口**（§1.V3-0） | a. 派机械合并小卡（改 F20/F26 两行＋重建 portfolio.json）后翻 PASS-with-notes；b. 接受现状＋在 DoD 决议注加「CSV 两行待同步」显式矛盾注记 | **倾向 a**：修复是确定性数据合并（DELTA CSV 就是 diff 本体），半小时级；真源矛盾留在唯一真源里会被任何独立复核（含双审）当场击穿，b 方案等于让 V3-0 带着自相矛盾进双审。连带：FIX-533 行加注/重开走协调方渠道。**本草案分支不代改权威矩阵**（真源变更应走裁决渠道，非报告卡）。 |
| 2 | **S4 why-now 口径**（预裁②尾） | A. 输出=intervention/proposal 输出→V3-2 PASS（task 级缺位登记 V4）；B. 输出=ActionPlan/task 级→V3-2 FAIL/BLOCKED | **倾向 A**：①gate 原文「输出必须包含」未锚定 task 级契约；②Aurora 侧 why_now 已在生产信号面（`aurora_core_session.py:59`/`plan_quality_contract.py:211`），用户可感的干预路径不缺该要素；③B 口径会把一个被 X-01 自评为 EXP 级的字段位缺口放大成整 gate FAIL，与 V3-2 其余五子项全 PASS 的证据面不成比例。附带裁决：S2 是否要求 20 场景真模型复验——倾向**不要求**（原文未规定模型口径＋规则层生产模块直跑已可证伪；真模型复验登记 V4 增强项）。 |
| 3 | **修而不复跑三选一**（预裁⑤：Q-02 全 20 GJ／Q-04 六路红队） | 补跑／按锁级判／如实 FAIL(NOT_REMEASURED) | **倾向：Q-04 优先补跑（若有窗口），否则如实 FAIL**——Q-04 是 FINAL 的 FAIL 分量决定项，dashboard 级复测是唯一能让 V3-4 翻面的证据，锁级绿不能替代（判定器对 dashboard 的变异红证恰证明这点）；**Q-02 次优先补跑，否则按「首轮＋逐 FIX 闭账＋WT400 局部复验」链式口径 PASS-with-notes**（GJ08 轮间波动在档如实注记；核心 8 GJ 语义面已由修复链＋局部复验覆盖，全 20 GJ 重跑是增强非缺口）。两卡驱动均在库、约半窗各。 |
| 4 | **SLO 修订决议 R1＋gate 级判定口径**（预裁③） | a. 采纳 R1（L2 deep p95≤75s＋重校准触发＋两条硬伴随门）＋gate 按条款计数；b. 不修订（选项 A）；c. 仅环境注记（选项 C） | **倾向 a**：DoD V3-8 原文「必须重新定真实 SLO」使「不产出修订决议」本身构成未完成 DoD 内嵌义务（选项 A 的悖论）；环境注记无法升级为豁免且会连累 L0 定性可信度（选项 C 风险）；R1 结构可证伪（争议只剩 1.15 余量参数一个）。**R1 文本随 FINAL 报告同批产出，落库走 DoD 决议注渠道（协调方），与预裁①同形态。** |
| 5 | **V3-5 丙口径＋P1 探针**（预裁⑥） | 甲（修复即满足）／乙（先运行级证据）／丙（机制 PASS＋运行级注记＋P1） | **倾向丙**：丙不宣称运行级已验证（与甲的诚实性区别所在），不把零观测误读为修复无效（与乙的口径错误区别所在）；P1 是一条只读 SQL 零成本，正式执行第 1 步顺手执行把注记升级为实测。**本会话无 DB 访问，P1 未执行——如实声明。** |
| 6 | **三端双口径细则**（预裁④） | 采纳 memo-4 三条执行细则（双口径并行不替代／「三端通过」卡按「三端或明确平台适用」解释／解除与豁免二选一可证伪） | **倾向全部采纳**：细则把 BLOCKED 的两类解锁条件（设备=H-009 永需采集；远程=O-01 部署后可补）拆清，避免 FINAL 报告把「等部署」和「等设备」混写。豁免与否是 fleet owner 权（H-009-7 明文通道），本草案只留槽。 |
| 7 | **V3-0 钉时点 vs 重跑** | a. 钉时点注记＋抽查；b. 按 HEAD 重跑 B-01 式审计 | **倾向 a＋W12-01 修复后执行**：本草案已实测 `27bd05e5..HEAD` 95 commit 中 mobile/lib 仅 6 文件（FIX-539/540/tokens 族）、feature 拓扑零漂移——钉时点的证据成本已付；全量重跑（约半窗）在此漂移面上信息增量极低。 |
| 8 | **FIX-545 计量盲区阈值 R3** | 采纳 5% 可信阈值＋harness 补 `no_generation_model`-with-tokens 检出 | **倾向采纳**：阈值可证伪（现 6.7% 超标=注记 FAIL 倾向）；harness 补检出是 wt803 §6 不阻塞建议，防同类盲区逃过未来 bench。**对 V3-8 的影响边界：只影响条款7 注记形态与成本口径可信度，不翻任何条款 PASS/FAIL——已在 §1.V3-8 表内落位。** |

---

## 3. FINAL 草案形态与双审条件

- **按骨架 §2.4 判定规则的草案汇总**：PASS=V3-1、V3-3；PASS-with-notes=V3-2（条件 S4-A）、V3-5（条件丙）、V3-6、V3-10、V3-9 机制面（BLOCKED 分量单列）、V3-7 口径A（口径B 分量单列留空）；**FAIL=V3-4（NOT_REMEASURED）、V3-8（L0 条款）、V3-0（W12-01，可机械翻案）**。
- **FINAL_V3 草案形态 = FAIL（诚实分量：V3-4＋V3-8/L0；V3-0 视拍板1 翻案）＋BLOCKED 分量（V3-7 口径B／V3-9 远程段／O-01／Q-07）**——Q 线先例：诚实 FAIL 合法且优于假 PASS。若拍板3 选补跑且复测翻面、拍板1 修复入册，FINAL 可收敛为「FAIL（仅 V3-8/L0 条款分量）＋BLOCKED 分量」；V3-8 是否以「条款级 FAIL」计入 gate FAIL 计数随拍板4 的 gate 级口径一并定。
- **双审前置硬条件（缺一不可）**：①§2 八项拍板落定；②Q-07 状态显式处理（仍 TODO——若窗口不够，Q-08 按 Q-07=NOT_RUN 如实标注，runbook §4.4，不得用历史 X-09 面替代）；③ns001 day7 证据从 /tmp 收编入库；④V3-6 两项低成本补证（trace 重建＋批量统计锚）；⑤release-manifest 抓取＋SHA 带外记录；⑥台账 `ledger_union_merge.py --verify --strict-pipes` 复测；⑦双 reviewer 独立签收（独立=未参与本卡与被审 gate 交付）。
- **本草案未做（如实声明）**：P1 SQL 探针（无 DB 访问）；f507 双套重跑（引用 wt797/wt806 记录）；Q-02/Q-04 补跑（属拍板3 裁量）；CI 31/32 的 gh 实核（协调分支口径引述）；权威矩阵修复（属拍板1 裁量，本卡不代改真源）；未 push；未动 tasks.json/台账/DoD。
