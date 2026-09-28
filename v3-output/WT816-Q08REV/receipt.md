# WT816-Q08REV/receipt.md —— Q-08 终验 11-gate 裁决草案独立一审 receipt（wt816）

> Reviewer: wt816（独立一审会话，未参与 wt812 草案任何工作）｜ 2026-09-28
> 审查对象：[WT812-Q08DRAFT/FINAL_V3_GATE_REPORT_DRAFT.md](../WT812-Q08DRAFT/FINAL_V3_GATE_REPORT_DRAFT.md)（草案基线 main@`5c288841`）
> 本审查时点：main@`35f0d62f`（轮#317），worktree `agent/wt816/q08rev`；全程只读核验＋本 receipt 产出，未改任何被审 artifact，未 push。
> 方法：逐 gate 抽查证据链接（覆盖全部 3 个 FAIL 与全部 PASS-with-notes，9/11 gate 实核，超 50% 抽查率）；CI 结论经 `gh run list/view` 独立实核；台账/矩阵/portfolio 用机器口径复算；git 祖先与 diff 实测。

---

## 0. 总裁决

**APPROVE-with-conditions。** 草案的 11 个 gate 裁决、三个 FAIL 的定性、BLOCKED 的双口径归因、8 项拍板倾向，经独立抽查**全部成立**；诚实纪律属实（断裂处如实写断、未亲证处逐条标注）。发现 **1 处实质性 CHALLENGED**（V3-4 引用的 A-08 消融数字与方向同其所引 artifact 相反，须修后方可入 FINAL）、3 处轻微瑕疵、2 处遗漏补强。V3-0 的可翻案缺口（W12-01）在草案时点后被 wt814 以 FIX-555 机械合并修复入主干（`cc90eb2f`/`54d74f09`），本审查已逐格复核修复态——草案的翻案路径判断被后续事实验证。

---

## 1. 逐 gate 抽查结论

