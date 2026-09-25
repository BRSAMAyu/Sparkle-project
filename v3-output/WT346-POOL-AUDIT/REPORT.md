# WT346 · V3 卡池双证盘点与排产提案（leader 排产地基）

- 工号：wt346 ｜ 日期：2026-09-25 ｜ 槽型：LIGHT（只读分析+报告）
- 分支：`wt346-pool-audit`（base = main@b280d38a）｜ 主仓只读，一切改动在本 worktree
- 交付物：本报告 + `changes.patch`

## 0. 方法与证据口径

**三证据源**（与 HANDOVER-20260925.md §22 双证口径一致，加台账为第三源）：
1. `git log main` 全量 701 提交，按卡号 grep（词边界）；
2. `v3-output/` 268 个交付目录；
3. 台账 `v3/.sparkle_v3_fleet_state.json`（done 数组 69 条 = 63 张编号卡 + B-02X + 4×V3-FIX；notes 117KB；blocked 空；`active=["B-02"]` 已过期）+ `v3/HANDOVER-20260925.md`（§18 合入全记录、§13 候补池、§22 判卡方法）。

**关键修正**：done 数组滞后于实际合并——11 张已合并卡未收账（A-06/G-03/G-04/J-02/J-03/J-05/J-07/J-08/S-03/S-04/U-05，逐卡提交 sha 见判定表）。`tasks.json` 的 status 字段 107 张全 TODO（卡面已声明不可信），本审计不采用其状态、仅采用其 deps/Resource 字段。

**判定规则**：DONE = 代码已合并 main 且 ≥2 证据源；PARTIAL = 有交付但卡面验收明显未闭；BLOCKED = 缺上游/凭据/设备；READY = 声明 deps 全部 done、可直接派发。结果：PARTIAL=0、UNKNOWN=0（理由见 §6 诚实边界）。

## 1. 总判定

**107 = DONE 74（69.2%）+ READY 12 + BLOCKED 21 + PARTIAL 0 + UNKNOWN 0**

- 台账账面 63 张 → 实际 74 张，差的 11 张就是「合并后不回写」流程债的直接量化证据。
- BLOCKED 21 张中：20 张是纯上游依赖（追根全部汇入 READY 12 张或 O-01 凭据），**1 张是外部条件阻塞：O-01 公网部署卡用户凭据三选一**（HANDOVER §2-7，已问多次未答）。
- 12 张 READY 全部 HEAVY（S-01 可拆两段），卡池已进入「重卡尾巴 + 红队链」阶段，与 HANDOVER §13「产品线余卡已尽」的判断一致并精确化。

## 2. 107 卡全量判定表

