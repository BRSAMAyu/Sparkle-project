# WT686 · U-05 续做——B-04-L-01 demo 首屏错误裸露收口 + U-09 chat 令牌撕裂机械收口

会话 wt686（卡池 U-05：首页/Goal/Chat 三屏 L2 产品化重构）｜base=8860af76｜worktree `agent/node-b/wt686/u05`｜分支 `agent/node-b/wt686/u05`
性质：**双证判 U-05 主体已完成不重做，续做产品化打磨机械项**（10/4 交付红线内：B-04 ledger B 级可静态修项 + U-09 矩阵点名 chat 撕裂收口；结构性重构一律入计划移交）。

---

## 0. 卡完成双证判定（不重做判据）

| 证据 | 内容 |
|---|---|
| 提交证据 | wt315 首轮 `cb022dad`（2026-09-24）：HOME 行动脊柱（growthSections 双渲染真缺陷修复）、GOAL `_MilestoneStrip`+`_GoalRecoveryActions`、CHAT `structured_suggestion_body` 长建议结构化；`git merge-base --is-ancestor cb022dad HEAD` = true |
| 模拟器证据 | wt324 `a08d20f0`：U-05 action spine + source/receipt PASS（32 截图），发现 F-1~F-11 |
| 闭环证据 | F-4 GlobalKey 崩溃 wt336 `a79d39be` 修复 + wt339 `45499ea8` group 同款清零 + 后续 DEFERRED 测试批 `450437c0` 红转绿**正式闭环（wt324 F-1~F-11 全收官）**；F-8 双 CTA 同批收口 |
| 本卡边界 | 卡面验收「5 秒测试/Persona A/B issue=0/功能不退化」中运行级证据（5 Persona screenshot A/B）属模拟器/真机面，wt324 已交付 PASS 段；本轮不重做、不伪造 |

## 1. 本轮实施（机械项，≤10/4 红线）

### V3-FIX-376 · B-04-L-01 demo 首屏理解快照错误裸露（B 级 → FIXED@c416d7db）
- **现象**（B-04 ledger 原录 + 本轮亲读 golden PNG 复核）：`home__main__demo_data` 主叙事句「早上好，今天先从一小步开始…」正下渲染「ⓘ 加载失败 轻触重试」，android/macos 两批一致；Q03 基线（WT401 C01）同位既有。
- **根因**：`understandingSnapshotProvider._fetch()` 无 demo 分支——demo 首屏直打真网 understanding 端点失败 → `UnderstandingSnapshotCard` error 分支渲染 `CompactErrorCard`。该错误行处于 HOME.md 第 5 层 understanding receipt 保留位（wt315 spine）。
- **修法**（ledger 裁决方向「demo 叙事源失败降级为隐藏/占位」）：`_fetch` 顶部 `DemoDataService.isDemoMode` 门控返回内建空快照；卡片（空 summary 默认文案）与 understanding_panel（既有 `isEmpty` 空态分支）的原生空态渲染承载，零新 UI 逻辑零新文案；与 `growth_narrative_repository` 的 `isDemoMode → placeholder()` 仓内先例同构。非 demo 路径逐字节不动；不改既有错误呈现语义（真机真后端失败仍诚实显示可重试错误）。
- **红先行**：新增 pin 测试 `understanding_snapshot_demo_placeholder_test`（2 case）——stash 修法跑红（demo 下 provider .future 抛网络错）→ 恢复 2/2 绿。

### V3-FIX-377 · U-09 矩阵点名的 chat 令牌双态撕裂机械收口首批（→ FIXED@3d00aec9）
- **依据**：U-09 `WT676_CONSISTENCY_DIFF_MATRIX.md` §2.1——chat fontSize 双态撕裂 108 字面量 vs 120 令牌形并存（最大字面量族面）；§5.2 收敛建议移交。
- **实施**（零风险机械统一式 = 字面量 → 同值既有 DS 令牌）：`fontSize: 12 → DS.fontSizeXs`（26 处）+ `fontSize: 16 → DS.fontSizeBase`（2 处）= **28 处 10 文件**（chat presentation/widgets，全部已 import design_system，零 import 增量，零视觉/行为变化）。撕裂面 108→80 字面量、120→148 令牌形。
- **族外值 80 处不动只登记**：10/11（含 11.5）属 TYPO-RHYTHM N41 sub-12 登记债（冻结只降、迁移归其 §3.1 数值迁移批）；13/14/18/12.5 需设计 owner 裁决（同 U-09 §5.1 圆角族外值处置先例）。