| Gate | 草案裁决 | 一审结论 | 关键核验证据（本会话亲证） |
|---|---|---|---|
| V3-0 | FAIL（W12-01 可翻案） | **CONFIRMED（且已被后续修复翻转）** | `git show cf8d6c16` diff 实证：MODULE_MATRIX.csv 仅删 F24＋追加 F43/F44，F20/F26 原样 HIDDEN@a2d8a10c；基线 portfolio.json `total=42` vs `feature_count=43` 自相矛盾、F24 在册、F43/F44 缺席——W12-01 全链属实。**当前 HEAD 复核：F20/F26=CONTEXTUAL@27bd05e5、portfolio modules=43 与 CSV 零冲突、DoD 加勘误注记（FIX-555/wt814）**——修复态逐格吻合。钉时点漂移主张独立复现：`27bd05e5..5c288841` 实测 95 commit、mobile/lib 恰 6 文件 151+/50-、`git ls-tree` features 拓扑差集为空 |
| V3-1 | PASS-with-notes | **CONFIRMED** | WT802 REPORT：run_id `j02retest_macos_20260928_101701_wt802`、6/6 秒表入预算（102,170/98,767/100,735/101,730/99,754/99,948ms）、FirstActionCard 6/6、纯 UI 注册 6/6、51,347ms 迭代跑佐证、R9 后端 6/6 tasks=1 而 UI 确认面缺口如实、A1b 种子隔离 guest_03a6e396305e memory_goals=0 实证。注记项（R9/541/upgrade 面/真机段）与 REPORT 一致 |
| V3-2 | PASS-with-notes（条件 S4-A） | **CONFIRMED** | fixture 实读 scenarios=20＋hard_family=6；`aurora_core_session.py:59` why_now 字段、`plan_quality_contract.py:211` why_now 组装、`action_plan.py:204` 伪步骤不合法＋封闭词表、`aurora_decision.py` inert 域与 clarify 必带问句，全部在码；X-01 REPORT L171 自证 why_now 系「EXP-级未来项（未做）」；DoD 原文「输出必须包含…为什么现在做…」**未锚定 task 级契约**——口径A 读法成立 |
| V3-3 | PASS | **CONFIRMED** | X-10 REPORT：allocation 100%（28/28）、high-risk auto=0、false success=0、`real_llm_calls=0` 判定器强制断言＋results.json 891 条 checks 留痕，逐项在文 |
| V3-4 | FAIL（NOT_REMEASURED） | **裁决 CONFIRMED／一处证据句 CHALLENGED（见 §3-C1）** | dashboard.json 实读：`git_sha=46762b31`、100 records、20 blind pairs、fleet precision=0.0（target 0.95）、valid_uses=0/10、gates 全 false、acceptance=FAIL、overpersonalization_rate=0.4167——全吻合。dashboard 生成于 09-25T16:49，FIX-67/68/69/70 修于 09-26（`7244efb2`/`12ce081b`）——**修后确无 dashboard 级复测，NOT_REMEASURED 成立**；`test_q04_redteam_final.py` 在库亲证。锁级不能替代 dashboard 级的论证线成立 |
| V3-5 | PASS-with-notes（丙） | **CONFIRMED** | `git merge-base --is-ancestor`：8e503cd8/cdc547be/27bd05e5 均 HEAD 祖先；f507 双套测试实际路径=`backend/tests/services/test_f507_readface_dataflow.py`+`test_f507_lifecycle_wiring.py`（草案对 memo-6 的路径勘误正确）；wt801 notes 头部 09:55:27 滚启＋栈=`cdc547be` 亲证；D-08 REPORT/校准回退链锚在位 |
| V3-6 | PASS-with-notes | **CONFIRMED** | `test_x09_failure_recovery.py`/`test_failure_semantics.py` 在库；**v3-output/X-09 独立产物目录确不存在**——草案「100 run≥99 terminal 未定位到证据」的写断如实；`trace_timeline.py` 在库；FIX-530 FIXED（v0.9 P1 清零）、FIX-542 OPEN（台账亲证）注记属实 |
| V3-7 | 口径A PASS 候选／口径B 留空 | **CONFIRMED** | Q-03 rubric「核心旅程 A/B 合计=0」原文在档；U-09 REPORT 在库；HUMAN_INBOX H-009（十子项，H-009-7 明文「fleet owner 显式裁决豁免并记账」通道）与 H-002（OPEN，TCC 已解锁/AK 轮转在途/凭据未产出）锚点逐条核实——设备段/远程段两类解锁条件的拆分与收件箱原文一致 |
| V3-8 | FAIL（L0 条款）→派V4＋R1 | **CONFIRMED** | facts.json 实读全部吻合：L0 ttft_p95=1.7812s（p50 1.0767s）、L1 1.6565/2.5962s、L2 阶段反馈 42ms（修前 4282ms）、L2 total_p95=65.3564s（修前 49.5s 上行）、L3 ACK 0.054s（修前 7.03s）；slo_results 六判=2 FAIL/4 PASS 同构；WT406 报告 L0 p95=1879ms 补齐「四轮同带 2.03/1.88/1.78」中值；R1 算术 65.3564×1.15=75.16≈75s 复算成立；7 错挂 qid（L3-06/08/15/18/21/23/26）与 FIX-545 行（台账 L417 OPEN）吻合；fast68/plus12/max5/standard1 与 models 分布吻合；**DoD V3-8 原文「必须重新定真实 SLO」在案——拍板4 倾向 a 的前提成立** |
| V3-9 | 机制面 PASS-with-notes／远程 BLOCKED | **CONFIRMED** | `ops_release.py` GET /release-manifest 在码；WT773-O05 notes、WT788 runbook §4.3（build 注入 or 带外记录两选项）在库；v0.9 §3「三层分开看」/TCC 已解锁/RAM 会话博仁 profile/AK 轮转在途/凭据未产出逐句核实；工程面 compose.prod＋deploy 脚本在库 |
| V3-10 | PASS-with-notes（本地演示形态） | **CONFIRMED** | `north_star_wvpl.py`/`cost_wvpl_metrics.py` 在库；fleet state 亲证：轮#288「day7 升栈 0-7 步全绿 07:35」、轮#289「day7 终门 PASS 7/7 收官 08:19＋备份 Sparkle-sysrev/.journey_ns001_state_backup.json」；证据在 /tmp 与 sysrev 备份、非库内——「收编入库为 FINAL 前必做」的写断属实 |