|卡号|判定|证据指针|
|---|---|---|
|A-01|DONE|台账done + git×1 + v3-output/A-01|
|A-02|DONE|台账done + git×1 + v3-output/A-02|
|A-03|DONE|台账done + git×1|
|A-04|DONE|台账done + git×1|
|A-05|DONE|台账done + git×1 + v3-output/A-05|
|A-06|DONE|合并 d8a89bec (wt311) + git×1 + v3-output/WT311-A06|
|A-07|BLOCKED|缺上游 U-02（未done，git 0 提及、无 v3-output）|
|A-08|BLOCKED|缺上游 A-07（未done，git 0 提及、无 v3-output）|
|B-01|DONE|台账done + git×3 + v3-output/B-01|
|B-02|DONE|台账done + git×6 + v3-output/B-02X|
|B-03|DONE|台账done + git×3 + v3-output/B-03|
|B-04|DONE|台账done + 状态提交 fdf8204a「B-04 complete 9/9 verified」+ git×2|
|B-05|DONE|台账done + git×5 + v3-output/B-05|
|B-06|DONE|台账done + git×2 + v3-output/B-06|
|C-01|DONE|台账done + git×6 + v3-output/C-01|
|C-02|DONE|台账done + git×2 + v3-output/C-02|
|C-03|DONE|台账done + git×2 + v3-output/C-03|
|C-04|DONE|台账done + git×2|
|C-05|DONE|台账done + git×2|
|C-06|DONE|台账done + git×1|
|C-07|DONE|台账done + git×1|
|C-08|DONE|台账done + git×2|
|D-01|DONE|台账done + git×2 + v3-output/D-01|
|D-02|DONE|台账done + git×1 + v3-output/D-02|
|D-03|DONE|台账done + git×1 + v3-output/D-03|
|D-04|DONE|台账done + git×1|
|D-05|DONE|台账done + git×1|
|D-06|DONE|台账done + git×1|
|D-07|READY|deps 全done（D-03,D-04,D-05,U-05均双证）；Resource=HEAVY|
|D-08|BLOCKED|缺上游 D-07,A-08（未done，git 0 提及、无 v3-output）|
|E-01|DONE|台账done + git×2 + v3-output/E-01|
|E-02|DONE|台账done + git×4 + v3-output/E-02|
|E-03|READY|deps 全done（E-02,U-04均双证）；Resource=HEAVY|
|E-04|DONE|台账done + git×1|
|E-05|DONE|台账done + git×1 + v3-output/E-05-staging|
|E-06|DONE|台账done + git×2|
|E-07|DONE|台账done + git×1|
|E-08|BLOCKED|缺上游 E-03（未done，git 0 提及、无 v3-output）|
|G-01|DONE|台账done + git×2|
|G-02|DONE|台账done + git×1|
|G-03|DONE|合并 f2fb8c2b (wt305) + git×3 + v3-output/wt305-g03-galaxy-ux|
|G-04|DONE|合并 05155fff (wt314) + git×1 + v3-output/WT314-G04|
|G-05|BLOCKED|缺上游 U-09（未done，git 0 提及、无 v3-output）|
|J-01|READY|deps 全done（B-01,B-03,B-04均双证）；Resource=HEAVY|
|J-02|DONE|合并 cd154f03 (wt282) + 舰队日志 d6e64a8b + git×3（v3-output 目录缺席，早于归档纪律）|
|J-03|DONE|合并 2421a04f (wt306) + git×2 + v3-output/WT306-J03|
|J-04|READY|deps 全done（J-02,J-03,A-03,X-03均双证）；Resource=HEAVY|
|J-05|DONE|合并 73566bb0 (wt302) + git×4 + v3-output/wt302-j05-stuck-recovery|
|J-06|READY|deps 全done（J-05,X-07均双证）；Resource=HEAVY|
|J-07|DONE|合并 7624ec6a (wt303 mobile) + wt313 引擎侧收口 + git×3 + v3-output/wt303-j07-comeback、WT313-COMEBACK|
|J-08|DONE|2b790fea 合流入库 (wt304，HANDOVER §18) + 舰队日志 6fa1bc25 + git×1 + v3-output/wt304-j08-goal-completion|
|M-01|DONE|台账done + git×4 + v3-output/M-01-staging|
|M-02|DONE|台账done + git×3 + v3-output/M-02|
|M-03|DONE|台账done + git×1 + v3-output/M-03|
|M-04|DONE|台账done + git×4 + v3-output/M-04|
|M-05|DONE|台账done + git×2 + v3-output/M-05|
|M-06|DONE|台账done + git×1|
|M-07|DONE|台账done + git×3 + v3-output/M-07|
|M-08|DONE|台账done + git×1|
|M-09|DONE|台账done + git×2|
|M-10|READY|deps 全done（M-08,U-03,M-09均双证）；Resource=HEAVY|
|O-01|BLOCKED|deps B-06 已done；缺公网凭据（AK/IAB/扩展三选一未答，HANDOVER §2-7/§10）；弹药已备 /tmp/sparkle_cloud_secrets|
|O-02|DONE|台账done + git×1|
|O-03|DONE|台账done + git×1|
|O-04|DONE|台账done + git×1|
|O-05|BLOCKED|缺上游 O-01（未done，git 0 提及、无 v3-output）|
|O-06|BLOCKED|缺上游 O-01（未done，git 0 提及、无 v3-output）|
|O-07|DONE|台账done + git×3|
|P-01|DONE|台账done + git×2|
|P-02|DONE|台账done + git×1|
|P-03|READY|deps 全done（P-01,U-05均双证）；Resource=HEAVY|
|P-04|DONE|台账done + git×1|
|P-05|BLOCKED|缺上游 P-03（未done，git 0 提及、无 v3-output）|
|P-06|BLOCKED|缺上游 P-03,A-07（未done，git 0 提及、无 v3-output）|
|Q-01|DONE|台账done + git×1|
|Q-02|BLOCKED|缺上游 U-09,M-10（未done，git 0 提及、无 v3-output）|
|Q-03|BLOCKED|缺上游 U-09,U-10,Q-02（未done，git 0 提及、无 v3-output）|
|Q-04|BLOCKED|缺上游 A-08,D-08（未done，git 0 提及、无 v3-output）|
|Q-05|BLOCKED|缺上游 S-05（未done，git 0 提及、无 v3-output）|
|Q-06|BLOCKED|缺上游 E-08（未done，git 0 提及、无 v3-output）|
|Q-07|BLOCKED|缺上游 O-05,U-06（未done，git 0 提及、无 v3-output）|
|Q-08|BLOCKED|缺上游 Q-02,Q-03,Q-04,Q-05,Q-06,Q-07,D-08,P-05,G-05（未done，git 0 提及、无 v3-output）|
|S-01|READY|deps 全done（B-01,B-03均双证）；Resource=HEAVY|
|S-02|BLOCKED|缺上游 S-01（未done，git 0 提及、无 v3-output）|
|S-03|DONE|合并 41d83f83 (wt307) + git×1 + v3-output/WT307-S03|
|S-04|DONE|合并 c026f0c1 (wt312) + git×1 + v3-output/WT312-S04|
|S-05|BLOCKED|缺上游 S-02（未done，git 0 提及、无 v3-output）|
|U-01|DONE|台账done + git×9|
|U-02|READY|deps 全done（U-01均双证）；Resource=HEAVY|
|U-03|DONE|台账done + git×2 + v3-output/U-03|
|U-04|DONE|台账done + git×1|
|U-05|DONE|合并 cb022dad (wt315) + git×2 + v3-output/WT315-U05|
|U-06|READY|deps 全done（U-04,U-05均双证）；Resource=HEAVY|
|U-07|READY|deps 全done（B-01,U-05均双证）；Resource=HEAVY|
|U-08|READY|deps 全done（U-05均双证）；Resource=HEAVY|
|U-09|BLOCKED|缺上游 U-06,U-08（未done，git 0 提及、无 v3-output）|
|U-10|BLOCKED|缺上游 U-07（未done，git 0 提及、无 v3-output）|
|X-01|DONE|台账done + git×1 + v3-output/X-01|
|X-02|DONE|台账done + git×2 + v3-output/X-02|
|X-03|DONE|台账done + git×1|
|X-04|DONE|台账done + git×1 + v3-output/V3-FIX-04|
|X-05|DONE|台账done + git×3|
|X-06|DONE|台账done + git×2|
|X-07|DONE|台账done + git×3 + v3-output/V3-FIX-07|
|X-08|DONE|台账done + git×1 + v3-output/V3-FIX-08|
|X-09|DONE|台账done + git×1 + v3-output/V3-FIX-09|
|X-10|DONE|台账done + git×1 + v3-output/X-10|