## 2. 计划移交（不在本轮实施）

1. **chat 撕裂残余 80 处**：随 chat 面收敛卡统一裁决（U-09 §5.2 原建议「随 chat 面收敛卡一次做」）；13/14/18 值需先扩族或归一（视觉决策需 golden 真机基线背书）。
2. **B-04-L-02/L-03**（chat 手机宽死区 / 桌面宽浮层叠压）：布局结构项，非机械可静态修，留 chat 收敛卡/桌面适配卡。
3. **B-04 基线重采**：V3-FIX-376 落地后 `home__main__demo_data` 渲染已变，v3-output/B-04 PNG（SHA8 d7a961da 批）陈旧——待下次 B-04 重采批刷新（本轮 golden 禁碰未执行；重采为 HEAVY 需过内存门）。
4. **UI-TOKENS 基线收紧**：fontSize 真实计数 727→641（含历批），基线 JSON 冻结未动；下轮 ratchet sweep 可 `--update-baseline` 锁定增益（避免与他卡 JSON 撞面，本轮不动）。

## 3. 验证件套（当场真跑）

| 门 | 结果 |
|---|---|
| dart analyze 全树 | **0 issue**（基线即 E0/W0/I0，零漂移；含新增 pin 测试文件） |
| 红先行 | stash V3-FIX-376 修法 → pin 测试 1 红；恢复 → **2/2 绿** |
| 定向 flutter test（--concurrency=1，swap 门内 1.1-1.5G） | **72/72 绿**：pin 2 + chat 直触 9（reasoning_visualization/agent_message_failed_state/offline_queue_indicator×2）+ 契约 18（j1/j3_closure/nav_contract/mirofish）+ 状态隔离与 overview 12（n4_session_isolation/understanding_overview/a11y_batch2_guard/group_chat_index_shift）+ demo 冒烟 24（main_pages_load/router_smoke/tab_zero/main_actions）+ j2_closure/dashboard_l2 7 |
| 全量治理守卫 | **86 规则 exit 0**（AQ/BG 环境项按先例自主仓补拷 gen 未入库） |
| ratchet 四件 | UI-TOKENS fontSize=641/727 只降、TYPO-RHYTHM sub12=234/234 零漂移、UX-COMP 25/58·34/40·40/40·200/201·121/121 PASS、SPACING PASS |
| dart format | 我改的行零新增漂移（agent_reasoning_bubble 手工收拢 + 尾逗号双门满足）；触达文件存在**既有** format 漂移（main 同判 4/4 changed），仓库无 format 门，不顺手重排制造噪声 |

## 4. Forbidden 自查

- 未重建权威真源：demo 门控消费既有 `DemoDataService.isDemoMode`（D04 受控轨合法面）与卡片既有空态渲染；零新真源零新文案。
- 未用 mock 冒充：demo 空快照 = 「尚无理解声明」的诚实空态，非伪造理解内容；非 demo 路径未动。
- 未只以静态阅读宣称体验：pin 测试红→绿 + 72 定向绿真跑；golden PNG 亲读定位错误行；运行级 Persona A/B 沿用 wt324 已有 PASS 证据不重做不伪造。
- 未弱化守卫：86 规则 exit 0；ratchet 四件 PASS 全只降/零漂移；错误呈现语义未砍（真失败仍可见可重试）。
- 未触碰：golden 基线文件、`.env`、`tasks.json`、arb（wt685 面）、galaxy E1 冻结预算文件；wt683/wt685/wt687/wt688 文件面零交叠（377 只消费既有令牌不新增，与 U-02 令牌定义无语义撞面）。
- 未 push 远端。

## 5. 交付物

- 实施双 commit：`c416d7db`（V3-FIX-376 + pin 测试）、`3d00aec9`（V3-FIX-377，10 文件 +31/−29）
- 台账 commit：本目录 REPORT.md + changes.patch
- 状态：**READY_FOR_REVIEW**（待独立会话审查；运行级 A/B 与 5 秒测试属既有 wt324 证据 + HUMAN_INBOX 段，本轮无新增伪造面）