抽查覆盖：9/11 gate 实核（V3-6/V3-7 为部分实核），覆盖全部 FAIL 与 PASS-with-notes，超 50% 抽查率要求。所有被引文件路径**零死链**。

---

## 2. 三个 FAIL 裁决深查

### 2.1 V3-0（W12-01）——证据链闭合，翻案路径已被事实验证
- 断裂点全部亲证（§1 表）；草案将其定性为「唯一真源自相矛盾」而非五态结构缺失，在 Truth gate 语境下成立。
- **反证检查**：未发现被草案弱化的反证。wt790 DELTA CSV 逐字含 F20/F26 改写行（本会话比对 CSV 现行文与 DELTA 行一致）；FIX-533 闭账注记的 artifact 层不成立判断属实（L405 行仍载「portfolio.json 同步」，见 §5-O2）。
- **后续发展（草案时点后）**：wt814 FIX-555 机械合并已入主干（`cc90eb2f`，FIXED@`54d74f09`），修复态经本会话 20 格逐项复核（判据①②翻转、43 行状态零冲突、DoD 勘误注记在位）。**草案「FAIL（可翻案，修复=机械合并）」的裁决与翻案路径双双被后续事实确认。**

### 2.2 V3-4（NOT_REMEASURED）——裁决成立；但「双独立 eval 同向证据」句须修
- 裁决的承重证据（dashboard 修前现值＋修后无全量重跑＋锁级不可替代）全部亲证闭合，FAIL 判定**不受**下述 CHALLENGED 影响。
- **CHALLENGED（C1，实质性）**：草案称「A-08 消融 journey 面 no_memory 臂 0.55 反超 full 臂 0.45」——**与所引 artifact 相反**。WT393 summary.json 实读：stuck_accuracy full=0.65 / no_memory=0.55（full 高 0.10）；utility full=-16.2 / no_memory=-21.4（full 高 5.2）；全 11 项 comparison 中 full 占优居多。WT393 REPORT.md 原文结论：「vs 无记忆（方向达成，含反例）：记忆面净收益 +0.10 accuracy、+5.2 效用、uncertain 行动 −7」。「0.55/0.45」两数在本目录与其余备忘中均不存在（全仓检索无果）。artifact 中真实存在的反证较窄：no_memory 收敛更快（1.09 vs 1.38 会话）、chat 面匹配微高（0.6304 vs 0.619）、no_experience 与 full 同为 0.65（experience 面增益存疑）、p07 反例。**「双独立 eval 同向证据」的表述必须改为如上如实口径，否则 FINAL 的「诚实分量」叙事自身带伤。**（修法建议见 §6 条件 1）

### 2.3 V3-8（L0）——条款级 FAIL 成立，定性正确
- L0 四轮同带（2033/1879/1781ms）横跨修前/WT406/wt801 三源亲证；「功能缺位（TRIVIAL 不跳过生成链）非环境非口径」的定性与 wt801 report E08-ISS-L0-TTFT 行原文一致；DoD 无 L0 重校准出口（500ms 是「候选目标」中唯一无 provider 侧不可满足论证的条款）。条款级 FAIL→派V4、不随 R1 放宽，成立。
- R1 修订：DoD 原文内嵌「必须重新定真实 SLO」义务（原文亲证），R1 结构（75.16s 阈值＋重校准触发＋两条硬伴随门，伴随门现值 42ms/400ms 亲证在带）可证伪，非改口径粉饰。L2「原口径 FAIL 事实保留＋R1 下 PASS」的双账处理诚实。