## 3. 下一批 10 张排产队列（READY 12 选 10）

**排序依据**：解锁链杠杆（谁 unlock 红队/RC 链最深）× 用户主次重排（HANDOVER §2-6：A 线产品体验卡占多数）× 在航战区冲突最小化。**本机 HEAVY≤1（§7 内存纪律）→ 实际串行执行**，本队列是 HEAVY 槽空出时的补位顺序；每张卡派发时按 §4 协议配 1 个 LIGHT review 槽。

**在航战区**（冲突提示基准）：云端浏览器（云部署侦察）/ mypy 烧减（后端全画面）/ 质量尾账（测试体系）；另 HANDOVER §10 时代在航 wt326（后端 blocker F-5/6/7：plans/goal/chat_mode）与 wt327（移动端 blocker F-4/8：ChatScreen GlobalKey + cockpit 双 CTA）——若尚未合并，下述 chat/home/plans 触面卡必须排在其后或在合并态做编译验证（§12-8）。

| # | 卡 | 槽型 | 卡面核心 3 行 | 解锁 | 战区冲突提示 |
|---|---|---|---|---|---|
| 1 | **U-02** Calm/Warm 设计语言与低刺激模式 | HEAVY | 验收：普通/低刺激模式核心截图过 contrast/hierarchy rubric；低刺激真实减少动效/挑战元素而非空设置值。Forbidden：不重建既有权威真源。种子：`mobile/lib/core/design`、`features/aurora`、`features/settings` | **A-07→A-08 全线解锁**（用户优先的 A 线单点在此）+ P-06 半边 | 触 core/design 面广而浅；与在航无直接交叠；与 U-06/U-08 建议错峰合并 |
| 2 | **M-10** Memory/Aurora UI 全链集成 | HEAVY | 验收：GJ08/GJ09 三端过；用户无需懂 Memory 内部结构；删除后当前/未来个性化正确变化。Forbidden：不用 mock 冒充真实行为。种子：`mobile/lib/features/memory`、`features/aurora` | **Q-02**（20 Golden Journeys 前置） | 低：memory/aurora 面无在航；M-08/U-03 表面已合并，纯集成 |
| 3 | **U-06** L4 状态完备性注入 | HEAVY | 验收：核心 surfaces state matrix ≥95% 覆盖、所有错误有下一步；>500ms 有 stage feedback；无 terminal spinner。Forbidden：不用 mock/seed 冒充。种子：`mobile/lib/core`、`features` | **U-09**→Q-02/Q-03/G-05 | 中：features 全面 fan-out；错误态面与 wt327（chat/home）可能碰文件——合并态验证+错峰 |
| 4 | **U-08** Accessibility 全链升级 | HEAVY | 验收：GJ01/GJ03/GJ08 核心控件可由辅助技术完成；WCAG AA；不靠颜色传达关键状态。Forbidden：不重建真源。种子：`mobile/lib` | **U-09**（与 U-06 双前置齐） | 中：semantics 广 fan-out；与 U-06 同文件面风险高，两者必须串行合并 |
| 5 | **E-03** 实时 Stage Events 首反馈 | HEAVY | 验收：深路径 500ms 内真实阶段反馈且 stage 与 trace 匹配；不显示 reasoning_content 原文。Forbidden：**不暴露 CoT**。种子：`backend/app/orchestration`、`backend/gateway`、`mobile/lib/features/chat` | **E-08**→Q-06 | 高：引擎+网关+chat 三层——后端面吃 mypy 棘轮义务（mypy 战区），chat 面与 wt327/F-4 潜在重叠；排 wt327 合并后 |
| 6 | **S-01** Community Realtime/Read-model 真相复测 | HEAVY（可拆两段） | 验收：当前状态可重复 report；live 失败不 fallback 假 realtime。Forbidden：不用 mock 冒充；不得静态阅读宣称体验通过。种子：`mobile/lib/features/community`、`backend/gateway/internal/cqrs`、`backend/app/api/v1/community.py` | **S-02→S-05→Q-05**（critical 安全红队门） | 低：wt307/wt312 已合并；两账号 live 需模拟器（HEAVY），可先交付读模审计+report、live 证据 DEFERRED 二段（wt307/312 先例） |
| 7 | **D-07** Evidence-driven Insights 重构 | HEAVY | 验收：每条洞察可点来源、纠错后后续更新；无数据不生成人格结论；Simulator 能理解 ≥3 条 insight。Forbidden：不重建权威真源。种子：`mobile/lib/features/insights`、`features/cognitive`、`backend/app/services/analytics` | **D-08**→Q-04 | 中低：后端 analytics 面带 mypy 义务；移动 insights 面无在航 |
| 8 | **P-03** Proactive Suggestion UX | HEAVY | 验收：重复建议不刷屏、拒绝后 cooldown 生效；离线/过期通知点击有合理恢复。Forbidden：不重建真源。种子：`mobile/lib/features/notification_center`、`features/home` | **P-05、P-06**（Q-08 链） | 中：home 面与 wt327 cockpit 双 CTA 战区相邻——排 wt327 合并后；notification 面无冲突 |
| 9 | **J-04** First Meaningful Action 端到端 | HEAVY | 验收：GJ01 三端；5 Persona action 不模板化；重开存在；提案生成失败诚实处理。Forbidden：不用 mock 冒充。种子：`mobile/lib`、`backend/app/aurora`、`backend/app/services` | 叶卡（无下游），但旗舰 journey 体验 | 高：onboarding/home/chat+后端 aurora/services——与 wt327（chat）、wt326（plans）重叠最大，两者合并后再派；可降 LIGHT 执行+DEFERRED 证据 |
| 10 | **U-07** 长尾 Feature 导航减负 | HEAVY | 验收：五 Tab 不增；CORE journey 无关入口不出现；HIDDEN 不可达；CONTEXTUAL ≥1 自然 journey。Forbidden：不重建真源。种子：`mobile/lib/app`、`features` | **U-10**（LIGHT，文案终审） | 低：与已合并 NAV-SQUAD/PHOTON 改造衔接；无在航冲突 |

**落选 2 张（备胎/11-12 位）**：J-01（First 3 Minutes 实测，纯测量卡、零代码冲突，但无下游解锁且证据需录像=HEAVY）、J-06（Hybrid Flagship Journey，叶卡）。任何 HEAVY 空窗可插入，优先级低于上表。

## 4. 卡池健康度

| 线 | 总卡 | DONE | 剩余 READY | 剩余 BLOCKED | 剩余槽当量* |
|---|---|---|---|---|---|
| A | 8 | 6 | 0 | 2（A-07←U-02、A-08←A-07） | 4.0 |
| B | 6 | 6 | 0 | 0 | 0 |
| C | 8 | 8 | 0 | 0 | 0 |
| D | 8 | 6 | 1（D-07） | 1（D-08） | 4.0 |
| E | 8 | 6 | 1（E-03） | 1（E-08） | 4.0 |
| G | 5 | 4 | 0 | 1（G-05←U-09） | 2.0 |
| J | 8 | 5 | 3（J-01/J-04/J-06） | 0 | 6.0 |
| M | 10 | 9 | 1（M-10） | 0 | 2.0 |
| O | 7 | 4 | 0 | 3（O-01 凭据；O-05/O-06←O-01） | 5.0 |
| P | 6 | 3 | 1（P-03） | 2（P-05←P-03、P-06←P-03+A-07） | 5.0 |
| Q | 8 | 1 | 0 | 7（Q-02..Q-08 全部待上游） | 11.0 |
| S | 5 | 2 | 1（S-01） | 2（S-02←S-01、S-05←S-01+S-02） | 5.0 |
| U | 10 | 4 | 4（U-02/U-06/U-07/U-08） | 2（U-09←U-06+U-08、U-10←U-07） | 10.5 |
| X | 10 | 10 | 0 | 0 | 0 |
| **计** | **107** | **74** | **12** | **21** | **≈58.5** |