---

## 3. CHALLENGED 与瑕疵清单

- **C1（实质，须修后方可入 FINAL）**：V3-4 的 A-08 证据句数字与方向同 artifact 相反（详见 §2.2）。不影响 V3-4 FAIL 裁决本身，影响 FINAL 报告的证据表述诚实性。
- **C2（轻微）**：§0「台账 47 OPEN（P2×6 含 547）」按行尾 `^OPEN` 朴素口径把 **FIX-547 的陈旧 OPEN 重复行**（L427）计入，而同 ID 的 FIXED@`3bf967ac` 行（L419）在草案基线已在册——去重后实际 OPEN 缺口=46、P2 OPEN=5。该重复行至今（HEAD `35f0d62f`）未清，语义上疑似「测试侧已修／产品侧建议独立卡」的双轨残留，但同 ID 双行必然污染机器口径与 FINAL 的台账复测（§3-⑥）。
- **C3（轻微，笔误）**：V3-1 秒表区间「99,767-102,170ms」下界应为 98,767（REPORT 实值 min=98,767）；V3-0 可证伪判据②引用 `portfolio.json['features']`，实际键名为 `modules`（判据照抄会 KeyError，实质结论不受影响）。

---

## 4. 八项拍板倾向独立意见

| # | 草案倾向 | wt816 意见 | 理由 |
|---|---|---|---|
| 1 W12-01 | a（派机械合并小卡） | **同意（已被执行验证）** | wt814 已按 a 路径修复入主干，逐格复核通过——倾向的事后正确性已定。残留条件：FIX-533 行闭账注记加勘误注（草案已提，须落 FINAL checklist，见 §5-O2） |
| 2 S4 口径 | A（输出=intervention/proposal 输出） | **同意 A** | 亲证 DoD 原文未锚 task 级；why_now 在生产信号面在码（`aurora_core_session.py:59`/`plan_quality_contract.py:211`）；X-01 自证该缺位为 EXP-级未来项。B 会以字段位缺口翻整 gate，与六子项证据面不成比例。附带裁决（S2 不强制 20 场景真模型复验，登记 V4 增强）：**同意**——原文未规定模型口径，规则层对生产模块直跑可证伪 |
| 3 预裁⑤ | Q-04 优先补跑否则如实 FAIL；Q-02 次优先否则链式口径 PASS-with-notes | **同意** | Q-04 是 FINAL FAIL 分量决定项且唯一翻面证据=dashboard 级复测（本审查确认现存 dashboard 修前于修复）；Q-02 链式口径（首轮 13P/6F/1R＋逐 FIX 闭账＋WT400 6GJ 3P、GJ04/09 翻 P、GJ08 波动在档——全部亲证）覆盖核心 8 GJ 语义面，全 20 重跑属增强。两分支均可证伪、诚实 |
| 4 R1＋gate 级口径 | a（采纳 R1＋条款计数） | **同意** | 「不产出修订决议」本身违反 DoD 内嵌义务（原文亲证）；R1 可证伪且硬伴随门不放水；gate 级按条款计数（仍带 L0 FAIL 分量）是诚实呈现 |
| 5 V3-5 丙＋P1 | 丙 | **同意** | 丙与甲的诚实性区分、与乙的口径区分均成立；P1 只读 SQL 零成本，草案如实声明未执行 |
| 6 三端细则 | 全部采纳 memo-4 | **同意** | 两类解锁条件拆分与 HUMAN_INBOX 原文逐条吻合（H-009 设备段／H-002 远程段），防「等部署」「等设备」混写 |
| 7 钉时点 vs 重跑 | a＋W12-01 修复后执行 | **同意 a** | 漂移面已由本审查独立复现（95 commit/6 文件/拓扑零漂移）；全量重跑在此窗口信息增量极低。附加条件：钉时点注记须显式记录 SHA 窗口（`27bd05e5`..FINAL 时点 HEAD）与 6 文件清单，且 wt814 改写后 source_sha 已指向 `27bd05e5`——注记应说明矩阵审计基准与漂移窗口的关系 |
| 8 R3 5% 阈值 | 采纳 | **同意** | 阈值可证伪（现 6.7%=7/104 亲证超标）；对 V3-8 的影响边界（只动条款7 注记形态）与 §1.V3-8 表内落位一致 |