\* 槽当量口径：HEAVY=2 / MEDIUM=1 / LIGHT=0.5 个 worker 会话（依据历史观察：HEAVY 卡普遍 1 个执行会话 + 证据/返修尾巴，如 wt313 重建、wt306 抢救）。O 线当量 8.0 中 5.0 被云端凭据单点冻结。

**RC 关键路径（Q-08 Final Gate 的六条必经链）**：
1. U-06 + U-08 → U-09 → Q-02/Q-03、G-05；
2. M-10 → Q-02；
3. E-03 → E-08 → Q-06；
4. D-07 → D-08 → Q-04；
5. S-01 → S-02 → S-05 → Q-05；
6. **O-01（凭据，外部阻塞）→ O-05 → Q-07**（O-06 亦挂 O-01）。

12 张 READY 中 10 张全部在这六条链的链头——**无一张多余卡**；队列派完即只剩凭据与链式等待。进度参照：09-19→09-25 六天 74 张（≈12 张/日满编），但剩余全是 HEAVY 尾巴+链式依赖，实际吞吐预计显著低于该速率；O 线解冻（凭据到手）可一次性释放 3 卡 8.0 当量。

## 5. tasks.json 回写机制缺失 — 最小回写方案建议（不执行）

**债务实锤**：① status 107 全 TODO；② done 数组滞后 11 张；③ `active` 含已 done 的 B-02；④ 唯一活台账 notes 是 117KB 追加式字符串，机器不可读；⑤ wt304/J-08 代码经 2b790fea「sweep-in」入库，提交与卡号脱钩——五个症状同一根因：**合并管线没有状态回写步骤，也没有防漂移守卫**。

**最小方案（推荐，四处改动）**：
1. **schema**：`tasks.json` 每个 task 增可选 `execution` 块 `{status: DONE|IN_FLIGHT|BLOCKED|READY, merged_in: <sha>, evidence: v3-output/<dir>, reviewed: R2|R1|单员全权, updated_at}`——规格字段（objective/work/acceptance）零改动，运行态集中在新增块。
2. **唯一写入口**：仅 Leader 整合管线（HANDOVER §5）第 8 步「删树+补位」后调用 `scripts/devtools/task_state_write.py <card> --status DONE --sha <merge_sha>`（读-改-写 + json 排序 + `git diff --stat` 自检），与台账 notes 追加同一 commit。
3. **防漂移守卫**（入 `run_all_rule_guards.sh`）：校验 (a) `execution.status=DONE` 的卡 `git log --grep` 能命中 merged_in sha 或卡号；(b) 台账 done 数组与 tasks.json DONE 集合双向一致。不一致即红——「忘回写」从静默债变成门禁红。
4. **一次性回填**：以本报告 §2 的 74 张判定为基线脚本化回填，一笔 commit。

**更小的替代方案**（若不愿动 tasks.json）：弃 status 回写，把 done 数组当唯一机器可读态，但必须配套第 3 步双向守卫 + 「合并即回写」纪律。不推荐——done 数组已经漂移过一次，且 notes 不可机读，同样的债会复发。

## 6. 关键发现与诚实边界

1. **发现（高）**：done 数组滞后 11 卡（§1），tasks.json 回写机制缺失（§5）——leader 若只看台账会漏掉 11 张已合并卡的下游解锁（本审计已修正）。
2. **发现（中）**：部分 v3-output 目录缺 `changes.patch`（WT307-S03、WT311-A06 仅 REPORT.md）——违反收工协议 §4-4d 的交付物尾账，非阻塞本审计，建议随下批补齐。
3. **发现（中）**：HANDOVER §13 候补池漏列了 8 张实际 READY 的卡（D-07/J-04/J-06/M-10/P-03/U-06/U-07/U-08）——该节是凭记忆速写，本报告为其精确化替代。
4. **发现（低）**：实际执行与卡面 deps 有偏离先例（J-02 声明依赖 J-01，J-01 至今未做但 J-02 已合并收账）——依赖图是调度参考非硬门；本审计 BLOCKED 判定一律按 tasks.json 声明 deps，Leader 可按战况裁剪（裁剪时留痕台账即可）。
5. **诚实边界**：本卡 LIGHT 只读——DONE=「已合并 main + 双证」，不重跑测试、不复验运行态（合并态 mypy/lint 复验属整合管线职责）；槽当量为历史观察估算非测量值；S-01 判 READY 但其验收需两账号 live realtime（此前 wt307/wt312 两度 DEFERRED），派发时应明确允许「报告先行 + live 证据二段式」，否则应转 BLOCKED(设备/HEAVY)。
6. **UNKNOWN 说明**：107 张全部给出判定，无 UNKNOWN。唯一保留意见同第 5 条：S-01 的 READY 成立以「允许二段式证据」为前提。

---
*wt346 收工。判定表证据指针可逐卡复核：`git log --oneline main | grep <卡号>`、`ls v3-output/ | grep -i <卡号>`、台账 done 数组。*