---

## 5. 遗漏补强（草案未纳入的证据面）

- **O1**：FIX-547 同 ID 双行（OPEN L427＋FIXED L419）未在草案任何位置披露；FINAL 前须去重或显式注记双轨语义，否则 §3-⑥ 台账复测与 §0 机器口径复算都会被它击中（对应 C2）。
- **O2**：FIX-533 行（L405）闭账注记「portfolio.json 同步+b01_delta_merge 决议注」在 artifact 层不成立的勘误，目前只落在 FIX-555 行与 DoD 勘误注——FIX-533 行本体仍载不实闭账文。拍板1 连带项应升级为 FINAL checklist 显式条件。
- **O3（备忘级）**：主 checkout 存在 3 个未提交的 WT401 probe json 脏文件（fleet 轮#30x 已注记「runday7 第 0 步预期内」）——FINAL 引用 WT401 证据时应注明该脏文件状态或先行收编，防 Truth gate 复核歧义。
- **O4（备忘级）**：CI 32 attempt1 红的归因未随草案快照入册（草案时 CI32 在跑；现已 attempt2 绿=#567@`5c288841`，第 7 绿）。FINAL CI 段应补记该 rerun 归因，保持「23/25/27/29r/30/31/32r」全链归因完整。

---

## 6. 条件清单（FINAL 受理前置）

1. **修 C1**：V3-4 的 A-08 证据句改为 artifact 如实口径（full 0.65/-16.2 vs no_memory 0.55/-21.4＋REPORT「净收益为正、含反例」原文＋真实反证面：收敛速度 1.38 vs 1.09、no_experience==full、p07 反例），删除「双独立 eval 同向证据」框定；「个性化净贡献未被证明为正」如保留，须缩定到具体面并注明 A-08 主指标方向相反。
2. **清 C2/O1**：FIX-547 双行去重或加双轨注记；FIX-533 行加勘误注（O2）；完成后跑 `ledger_union_merge.py --verify --strict-pipes` 并把复核口径改为「行尾状态格计数＋同 ID 唯一性」双检。
3. **修 C3**：FINAL 文本更正 98,767 下界与 `modules` 键名。
4. **补 O3/O4**：WT401 脏文件状态注记；CI 32 rerun 归因入 CI 段。
5. 草案 §3 双审前置硬条件 ①-⑦ 维持不变，全部继续有效（其中 ③ ns001 收编与 ⑥ 台账复测因上文 O1/O2 增重）。
6. 八项拍板按 §4 意见落定后，V3-0 翻 PASS-with-notes（钉时点注记按条件 7a 附 SHA 窗口）。

---

## 7. 附：CI 独立实核记录（gh，2026-09-28）

fleet「第N次」口径 → gh run 映射（经 fleet state 内嵌 run id 钉定）：CI25=`36350830485`(#559) success；CI27=`36365191735`(#562) success；CI28=`36369273304`(#563) failure（双归因在案）；CI29=`36372459978`(#564) attempt2 success（attempt1 红=FIX-547，与台账 job 108772804580 记载一致）；CI30=`36378341486`(#565) success；CI31=`36383406020`(#566) success；CI32=`36389163440`(#567) attempt2 success（sha=`5c288841`）；CI33=`36397049467`(#568) 在跑（sha=`8be9831c`）。草案「五绿＋31 引述＋32 在跑」与 gh 实况一致；草案时点的 31/32 引述现均已落绿，第 7 绿成立。wt807 FIX-547 修复已入主干（FIXED@`3bf967ac`）。

—— wt816 一审完。本 receipt 仅表独立审查结论，不代行任何裁决权。
